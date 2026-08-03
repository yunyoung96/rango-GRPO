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
    # 분해 노드에서 구조적 분해(destruct/induction/inversion)를 강제 열거하고, 각 후보를
    # value-free MC 롤아웃 성공률로 채점(critic 학습 불요). backtrack은 best-first가 자동 제공.
    use_vfsearch: bool = False
    mc_K: int = 4               # MC 롤아웃 수(분해 노드에서만)
    mc_D: int = 6               # MC 깊이(step)
    struct_cap: int = 8         # 분해 후보 최대 수(compute bound)
    # ── Planner–Executor (PLANNER_EXECUTOR_DESIGN.md) ──
    # 분해 노드에서 강한 로컬 planner가 고수준 분해(tactic 후보)를 제안 → 강제 후보로.
    # value-free MC(sparse 붕괴)와 달리 dense 채점(planner 순위 + goal 수 감소).
    use_planner: bool = False
    planner_model: str = "Qwen/Qwen2.5-Coder-7B-Instruct"
    planner_4bit: bool = False
    planner_device: str = "cuda:0"
    planner_url: Optional[str] = None   # 설정 시 persistent planner_server(HTTP) 사용(정리 재로드 방지)
    plan_bonus: float = 500.0   # planner 후보 우선확장 bonus
    # planner 게이팅: 취약한 _is_decomp_point 대신 depth 기반(초반 분해가 병목 §divergence).
    plan_max_depth: int = 6     # 이 depth 이하 노드에서 planner 호출
    plan_budget: int = 20       # 정리당 planner 호출(=분해노드) 상한(compute bound)
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
            yaml_data.get("struct_cap", 8),
            yaml_data.get("use_planner", False),
            yaml_data.get("planner_model", "Qwen/Qwen2.5-Coder-7B-Instruct"),
            yaml_data.get("planner_4bit", False),
            yaml_data.get("planner_device", "cuda:0"),
            yaml_data.get("plan_bonus", 500.0),
            yaml_data.get("plan_max_depth", 6),
            yaml_data.get("plan_budget", 20),
            yaml_data.get("planner_url", None),
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
        struct_cap: int = 8,
        use_planner: bool = False,
        planner_model: str = "Qwen/Qwen2.5-Coder-7B-Instruct",
        planner_4bit: bool = False,
        planner_device: str = "cuda:0",
        plan_bonus: float = 500.0,
        plan_max_depth: int = 6,
        plan_budget: int = 20,
        planner_url: Optional[str] = None,
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
        self.struct_cap = struct_cap
        self.n_decomp_nodes = 0   # 진단/로그용: MC를 돌린 분해 노드 수
        self.use_planner = use_planner
        self.plan_bonus = plan_bonus
        self.plan_max_depth = plan_max_depth
        self.plan_budget = plan_budget
        self.planner = None
        if use_planner:
            from model_deployment.planner_client import PlannerClient, PlannerConf
            self.planner = PlannerClient(PlannerConf(
                model_name=planner_model, load_4bit=planner_4bit, device=planner_device,
                server_url=planner_url,   # 설정 시 persistent 서버(HTTP), 아니면 in-process 로드
            ))
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
            getattr(conf, "mc_K", 4),
            getattr(conf, "mc_D", 6),
            getattr(conf, "struct_cap", 8),
            getattr(conf, "use_planner", False),
            getattr(conf, "planner_model", "Qwen/Qwen2.5-Coder-7B-Instruct"),
            getattr(conf, "planner_4bit", False),
            getattr(conf, "planner_device", "cuda:0"),
            getattr(conf, "plan_bonus", 500.0),
            getattr(conf, "plan_max_depth", 6),
            getattr(conf, "plan_budget", 20),
            getattr(conf, "planner_url", None),
        )

    def _goal_key(self, goals: list[Goal]) -> str:
        return "\n===\n".join(repr(g) for g in goals)

    def _score(self, cum_logprob: float, depth: int) -> float:
        # score = cum_logprob / L^α  (L≥1)
        L = max(1, depth)
        return cum_logprob / (L ** self.alpha)

    # ── value-free structural search helpers (VALUE_FREE_SEARCH.md §7) ──────
    @staticmethod
    def _vf_imports():
        # lazy import: vfsearch 안 쓰면 grpo_rollout(무거운 의존) 로드 회피.
        from tactic_gen.grpo_rollout import (
            rollout_attempt as _ra,
            _targeted_cands as _tc,
            _goals_str as _gs,
        )
        return _ra, _tc, _gs

    def _goals_list(self, check) -> list:
        _, _, _gs = self._vf_imports()
        return _gs(check)

    def _is_decomp_point(self, check) -> bool:
        """현재 goal에 destruct/induction/inversion 가능한 hyp/inductive var 존재 → 분해 결정 지점."""
        _, _tc, _gs = self._vf_imports()
        return len(_tc(_gs(check))) > 0

    def _enumerate_structural(self, check) -> list[str]:
        """각 hyp destruct / 각 var induction / inversion (Coq이 무효 필터). compute bound=struct_cap."""
        _, _tc, _gs = self._vf_imports()
        return _tc(_gs(check))[: self.struct_cap]

    def _mc_value(self, child_script: str, theorem) -> float:
        """value-free 점수: 이 state에서 policy로 K개 짧은(깊이 D) 롤아웃 → QED 도달률.
        QED가 하나도 없으면 subgoal-close(goal수↓) 비율을 작은 가중으로(랭킹 붕괴 방지). critic 학습 없음."""
        _ra, _, _ = self._vf_imports()
        client = self.tactic_clients[0]
        qed = 0
        prog = 0
        for i in range(self.mc_K):
            r = _ra(client, self.proof_manager, theorem, child_script, self.mc_D,
                    temperature_seed=i, max_retries=0)
            if r["reward"] >= 1.0:
                qed += 1
                continue
            rp = _ra(client, self.proof_manager, theorem, child_script, self.mc_D,
                     temperature_seed=i, max_retries=0, subgoal_reward=True)
            if rp["reward"] >= 1.0:
                prog += 1
        K = max(self.mc_K, 1)
        return qed / K + 0.1 * (prog / K)

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

            # ★ 분해 노드면 구조적 분해를 강제 후보로 정책 후보 앞에 붙인다.
            #   coverage 22%(정책이 정답 분해를 안 생성) 병목을 우회:
            #     · use_planner : 강한 로컬 planner가 고수준 분해 tactic 제안(PLANNER_EXECUTOR_DESIGN)
            #     · use_vfsearch: 맹목 structural 열거(_targeted_cands)
            cand = list(zip(recs.next_tactic_list, recs.score_list))  # (tactic, logprob)
            # ★ planner: depth 기반 게이팅(취약한 _is_decomp_point 비의존). 초반 노드=분해 결정 지점.
            #   vfsearch: 기존 _is_decomp_point(파서 수정으로 이제 다중이름/쉼표 goal도 감지).
            if self.use_planner:
                is_dp = (node.depth <= self.plan_max_depth) and (self.n_decomp_nodes < self.plan_budget)
            elif self.use_vfsearch:
                is_dp = self._is_decomp_point(node.check_result)
            else:
                is_dp = False
            planner_set: set[str] = set()
            if is_dp:
                self.n_decomp_nodes += 1
                if self.use_planner and self.planner is not None:
                    struct = self.planner.plan("\n".join(self._goals_list(node.check_result)))
                    planner_set = set(struct)
                    tag = "planner"
                else:
                    struct = self._enumerate_structural(node.check_result)
                    tag = "vfsearch"
                cand = [(t, None) for t in struct] + cand   # 분해 후보 먼저, logprob 없음
                if self.print_proofs:
                    print(f"  [{tag}] 분해노드#{self.n_decomp_nodes} d={node.depth} "
                          f"분해후보 {len(struct)} + 정책 {len(recs.next_tactic_list)}")

            for tactic, tac_logprob in cand:
                res = self.proof_manager.check_proof(script + tactic, new_proof.theorem)
                if self.print_proofs:
                    print(f"  [BFS-Prover d={node.depth+1}] {tactic.strip()!r} → {res.tactic_result.name}")
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
                    lp = tac_logprob if tac_logprob is not None else 0.0
                    cum = node.cum_logprob + lp   # Σ log p(a_t|s_t) (분해 후보는 logprob 0=중립)
                    depth = node.depth + 1
                    is_struct_child = is_dp and tac_logprob is None  # 분해 후보에서 나온 자식
                    if self.use_planner and is_struct_child:
                        # ★ dense 채점(MC 금지): planner 순위(seq가 보존) + goal 수 감소.
                        #   sparse-reward MC가 17%로 붕괴한 교훈 → QED 롤아웃 안 씀.
                        ng = len(self._goals_list(res))
                        bonus = self.plan_bonus + (10.0 if tactic in planner_set else 0.0)
                        score = bonus - 0.1 * ng
                    elif self.use_vfsearch and is_struct_child and (time.time() - start) < self.timeout:
                        v = self._mc_value(script + tactic, new_proof.theorem)
                        score = 1000.0 + v
                    else:
                        score = self._score(cum, depth)         # / L^α (기존 BFS-Prover)
                    seq += 1
                    child_id = seq
                    self.node_parent[child_id] = (node.node_id, tactic)
                    heapq.heappush(frontier, _QNode(-score, seq, res, cum, depth, child_id))
                # INVALID → terminal, 버림 (stuck→backtrack은 best-first frontier가 자동)
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
