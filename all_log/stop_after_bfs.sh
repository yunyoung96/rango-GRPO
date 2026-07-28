#!/bin/bash
# bfs-a1 완료 후 rango-portfolio 가 시작되지 않도록 드라이버를 멈춘다(사용자 요청).
# 순서가 중요: run_all 종료 → 드라이버가 ■ 결과 라인을 로그에 기록 → 그 다음에 죽인다.
set -u
RUNALL=1809863     # bfs-a1 run_all
DRIVER=1605702     # robustness 드라이버
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a all_log/stop_after_bfs.log; }

say "감시 시작: bfs-a1 run_all(${RUNALL}) 종료 대기 → portfolio 차단"
while kill -0 "$RUNALL" 2>/dev/null; do sleep 20; done
say "bfs-a1 run_all 종료됨. ■ 결과 라인 기록 대기(최대 90초)"

for i in $(seq 18); do
  grep -q '■ bfs-a1' all_log/robustness_180.log && break
  sleep 5
done
if grep -q '■ bfs-a1' all_log/robustness_180.log; then
  say "✅ bfs-a1 결과 기록 확인: $(grep '■ bfs-a1' all_log/robustness_180.log)"
else
  say "⚠️ ■ bfs-a1 라인 미기록 — summary.json 은 무사하니 수치는 살아있음"
fi

# 드라이버 프로세스 그룹 통째로 종료 → 막 시작했을 수 있는 portfolio run_all/run_thm 도 같이 정리
say "드라이버(${DRIVER}) 프로세스 그룹 종료 → rango-portfolio 차단"
kill -TERM -"$DRIVER" 2>/dev/null || kill -TERM "$DRIVER" 2>/dev/null
sleep 5
pkill -f "run_all.py --alias rango-portfolio" 2>/dev/null
sleep 3
if kill -0 "$DRIVER" 2>/dev/null; then
  say "SIGTERM 무시 → SIGKILL"
  kill -KILL -"$DRIVER" 2>/dev/null || kill -KILL "$DRIVER" 2>/dev/null
fi
say "✅ 드라이버 종료 완료 → fix_contested(오염수습)가 자동으로 이어짐"
say "   잔여: $(ps -eo args | grep -cE 'run_all.py --alias rango-portfolio' || true) 개 portfolio 프로세스"
