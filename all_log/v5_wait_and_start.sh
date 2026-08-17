#!/bin/bash
# GPU 4장이 **연속으로 비어 있으면** 3B v5 학습을 시작한다.
#
# 왜 대기하나: 같은 머신의 다른 세션이 7B 학습을 자동 재시작한다. 그 프로세스가 GPU 를
#   물고 있으면 우리 4랭크 중 하나가 메모리 부족으로 죽고(실측: rank2 exitcode 1),
#   torchrun 이 나머지를 SIGTERM 으로 정리해 매번 2~3분 만에 종료됐다.
#   → 4장 모두 여유 40GB 이상인 상태가 3회 연속(=2분) 확인되면 시작한다.
cd /app/coq-modeling || exit 1
set -u
LOG=all_log/v5_wait_and_start.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
say "===== GPU 대기 시작 (4장 × 여유 40GB 이상) ====="
ok=0
while [ "$ok" -lt 3 ]; do
  n=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | awk '$1>40000{c++} END{print c+0}')
  if [ "$n" -ge 4 ]; then
    ok=$((ok+1)); say "  4장 여유 확인 ($ok/3)"
  else
    [ "$ok" -gt 0 ] && say "  점유 감지 — 카운터 초기화 (여유 GPU $n/4)"
    ok=0
  fi
  sleep 40
done
say "GPU 확보 — v5 학습 시작"
setsid nohup bash all_log/v5_supervisor.sh > /dev/null 2>&1 < /dev/null &
sleep 5
setsid nohup bash all_log/v5_health_logger.sh > /dev/null 2>&1 < /dev/null &
say "===== 시작 완료 ====="
