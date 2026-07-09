#!/bin/bash
# 스케일링: 기존 방법을 개수 늘려가며(N=100) 신선한 baseline과 공정 비교.
# portfolio +2가 N 커져도 유지/증가하는지 + baseline 변동 통제.
cd /app/coq-modeling
log(){ echo "[$(date -u +%H:%M:%S)] $*" >> all_log/scaling.log; }
log "=== 스케일링 드라이버: 앞선 GPU 실험 대기 ==="
sleep 30
while ps -eo args | grep -qE "[o]racle_ablation|[r]un_all.py --alias|[r]un_qed.sh|[r]un_6.7b_lean.sh|[r]un_oracle_both.sh|[r]un_rmaxts.sh|[r]un rmaxts|[r]un_bfs.sh|[r]un bfs-prover|[r]un_ablation.sh|[r]un_ablation40.sh"; do sleep 120; done
# 신선한 baseline + 핵심 기법들을 idx0-99(100정리)에 @600. 각 완료마다 unique_solves 갱신.
for a in rango rango-portfolio rango-sauto; do
  for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
  log "▶ $a idx0-99 @600 (N=100 스케일링)"
  python3 scripts/run_all.py --alias "$a" --num 100 --timeout 600 --workers 1 \
    --description "스케일링 N=100 (개수 늘려 강점·net 재확인)" >> all_log/scaling.log 2>&1
  dir=$(ls -dt all_results/*/ | head -1)
  s=$(python3 -c "import json;d=json.load(open('$dir/summary.json'));print(d['success'],'/',d['total'])" 2>/dev/null)
  log "■ $a 완료: $s → $dir"
  python3 scripts/unique_solves.py >> all_log/scaling.log 2>&1
done
log "=== 스케일링 종료 ==="
