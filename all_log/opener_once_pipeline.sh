#!/bin/bash
# opener-once(with compound) 파이프라인 — opener가 전체 opening을 첫 한 번에(NMD까지) 다 하고 rango가 닫음.
#   7B, epoch 4. Stage1 SFT → Stage2 롤아웃(PLANNER_PRELOOP) → Stage3 GRPO → Stage4 eval.
#   train: GPU0+1 워커多. test: w2. 외부 GPU0 감지→GPU1만.
cd /app/coq-modeling || exit 1
LOG=all_log/opener_once.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
QWEN=Qwen/Qwen2.5-Coder-7B-Instruct
OPENER=models/opener-7b-once-comp/adapter    # ★ 첫 한번만 여는 opener(with compound)
EXECU=models/rango-grpo-subgoal-bs2/adapter
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
FINAL=models/rango-opener-once-comp-grpo
ROLL=data/grpo_rollouts/opener_once_pipe2.jsonl
ROLL_IDX=data/compcert_bs2_train_idx.txt
RAND=data/compcert_bs2_rand200_idx.txt
PORT=8133; URL=http://127.0.0.1:$PORT
SRVLOG=all_log/opener_once_server.log
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'),'(',round(100*d.get('success',0)/max(d.get('done',1),1),1),'%)')" 2>/dev/null; }
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
wait_gpu(){ local need=${1:-26000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ] && { echo 0;return; }
  [ "$f1" -ge "$need" ] && { echo 1;return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 20;w=$((w+20)); done; }
wait_gpus(){ local need=${1:-13000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  local g=""; [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ]&&g="0"; [ "$f1" -ge "$need" ]&&g="${g:+$g,}1"
  [ -n "$g" ]&&{ echo "$g";return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 20;w=$((w+20)); done; }

# ── Stage0: 데이터 ──
[ -s data/grpo_rollouts/opener_once.jsonl ] || python3 scripts/build_opener_once_data.py >> "$LOG" 2>&1
say "Stage0: $(wc -l < data/grpo_rollouts/opener_once.jsonl) 예시 (전체opening+NMD)"

# ── Stage1: opener 7B SFT (epoch 4) ──
if [ ! -f "$OPENER/adapter_model.safetensors" ]; then
  for try in 1 2 3; do
    [ -f "$OPENER/adapter_model.safetensors" ] && break
    G=$(wait_gpu 26000); say "Stage1: opener-once SFT 7B (GPU$G, ep4, try$try)"
    HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$G \
      python3 scripts/train_opener_tac.py --model "$QWEN" --data data/grpo_rollouts/opener_once.jsonl \
      --save "$OPENER" --epochs 4 --max_len 3072 >> "$LOG" 2>&1
    [ -f "$OPENER/adapter_model.safetensors" ] || { say "  try$try 실패 → 대기 재시도"; sleep 30; }
  done
fi
[ -f "$OPENER/adapter_model.safetensors" ] || { say "Stage1 실패 — 중단"; exit 1; }
say "Stage1 완료: OK"

# ── Stage2: 롤아웃 (PLANNER_PRELOOP: opener 전체opening 첫 한번 → rango) ──
start_srv(){ pkill -9 -f 'planner_server.py' 2>/dev/null; sleep 3; : > "$SRVLOG"
  local G=$(wait_gpu 16000)
  HF_HUB_OFFLINE=1 PLANNER_ADAPTER=$OPENER PLANNER_TAC=1 CUDA_VISIBLE_DEVICES=$G \
    python3 src/model_deployment/planner_server.py "$QWEN" "$PORT" >> "$SRVLOG" 2>&1 &
  SRV=$!; for i in $(seq 1 90); do grep -q READY "$SRVLOG" 2>/dev/null && break; sleep 5; done
  grep -q READY "$SRVLOG" 2>/dev/null && say "  opener-once 서버 READY(GPU$G)" || say "  ✗ 서버 실패"; }
if [ ! -s "$ROLL" ]; then
  say "Stage2: 롤아웃 (300 theorem, PLANNER_PRELOOP, executor=subgoal, hedge)"
  start_srv
  GPUS=$(wait_gpus 13000); say "  롤아웃 GPU: $GPUS"
  HF_HUB_OFFLINE=1 EXEC_ADAPTER=$EXECU PLANNER_FIRST_URL=$URL PLANNER_PRELOOP=1 PLANNER_HEDGE=1 \
    ROLLOUT_OUT=$ROLL ROLLOUT_RETRY=1 \
    python3 scripts/run_all.py --alias grpo-rollout-pf --idx-file "$ROLL_IDX" --timeout 400 --gpus "$GPUS" --workers 4 >> "$LOG" 2>&1
  kill -9 "$SRV" 2>/dev/null; pkill -9 -f 'planner_server.py' 2>/dev/null; pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 5
fi
python3 - >> "$LOG" 2>&1 <<'PY'
import json,os
F='data/grpo_rollouts/opener_once_pipe2.jsonl'
rows=[json.loads(l) for l in open(F)] if os.path.exists(F) else []
a=m=d=0;ts=ta=0
for g in rows:
    ns=sum(1 for x in g['attempts'] if x.get('reward',0)>0);ta+=len(g['attempts']);ts+=ns
    if ns==0:d+=1
    elif ns==len(g['attempts']):a+=1
    else:m+=1
n=max(len(rows),1)
print(f"[opener-once-comp 롤아웃] {len(rows)}그룹 | mixed {m}({100*m/n:.0f}%) dead {d} | attempt {100*ts/max(ta,1):.1f}% (opener-tac 28%, plain 27%)")
PY
say "Stage2 완료"

# ── Stage3: GRPO ──
if [ ! -f "$FINAL/adapter/adapter_model.safetensors" ] && [ -s "$ROLL" ]; then
  G=$(wait_gpu 24000); say "Stage3: GRPO (init=subgoal, GPU$G)"
  HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$G python3 -m tactic_gen.grpo_train \
    --rollouts "$ROLL" --model_name "$BASE" --init_adapter "$EXECU" --collator_conf "$CONF" \
    --max_len 3072 --save_dir "$FINAL/adapter" --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$FINAL/" 2>/dev/null
fi
say "Stage3 완료: $([ -f "$FINAL/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)"

# ── Stage4: eval rand200 w2 (opener 없이) ──
if [ -f "$FINAL/adapter/adapter_model.safetensors" ]; then
  GPUS=$(wait_gpus 14000); say "Stage4: eval rand200 w2 (GPU $GPUS)"
  [ -s all_results/oonce_final/summary.json ] || HF_HUB_OFFLINE=1 EXEC_ADAPTER=$FINAL/adapter \
    python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" --timeout 300 --gpus "$GPUS" --workers 2 \
    --out all_results/oonce_final --description "opener-once-comp final" >> "$LOG" 2>&1
  pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
  say "  opener-once-comp 최종 rand200: $(sumline all_results/oonce_final)  (opener-tac 31.0%, subgoal 30.5%)"
fi
say "=== PIPELINE 완료 OONCE_DONE ==="
