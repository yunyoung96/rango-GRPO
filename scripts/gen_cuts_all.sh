#!/bin/bash
# 한 split 의 cut 을 **전량** 생성한다. 재개 가능(멱등).
#
# ★ 왜 청크로 쪼개고 재개 가능하게 만드나
#   build_cuts.py 는 끝에서야 `os.replace` 로 결과를 내놓는다. 큰 샤드 하나가 중간에
#   죽으면 그때까지의 작업이 통째로 날아간다(실제로 두 번 당했다 — 세션이 끝나며
#   프로세스가 정리되어 11분·70분치가 사라졌다).
#   → 청크를 25,000 예제로 쪼개면 손실이 한 청크(약 60분)로 제한되고,
#     이미 끝난 청크는 **파일 존재로 건너뛴다**. 같은 명령을 다시 실행하면 이어서 간다.
#
# ★ 왜 전량인가
#   cut 파일은 인덱스 [START, START+N) 만 덮는 범위 제한 산출물이다. 필요 범위가
#   설정(max_steps · 배치 · CUT_DROP_HOPELESS)에 따라 바뀌어서, "이번엔 충분"이
#   다음엔 부족해진다. 전량을 만들면 범위 개념 자체가 사라진다.
#
# 사용:
#   bash scripts/gen_cuts_all.sh train          # TRAIN 전량
#   bash scripts/gen_cuts_all.sh val            # VAL 전량
#   (죽으면 같은 명령을 다시 실행)
set -u
SPLIT="${1:-train}"
CHUNK="${CHUNK:-25000}"
PAR="${PAR:-12}"                       # 동시 실행 수 = 코어 수
cd /app/coq-modeling || exit 1
source all_log/v9_env.sh
unset CUTS_PATH                        # 생성 중에는 조회 비활성

OUT="data/cut_chunks_$SPLIT"
mkdir -p "$OUT"
LOG="$OUT/_progress.log"

TOTAL=$(PYTHONPATH=src python3 - "$SPLIT" <<'PYX'
import sys, yaml, logging
from pathlib import Path
sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
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
  f="$OUT/c_$k.jsonl"
  [ -s "$f" ] && continue                      # ★ 완료된 청크는 건너뛴다
  st=$(( k * CHUNK ))
  python3 -u scripts/build_cuts.py "$CHUNK" "$SPLIT" "$f" "$st" \
      > "$OUT/c_$k.log" 2>&1 &
  running=$((running+1))
  if [ "$running" -ge "$PAR" ]; then wait -n; running=$((running-1)); fi
done
wait

done_n=$(ls "$OUT"/c_*.jsonl 2>/dev/null | wc -l)
echo "[$(date '+%m-%d %H:%M')] $SPLIT 완료 청크 $done_n/$N" >> "$LOG"
if [ "$done_n" -ge "$N" ]; then
  echo "ALL_DONE" >> "$LOG"
  exit 0
fi
echo "[$(date '+%m-%d %H:%M')] 미완 $((N-done_n))개 — 같은 명령을 다시 실행하면 이어서 간다" >> "$LOG"
exit 1
