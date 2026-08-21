#!/bin/bash
# 완성된 계획 청크를 **나오는 대로** Coq 으로 검증한다 (1번과 동시 진행).
#
# ★ 왜 스트리밍인가: 계획 생성이 4시간 걸리는데, 청크는 완성되는 대로 독립적인
#   파일이 된다. 다 기다릴 이유가 없다 — 나온 것부터 검증하면 총 시간이 겹친다.
#
# ★ 왜 파일 배치를 안 쓰나: 파일 전체를 컴파일하면 뒷부분 의존성 때문에 **원본조차**
#   73% 가 실패한다(실측). 검증된 `hunt_assert_errors` 는 파일을 그 증명에서 **잘라내고**
#   앞부분만 컴파일해서 원본 실패가 15% 에 그친다. 그 방식을 쓴다.
set -u
cd /app/coq-modeling || exit 1
OUT=all_log/au_research/coqver
mkdir -p "$OUT"
LOG="$OUT/_progress.log"
PAR="${PAR:-4}"          # Coq 은 무겁다 — 계획 생성(12)과 나눠 쓴다
source all_log/v9_env.sh
unset CUTS_PATH

say(){ echo "[$(date '+%m-%d %H:%M')] $*" >> "$LOG"; }
say "스트리밍 검증 시작 (동시 $PAR)"

done_marker(){ echo "$OUT/$(basename "$1" .jsonl).done"; }

while true; do
  todo=""
  for f in data/cut_plan_chunks_train/p_*.jsonl; do
    [ -s "$f" ] || continue
    [ -f "$(done_marker "$f")" ] && continue
    todo="$todo $f"
  done
  if [ -z "$todo" ]; then
    # 계획 생성이 끝났고 남은 것도 없으면 종료
    n=$(ls data/cut_plan_chunks_train/p_*.jsonl 2>/dev/null | wc -l)
    [ "$n" -ge 81 ] && { say "전 청크 검증 완료"; break; }
    sleep 120; continue
  fi
  running=0
  for f in $todo; do
    b=$(basename "$f" .jsonl)
    PYTHONPATH=src nice -n 19 python3 -u scripts/verify_cut_substeps.py \
        "$f" "$OUT/$b.jsonl" > "$OUT/$b.log" 2>&1 && touch "$(done_marker "$f")" &
    running=$((running+1))
    [ "$running" -ge "$PAR" ] && { wait -n; running=$((running-1)); }
  done
  wait
  say "배치 완료 — 검증된 청크 $(ls "$OUT"/*.done 2>/dev/null | wc -l)"
done
say "스트리밍 검증 종료"
