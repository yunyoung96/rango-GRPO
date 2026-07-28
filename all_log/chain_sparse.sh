#!/bin/bash
set -u
WAIT=${WAIT:?}
echo "[$(date '+%m-%d %H:%M')] sparse 재검증 대기 (master ${WAIT} 종료 후)" | tee -a all_log/sparse_revisit.log
while kill -0 "$WAIT" 2>/dev/null; do sleep 120; done
echo "[$(date '+%m-%d %H:%M')] master 종료 → sparse 재검증 시작" | tee -a all_log/sparse_revisit.log
exec bash all_log/run_sparse_revisit.sh
