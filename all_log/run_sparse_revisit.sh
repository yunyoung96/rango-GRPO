#!/bin/bash
# ★ sparse-mitigation 기법 재검증 — 베이스 정정 후 재실험.
#
# 배경: 옛 effstudy(E1~E4)는 base 불일치 버그가 있던 상태로 평가돼 전부 실패 판정.
#   fix(베이스 정정)가 rango-grpo −1 → +2 로 뒤집힌 걸 보고, 그 기법들도 재검증.
#   비교기준 = 우리 rango (@20=11 @40=15). smart_eval 에스컬레이션.
#
# 순서(싼 것 먼저):
#   E2-fix (dense reward)   : 기존 E2-dense.jsonl 재학습만  [빠름]
#   E3-fix (curriculum)     : 기존 E3-curriculum.jsonl 재학습만 [빠름]
#   E4-fix (G=16 scale)     : G16 롤아웃 재수집 → 학습        [중간]
#   E1-fix (expert-iter)    : rango-grpo-fix 정책으로 재롤아웃 → 학습 [중간]
set -u
LOG=all_log/sparse_revisit.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF="$(dirname "$INIT")/training_conf.yaml"
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
train(){ python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$2" --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 "${@:3}" >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$(dirname "$2")/" 2>/dev/null; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }

say "===== sparse-mitigation 재검증 시작 ====="

# ── E2-fix (dense reward) — 기존 데이터 재학습 ───────────────────────
say "▶ E2-fix (dense reward, 기존 롤아웃 재학습)"
[ ! -f models/rango-grpo-e2fix/adapter/adapter_model.safetensors ] && \
  train data/grpo_rollouts/E2-dense.jsonl models/rango-grpo-e2fix/adapter
seval rango-grpo-e2fix

# ── E3-fix (curriculum) — 기존 데이터 재학습 ─────────────────────────
say "▶ E3-fix (curriculum, 기존 롤아웃 재학습)"
[ ! -f models/rango-grpo-e3fix/adapter/adapter_model.safetensors ] && \
  train data/grpo_rollouts/E3-curriculum.jsonl models/rango-grpo-e3fix/adapter
seval rango-grpo-e3fix

# ── E4-fix (G=16 scale) — 롤아웃 재수집 ──────────────────────────────
say "▶ E4-fix (G=16, 롤아웃 재수집)"
if [ ! -s data/grpo_rollouts/E4-g16.jsonl ]; then
  rm -f data/grpo_rollouts/E4-g16.jsonl
  python3 scripts/run_all.py --alias grpo-rollout-g16 --start 200 --num 40 --timeout 600 --workers 2 \
    --description "E4 G16 재수집" >> "$LOG" 2>&1
fi
[ -s data/grpo_rollouts/E4-g16.jsonl ] && [ ! -f models/rango-grpo-e4fix/adapter/adapter_model.safetensors ] && \
  train data/grpo_rollouts/E4-g16.jsonl models/rango-grpo-e4fix/adapter
[ -f models/rango-grpo-e4fix/adapter/adapter_model.safetensors ] && seval rango-grpo-e4fix || say "  ★ E4 실패"

# ── E1-fix (expert-iter) — fix 정책으로 재롤아웃 → 학습 ──────────────
say "▶ E1-fix (expert-iter: rango-grpo-fix 정책으로 재롤아웃)"
if [ ! -s data/grpo_rollouts/e1fix.jsonl ]; then
  rm -f data/grpo_rollouts/e1fix.jsonl
  python3 scripts/run_all.py --alias grpo-rollout-e1fix --start 200 --num 40 --timeout 600 --workers 2 \
    --description "E1 expert-iter 재롤아웃(fix 정책)" >> "$LOG" 2>&1
fi
[ -s data/grpo_rollouts/e1fix.jsonl ] && [ ! -f models/rango-grpo-e1fix/adapter/adapter_model.safetensors ] && \
  train data/grpo_rollouts/e1fix.jsonl models/rango-grpo-e1fix/adapter
[ -f models/rango-grpo-e1fix/adapter/adapter_model.safetensors ] && seval rango-grpo-e1fix || say "  ★ E1 실패"

say "===== sparse-mitigation 재검증 완료 ====="
grep -h "smart\] ■" "$LOG" | tail -8
