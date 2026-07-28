#!/bin/bash
set -u
WAIT_PID=${WAIT_PID:?}
echo "[$(date '+%m-%d %H:%M')] cross-repo GRPO 대기 (resume_all ${WAIT_PID} 종료 후)" | tee -a all_log/crossrepo_grpo.log
while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 120; done
echo "[$(date '+%m-%d %H:%M')] 선행 완료 → cross-repo GRPO 시작" | tee -a all_log/crossrepo_grpo.log
exec bash all_log/run_crossrepo_grpo.sh
