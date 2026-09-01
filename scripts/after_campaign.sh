#!/bin/bash
# 캠페인 종료 대기 → 빈루트 재시도(--retry-logical) → 전 지점 수집(collect_all.sh) 자동 체인
cd /app/coq-modeling
until grep -q 'CAMPAIGN_DONE' all_log/au_research/build_campaign.log 2>/dev/null; do sleep 60; done
echo "[$(date '+%H:%M') KST] 캠페인 종료 → 빈루트 재시도"
python3 scripts/train_build_campaign.py --retry-logical > all_log/au_research/retry_logical.log 2>&1
echo "[$(date '+%H:%M') KST] 재시도 종료 → 전 지점 수집"
bash scripts/collect_all.sh > all_log/au_research/r19_v1_train_all.log 2>&1
echo "AFTER_CAMPAIGN_DONE"
