#!/bin/bash
# Iteration 1: baseline(resume) → M1 backtracking. detach 실행용.
cd /app/coq-modeling
echo "### RESUME BASELINE $(date)"
python3 scripts/run_all.py --alias rango --num 20 --timeout 300 --workers 1 \
  --out all_results/20260705-062926 \
  --description "M0 baseline: StraightLineSearcher, BM25 proof + TFIDF premise retrieval only"
echo "### M1 rango-best-beam $(date)"
python3 scripts/run_all.py --alias rango-best-beam --num 20 --timeout 300 --workers 1 \
  --description "M1 backtracking: best-first ClassicalSearch(seen_goals dedup), valid prefix 보존해 실패 step만 교체"
echo "### ITER1 DONE $(date)"
