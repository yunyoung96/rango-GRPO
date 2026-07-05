#!/bin/bash
# 오버나이트 자동 연쇄 실험 드라이버.
# queue.txt(alias|timeout|desc)를 순차 처리: 스모크(idx6)→run_all→make_report.
# 깨진 alias는 스킵. done.txt로 중복 방지. queue.txt에 줄 추가하면 다음 패스에서 픽업.
# 한 번에 GPU 하나. 재시작 안전(done.txt 기반 resume).
cd /app/coq-modeling
Q=all_log/queue.txt
DONE=all_log/done.txt
touch "$DONE"
log(){ echo "[$(date -u +%H:%M:%S)] $*" >> all_log/overnight.log; }

log "=== overnight driver 시작 ==="
# 기존 실험 있으면 대기
while pgrep -f "run_thm.py run" >/dev/null 2>&1; do sleep 30; done

idle_passes=0
while [ $idle_passes -lt 3 ]; do
  did_work=0
  while IFS='|' read -r alias timeout desc; do
    [ -z "$alias" ] && continue
    key="$alias|$timeout"
    grep -qxF "$key" "$DONE" && continue
    did_work=1
    log "▶ $alias @${timeout}s 스모크 시작"
    # 고아 서버 정리
    for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done
    sleep 2
    if timeout 260 python3 scripts/run_thm.py run "$alias" test 6 --timeout 90 \
         > "all_log/smoke_${alias}.log" 2>&1 && \
       grep -q "CURRENT RESULT: SUCCESS" "all_log/smoke_${alias}.log"; then
      log "✓ $alias 스모크 통과 → 본실험"
      python3 scripts/run_all.py --alias "$alias" --num 20 --timeout "$timeout" \
        --workers 1 --description "$desc" >> "all_log/overnight.log" 2>&1
      dir=$(ls -dt all_results/*/ | head -1)
      python3 scripts/make_report.py "$dir" >> "all_log/overnight.log" 2>&1
      s=$(python3 -c "import json;d=json.load(open('$dir/summary.json'));print(d['success'],'/',d['total'])" 2>/dev/null)
      log "■ $alias 완료: $s → $dir"
    else
      log "✗ $alias 스모크 실패 → 스킵"
    fi
    echo "$key" >> "$DONE"
  done < "$Q"
  if [ $did_work -eq 0 ]; then
    idle_passes=$((idle_passes+1)); sleep 120
  else
    idle_passes=0
  fi
done
log "=== overnight driver 종료 (큐 소진) ==="
