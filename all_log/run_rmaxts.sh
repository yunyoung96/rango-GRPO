#!/bin/bash
cd /app/coq-modeling
log(){ echo "[$(date -u +%H:%M:%S)] $*" >> all_log/rmaxts.log; }
log "=== RMaxTS 드라이버: 앞선 GPU 실험 대기 ==="
sleep 30
while ps -eo args | grep -qE "[o]racle_ablation|[r]un_all.py --alias|[r]un_qed.sh|[r]un_6.7b_lean.sh"; do sleep 120; done
for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
# 스모크: end-to-end 동작 검증 (모델+Coq+트리)
log "▶ 스모크 rmaxts idx6 @180"
timeout 500 python3 scripts/run_thm.py run rmaxts test 6 --timeout 180 > all_log/smoke_rmaxts.log 2>&1
if grep -qE "RMaxTS.*성공|CURRENT RESULT: SUCCESS|RANGO_JSON_SUCCESS" all_log/smoke_rmaxts.log; then
  log "✓ 스모크 동작(성공 여부 무관, 크래시 없음) → first-20"
  for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
  python3 scripts/run_all.py --alias rmaxts --num 20 --timeout 600 --workers 1 \
    --description "RMaxTS 충실 재구현(DeepSeek-Prover-V1.5 알고리즘)" >> all_log/rmaxts.log 2>&1
  dir=$(ls -dt all_results/*/ | head -1)
  python3 scripts/make_report.py "$dir" >> all_log/rmaxts.log 2>&1
  s=$(python3 -c "import json;d=json.load(open('$dir/summary.json'));print(d['success'],'/',d['total'])" 2>/dev/null)
  log "■ rmaxts first-20 완료: $s → $dir"
else
  log "✗ 스모크 크래시 — smoke_rmaxts.log 확인"
  tail -20 all_log/smoke_rmaxts.log >> all_log/rmaxts.log
fi
log "=== RMaxTS 드라이버 종료 ==="
