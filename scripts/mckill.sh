#!/bin/bash
# 정체 coqtop 컷 (학습용 저장소 tmp/tr 밑 coqtop 10분 상한(무상한 수집: 세션이 길어짐)). 정지: touch tmp/mckill.stop
while true; do
  [ -f /app/coq-modeling/tmp/mckill.stop ] && exit 0
  for p in $(ps -eo pid,etimes,args | awk '/coqto[p]/ && /tmp\/tr/ && $2>600 {print $1}'); do
    kill -9 $p 2>/dev/null && echo "[$(date -u -d '+9 hours' '+%H:%M')] killed $p"
  done
  sleep 60
done
