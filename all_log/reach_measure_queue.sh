#!/bin/bash
# [값싼 도달성 측정] once-v2 opener를 EVERY(재귀 per-state)로 300 train에 돌려
#   gold s1(leaf) 진입상태 도달률 측정 → executor(cascade-s0 16.7%, §10)와 정면 비교.
#   질문: 재귀 opener가 cascade 학습 leaf 상태에 더 잘 도달하나? (예 → per-state opener 재학습 가치)
#   mt_probe(=600s 뒤) 완료 후 자동 실행.
cd /app/coq-modeling || exit 1
LOG=all_log/reach_measure.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
QWEN=Qwen/Qwen2.5-Coder-7B-Instruct
OPENER=models/opener-7b-once-v2/adapter
EXECU=models/rango-grpo-subgoal-bs2/adapter
TRAIN=data/compcert_bs2_train_idx.txt
S1=data/grpo_rollouts/rango-grpo-cascade-s1_s1.jsonl
ROLL=data/grpo_rollouts/reach_opener_every.jsonl
REPORT=all_log/docs/grpo/OPENER_REACH_RESULT.md
PORT=8137; URL=http://127.0.0.1:$PORT
SRVLOG=all_log/reach_server.log
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
wait_gpu(){ local need=${1:-16000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ] && { echo 0;return; }
  [ "$f1" -ge "$need" ] && { echo 1;return; }; [ $w -ge 7200 ]&&{ echo 1;return; }; sleep 30;w=$((w+30)); done; }
wait_gpus(){ local need=${1:-13000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  local g=""; [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ]&&g="0"; [ "$f1" -ge "$need" ]&&g="${g:+$g,}1"
  [ -n "$g" ]&&{ echo "$g";return; }; [ $w -ge 7200 ]&&{ echo 1;return; }; sleep 30;w=$((w+30)); done; }
start_srv(){ pkill -9 -f 'planner_server.py' 2>/dev/null; sleep 3; : > "$SRVLOG"
  local G=$(wait_gpu 16000)
  HF_HUB_OFFLINE=1 PLANNER_ADAPTER=$OPENER PLANNER_TAC=1 CUDA_VISIBLE_DEVICES=$G \
    python3 src/model_deployment/planner_server.py "$QWEN" "$PORT" >> "$SRVLOG" 2>&1 &
  for i in $(seq 1 90); do grep -q READY "$SRVLOG" 2>/dev/null && break; sleep 5; done
  grep -q READY "$SRVLOG" 2>/dev/null && say "  opener 서버 READY(GPU$G)" || { say "  ✗ 서버 실패"; return 1; }; }

# ── 1) mt_probe(600s 뒤) 완료 대기 ──
say "mt_probe(=600s 뒤) 완료 대기 (MT_PROBE_DONE)..."
S=$SECONDS
while :; do
  grep -q 'MT_PROBE_DONE' all_log/mt_probe.log 2>/dev/null && break
  sleep 60; [ $((SECONDS-S)) -ge 54000 ] && { say "대기 타임아웃(15h) — 그래도 진행"; break; }
done
say "→ 도달성 측정 시작"
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; pkill -9 -f 'planner_server.py' 2>/dev/null; sleep 5

# ── 2) opener-EVERY(재귀) 롤아웃, 300 train, state 기록 ──
if [ ! -s "$ROLL" ]; then
  start_srv || { say "서버 실패 — 중단"; exit 1; }
  GPUS=$(wait_gpus 13000); say "opener-EVERY 롤아웃 (GPU $GPUS, 300정리, PLANNER_EVERY, hedge off)"
  HF_HUB_OFFLINE=1 EXEC_ADAPTER=$EXECU PLANNER_FIRST_URL=$URL PLANNER_EVERY=1 \
    ROLLOUT_OUT=$ROLL ROLLOUT_RETRY=1 \
    python3 scripts/run_all.py --alias grpo-rollout-pf --idx-file "$TRAIN" \
    --timeout 200 --gpus "$GPUS" --workers 4 >> "$LOG" 2>&1
  pkill -9 -f 'planner_server.py' 2>/dev/null; pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 3
fi
NG=$([ -f "$ROLL" ] && wc -l < "$ROLL" || echo 0)
say "롤아웃 완료: $NG 그룹"

# ── 3) 도달성 측정 → MD ──
if [ "$NG" -ge 1 ]; then
  python3 scripts/measure_opener_reach.py "$S1" \
    data/grpo_rollouts/rango-grpo-cascade-s0.jsonl \
    "$ROLL" \
    data/grpo_rollouts/opener_once_pipe2.jsonl > "$REPORT" 2>> "$LOG"
  cat "$REPORT" >> "$LOG"
  REACH=$(grep -i 'reach_opener_every' "$REPORT" | head -1)
  say "측정 완료 → $REPORT"
  say "opener-EVERY: $REACH  (vs executor cascade-s0 16.7%)"
else
  say "롤아웃 0 — 서버/실행 실패. 로그 확인 필요."
fi
say "=== REACH_MEASURE_DONE ==="
