#!/bin/bash
# 학습×탐색 교차 ablation: GRPO 정책 + RMaxTS(정식 full) / BFS α=1.0. eval 0-40.
cd /app/coq-modeling
export PYTHONPATH=src
LOG=all_log/grpo_search_cross.log
echo "[$(date -u '+%H:%M')] GRPO×탐색 교차 시작" >> $LOG
for alias in rango-grpo-rmaxts rango-grpo-bfs; do
  echo "[$(date -u '+%H:%M')] === $alias @40 ===" >> $LOG
  python3 scripts/run_all.py --alias "$alias" --num 40 --timeout 600 --workers 1 \
    --description "학습×탐색 교차: $alias" >> $LOG 2>&1
  d=$(ls -dt all_results/2026071*/ | head -1)
  s=$(python3 -c "import json;dd=json.load(open('$d/summary.json'));print(dd.get('success'),'/',dd.get('total'))" 2>/dev/null)
  echo "[$(date -u '+%H:%M')] ■ $alias: $s -> $d" >> $LOG
done
echo "[$(date -u '+%H:%M')] GRPO×탐색 교차 완료" >> $LOG
