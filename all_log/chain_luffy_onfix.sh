#!/bin/bash
# ★ LUFFY-on-fix — fix 어댑터 위에서 재구현한 LUFFY 를 fix@180 직전에 선점해 먼저 실행.
#   현재 chain_luffy_now.sh(=$WAIT_PID) 는 backward→retry-prm→fix@180 순. backward·retry-prm 은
#   보존하고, chain 이 'fix @180'(4/4) 에 진입하는 순간 그 단계만 선점 취소 →
#   LUFFY-on-fix 실행 → 끝나면 미뤄둔 fix@180 실행.
set -u
WAIT_PID=${WAIT_PID:?"WAIT_PID 필요 (chain_luffy_now.sh PID)"}
LOG=all_log/chain_luffy_onfix.log
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "대기: chain(${WAIT_PID}) 가 backward·retry-prm 마치고 fix@180(4/4) 진입할 때까지"
PREEMPTED=0
while kill -0 "$WAIT_PID" 2>/dev/null; do
  if grep -q "▶ 4/4  fix @180" all_log/chain_luffy_now.log 2>/dev/null; then
    PREEMPTED=1
    say "fix@180 진입 감지 → 선점(backward·retry-prm 결과는 보존)"
    kill "$WAIT_PID" 2>/dev/null
    pkill -f "smart_eval.py --alias rango-grpo-fix" 2>/dev/null
    pkill -f "run_all.py --alias rango-grpo-fix" 2>/dev/null
    pkill -f "run_thm.py run rango-grpo-fix" 2>/dev/null
    pkill -f "tactic_gen_server.py.*rango-grpo-fix" 2>/dev/null
    break
  fi
  sleep 60
done
[ "$PREEMPTED" = "1" ] || say "chain 자연 종료(선점 안 함) — 그대로 진행"

say "GPU 잔여 정리 대기(15s)"; sleep 15

say "▶ 1/2  LUFFY-on-fix @20→@40 (fix 어댑터 위에서 재학습)"
bash all_log/run_luffy.sh
say "◀ LUFFY-on-fix 완료"

if [ "$PREEMPTED" = "1" ]; then
  say "▶ 2/2  fix @180 (미뤄둔 통계 확정)"
  python3 scripts/smart_eval.py --alias rango-grpo-fix --stages 180 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"
else
  say "▶ 2/2  fix@180 스킵(선점 안 함)"
fi
say "===== LUFFY-on-fix 큐 완료 ====="
grep -h "smart\] ■" all_log/luffy.log 2>/dev/null | tail -4
