#!/bin/bash
# ★ LUFFY 즉시 우선 — 사용자 "luffy를 먼저해줘". core 의 retry-prm(진행중)을 선점하고
#   지금 바로 LUFFY 실행. 미뤄둔 core 꼬리(retry-prm 재학습 + fix@180)는 backward 뒤에 실행.
#   순서: LUFFY @20→@40  →  backward @20→@40  →  retry-prm(재학습+eval)  →  fix@180
set -u
LOG=all_log/chain_luffy_now.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF="$(dirname "$INIT")/training_conf.yaml"
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }

say "===== LUFFY 즉시 우선 큐 시작 ====="
sleep 12  # 선점 kill 후 GPU 잔여 정리 대기

say "▶ 1/4  LUFFY @20→@40 (즉시)"
bash all_log/run_luffy.sh
say "◀ LUFFY 완료"

say "▶ 2/4  Backward curriculum @20→@40"
bash all_log/run_backward.sh
say "◀ Backward 완료"

# ── 미뤄둔 core 꼬리 ─────────────────────────────────────────────────
say "▶ 3/4  retry-prm 재학습 + eval (선점으로 중단됐던 것)"
if [ ! -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && [ -s data/grpo_rollouts/retry.jsonl ]; then
  python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/retry.jsonl \
    --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 \
    --save_dir models/rango-grpo-retry-prm/adapter \
    --process --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-retry-prm/ 2>/dev/null
fi
[ -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && seval rango-grpo-retry-prm || say "  ★ retry-prm 학습 실패"

say "▶ 4/4  fix @180 (통계 확정)"
python3 scripts/smart_eval.py --alias rango-grpo-fix --stages 180 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"

say "===== 전체 완료 ====="
grep -h "smart\] ■" all_log/luffy.log all_log/backward.log "$LOG" 2>/dev/null | tail -10
