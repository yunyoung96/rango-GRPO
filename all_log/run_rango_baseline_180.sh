#!/bin/bash
# ★ 우리 자체 rango baseline @180 — 지금까지 없던 가장 중요한 대조군.
#
# 문제: results/rango.json (published baseline) 은 **RTX 2080 Ti + CPU 1코어**에서 나온 결과다
#   (rango.json 의 hardware 필드 원문:
#    "Each theorem ran with a 10 minute timeout using a single gpu (2080ti) and a single cpu
#     with 16 gigabytes of memory.")
#   우리는 **RTX 6000 Ada(48GB) + 96코어**를 쓰고 타임아웃은 똑같이 600초 벽시계다.
#   → 같은 600초 안에 훨씬 많은 tactic 을 시도한다. 즉 우리가 더 큰 탐색 예산으로 비교해 왔다.
#
# 실측 증거: @20 에서 우리 rango 10 vs published 8 (+2). @40 에서 GRPO 는 published 대비 +4 지만
#   **우리 rango 재현 대비로는 +1** 뿐이었다(IMPLEMENTATION.md:1253).
#
# 이 스크립트가 없으면 rango-grpo 의 "+7" 이 GRPO 덕분인지 하드웨어 덕분인지 분해가 불가능하다.
set -u
LOG=all_log/rango_baseline_180.log
WORKERS=${WORKERS:-2}
DRIVER_PID=${DRIVER_PID:?robustness 드라이버 PID 필요}
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "===== rango baseline @180 대기 (robustness 드라이버 ${DRIVER_PID} 종료 후) ====="
while kill -0 "$DRIVER_PID" 2>/dev/null; do sleep 60; done
say "드라이버 종료 → rango baseline 시작 (GPU 독점)"

python3 scripts/run_all.py --alias rango --num 180 --timeout 600 --workers "$WORKERS" \
  --description "우리 자체 rango baseline @180 (RTX 6000 Ada). published rango.json 은 2080Ti 기준이라 하드웨어 교란 분리용" \
  >> "$LOG" 2>&1

D=$(ls -dt all_results/*_rango | head -1)
python3 - "$D" <<'PY' 2>&1 | tee -a "$LOG"
import json, sys, math
d=sys.argv[1]
r=json.load(open(f"{d}/summary.json"))["results"]
ours=sum(1 for x in r if x.get("success"))
pub =sum(1 for x in r if x.get("original_success"))
g=[x['idx'] for x in r if x.get('success') and not x.get('original_success')]
c=[x['idx'] for x in r if x.get('original_success') and not x.get('success')]
b,cc=len(g),len(c); n=b+cc
p=min(2*sum(math.comb(n,k) for k in range(0,min(b,cc)+1))/2**n,1.0) if n else 1.0
print(f"\n■ 우리 rango(RTX 6000 Ada): {ours}/{len(r)}")
print(f"■ published rango(2080 Ti) : {pub}/{len(r)}")
print(f"■ 하드웨어 효과 추정        : {ours-pub:+d}  (gain {b} / 회귀 {cc}, McNemar p={p:.4f})")
print(f"\n→ rango-grpo 60/180 과 비교하면 **진짜 GRPO 효과 = {60-ours:+d}**")
print(f"   (지금까지 보고된 +7 은 published 대비였고, 그 중 {ours-pub:+d} 는 하드웨어)")
PY
say "===== rango baseline @180 완료 ====="
