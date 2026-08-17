#!/bin/bash
# v6 학습 감독 — 죽으면 마지막 체크포인트에서 재개 + **발산 자동 감지**.
#
# 왜 발산 감지가 필요한가: lr=1e-3(rango 1.3B 값)로 3B 를 돌렸더니 step 245 에서
#   grad_norm 64.6 으로 터지며 loss 1.07 → 4.6 으로 발산했고, **그대로 9.5시간을 돌았다**.
#   loss 가 초기 최저값의 2배를 넘긴 채 오래 유지되면 즉시 멈추고 알린다.
cd /app/coq-modeling || exit 1
set -u
LOG=all_log/ft_qwen3b_v6.log
SUP=all_log/v6_supervisor.log
OUT=models/rango-qwen3b-v6-ft
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$SUP"; }

# 백그라운드 감시: 5분마다 loss 를 보고 발산이면 학습을 죽인다
watch_divergence(){
  while true; do
    sleep 300
    [ -f "$LOG" ] || continue
    OUT=$(python3 scripts/v5_health.py "$LOG" 2>&1); rc=$?
    echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $OUT" >> all_log/v6_health.log
    if [ $rc -eq 7 ]; then
      say "★ 이상 감지 — 학습 중단: $OUT"
      pkill -9 -f train_decoder
      touch /tmp/v6_diverged
      return
    fi
  done
}
watch_divergence &
WATCH=$!
trap "kill $WATCH 2>/dev/null" EXIT

FAST=0
say "===== v6 감독 시작 (Qwen2.5-Coder-3B + v6) ====="
for try in $(seq 1 50); do
  [ -f /tmp/v6_diverged ] && { say "발산 플래그 존재 — 감독 종료"; break; }
  if [ -f "$OUT/adapter_model.safetensors" ]; then say "완주 감지 — 종료"; break; fi
  # ★ GPU 중단 대비: GPU 가 안 보이면 재시도를 소모하지 말고 **기다린다**.
  #   (예전 로직은 실패-30초-실패를 반복해 50회를 25분만에 소진했다)
  waited=0
  while ! nvidia-smi -L > /dev/null 2>&1; do
    [ $((waited % 10)) -eq 0 ] && say "  GPU 없음 — 대기 중 ($((waited*60/60))분)"
    sleep 60; waited=$((waited+1))
  done
  # ★ 좀비 GPU 점유 정리 — 죽은 학습의 잔재가 GPU 를 물고 있으면 새 학습이 OOM 으로
  #   즉사하고 감독이 무한 재시도한다(실제로 75GB×2 좀비 때문에 39회 크래시 루프).
  for _p in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | sort -u); do
    if ! ps -p "$_p" -o args= 2>/dev/null | grep -qE "train_v6|train_decoder"; then continue; fi
    say "  ★ 좀비 학습 프로세스 $_p 정리"
    kill -9 "$_p" 2>/dev/null
  done
  sleep 5

  LAST=$(ls -d "$OUT"/checkpoint-* 2>/dev/null | sed 's/.*checkpoint-//' | sort -rn | head -1)
  say "시도 $try (마지막 체크포인트: ${LAST:-없음})"
  _t0=$(date +%s)
  bash all_log/run_qwen3b_v6.sh
  say "  종료 rc=$?"
  # ★ 크래시 루프 감지: 시작 직후(<5분) 죽는 일이 3회 연속이면 원인이 환경에 있다.
  #   50회를 조용히 소모하는 대신 멈추고 알린다(실제로 좀비 OOM 으로 39회 낭비).
  _now=$(date +%s); _dur=$((_now - _t0))
  if [ "$_dur" -lt 300 ]; then FAST=$((FAST+1)); else FAST=0; fi
  if [ "$FAST" -ge 3 ]; then
    say "★ 5분 내 즉사 3회 연속 — 환경 문제로 판단, 감독 중단(수동 확인 필요)"
    exit 1
  fi
  if ! grep -aqE "loss': '[0-9]" "$LOG"; then
    say "  ★ loss 기록이 전혀 없음 — 설정 문제로 판단, 감독 중단"; exit 1
  fi
  sleep 30
done
say "===== v6 감독 종료 ====="
