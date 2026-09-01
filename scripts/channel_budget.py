#!/usr/bin/env python3
"""★★ **채널별 예산 배분** — tactic 마다 필요한 집합이 다른데 프롬프트는 하나다.

## 문제

`apply` 와 `rewrite` 가 요구하는 집합은 자카드 **5.0%** 로 거의 안 겹친다.
그런데 프롬프트에 실을 수 있는 premise 는 K 개뿐이고, **어느 tactic 을 쓸지는
모른 채로** 골라야 한다. 지금은 다섯 채널을 합쳐 하나로 정렬한다 — 채널 정보를
버리는 것이고, 채널마다 필요한 개수가 다르다는 사실도 무시한다.

## 정식화

    p_t          tactic t 가 나올 사전확률 (말뭉치 빈도)
    F_c(b)       채널 c 에서 상위 b 개 안에 gold 이 들어올 확률 (실측 CDF)
    b_c          채널 c 에 줄 슬롯 수,  Σ b_c ≤ K

    최대화   E[gold 이 프롬프트에 있음] = Σ_t p_t · F_{ch(t)}(b_{ch(t)})

이건 **물채우기(water-filling)** 다. 한계이득 `p_t · [F(b+1) − F(b)]` 가
가장 큰 채널에 한 칸씩 준다. 한계이득이 같아질 때까지.

## 왜 이게 중요한가 (실측)

    unfold    @10 이미 98.5% → 슬롯을 더 줘도 얻는 게 없다
    destruct  @10 46.0% · @50 80.0% → 슬롯을 주면 크게 오른다

균등하게 나누거나 한 줄로 합치면 **unfold 에 낭비하고 destruct 를 굶긴다**.

사용: python3 scripts/channel_budget.py [K]
"""
import sys, math, collections

K = int(sys.argv[1]) if len(sys.argv) > 1 else 100

#: gold tactic 사전확률 — rand200 실측 (외부 이름을 쓰는 스텝 1,464개 기준)
PRIOR = {"apply": 0.320, "rewrite": 0.221, "destruct": 0.171,
         "unfold": 0.102, "case_ind": 0.043, "exact": 0.023}

#: 실측 CDF — (@10, @20, @50, @100). 나이브베이즈 랭커, CompCert 450지점
CDF = {
    "apply":    {10: 0.750, 20: 0.817, 50: 0.850, 100: 0.917},
    "rewrite":  {10: 0.667, 20: 0.754, 50: 0.807, 100: 0.860},
    "destruct": {10: 0.460, 20: 0.620, 50: 0.800, 100: 0.860},
    "unfold":   {10: 0.985, 20: 1.000, 50: 1.000, 100: 1.000},
    "case_ind": {10: 0.545, 20: 0.636, 50: 0.636, 100: 0.818},
    "exact":    {10: 1.000, 20: 1.000, 50: 1.000, 100: 1.000},
}


def F(t, b):
    """상위 b 개 안에 gold 이 있을 확률 — 측정점 사이는 로그 보간."""
    if b <= 0: return 0.0
    pts = sorted(CDF[t].items())
    if b <= pts[0][0]:
        return CDF[t][pts[0][0]] * (math.log1p(b) / math.log1p(pts[0][0]))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if b <= x1:
            w = (math.log(b) - math.log(x0)) / (math.log(x1) - math.log(x0))
            return y0 + w * (y1 - y0)
    return pts[-1][1]


def waterfill(K):
    """한계이득이 가장 큰 채널에 한 칸씩 준다."""
    b = {t: 0 for t in PRIOR}
    for _ in range(K):
        best, gain = None, -1.0
        for t in PRIOR:
            g = PRIOR[t] * (F(t, b[t] + 1) - F(t, b[t]))
            if g > gain: best, gain = t, g
        b[best] += 1
    return b


def expected(b):
    return sum(PRIOR[t] * F(t, b[t]) for t in PRIOR)


if __name__ == "__main__":
    n = len(PRIOR)
    schemes = {
        "① 균등 배분": {t: K // n for t in PRIOR},
        "② 사전확률 비례": {t: max(1, int(K * PRIOR[t])) for t in PRIOR},
        "③ ★물채우기": waterfill(K),
    }
    # ④ 한 줄로 합치기 — 채널 구분 없이 상위 K. 각 tactic 은 자기 채널이
    #    전체에서 차지하는 비율만큼만 슬롯을 얻는다고 근사한다.
    share = {"apply": 0.19, "rewrite": 0.23, "destruct": 0.28,
             "unfold": 0.004, "case_ind": 0.28, "exact": 0.016}
    schemes["④ 합쳐서 상위K"] = {t: max(0, int(K * share[t])) for t in PRIOR}

    print(f"■ 프롬프트 슬롯 K={K} · 채널별 배분 비교\n")
    print(f"   {'방식':16s}{'E[gold 실림]':>14s}   배분")
    for name, b in schemes.items():
        alloc = " ".join(f"{t[:4]}={b[t]}" for t in
                         sorted(PRIOR, key=lambda x: -PRIOR[x]))
        print(f"   {name:16s}{expected(b)*100:12.1f}%   {alloc}")
    print(f"\n   ── 물채우기가 준 슬롯과 그때의 채널별 적중 ──")
    b = schemes["③ ★물채우기"]
    print(f"   {'채널':10s}{'사전확률':>9s}{'슬롯':>7s}{'적중':>9s}{'한계이득':>11s}")
    for t in sorted(PRIOR, key=lambda x: -PRIOR[x]):
        mg = PRIOR[t] * (F(t, b[t] + 1) - F(t, b[t]))
        print(f"   {t:10s}{PRIOR[t]*100:8.1f}%{b[t]:7d}{F(t,b[t])*100:8.1f}%{mg*1000:10.3f}‰")
