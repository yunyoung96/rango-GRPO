#!/bin/bash
# worker=1 재구성(사용자 요청) — chain_B 남은 단계 전부 --workers 1 로.
#   KL-LUFFY eval → adaptprefix → bread → backward-prm → retry-prm → fixdyn(refix)
#   → deepres 개선(anneal/luffy-ch/dapo) → bigscale(맨 마지막).
#   평가는 smart_eval 캐시 resume(끊긴 luffy-kl @20 이어서). 학습 완료 adapter 는 스킵.
set -u
LOG=all_log/chain_C.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT_FIX=models/rango-grpo-fix/adapter
INIT_ORIG=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 --workers 1 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"; }
roll(){ [ -s "$2" ] && return 0; rm -f "$2"; python3 scripts/run_all.py --alias "$1" --start 200 --num 40 --timeout 900 --workers 1 --description "$1" >> "$LOG" 2>&1; [ -s "$2" ]; }
trainf(){ python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$INIT_FIX" --collator_conf "$CONF" --max_len 3072 --save_dir "$2" --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 "${@:3}" >> "$LOG" 2>&1; cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$(dirname "$2")/" 2>/dev/null; }

say "===== chain_C (workers=1) 시작 ====="

say "▶ 1  KL-LUFFY 평가 (w1, 캐시 resume)"; seval rango-grpo-luffy-kl

say "▶ 2  adaptprefix (w1)"
if roll grpo-rollout-adaptprefix data/grpo_rollouts/adaptprefix.jsonl; then
  [ ! -f models/rango-grpo-adaptprefix/adapter/adapter_model.safetensors ] && trainf data/grpo_rollouts/adaptprefix.jsonl models/rango-grpo-adaptprefix/adapter
  seval rango-grpo-adaptprefix; fi

say "▶ 3  bread (w1)"
if roll grpo-rollout-bread data/grpo_rollouts/bread.jsonl; then
  [ ! -f models/rango-grpo-bread/adapter/adapter_model.safetensors ] && trainf data/grpo_rollouts/bread.jsonl models/rango-grpo-bread/adapter --luffy
  seval rango-grpo-bread; fi

say "▶ 4  backward-prm eval (w1)"; [ -f models/rango-grpo-backward-prm/adapter/adapter_model.safetensors ] && seval rango-grpo-backward-prm

say "▶ 5  retry-prm (w1)"
if [ ! -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && [ -s data/grpo_rollouts/retry.jsonl ]; then
  python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/retry.jsonl --model_name "$BASE" --init_adapter "$INIT_ORIG" --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-grpo-retry-prm/adapter --process --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-retry-prm/ 2>/dev/null; fi
[ -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && seval rango-grpo-retry-prm

say "▶ 6  fixdyn refix (w1)"; bash all_log/run_fixdyn_refix.sh

say "▶ 7  deepres 개선(anneal/luffy-ch/dapo) + bigscale(맨 마지막) (w1)"; bash all_log/run_deepres_improvements.sh

say "===== chain_C(w1) 전체 완료 ====="
