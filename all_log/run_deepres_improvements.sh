#!/bin/bash
# deep-research 진단 → 3개 개선 적용 실험 (worker 2, 순차).
#   (1) revcurr-anneal : 기존 revcurr.jsonl 재사용 + --curriculum_anneal (near-goal→s0)
#   (2) luffy-ch       : 기존 luffy.jsonl 재사용 + --clip_eps_high 0.28 (exploration 보존)
#   (3) dapo           : dynamic-sampling 롤아웃 + --dapo (clip-higher+token-level+KL제거+overlong)
# 비교기준 = 우리 rango(@20=11,@40=15) + fix(@20=13,@40=19). published 비교 안 함.
set -u
LOG=all_log/deepres_improve.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT_FIX=models/rango-grpo-fix/adapter
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 --workers 1 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }
roll(){ [ -s "$2" ] && return 0; rm -f "$2"; python3 scripts/run_all.py --alias "$1" --start 200 --num 40 --timeout 900 --workers 1 --description "$1" >> "$LOG" 2>&1; [ -s "$2" ]; }

# ── (1) revcurr-anneal — revcurr.jsonl 이 준비돼 있어야 함(같은 롤아웃 재사용) ──
say "▶ (1) revcurr-anneal (anneal-to-s0, revcurr.jsonl 재사용)"
if [ -s data/grpo_rollouts/revcurr.jsonl ]; then
  if [ ! -f models/rango-grpo-revcurr-anneal/adapter/adapter_model.safetensors ]; then
    python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/revcurr.jsonl \
      --model_name "$BASE" --init_adapter "$INIT_FIX" --collator_conf "$CONF" --max_len 3072 \
      --save_dir models/rango-grpo-revcurr-anneal/adapter --curriculum_anneal \
      --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1
    cpconf models/rango-grpo-revcurr-anneal
  fi
  [ -f models/rango-grpo-revcurr-anneal/adapter/adapter_model.safetensors ] && seval rango-grpo-revcurr-anneal || say "★ anneal 학습 실패"
else
  say "★ revcurr.jsonl 없음 — revcurr 롤아웃 완료 후 재실행 필요. 건너뜀."
fi

# ── (2) luffy-ch — luffy.jsonl 재사용 + clip-higher ──
say "▶ (2) luffy-ch (clip-higher 0.28, exploration 보존, luffy.jsonl 재사용)"
if [ -s data/grpo_rollouts/luffy.jsonl ]; then
  if [ ! -f models/rango-grpo-luffy-ch/adapter/adapter_model.safetensors ]; then
    python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/luffy.jsonl \
      --model_name "$BASE" --init_adapter "$INIT_FIX" --collator_conf "$CONF" --max_len 3072 \
      --save_dir models/rango-grpo-luffy-ch/adapter --luffy --clip_eps_high 0.28 \
      --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1
    cpconf models/rango-grpo-luffy-ch
  fi
  [ -f models/rango-grpo-luffy-ch/adapter/adapter_model.safetensors ] && seval rango-grpo-luffy-ch || say "★ luffy-ch 학습 실패"
else
  say "★ luffy.jsonl 없음 — 건너뜀."
fi

# ── (3) dapo — dynamic-sampling 롤아웃 + 4기법 학습 ──
say "▶ (3) dapo (dynamic sampling + clip-higher + token-level + overlong)"
if roll grpo-rollout-dapo data/grpo_rollouts/dapo.jsonl; then
  if [ ! -f models/rango-grpo-dapo/adapter/adapter_model.safetensors ]; then
    python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/dapo.jsonl \
      --model_name "$BASE" --init_adapter "$INIT_FIX" --collator_conf "$CONF" --max_len 3072 \
      --save_dir models/rango-grpo-dapo/adapter --dapo --clip_eps_high 0.28 \
      --kl_beta 0.0 --overlong_cap 18 --overlong_buffer 4 \
      --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
    cpconf models/rango-grpo-dapo
  fi
  [ -f models/rango-grpo-dapo/adapter/adapter_model.safetensors ] && seval rango-grpo-dapo || say "★ dapo 학습 실패"
else
  say "★ dapo 롤아웃 실패 — 건너뜀."
fi

say "===== deep-research 개선 3종 완료 ====="
grep -h "smart\] ■" "$LOG" 2>/dev/null | tail -6

# ── 맨 마지막: bigscale (사용자 요청으로 전체 큐의 최후로 미룸) ──
say "▶ (마지막) bigscale — run_bigscale_real.sh"
bash all_log/run_bigscale_real.sh
say "===== 전체 큐 완전 종료(bigscale 포함) ====="
