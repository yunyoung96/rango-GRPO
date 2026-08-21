#!/bin/bash
# α-동치 랭커(eqa) 검증 체인.
#
# ★ 무엇을 재나: `eq` 는 정규형을 **이름까지** 비교한다(포섭 선순서의 몫을 안 냄).
#   `eqa` 는 대칭화 ⊑∩⊒ = α-동치로 비교한다 — 이름에 의존하지 않는 구조 비교.
#   동시에 C 국면 질의를 **실제 assert 가 만드는 subgoal**(statement_of, ∀ 포함)로
#   바꿨다. 옛 질의는 gold 의 결론부라 이름이 gold 것 그대로여서 eq 가 공짜로
#   맞았다 — C 수치가 낙관적이었다. 그래서 2차의 C 숫자와는 직접 비교가 안 된다.
#
# ★ pgrep 자기매칭 주의: 반드시 `python3 -u scripts/...` 전체를 패턴으로 쓴다.
set -u
cd /app/coq-modeling || exit 1
OUT=all_log/au_research
mkdir -p "$OUT"
L="$OUT/chain.log"
say(){ echo "[$(date '+%m-%d %H:%M')] $*" >> "$L"; }
PAT='python3 -u scripts/exp_abcd\.py'
wait_free(){ while pgrep -f "$PAT" > /dev/null; do sleep 60; done; }

wait_free
source all_log/v9_env.sh
unset CUTS_PATH

say "3차 시작 — TEST n=1500 · rrf,eq,eqa,structural (질의 충실화 후 재측정)"
nice -n 19 python3 -u scripts/exp_abcd.py --split test --n 1500 \
    --rankers rrf,eq,eqa,structural > "$OUT/round3_test.log" 2>&1
say "3차 완료 → $OUT/round3_test.log"

wait_free
say "4차 시작 — VAL n=1500 · rrf,eq,eqa,structural"
nice -n 19 python3 -u scripts/exp_abcd.py --split val --n 1500 \
    --rankers rrf,eq,eqa,structural > "$OUT/round4_val.log" 2>&1
say "4차 완료 → $OUT/round4_val.log"

touch "$OUT/chain.done"
say "연구 체인 종료"
