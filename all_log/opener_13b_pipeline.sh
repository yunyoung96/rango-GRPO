#!/bin/bash
# 1.3B opener 전체 파이프라인 (opener-tac과 동일하되 opener=DeepSeek-Coder-1.3B). GPU0+1 둘 다 사용.
#   Stage1 opener SFT(1.3B) → Stage2 롤아웃(executor=subgoal모델) → Stage3 GRPO → Stage4 rand200 eval.
#   probe가 만든 models/opener-1.3b-tac 재활용(있으면 SFT 스킵).
cd /app/coq-modeling || exit 1
LOG=all_log/opener_13b_pipe.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
M13=deepseek-ai/deepseek-coder-1.3b-instruct
OPENER=models/opener-1.3b-tac/adapter
EXECU=models/rango-grpo-subgoal-bs2/adapter
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
FINAL=models/rango-opener13-tac-grpo
SUBG=models/rango-grpo-subgoal-bs2/adapter
ROLL=data/grpo_rollouts/opener13_tac_pipe.jsonl
ROLL_IDX=/tmp/roll100_idx.txt
RAND=data/compcert_bs2_rand200_idx.txt
PORT=8132; URL=http://127.0.0.1:$PORT
SRVLOG=all_log/opener13_server.log
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'),'(',round(100*d.get('success',0)/max(d.get('done',1),1),1),'%)')" 2>/dev/null; }
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
# 여유 단일 GPU. 외부 플래그(/tmp/gpu0_foreign) 있으면 GPU0 안 씀(GPU1만).
wait_gpu(){ local need=${1:-20000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ] && { echo 0;return; }
  [ "$f1" -ge "$need" ] && { echo 1;return; }
  [ $w -ge 5400 ] && { echo 1;return; }; sleep 20;w=$((w+20)); done; }
# 롤아웃/eval용 GPU 리스트. 외부 플래그면 GPU0 제외(GPU1만).
wait_gpus(){ local need=${1:-12000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  local g=""; [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ]&&g="0"; [ "$f1" -ge "$need" ]&&g="${g:+$g,}1"
  [ -n "$g" ]&&{ echo "$g";return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 20;w=$((w+20)); done; }

# ── Stage1: opener 1.3B SFT (probe가 만들었으면 스킵) ──
if [ ! -f "$OPENER/adapter_model.safetensors" ]; then
  G=$(wait_gpu 12000); say "Stage1: opener 1.3B SFT (GPU$G)"
  HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=$G python3 scripts/train_opener_tac.py \
    --model "$M13" --save "$OPENER" --epochs 4 --max_len 3072 >> "$LOG" 2>&1
fi
[ -f "$OPENER/adapter_model.safetensors" ] || { say "Stage1 실패 — 중단"; exit 1; }
say "Stage1 완료: opener-1.3b OK (재활용)"

# ── Stage2: 롤아웃 (opener=1.3b, executor=subgoal, tac+NMD, hedge) 양쪽 GPU ──
start_srv(){ pkill -9 -f 'planner_server.py' 2>/dev/null; sleep 3; : > "$SRVLOG"
  local G=$(wait_gpu 6000)
  HF_HUB_OFFLINE=1 PLANNER_ADAPTER=$OPENER PLANNER_TAC=1 CUDA_VISIBLE_DEVICES=$G \
    python3 src/model_deployment/planner_server.py "$M13" "$PORT" >> "$SRVLOG" 2>&1 &
  SRV=$!; for i in $(seq 1 90); do grep -q READY "$SRVLOG" 2>/dev/null && break; sleep 5; done
  grep -q READY "$SRVLOG" 2>/dev/null && say "  opener-1.3b 서버 READY(GPU$G)" || say "  ✗ 서버 실패"; }
if [ ! -s "$ROLL" ]; then
  say "Stage2: 롤아웃 (100 theorem, opener=1.3b, executor=subgoal, 양쪽 GPU)"
  start_srv
  GPUS=$(wait_gpus 12000); say "  롤아웃 GPU: $GPUS"
  HF_HUB_OFFLINE=1 EXEC_ADAPTER=$EXECU PLANNER_FIRST_URL=$URL PLANNER_EVERY=1 PLANNER_HEDGE=1 \
    ROLLOUT_OUT=$ROLL ROLLOUT_RETRY=1 \
    python3 scripts/run_all.py --alias grpo-rollout-pf --idx-file "$ROLL_IDX" --timeout 400 --gpus "$GPUS" --workers 4 >> "$LOG" 2>&1
  kill -9 "$SRV" 2>/dev/null; pkill -9 -f 'planner_server.py' 2>/dev/null; pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 5
fi
python3 - >> "$LOG" 2>&1 <<'PY'
import json,os
F='data/grpo_rollouts/opener13_tac_pipe.jsonl'
rows=[json.loads(l) for l in open(F)] if os.path.exists(F) else []
a=m=d=0;ts=ta=0
for g in rows:
    ns=sum(1 for x in g['attempts'] if x.get('reward',0)>0);ta+=len(g['attempts']);ts+=ns
    if ns==0:d+=1
    elif ns==len(g['attempts']):a+=1
    else:m+=1
n=max(len(rows),1)
print(f"[opener-1.3b 롤아웃] {len(rows)}그룹 | mixed {m}({100*m/n:.0f}%) dead {d} | attempt {100*ts/max(ta,1):.1f}% (opener-7b-tac 28%, plain 27%)")
PY
say "Stage2 완료"

# ── Stage3: GRPO (init=subgoal) ──
if [ ! -f "$FINAL/adapter/adapter_model.safetensors" ] && [ -s "$ROLL" ]; then
  G=$(wait_gpu 24000); say "Stage3: GRPO (init=subgoal, GPU$G)"
  HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$G python3 -m tactic_gen.grpo_train \
    --rollouts "$ROLL" --model_name "$BASE" --init_adapter "$EXECU" --collator_conf "$CONF" \
    --max_len 3072 --save_dir "$FINAL/adapter" --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$FINAL/" 2>/dev/null
fi
say "Stage3 완료: $([ -f "$FINAL/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)"

# ── Stage4: rand200 eval (opener 없이) 양쪽 GPU ──
if [ -f "$FINAL/adapter/adapter_model.safetensors" ]; then
  GPUS=$(wait_gpus 14000); say "Stage4: eval rand200 (GPU $GPUS)"
  [ -s all_results/otac13_final/summary.json ] || HF_HUB_OFFLINE=1 EXEC_ADAPTER=$FINAL/adapter \
    python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" --timeout 300 --gpus "$GPUS" --workers 2 \
    --out all_results/otac13_final --description "opener13 final" >> "$LOG" 2>&1
  pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
  say "  opener-1.3b 최종 rand200: $(sumline all_results/otac13_final)  (7B-tac 31.0%, subgoal 30.5%)"
fi
say "=== PIPELINE 완료 OTAC13_DONE ==="
