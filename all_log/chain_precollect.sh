#!/bin/bash
# ★ 빈 worker 슬롯 활용 — 다음 기법 롤아웃을 미리 수집(bursty, fix@180/eval 과 동시 안전).
#   마스터(chain_all_remaining)는 이미 수집된 jsonl 은 건너뛰고 학습+평가만.
#   순서: revcurr → adaptprefix → bread → bigscale(뒤1000). workers=1(fix 와 합쳐 2스트림).
set -u
say(){ echo "[$(date '+%m-%d %H:%M')] precollect: $*" | tee -a all_log/precollect.log; }
pre(){ # $1=alias $2=out $3=extra(idx-file 등)
  [ -s "$2" ] && { say "$1 이미 있음(skip)"; return 0; }
  say "$1 롤아웃 수집 시작"
  python3 scripts/run_all.py --alias "$1" --timeout 900 --workers 1 $3 --description "precollect $1" >> all_log/precollect.log 2>&1
  say "$1 완료 ($(wc -l < $2 2>/dev/null) 그룹)"
}
say "===== 롤아웃 프리콜렉터 시작 ====="
pre grpo-rollout-revcurr     data/grpo_rollouts/revcurr.jsonl     "--start 200 --num 40"
pre grpo-rollout-adaptprefix data/grpo_rollouts/adaptprefix.jsonl "--start 200 --num 40"
pre grpo-rollout-bread       data/grpo_rollouts/bread.jsonl       "--start 200 --num 40"
pre grpo-rollout-bigscale    data/grpo_rollouts/bigscale.jsonl    "--idx-file data/compcert_bigscale_train_idx.txt"
say "===== 프리콜렉터 완료 (모든 롤아웃 수집됨) ====="
