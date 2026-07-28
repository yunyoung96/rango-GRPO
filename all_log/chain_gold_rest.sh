#!/bin/bash
# on-policy 축(vine·fixdyn) 완료 후 나머지: revcurr → adaptprefix → bread → fix@180 → backward-prm → retry-prm.
# 사용자가 vine/fixdyn 결과 보고 이 gold 계열을 취소하려면 이 스크립트 PID 만 kill 하면 됨.
set -u
WAIT_PID=${WAIT_PID:?}
LOG=all_log/chain_gold_rest.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT_FIX=models/rango-grpo-fix/adapter
INIT_ORIG=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }
roll(){ [ -s "$2" ] && return 0; rm -f "$2"; python3 scripts/run_all.py --alias "$1" --start 200 --num 40 --timeout "$3" --workers 2 --description "$1" >> "$LOG" 2>&1; [ -s "$2" ]; }
trainf(){ python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$INIT_FIX" --collator_conf "$CONF" --max_len 3072 --save_dir "$2" --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 "${@:3}" >> "$LOG" 2>&1; cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$(dirname "$2")/" 2>/dev/null; }

say "대기: on-policy 축(${WAIT_PID}) 완료까지"
while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 120; done
say "on-policy 축 종료 확인 → gold 계열 시작"

say "▶ KL-LUFFY (회귀 처방, luffy.jsonl 재사용 — 빠름)"; bash all_log/run_luffy_kl.sh

say "▶ revcurr"; bash all_log/run_revcurr.sh

say "▶ adaptprefix"
if roll grpo-rollout-adaptprefix data/grpo_rollouts/adaptprefix.jsonl 900; then
  [ ! -f models/rango-grpo-adaptprefix/adapter/adapter_model.safetensors ] && trainf data/grpo_rollouts/adaptprefix.jsonl models/rango-grpo-adaptprefix/adapter
  seval rango-grpo-adaptprefix
fi

say "▶ bread"
if roll grpo-rollout-bread data/grpo_rollouts/bread.jsonl 900; then
  [ ! -f models/rango-grpo-bread/adapter/adapter_model.safetensors ] && trainf data/grpo_rollouts/bread.jsonl models/rango-grpo-bread/adapter --luffy
  seval rango-grpo-bread
fi

say "▶ fix@180"; python3 scripts/smart_eval.py --alias rango-grpo-fix --stages 180 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"
say "▶ backward-prm"; [ -f models/rango-grpo-backward-prm/adapter/adapter_model.safetensors ] && seval rango-grpo-backward-prm
say "▶ retry-prm"
if [ ! -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && [ -s data/grpo_rollouts/retry.jsonl ]; then
  python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/retry.jsonl --model_name "$BASE" --init_adapter "$INIT_ORIG" --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-grpo-retry-prm/adapter --process --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-retry-prm/ 2>/dev/null
fi
[ -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && seval rango-grpo-retry-prm

say "===== gold 계열 전체 완료 ====="
