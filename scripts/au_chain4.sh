#!/bin/bash
# 3b차(이름 편향 제거 · 전 랭커) → 4차(VAL).
#
# ★ 구조적 방어 두 개 (3b 가 `import re` 누락으로 30분 만에 조용히 죽은 뒤 추가)
#   ① 실행 **전** 자기검사를 따로 돌려서, 실패하면 본 실험을 시작조차 안 한다.
#   ② 실행 **후** 결과 표가 실제로 찍혔는지 확인한다. 프로세스가 0 으로 끝나도
#      결과가 없으면 실패로 처리하고 체인을 멈춘다 — "완료" 라고 로그만 남기고
#      빈 파일을 남기는 것이 제일 나쁘다.
set -u
cd /app/coq-modeling || exit 1
OUT=all_log/au_research
mkdir -p "$OUT"
L="$OUT/chain.log"
say(){ echo "[$(date '+%m-%d %H:%M')] $*" >> "$L"; }
PAT='python3 -u scripts/exp_abcd\.py'
wait_free(){ while pgrep -f "$PAT" > /dev/null; do sleep 60; done; }
R='rrf,eq,eqa,eqx,afh95,afh90,afh80,structural'

run(){  # run <split> <로그파일> <설명>
  local sp="$1" lg="$2" desc="$3"
  wait_free
  say "$desc 시작 — $sp n=1500 · C_RENAME=1 · $R"
  C_RENAME=1 nice -n 19 python3 -u scripts/exp_abcd.py --split "$sp" --n 1500 \
      --rankers "$R" > "$lg" 2>&1
  if grep -q '프롬프트 포함(P) 기준' "$lg"; then
    say "$desc 완료 → $lg"
    return 0
  fi
  say "★★ $desc 실패 — 결과 표가 없다. 체인을 멈춘다. 꼬리:"
  tail -6 "$lg" >> "$L"
  return 1
}

source all_log/v9_env.sh
unset CUTS_PATH

# ① 사전 자기검사 — 실패하면 본 실험을 시작조차 안 한다
wait_free
if ! python3 -u scripts/exp_abcd.py --selftest 2>&1 | grep -q '자기검사: 통과'; then
  say "★★ 사전 자기검사 실패 — 실험을 시작하지 않는다"
  exit 1
fi
say "사전 자기검사 통과"

run test "$OUT/round3b_test_rename.log" "3b차" || exit 1
run val  "$OUT/round4_val.log"          "4차"  || exit 1

touch "$OUT/chain.done"
say "연구 체인 종료 — 전 회차 결과 확인됨"
