from __future__ import annotations
import heapq
import time
from typing import Optional, Any
from dataclasses import dataclass
from data_management.dataset_file import Proof, DatasetFile
from model_deployment.proof_manager import ProofManager, TacticResult
from model_deployment.tactic_gen_client import TacticGenClient
from model_deployment.goal_comparer import AlphaGoalComparer

from coqpyt.coq.lsp.structs import Goal


@dataclass
class ClassicalSearchConf:
    max_branch: int
    max_search_steps: int
    depth_limit: int
    timeout: int
    beam_decode: bool
    initial_proof: Optional[str]
    use_memo: bool = False  # M2: transposition table + failed-tactic memo + cycle guard
    log_tree: bool = False  # MR1(RL): 탐색 트리의 (state,label) 쌍을 value model 학습용으로 덤프
    log_dir: Optional[str] = None
    value_ckpt: Optional[str] = None  # MR1: 학습된 value head 경로(있으면 frontier 블렌드)
    value_weight: float = 0.0  # score = cum_logprob + value_weight*log(V+eps)
    # MR-Hybrid: retrieval-신뢰도(모델 top log-prob) 게이팅 adaptive-width.
    #   확신↑(top≥conf_threshold) → width 1 greedy(=rango 기법), 확신↓ → width max_branch 탐색.
    hybrid_conf: bool = False
    conf_threshold: float = -0.05
    qed_ckpt: Optional[str] = None  # QEDCartographer: coq2vec value + product-over-subgoals backup
    ALIAS = "classical"

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> ClassicalSearchConf:
        return cls(
            yaml_data["max_branch"],
            yaml_data["max_search_steps"],
            yaml_data["depth_limit"],
            yaml_data["timeout"],
            yaml_data["beam_decode"],
            yaml_data.get("initial_proof", None),
            yaml_data.get("use_memo", False),
            yaml_data.get("log_tree", False),
            yaml_data.get("log_dir", None),
            yaml_data.get("value_ckpt", None),
            yaml_data.get("value_weight", 0.0),
            yaml_data.get("hybrid_conf", False),
            yaml_data.get("conf_threshold", -0.05),
            yaml_data.get("qed_ckpt", None),
        )


@dataclass
class ClassicalSuccess:
    time: float
    model_time: float
    search_steps: int
    successful_candidate: Candidate
    root_candidate: Candidate


@dataclass
class ClassicalFailure:
    time: float
    model_time: float
    search_steps: int
    root_candidate: Candidate


class Candidate:
    def __init__(
        self,
        proof: Optional[Proof],
        proof_str: str,
        tactic: str,
        score: float,
        tactic_score: float,
        depth: int,
        children: Optional[list[Candidate]],
        parent_goal_key: Optional[str] = None,
    ):
        self.proof = proof
        self.proof_str = proof_str
        self.tactic = tactic
        self.score = score
        self.tactic_score = tactic_score
        self.depth = depth
        # M2: goal-state hash of the state this candidate's tactic was applied FROM
        self.parent_goal_key = parent_goal_key
        # MR1(RL): 이 candidate의 tactic 적용 후 도달한 goal 상태(가치 라벨 대상). solved=이 노드가 COMPLETE.
        self.goal_text: Optional[str] = None
        self.solved: bool = False
        if children is None:
            self.children = []
        else:
            self.children = children

    def __lt__(self, other: Candidate) -> bool:
        return other.score <= self.score  # Reversed so higher scores are first in pq


class ClassicalSearcher:
    def __init__(
        self,
        tactic_client: TacticGenClient,
        proof_manager: ProofManager,
        max_branch: int,
        max_search_steps: int,
        depth_limit: int,
        timeout: int,
        beam_decode: bool,
        initial_proof: Optional[str] = None,
        use_memo: bool = False,
        log_tree: bool = False,
        log_dir: Optional[str] = None,
        value_ckpt: Optional[str] = None,
        value_weight: float = 0.0,
        hybrid_conf: bool = False,
        conf_threshold: float = -0.05,
        qed_ckpt: Optional[str] = None,
    ):
        self.hybrid_conf = hybrid_conf
        self.conf_threshold = conf_threshold
        self.qed_ckpt = qed_ckpt
        self._qed_model = None
        self.tactic_client = tactic_client
        self.proof_manager = proof_manager
        self.max_branch = max_branch
        self.max_search_steps = max_search_steps
        self.depth_limit = depth_limit
        self.timeout = timeout
        self.beam_decode = beam_decode
        self.initial_proof = initial_proof
        # MR1(RL)
        self.log_tree = log_tree
        self.log_dir = log_dir or "data/vguided_trees"
        self.value_ckpt = value_ckpt
        self.value_weight = value_weight
        self._value_model = None  # lazy
        # M2 (search-memory): goal-hash → {"dead", "rejected": set[str], "expanded"}
        self.use_memo = use_memo
        self.goal_memo: dict[str, dict[str, Any]] = {}
        self.memo_pruned = 0  # 진단용: memo로 건너뛴 노드 수

        initial_dset_file = proof_manager.get_initial_context()
        if initial_dset_file is None:
            raise ValueError("Could not get initial datasetfile")
        self.initial_dset_file = initial_dset_file

        if initial_proof is None:
            initial_proof = ""

        self.need_goal_record = False
        self.total_model_time = 0

        self.comparer = AlphaGoalComparer()

        self.root_candidate = Candidate(None, "", initial_proof, 0, 0, 0, None)
        self.frontier: list[Candidate] = []
        self.seen_goals: list[list[Goal]] = []
        self.seen_goals_candidates: list[Candidate] = []
        heapq.heappush(self.frontier, self.root_candidate)

    @classmethod
    def from_conf(
        cls,
        conf: ClassicalSearchConf,
        tactic_clients: list[TacticGenClient],
        proof_manager: ProofManager,
    ) -> ClassicalSearcher:
        assert len(tactic_clients) == 1
        return cls(
            tactic_clients[0],
            proof_manager,
            conf.max_branch,
            conf.max_search_steps,
            conf.depth_limit,
            conf.timeout,
            conf.beam_decode,
            conf.initial_proof,
            conf.use_memo,
            getattr(conf, "log_tree", False),
            getattr(conf, "log_dir", None),
            getattr(conf, "value_ckpt", None),
            getattr(conf, "value_weight", 0.0),
            getattr(conf, "hybrid_conf", False),
            getattr(conf, "conf_threshold", -0.05),
            getattr(conf, "qed_ckpt", None),
        )

    def search(
        self, print_proofs: bool = False, print_trees: bool = False
    ) -> ClassicalSuccess | ClassicalFailure:
        start = time.time()
        num_steps = 0
        for i in range(self.max_search_steps):
            cur = time.time()
            if self.timeout <= cur - start:
                if self.log_tree:  # MR1: timeout 실패 트리도 덤프(negative 데이터)
                    self._dump_tree()
                return ClassicalFailure(
                    cur - start, self.total_model_time, num_steps, self.root_candidate
                )
            if len(self.frontier) == 0:
                if self.log_tree:  # MR1: frontier 소진 실패 트리도 덤프
                    self._dump_tree()
                return ClassicalFailure(
                    cur - start, self.total_model_time, num_steps, self.root_candidate
                )
            num_steps += 1
            possible_success = self.search_step(num_steps, print_proofs)
            if possible_success is not None:
                if self.log_tree:
                    self._dump_tree()
                return ClassicalSuccess(
                    time.time() - start,
                    self.total_model_time,
                    num_steps,
                    possible_success,
                    self.root_candidate,
                )
        if self.log_tree:
            self._dump_tree()
        return ClassicalFailure(
            time.time() - start, self.total_model_time, num_steps, self.root_candidate
        )

    def _dump_tree(self) -> None:
        """MR1(RL): 탐색 트리를 (state, label, dist) JSONL로 덤프.
        label=1: 이 state에서 (예산 내) 증명 완료 가능(성공경로/조상). dist=QED까지 step.
        label=0: subtree 전멸(예산 내 미완). value model이 P(solvable)를 학습하도록."""
        import os, json
        records: list[dict] = []

        def visit(node: "Candidate") -> tuple[bool, int]:
            child_res = [visit(c) for c in node.children]
            solved_below = node.solved or any(r[0] for r in child_res)
            if node.solved:
                dist = 0
            elif solved_below:
                dist = 1 + min(r[1] for r in child_res if r[0])
            else:
                dist = -1
            if node.goal_text is not None:
                records.append({
                    "goal": node.goal_text,
                    "label": 1 if solved_below else 0,
                    "dist": dist,
                    "depth": node.depth,
                    "cum_score": node.score,
                    "tactic_score": node.tactic_score,
                    "tactic": node.tactic.strip()[:200],
                })
            return (solved_below, dist)

        try:
            visit(self.root_candidate)
            if not records:
                return
            os.makedirs(self.log_dir, exist_ok=True)
            thm = self.initial_dset_file.proofs[-1].theorem.term.text if self.initial_dset_file.proofs else "unknown"
            fname = f"{abs(hash(thm)) % (10**12)}.jsonl"
            with open(os.path.join(self.log_dir, fname), "w") as f:
                for r in records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n_pos = sum(r["label"] for r in records)
            print(f"[MR1] tree dump: {len(records)} states ({n_pos} pos) → {self.log_dir}/{fname}")
        except Exception as e:
            print(f"[MR1] tree dump 실패: {e}")

    # Delay checking until node is selected
    def is_only_focusing(self, tactic: str) -> bool:
        stripped_tactic = tactic.strip()
        return all([c in "*-+" for c in stripped_tactic])

    def is_only_proof(self, tactic: str) -> bool:
        # could ensure that the tactic is the first proof tactic
        return tactic.strip() == "Proof."

    def is_redundant(self, candidate: Candidate, candidate_goals: list[Goal]) -> bool:
        if self.is_only_focusing(candidate.tactic) or self.is_only_proof(
            candidate.tactic
        ):
            return False
        for seen_goals in self.seen_goals:
            if self.comparer.as_hard_as(
                candidate_goals,
                seen_goals,
                self.proof_manager.fast_client,
                self.proof_manager.file_prefix,
            ):
                return True
        return False

    def _goal_key(self, goals: list[Goal]) -> str:
        """goal 상태의 (정확) 문자열 해시 키. coqpyt Goal.__repr__는 hyps+ty를 준다."""
        return "\n===\n".join(repr(g) for g in goals)

    def _value_of(self, cand: "Candidate") -> float:
        """확장 중인 state의 value. QED모드=coq2vec value의 **product-over-subgoals**(∏V),
        아니면 MR1 supervised critic. value_weight==0이면 미사용."""
        if self.value_weight == 0.0 or cand.goal_text is None:
            return 1.0
        # QEDCartographer: per-subgoal value의 곱(AND 구조 backup)
        if self.qed_ckpt is not None:
            if self._qed_model is None:
                from model_deployment.qed_cartographer import QEDValuePredictor
                self._qed_model = QEDValuePredictor(self.qed_ckpt)
            subgoals = [g for g in cand.goal_text.split("\n===\n") if g.strip()]
            return self._qed_model.value_state(subgoals)
        if self._value_model is None:
            from model_deployment.value_head import ValuePredictor
            self._value_model = ValuePredictor(self.value_ckpt)
        return self._value_model.value(
            cand.goal_text, cand.depth, cand.score, cand.tactic_score
        )

    def _memo(self, key: str) -> dict[str, Any]:
        entry = self.goal_memo.get(key)
        if entry is None:
            entry = {"dead": False, "rejected": set(), "expanded": False}
            self.goal_memo[key] = entry
        return entry

    def search_step(self, attempt_num: int, print_proofs: bool) -> Optional[Candidate]:
        cur_candidate = heapq.heappop(self.frontier)
        print(f"\n[Search] 호출 #{attempt_num} | iterate #{attempt_num}  depth={cur_candidate.depth}  score={cur_candidate.score:.4f}  tactic={repr(cur_candidate.tactic.strip())}")
        if print_proofs:
            print(f"===== Attempt {attempt_num} ======")
            print(cur_candidate.proof_str)
            print()
        proof_check_result = self.proof_manager.check_proof(
            cur_candidate.proof_str,
            self.initial_dset_file.proofs[-1].theorem,
        )
        match proof_check_result.tactic_result:
            case TacticResult.COMPLETE:
                assert proof_check_result.new_proof is not None
                cur_candidate.proof = proof_check_result.new_proof
                cur_candidate.solved = True  # MR1: 라벨링용
                return cur_candidate
            case TacticResult.INVALID:
                # M2: 이 tactic이 parent goal 상태에서 실패했음을 기록
                if self.use_memo and cur_candidate.parent_goal_key is not None:
                    self._memo(cur_candidate.parent_goal_key)["rejected"].add(
                        cur_candidate.tactic.strip()
                    )
                return None
            case TacticResult.VALID:
                assert proof_check_result.new_proof is not None
                assert proof_check_result.current_goals is not None
                cur_candidate.proof = proof_check_result.new_proof
                cur_dset_file = self.proof_manager.build_dset_file(cur_candidate.proof)
                cur_goals = proof_check_result.current_goals

                # MR1(RL): 이 노드가 도달한 goal 상태 저장(라벨/특징용)
                if self.log_tree or self.value_weight != 0.0:
                    cur_candidate.goal_text = self._goal_key(cur_goals)

                if self.use_memo:
                    goal_key = self._goal_key(cur_goals)
                    # cycle guard: tactic 적용 후 goal 상태가 그대로면(무진전) 버림
                    if (
                        cur_candidate.parent_goal_key is not None
                        and goal_key == cur_candidate.parent_goal_key
                    ):
                        self.memo_pruned += 1
                        return None
                    entry = self._memo(goal_key)
                    # transposition dedup: 이미 확장했거나 dead인 상태면 건너뜀 (해시 O(1))
                    if entry["dead"] or entry["expanded"]:
                        self.memo_pruned += 1
                        return None
                    entry["expanded"] = True
                else:
                    goal_key = None
                    if self.is_redundant(cur_candidate, cur_goals):
                        return None
                    self.seen_goals.append(cur_goals)
                    self.seen_goals_candidates.append(cur_candidate)

                if self.depth_limit <= cur_candidate.depth:
                    return None
                start_time = time.time()
                recs = self.tactic_client.get_recs(
                    len(cur_candidate.proof.steps) - 1,
                    cur_candidate.proof,
                    cur_dset_file,
                    self.max_branch,
                    beam=self.beam_decode,
                    file_prefix=self.proof_manager.file_prefix,
                )
                end_time = time.time()
                self.total_model_time += end_time - start_time
                rejected = self.goal_memo[goal_key]["rejected"] if self.use_memo else set()
                # MR1: 확장 중인 state의 value를 자식 우선순위에 블렌드(가지 간 판별).
                #   score = cum_score + tactic_score + value_weight*log(V(parent_state)+eps)
                value_bonus = 0.0
                if self.value_weight != 0.0:
                    import math as _m
                    value_bonus = self.value_weight * _m.log(self._value_of(cur_candidate) + 1e-6)

                # MR-Hybrid: 모델 확신도로 width 게이팅. 확신 높으면 top-1만(greedy=rango 기법),
                #   낮으면 전체(max_branch) 탐색. retrieval이 잘 매치될수록 top log-prob이 뾰족.
                rec_triples = list(zip(recs.next_tactic_list, recs.score_list, recs.num_tokens_list))
                if self.hybrid_conf and rec_triples:
                    top_score = max(t[1] for t in rec_triples)
                    if top_score >= self.conf_threshold:
                        # 확신↑ → argmax 하나만 유지(greedy commit)
                        rec_triples = [max(rec_triples, key=lambda t: t[1])]
                        print(f"[Hybrid] 확신↑(top={top_score:.3f}≥{self.conf_threshold}) → greedy width1")
                for tactic, tactic_score, num_tokens in rec_triples:
                    # M2: 이 goal 상태에서 이미 실패한 tactic은 Coq 치기 전에 제외
                    if self.use_memo and tactic.strip() in rejected:
                        self.memo_pruned += 1
                        continue
                    admitted_step = cur_candidate.proof.steps[-1]
                    proof_str = (
                        cur_candidate.proof.proof_prefix_to_string(
                            admitted_step, include_theorem=False
                        )
                        + tactic
                    )
                    score = cur_candidate.score + tactic_score + value_bonus
                    depth = cur_candidate.depth + 1
                    new_candidate = Candidate(
                        None, proof_str, tactic, score, tactic_score, depth, None,
                        parent_goal_key=goal_key,
                    )
                    cur_candidate.children.append(new_candidate)
                    heapq.heappush(self.frontier, new_candidate)
