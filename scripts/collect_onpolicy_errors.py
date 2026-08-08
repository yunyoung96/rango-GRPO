#!/usr/bin/env python3
"""on-policy 에러 수집 — gold prefix 에서 **실제로 1-step 예측 → Coq 실행 → 에러 수집**.

## 왜 (합성 에러의 문제)

지금 ERROR_COND 학습은 합성 에러를 쓴다. 그 코드는 gold 정답에서 분기 수를 세어
`Expects a disjunctive pattern with N branches` 를 **직접 써넣는다** — Coq 을 호출하지 않는다.
문제:
  · 시도(`[ATTEMPT]`)가 가짜다. 모델이 실제로 낸 적 없는 tactic 이다.
  · 에러가 gold 에서 역산됐다 = **정답이 프롬프트에 새어든다**.
  · 실패의 3%(분기수)만 다룬다. 나머지(이름없음 45%, 문법 5.8%, inductive아님 4%)는 못 만든다.

## 이 스크립트가 하는 일

    gold 증명의 앞 k 스텝을 **실제로 적용**해 상태를 만든다   (prefix 재생)
      ↓
    그 상태에서 모델에게 **1-step 예측**을 시킨다 (n회 샘플)  ← 진짜 on-policy
      ↓
    각 후보를 **Coq 으로 실행**한다                            ← 진짜 검증
      ↓
    INVALID 면 coq-lsp 가 준 **진짜 에러 메시지**를 받는다
      ↓
    (state, 실패한 tactic, 그 에러) → gold[k]  를 SFT 레코드로 저장

학습 시 프롬프트는 [ATTEMPT]/[ERROR] 로 들어가고 타깃은 gold 다. 즉
  "이 상태에서 이걸 시도했다가 이 에러를 받았다 → 그럼 다음엔 이걸 해라"
를 **실제 실패로부터** 배운다.

## 사용 (모델 서버가 떠 있어야 함 — run_all/run_thm 과 동일 인프라)
    python3 scripts/collect_onpolicy_errors.py --num 300 --n-samples 2 \\
        --out data/error_sft/onpolicy.jsonl
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, "src")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--num", type=int, default=200, help="정리 수(train split)")
    ap.add_argument("--start", type=int, default=200, help="eval 셋과 분리 오프셋")
    ap.add_argument("--n-samples", type=int, default=2, help="상태당 예측 횟수")
    ap.add_argument("--max-steps", type=int, default=12, help="정리당 최대 gold 스텝")
    ap.add_argument("--out", default="data/error_sft/onpolicy.jsonl")
    ap.add_argument("--checkpoint", default=None, help="EXEC_ADAPTER 대신 쓸 체크포인트")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    # grpo_rollout 의 인프라를 그대로 재사용한다(서버 기동·ProofManager 구성 포함).
    #   ★ 새로 짜지 않는 이유: 파일 컴파일·전제 검색·프롬프트 포맷이 전부 그쪽에 맞춰져 있어
    #     따로 만들면 학습/추론과 프롬프트가 어긋날 위험이 크다(R1 포맷 불일치).
    from tactic_gen import grpo_rollout as gr

    print(f"[수집] 정리 {args.num}개, 상태당 {args.n_samples}회 예측, 최대 {args.max_steps} 스텝")
    print(f"       출력: {args.out}")
    print("       ※ ERROR 는 coq-lsp 가 실제로 낸 메시지만 기록한다(합성 아님).")

    # RECORD_ERROR=1 이면 rollout 이 INVALID step 에 coq_error 를 붙여 저장한다.
    os.environ["RECORD_ERROR"] = "1"
    os.environ.setdefault("GOLD_PREFIX", "1")

    argv = ["grpo_rollout",
            "--num", str(args.num), "--start", str(args.start),
            "--group_size", str(args.n_samples),
            "--max_steps", str(args.max_steps),
            "--out", args.out]
    if args.checkpoint:
        os.environ["EXEC_ADAPTER"] = args.checkpoint
    sys.argv = argv
    t0 = time.time()
    gr.main()
    print(f"[수집] 완료 {time.time()-t0:.0f}s → {args.out}")


if __name__ == "__main__":
    main()
