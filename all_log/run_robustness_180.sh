#!/bin/bash
# Robustness @180: @40에서 baseline 초과했던 방법들을 180정리(position 0~179)로 재검증.
# position 0~179 = 표준 GRPO 학습셋(compcert 200:240)과 완전 disjoint.
# published Rango baseline은 각 run이 original_success로 자동 기록.
# 사용: effstudy + PRM-GRPO 완료 후 자동 실행. 대상/워커 조정 가능.
set -u
LOG=all_log/robustness_180.log
WORKERS=${WORKERS:-2}          # 시간 단축 위해 기본 2 (OOM 위험 → 모니터링 필수)
NUM=180
say(){ echo "[$(date '+%H:%M')] $*" | tee -a "$LOG"; }

# 대상: @40 baseline 초과분. 필요시 목록 수정.
ALIASES=(${ALIASES:-rango-grpo bfs-a1 rango-portfolio})

say "===== Robustness @${NUM} 시작 (workers=${WORKERS}) 대상: ${ALIASES[*]} ====="
for a in "${ALIASES[@]}"; do
  say "----- ${a} @${NUM} -----"
  python3 scripts/run_all.py --alias "$a" --num "$NUM" --timeout 600 --workers "$WORKERS" \
    --description "robustness @${NUM} (disjoint from GRPO train 200:240)" >> "$LOG" 2>&1
  d=$(ls -dt all_results/*_"$(echo "$a" | sed 's/[^A-Za-z0-9._-]/-/g')" 2>/dev/null | head -1)
  s=$(python3 -c "import json;dd=json.load(open('$d/summary.json'));\
o=sum(1 for r in dd['results'] if r.get('original_success'));\
print(dd['success'],'/',dd['total'],'| published:',o)" 2>/dev/null)
  say "■ ${a}: ${s}  -> ${d}"
done
say "===== Robustness @${NUM} 완료 ====="
