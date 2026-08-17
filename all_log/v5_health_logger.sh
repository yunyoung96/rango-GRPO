#!/bin/bash
# 5분마다 학습 건강검진을 기록만 한다(중단은 감독이 담당).
cd /app/coq-modeling || exit 1
while true; do
  OUT=$(python3 scripts/v5_health.py all_log/ft_qwen3b_v5.log 2>&1)
  echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $OUT" >> all_log/v5_health.log
  sleep 300
done
