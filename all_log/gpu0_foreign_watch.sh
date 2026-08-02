#!/bin/bash
# GPU0 외부 사용 감지 → /tmp/gpu0_foreign 플래그 + 알림.
#   컨테이너 PID격리로 외부PID 직접매칭 불가 → 메모리 급증으로 감지.
#   baseline(우리 학습분) 대비 +THRESH MiB 가 SUSTAIN회 연속 지속 = 외부 유저.
#   플래그 세팅 시 이후 wait_gpus 들이 gpu0 회피(gpu1로). 현재 실행 stage는 알림 보고 수동전환.
LOG=all_log/gpu0_watch.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M:%S')] $*" >> "$LOG"; }
: > "$LOG"
mem0(){ nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 0 2>/dev/null; }
THRESH=6000     # baseline 대비 이만큼(MiB) 초과 = 외부 의심
SUSTAIN=3       # 연속 이 횟수(×20s=60s) 지속돼야 확정(우리 자체 스파이크 무시)
# baseline = 시작 시 우리 학습분(안정화 위해 30s 후 측정)
sleep 30
BASE=$(mem0); BASE=${BASE:-0}
say "watch 시작. baseline(우리분) GPU0=${BASE}MiB, 임계=+${THRESH}MiB×${SUSTAIN}회"
cnt=0
while :; do
  m=$(mem0); m=${m:-0}
  # baseline 자체가 우리 학습 stage 전환으로 오를 수 있음 → 하강 시 baseline 갱신(우리 최소선 추적)
  if [ "$m" -lt "$BASE" ]; then BASE=$m; fi
  over=$((m - BASE))
  if [ "$over" -ge "$THRESH" ]; then
    cnt=$((cnt+1))
    if [ "$cnt" -ge "$SUSTAIN" ] && [ ! -f /tmp/gpu0_foreign ]; then
      touch /tmp/gpu0_foreign
      say "★ 외부 GPU0 감지! GPU0=${m}MiB (baseline ${BASE}, +${over}MiB) → /tmp/gpu0_foreign 세팅. 이후 stage들 gpu1로 회피."
      say "FOREIGN_GPU0_DETECTED"
    fi
  else
    cnt=0
    # 외부가 빠지고(플래그 있는데 정상복귀) 30분 지속되면 플래그 해제? — 수동으로. 자동해제 안함(안전).
  fi
  sleep 20
done
