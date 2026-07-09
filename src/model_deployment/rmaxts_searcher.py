"""RMaxTS — DeepSeek-Prover-V1.5 (arXiv:2408.08152)의 탐색 알고리즘 충실 재구현.

논문 핵심(그대로 구현):
  · 트리 노드 = tactic state. 같은 state는 **병합**(동치 tactic 집합 저장).
  · **truncate-and-resume**: state에서 증명을 생성 → Coq 검증 → 첫 에러에서 자르고 유효 prefix만
    노드 경로로 삽입 → 그 state에서 재개.
  · **DUCB 선택**: Q_DUCB = W_γ/N_γ + sqrt(2 ln ΣN_γ / N_γ), γ=0.99 (할인 카운트).
  · **RMax intrinsic reward**: R = 1[롤아웃에서 새 노드가 하나라도 추가됨] (novelty 탐색; 외부보상 없음).
  · **expansion**: 선택 노드에서 whole-proof 롤아웃 1회 → 여러 tactic(노드 경로) 삽입.
  · **backprop**: 궤적 (s,a)마다 N_γ←γN_γ+1, W_γ←γW_γ+R (할인 누적).

주의(불가피한 대체): 논문 모델 DeepSeek-Prover-V1.5(7B, Lean)은 없음 → 우리 Coq 모델(1.3B)을 정책으로
사용. Lean→Coq(coqpyt). **알고리즘은 rango 탐색과 안 섞은 순수 RMaxTS.** 정책 모델만 공유 인프라.
"""
from __future__ import annotations
import math
import time
from dataclasses import dataclass
from typing import Any, Optional

from data_management.dataset_file import Proof
from model_deployment.proof_manager import ProofManager, TacticResult
from model_deployment.tactic_gen_client import TacticGenClient
from model_deployment.straight_line_searcher import (
    StraightLineSuccess,
    StraightLineFailure,
)
from coqpyt.coq.lsp.structs import Goal

GAMMA = 0.99  # 논문 DUCB 할인계수


@dataclass
class RMaxTSSearchConf:
    timeout: int
    n_rollout_steps: int = 8        # truncate-and-resume 롤아웃 최대 tactic 수
    print_proofs: bool = True
    initial_proof: Optional[str] = None
    ALIAS = "rmaxts"

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> "RMaxTSSearchConf":
        return cls(
            yaml_data["timeout"],
            yaml_data.get("n_rollout_steps", 8),
            yaml_data.get("print_proofs", True),
            yaml_data.get("initial_proof", None),
        )


class RMaxNode:
    """트리 노드 = tactic state. 자식 = 이 state에서 시도한 tactic(action). DUCB 통계는 할인 카운트."""

    def __init__(self, check_result: Any, goal_key: str):
        self.check_result = check_result          # ProofCheckResult (new_proof, current_goals)
        self.goal_key = goal_key
        self.children: dict[str, "RMaxNode"] = {}  # tactic -> child(=도달 state, 병합됨)
        self.N: dict[str, float] = {}             # N_γ(self, tactic)
        self.W: dict[str, float] = {}             # W_γ(self, tactic)
        self.tactics: list[str] = []              # 시도한 tactic들(동치집합/자식키)
        self.terminal = False


class RMaxTSSearcher:
    def __init__(
        self,
        tactic_clients: list[TacticGenClient],
        proof_manager: ProofManager,
        timeout: int,
        n_rollout_steps: int = 8,
        print_proofs: bool = True,
        initial_proof: Optional[str] = None,
    ):
        self.tactic_clients = tactic_clients
        self.proof_manager = proof_manager
        self.timeout = timeout
        self.n_rollout_steps = n_rollout_steps
        self.print_proofs = print_proofs
        self.total_model_time = 0.0

        init_dset = proof_manager.get_initial_context()
        if init_dset is None:
            raise ValueError("Could not get initial datasetfile")
        theorem = init_dset.proofs[-1].theorem
        init = proof_manager.check_proof(initial_proof or "", theorem)
        assert init.tactic_result == TacticResult.VALID and init.current_goals is not None
        self.theorem = theorem
        self.root = RMaxNode(init, self._goal_key(init.current_goals))
        self.nodes: dict[str, RMaxNode] = {self.root.goal_key: self.root}  # state 병합 테이블

    @classmethod
    def from_conf(cls, conf: RMaxTSSearchConf, tactic_clients, proof_manager):
        return cls(
            tactic_clients, proof_manager, conf.timeout,
            getattr(conf, "n_rollout_steps", 8),
            getattr(conf, "print_proofs", True),
            getattr(conf, "initial_proof", None),
        )

    def _goal_key(self, goals: list[Goal]) -> str:
        return "\n===\n".join(repr(g) for g in goals)

    # ── DUCB 선택: root에서 leaf까지 하강 ──────────────────────────────
    def _select(self) -> tuple[RMaxNode, list[tuple[RMaxNode, str]]]:
        node = self.root
        path: list[tuple[RMaxNode, str]] = []
        while node.children and not node.terminal:
            total = sum(node.N.get(t, 0.0) for t in node.tactics) + 1e-9

            def ducb(t: str) -> float:
                n = node.N.get(t, 0.0) + 1e-9
                q = node.W.get(t, 0.0) / n
                return q + math.sqrt(2.0 * math.log(total) / n)

            best_t = max(node.tactics, key=ducb)
            path.append((node, best_t))
            child = node.children[best_t]
            if child is node:  # self-merge 방지
                break
            node = child
        return node, path

    # ── expansion: truncate-and-resume 롤아웃 ────────────────────────
    def _expand(self, leaf: RMaxNode, client: TacticGenClient, start: float):
        cur = leaf
        new_path: list[tuple[RMaxNode, str]] = []
        any_new = False
        for _ in range(self.n_rollout_steps):
            if time.time() - start >= self.timeout:
                break
            new_proof = cur.check_result.new_proof
            if new_proof is None:
                break
            dset = self.proof_manager.build_dset_file(new_proof)
            proof = dset.proofs[-1]
            script = proof.proof_prefix_to_string(proof.steps[-1], include_theorem=False)
            t0 = time.time()
            recs = client.get_recs(  # n=1, beam=False → temperature=1.0 샘플링(다양 롤아웃)
                len(proof.steps) - 1, proof, dset, 1,
                beam=False, file_prefix=self.proof_manager.file_prefix,
            )
            self.total_model_time += time.time() - t0
            if not recs.next_tactic_list:
                break
            tactic = recs.next_tactic_list[0]
            res = self.proof_manager.check_proof(script + tactic, new_proof.theorem)
            if self.print_proofs:
                print(f"  [RMaxTS] tactic={tactic.strip()!r} → {res.tactic_result.name}")
            if res.tactic_result == TacticResult.COMPLETE:
                new_path.append((cur, tactic))
                return res.new_proof, new_path, True   # 증명 성공
            if res.tactic_result == TacticResult.INVALID:
                break                                    # truncate at first error
            # VALID: 노드 병합(state 동일하면 기존 노드 재사용 = 동치 tactic 추가)
            gk = self._goal_key(res.current_goals)
            if gk in self.nodes:
                child = self.nodes[gk]
            else:
                child = RMaxNode(res, gk)
                self.nodes[gk] = child
                any_new = True
            if tactic not in cur.children:
                cur.children[tactic] = child
                cur.tactics.append(tactic)
                cur.N[tactic] = 0.0
                cur.W[tactic] = 0.0
            new_path.append((cur, tactic))
            cur = child
        return None, new_path, any_new

    # ── backprop: 할인 누적 ──────────────────────────────────────────
    def _backprop(self, sel_path, new_path, reward: float):
        for node, tactic in sel_path + new_path:
            node.N[tactic] = GAMMA * node.N.get(tactic, 0.0) + 1.0
            node.W[tactic] = GAMMA * node.W.get(tactic, 0.0) + reward

    def search(self, **kwargs) -> StraightLineSuccess | StraightLineFailure:
        start = time.time()
        it = 0
        while time.time() - start < self.timeout:
            it += 1
            client = self.tactic_clients[it % len(self.tactic_clients)]
            leaf, sel_path = self._select()
            success_proof, new_path, any_new = self._expand(leaf, client, start)
            reward = 1.0 if any_new else 0.0   # RMax intrinsic
            self._backprop(sel_path, new_path, reward)
            if success_proof is not None:
                if self.print_proofs:
                    print(f"[RMaxTS] 성공 (iter {it}, 노드 {len(self.nodes)})")
                return StraightLineSuccess(
                    time.time() - start, self.total_model_time, success_proof, [],
                )
        return StraightLineFailure(time.time() - start, self.total_model_time, [])
