#!/bin/bash
# 5차/6차 — τ 스윕 + 전 기준선. n=3000 · 쌍 비교(McNemar) 포함.
#
# ★ n 을 1500 → 3000 으로 올렸다. 다만 **더 중요한 것은 통계 방식**이다.
#   랭커들은 같은 예제·같은 후보 풀을 보므로 독립 표본 CI 는 공통 분산까지 오차로
#   세어 실제 차이를 "구분 불가" 로 잘못 판정한다. McNemar 는 불일치 쌍만 세므로
#   같은 데이터에서 훨씬 예민하다 — n 을 두 배 늘리는 것보다 이득이 크다.
#
# ★ tfidf 를 넣는다: rango 원본 검색이라 "얼마나 올렸나" 의 분모다.
#   rrf 는 이미 우리 융합(tfidf 순위 + 결론구조 C' 순위)이라 원본이 아니다.
set -u
cd /app/coq-modeling || exit 1
OUT=all_log/au_research
L="$OUT/chain.log"
say(){ echo "[$(date '+%m-%d %H:%M')] $*" >> "$L"; }
source all_log/v9_env.sh
unset CUTS_PATH
R='tfidf,rrf,structural,eq,eqx,afh90,afh80,afh70,afh60,afh50'
N=3000

run(){
  local sp="$1" lg="$2" desc="$3"
  say "$desc 대기 — $sp n=$N · C_RENAME=1 · $R"
  C_RENAME=1 nice -n 19 bash scripts/exp_lock.sh \
      python3 -u scripts/exp_abcd.py --split "$sp" --n "$N" --rankers "$R" > "$lg" 2>&1
  if grep -q '프롬프트 포함(P) 기준' "$lg"; then say "$desc 완료 → $lg"; return 0; fi
  say "★★ $desc 실패 — 결과 표가 없다"; tail -6 "$lg" >> "$L"; return 1
}
run test "$OUT/round5_tau.log"     "5차 TEST τ스윕" || exit 1
run val  "$OUT/round6_val_tau.log" "6차 VAL τ스윕"  || exit 1
say "τ 스윕 체인 종료"
