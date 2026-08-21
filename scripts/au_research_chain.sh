#!/bin/bash
# 2차(cov 절제 + hinge) → 3차(국면 게이트) 자동 연결.
#
# ★ 왜 자동으로 잇나: 각 회차가 n=1000 으로 1~2시간 걸리고, cut 전량 생성과
#   CPU 를 나눠 쓰므로 사람이 붙어 있을 이유가 없다. 결과는 로그에 쌓인다.
set -u
cd /app/coq-modeling || exit 1
OUT=all_log/au_research
mkdir -p "$OUT"
L="$OUT/chain.log"
say(){ echo "[$(date '+%m-%d %H:%M')] $*" >> "$L"; }

# ① 2차 완료 대기
while pgrep -f exp_abcd.py > /dev/null; do sleep 60; done
say "2차 완료 대기 끝"

# ② 3차 — 국면 게이트 (τ₀ 세 종)
#    τ(g) = max_p F₁(p,g) 로 국면을 탐지하고, C 국면에서만 구조 항을 켠다.
#    ω≡0 → rrf(A 최고) · ω≡1 → structural 유사(C 최고) 를 잇는 연속 족.
say "3차 시작 — gate,gate80,gate95 + 기준선"
source all_log/v9_env.sh
unset CUTS_PATH
nice -n 19 python3 -u scripts/exp_abcd.py --split test --n 1000 \
    --rankers rrf,structural,gate,gate80,gate95 \
    > "$OUT/round3_test.log" 2>&1
say "3차 완료 → $OUT/round3_test.log"

# ③ 3차에서 이긴 것이 있으면 VAL 로 교차확인
BEST=$(grep -A 12 "프롬프트 포함(P) 기준" "$OUT/round3_test.log" 2>/dev/null \
       | awk 'NF>=3 && $2 ~ /%/ {gsub("%","",$3); if ($3+0 > m) {m=$3+0; b=$1}} END{print b}')
say "3차 최선: ${BEST:-없음}"
if [ -n "${BEST:-}" ]; then
  say "VAL 교차확인 시작 — rrf,structural,$BEST"
  nice -n 19 python3 -u scripts/exp_abcd.py --split val --n 1000 \
      --rankers "rrf,structural,$BEST" \
      > "$OUT/round4_val.log" 2>&1
  say "VAL 완료 → $OUT/round4_val.log"
fi
touch "$OUT/chain.done"
say "연구 체인 종료"
