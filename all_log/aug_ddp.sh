#!/bin/bash
# augmented SFT를 DDP 2-GPU로 학습 → rand200@600s 평가.
#   grpo_train.py DDP: DDP_TRAIN=1 + torchrun. group을 rank별 샤딩 + join()으로 backward불균형 데드락 방지.
#   0) DDP smoke(20그룹 1ep, timeout가드) → 데드락/저장 확인  1) 전체 SFT(2ep)  2) rand200@600s eval
cd /app/coq-modeling || exit 1
LOG=all_log/aug_ddp.log
: > "$LOG"
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
GOLD=data/grpo_rollouts/goldsft_bs2.jsonl
RAND=data/compcert_bs2_rand200_idx.txt
AUGM=models/rango-aug-bs2-sft
export INJECT_TYPES=1 INJECT_DEFS=1 RERANK_PREMISES=1 HF_HUB_OFFLINE=1
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'),'(',round(100*d.get('success',0)/max(d.get('done',1),1),1),'%)')" 2>/dev/null; }

DDP_ENV="DDP_TRAIN=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=0,1 INJECT_TYPES=1 INJECT_DEFS=1 RERANK_PREMISES=1 HF_HUB_OFFLINE=1"

# ── 0) DDP smoke: 20그룹 1ep, timeout 600s(데드락이면 강제종료) ──
say "▶0 DDP smoke (20그룹 1ep, 2-GPU, 데드락/저장 검증)"
head -20 "$GOLD" > /tmp/gold_smoke.jsonl
rm -rf /tmp/ddp_smoke_adapter
timeout 600 env $DDP_ENV \
  torchrun --standalone --nproc_per_node=2 -m tactic_gen.grpo_train \
    --rollouts /tmp/gold_smoke.jsonl --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir /tmp/ddp_smoke_adapter --sft --kl_beta 0.0 \
    --epochs 1 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
RC=$?
if [ $RC -eq 124 ]; then say "  ✗ smoke TIMEOUT — 데드락 의심. 중단."; exit 1; fi
if [ ! -f /tmp/ddp_smoke_adapter/adapter_model.safetensors ]; then say "  ✗ smoke 저장 실패(rc=$RC). 중단."; exit 1; fi
say "  ✓ DDP smoke OK (rc=$RC, 데드락 없음·rank0 저장됨) → 전체 학습 진행"

# ── 1) 전체 augmented SFT (DDP 2-GPU, 2ep) ──
say "▶1 augmented SFT DDP 2-GPU (train300 gold, 2ep)"
rm -rf "$AUGM/adapter"
env $DDP_ENV \
  torchrun --standalone --nproc_per_node=2 -m tactic_gen.grpo_train \
    --rollouts "$GOLD" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$AUGM/adapter" --sft --kl_beta 0.0 \
    --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$AUGM/" 2>/dev/null
say "  SFT: $([ -f "$AUGM/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)"
[ -f "$AUGM/adapter/adapter_model.safetensors" ] || { say "SFT 실패 — 중단"; exit 1; }

# ── 2) rand200 @600s 평가 (augmented env, w2) ──
say "▶2 평가 augmented SFT rand200 @600s w2 (INJECT env, GPU 0,1)"
rm -rf all_results/aug_bs2_rand200_600
EXEC_ADAPTER=$AUGM/adapter INJECT_TYPES=1 INJECT_DEFS=1 RERANK_PREMISES=1 HF_HUB_OFFLINE=1 \
  python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" --timeout 600 --gpus "0,1" --workers 2 \
  --out all_results/aug_bs2_rand200_600 --description "augmented SFT rand200 @600s" >> "$LOG" 2>&1
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
say "  ★★ augmented SFT rand200@600s: $(sumline all_results/aug_bs2_rand200_600)"
say "     비교(rand200@600s): base rango 67/200(33.5%) / SFT→GRPO 75/200(37.5%)"
say "=== AUG_DDP_DONE ==="
