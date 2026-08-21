#!/bin/bash
# τ 스윕 — afh 족에서 최적점을 찾는다.
#
# ★ 3b차에서 ALL·P 가 τ 에 **단조**였다(0.80 > 0.90 > 0.95 > 1.0). 네 점 모두
#   같은 방향이라 노이즈로 보기 어렵다. 그러면 물어야 할 것은 "어디서 꺾이나" 다.
#   τ 를 더 낮추면 결국 구조 신호가 상시 켜지는 것과 같아져 A 가 무너져야 한다
#   (auf 가 그랬다). 그 전환점이 τ* 이고, 그것이 이 족의 유일한 자유 매개변수다.
#
# ★ 직렬화는 flock. 앞 실험(4차 VAL)이 끝나면 자동으로 이어진다.
set -u
cd /app/coq-modeling || exit 1
OUT=all_log/au_research
L="$OUT/chain.log"
say(){ echo "[$(date '+%m-%d %H:%M')] $*" >> "$L"; }
source all_log/v9_env.sh
unset CUTS_PATH
R='eqx,afh90,afh80,afh70,afh60,afh50,afh40,rrf'
say "5차 시작 — TEST n=1500 · C_RENAME=1 · τ 스윕 $R"
C_RENAME=1 nice -n 19 bash scripts/exp_lock.sh \
    python3 -u scripts/exp_abcd.py --split test --n 1500 --rankers "$R" \
    > "$OUT/round5_tau.log" 2>&1
if grep -q '프롬프트 포함(P) 기준' "$OUT/round5_tau.log"; then
  say "5차 완료 → $OUT/round5_tau.log"
else
  say "★★ 5차 실패 — 결과 표가 없다"; tail -6 "$OUT/round5_tau.log" >> "$L"
fi
