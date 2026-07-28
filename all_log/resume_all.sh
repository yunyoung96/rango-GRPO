#!/bin/bash
# 서버 재부팅(2026-07-14 ~10:10 UTC) 후 재개 체인.
# GPU 를 절대 나눠 쓰지 않는다 — 벽시계 600초 타임아웃 평가라 경합 = 결과 왜곡.
#
# 재부팅 시점 상태:
#   rango-grpo       179/180 (오염수습 중 idx 38 하나 남기고 중단)  net +7
#   bfs-a1           180/180 완료                                    net -4
#   rango-portfolio    0/180 (시작만 하고 드라이버 사망)
#   rango baseline     미시작   ← 가장 중요(하드웨어 교란 분리)
#   SOTA 3종           미시작
set -u
LOG=all_log/resume_all.log
WORKERS=${WORKERS:-2}
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

report(){  # report <alias> <dir>
  python3 - "$1" "$2" <<'PY' 2>&1 | tee -a "$LOG"
import json, sys, math
a, d = sys.argv[1], sys.argv[2]
r = json.load(open(f"{d}/summary.json"))["results"]
s = sum(1 for x in r if x.get("success")); o = sum(1 for x in r if x.get("original_success"))
g = [x['idx'] for x in r if x.get('success') and not x.get('original_success')]
c = [x['idx'] for x in r if x.get('original_success') and not x.get('success')]
b, cc = len(g), len(c); n = b + cc
p = min(2*sum(math.comb(n,k) for k in range(0, min(b,cc)+1))/2**n, 1.0) if n else 1.0
print(f"■ {a}: {s}/{len(r)} | published {o} | net {s-o:+d} | gain {b} 회귀 {cc} {c} | McNemar p={p:.4f}")
PY
}

say "===== 재부팅 후 재개 시작 ====="

# ── 1. rango-grpo 오염수습 마무리 (idx 38 하나) ──────────────────────
D_GRPO=all_results/20260713-120829_rango-grpo
say "▶ 1/4  rango-grpo 오염수습 마무리 (누락 idx 38)"
python3 scripts/run_all.py --alias rango-grpo --num 180 --timeout 600 --workers "$WORKERS" \
  --out "$D_GRPO" --description "robustness @180 (contested re-run, GPU 독점)" >> "$LOG" 2>&1
report rango-grpo "$D_GRPO"
say "◀ rango-grpo 확정"

# ── 2. ★ rango baseline @180 — 하드웨어 교란 분리 ────────────────────
# results/rango.json(published)은 RTX 2080 Ti + CPU 1코어에서 나온 결과다.
# 우리는 RTX 6000 Ada + 96코어. 타임아웃은 똑같이 600초 **벽시계**.
# → 같은 600초에 훨씬 많은 tactic 을 시도한다. 이 대조군이 없으면 rango-grpo 의 "+7" 이
#   GRPO 덕분인지 하드웨어 덕분인지 분해가 불가능하다.
say "▶ 2/4  ★ rango baseline @180 (가장 중요한 대조군)"
python3 scripts/run_all.py --alias rango --num 180 --timeout 600 --workers "$WORKERS" \
  --description "우리 자체 rango baseline @180 (RTX 6000 Ada). published rango.json 은 2080Ti 기준" \
  >> "$LOG" 2>&1
D_BASE=$(ls -dt all_results/*_rango | head -1)
report rango "$D_BASE"
python3 - "$D_BASE" "$D_GRPO" <<'PY' 2>&1 | tee -a "$LOG"
import json, sys
def stat(d):
    r=json.load(open(f"{d}/summary.json"))["results"]
    return (sum(1 for x in r if x.get("success")),
            sum(1 for x in r if x.get("original_success")), len(r))
ours,pub,n = stat(sys.argv[1]); grpo,_,_ = stat(sys.argv[2])
print(f"\n★★ 하드웨어 교란 분리 (n={n})")
print(f"  published rango (2080 Ti)   : {pub}")
print(f"  우리 rango (RTX 6000 Ada)   : {ours}   → 하드웨어 효과 {ours-pub:+d}")
print(f"  rango-grpo (RTX 6000 Ada)   : {grpo}   → **진짜 GRPO 효과 {grpo-ours:+d}**")
print(f"  (지금까지 보고된 {grpo-pub:+d} 중 {ours-pub:+d} 는 하드웨어였다)")
PY
say "◀ rango baseline 완료"

# ── 3. SOTA 3종 + 재샘플링 ───────────────────────────────────────────
say "▶ 3/4  SOTA 3종 + 재샘플링"
bash all_log/run_sota3.sh
say "◀ SOTA 3종 완료"

# ── 4. rango-portfolio @180 (우선순위 낮음) ──────────────────────────
# bfs-a1 이 @40 +4 → @180 -4 로 뒤집힌 걸 보면 탐색계열은 @180 에서 음수일 공산이 크다.
say "▶ 4/4  rango-portfolio @180 (우선순위 낮음)"
python3 scripts/run_all.py --alias rango-portfolio --num 180 --timeout 600 --workers "$WORKERS" \
  --description "robustness @180" >> "$LOG" 2>&1
report rango-portfolio "$(ls -dt all_results/*_rango-portfolio | head -1)"

say "===== 전체 완료 ====="
grep '■\|★★' "$LOG"
