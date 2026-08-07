#!/bin/bash
# ablation 4조건이 끝나면 → 이름필터 ON 평가로 이어간다(같은 GPU 순차 사용).
cd /app/coq-modeling || exit 1
LOG=all_log/queue_after_ablation.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
say "ablation 종료 대기"
gone=0
while :; do
  sleep 120
  if pgrep -f ablation_types.sh >/dev/null; then gone=0
  else gone=$((gone+1)); [ $gone -ge 3 ] && break; fi
done
say "ablation 종료 감지 → 이름필터 평가 시작"
bash all_log/eval_name_filter.sh
say "완료"
