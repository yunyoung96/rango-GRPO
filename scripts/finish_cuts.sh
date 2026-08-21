#!/bin/bash
# 계획 청크 완료 대기 → 병합 → 전 인덱스 검증 → 배선 검증. 하나라도 실패하면 멈춘다.
#
# ★ 흐름
#     gen_plans_all.sh   →  data/cut_plan_chunks_train/p_*.jsonl  (81개)
#     merge_cuts.sh      →  data/cut_plans_train.jsonl            (= CUTS_PATH 가 될 것)
#     verify_cut_all.py  →  전 인덱스가 판정을 받았나 · cut 형태가 정상인가
#     verify_cut_wiring  →  학습 시점 결정 규칙 (1)(2)(3) 이 다 도는가
set -u
cd /app/coq-modeling || exit 1
L=data/cut_plan_chunks_train/_progress.log
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$L"; }

# ① 81개가 다 찰 때까지 (파일 개수로 판단 — 프로세스 패턴은 자기매칭한다)
while [ "$(ls data/cut_plan_chunks_train/p_*.jsonl 2>/dev/null | wc -l)" -lt 81 ]; do sleep 60; done
say "계획 청크 81/81 완료"

bash scripts/merge_cuts.sh train plan || { say "★ 병합 실패"; exit 1; }
say "병합 완료 → data/cut_plans_train.jsonl"

source all_log/v9_env.sh
export CUTS_PATH=data/cut_plans_train.jsonl

PYTHONPATH=src python3 -u scripts/verify_cut_all.py train \
    > all_log/au_research/verify_cut_all.log 2>&1 \
  || { say "★ 전 인덱스 검증 실패 → all_log/au_research/verify_cut_all.log"; exit 1; }
say "전 인덱스 검증 통과"

PYTHONPATH=src python3 -u scripts/verify_cut_wiring.py \
    > all_log/au_research/verify_cut_wiring.log 2>&1 \
  || { say "★ 배선 검증 실패"; exit 1; }
say "배선 검증 통과"

touch data/cut_plan_chunks_train/_ALL_VERIFIED
say "cut 계획 전 과정 완료 — CUTS_PATH=data/cut_plans_train.jsonl 로 바꿀 준비 됨"
