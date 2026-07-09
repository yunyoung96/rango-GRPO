#!/bin/bash
cd /app/coq-modeling
log(){ echo "[$(date -u +%H:%M:%S)] $*" >> all_log/bfs.log; }
log "=== BFS-Prover 드라이버: rmaxts 및 앞선 실험 대기 ==="
sleep 45
while ps -eo args | grep -qE "[o]racle_ablation|[r]un_all.py --alias|[r]un_qed.sh|[r]un_6.7b_lean.sh|[r]un_rmaxts.sh|run rmaxts"; do sleep 120; done
for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
log "▶ 스모크 bfs-prover idx6 @180"
timeout 500 python3 scripts/run_thm.py run bfs-prover test 6 --timeout 180 > all_log/smoke_bfs.log 2>&1
if grep -qE "BFS-Prover.*성공|CURRENT RESULT: SUCCESS|RANGO_JSON_SUCCESS" all_log/smoke_bfs.log; then
  log "✓ 스모크 동작 → first-20"
  for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
  python3 scripts/run_all.py --alias bfs-prover --num 20 --timeout 600 --workers 1 \
    --description "BFS-Prover 충실 재구현(length-normalized best-first)" >> all_log/bfs.log 2>&1
  dir=$(ls -dt all_results/*/ | head -1)
  python3 scripts/make_report.py "$dir" >> all_log/bfs.log 2>&1
  s=$(python3 -c "import json;d=json.load(open('$dir/summary.json'));print(d['success'],'/',d['total'])" 2>/dev/null)
  log "■ bfs-prover first-20 완료: $s → $dir"
else
  log "✗ 스모크 크래시 — smoke_bfs.log 확인"; tail -20 all_log/smoke_bfs.log >> all_log/bfs.log
fi
log "=== BFS-Prover 드라이버 종료 ==="
