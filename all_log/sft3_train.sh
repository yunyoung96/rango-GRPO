#!/bin/bash
# sft-3 = "더 강한 sft" — sft-2(lr1e-4 bs4 ep3 noshuf) 대비 개선:
#   ★ SHUFFLE_GROUPS=1 (epoch마다 group 순서 셔플 — 상관배치 완화)
#   ★ micro_bsz 2→4 (DDP 2GPU → 유효배치 4→8)
#   ★ epochs 3→5
#   lr=1e-4 유지. init=rango baseline(checkpoint-54500) 위 gold --sft(MLE). epoch 0부터 새로.
#   이름: 특징 드러나는 서술형 ([[sft-iteration-naming]]).
set -u
cd /app/coq-modeling
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
GOLD=data/grpo_rollouts/tst1000tr5091_gold.jsonl
OUT=models/rango-tst1000tr5091-sft_lr1e-4_bs4_ep5_shuf   # ★bs8(micro4) OOM(48GB초과) → bs4(micro2)로. grad_accum 없이 bs8 불가.
LOG=all_log/sft3_train.log
echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] sft-3 시작 (DDP 2GPU, lr1e-4, micro2=유효배치4, ep5, SHUFFLE ON)" | tee -a "$LOG"
DDP_TRAIN=1 SHUFFLE_GROUPS=1 HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  torchrun --nproc_per_node=2 --master_port=29521 -m tactic_gen.grpo_train \
    --rollouts "$GOLD" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$OUT/adapter" \
    --sft --kl_beta 0.0 --epochs 5 --lr 1e-4 --micro_bsz 2 >> "$LOG" 2>&1
cp "$CONF" models/rango-grpo/lm-example-conf.yaml "$OUT/" 2>/dev/null
echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] sft-3 종료: $([ -f "$OUT/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)" | tee -a "$LOG"
