#!/bin/bash
# QED-full backup ablation: value-guided 탐색을 product(논문)/sum/min으로 순차 평가(eval 0-40).
cd /app/coq-modeling
export PYTHONPATH=src
LOG=all_log/qed_ablation.log
echo "[$(date -u '+%H:%M')] QED backup ablation 시작" >> $LOG
for alias in rango-qed rango-qed-sum rango-qed-min; do
  echo "[$(date -u '+%H:%M')] === $alias @40 ===" >> $LOG
  python3 scripts/run_all.py --alias "$alias" --num 40 --timeout 600 --workers 1 \
    --description "QED-full backup ablation: $alias" >> $LOG 2>&1
  d=$(ls -dt all_results/2026071*/ | head -1)
  s=$(python3 -c "import json;dd=json.load(open('$d/summary.json'));print(dd.get('success'),'/',dd.get('total'))" 2>/dev/null)
  echo "[$(date -u '+%H:%M')] ■ $alias: $s -> $d" >> $LOG
done
echo "[$(date -u '+%H:%M')] QED ablation 완료" >> $LOG
