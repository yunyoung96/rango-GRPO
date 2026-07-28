#!/bin/bash
# ★ 배치3: adaptive-prefix / dynamic-sampling / BREAD — 전부 on-fix. 각 @20→@40.
#   adaptprefix: pass-rate 조준 커리큘럼(plain GRPO)
#   fixdyn     : dynamic sampling(dead 재샘플, plain GRPO)
#   bread      : on-policy 궤적 + gold 다리(--luffy, 다리 step=off_policy)
# 비교기준 = 우리 rango(11/15) + fix(13/19). published 비교 안 함.
set -u
LOG=all_log/batch3.log
WORKERS=${WORKERS:-2}
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/rango-grpo-fix/adapter
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }
train(){  # $1=rollouts $2=save_dir  $3.. = 추가플래그
  python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$2" \
    --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 "${@:3}" >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$(dirname "$2")/" 2>/dev/null
  [ -f "$2/adapter_model.safetensors" ]; }
roll(){  # $1=alias $2=out $3=timeout
  [ -s "$2" ] && return 0
  rm -f "$2"
  python3 scripts/run_all.py --alias "$1" --start 200 --num 40 --timeout "$3" --workers "$WORKERS" \
    --description "batch3 $1" >> "$LOG" 2>&1
  [ -s "$2" ]; }

say "===== 배치3 시작 (adaptprefix / fixdyn / bread) ====="

# 사전: revcurr.json(adaptprefix용), gold.json(bread용) 존재 보장
[ -s data/curriculum/revcurr.json ] || python3 scripts/build_revcurr_curriculum.py >> "$LOG" 2>&1
[ -s data/curriculum/gold.json ] || python3 scripts/build_gold_trajectories.py --project compcert --start 200 --num 40 >> "$LOG" 2>&1

# ── 1. Adaptive prefix ───────────────────────────────────────────────
say "▶ 1/3  adaptive-prefix (pass-rate 조준 커리큘럼)"
if roll grpo-rollout-adaptprefix data/grpo_rollouts/adaptprefix.jsonl 900; then
  [ ! -f models/rango-grpo-adaptprefix/adapter/adapter_model.safetensors ] && \
    train data/grpo_rollouts/adaptprefix.jsonl models/rango-grpo-adaptprefix/adapter
  seval rango-grpo-adaptprefix
else say "  ★ adaptprefix 롤아웃 실패"; fi

# ── 2. Dynamic sampling ──────────────────────────────────────────────
say "▶ 2/3  dynamic-sampling (dead 재샘플)"
if roll grpo-rollout-fixdyn data/grpo_rollouts/fixdyn.jsonl 600; then
  [ ! -f models/rango-grpo-fixdyn/adapter/adapter_model.safetensors ] && \
    train data/grpo_rollouts/fixdyn.jsonl models/rango-grpo-fixdyn/adapter
  seval rango-grpo-fixdyn
else say "  ★ fixdyn 롤아웃 실패"; fi

# ── 3. BREAD ─────────────────────────────────────────────────────────
say "▶ 3/3  BREAD (gold 다리, --luffy)"
if roll grpo-rollout-bread data/grpo_rollouts/bread.jsonl 900; then
  [ ! -f models/rango-grpo-bread/adapter/adapter_model.safetensors ] && \
    train data/grpo_rollouts/bread.jsonl models/rango-grpo-bread/adapter --luffy
  seval rango-grpo-bread
else say "  ★ bread 롤아웃 실패"; fi

say "===== 배치3 완료 ====="
grep -h "smart\] ■" "$LOG" 2>/dev/null | tail -8
