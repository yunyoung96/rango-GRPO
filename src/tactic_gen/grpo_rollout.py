#!/usr/bin/env python3
"""GRPO rollout 수집기 — 정책 π_old로 정리마다 G개 증명 시도 생성 + Coq 검증 → 그룹 jsonl.

각 시도(attempt): 현재 상태에서 next-tactic 1개 샘플(temperature) → check_proof 적용,
COMPLETE(보상1)/INVALID·max_steps(보상0)까지 반복. step마다 (LmExample, tactic) 기록
(서버가 하던 collation을 학습 때 동일 재현하려 example_json 저장).

출력 jsonl(줄=그룹):
  {"theorem": <idx>, "attempts": [{"steps":[{"example":<json>,"tactic":str}], "reward":0/1}, ...]}

rollout은 서버(retrieval)+Coq이 필요 → 평가/실행 단계에서 구동. grpo_train.py가 소비.
★OCaml 무관.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from model_deployment.proof_manager import ProofManager, TacticResult
from model_deployment.tactic_gen_client import TacticGenClient
from model_deployment.straight_line_searcher import (
    StraightLineSuccess,
    StraightLineFailure,
)


def rollout_attempt(
    tactic_client: TacticGenClient,
    proof_manager: ProofManager,
    theorem: Any,
    initial_proof: str,
    max_steps: int,
    temperature_seed: Optional[int] = None,
    value_fn=None,           # (E2 dense reward) goals:list[str]->float ∈(0,1). None=binary.
    shaping_coef: float = 0.3,
) -> dict:
    """한 증명 시도. 반환 {"steps":[{example,tactic}], "reward":float}.
    binary: COMPLETE=1 else 0. dense(value_fn): 미완이면 마지막 valid 상태의 QED value×coef."""
    if temperature_seed is not None and hasattr(tactic_client, "set_seed"):
        tactic_client.set_seed(temperature_seed)
    steps: list[dict] = []
    check = proof_manager.check_proof(initial_proof, theorem)
    if check.tactic_result != TacticResult.VALID or check.new_proof is None:
        return {"steps": [], "reward": 0.0}
    script = initial_proof
    reward = 0.0
    last_valid_goals = _goals_str(check)  # dense reward용 마지막 valid 상태 goal들
    for _ in range(max_steps):
        new_proof = check.new_proof
        if new_proof is None:
            break
        dset = proof_manager.build_dset_file(new_proof)
        proof = dset.proofs[-1]
        # 서버가 만들 example 재현: 현재 step 기준 formatter example.
        fmt = tactic_client.formatters[0]
        example = fmt.example_from_step(len(proof.steps) - 1, proof.proof_idx, dset)
        prefix = proof.proof_prefix_to_string(proof.steps[-1], include_theorem=False)
        recs = tactic_client.get_recs(
            len(proof.steps) - 1, proof, dset, 1,
            beam=False, file_prefix=proof_manager.file_prefix,
        )
        if not recs.next_tactic_list:
            break
        tactic = recs.next_tactic_list[0]
        steps.append({"example": example.to_json(), "tactic": tactic})
        check = proof_manager.check_proof(prefix + tactic, new_proof.theorem)
        if check.tactic_result == TacticResult.VALID:
            last_valid_goals = _goals_str(check)
        if check.tactic_result == TacticResult.COMPLETE:
            reward = 1.0
            break
        if check.tactic_result == TacticResult.INVALID:
            break
        script = prefix + tactic
    # dense reward: 미완(reward=0)이고 value_fn 있으면 마지막 valid 상태의 QED value로 부분보상.
    if reward == 0.0 and value_fn is not None and steps:
        try:
            reward = float(shaping_coef) * float(value_fn(last_valid_goals))
        except Exception:
            reward = 0.0
    return {"steps": steps, "reward": reward}


def _goals_str(check) -> list[str]:
    """ProofCheckResult.current_goals → goal 문자열 리스트(QED value 입력)."""
    gs = getattr(check, "current_goals", None)
    if not gs:
        return []
    out = []
    for g in gs:
        try:
            out.append(repr(g))
        except Exception:
            pass
    return out


def collect_group(
    tactic_client: TacticGenClient,
    proof_manager: ProofManager,
    theorem: Any,
    theorem_id: int,
    group_size: int,
    max_steps: int,
    initial_proof: str = "",
    value_fn=None,
    shaping_coef: float = 0.3,
) -> dict:
    """정리 하나에 대해 G개 시도 → 그룹."""
    attempts = []
    for g in range(group_size):
        att = rollout_attempt(
            tactic_client, proof_manager, theorem, initial_proof, max_steps,
            temperature_seed=g + 1, value_fn=value_fn, shaping_coef=shaping_coef,
        )
        attempts.append(att)
    n_solved = sum(1 for a in attempts if a["reward"] >= 1.0)
    print(f"  [rollout] thm {theorem_id}: 완결 {n_solved}/{group_size}, "
          f"보상 {[round(a['reward'],2) for a in attempts]}")
    return {"theorem": theorem_id, "attempts": attempts}


def append_group(out_path: Path, group: dict) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a") as f:
        f.write(json.dumps(group, ensure_ascii=False) + "\n")


@dataclass
class GRPORolloutSearchConf:
    """run_thm 인프라 재사용을 위한 '탐색기' 형태의 rollout 수집기 설정.
    .search()가 정리에 G개 시도를 생성·검증해 그룹 jsonl에 append."""
    timeout: int
    group_size: int = 8
    max_steps: int = 20
    out: str = "data/grpo_rollouts/rollouts.jsonl"
    initial_proof: Optional[str] = None
    print_proofs: bool = True
    qed_ckpt: Optional[str] = None      # (E2) dense reward용 QED value 체크포인트. None=binary.
    shaping_coef: float = 0.3
    ALIAS = "grpo_rollout"

    @classmethod
    def from_yaml(cls, yaml_data: Any) -> "GRPORolloutSearchConf":
        return cls(
            yaml_data["timeout"],
            yaml_data.get("group_size", 8),
            yaml_data.get("max_steps", 20),
            yaml_data.get("out", "data/grpo_rollouts/rollouts.jsonl"),
            yaml_data.get("initial_proof", None),
            yaml_data.get("print_proofs", True),
            yaml_data.get("qed_ckpt", None),
            yaml_data.get("shaping_coef", 0.3),
        )


class GRPORolloutSearcher:
    def __init__(self, tactic_clients, proof_manager, conf: GRPORolloutSearchConf):
        self.tactic_clients = tactic_clients
        self.proof_manager = proof_manager
        self.conf = conf
        self.total_model_time = 0.0
        init_dset = proof_manager.get_initial_context()
        if init_dset is None:
            raise ValueError("Could not get initial datasetfile")
        self.theorem = init_dset.proofs[-1].theorem
        # (E2) dense reward: QED value 모델 로드 → value_fn(goals)->float
        self.value_fn = None
        if getattr(conf, "qed_ckpt", None):
            from model_deployment.qed_cartographer import QEDValuePredictor
            vp = QEDValuePredictor(conf.qed_ckpt)
            self.value_fn = lambda goals: vp.value_state(goals) if goals else 0.0

    @classmethod
    def from_conf(cls, conf, tactic_clients, proof_manager):
        return cls(tactic_clients, proof_manager, conf)

    def search(self, **kwargs):
        import time
        start = time.time()
        thm_text = self.theorem.term.text if hasattr(self.theorem, "term") else str(self.theorem)
        thm_id = abs(hash(thm_text)) % (10 ** 12)
        group = collect_group(
            self.tactic_clients[0], self.proof_manager, self.theorem, thm_id,
            self.conf.group_size, self.conf.max_steps, self.conf.initial_proof or "",
            value_fn=self.value_fn, shaping_coef=getattr(self.conf, "shaping_coef", 0.3),
        )
        append_group(Path(self.conf.out), group)
        n_solved = sum(1 for a in group["attempts"] if a["reward"] >= 1.0)
        elapsed = time.time() - start
        # rollout은 데이터 수집이 목적 → 항상 Failure 반환(run_all 성공집계 무의미).
        print(f"[GRPO-ROLLOUT] thm={thm_id} 완결 {n_solved}/{self.conf.group_size} "
              f"→ {self.conf.out} ({elapsed:.1f}s)")
        return StraightLineFailure(elapsed, self.total_model_time, [])


def main():
    ap = argparse.ArgumentParser(description="GRPO rollout 수집(run_thm 인프라 필요)")
    ap.add_argument("--group_size", type=int, default=8)
    ap.add_argument("--max_steps", type=int, default=20)
    ap.add_argument("--out", default="data/grpo_rollouts/rollouts.jsonl")
    ap.add_argument("--num", type=int, default=40, help="정리 수(train split)")
    ap.add_argument("--start", type=int, default=200, help="eval셋과 분리 오프셋")
    args = ap.parse_args()
    # 실제 구동은 run_thm의 서버/proof_manager 셋업을 재사용하는 드라이버에서 호출.
    # (여기서는 단독 실행 대신 collect_group을 라이브러리로 호출하는 것을 권장.)
    print("grpo_rollout: collect_group()을 run_thm 셋업과 함께 호출하세요.")
    print(f"  설정: group={args.group_size} max_steps={args.max_steps} out={args.out}")


if __name__ == "__main__":
    main()
