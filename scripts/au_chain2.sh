#!/bin/bash
# 3b차(이름 편향 제거) → 4차(VAL) 자동 연결.
#
# ★ 왜 3b 가 필요한가: 3차는 C 질의를 gold 의 statement 로 만드는데, 그러면 변수
#   이름이 gold 것 그대로다. `eq`(이름 비교)가 **공짜로** 맞아서 이름 강건성을
#   원리적으로 측정할 수 없다. C_RENAME=1 은 binder 를 개명해서 질의한다 —
#   실제 추론에서 모델이 assert 를 자기 말로 쓰는 조건이 바로 그것이다.
#
#   3차 (원 이름) 과 3b차 (개명) 의 **차이가 곧 이름 강건성**이다.
#
# ★ 실행 중인 스크립트 파일은 절대 편집하지 않는다(bash 가 바이트 오프셋으로
#   다시 읽어서 엉뚱한 줄을 실행한다). 그래서 새 파일로 잇는다.
set -u
cd /app/coq-modeling || exit 1
OUT=all_log/au_research
mkdir -p "$OUT"
L="$OUT/chain.log"
say(){ echo "[$(date '+%m-%d %H:%M')] $*" >> "$L"; }
PAT='python3 -u scripts/exp_abcd\.py'
wait_free(){ while pgrep -f "$PAT" > /dev/null; do sleep 60; done; }
R='rrf,eq,eqa,eqx,structural'

wait_free
source all_log/v9_env.sh
unset CUTS_PATH

say "3b차 시작 — TEST n=1500 · C_RENAME=1 (이름 편향 제거) · $R"
C_RENAME=1 nice -n 19 python3 -u scripts/exp_abcd.py --split test --n 1500 \
    --rankers "$R" > "$OUT/round3b_test_rename.log" 2>&1
say "3b차 완료 → $OUT/round3b_test_rename.log"

wait_free
say "4차 시작 — VAL n=1500 · C_RENAME=1 · $R"
C_RENAME=1 nice -n 19 python3 -u scripts/exp_abcd.py --split val --n 1500 \
    --rankers "$R" > "$OUT/round4_val.log" 2>&1
say "4차 완료 → $OUT/round4_val.log"

touch "$OUT/chain.done"
say "연구 체인 종료"
