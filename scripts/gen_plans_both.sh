#!/bin/bash
# TRAIN + VAL 계획을 만들고 **한 파일로** 합친다.
#
# ★ 왜 한 파일인가: `cut_lookup` 은 `CUTS_PATH` 하나를 읽는 싱글턴이다. TRAIN 과 VAL 을
#   따로 두면 eval 데이터셋이 TRAIN 파일을 읽고 "sid 가 없네" 하며 조용히 cut 없이 돈다.
#   합쳐 두면 `scanned_range(split)` 가 meta 의 split 으로 걸러 각자 제 범위를 본다.
set -u
cd /app/coq-modeling || exit 1
bash scripts/gen_plans_all.sh train || exit 1
CHUNK=25000 PAR=3 bash scripts/gen_plans_all.sh val || exit 1
: > data/cut_plans_all.jsonl.new
for f in data/cut_plan_chunks_train/p_*.jsonl data/cut_plan_chunks_val/p_*.jsonl; do
  cat "$f" >> data/cut_plans_all.jsonl.new
done
mv -f data/cut_plans_all.jsonl.new data/cut_plans_all.jsonl
echo "[$(date '+%m-%d %H:%M')] TRAIN+VAL 병합 → data/cut_plans_all.jsonl" \
  >> data/cut_plan_chunks_train/_progress.log
