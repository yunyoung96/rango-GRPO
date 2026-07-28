#!/bin/bash
# ★ 알고리즘 큐: core 파이프라인 종료 후 → LUFFY → backward curriculum (둘 다 @20→@40).
#   둘 다 GPU 단독 사용해야 결과 오염 없음(과거 경합 오염 사례) → core 종료를 기다린 뒤 순차 실행.
set -u
CORE_PID=${CORE_PID:?"CORE_PID 필요 (run_core.sh PID)"}
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a all_log/chain_algo.log; }

say "체인 대기: core(${CORE_PID}) 종료 후 → LUFFY → backward"
while kill -0 "$CORE_PID" 2>/dev/null; do sleep 120; done
say "core 종료 확인 — GPU 단독 확보"

say "▶ 1/2  LUFFY @20→@40 (off-policy gold 주입)"
bash all_log/run_luffy.sh
say "◀ LUFFY 완료"

say "▶ 2/2  Backward curriculum @20→@40 (중간상태 롤아웃)"
bash all_log/run_backward.sh
say "◀ Backward 완료"

say "===== 알고리즘 큐 전체 완료 ====="
grep -h "smart\] ■" all_log/luffy.log all_log/backward.log 2>/dev/null | tail -8
