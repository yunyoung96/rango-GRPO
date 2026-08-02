#!/bin/bash
# GPU0 외부사용 ALERT-ONLY watcher (자동플래그 없음 — 오탐 방지).
#   내 학습도 gpu0 다양하게 씀(gold replay 워커스파이크 ~10GB, SFT/GRPO ~23GB) → 절대임계 구분 어려움.
#   보수적: gpu0 ≥ THRESH 가 SUSTAIN(×30s) 지속 = 알림만. 내가 프로세스 확인 후 수동 판단/전환.
#   PID 네임스페이스 격리로 외부PID 직접매칭 불가 → 메모리+지속시간으로 근사.
LOG=all_log/gpu0_watch.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M:%S')] $*" >> "$LOG"; }
: > "$LOG"
mem0(){ nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 0 2>/dev/null; }
THRESH=${THRESH:-16000}   # 내 gold-replay 워커스파이크(~10.5GB) 위. SFT/GRPO 스테이지선 상향 필요.
SUSTAIN=${SUSTAIN:-10}    # ×30s = 5분 지속(내 순간 스파이크 무시)
say "alert-only watch 시작. gpu0≥${THRESH}MiB ×${SUSTAIN}회(30s간격=5분) 지속 시 알림(자동전환 없음)."
cnt=0; alerted=0
while :; do
  m=$(mem0); m=${m:-0}
  if [ "$m" -ge "$THRESH" ]; then
    cnt=$((cnt+1))
    if [ "$cnt" -ge "$SUSTAIN" ] && [ "$alerted" -eq 0 ]; then
      say "⚠ GPU0 높음 지속: ${m}MiB (≥${THRESH}, 5분+). 외부 유저 or 내 SFT/GRPO 스테이지일 수 있음 — 프로세스 확인 필요."
      say "GPU0_HIGH_SUSTAINED"
      alerted=1
    fi
  else
    cnt=0; alerted=0
  fi
  sleep 30
done
