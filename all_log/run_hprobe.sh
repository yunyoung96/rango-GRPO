#!/bin/bash
cd /app/coq-modeling
log(){ echo "[$(date -u +%H:%M:%S)] $*" >> all_log/hprobe.log; }
log "=== hprobe 러너 시작: psauto 완료 대기 ==="
# psauto run_all 끝날 때까지 대기
while ps -eo args | grep -q "[r]un_all.py --alias rango-psauto"; do sleep 60; done
log "psauto 완료 확인. 고아 서버 정리."
for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done
sleep 3
# 1) idx840 단독 — sauto probe가 잡는지(추가 capability 증명)
log "▶ hprobe idx840 @600 (capability demo)"
timeout 700 python3 scripts/run_thm.py run rango-hprobe test 840 --timeout 600 \
  > all_log/hprobe_idx840.log 2>&1
grep -q "RANGO_JSON_SUCCESS: True" all_log/hprobe_idx840.log && log "✓ idx840 SOLVED by hprobe" || log "✗ idx840 not solved"
for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done
sleep 3
# 2) first-20 @600 — baseline parity 확인(회귀 없어야)
log "▶ hprobe first-20 @600 (parity)"
python3 scripts/run_all.py --alias rango-hprobe --num 20 --timeout 600 --workers 1 \
  --description "cheap sauto probe(<=90s)+full straight-line: baseline parity + sauto bonus" \
  >> all_log/hprobe.log 2>&1
dir=$(ls -dt all_results/*/ | head -1)
python3 scripts/make_report.py "$dir" >> all_log/hprobe.log 2>&1
s=$(python3 -c "import json;d=json.load(open('$dir/summary.json'));print(d['success'],'/',d['total'])" 2>/dev/null)
log "■ hprobe first-20 완료: $s → $dir"
echo "rango-hprobe|600" >> all_log/done.txt
log "=== hprobe 러너 종료 ==="
