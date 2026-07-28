#!/bin/bash
# RFT / expert-iteration (내 추천 #2) — 성공 궤적 SFT(순수 MLE). worker 1.
#   rft-gold : luffy.jsonl(gold 궤적 포함) SFT → fail set 직접 겨냥. fix anchor(KL β=0.04).
#   rft-self : revcurr.jsonl(모델 자기 성공만) SFT → on-policy, shift 없음(대조군).
# 둘 다 fix 초기화. 비교기준 = 우리 rango(11/15) + fix(13/19). published 비교 안 함.
set -u
LOG=all_log/rft.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT_FIX=models/rango-grpo-fix/adapter
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 --workers 1 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }
sft(){  # $1=rollout jsonl  $2=save alias-sub  $3=kl_beta
  local m="models/rango-grpo-$2/adapter"
  if [ ! -f "$m/adapter_model.safetensors" ]; then
    python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$INIT_FIX" \
      --collator_conf "$CONF" --max_len 3072 --save_dir "$m" --sft --kl_beta "$3" \
      --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
    cpconf "models/rango-grpo-$2"
  fi
  [ -f "$m/adapter_model.safetensors" ] && seval "rango-grpo-$2" || say "★ $2 학습 실패"
}

say "===== RFT/expert-iteration (SFT) 시작 ====="
say "▶ rft-gold (luffy.jsonl gold 궤적 SFT, fail set 겨냥, KL anchor 0.04)"
[ -s data/grpo_rollouts/luffy.jsonl ] && sft data/grpo_rollouts/luffy.jsonl rft-gold 0.04 || say "★ luffy.jsonl 없음"
say "▶ rft-self (revcurr.jsonl 자기 성공만 SFT, shift 없음, KL anchor 0.04)"
[ -s data/grpo_rollouts/revcurr.jsonl ] && sft data/grpo_rollouts/revcurr.jsonl rft-self 0.04 || say "★ revcurr.jsonl 없음"
say "===== RFT 완료 ====="
grep -h "smart\] ■" "$LOG" 2>/dev/null | tail -4
