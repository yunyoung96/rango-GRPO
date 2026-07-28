#!/bin/bash
# SFT→PPO / PPO 평가 (최후순위로 분리). 6조건 중 나머지 2개.
#   순서: SFT→PPO → PPO (사용자 요청). test 1191, timeout 120s, w2.
set -u
LOG=all_log/bigscale2.log
TEST=data/compcert_bs2_test_idx.txt
NTEST=$(wc -l < "$TEST")
T=120
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
teval(){ local d="all_results/bs2_$2_test${T}_w2/summary.json"; local n
  n=$([ -s "$d" ] && python3 -c "import json;print(len(json.load(open('$d'))['results']))" 2>/dev/null || echo 0)
  [ "$n" -ge "$NTEST" ] && { say "   $2 이미 완료($n)"; return 0; }
  python3 scripts/run_all.py --alias "$1" --idx-file "$TEST" --timeout "$T" --workers 2 \
    --out "all_results/bs2_$2_test${T}_w2" --description "bs2 test $2 test${T}_w2" >> "$LOG" 2>&1; }

say "===== SFT→PPO / PPO 평가 (최후순위) 시작 ====="
say "  SFT→PPO";  teval rango-grpo-bs2-sftppo sftppo
say "  PPO";      teval rango-grpo-bs2-ppo ppo
say "===== SFT→PPO / PPO 완료 → 6조건 최종표 ====="
python3 - <<PY 2>&1 | tee -a "$LOG"
import json
for nm,d in [('baseline','baseline'),('SFT','sft'),('GRPO','grpo'),('SFT→GRPO','sftgrpo'),('SFT→PPO','sftppo'),('PPO','ppo')]:
    try:
        r=json.load(open(f'all_results/bs2_{d}_test120_w2/summary.json'))['results']
        print(f'  {nm:9s}: {sum(1 for x in r if x["success"])}/{len(r)}')
    except Exception: print(f'  {nm:9s}: (미완)')
PY
