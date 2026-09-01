#!/bin/bash
# undecidability 재빌드 완료를 기다렸다가 variant 전체 배치(art+undec, 이어쓰기)를 재개한다.
cd /app/coq-modeling
until grep -q 'REBUILD_DONE' all_log/au_research/rebuild_tr.log 2>/dev/null; do sleep 120; done
R=/app/coq-modeling/tmp/tr
echo "[$(date '+%H:%M') KST] variant 전체 배치 재개 (이어쓰기)"
python3 scripts/variant_gen.py 4000 "coq-community-coq-art=$R/coq-community-coq-art,uds-psl-coq-library-undecidability=$R/uds-psl-coq-library-undecidability" > all_log/au_research/vargen_full2.log 2>&1 < /dev/null
echo "AFTER_REBUILD_DONE"
