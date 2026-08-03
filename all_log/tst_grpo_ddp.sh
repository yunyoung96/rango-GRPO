#!/bin/bash
# tst1000tr5091 Stage4: SFT→GRPO 학습을 이어서(중단됐던 파이프라인의 마지막 조각).
#   기존 롤아웃(sftroll 3148그룹, mixed 933) + SFT모델 init → GRPO(kl0.04). DDP 2-GPU.
#   0) GRPO DDP smoke(60그룹 1ep, timeout가드: ref/kl 경로가 join과 맞는지) 1) 전체 GRPO
cd /app/coq-modeling || exit 1
TAG=tst1000tr5091
LOG=all_log/${TAG}_grpo_ddp.log
: > "$LOG"
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
SFTM=models/rango-${TAG}-sft
SFTROLL=data/grpo_rollouts/${TAG}_sftroll.jsonl
FINM=models/rango-${TAG}-sftgrpo
DDP_ENV="DDP_TRAIN=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=0,1 HF_HUB_OFFLINE=1"
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }

[ -f "$SFTM/adapter/adapter_model.safetensors" ] || { say "SFT 모델 없음 — 중단"; exit 1; }
[ -s "$SFTROLL" ] || { say "롤아웃 없음 — 중단"; exit 1; }
say "이어서: Stage4 GRPO (sftroll $(wc -l < $SFTROLL)그룹, init=$SFTM, kl0.04, DDP 2-GPU)"

# ── 0) GRPO DDP smoke: 60그룹 1ep, timeout 600(데드락 가드). ref/kl 경로 검증 ──
say "▶0 GRPO DDP smoke (60그룹 1ep, ref/kl+join 검증)"
head -60 "$SFTROLL" > /tmp/${TAG}_grpo_smoke.jsonl
rm -rf /tmp/${TAG}_grpo_smoke_adapter
timeout 600 env $DDP_ENV \
  torchrun --standalone --nproc_per_node=2 -m tactic_gen.grpo_train \
    --rollouts /tmp/${TAG}_grpo_smoke.jsonl --model_name "$BASE" --init_adapter "$SFTM/adapter" \
    --collator_conf "$CONF" --max_len 3072 --save_dir /tmp/${TAG}_grpo_smoke_adapter \
    --kl_beta 0.04 --epochs 1 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
RC=$?
if [ $RC -eq 124 ]; then say "  ✗ smoke TIMEOUT — 데드락 의심. 중단."; exit 1; fi
if [ ! -f /tmp/${TAG}_grpo_smoke_adapter/adapter_model.safetensors ]; then say "  ✗ smoke 저장 실패(rc=$RC). 중단."; exit 1; fi
say "  ✓ GRPO DDP smoke OK (rc=$RC, 데드락 없음·저장됨) → 전체 진행"

# ── 1) 전체 SFT→GRPO (DDP 2-GPU, 3148그룹, kl0.04 ep2) ──
say "▶1 SFT→GRPO 전체 (DDP 2-GPU, kl0.04 ep2)"
rm -rf "$FINM/adapter"
env $DDP_ENV \
  torchrun --standalone --nproc_per_node=2 -m tactic_gen.grpo_train \
    --rollouts "$SFTROLL" --model_name "$BASE" --init_adapter "$SFTM/adapter" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$FINM/adapter" \
    --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
cpconf "$FINM"
say "  SFT→GRPO: $([ -f "$FINM/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)"
say "=== ${TAG}_GRPO_DONE (모델: $FINM) ==="
