#!/bin/bash
# fix_contested(오염수습) 종료를 기다렸다가 SOTA 3종 평가를 GPU 독점으로 실행.
set -u
FIX_PID=${FIX_PID:?}
echo "[$(date '+%m-%d %H:%M')] SOTA3 대기 (fix_contested PID ${FIX_PID})" | tee -a all_log/sota3.log
while kill -0 "$FIX_PID" 2>/dev/null; do sleep 120; done
echo "[$(date '+%m-%d %H:%M')] 수습 종료 확인 → SOTA3 시작" | tee -a all_log/sota3.log
exec bash all_log/run_sota3.sh
