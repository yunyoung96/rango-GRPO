#!/bin/bash
# 3b차(이름 편향 제거) → 4차(VAL). 전 랭커 8개.
#
# ★ 직렬화는 flock (scripts/exp_lock.sh). pgrep 패턴은 쓰지 않는다 — 이유는 그 파일 참고.
# ★ 실행 후 결과 표 존재를 확인한다. exit 0 이어도 결과가 없으면 실패로 멈춘다.
set -u
cd /app/coq-modeling || exit 1
OUT=all_log/au_research
mkdir -p "$OUT"
L="$OUT/chain.log"
say(){ echo "[$(date '+%m-%d %H:%M')] $*" >> "$L"; }
R='rrf,eq,eqa,eqx,afh95,afh90,afh80,structural'

source all_log/v9_env.sh
unset CUTS_PATH

run(){  # run <split> <로그> <설명>
  local sp="$1" lg="$2" desc="$3"
  say "$desc 시작 — $sp n=1500 · C_RENAME=1 · $R"
  C_RENAME=1 nice -n 19 bash scripts/exp_lock.sh \
      python3 -u scripts/exp_abcd.py --split "$sp" --n 1500 --rankers "$R" > "$lg" 2>&1
  if grep -q '프롬프트 포함(P) 기준' "$lg"; then
    say "$desc 완료 → $lg"; return 0
  fi
  say "★★ $desc 실패 — 결과 표가 없다. 체인을 멈춘다. 꼬리:"
  tail -6 "$lg" >> "$L"; return 1
}

if ! nice -n 19 bash scripts/exp_lock.sh python3 -u scripts/exp_abcd.py --selftest 2>&1 \
     | grep -q '자기검사: 통과'; then
  say "★★ 사전 자기검사 실패 — 실험을 시작하지 않는다"; exit 1
fi
say "사전 자기검사 통과"

run test "$OUT/round3b_test_rename.log" "3b차" || exit 1
run val  "$OUT/round4_val.log"          "4차"  || exit 1
touch "$OUT/chain.done"
say "연구 체인 종료 — 전 회차 결과 확인됨"
