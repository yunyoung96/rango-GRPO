#!/bin/bash
# augmented(rerank+[TYPES]재귀+[DEFINITIONS]) 실험 — train300/test1191, base rango 이어서 continue-SFT.
#   비교: 비증강 SFT(rango-grpo-bs2-sft = 324/1191=27.2% @120s) vs augmented SFT.
#   env INJECT_TYPES/INJECT_DEFS/RERANK_PREMISES 를 학습·평가 모두 동일 적용(OOD 방지).
cd /app/coq-modeling || exit 1
LOG=all_log/aug_bs2.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500   # base rango
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
GOLD=data/grpo_rollouts/goldsft_bs2.jsonl        # train300 gold-SFT 데이터(이미 있음)
TEST=data/compcert_bs2_test_idx.txt              # 1191
AUGM=models/rango-aug-bs2-sft
# ★ augmented env (학습·평가 동일)
export INJECT_TYPES=1 INJECT_DEFS=1 RERANK_PREMISES=1
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'),'(',round(100*d.get('success',0)/max(d.get('done',1),1),1),'%)')" 2>/dev/null; }
wait_gpu(){ local need=${1:-24000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ] && { echo 0;return; }
  [ "$f1" -ge "$need" ] && { echo 1;return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 20;w=$((w+20)); done; }
wait_gpus(){ local need=${1:-13000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  local g=""; [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ]&&g="0"; [ "$f1" -ge "$need" ]&&g="${g:+$g,}1"
  [ -n "$g" ]&&{ echo "$g";return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 20;w=$((w+20)); done; }

# ── 인덱스 확인 ──
[ -s data/type_defs.json ] || python3 scripts/build_struct_index.py >> "$LOG" 2>&1
say "인덱스: type $(python3 -c "import json;print(len(json.load(open('data/type_defs.json'))))") / func $(python3 -c "import json;print(len(json.load(open('data/func_defs.json'))))")"

# ── smoke: augmented 프롬프트로 5정리 eval (배선·크래시 확인) ──
say "smoke: augmented 5정리 eval"
head -5 "$TEST" > /tmp/aug_smoke.txt
GPUS=$(wait_gpus 13000)
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$INIT INJECT_TYPES=1 INJECT_DEFS=1 RERANK_PREMISES=1 \
  python3 scripts/run_all.py --alias rango-grpo --idx-file /tmp/aug_smoke.txt --timeout 120 --gpus "$GPUS" --workers 2 --out /tmp/aug_smoke_res >> "$LOG" 2>&1
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 3
say "  smoke: $(sumline /tmp/aug_smoke_res) (크래시 없으면 진행)"

# ── 1) augmented continue-SFT (base rango 위, gold train300, augmented env) ──
say "▶1 augmented SFT (init=base rango, INJECT_TYPES+DEFS+RERANK)"
if [ ! -f "$AUGM/adapter/adapter_model.safetensors" ]; then
  G=$(wait_gpu 24000); say "  SFT GPU:$G"
  HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$G \
    INJECT_TYPES=1 INJECT_DEFS=1 RERANK_PREMISES=1 \
    python3 -m tactic_gen.grpo_train --rollouts "$GOLD" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$AUGM/adapter" --sft --kl_beta 0.0 \
    --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$AUGM/" 2>/dev/null
fi
say "  SFT: $([ -f "$AUGM/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)"
[ -f "$AUGM/adapter/adapter_model.safetensors" ] || { say "SFT 실패 — 중단"; exit 1; }

# ── 2) 평가: augmented SFT (test1191, augmented env, w2 @120s) ──
say "▶2 평가 augmented SFT (test1191 @120s w2, INJECT env)"
GPUS=$(wait_gpus 13000)
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$AUGM/adapter INJECT_TYPES=1 INJECT_DEFS=1 RERANK_PREMISES=1 \
  python3 scripts/run_all.py --alias rango-grpo --idx-file "$TEST" --timeout 120 --gpus "$GPUS" --workers 2 \
  --out all_results/aug_bs2_sft --description "augmented SFT test1191" >> "$LOG" 2>&1
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
say "  ★ augmented SFT: $(sumline all_results/aug_bs2_sft)"
say "     비교(비증강 SFT): 324/1191 (27.2%)"
say "=== AUG_BS2_DONE ==="
