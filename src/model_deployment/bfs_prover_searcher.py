"""BFS-Prover (arXiv:2502.03438)의 탐색 알고리즘 충실 재구현.

논문 핵심(그대로 구현):
  · **length-normalized best-first search**: 노드 우선순위
        score(s_L) = ( Σ_{t=0}^{L-1} log p(a_t | s_t) ) / L^α
    분자 = root→노드 경로의 tactic log-prob 합, L = 경로 길이(tactic 수), α∈[0,1].
    α로 나눠 **깊은 경로 탐색을 장려**(누적 log-prob의 짧은-증명 편향 완화). 논문 평가값 α=0.5.
  · **expansion**: priority queue에서 최고 score pop → 정책 LLM이 tactic E개 샘플(평가 폭 E=2, temp 1.1).
    각 tactic → valid(큐에 추가) / complete(성공) / error(terminal, 버림).

주의: 논문 모델 BFS-Prover(Lean, expert-iter+DPO 학습)은 없음 → 우리 Coq 1.3B를 정책으로 사용.
Lean→Coq. **탐색 알고리즘은 rango 탐색과 안 섞은 순수 length-normalized BFS.** (rango classical의
누적-logprob 정렬과 달리 L^α 정규화가 핵심 차이 — 논문 그대로.)
"""
from __future__ import annotations
import heapq
import math
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from model_deployment.proof_manager import ProofManager, TacticResult
from model_deployment.tactic_gen_client import TacticGenClient
from model_deployment.straight_line_searcher import (
    StraightLineSuccess,
    StraightLineFailure,
)
from coqpyt.coq.lsp.structs import Goal


@dataclass
class BFSProverSearchConf:
    timeout: int
    alpha: float = 0.5          # length normalization 지수 (논문 평가값)
    expand_width: int = 2       # 노드당 샘플 tactic 수 E (논문 평가값)
    max_depth: int = 50
    print_proofs: bool = True
    initial_proof: Optional[str] = None
    trace_out: Optional[str] = None   # expert-iter/DPO용 트리 덤프 jsonl 경로(None=끔)
    # ── value-free structural search (VALUE_FREE_SEARCH.md) ──
    use_vfsearch: bool = False        # True=분해노드서 구조적 후보 열거 + MC-rollout 랭킹 + backtrack
    mc_K: int = 4                     # 분해 후보당 MC 롤아웃 수
    mc_D: int = 6                     # MC 롤아웃 깊이(step)
    mc_budget: int = 240              # 정리당 총 MC 롤아웃 상한(초과 시 logprob fallback) — compute 폭발 방지
    struct_cap: int = 8               # 분해노드당 MC 평가할 구조적 후보 상한
    ALIAS = "bfs_prover"

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> "BFSProverSearchConf":
        return cls(
            yaml_data["timeout"],
            yaml_data.get("alpha", 0.5),
            yaml_data.get("expand_width", 2),
            yaml_data.get("max_depth", 50),
            yaml_data.get("print_proofs", True),
            yaml_data.get("initial_proof", None),
            yaml_data.get("trace_out", None),
            yaml_data.get("use_vfsearch", False),
            yaml_data.get("mc_K", 4),
            yaml_data.get("mc_D", 6),
            yaml_data.get("mc_budget", 240),
            yaml_data.get("struct_cap", 8),
        )


@dataclass(order=True)
class _QNode:
    neg_score: float                         # heapq는 min-heap → -score로 최고 우선
    seq: int = field(compare=True)
    check_result: Any = field(compare=False)  # ProofCheckResult
    cum_logprob: float = field(compare=False)
    depth: int = field(compare=False)          # L (tactic 수)
    node_id: int = field(compare=False, default=0)


class BFSProverSearcher:
    def __init__(
        self,
        tactic_clients: list[TacticGenClient],
        proof_manager: ProofManager,
        timeout: int,
        alpha: float = 0.5,
        expand_width: int = 2,
        max_depth: int = 50,
        print_proofs: bool = True,
        initial_proof: Optional[str] = None,
        trace_out: Optional[str] = None,
        use_vfsearch: bool = False,
        mc_K: int = 4,
        mc_D: int = 6,
        mc_budget: int = 240,
        struct_cap: int = 8,
    ):
        self.tactic_clients = tactic_clients
        self.proof_manager = proof_manager
        self.timeout = timeout
        self.alpha = alpha
        self.expand_width = expand_width
        self.max_depth = max_depth
        self.print_proofs = print_proofs
        self.trace_out = trace_out
        self.use_vfsearch = use_vfsearch
        self.mc_K = mc_K
        self.mc_D = mc_D
        self.mc_budget = mc_budget
        self.struct_cap = struct_cap
        self.mc_spent = 0             # 이 정리에서 소비한 MC 롤아웃 수
        self.total_model_time = 0.0
        # 트리 덤프용: node_id -> record{state_example, tactics[]}, 그리고 부모 링크.
        self.trace_records: dict[int, dict] = {}
        self.node_parent: dict[int, tuple[int, str]] = {}  # node_id -> (parent_id, tactic)

        init_dset = proof_manager.get_initial_context()
        if init_dset is None:
            raise ValueError("Could not get initial datasetfile")
        self.theorem = init_dset.proofs[-1].theorem
        init = proof_manager.check_proof(initial_proof or "", self.theorem)
        assert init.tactic_result == TacticResult.VALID
        self.init_check = init
        self.seen: set[str] = set()  # 동일 state 재확장 방지(표준 graph-BFS 가드)

    @classmethod
    def from_conf(cls, conf: BFSProverSearchConf, tactic_clients, proof_manager):
        return cls(
            tactic_clients, proof_manager, conf.timeout,
            getattr(conf, "alpha", 0.5), getattr(conf, "expand_width", 2),
            getattr(conf, "max_depth", 50), getattr(conf, "print_proofs", True),
            getattr(conf, "initial_proof", None),
            getattr(conf, "trace_out", None),
            getattr(conf, "use_vfsearch", False),
            getattr(conf, "mc_K", 4), getattr(conf, "mc_D", 6),
            getattr(conf, "mc_budget", 240), getattr(conf, "struct_cap", 8),
        )

    def _goal_key(self, goals: list[Goal]) -> str:
        return "\n===\n".join(repr(g) for g in goals)

    def _score(self, cum_logprob: float, depth: int) -> float:
        # score = cum_logprob / L^α  (L≥1)
        L = max(1, depth)
        return cum_logprob / (L ** self.alpha)

    # ── value-free structural search (VALUE_FREE_SEARCH.md) ─────────────
    def _is_decomp_point(self, check) -> bool:
        """현재 goal에 destruct/induction/inversion 가능한 hyp/inductive var가 있으면 분해 결정 지점."""
        from tactic_gen.grpo_rollout import _targeted_cands, _goals_str
        return len(_targeted_cands(_goals_str(check))) > 0

    def _enum_structural(self, check) -> list[str]:
        """분해 후보 강제 열거(각 가설 destruct / 각 변수 induction / inversion). coverage 22% 직격."""
        from tactic_gen.grpo_rollout import _targeted_cands, _goals_str
        return _targeted_cands(_goals_str(check))[: self.struct_cap]

    def _mc_value(self, child_script: str, theorem) -> float:
        """value-free 점수: child state에서 policy로 K개 짧은(깊이 D) 롤아웃 → subgoal 닫힘률(진전).
        1.3B는 D step 안에 전체 QED가 드무니 subgoal-close(goal 수↓)를 dense 신호로 사용(도달성 직격,
        전부-0 랭킹붕괴 완화). mc_budget 초과 시 -1 반환(호출부가 logprob fallback)."""
        from tactic_gen.grpo_rollout import rollout_attempt
        if self.mc_spent + self.mc_K > self.mc_budget:
            return -1.0
        prog = 0
        t0 = time.time()
        for i in range(self.mc_K):
            r = rollout_attempt(
                self.tactic_clients[0], self.proof_manager, theorem,
                child_script, max_steps=self.mc_D, temperature_seed=i,
                max_retries=1, subgoal_reward=True,
            )
            self.mc_spent += 1
            if r.get("reward", 0.0) >= 1.0:
                prog += 1
        self.total_model_time += time.time() - t0
        return prog / self.mc_K

    def search(self, **kwargs) -> StraightLineSuccess | StraightLineFailure:
        start = time.time()
        frontier: list[_QNode] = []
        seq = 0
        # root: depth 0, cum_logprob 0 → score 0, node_id 0
        heapq.heappush(frontier, _QNode(-0.0, seq, self.init_check, 0.0, 0, 0))
        client = self.tactic_clients[0]

        while frontier and time.time() - start < self.timeout:
            node = heapq.heappop(frontier)
            if node.depth >= self.max_depth:
                continue
            new_proof = node.check_result.new_proof
            if new_proof is None:
                continue
            # BFS-Prover는 pure best-first tree(논문). goal_key 병합/스킵 안 함
            # ("Proof." 같은 goal-불변 tactic이 스킵돼 진전 막히는 것 방지). max_depth로 bound.
            dset = self.proof_manager.build_dset_file(new_proof)
            proof = dset.proofs[-1]
            script = proof.proof_prefix_to_string(proof.steps[-1], include_theorem=False)
            self._record_state(node.node_id, proof, dset, client)
            t0 = time.time()
            recs = client.get_recs(  # E개 샘플 (beam=False → temperature 샘플링)
                len(proof.steps) - 1, proof, dset, self.expand_width,
                beam=False, file_prefix=self.proof_manager.file_prefix,
            )
            self.total_model_time += time.time() - t0

            # ── 후보 tactic 구성 ──
            # vfsearch + 분해노드: 구조적 후보(강제 열거, logprob=None→MC 랭킹) + 정책 top-k(logprob).
            # 아니면: 정책 top-k만 (기존 BFS-Prover).
            decomp = self.use_vfsearch and self._is_decomp_point(node.check_result)
            cand: list[tuple[str, Optional[float]]] = []
            if decomp:
                for t in self._enum_structural(node.check_result):
                    cand.append((t, None))          # 구조적 후보 = MC로 점수
            seen_t = {t for t, _ in cand}
            for t, lp in zip(recs.next_tactic_list, recs.score_list):
                if t not in seen_t:
                    cand.append((t, lp))            # 정책 후보 = logprob 점수
                    seen_t.add(t)

            for tactic, tac_logprob in cand:
                res = self.proof_manager.check_proof(script + tactic, new_proof.theorem)
                if self.print_proofs:
                    tag = "VF" if (decomp and tac_logprob is None) else "BFS"
                    print(f"  [{tag} d={node.depth+1}] {tactic.strip()!r} → {res.tactic_result.name}")
                self._record_tactic(node.node_id, tactic, res.tactic_result.name)
                if res.tactic_result == TacticResult.COMPLETE:
                    if self.print_proofs:
                        print(f"[BFS-Prover] 성공 (탐색노드 {len(self.seen)})")
                    self._mark_success_path(node.node_id, tactic)
                    self._dump_trace()
                    return StraightLineSuccess(
                        time.time() - start, self.total_model_time, res.new_proof, [],
                    )
                if res.tactic_result == TacticResult.VALID:
                    depth = node.depth + 1
                    if decomp and tac_logprob is None:
                        # ★ value-free: 이 분해가 좋은지 MC-rollout 진전률로 점수. budget 있으면 큰 bonus로 우선.
                        mcv = self._mc_value(script + tactic, new_proof.theorem)
                        cum = node.cum_logprob       # 구조적 후보엔 logprob 없음(불변)
                        if mcv >= 0.0:
                            neg_score = -(1000.0 + mcv)   # 분해 자식 먼저 확장(진전 높을수록 먼저)
                        else:
                            neg_score = -self._score(cum, depth)  # budget 소진 → logprob fallback
                    else:
                        cum = node.cum_logprob + tac_logprob   # Σ log p(a_t|s_t)
                        neg_score = -self._score(cum, depth)    # / L^α
                    seq += 1
                    child_id = seq
                    self.node_parent[child_id] = (node.node_id, tactic)
                    heapq.heappush(frontier, _QNode(neg_score, seq, res, cum, depth, child_id))
                # INVALID → terminal, 버림 (stuck→backtrack은 frontier가 자동)
        self._dump_trace()
        return StraightLineFailure(time.time() - start, self.total_model_time, [])

    # ── 트리 덤프(expert-iter/DPO 데이터) ──────────────────────────────
    def _record_state(self, node_id: int, proof, dset, client) -> None:
        if not self.trace_out or node_id in self.trace_records:
            return
        try:
            fmt = client.formatters[0]
            example = fmt.example_from_step(len(proof.steps) - 1, proof.proof_idx, dset)
            state = example.to_json()
        except Exception:
            state = None
        self.trace_records[node_id] = {"state_example": state, "tactics": []}

    def _record_tactic(self, node_id: int, tactic: str, result: str) -> None:
        if not self.trace_out:
            return
        rec = self.trace_records.get(node_id)
        if rec is not None:
            rec["tactics"].append({
                "tactic": tactic, "result": result,
                "leads_to_success": (result == "COMPLETE"),
            })

    def _mark_success_path(self, node_id: int, tactic: str) -> None:
        """COMPLETE 낸 (node,tactic)부터 root까지 부모 tactic들을 성공경로로 표시."""
        if not self.trace_out:
            return
        cur, tac = node_id, tactic
        while True:
            rec = self.trace_records.get(cur)
            if rec is not None:
                for t in rec["tactics"]:
                    if t["tactic"] == tac:
                        t["leads_to_success"] = True
            if cur not in self.node_parent:
                break
            cur, tac = self.node_parent[cur]

    def _dump_trace(self) -> None:
        if not self.trace_out or not self.trace_records:
            return
        import json
        from pathlib import Path
        p = Path(self.trace_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a") as f:
            for rec in self.trace_records.values():
                if rec.get("state_example") is not None:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
