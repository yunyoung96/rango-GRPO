#!/bin/bash
# VinePPO 를 revcurr 뒤(=tail 체인 완료 후) 실행.
set -u
WAIT_PID=${WAIT_PID:?}
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a all_log/chain_vine_after.log; }
say "대기: tail 체인(${WAIT_PID}) 완료까지 (그 후 VinePPO 실행)"
while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 120; done
say "tail 체인 종료 확인 → VinePPO 시작"
bash all_log/run_vine.sh
say "===== VinePPO 완료 ====="
