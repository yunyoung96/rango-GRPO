#!/bin/bash
# 마지막 큐: DAPG(감쇠 demo-gradient, LUFFY 회귀 방지 장치) → bigscale. worker 1.
#   DAPG: luffy.jsonl(gold 주입) 재사용, fix 초기화. on-policy GRPO + gold demo(λ₀·λ₁^step 감쇠).
# 비교기준 = 우리 rango(11/15) + fix(13/19). published 비교 안 함.
set -u
LOG=all_log/dapg.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT_FIX=models/rango-grpo-fix/adapter
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 --workers 1 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"; }

say "===== DAPG 시작 (gold demo 감쇠 λ₀=0.1 λ₁=0.999, on-fix) ====="
if [ -s data/grpo_rollouts/luffy.jsonl ]; then
  if [ ! -f models/rango-grpo-dapg/adapter/adapter_model.safetensors ]; then
    python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/luffy.jsonl \
      --model_name "$BASE" --init_adapter "$INIT_FIX" --collator_conf "$CONF" --max_len 3072 \
      --save_dir models/rango-grpo-dapg/adapter --dapg --dapg_l0 0.1 --dapg_l1 0.999 \
      --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1
    cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-dapg/ 2>/dev/null
  fi
  [ -f models/rango-grpo-dapg/adapter/adapter_model.safetensors ] && seval rango-grpo-dapg || say "★ DAPG 학습 실패"
else
  say "★ luffy.jsonl 없음 — DAPG 스킵"
fi
say "===== DAPG 완료 ====="

say "▶ (마지막) bigscale"
bash all_log/run_bigscale_real.sh
say "===== 전체 종료(DAPG + bigscale) ====="
grep -h "smart\] ■" "$LOG" all_log/bigscale.log 2>/dev/null | tail -4
