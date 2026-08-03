#!/bin/bash
# tactic-단위 opener(retrieval+후보+NMD) 신규 파이프라인 (GPU 여유 대기 + 외부유저 폴백).
#   Stage0 데이터 → Stage1 opener SFT(7B) → Stage2 opener-tac 롤아웃(executor=subgoal모델) → Stage3 GRPO.
#   각 GPU 스테이지는 **여유 GPU를 기다렸다가** 실행(외부 버스트에 안 죽음). 플래그면 GPU1 선호.
cd /app/coq-modeling || exit 1
LOG=all_log/opener_tac.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
QWEN=Qwen/Qwen2.5-Coder-7B-Instruct
OPENER=models/opener-7b-tac/adapter
EXECU=models/rango-grpo-subgoal-bs2/adapter   # ★ subgoal rollout로 update된 모델(닫기 학습)
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
FINAL=models/rango-opener-tac-grpo
ROLL=data/grpo_rollouts/opener_tac_pipe.jsonl
ROLL_IDX=/tmp/roll100_idx.txt
PORT=8131; URL=http://127.0.0.1:$PORT
SRVLOG=all_log/opener_tac_server.log

freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
# ★ GPU1 전용 (사용자 지시). GPU1 여유를 기다려 항상 1 반환. GPU0은 절대 안 씀.
wait_gpu(){
  local need=${1:-28000} waited=0
  while :; do
    local f1=$(freemem 1); f1=${f1:-0}
    [ "$f1" -ge "$need" ] && { echo 1; return; }
    [ $waited -ge 5400 ] && { echo 1; return; }   # 90분 캡
    sleep 20; waited=$((waited+20))
  done
}
# 롤아웃도 GPU1 전용.
wait_gpus(){ wait_gpu "${1:-14000}" >/dev/null; echo 1; }

# ── Stage0: 데이터 ──
if [ ! -s data/grpo_rollouts/opener_tac.jsonl ]; then
  say "Stage0: 데이터 빌드"; python3 scripts/build_opener_tac_data.py >> "$LOG" 2>&1
fi
say "Stage0 완료: $(wc -l < data/grpo_rollouts/opener_tac.jsonl) 예시"

# ── Stage1: opener SFT (7B) — 여유 GPU 기다렸다 실행, 최대 4회 ──
for try in 1 2 3 4; do
  [ -f "$OPENER/adapter_model.safetensors" ] && break
  G=$(wait_gpu 26000); say "Stage1: opener-tac SFT (GPU$G, try$try)"
  HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$G python3 scripts/train_opener_tac.py \
    --save "$OPENER" --epochs 5 --max_len 3072 >> "$LOG" 2>&1
  [ -f "$OPENER/adapter_model.safetensors" ] || { say "  Stage1 try$try 실패(OOM/양보?) → 대기 후 재시도"; sleep 30; }
done
[ -f "$OPENER/adapter_model.safetensors" ] || { say "Stage1 최종 실패 — 중단"; exit 1; }
say "Stage1 완료: OK"

# ── Stage2: opener-tac 롤아웃 (executor=subgoal모델, opener 매스텝+NMD, hedge) ──
start_srv(){ pkill -9 -f 'planner_server.py' 2>/dev/null; sleep 3; : > "$SRVLOG"
  local G=$(wait_gpu 16000)
  HF_HUB_OFFLINE=1 PLANNER_ADAPTER=$OPENER PLANNER_TAC=1 CUDA_VISIBLE_DEVICES=$G \
    python3 src/model_deployment/planner_server.py "$QWEN" "$PORT" >> "$SRVLOG" 2>&1 &
  SRV=$!; for i in $(seq 1 90); do grep -q READY "$SRVLOG" 2>/dev/null && break; sleep 5; done
  grep -q READY "$SRVLOG" 2>/dev/null && say "  opener-tac 서버 READY(GPU$G)" || say "  ✗ opener 서버 실패"; }
if [ ! -s "$ROLL" ]; then
  say "Stage2: opener-tac 롤아웃 (100 theorem, executor=subgoal모델, tac+NMD, hedge)"
  start_srv
  GPUS=$(wait_gpus 14000)
  say "  롤아웃 GPU: $GPUS"
  HF_HUB_OFFLINE=1 EXEC_ADAPTER=$EXECU PLANNER_FIRST_URL=$URL PLANNER_EVERY=1 PLANNER_HEDGE=1 \
    ROLLOUT_OUT=$ROLL ROLLOUT_RETRY=1 \
    python3 scripts/run_all.py --alias grpo-rollout-pf --idx-file "$ROLL_IDX" --timeout 400 --gpus "$GPUS" --workers 4 >> "$LOG" 2>&1
  kill -9 "$SRV" 2>/dev/null; pkill -9 -f 'planner_server.py' 2>/dev/null; pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 5
fi
python3 - >> "$LOG" 2>&1 <<'PY'
import json,os
F='data/grpo_rollouts/opener_tac_pipe.jsonl'
rows=[json.loads(l) for l in open(F)] if os.path.exists(F) else []
a=m=d=0;ts=ta=0
for g in rows:
    ns=sum(1 for x in g['attempts'] if x.get('reward',0)>0);ta+=len(g['attempts']);ts+=ns
    if ns==0:d+=1
    elif ns==len(g['attempts']):a+=1
    else:m+=1
n=max(len(rows),1)
print(f"[opener-tac 롤아웃] {len(rows)}그룹 | mixed {m}({100*m/n:.0f}%) dead {d} | attempt {100*ts/max(ta,1):.1f}% (plain 27%/34%, opener-once 30%/33%)")
PY
say "Stage2 완료(mixed 로그 참조)"

# ── Stage3: GRPO (init=subgoal모델) ──
if [ ! -f "$FINAL/adapter/adapter_model.safetensors" ] && [ -s "$ROLL" ]; then
  for try in 1 2 3 4; do
    [ -f "$FINAL/adapter/adapter_model.safetensors" ] && break
    G=$(wait_gpu 30000); say "Stage3: GRPO (init=subgoal모델, GPU$G, try$try)"
    HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$G python3 -m tactic_gen.grpo_train \
      --rollouts "$ROLL" --model_name "$BASE" --init_adapter "$EXECU" --collator_conf "$CONF" \
      --max_len 3072 --save_dir "$FINAL/adapter" --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
    [ -f "$FINAL/adapter/adapter_model.safetensors" ] || { say "  Stage3 try$try 실패 → 대기 후 재시도"; sleep 30; }
  done
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$FINAL/" 2>/dev/null
fi
say "Stage3 완료: $([ -f "$FINAL/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)"
say "=== PIPELINE 완료 OTAC_DONE ==="
