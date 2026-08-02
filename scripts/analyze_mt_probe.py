#!/usr/bin/env python3
"""MT_PROBE 결과 분석 → A0(에러없이) vs A1(에러주석) 고침율 + 에러유형별 + MD 리포트.
사용: python3 scripts/analyze_mt_probe.py <probe.jsonl> [out.md]"""
import json, sys, os, math
from collections import Counter, defaultdict


def mcnemar_exact_p(b, c):
    """짝지은 A0/A1 불일치쌍(b=only_a1, c=only_a0)에 대한 양측 McNemar 정확검정(이항 sign test)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    # 양측 p = 2 * P(X <= k), X~Binom(n, 0.5), 1로 클립
    tail = sum(math.comb(n, i) for i in range(k + 1)) * (0.5 ** n)
    return min(1.0, 2 * tail)


def wilson_ci(x, n, z=1.96):
    """비율 x/n의 Wilson 95% 신뢰구간(%)."""
    if n == 0:
        return (0.0, 0.0)
    p = x / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * (c - h), 100 * (c + h))

path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/mt_probe.jsonl"
out_md = sys.argv[2] if len(sys.argv) > 2 else None
rows = []
if os.path.exists(path):
    for l in open(path):
        l = l.strip()
        if l:
            try: rows.append(json.loads(l))
            except: pass

N = len(rows)
if N == 0:
    print("프로브 기록 없음:", path); sys.exit(0)

a0 = sum(1 for r in rows if r.get("a0_fixed"))
a1 = sum(1 for r in rows if r.get("a1_fixed"))
both = sum(1 for r in rows if r.get("a0_fixed") and r.get("a1_fixed"))
only_a1 = sum(1 for r in rows if r.get("a1_fixed") and not r.get("a0_fixed"))
only_a0 = sum(1 for r in rows if r.get("a0_fixed") and not r.get("a1_fixed"))
neither = sum(1 for r in rows if not r.get("a0_fixed") and not r.get("a1_fixed"))

# 에러 유형별
by = defaultdict(lambda: {"n": 0, "a0": 0, "a1": 0})
for r in rows:
    t = r.get("error_type", "other")
    by[t]["n"] += 1
    by[t]["a0"] += 1 if r.get("a0_fixed") else 0
    by[t]["a1"] += 1 if r.get("a1_fixed") else 0

meaningful = sum(by[t]["n"] for t in ("unify", "not_found"))
useless = sum(by[t]["n"] for t in ("empty", "syntax"))

def pct(x, n): return f"{100*x/max(n,1):.1f}%"

L = []
L.append("# multi-turn 에러 피드백 A/B 프로브 결과")
L.append("")
L.append(f"작성 데이터: `{path}` · 케이스 {N}개 (executor=subgoal 1.3B, INVALID state, 같은 예산 n={rows[0].get('n')}샘플)")
L.append("")
L.append("## 핵심 — A0(에러 없이) vs A1(에러 주석 재주입)")
L.append("")
c0lo, c0hi = wilson_ci(a0, N); c1lo, c1hi = wilson_ci(a1, N)
L.append("| | 고침(valid 만듦) | 비율 | 95% CI(Wilson) |")
L.append("|---|---|---|---|")
L.append(f"| A0 (대조: [STATE]만 재샘플) | {a0}/{N} | **{pct(a0,N)}** | [{c0lo:.1f}, {c0hi:.1f}]% |")
L.append(f"| A1 (처리: +실패tactic·에러 주석) | {a1}/{N} | **{pct(a1,N)}** | [{c1lo:.1f}, {c1hi:.1f}]% |")
L.append(f"| Δ (A1−A0) | {a1-a0:+d} | **{100*(a1-a0)/max(N,1):+.1f}pp** | (CI 겹치면 무의미) |")
L.append("")
L.append("### 짝지은 변화 (같은 케이스에서)")
L.append(f"- A1만 고침(A0 실패): **{only_a1}** ← 에러가 도운 순증거")
L.append(f"- A0만 고침(A1 실패): **{only_a0}** ← 주석이 오히려 방해(OOD 노이즈)")
L.append(f"- 둘 다 고침: {both} · 둘 다 실패: {neither}")
if only_a1 + only_a0 > 0:
    net = only_a1 - only_a0
    L.append(f"- 순 효과 = {only_a1}−{only_a0} = **{net:+d}** ({'A1 우세' if net>0 else 'A0 우세' if net<0 else '동률'})")
L.append("")
L.append("## 에러 유형별 (품질 + 유형별 고침율)")
L.append("")
L.append("| 유형 | 케이스 | A0 고침 | A1 고침 | A1−A0 |")
L.append("|---|---|---|---|---|")
for t in sorted(by, key=lambda k: -by[k]["n"]):
    d = by[t]
    L.append(f"| {t} | {d['n']} | {pct(d['a0'],d['n'])} | {pct(d['a1'],d['n'])} | {100*(d['a1']-d['a0'])/max(d['n'],1):+.1f}pp |")
L.append("")
L.append(f"- **의미적 에러**(unify+not_found) = {meaningful}/{N} ({pct(meaningful,N)}) — 모델이 고칠 단서 있음")
L.append(f"- **무의미 에러**(empty+syntax) = {useless}/{N} ({pct(useless,N)}) — 재주입해도 소용 없을 가능성")
L.append("")
L.append("## 판정 (McNemar 정확검정 — paired)")
delta = 100*(a1-a0)/max(N,1)
p = mcnemar_exact_p(only_a1, only_a0)   # b=only_a1, c=only_a0
disc = only_a1 + only_a0
L.append("")
L.append(f"- 불일치쌍: only_A1={only_a1}, only_A0={only_a0} (합 {disc}) → **McNemar 양측 p = {p:.3f}**")
L.append(f"- 순 효과 Δ = {delta:+.1f}pp ({a1-a0:+d}케이스). ※ paired라 Δ의 유의성은 p값이 판정(절대 pp 아님).")
L.append("")
# 판정: 유의성(p<0.05) + 방향
if disc < 8:
    verdict = (f"**표본 부족 (불일치쌍 {disc}개) → 판정 보류.** paired 검정력이 낮아 결론 불가. "
               f"cap↑ 또는 정리↑로 불일치쌍 ≥15 확보 후 재측정 권장.")
elif p < 0.05 and only_a1 > only_a0:
    verdict = (f"**A1 > A0, 유의 (p={p:.3f})** → 1.3B가 에러를 활용해 고치는 능력이 통계적으로 있음. "
               f"multi-turn GRPO(설계 B) 진행 가치 있음. (효과크기 Δ={delta:+.1f}pp)")
elif p < 0.05 and only_a0 > only_a1:
    verdict = (f"**A1 < A0, 유의 (p={p:.3f})** → 에러 주석이 오히려 방해(강한 OOD). "
               f"in-format 주석 방식은 접고, 학습 없이는 무효.")
else:
    verdict = (f"**A0 ≈ A1, 유의차 없음 (p={p:.3f})** → 인퍼런스만으론 에러 활용 능력이 통계적으로 확인 안 됨(Δ={delta:+.1f}pp는 노이즈). "
               f"→ 설계 B(학습으로 가르치기)로 가거나, 효과가 크지 않으면 접기. "
               f"단 '의미적 에러 비율'(위)이 높으면 학습판은 시도해볼 여지.")
L.append(verdict)
L.append("")
L.append(f"> 참고: p<0.05를 얻으려면 대략 불일치쌍이 한쪽으로 크게 쏠려야 함(예 12:2, 15:4). "
         f"단순 순 +3~4케이스(≈+3pp)는 p≈0.3~0.4로 **노이즈**라 '능력 있음'으로 못 봄.")
L.append("")
L.append("## 실제 예시 (A1이 고친 것 / 못 고친 것)")
ex_win = [r for r in rows if r.get("a1_fixed") and not r.get("a0_fixed")][:3]
ex_fail = [r for r in rows if not r.get("a1_fixed") and not r.get("a0_fixed")][:3]
if ex_win:
    L.append("### A1이 고침 (에러 준 덕에):")
    for r in ex_win:
        L.append(f"- 실패: `{r.get('failed_tactic')}` — 에러[{r.get('error_type')}]: {r.get('error')}")
        L.append(f"  → A1 고침: `{r.get('a1_tactic')}`")
if ex_fail:
    L.append("### 둘 다 실패 (에러 줘도 못 고침):")
    for r in ex_fail:
        L.append(f"- 실패: `{r.get('failed_tactic')}` — 에러[{r.get('error_type')}]: {r.get('error')}")
L.append("")
L.append("관련: [[MULTITURN_DESIGN]] · [[CLOSING_FAILURE_ANALYSIS]] · [[RANKING_GOLD_VS_APPLIED]]")

report = "\n".join(L)
print(report)
if out_md:
    with open(out_md, "w") as f:
        f.write(report + "\n")
    print(f"\n저장: {out_md}")
# 요약 한 줄(로그용)
print(f"\nSUMMARY N={N} a0={pct(a0,N)} a1={pct(a1,N)} delta={delta:+.1f}pp onlyA1={only_a1} onlyA0={only_a0} mcnemar_p={p:.3f} meaningful={pct(meaningful,N)}")
