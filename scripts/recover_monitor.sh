#!/bin/bash
# TRAIN 저장소 복구를 감시한다 — 위험할 때만 멈춘다.
#
# ★ 설계 요점: **우리 작업의 몫**을 기준으로 삼는다.
#   전체 load 로 판단하면 다른 사용자의 학습 작업(관측: exp_retrieval_head 4개 +
#   train.py 2개 = 약 7코어) 때문에 우리 git clone 이 애먼 이유로 멈춘다.
#   우리 몫은 실측 0.6코어뿐이었다.
#   디스크·메모리는 실제 위험이므로 절대 기준을 유지한다.
LOG="${1:-/tmp/recover_monitor.log}"
MAX_DISK_PCT=85        # /tmp 사용률 상한
MIN_FREE_G=60          # /tmp 최소 여유 GB
MIN_MEM_G=40           # 최소 여유 메모리 GB
MAX_OURS_PCT=400       # **우리 프로세스** CPU 합 상한(%) = 4코어
MAX_LOAD=22            # 최후 안전망 (24코어)

ours_cpu() {
  local pids
  pids=$(pgrep -d, -f "hunt_assert|recover_train|coq-lsp|coqtop|research_" 2>/dev/null)
  [ -z "$pids" ] && { echo 0; return; }
  ps -o %cpu= -p "$pids" 2>/dev/null | awk '{s+=$1} END{printf "%.0f", s+0}'
}

while true; do
  ts=$(date -d "+9 hours" "+%m-%d %H:%M KST")
  dpct=$(df /tmp | awk 'NR==2{gsub("%","",$5); print $5}')
  dfree=$(df -BG /tmp | awk 'NR==2{gsub("G","",$4); print $4}')
  load=$(awk '{printf "%.1f", $1}' /proc/loadavg)
  memfree=$(free -g | awk 'NR==2{print $7}')
  nrepo=$(ls /tmp/coq-dataset/repos 2>/dev/null | wc -l)
  size=$(du -sh /tmp/coq-dataset/repos 2>/dev/null | cut -f1)
  ours=$(ours_cpu)
  echo "$ts | repos $nrepo ($size) | disk ${dpct}% 여유${dfree}G | load $load (우리 ${ours}%) | mem 여유${memfree}G" >> "$LOG"

  stop=""
  [ "$dpct" -ge "$MAX_DISK_PCT" ] && stop="디스크 ${dpct}%"
  [ "$dfree" -le "$MIN_FREE_G" ] && stop="디스크 여유 ${dfree}G"
  [ "$memfree" -le "$MIN_MEM_G" ] && stop="메모리 여유 ${memfree}G"
  [ "$ours" -ge "$MAX_OURS_PCT" ] && stop="우리 CPU ${ours}% ≥ ${MAX_OURS_PCT}%"
  awk -v l="$load" -v m="$MAX_LOAD" 'BEGIN{exit !(l>m)}' && stop="전체 부하 $load > $MAX_LOAD"

  if [ -n "$stop" ]; then
    echo "$ts | ★ 임계 초과($stop) → 복구 중단" >> "$LOG"
    pkill -f recover_train_repos
    sleep 300
  fi
  sleep 120
done
