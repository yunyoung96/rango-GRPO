#!/bin/bash
# opener-once v2 (버그 수정판) 자율 파이프라인.
#   원인: opener-once 데이터에 Proof/NMD 지배 → opener가 Proof후 바로 NMD(opening 안함).
#   수정: 데이터서 Proof 제외 + pre-loop이 Proof 직접(+no-progress 가드). → opener 재학습.
#   Stage0 데이터재생성 → Stage1 opener SFT재학습 → ★검증게이트(5정리) → 통과시 300롤→GRPO→rand200.
cd /app/coq-modeling || exit 1
LOG=all_log/once_v2.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
QWEN=Qwen/Qwen2.5-Coder-7B-Instruct
OPENER=models/opener-7b-once-v2/adapter    # ★ 새 이름(재학습, Proof 제외 데이터)
EXECU=models/rango-grpo-subgoal-bs2/adapter
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
FINAL=models/rango-opener-once-v2-grpo
ROLL=data/grpo_rollouts/once_v2_pipe.jsonl
TRAIN=data/compcert_bs2_train_idx.txt
RAND=data/compcert_bs2_rand200_idx.txt
PORT=8135; URL=http://127.0.0.1:$PORT
SRVLOG=all_log/once_v2_server.log
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'),'(',round(100*d.get('success',0)/max(d.get('done',1),1),1),'%)')" 2>/dev/null; }
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
wait_gpu(){ local need=${1:-26000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ] && { echo 0;return; }
  [ "$f1" -ge "$need" ] && { echo 1;return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 20;w=$((w+20)); done; }
wait_gpus(){ local need=${1:-13000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  local g=""; [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ]&&g="0"; [ "$f1" -ge "$need" ]&&g="${g:+$g,}1"
  [ -n "$g" ]&&{ echo "$g";return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 20;w=$((w+20)); done; }
start_srv(){ pkill -9 -f 'planner_server.py' 2>/dev/null; sleep 3; : > "$SRVLOG"
  local G=$(wait_gpu 16000)
  HF_HUB_OFFLINE=1 PLANNER_ADAPTER=$OPENER PLANNER_TAC=1 CUDA_VISIBLE_DEVICES=$G \
    python3 src/model_deployment/planner_server.py "$QWEN" "$PORT" >> "$SRVLOG" 2>&1 &
  SRV=$!; for i in $(seq 1 90); do grep -q READY "$SRVLOG" 2>/dev/null && break; sleep 5; done
  grep -q READY "$SRVLOG" 2>/dev/null && say "  서버 READY(GPU$G)" || say "  ✗ 서버 실패"; }

# ── Stage0: 데이터 재생성 (Proof 제외판) ──
python3 scripts/build_opener_once_data.py >> "$LOG" 2>&1
say "Stage0: $(wc -l < data/grpo_rollouts/opener_once.jsonl) 예시 (Proof 제외)"

# ── Stage1: opener 재학습 (ep4) ──
if [ ! -f "$OPENER/adapter_model.safetensors" ]; then
  for try in 1 2 3; do
    [ -f "$OPENER/adapter_model.safetensors" ] && break
    G=$(wait_gpu 26000); say "Stage1: opener SFT 재학습 (GPU$G, ep4, try$try)"
    HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$G \
      python3 scripts/train_opener_tac.py --model "$QWEN" --data data/grpo_rollouts/opener_once.jsonl \
      --save "$OPENER" --epochs 4 --max_len 3072 >> "$LOG" 2>&1
    [ -f "$OPENER/adapter_model.safetensors" ] || { say "  try$try 실패 → 재시도"; sleep 30; }
  done
fi
[ -f "$OPENER/adapter_model.safetensors" ] || { say "Stage1 실패 — 중단"; exit 1; }
say "Stage1 완료: OK"

# ── ★검증 게이트: 5정리 롤아웃 → opener가 실제 opening(intros/destruct) 내나 ──
say "검증: 5정리 롤아웃 (opener가 opening 내는지)"
head -5 "$TRAIN" > /tmp/v2_5idx.txt
start_srv
GPUS=$(wait_gpus 13000)
rm -f /tmp/v2_5roll.jsonl
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$EXECU PLANNER_FIRST_URL=$URL PLANNER_PRELOOP=1 PLANNER_HEDGE=1 \
  ROLLOUT_OUT=/tmp/v2_5roll.jsonl ROLLOUT_RETRY=1 \
  python3 scripts/run_all.py --alias grpo-rollout-pf --idx-file /tmp/v2_5idx.txt --timeout 300 --gpus "$GPUS" --workers 2 >> "$LOG" 2>&1
pkill -9 -f 'planner_server.py' 2>/dev/null; pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 5
PASS=$(python3 - <<'PY'
import json,re
try: rows=[json.loads(l) for l in open('/tmp/v2_5roll.jsonl')]
except: print("FAIL"); raise SystemExit
def kw(t):
    m=re.match(r'\s*([a-z_]+)',(t or '').strip().lstrip('\n'));return m.group(1) if m else ''
opener_att=real=0
for g in rows:
    for a in g['attempts']:
        ops=[s for s in a['steps'] if s.get('planner_opening')]
        if not ops: continue
        opener_att+=1
        if any(kw(s.get('tactic','')) in ('intros','intro','destruct','induction','inv','unfold','simpl','revert') for s in ops): real+=1
print("PASS" if (opener_att>0 and real>0) else "FAIL")
PY
)
say "검증 판정: $PASS (opener가 실제 opening 내는지)"
if [ "$PASS" != "PASS" ]; then say "★검증 실패 — opener 여전히 opening 안함. 300 중단(낭비방지). 수동확인 필요."; exit 1; fi

# ── Stage2: 300 롤아웃 ──
if [ ! -s "$ROLL" ]; then
  say "Stage2: 300 롤아웃 (PLANNER_PRELOOP, executor=subgoal)"
  start_srv
  GPUS=$(wait_gpus 13000); say "  롤아웃 GPU: $GPUS"
  HF_HUB_OFFLINE=1 EXEC_ADAPTER=$EXECU PLANNER_FIRST_URL=$URL PLANNER_PRELOOP=1 PLANNER_HEDGE=1 \
    ROLLOUT_OUT=$ROLL ROLLOUT_RETRY=1 \
    python3 scripts/run_all.py --alias grpo-rollout-pf --idx-file "$TRAIN" --timeout 400 --gpus "$GPUS" --workers 4 >> "$LOG" 2>&1
  pkill -9 -f 'planner_server.py' 2>/dev/null; pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 5
fi
python3 - >> "$LOG" 2>&1 <<'PY'
import json,os
F='data/grpo_rollouts/once_v2_pipe.jsonl'
rows=[json.loads(l) for l in open(F)] if os.path.exists(F) else []
a=m=d=0;ts=ta=0
for g in rows:
    ns=sum(1 for x in g['attempts'] if x.get('reward',0)>0);ta+=len(g['attempts']);ts+=ns
    if ns==0:d+=1
    elif ns==len(g['attempts']):a+=1
    else:m+=1
n=max(len(rows),1)
print(f"[once-v2 롤아웃] {len(rows)}그룹 | mixed {m}({100*m/n:.0f}%) dead {d} | attempt {100*ts/max(ta,1):.1f}% (plain 26%)")
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

# ── Stage4: rand200 w2 ──
if [ -f "$FINAL/adapter/adapter_model.safetensors" ]; then
  GPUS=$(wait_gpus 14000); say "Stage4: rand200 w2 (GPU $GPUS)"
  [ -s all_results/once_v2_final/summary.json ] || HF_HUB_OFFLINE=1 EXEC_ADAPTER=$FINAL/adapter \
    python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" --timeout 300 --gpus "$GPUS" --workers 2 \
    --out all_results/once_v2_final --description "once-v2 final" >> "$LOG" 2>&1
  pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
  say "  once-v2 최종 rand200: $(sumline all_results/once_v2_final)  (subgoal 30.5%, SFT→GRPO 37.5%@600s)"
fi
say "=== PIPELINE 완료 ONCEV2_DONE ==="
