#!/bin/bash
# ★ fix@180(robustness)과 동시에 새 기법 @40 시도. workers=1(가볍게). smart_eval 캐싱=안 돈 것만.
#   순서: KL-LUFFY(회귀처방, 롤아웃 재사용=가벼움) → vine → revcurr → adaptprefix → bread.
set -u
export WORKERS=1
LOG=all_log/newtech.log
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
say "===== 새 기법 @40 동시 파이프라인 시작(workers=1) ====="
say "▶ KL-LUFFY (luffy.jsonl 재사용, 회귀 처방)"; bash all_log/run_luffy_kl.sh
say "▶ VinePPO"; bash all_log/run_vine.sh
say "▶ revcurr"; bash all_log/run_revcurr.sh
say "▶ adaptprefix"
BASE=deepseek-ai/deepseek-coder-1.3b-instruct; INIT=models/rango-grpo-fix/adapter
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 --workers 1 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"; }
if [ ! -s data/grpo_rollouts/adaptprefix.jsonl ]; then python3 scripts/run_all.py --alias grpo-rollout-adaptprefix --start 200 --num 40 --timeout 900 --workers 1 --description adaptprefix >> "$LOG" 2>&1; fi
[ -s data/grpo_rollouts/adaptprefix.jsonl ] && { [ ! -f models/rango-grpo-adaptprefix/adapter/adapter_model.safetensors ] && python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/adaptprefix.jsonl --model_name "$BASE" --init_adapter "$INIT" --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-grpo-adaptprefix/adapter --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1; cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-adaptprefix/ 2>/dev/null; seval rango-grpo-adaptprefix; }
say "▶ bread"
if [ ! -s data/grpo_rollouts/bread.jsonl ]; then python3 scripts/run_all.py --alias grpo-rollout-bread --start 200 --num 40 --timeout 900 --workers 1 --description bread >> "$LOG" 2>&1; fi
[ -s data/grpo_rollouts/bread.jsonl ] && { [ ! -f models/rango-grpo-bread/adapter/adapter_model.safetensors ] && python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/bread.jsonl --model_name "$BASE" --init_adapter "$INIT" --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-grpo-bread/adapter --luffy --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1; cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-bread/ 2>/dev/null; seval rango-grpo-bread; }
say "===== 새 기법 전체 완료 ====="
grep -h "smart\] ■" "$LOG" | tail -6
