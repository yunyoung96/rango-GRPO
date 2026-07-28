"""PGTS(arXiv:2604.24354) 스타일 tactic-pattern 재랭킹 + 기호적 가지치기.

논문 핵심(Coq 네이티브, CoqGym 13,137정리, +8.05% 상대):
  · 인간 증명에서 **tactic 전이 패턴**(연속 tactic의 n-gram)을 오프라인 채굴.
  · 정책 LLM의 후보 tactic들을 **패턴 적합도로 재랭킹**. 모델 재학습 없음(plug-and-play).
  · 진단: "정책이 확신을 갖고 틀린다 → best-first가 그 확신을 따라 예산을 태운다."

우리 구현(정직한 차이):
  · 베이스 탐색 = **length-normalized best-first(BFS-Prover α)**. 우리 세팅 최강(bfs-a1 16/40)이라
    PGTS를 그 위의 순수 ablation으로 얹는다. 논문은 DFS 계열(ASTactic/Tac/Tok/Passport) 위에 얹었다.
  · 패턴 단위 = tactic **head**(첫 식별자: intros/apply/induction/…). 논문의 transition pattern을
    Coq tactic head bigram으로 축약(전체 tactic 문자열은 인자 때문에 희소해 n-gram이 성립 안 함).
  · 재랭킹 = score += beta * log P_pattern(head | prev_head)  (add-k 스무딩 + unigram 백오프).
    beta=0 이면 정확히 bfs-a1과 동일 → **beta가 유일한 변인**.

추가로 얹은 두 가지 기호적 가지치기(Copra 2310.04353; Rango 논문이 둘 다 없음이 확인됨):
  · **failure dictionary**: (goal_key → 그 상태에서 **INVALID 난** tactic 집합). 같은 상태에 다시 오면 재시도 안 함.
    Rango는 invalid tactic이 나오면 롤아웃을 버리고 처음부터 다시 해서 **같은 나쁜 tactic을 또 뽑는다**(논문 확인).
    ⚠️ "시도한 tactic 전부"로 넓히면 안 된다: `Proof.` 같은 goal-불변 tactic 때문에 부모와 자식이
    같은 goal_key 를 공유하므로, 루트에서 시도한 tactic 이 그 자식에서 통째로 금지되어 **정답까지 막힌다**
    (실측: idx6 이 성공→실패로 회귀). 금지는 반드시 **실패한 것만**.
  · ⚠️ **중복 샘플을 dedup 하지 말 것**(시도했다가 되돌림): expand_width>1 이 같은 tactic 을 중복으로
    뽑으면 낭비처럼 보이지만, 동일 노드가 frontier 에 2개 들어가 **두 번 확장되고 매번 새로 샘플링**된다
    (beam=False = temperature 샘플링). 즉 중복 = 그 상태에서의 **추가 샘플링 기회**다. 제거하면 유효
    탐색 폭이 줄어 성능이 떨어진다(실측: idx6 이 dedup 켠 실행에서 연속 실패).
  · **no-progress filter**: tactic 적용 후 goal 상태가 부모와 동일하면 버림(무진전 사이클 차단).
    단 depth 0(=`Proof.` 같은 초기 bookkeeping)은 면제 — 아니면 시작부터 막힌다.
"""
from __future__ import annotations

import heapq
import json
import math
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from model_deployment.proof_manager import ProofManager, TacticResult
from model_deployment.tactic_gen_client import TacticGenClient
from model_deployment.straight_line_searcher import (
    StraightLineSuccess,
    StraightLineFailure,
)
from coqpyt.coq.lsp.structs import Goal


# tactic 문자열 → head 식별자. "intros H x." → "intros", "apply foo." → "apply".
# bullet(-,+,*,{,}) 과 Proof./Qed. 같은 bookkeeping 은 그 자체를 head 로 둔다.
_HEAD_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_']*)")


def tactic_head(tactic: str) -> str:
    t = tactic.strip()
    if not t:
        return "<empty>"
    m = _HEAD_RE.match(t)
    if m:
        return m.group(1)
    return t[0]  # bullet/브레이스 등 기호 한 글자


BOS = "<bos>"  # 증명의 첫 tactic 앞 컨텍스트


@dataclass
class PatternDB:
    """tactic head bigram 통계. mine_tactic_patterns.py 가 만든 json 을 읽는다."""

    bigram: dict[str, dict[str, int]]
    unigram: dict[str, int]
    total: int
    smooth_k: float = 5.0

    @classmethod
    def load(cls, path: str | Path, smooth_k: float = 5.0) -> "PatternDB":
        with open(path) as f:
            d = json.load(f)
        return cls(d["bigram"], d["unigram"], d["total"], smooth_k)

    def log_prob(self, prev_head: str, head: str) -> float:
        """log P(head | prev_head), add-k 스무딩 + unigram 백오프.

        미등록 head(모델이 만든 낯선 tactic)도 unigram 백오프로 0 확률이 안 되게 한다.
        """
        uni = (self.unigram.get(head, 0) + 1) / (self.total + len(self.unigram) + 1)
        row = self.bigram.get(prev_head)
        if not row:
            return math.log(uni)
        row_total = sum(row.values())
        k = self.smooth_k
        p = (row.get(head, 0) + k * uni) / (row_total + k)
        return math.log(max(p, 1e-12))


@dataclass
class PGTSSearchConf:
    timeout: int
    alpha: float = 1.0  # length normalization (bfs-a1 = 1.0, 우리 최고 설정)
    beta: float = 0.5  # 패턴 재랭킹 가중치. 0 이면 bfs-a1 과 동일
    expand_width: int = 2
    max_depth: int = 50
    pattern_db: Optional[str] = None  # None 이면 패턴 재랭킹 끔(β 무시)
    use_failure_dict: bool = True
    use_no_progress_filter: bool = True
    print_proofs: bool = True
    initial_proof: Optional[str] = None
    ALIAS = "pgts"

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> "PGTSSearchConf":
        return cls(
            yaml_data["timeout"],
            yaml_data.get("alpha", 1.0),
            yaml_data.get("beta", 0.5),
            yaml_data.get("expand_width", 2),
            yaml_data.get("max_depth", 50),
            yaml_data.get("pattern_db", None),
            yaml_data.get("use_failure_dict", True),
            yaml_data.get("use_no_progress_filter", True),
            yaml_data.get("print_proofs", True),
            yaml_data.get("initial_proof", None),
        )


@dataclass(order=True)
class _QNode:
    neg_score: float
    seq: int = field(compare=True)
    check_result: Any = field(compare=False)
    cum_score: float = field(compare=False)  # Σ (log p + β·log P_pattern)
    depth: int = field(compare=False)
    prev_head: str = field(compare=False, default=BOS)
    goal_key: str = field(compare=False, default="")


class PGTSSearcher:
    def __init__(
        self,
        tactic_clients: list[TacticGenClient],
        proof_manager: ProofManager,
        timeout: int,
        alpha: float = 1.0,
        beta: float = 0.5,
        expand_width: int = 2,
        max_depth: int = 50,
        pattern_db: Optional[str] = None,
        use_failure_dict: bool = True,
        use_no_progress_filter: bool = True,
        print_proofs: bool = True,
        initial_proof: Optional[str] = None,
    ):
        self.tactic_clients = tactic_clients
        self.proof_manager = proof_manager
        self.timeout = timeout
        self.alpha = alpha
        self.beta = beta
        self.expand_width = expand_width
        self.max_depth = max_depth
        self.use_failure_dict = use_failure_dict
        self.use_no_progress_filter = use_no_progress_filter
        self.print_proofs = print_proofs
        self.total_model_time = 0.0

        self.patterns: Optional[PatternDB] = None
        if pattern_db and beta != 0.0:
            self.patterns = PatternDB.load(pattern_db)

        # 기호적 가지치기 상태
        self.failed: dict[str, set[str]] = {}  # goal_key -> 그 상태에서 INVALID 난 tactic 들
        self.n_pruned_failure = 0
        self.n_pruned_noprogress = 0

        init_dset = proof_manager.get_initial_context()
        if init_dset is None:
            raise ValueError("Could not get initial datasetfile")
        self.theorem = init_dset.proofs[-1].theorem
        init = proof_manager.check_proof(initial_proof or "", self.theorem)
        assert init.tactic_result == TacticResult.VALID
        self.init_check = init

    @classmethod
    def from_conf(cls, conf: PGTSSearchConf, tactic_clients, proof_manager):
        return cls(
            tactic_clients,
            proof_manager,
            conf.timeout,
            conf.alpha,
            conf.beta,
            conf.expand_width,
            conf.max_depth,
            conf.pattern_db,
            conf.use_failure_dict,
            conf.use_no_progress_filter,
            conf.print_proofs,
            conf.initial_proof,
        )

    def _goal_key(self, goals: Optional[list[Goal]]) -> str:
        if not goals:
            return ""
        return "\n===\n".join(repr(g) for g in goals)

    def _score(self, cum_score: float, depth: int) -> float:
        return cum_score / (max(1, depth) ** self.alpha)

    def _pattern_bonus(self, prev_head: str, tactic: str) -> float:
        if self.patterns is None:
            return 0.0
        return self.beta * self.patterns.log_prob(prev_head, tactic_head(tactic))

    def search(self, **kwargs) -> StraightLineSuccess | StraightLineFailure:
        start = time.time()
        frontier: list[_QNode] = []
        seq = 0
        root_key = self._goal_key(self.init_check.current_goals)
        heapq.heappush(
            frontier, _QNode(-0.0, seq, self.init_check, 0.0, 0, BOS, root_key)
        )
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
            script = proof.proof_prefix_to_string(
                proof.steps[-1], include_theorem=False
            )

            t0 = time.time()
            recs = client.get_recs(
                len(proof.steps) - 1,
                proof,
                dset,
                self.expand_width,
                beam=False,
                file_prefix=self.proof_manager.file_prefix,
            )
            self.total_model_time += time.time() - t0

            banned = self.failed.get(node.goal_key, set())
            for tactic, tac_logprob in zip(recs.next_tactic_list, recs.score_list):
                # ── failure dictionary: 이 상태에서 이미 INVALID 였던 tactic 은 Coq 호출조차 안 한다
                if self.use_failure_dict and tactic in banned:
                    self.n_pruned_failure += 1
                    continue

                res = self.proof_manager.check_proof(
                    script + tactic, new_proof.theorem
                )
                if self.print_proofs:
                    print(
                        f"  [PGTS d={node.depth+1}] {tactic.strip()!r} → {res.tactic_result.name}"
                    )

                if res.tactic_result == TacticResult.COMPLETE:
                    if self.print_proofs:
                        print(
                            f"[PGTS] 성공 (pruned: failure={self.n_pruned_failure} "
                            f"noprogress={self.n_pruned_noprogress})"
                        )
                    return StraightLineSuccess(
                        time.time() - start, self.total_model_time, res.new_proof, []
                    )

                if res.tactic_result == TacticResult.INVALID:
                    if self.use_failure_dict:
                        self.failed.setdefault(node.goal_key, set()).add(tactic)
                    continue

                # VALID
                child_key = self._goal_key(res.current_goals)
                # ── no-progress filter: goal 이 그대로면 무진전. depth 0 은 면제(`Proof.` 등).
                if (
                    self.use_no_progress_filter
                    and node.depth > 0
                    and child_key == node.goal_key
                ):
                    self.n_pruned_noprogress += 1
                    continue

                cum = node.cum_score + tac_logprob + self._pattern_bonus(
                    node.prev_head, tactic
                )
                depth = node.depth + 1
                seq += 1
                heapq.heappush(
                    frontier,
                    _QNode(
                        -self._score(cum, depth),
                        seq,
                        res,
                        cum,
                        depth,
                        tactic_head(tactic),
                        child_key,
                    ),
                )

        if self.print_proofs:
            print(
                f"[PGTS] 실패 (pruned: failure={self.n_pruned_failure} "
                f"noprogress={self.n_pruned_noprogress})"
            )
        return StraightLineFailure(time.time() - start, self.total_model_time, [])
