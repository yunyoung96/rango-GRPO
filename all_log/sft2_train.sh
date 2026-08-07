#!/bin/bash
# sft-2 재학습 — sft-1(lr1e-6 ep2)이 gold서 exact-match 40%뿐(underfit) → 강화.
#   변경: lr 1e-6→1e-4(100×↑, 진짜 원인), epochs 2→3. init=rango baseline 위 gold --sft(MLE, kl0).
#   ★DDP 2-GPU(torchrun) — SFT(MLE)는 DDP 안전([[ddp-grpo-ratio-explode]]). gold 38k step이라 단일GPU 17h → DDP ~5h.
#   모델명 규칙: rango-...-sft-2 ([[sft-iteration-naming]]).
set -u
cd /app/coq-modeling
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
GOLD=data/grpo_rollouts/tst1000tr5091_gold.jsonl
OUT=models/rango-tst1000tr5091-sft-2
LOG=all_log/sft2_train.log
echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] sft-2 시작 (DDP 2-GPU, lr=1e-4 ep3, init=rango baseline, gold --sft)" | tee -a "$LOG"
DDP_TRAIN=1 HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  torchrun --nproc_per_node=2 --master_port=29517 -m tactic_gen.grpo_train \
    --rollouts "$GOLD" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$OUT/adapter" \
    --sft --kl_beta 0.0 --epochs 3 --lr 1e-4 --micro_bsz 2 >> "$LOG" 2>&1
cp "$CONF" models/rango-grpo/lm-example-conf.yaml "$OUT/" 2>/dev/null
echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] sft-2 종료: $([ -f "$OUT/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)" | tee -a "$LOG"
