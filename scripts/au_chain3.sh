#!/bin/bash
# 3b차(이름 편향 제거 · 전 랭커) → 4차(VAL) 자동 연결.
#
# ★ 한 번에 8개 랭커를 돌린다. 비싼 부분(후보 풀 + tf-idf + 구조 신호)이 랭커마다
#   공유되므로, 따로 돌리는 것보다 훨씬 싸다.
#
# ★ 무엇을 겨루나
#     rrf            바탕만                          (A 상한 기준선)
#     eq             + 정규형 동일성(이름 의존)       — 지금 쓰는 것의 3항 판
#     eqa            + α-동치(결론만)                 — exact 에 불건전
#     eqx  = afh100  + α-동치(전체 명제)              — 발화 ⟺ exact 성공
#     afh95/90/80    + h_τ(F₁^α)  τ<1                — 같은 족의 연속 확장
#     structural     현재 프로덕션(5항)
#
#   afh 족은 `score_τ = RRF + W·h_τ(F₁^α)` 하나이고 eqx 가 그 τ→1 끝점이다.
#   옛 auf/aufh 는 여기에 cov(A −6.9pp)와 상시 RRF(F₁)를 얹었고 F 가 비대칭이라
#   몫 위의 함수가 아니었다 — 그래서 못생겼고 성능도 낮았다.
#
# ★ 실행 중인 스크립트 파일은 절대 편집하지 않는다. 새 파일로 잇는다.
set -u
cd /app/coq-modeling || exit 1
OUT=all_log/au_research
mkdir -p "$OUT"
L="$OUT/chain.log"
say(){ echo "[$(date '+%m-%d %H:%M')] $*" >> "$L"; }
PAT='python3 -u scripts/exp_abcd\.py'
wait_free(){ while pgrep -f "$PAT" > /dev/null; do sleep 60; done; }
R='rrf,eq,eqa,eqx,afh95,afh90,afh80,structural'

wait_free
source all_log/v9_env.sh
unset CUTS_PATH

say "3b차 시작 — TEST n=1500 · C_RENAME=1 · $R"
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
