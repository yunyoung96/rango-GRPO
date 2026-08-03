#!/bin/bash
# GPU 가드 (플래그 전용 — kill 안 함).
#   컨테이너라 GPU host-PID cmdline 못 읽음 → 메모리+우리job존재로 외부 판정.
#   외부 감지 = (GPU0 >3GB 점유 AND 우리 job 하나도 안 돎) OR (GPU0 >40GB).
#   → 플래그(/tmp/gpu0_foreign)만 세팅. 오케스트레이터가 이걸 보고 GPU1로 재실행.
#   kill 안 하는 이유: pkill은 이름기반이라 GPU1의 우리 job까지 죽임. 대신 OOM+재시도가 양보 처리.
#   외부가 사라지면 플래그 해제(다시 GPU0 사용 가능).
FLAG=/tmp/gpu0_foreign
OURS='train_opener_tac|run_all|run_thm|planner_server|tactic_gen_server|grpo_train|build_opener'
while true; do
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i 0 2>/dev/null)
  used=${used:-0}
  ourjob=0; pgrep -f "$OURS" >/dev/null 2>&1 && ourjob=1
  foreign=0
  [ "$used" -gt 3000 ] && [ "$ourjob" = "0" ] && foreign=1
  [ "$used" -gt 40000 ] && foreign=1
  if [ "$foreign" = "1" ]; then
    [ -f "$FLAG" ] || echo "[gpu_guard $(TZ=Asia/Seoul date +%H:%M)] 외부 GPU0 감지(used=${used}MiB) → 플래그 세팅(GPU1 전용)"
    touch "$FLAG"
  else
    [ -f "$FLAG" ] && echo "[gpu_guard $(TZ=Asia/Seoul date +%H:%M)] GPU0 외부 해제(used=${used}MiB) → 플래그 제거(GPU0 재사용)"
    rm -f "$FLAG"
  fi
  sleep 15
done
