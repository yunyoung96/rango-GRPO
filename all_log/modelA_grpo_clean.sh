#!/bin/bash
# 모델A (single-round) GRPO 재실행 — 초대형 float폭발 그룹 21개 제외한 clean mixed로.
#   GPU0 단독. 완료되면 /tmp/gpu0_foreign 제거 → 모델B(GPU1)가 양쪽 GPU 사용.
#   rand200 비교는 모델B chunk 스크립트가 끝에서 일괄(모델A+모델B).
cd /app/coq-modeling || exit 1
TAG=tst1000tr5091
LOG=all_log/${TAG}_modelA_clean.log
: > "$LOG"
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
SFTM=models/rango-${TAG}-sft
FINM=models/rango-${TAG}-sftgrpo
MIXED=data/grpo_rollouts/${TAG}_sftroll_mixed_clean.jsonl
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }

say "▶ 모델A GRPO (clean mixed $(wc -l < $MIXED)그룹, GPU0, kl0.04 ep2)"
rm -rf "$FINM/adapter"
HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=0 \
  python3 -m tactic_gen.grpo_train --rollouts "$MIXED" --model_name "$BASE" --init_adapter "$SFTM/adapter" \
    --ref_adapter "$SFTM/adapter" --collator_conf "$CONF" --max_len 3072 --save_dir "$FINM/adapter" \
    --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
cpconf "$FINM"
if [ -f "$FINM/adapter/adapter_model.safetensors" ]; then
  say "  모델A GRPO OK → $FINM"
else
  say "  모델A GRPO 실패"
fi
# GPU0 해제 → 모델B가 양쪽 GPU 사용
rm -f /tmp/gpu0_foreign
say "  /tmp/gpu0_foreign 제거 = GPU0 해제. 모델B가 이제 양쪽 GPU 사용."
say "=== ${TAG}_MODELA_CLEAN_DONE ==="
