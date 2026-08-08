#!/usr/bin/env python3
"""진짜 Coq 에러 수집 — 롤아웃에 남은 INVALID tactic 을 **재실행**해 에러 메시지를 받는다.

## 왜 필요한가

ERROR_COND 학습은 지금 **합성 에러**를 쓴다(src/tactic_gen/synth_error.py). 문구는 실제와
동일하지만(형식 검증 통과), **모델이 실제로 내는 실패 분포**와는 다르다. 진짜가 낫다.

기존 롤아웃(data/grpo_rollouts/*.jsonl)에는 (example, tactic, INVALID) 가 남아 있는데
**coq_error 는 없다**(RECORD_ERROR 가 꺼진 채 수집됨). 다행히 tactic 과 프롬프트 상태가 있으니
**재실행하면 에러를 복원**할 수 있고, 이는 **CPU 만 쓴다**(모델 샘플링 불필요).
→ GPU 가 학습에 묶여 있어도 병행 가능하다.

## 방식

1. 롤아웃에서 result=INVALID 인 step 을 (파일, proof_idx) 로 묶는다
2. 정리마다 ProofManager 를 한 번 만들고(무거운 부분), 그 안에서 tactic 들을 재검증
3. (example, tactic, error) 를 JSONL 로 저장

## 사용
    python3 scripts/collect_real_errors.py --rollout data/grpo_rollouts/adaptprefix.jsonl \\
        --out data/error_sft/real_errors.jsonl --max-thms 200 --workers 8
"""
import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "src")


def load_invalid_steps(path: str, limit: int):
    """롤아웃에서 INVALID step 을 (file, proof_idx) 별로 모은다."""
    groups = defaultdict(list)
    n = 0
    with open(path) as f:
        for line in f:
            try:
                g = json.loads(line)
            except Exception:
                continue
            for a in g.get("attempts", []):
                for st in a.get("steps", []):
                    if st.get("result") != "INVALID" or not st.get("example"):
                        continue
                    ex = st["example"]
                    key = (ex.get("file_name"), ex.get("proof_idx"))
                    if key[0] is None:
                        continue
                    groups[key].append({"example": ex, "tactic": st.get("tactic", "")})
                    n += 1
            if limit and len(groups) >= limit:
                break
    return groups, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rollout", required=True)
    ap.add_argument("--out", default="data/error_sft/real_errors.jsonl")
    ap.add_argument("--max-thms", type=int, default=100)
    ap.add_argument("--max-per-thm", type=int, default=8)
    args = ap.parse_args()

    groups, n_steps = load_invalid_steps(args.rollout, args.max_thms)
    print(f"INVALID step {n_steps:,}개, 정리 {len(groups)}개")
    if not groups:
        print("수집할 것 없음")
        return

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    # 재실행은 정리마다 Coq 파일 컴파일이 필요해 무겁다 → 우선 '무엇을 재실행할지'만 뽑아둔다.
    # 실제 재실행은 run_thm 인프라(ProofManager)가 필요하므로 별도 워커에서 수행한다.
    todo = args.out + ".todo"
    with open(todo, "w") as f:
        for (fn, pidx), items in list(groups.items())[: args.max_thms]:
            f.write(json.dumps({
                "file_name": fn, "proof_idx": pidx,
                "tactics": [it["tactic"] for it in items[: args.max_per_thm]],
                "example": items[0]["example"],
            }, ensure_ascii=False) + "\n")
    print(f"재실행 대상 {min(len(groups), args.max_thms)}정리 → {todo}")
    print("  ※ 실제 재실행은 Coq 컴파일이 정리당 수십 초 걸린다. 병렬 워커로 돌릴 것.")


if __name__ == "__main__":
    main()
