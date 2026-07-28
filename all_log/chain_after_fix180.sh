#!/bin/bash
# fix@180(robustness) 완료 후 새 기법 순차 @40. smart_eval 캐싱=안 돈 것만.
set -u
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a all_log/newtech.log; }
say "대기: fix@180 완료까지"
until [ "$(python3 -c "import json;print(len(json.load(open('all_results/smart_rango-grpo-fix/summary.json'))['results']))" 2>/dev/null || echo 0)" -ge 180 ]; do sleep 120; done
say "fix@180 완료 → 새 기법 순차 시작"
bash all_log/run_luffy_kl.sh
bash all_log/run_vine.sh
bash all_log/run_revcurr.sh
say "===== 순차 큐 완료(adaptprefix/bread 는 이어서) ====="
