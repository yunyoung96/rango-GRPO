#!/bin/bash
# fixdyn 재실행 — dynamic sampling 시드 no-op 버그 수정(collect_group seed_base) 후 clean 재수집·재학습·평가.
# 현재 master 큐(chain_all_remaining.sh)가 끝난 뒤 자동 시작되도록 launcher 가 대기시킴.
set -u
LOG=all_log/run_fixdyn_refix.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT_FIX=models/rango-grpo-fix/adapter
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "▶ fixdyn(fixed) 롤아웃 수집 — dynamic sampling 재샘플 시드 실제 변동"
if [ ! -s data/grpo_rollouts/fixdyn.jsonl ]; then
  python3 scripts/run_all.py --alias grpo-rollout-fixdyn --num 40 --timeout 900 --workers 1 \
    --description "fixdyn refix rollout" >> "$LOG" 2>&1
fi
[ -s data/grpo_rollouts/fixdyn.jsonl ] || { say "✗ 롤아웃 수집 실패 — 중단"; exit 1; }

say "▶ fixdyn(fixed) 학습 — on fix"
if [ ! -f models/rango-grpo-fixdyn/adapter/adapter_model.safetensors ]; then
  python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/fixdyn.jsonl \
    --model_name "$BASE" --init_adapter "$INIT_FIX" --collator_conf "$CONF" \
    --max_len 3072 --save_dir models/rango-grpo-fixdyn/adapter \
    --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-fixdyn/ 2>/dev/null
fi
[ -f models/rango-grpo-fixdyn/adapter/adapter_model.safetensors ] || { say "✗ 학습 실패 — 중단"; exit 1; }

say "▶ fixdyn(fixed) 평가 @20,40"
python3 scripts/smart_eval.py --alias rango-grpo-fixdyn --stages 20,40 --workers 1 2>&1 \
  | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"
say "===== fixdyn(fixed) 완료 ====="
