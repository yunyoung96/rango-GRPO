#!/bin/bash
cd /app/coq-modeling
log(){ echo "[$(date -u +%H:%M:%S)] $*" >> all_log/hybrid.log; }
log "=== 하이브리드 드라이버 시작 ==="
# GPU 점유 실험 끝날 때까지 대기
while ps -eo args | grep -qE "[r]un_all.py --alias rango-(vlog|vguided|6.7b)"; do sleep 60; done
for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
# 스모크
log "▶ 스모크 rango-hybrid idx6 @120"
timeout 400 python3 scripts/run_thm.py run rango-hybrid test 6 --timeout 120 > all_log/smoke_hybrid.log 2>&1
grep -q "RANGO_JSON_SUCCESS: True" all_log/smoke_hybrid.log && log "✓ 스모크 통과" || log "✗ 스모크 실패(로그확인)"
for a in rango-hybrid rango-hybrid-v; do
  for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
  log "▶ 본실험 $a first-20 @600"
  python3 scripts/run_all.py --alias "$a" --num 20 --timeout 600 --workers 1 \
    --description "retrieval-신뢰도 게이팅 adaptive-width hybrid" >> all_log/hybrid.log 2>&1
  dir=$(ls -dt all_results/*/ | head -1)
  python3 scripts/make_report.py "$dir" >> all_log/hybrid.log 2>&1
  s=$(python3 -c "import json;d=json.load(open('$dir/summary.json'));print(d['success'],'/',d['total'])" 2>/dev/null)
  log "■ $a 완료: $s → $dir"
done
log "=== 하이브리드 드라이버 종료 ==="
