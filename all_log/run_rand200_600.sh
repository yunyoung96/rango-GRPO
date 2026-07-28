#!/bin/bash
# rand200_600s_w2: bigscale test set(1191)에서 랜덤 추출한 200개(seed=42)에 대해
#   timeout 600s / w2 로 baseline vs SFT→GRPO 비교. "시간을 더 주면 성능이 오르나 + 격차가 유지되나".
# ★ 근거: bs2(120s) 실패의 99%가 timeout, SFT→GRPO는 '느리지만 끈질긴' 정책 → 시간↑에 유리 예상.
#   idx 파일: compcert_bs2_rand200_idx.txt (전 test set 대표, 앞300 편향 회피).
#   출력 이름에 test600_w2 명시(로그에 600 각인).
set -u
LOG=all_log/rand200_600.log
TEST=data/compcert_bs2_rand200_idx.txt
NTEST=$(wc -l < "$TEST")
T=600
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
teval(){ local d="all_results/rand200_$2_test${T}_w2/summary.json"; local n
  n=$([ -s "$d" ] && python3 -c "import json;print(len(json.load(open('$d'))['results']))" 2>/dev/null || echo 0)
  [ "$n" -ge "$NTEST" ] && { say "   $2 이미 완료($n)"; return 0; }
  python3 scripts/run_all.py --alias "$1" --idx-file "$TEST" --timeout "$T" --workers 2 \
    --out "all_results/rand200_$2_test${T}_w2" --description "rand200 $2 test${T}_w2 (600s 200개)" >> "$LOG" 2>&1; }

say "===== rand200_600s_w2 (baseline + SFT→GRPO, 랜덤 ${NTEST}개, timeout ${T}s, w2) 시작 ====="
say "  baseline";  teval rango baseline
say "  SFT→GRPO";  teval rango-grpo-bs2-sftgrpo sftgrpo

say "===== rand200_600 완료 — 120s 대비 비교 ====="
python3 - <<PY 2>&1 | tee -a "$LOG"
import json
T=$T
idx=[int(x) for x in open("$TEST").read().split()]
def load(p):
    try: return {x['idx']:x.get('success') for x in json.load(open(p))['results']}
    except: return {}
print(f"  조건       | 600s(200개) | 120s(같은200개) | 증가")
for nm,c in [("baseline","baseline"),("SFT→GRPO","sftgrpo")]:
    r6=load(f"all_results/rand200_{c}_test{T}_w2/summary.json")
    r1=load(f"all_results/bs2_{c}_test120_w2/summary.json")
    s6=sum(1 for i in idx if r6.get(i)); n6=sum(1 for i in idx if i in r6)
    s1=sum(1 for i in idx if i in r1 and r1.get(i))
    print(f"  {nm:9s} | {s6}/{n6} | {s1} | {s6-s1:+d}")
# 600s에서의 baseline vs sftgrpo 격차
b=load(f"all_results/rand200_baseline_test{T}_w2/summary.json")
sg=load(f"all_results/rand200_sftgrpo_test{T}_w2/summary.json")
common=[i for i in idx if i in b and i in sg]
bs=sum(1 for i in common if b[i]); sgs=sum(1 for i in common if sg[i])
print(f"\n  ★ 600s 격차 (같은 {len(common)}개): baseline {bs} vs SFT→GRPO {sgs} → {sgs-bs:+d}")
PY
