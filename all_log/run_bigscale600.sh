#!/bin/bash
# bigscale600s_w2: timeout 을 120→600s 로 늘려 "시간을 더 주면 성능이 오르나" 검증.
#   대상: baseline, SFT→GRPO 2조건만. 범위: test 앞 300개(compcert_bs2_test300_idx.txt).
# ★ 근거: bs2(120s)에서 실패의 99%가 timeout(탐색막힘 아님) + SFT→GRPO는 '느리지만 끈질긴' 정책
#   (같은 정리 71% 케이스에서 baseline보다 느림) → 시간 늘리면 SFT→GRPO가 특히 오를 것으로 예상.
#   출력 이름에 test600_w2 명시(로그에 600 각인).
set -u
LOG=all_log/bigscale600.log
TEST=data/compcert_bs2_test300_idx.txt
NTEST=$(wc -l < "$TEST")
T=600
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
# 완성도 체크 resume(부분→완성 오인 방지)
teval(){ local d="all_results/bs2_$2_test${T}_w2/summary.json"; local n
  n=$([ -s "$d" ] && python3 -c "import json;print(len(json.load(open('$d'))['results']))" 2>/dev/null || echo 0)
  [ "$n" -ge "$NTEST" ] && { say "   $2 이미 완료($n)"; return 0; }
  python3 scripts/run_all.py --alias "$1" --idx-file "$TEST" --timeout "$T" --workers 2 \
    --out "all_results/bs2_$2_test${T}_w2" --description "bs2 test $2 test${T}_w2 (600s 300개)" >> "$LOG" 2>&1; }

say "===== bigscale600s_w2 (baseline + SFT→GRPO, 앞 ${NTEST}개, timeout ${T}s, w2) 시작 ====="
say "  baseline";  teval rango baseline
say "  SFT→GRPO";  teval rango-grpo-bs2-sftgrpo sftgrpo

say "===== bigscale600 완료 — 120s 대비 비교 ====="
python3 - <<PY 2>&1 | tee -a "$LOG"
import json
T=$T; N=$NTEST
idx=[int(x) for x in open("$TEST").read().split()]
def load(path):
    try: return {x['idx']:x.get('success') for x in json.load(open(path))['results']}
    except: return {}
print(f"  조건        | 600s({N}개) | 120s(같은{N}개) | 증가")
for nm,c in [("baseline","baseline"),("SFT→GRPO","sftgrpo")]:
    r6=load(f"all_results/bs2_{c}_test{T}_w2/summary.json")
    r1=load(f"all_results/bs2_{c}_test120_w2/summary.json")
    s6=sum(1 for i in idx if r6.get(i))
    s1=sum(1 for i in idx if i in r1 and r1.get(i))
    n6=sum(1 for i in idx if i in r6)
    print(f"  {nm:10s} | {s6}/{n6} | {s1} | {s6-s1:+d}")
PY
