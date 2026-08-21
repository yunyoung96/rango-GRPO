#!/bin/bash
# λ 스윕 + λ-free 변형까지 A/B/C 측정.  cut 생성과 병행하므로 낮은 우선순위.
#
# ★ 보는 법: A 와 C 를 **따로** 본다.
#   과거 실패(A 45.4% → 18.2%)가 정확히 "C 는 좋아지고 A 가 무너지는" 형태였고,
#   합친 목표지표만 보면 못 잡는다. 그리고 A 가 높을수록 cut 없이 gold 를 그대로
#   예측하므로 안전하다(cut 은 생성 실패·문법 오류 위험이 있다).
set -u
SPLIT="${1:-test}"
N="${2:-1000}"
cd /app/coq-modeling || exit 1
source all_log/v9_env.sh
unset CUTS_PATH
exec nice -n 19 python3 -u scripts/exp_abcd.py \
    --split "$SPLIT" --n "$N" \
    --rankers tfidf,rrf,structural,aul,aul05,aul2,auf
