#!/bin/bash
# once-v2 GRPO+eval resume (롤아웃 287·opener 이미 있음). GRPO opener-step-skip 수정 후.
cd /app/coq-modeling || exit 1
LOG=all_log/once_v2.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
EXECU=models/rango-grpo-subgoal-bs2/adapter
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
FINAL=models/rango-opener-once-v2-grpo
ROLL=data/grpo_rollouts/once_v2_pipe.jsonl
RAND=data/compcert_bs2_rand200_idx.txt
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'),'(',round(100*d.get('success',0)/max(d.get('done',1),1),1),'%)')" 2>/dev/null; }
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
wait_gpu(){ local need=${1:-24000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ] && { echo 0;return; }
  [ "$f1" -ge "$need" ] && { echo 1;return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 20;w=$((w+20)); done; }
wait_gpus(){ local need=${1:-14000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  local g=""; [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ]&&g="0"; [ "$f1" -ge "$need" ]&&g="${g:+$g,}1"
  [ -n "$g" ]&&{ echo "$g";return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 20;w=$((w+20)); done; }
G=$(wait_gpu 24000); say "resume Stage3: GRPO (GPU$G, opener-step-skip fix)"
HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$G python3 -m tactic_gen.grpo_train \
  --rollouts "$ROLL" --model_name "$BASE" --init_adapter "$EXECU" --collator_conf "$CONF" \
  --max_len 3072 --save_dir "$FINAL/adapter" --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$FINAL/" 2>/dev/null
say "resume Stage3 완료: $([ -f "$FINAL/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)"
if [ -f "$FINAL/adapter/adapter_model.safetensors" ]; then
  GPUS=$(wait_gpus 14000); say "resume Stage4: rand200 w2 (GPU $GPUS)"
  HF_HUB_OFFLINE=1 EXEC_ADAPTER=$FINAL/adapter python3 scripts/run_all.py --alias rango-grpo \
    --idx-file "$RAND" --timeout 300 --gpus "$GPUS" --workers 2 --out all_results/once_v2_final --description "once-v2 final" >> "$LOG" 2>&1
  pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
  say "once-v2 최종 rand200: $(sumline all_results/once_v2_final)  (subgoal 30.5% @300s)"
fi
say "=== RESUME 완료 ONCEV2_DONE ==="
