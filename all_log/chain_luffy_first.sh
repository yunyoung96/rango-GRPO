#!/bin/bash
# ★ LUFFY 우선 큐 — fix@180(통계 확정)을 뒤로 미루고 LUFFY 를 앞당긴다.
#   core 의 retry/retry-prm(진행 중, 가치 있음)은 보존하고, core 가 'fix @180' 단계에 진입하는
#   순간 그 단계만 선점 취소한 뒤: LUFFY → backward → (미뤄둔)fix@180 순으로 GPU 단독 실행.
#   ⚠️ 실행 중 run_core.sh 파일을 편집하면 bash 바이트오프셋이 깨지므로, 편집 대신 프로세스 선점.
set -u
CORE_PID=${CORE_PID:?"CORE_PID 필요 (run_core.sh PID)"}
LOG=all_log/chain_luffy_first.log
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "LUFFY 우선 큐 대기: core(${CORE_PID}) retry/retry-prm 완료 → fix@180 진입 시 선점"

PREEMPTED=0
while kill -0 "$CORE_PID" 2>/dev/null; do
  if grep -q "▶ fix @180" all_log/core.log 2>/dev/null; then
    PREEMPTED=1
    say "fix@180 진입 감지 → 선점: fix 단계만 취소(retry/retry-prm 결과는 보존)"
    kill "$CORE_PID" 2>/dev/null                             # core bash 종료(다음 단계 없음)
    pkill -f "smart_eval.py --alias rango-grpo-fix" 2>/dev/null
    pkill -f "run_all.py --alias rango-grpo-fix" 2>/dev/null
    pkill -f "run_thm.py run rango-grpo-fix" 2>/dev/null
    pkill -f "tactic_gen_server.py.*rango-grpo-fix" 2>/dev/null
    break
  fi
  sleep 30
done
[ "$PREEMPTED" = "1" ] || say "core 가 스스로 종료됨(선점 안 함) — 그대로 진행"

say "GPU 잔여 프로세스 정리 대기(15s)"
sleep 15

say "▶ 1/3  LUFFY @20→@40 (앞당김)"
bash all_log/run_luffy.sh
say "◀ LUFFY 완료"

say "▶ 2/3  Backward curriculum @20→@40"
bash all_log/run_backward.sh
say "◀ Backward 완료"

# fix@180 은 우리가 취소했을 때만 뒤에서 실행(자연종료로 이미 돌았으면 중복 방지)
if [ "$PREEMPTED" = "1" ]; then
  say "▶ 3/3  fix @180 (미뤄둔 통계 확정, 우리rango 61 기준)"
  python3 scripts/smart_eval.py --alias rango-grpo-fix --stages 180 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"
  say "◀ fix@180 완료"
else
  say "▶ 3/3  fix@180 스킵(선점 안 함 — core 에서 이미 처리됐거나 미도달)"
fi

say "===== LUFFY 우선 큐 전체 완료 ====="
grep -h "smart\] ■" all_log/luffy.log all_log/backward.log 2>/dev/null | tail -8
