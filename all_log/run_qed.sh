#!/bin/bash
cd /app/coq-modeling
log(){ echo "[$(date -u +%H:%M:%S)] $*" >> all_log/qed.log; }
log "=== QED 드라이버(최후순위): 앞선 실험 모두 대기 ==="
while ps -eo args | grep -qE "[r]un_bigger.sh|[r]un_oracle.sh|[o]racle_ablation|[r]un_all.py --alias"; do sleep 120; done
for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
# QED value 학습 (트리 데이터에서 gamma^dist 회귀)
log "▶ QED value 학습"
python3 scripts/train_qed_value.py --epochs 40 >> all_log/qed.log 2>&1
if [ -f models/qed_value/qed.pt ]; then
  # 단순 QED vs QED+retrieval혼용(hybrid) 둘 다 평가·비교
  for a in rango-qed rango-qed-hybrid; do
    for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
    log "▶ $a 평가 first-20 @600"
    python3 scripts/run_all.py --alias "$a" --num 20 --timeout 600 --workers 1 \
      --description "QEDCartographer 계열 비교" >> all_log/qed.log 2>&1
    dir=$(ls -dt all_results/*/ | head -1)
    python3 scripts/make_report.py "$dir" >> all_log/qed.log 2>&1
    s=$(python3 -c "import json;d=json.load(open('$dir/summary.json'));print(d['success'],'/',d['total'])" 2>/dev/null)
    log "■ $a 완료: $s → $dir"
  done
  python3 scripts/unique_solves.py >> all_log/qed.log 2>&1
else
  log "✗ qed.pt 학습 실패"
fi
log "=== QED 드라이버 종료 ==="
