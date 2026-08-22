#!/bin/bash
# 웜 스모크가 끝난 **뒤에** 남은 실험을 돌린다 — 속도 측정이 오염되지 않게.
#
# ★ flock 으로 중복 실행을 막는다. `pgrep -f` 는 **자기 자신과 이 파일을 쓴 heredoc 까지**
#   매칭해 영구 교착을 만든다(실제로 세 번 겪었다). 잠금은 파일로 한다.
set -u
cd /app/coq-modeling || exit 1
exec 9>/tmp/after_smoke.lock
flock -n 9 || { echo "이미 실행 중"; exit 0; }

L=all_log/au_research/after_smoke.log
say() { echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$L"; }

say "── 스모크 종료 대기"
for _ in $(seq 1 900); do
  grep -q "train_runtime" all_log/smoke_train_warm.log 2>/dev/null && break
  grep -qE "ChildFailedError" all_log/smoke_train_warm.log 2>/dev/null && { say "★ 스모크 실패"; break; }
  sleep 20
done
say "스모크 종료 확인"

source all_log/v9_env.sh
export CUTS_PATH=data/cut_plans_all.jsonl
export CUTS_ALLOW_PARTIAL=1

# ① tfidf 1단계 필터를 **안 거치는** 랭커 — 사용자가 요청했으나 어젯밤 목록에서 빠졌다.
#    stage1=5,000 이 후보 풀(중앙 7,378 · 최대 14,333)을 68% 의 스텝에서 자르고 있다.
#    자르지 않으면 어떤지 봐야 "tfidf 가 필요하다"는 결론이 성립한다.
say "── ① jac_all 실험 (tfidf 필터 없음) test n=1500"
# ★ 검색 실험은 cut 과 무관하다. CUTS_PATH 가 있으면 TEST 커버리지를 요구하며 죽는데
#   (계획은 TRAIN+VAL 만 만들었다), 이 실험은 랭킹만 재므로 cut 을 볼 이유가 없다.
C_RENAME=1 CUTS_PATH= PYTHONPATH=src nice -n 10 timeout 14400 python3 -u scripts/exp_abcd.py \
    --split test --n 1500 \
    --rankers tfidf,eqx,jac,jac_all,jac_all_eqx \
    >> all_log/au_research/jac_all_test.log 2>&1
say "① 종료(rc=$?)"

# ② 계획 파일의 cut 을 **Coq 으로** 검증한다 (계획 모드).
#    옛 경로는 런타임 `Check` 출력을 재파싱해 `assert (string)` 같은 쓰레기를 냈다.
#    계획 파일은 premise 원문을 쓰므로 그 경로가 없다 — 실제로 확인한다.
say "── ② 계획 cut 동적 Coq 검증 250건"
PLANS=data/cut_plans_all.jsonl PYTHONPATH=src nice -n 10 timeout 21600 \
    python3 -u scripts/hunt_assert_errors.py 250 train \
    >> all_log/au_research/plan_coq_train.log 2>&1
say "② 종료(rc=$?)"
say "===== after_smoke 종료 ====="
