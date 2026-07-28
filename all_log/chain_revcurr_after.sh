#!/bin/bash
# revcurr 을 현재 priority 체인(LUFFY-on-fix→backward-prm→retry-prm→fix@180) 완료 후 실행.
set -u
WAIT_PID=${WAIT_PID:?}
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a all_log/chain_revcurr_after.log; }
say "대기: priority 체인(${WAIT_PID}) 완료까지 (그 후 revcurr 실행)"
while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 120; done
say "priority 체인 종료 확인 → revcurr 시작"
bash all_log/run_revcurr.sh
say "===== revcurr 완료 ====="
