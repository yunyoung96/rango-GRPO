#!/bin/bash
# 단일 방법 실험 detach 실행용. 사용: run_method.sh <alias> <timeout> "<description>"
# baseline = all_results/20260701-061839 (M0@600, 앞-20 11/20). 방법은 동일 조건(600s/20)으로 비교.
cd /app/coq-modeling
ALIAS="$1"; TIMEOUT="${2:-600}"; DESC="$3"
echo "### $ALIAS @${TIMEOUT}s/20 시작: $(date -u)"
python3 scripts/run_all.py --alias "$ALIAS" --num 20 --timeout "$TIMEOUT" --workers 1 \
  --description "$DESC"
echo "### $ALIAS 완료: $(date -u)"
