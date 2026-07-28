#!/bin/bash
# ★ fix@180 완료 후 남은 전체: vine→KL-LUFFY→revcurr→adaptprefix→bread→backward-prm(eval)→bigscale→retry-prm.
set -u
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a all_log/newtech.log; }
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT_FIX=models/rango-grpo-fix/adapter
INIT_ORIG=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 --workers 2 2>&1 | tee -a all_log/newtech.log | grep -E "smart\] ■"; }
roll(){ [ -s "$2" ] && return 0; rm -f "$2"; python3 scripts/run_all.py --alias "$1" --start 200 --num 40 --timeout 900 --workers 2 --description "$1" >> all_log/newtech.log 2>&1; [ -s "$2" ]; }
trainf(){ python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$INIT_FIX" --collator_conf "$CONF" --max_len 3072 --save_dir "$2" --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 "${@:3}" >> all_log/newtech.log 2>&1; cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$(dirname "$2")/" 2>/dev/null; }

say "대기: fix@180 완료까지"
until [ "$(python3 -c "import json;print(len(json.load(open('all_results/smart_rango-grpo-fix/summary.json'))['results']))" 2>/dev/null||echo 0)" -ge 180 ]; do sleep 120; done
say "fix@180 완료 → 남은 기법 순차 시작"

say "▶ 1/8 vine 학습+eval (롤아웃 완료됨)"
[ -s data/grpo_rollouts/vine.jsonl ] && [ ! -f models/rango-grpo-vine/adapter/adapter_model.safetensors ] && python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/vine.jsonl --model_name "$BASE" --init_adapter "$INIT_FIX" --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-grpo-vine/adapter --vine --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> all_log/newtech.log 2>&1
cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-vine/ 2>/dev/null
[ -f models/rango-grpo-vine/adapter/adapter_model.safetensors ] && seval rango-grpo-vine

say "▶ 2/8 KL-LUFFY"; bash all_log/run_luffy_kl.sh
say "▶ 3/8 revcurr"; bash all_log/run_revcurr.sh
say "▶ 4/8 adaptprefix"
roll grpo-rollout-adaptprefix data/grpo_rollouts/adaptprefix.jsonl && { [ ! -f models/rango-grpo-adaptprefix/adapter/adapter_model.safetensors ] && trainf data/grpo_rollouts/adaptprefix.jsonl models/rango-grpo-adaptprefix/adapter; seval rango-grpo-adaptprefix; }
say "▶ 5/8 bread"
roll grpo-rollout-bread data/grpo_rollouts/bread.jsonl && { [ ! -f models/rango-grpo-bread/adapter/adapter_model.safetensors ] && trainf data/grpo_rollouts/bread.jsonl models/rango-grpo-bread/adapter --luffy; seval rango-grpo-bread; }
say "▶ 6/8 backward-prm (eval only)"; [ -f models/rango-grpo-backward-prm/adapter/adapter_model.safetensors ] && seval rango-grpo-backward-prm
say "▶ 7/8 bigscale (뒤1000 학습/앞5091 평가 — 매우 오래)"; bash all_log/run_bigscale.sh
say "▶ 8/8 retry-prm"
[ ! -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && [ -s data/grpo_rollouts/retry.jsonl ] && { python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/retry.jsonl --model_name "$BASE" --init_adapter "$INIT_ORIG" --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-grpo-retry-prm/adapter --process --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> all_log/newtech.log 2>&1; cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-retry-prm/ 2>/dev/null; }
[ -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && seval rango-grpo-retry-prm
say "===== 전체 완료 ====="
