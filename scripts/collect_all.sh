#!/bin/bash
# ①+(b) 전 지점 풀 수집 — 캠페인에서 빌드된(vo>0) TRAIN 저장소 전부에 r19 필터를 돌린다 (train_pool all 모드).
# 로그 명명: r19_v2_train_all.log (플러그인 r19 · 회차 2 — 무상한). 재실행 시 resume 로 이어쓴다.
cd /app/coq-modeling
R=/app/coq-modeling/tmp/tr
REPOS=$(python3 scripts/train_repos.py)
python3 - "$REPOS" <<'PYG' || exit 1
import sys; sys.path.insert(0,"scripts")
from train_repos import leaky
repos=[x.split("=")[0] for x in sys.argv[1].split(",") if x]
bad=[r for r in repos if leaky(r)]
assert not bad, f"★누출 사전검사 실패: {bad}"
print(f"누출 사전검사 통과: {len(repos)} 저장소")
PYG
N=$(echo "$REPOS" | tr ',' '\n' | grep -c .)
echo "[$(date '+%H:%M') KST] 전 지점 수집 시작 · 저장소 $N · 워커 8"
python3 scripts/train_pool.py 1000000 "$REPOS" all 8 resume
echo "COLLECT_ALL_DONE rc=$?"
