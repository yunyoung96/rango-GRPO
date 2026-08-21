#!/bin/bash
# 청크 → 최종 cut 파일 병합.  data/cut_chunks_<split>/c_*.jsonl → data/cuts_<split>.jsonl
#
# ★ 왜 스크립트로 만드나: 학습이 실제로 읽는 것은 **도착지 파일 하나**다
#   (v9_env.sh 의 CUTS_PATH). 청크를 아무리 만들어도 여기로 옮기지 않으면
#   옛 파일이 그대로 쓰인다 — 그 상태로 학습이 돈 적이 있다.
#
# ★ 안전장치 셋
#   ① 청크가 **전부** 있을 때만 병합한다. 부분 병합이 제일 위험하다 —
#      "새 파일이니 최신이겠지" 라고 믿게 만들면서 구멍이 있다.
#   ② 숫자순으로 붙인다(글롭은 사전순이라 c_0, c_1, c_10, … 이 된다).
#      기능상 레코드는 순서 무관이지만 사람이 볼 때 헷갈린다.
#   ③ 붙인 뒤 `scanned_range()` 로 **연속 커버리지**를 확인하고, 전 구간이
#      아니면 도착지를 건드리지 않고 실패한다.
set -u
SPLIT="${1:-train}"
MODE="${2:-plan}"          # plan(기본) | cut(옛 형식)
cd /app/coq-modeling || exit 1
if [ "$MODE" = "plan" ]; then
  SRC="data/cut_plan_chunks_$SPLIT"; PFX="p"; DST="data/cut_plans_$SPLIT.jsonl"
else
  SRC="data/cut_chunks_$SPLIT";      PFX="c"; DST="data/cuts_$SPLIT.jsonl"
fi
CHUNK="${CHUNK:-25000}"

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
have=$(ls "$SRC"/${PFX}_*.jsonl 2>/dev/null | wc -l)
echo "전체 $TOTAL · 청크 $CHUNK × $N · 보유 $have"

if [ "$have" -lt "$N" ]; then
  echo "★ 청크가 모자란다 ($have/$N) — 병합하지 않는다."
  for k in $(seq 0 $((N-1))); do [ -s "$SRC/${PFX}_$k.jsonl" ] || echo "   빠진 청크 ${PFX}_$k (인덱스 $((k*CHUNK)) ~ $(( (k+1)*CHUNK )))"; done
  exit 1
fi

TMP="$DST.new"
: > "$TMP"
for k in $(seq 0 $((N-1))); do cat "$SRC/${PFX}_$k.jsonl" >> "$TMP"; done   # ② 숫자순
echo "이어붙임: $(wc -l < "$TMP") 줄 · $(du -h "$TMP" | cut -f1)"

# ③ 연속 커버리지 확인 — 도착지를 건드리기 **전에** 본다
PYTHONPATH=src CUTS_PATH="$TMP" python3 - "$TOTAL" <<'PYX' || { echo "★ 커버리지 검증 실패 — 도착지를 건드리지 않았다"; rm -f "$TMP"; exit 1; }
import sys, logging
sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
from tactic_gen import cut_lookup
need = int(sys.argv[1])
a, b = cut_lookup.scanned_range()
print(f"   연속 스캔 범위 [{a:,}, {b:,})  필요 [0, {need:,})")
print(f"   {cut_lookup.stats()}")
sys.exit(0 if (a <= 0 and b >= need) else 1)
PYX

mv -f "$TMP" "$DST"
echo "✓ 병합 완료 → $DST"
