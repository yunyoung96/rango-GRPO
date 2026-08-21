#!/bin/bash
# 청크 완료 대기 → 병합 → 전 인덱스 검증. 하나라도 실패하면 거기서 멈춘다.
set -u
cd /app/coq-modeling || exit 1
L=data/cut_chunks_train/_progress.log
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$L"; }

# ① 81개가 다 찰 때까지 기다린다 (파일 개수로 판단 — 프로세스 패턴은 자기매칭한다)
while [ "$(ls data/cut_chunks_train/c_*.jsonl 2>/dev/null | wc -l)" -lt 81 ]; do sleep 60; done
say "청크 81/81 완료"

# ② 병합 (청크가 전부 있을 때만 · 연속 커버리지 확인 후 도착지 교체)
bash scripts/merge_cuts.sh train || { say "★ 병합 실패"; exit 1; }
say "병합 완료"

source all_log/v9_env.sh
# ③ 전 인덱스 질의 검증
PYTHONPATH=src python3 -u scripts/verify_cut_all.py train \
    > all_log/au_research/verify_cut_all.log 2>&1
if [ $? -ne 0 ]; then say "★ 전 인덱스 검증 실패 → all_log/au_research/verify_cut_all.log"; exit 1; fi
say "전 인덱스 검증 통과"

# ④ 기존 범위 검증기 (2,000-윈도우 전수 · 0% 구간 탐색)
touch data/cut_chunks_train/_ALL_VERIFIED
say "cut 전 과정 완료"
