#!/bin/bash
set -u
FIX_PID=${FIX_PID:?}
DRV_PID=${DRV_PID:?}
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a all_log/chain_all.log; }
say "체인 대기 (robustness ${DRV_PID} → 수습 ${FIX_PID} → backward → rango baseline → SOTA3)"
while kill -0 "$FIX_PID" 2>/dev/null; do sleep 120; done
say "오염수습 종료 확인"
say "▶ 1/3  ★ Backward curriculum @40 (sparse reward 구조적 해법)"
bash all_log/run_backward.sh
say "◀ backward 완료"
say "▶ 2/3  rango baseline @180 (하드웨어 교란 분리)"
DRIVER_PID=$DRV_PID bash all_log/run_rango_baseline_180.sh
say "◀ rango baseline 완료"
say "▶ 3/3  SOTA 3종 + 재샘플링"
bash all_log/run_sota3.sh
say "◀ 전체 체인 완료"
