#!/bin/bash
# tst1000tr5091 Stage4: SFT→GRPO 학습 (검증된 단일-GPU 레시피).
#   DDP GRPO는 importance-ratio 폭발(max_ρ 수백만, 단일GPU는 4~24)로 불신 → 단일GPU로.
#   기존 롤아웃(sftroll 3148그룹) + SFT모델 init → GRPO(kl0.04, ep2, lr1e-6). = bigscale2와 동일.
cd /app/coq-modeling || exit 1
TAG=tst1000tr5091
LOG=all_log/${TAG}_grpo_1gpu.log
: > "$LOG"
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
SFTM=models/rango-${TAG}-sft
SFTROLL=data/grpo_rollouts/${TAG}_sftroll.jsonl
FINM=models/rango-${TAG}-sftgrpo
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
wait_gpu(){ local need=${1:-24000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ] && { echo 0;return; }
  [ "$f1" -ge "$need" ] && { echo 1;return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 20;w=$((w+20)); done; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }

[ -f "$SFTM/adapter/adapter_model.safetensors" ] || { say "SFT 모델 없음 — 중단"; exit 1; }
[ -s "$SFTROLL" ] || { say "롤아웃 없음 — 중단"; exit 1; }
G=$(wait_gpu 24000)
say "▶ SFT→GRPO 단일-GPU (sftroll $(wc -l < $SFTROLL)그룹, init=$SFTM, kl0.04 ep2, GPU $G)"
rm -rf "$FINM/adapter"
HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$G \
  python3 -m tactic_gen.grpo_train --rollouts "$SFTROLL" --model_name "$BASE" --init_adapter "$SFTM/adapter" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$FINM/adapter" \
    --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
cpconf "$FINM"
say "  SFT→GRPO: $([ -f "$FINM/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)"
say "=== ${TAG}_GRPO_1GPU_DONE (모델: $FINM) ==="
