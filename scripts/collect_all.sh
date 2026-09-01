#!/bin/bash
# ①+(b) 전 지점 풀 수집 — 캠페인에서 빌드된(vo>0) TRAIN 저장소 전부에 r19 필터를 돌린다 (train_pool all 모드).
# 로그 명명: r19_v1_train_all.log (플러그인 r19 · 회차 1). 재실행 시 resume 로 이어쓴다.
cd /app/coq-modeling
R=/app/coq-modeling/tmp/tr
REPOS=$(python3 - <<'PY'
import json, os
R="/app/coq-modeling/tmp/tr"; out=[]
for l in open("all_log/train_build_campaign.jsonl"):
    r=json.loads(l)
    if r.get("vo",0)>0 and os.path.isdir(f"{R}/{r['proj']}"): out.append(f"{r['proj']}={R}/{r['proj']}")
print(",".join(out))
PY
)
N=$(echo "$REPOS" | tr ',' '\n' | grep -c .)
echo "[$(date '+%H:%M') KST] 전 지점 수집 시작 · 저장소 $N · 워커 6"
python3 scripts/train_pool.py 1000000 "$REPOS" all 6 resume
echo "COLLECT_ALL_DONE rc=$?"
