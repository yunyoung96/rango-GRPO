#!/bin/bash
# cut **계획** 전량 생성 — 청크 병렬 · 중단되면 이어서.
#
# ★ 옛 `gen_cuts_all.sh` 와 다른 점: 검색을 안 돌린다. 그래서
#   ① 훨씬 빠르고 ② 검색 정책을 바꿔도 다시 만들 필요가 없다.
#   대신 lemma 를 쓰는 **모든** 스텝에 cut 을 만들어 둔다(예전엔 검색이 놓친 것만).
#
# ★ 옛 청크의 `stmt` 사전을 재사용한다(SEED_STMTS) — statement 추출은 검색과 무관한
#   사실이라 다시 뽑을 이유가 없다.
set -u
SPLIT="${1:-train}"
cd /app/coq-modeling || exit 1
OUT="data/cut_plan_chunks_$SPLIT"
mkdir -p "$OUT"
LOG="$OUT/_progress.log"
CHUNK="${CHUNK:-25000}"
PAR="${PAR:-12}"
export SEED_STMTS="${SEED_STMTS:-data/cut_chunks_$SPLIT}"
source all_log/v9_env.sh
unset CUTS_PATH

TOTAL=$(PYTHONPATH=src python3 - "$SPLIT" <<'PYX'
import sys, yaml
from pathlib import Path
sys.path.insert(0, "src")
from data_management.splits import Split
from tactic_gen.tactic_data import ShuffledIndex
cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
si = ShuffledIndex.load(Path(cc["tactic_data"]["shuffled_index_loc"]))
print(si.split_length(getattr(Split, sys.argv[1].upper())))
PYX
)
N=$(( (TOTAL + CHUNK - 1) / CHUNK ))
echo "[$(date '+%m-%d %H:%M')] $SPLIT 전체 $TOTAL · 청크 $CHUNK × $N · 동시 $PAR" >> "$LOG"

running=0
for k in $(seq 0 $((N-1))); do
  f="$OUT/p_$k.jsonl"
  [ -s "$f" ] && continue
  st=$(( k * CHUNK ))
  PYTHONPATH=src python3 -u scripts/build_cut_plans.py "$CHUNK" "$SPLIT" "$f" "$st" \
      > "$OUT/p_$k.log" 2>&1 &
  running=$((running+1))
  if [ "$running" -ge "$PAR" ]; then wait -n; running=$((running-1)); fi
done
wait
done_n=$(ls "$OUT"/p_*.jsonl 2>/dev/null | wc -l)
echo "[$(date '+%m-%d %H:%M')] $SPLIT 완료 청크 $done_n/$N" >> "$LOG"
[ "$done_n" -ge "$N" ] && { echo "ALL_DONE" >> "$LOG"; exit 0; }
echo "[$(date '+%m-%d %H:%M')] 미완 $((N-done_n))개 — 다시 실행하면 이어서 간다" >> "$LOG"
exit 1
