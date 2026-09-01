#!/bin/bash
# TRAIN 저장소 재구축 — scratchpad(tmpfs) 소실 후 영속 위치 tmp/tr 에 빌드.
# 사용: nohup bash scripts/rebuild_tr.sh > all_log/au_research/rebuild_tr.log 2>&1 &
R=/app/coq-modeling/tmp/tr
t0=$(date +%s)
echo "[$(date -u -d '+9 hours' '+%H:%M') KST] coq-art 빌드 시작"
( cd $R/coq-community-coq-art && make -j4 -k > build.log 2>&1 ); 
echo "coq-art: vo=$(find $R/coq-community-coq-art -name '*.vo' | wc -l) / v=$(find $R/coq-community-coq-art -name '*.v' | wc -l)  ($(( $(date +%s)-t0 ))s)"
t1=$(date +%s)
echo "[$(date -u -d '+9 hours' '+%H:%M') KST] undecidability 빌드 시작"
( cd $R/uds-psl-coq-library-undecidability/theories && make -j4 -k > ../build.log 2>&1 )
echo "undec: vo=$(find $R/uds-psl-coq-library-undecidability -name '*.vo' | wc -l) / v=$(find $R/uds-psl-coq-library-undecidability -name '*.v' | wc -l)  ($(( $(date +%s)-t1 ))s)"
echo "REBUILD_DONE"
