"""LeanProgress(arXiv:2502.17925) — progress critic 로 유도되는 best-first 탐색.

frontier 점수:
    C(s) = α · N(s)  +  (1−α) · P(s)
      N(s) = 1 − min(n̂,N_MAX)/N_MAX    ∈[0,1]   n̂ = critic 이 예측한 **남은 tactic 수**
      P(s) = exp( Σlogp / L )           ∈(0,1]   경로 tactic 들의 **기하평균 확률**

★ 스케일 맞춤(중요): 논문은 "N 과 누적 logprob 을 블렌드"라고만 쓰지만, N∈[0,1] 인데 누적
  logprob 은 −50 까지 간다. 그대로 더하면 α 가 사실상 무의미해진다(logprob 항이 압도).
  그래서 P 를 exp(평균 logprob)=기하평균 확률로 [0,1] 에 맞춘다. exp 는 단조증가라
  **α=0 이면 순위가 정확히 bfs-a1(length-normalized BFS, α_len=1.0, 우리 최강 16/40)과 동일**하다.
  → α 가 유일한 변인이 된다.

★ α 는 반드시 작아야 한다(논문 검증): α=0.2 가 최적, **α=1.0(순수 value 랭킹)이면 18.5% 로 붕괴**.
  우리 rango-qed(11/40, −1)가 정확히 value 로 랭킹해서 죽었다. critic 은 **소수항**이다.
"""
from __future__ import annotations

import heapq
import math
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from coqpyt.coq.lsp.structs import Goal

from model_deployment.proof_manager import ProofManager, TacticResult
from model_deployment.straight_line_searcher import (
    StraightLineFailure,
    StraightLineSuccess,
)
from model_deployment.tactic_gen_client import TacticGenClient
from tactic_gen.progress_critic import format_goals


@dataclass
class ProgressSearchConf:
    timeout: int
    alpha: float = 0.2  # critic 가중치. 논문 최적값. 0 이면 bfs-a1 과 동일
    expand_width: int = 2
    max_depth: int = 50
    critic_dir: Optional[str] = None  # models/progress_critic (adapter/ + head.pt)
    base_model: str = "deepseek-ai/deepseek-coder-1.3b-instruct"
    print_proofs: bool = True
    initial_proof: Optional[str] = None
    ALIAS = "progress"

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> "ProgressSearchConf":
        return cls(
            yaml_data["timeout"],
            yaml_data.get("alpha", 0.2),
            yaml_data.get("expand_width", 2),
            yaml_data.get("max_depth", 50),
            yaml_data.get("critic_dir", None),
            yaml_data.get("base_model", "deepseek-ai/deepseek-coder-1.3b-instruct"),
            yaml_data.get("print_proofs", True),
            yaml_data.get("initial_proof", None),
        )


@dataclass(order=True)
class _QNode:
    neg_score: float
    seq: int = field(compare=True)
    check_result: Any = field(compare=False)
    cum_logprob: float = field(compare=False)
    depth: int = field(compare=False)


class ProgressSearcher:
    def __init__(
        self,
        tactic_clients: list[TacticGenClient],
        proof_manager: ProofManager,
        timeout: int,
        alpha: float = 0.2,
        expand_width: int = 2,
        max_depth: int = 50,
        critic_dir: Optional[str] = None,
        base_model: str = "deepseek-ai/deepseek-coder-1.3b-instruct",
        print_proofs: bool = True,
        initial_proof: Optional[str] = None,
    ):
        self.tactic_clients = tactic_clients
        self.proof_manager = proof_manager
        self.timeout = timeout
        self.alpha = alpha
        self.expand_width = expand_width
        self.max_depth = max_depth
        self.print_proofs = print_proofs
        self.total_model_time = 0.0
        self.total_critic_time = 0.0

        self.critic = None
        if alpha > 0.0:
            if critic_dir is None:
                raise ValueError("alpha>0 인데 critic_dir 이 없습니다.")
            from tactic_gen.progress_critic import ProgressPredictor

            self.critic = ProgressPredictor(
                adapter_dir=f"{critic_dir}/adapter",
                head_path=f"{critic_dir}/head.pt",
                base_model=base_model,
            )

        init_dset = proof_manager.get_initial_context()
        if init_dset is None:
            raise ValueError("Could not get initial datasetfile")
        self.theorem = init_dset.proofs[-1].theorem
        init = proof_manager.check_proof(initial_proof or "", self.theorem)
        assert init.tactic_result == TacticResult.VALID
        self.init_check = init

    @classmethod
    def from_conf(cls, conf: ProgressSearchConf, tactic_clients, proof_manager):
        return cls(
            tactic_clients, proof_manager, conf.timeout, conf.alpha,
            conf.expand_width, conf.max_depth, conf.critic_dir, conf.base_model,
            conf.print_proofs, conf.initial_proof,
        )

    def _policy_term(self, cum_logprob: float, depth: int) -> float:
        """P(s) = exp(평균 tactic logprob) = 기하평균 확률 ∈(0,1]."""
        return math.exp(cum_logprob / max(1, depth))

    def _critic_term(self, goals: Optional[list[Goal]]) -> float:
        """N(s) ∈[0,1]. goal 이 없으면(=닫힘) 1."""
        if self.critic is None:
            return 0.0
        if not goals:
            return 1.0
        t0 = time.time()
        v = self.critic.value(format_goals(goals))
        self.total_critic_time += time.time() - t0
        return v

    def _score(self, cum_logprob: float, depth: int, goals) -> float:
        p = self._policy_term(cum_logprob, depth)
        if self.alpha <= 0.0:
            return p  # 정확히 bfs-a1 (exp 는 단조 → 순위 동일)
        n = self._critic_term(goals)
        return self.alpha * n + (1.0 - self.alpha) * p

    def search(self, **kwargs) -> StraightLineSuccess | StraightLineFailure:
        start = time.time()
        frontier: list[_QNode] = []
        seq = 0
        root_score = self._score(0.0, 0, self.init_check.current_goals)
        heapq.heappush(frontier, _QNode(-root_score, seq, self.init_check, 0.0, 0))
        client = self.tactic_clients[0]

        while frontier and time.time() - start < self.timeout:
            node = heapq.heappop(frontier)
            if node.depth >= self.max_depth:
                continue
            new_proof = node.check_result.new_proof
            if new_proof is None:
                continue

            dset = self.proof_manager.build_dset_file(new_proof)
            proof = dset.proofs[-1]
            script = proof.proof_prefix_to_string(proof.steps[-1], include_theorem=False)

            t0 = time.time()
            recs = client.get_recs(
                len(proof.steps) - 1, proof, dset, self.expand_width,
                beam=False, file_prefix=self.proof_manager.file_prefix,
            )
            self.total_model_time += time.time() - t0

            for tactic, tac_logprob in zip(recs.next_tactic_list, recs.score_list):
                res = self.proof_manager.check_proof(script + tactic, new_proof.theorem)
                if res.tactic_result == TacticResult.COMPLETE:
                    if self.print_proofs:
                        print(f"[progress] 성공 (critic {self.total_critic_time:.1f}s / "
                              f"model {self.total_model_time:.1f}s)")
                    return StraightLineSuccess(
                        time.time() - start, self.total_model_time, res.new_proof, []
                    )
                if res.tactic_result != TacticResult.VALID:
                    continue

                cum = node.cum_logprob + tac_logprob
                depth = node.depth + 1
                score = self._score(cum, depth, res.current_goals)
                if self.print_proofs:
                    print(f"  [progress d={depth}] {tactic.strip()!r} → VALID  C={score:.4f}")
                seq += 1
                heapq.heappush(frontier, _QNode(-score, seq, res, cum, depth))

        if self.print_proofs:
            print(f"[progress] 실패 (critic {self.total_critic_time:.1f}s / "
                  f"model {self.total_model_time:.1f}s)")
        return StraightLineFailure(time.time() - start, self.total_model_time, [])
