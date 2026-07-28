#!/bin/bash
# 배치3(adaptprefix/fixdyn/bread) 을 vine 뒤(=chain_vine_after 완료 후) 실행.
set -u
WAIT_PID=${WAIT_PID:?}
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a all_log/chain_batch3_after.log; }
say "대기: vine 큐(${WAIT_PID}) 완료까지 (그 후 배치3 실행)"
while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 120; done
say "vine 큐 종료 확인 → 배치3 시작"
bash all_log/run_batch3.sh
say "===== 배치3 완료 ====="
