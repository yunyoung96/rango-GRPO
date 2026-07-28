#!/bin/bash
# ★ on-policy 축 먼저 — fixdyn(빠름) → vine(느림). 사용자: fixdyn 더 빠르면 그거부터.
#   구 체인/luffy 평가 정리 후 실행. gold 계열은 chain_gold_rest.sh 가 이 스크립트 종료 후.
set -u
LOG=all_log/chain_onpolicy.log
WORKERS=${WORKERS:-2}
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/rango-grpo-fix/adapter
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }

say "===== 정리: luffy 평가 + 구 vine 롤아웃 + 구 체인 종료 ====="
kill 776806 799319 887197 895580 939621 939622 2>/dev/null
pkill -f "run_all.py --alias rango-grpo-luffy" 2>/dev/null
pkill -f "run_thm.py run rango-grpo-luffy" 2>/dev/null
pkill -f "run_all.py --alias grpo-rollout-vine" 2>/dev/null
pkill -f "run_thm.py run grpo-rollout-vine" 2>/dev/null
pkill -f "tactic_gen_server.py decoder-local models/rango-grpo-luffy" 2>/dev/null
pkill -f "bash all_log/run_luffy.sh" 2>/dev/null
pkill -f "bash all_log/run_vine.sh" 2>/dev/null
sleep 12
say "GPU: $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader)"

say "▶ 1/2  Dynamic sampling (fixdyn, on-policy pass-rate 제어) — 빠른 first read"
if [ ! -s data/grpo_rollouts/fixdyn.jsonl ]; then
  rm -f data/grpo_rollouts/fixdyn.jsonl
  python3 scripts/run_all.py --alias grpo-rollout-fixdyn --start 200 --num 40 --timeout 600 --workers "$WORKERS" \
    --description "fixdyn 롤아웃(dynamic sampling)" >> "$LOG" 2>&1
fi
if [ -s data/grpo_rollouts/fixdyn.jsonl ]; then
  [ ! -f models/rango-grpo-fixdyn/adapter/adapter_model.safetensors ] && \
    python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/fixdyn.jsonl \
      --model_name "$BASE" --init_adapter "$INIT" --collator_conf "$CONF" --max_len 3072 \
      --save_dir models/rango-grpo-fixdyn/adapter --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-fixdyn/ 2>/dev/null
  seval rango-grpo-fixdyn
else say "  ★ fixdyn 롤아웃 실패"; fi

say "▶ 2/2  VinePPO (on-policy MC advantage) — 느림"
bash all_log/run_vine.sh

say "===== on-policy 축(fixdyn·vine) 완료 ====="
grep -h "smart\] ■" all_log/vine.log "$LOG" 2>/dev/null | tail -6
