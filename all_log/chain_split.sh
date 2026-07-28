#!/bin/bash
# fix@180(w1)과 동시에 vine 롤아웃(w1) 수집(bursty, 총부하 fix w2와 동일). 학습은 fix@180 완료 후.
set -u
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a all_log/newtech.log; }
BASE=deepseek-ai/deepseek-coder-1.3b-instruct; INIT=models/rango-grpo-fix/adapter
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 --workers 1 2>&1 | tee -a all_log/newtech.log | grep -E "smart\] ■"; }
say "▶ vine 롤아웃 수집(w1, fix@180과 동시 — 롤아웃만)"
if [ ! -s data/grpo_rollouts/vine.jsonl ]; then
  python3 scripts/run_all.py --alias grpo-rollout-vine --start 200 --num 40 --timeout 1200 --workers 1 --description "vine roll w1" >> all_log/newtech.log 2>&1
fi
say "  vine 롤아웃 완료. fix@180 완료 대기(학습은 GPU 독점이라 뒤로)"
until [ "$(python3 -c "import json;print(len(json.load(open('all_results/smart_rango-grpo-fix/summary.json'))['results']))" 2>/dev/null||echo 0)" -ge 180 ]; do sleep 120; done
say "fix@180 완료 → 학습 단계(GPU 단독)"
# vine 학습+eval
[ -s data/grpo_rollouts/vine.jsonl ] && [ ! -f models/rango-grpo-vine/adapter/adapter_model.safetensors ] && python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/vine.jsonl --model_name "$BASE" --init_adapter "$INIT" --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-grpo-vine/adapter --vine --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> all_log/newtech.log 2>&1
cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-vine/ 2>/dev/null
[ -f models/rango-grpo-vine/adapter/adapter_model.safetensors ] && seval rango-grpo-vine
say "▶ KL-LUFFY"; bash all_log/run_luffy_kl.sh
say "▶ revcurr"; bash all_log/run_revcurr.sh
say "===== split 큐 완료(adaptprefix/bread 이어서) ====="
