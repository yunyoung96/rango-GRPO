#!/bin/bash
# TRAIN 저장소 복구를 감시한다 — 디스크·메모리·부하가 임계를 넘으면 **복구를 멈춘다**.
#
# 왜 필요한가: 2,268개 저장소를 받으면 수십 GB 이고, 과부하로 접속이 끊긴 전례가 있다.
# 임계에 닿으면 스스로 멈추고 로그에 남긴다(사람이 없어도 안전하게).
LOG="${1:-/tmp/recover_monitor.log}"
MAX_DISK_PCT=85        # /tmp 사용률 상한
MIN_FREE_G=60          # /tmp 최소 여유 GB
MAX_LOAD=10            # 1분 부하 상한 — VS Code 접속이 튕겨서 조였다
MIN_MEM_G=40           # 최소 여유 메모리 GB

while true; do
  ts=$(date -d "+9 hours" "+%m-%d %H:%M KST")
  dpct=$(df /tmp | awk 'NR==2{gsub("%","",$5); print $5}')
  dfree=$(df -BG /tmp | awk 'NR==2{gsub("G","",$4); print $4}')
  load=$(awk '{printf "%.1f", $1}' /proc/loadavg)
  memfree=$(free -g | awk 'NR==2{print $7}')
  nrepo=$(ls /tmp/coq-dataset/repos 2>/dev/null | wc -l)
  size=$(du -sh /tmp/coq-dataset/repos 2>/dev/null | cut -f1)
  nproc_r=$(pgrep -cf recover_train_repos)
  echo "$ts | repos $nrepo ($size) | disk ${dpct}% 여유${dfree}G | load $load | mem 여유${memfree}G | 복구프로세스 $nproc_r" >> "$LOG"

  stop=""
  [ "$dpct" -ge "$MAX_DISK_PCT" ] && stop="디스크 사용률 ${dpct}% ≥ ${MAX_DISK_PCT}%"
  [ "$dfree" -le "$MIN_FREE_G" ] && stop="디스크 여유 ${dfree}G ≤ ${MIN_FREE_G}G"
  [ "$memfree" -le "$MIN_MEM_G" ] && stop="메모리 여유 ${memfree}G ≤ ${MIN_MEM_G}G"
  awk -v l="$load" -v m="$MAX_LOAD" 'BEGIN{exit !(l>m)}' && stop="부하 $load > $MAX_LOAD"

  if [ -n "$stop" ]; then
    echo "$ts | ★ 임계 초과($stop) → 복구 중단" >> "$LOG"
    pkill -f recover_train_repos
    sleep 300                       # 진정될 시간을 준다
  fi
  sleep 120
done
