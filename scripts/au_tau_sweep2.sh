#!/bin/bash
# 5차 — τ 스윕 + **전 기준선**. 이름 편향 없는 조건(C_RENAME=1).
#
# ★ 기준선을 전부 넣는다. 특히 `tfidf` — **rango 원본이 쓰던 검색**이라
#   "우리가 얼마나 올렸나" 를 말하려면 이것이 분모여야 한다. `rrf` 는 이미
#   우리 융합(tfidf 순위 + 결론구조 C' 순위)이라 원본이 아니다.
#
#     tfidf       rango 원본 (BM25 계열 어휘 유사도만)
#     rrf         + 결론구조 C' 순위 융합
#     structural  현재 프로덕션 (rrf + cov + def + 완전일치)
#     eq          rrf + 완전일치(이름 의존)
#     eqx         rrf + α-동치(전체 명제) = afh 족의 τ=1 끝점
#     afh90..50   τ 를 낮춰가며 — 어디서 꺾이나
set -u
cd /app/coq-modeling || exit 1
OUT=all_log/au_research
L="$OUT/chain.log"
say(){ echo "[$(date '+%m-%d %H:%M')] $*" >> "$L"; }
source all_log/v9_env.sh
unset CUTS_PATH
R='tfidf,rrf,structural,eq,eqx,afh90,afh80,afh70,afh60,afh50'
say "5차 대기 — TEST n=1500 · C_RENAME=1 · $R"
C_RENAME=1 nice -n 19 bash scripts/exp_lock.sh \
    python3 -u scripts/exp_abcd.py --split test --n 1500 --rankers "$R" \
    > "$OUT/round5_tau.log" 2>&1
if grep -q '프롬프트 포함(P) 기준' "$OUT/round5_tau.log"; then
  say "5차 완료 → $OUT/round5_tau.log"
else
  say "★★ 5차 실패 — 결과 표가 없다"; tail -6 "$OUT/round5_tau.log" >> "$L"
fi

# 6차 — VAL 로 교차확인 (5차에서 이긴 것이 다른 스플릿에서도 이기나)
say "6차 대기 — VAL n=1500 · C_RENAME=1 · $R"
C_RENAME=1 nice -n 19 bash scripts/exp_lock.sh \
    python3 -u scripts/exp_abcd.py --split val --n 1500 --rankers "$R" \
    > "$OUT/round6_val_tau.log" 2>&1
if grep -q '프롬프트 포함(P) 기준' "$OUT/round6_val_tau.log"; then
  say "6차 완료 → $OUT/round6_val_tau.log"
else
  say "★★ 6차 실패"; tail -6 "$OUT/round6_val_tau.log" >> "$L"
fi
say "τ 스윕 체인 종료"
