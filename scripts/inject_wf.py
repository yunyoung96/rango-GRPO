#!/usr/bin/env python3
"""★★ 프롬프트 주입기 — **채널별 물채우기 + 나이브베이즈 순위**.

실측이 두 번 말했다: 필터가 gold 을 96.5% 찾아내도, **합쳐서 tf-idf 로 정렬**하면
프롬프트에서는 오히려 손해다(top8 39.2% → 37.0%).

이유는 배분이다:
    ④ 합쳐서 상위K   E[gold 실림] 58.0%   ← 지금까지 한 것. unfold 슬롯 0칸
    ③ 물채우기       E[gold 실림] 69.5%

여기서는 두 가지를 한다:
    ① 채널마다 **자기 순위**를 매긴다 (나이브베이즈 · 채널 특징 포함)
    ② 슬롯을 **한계이득이 큰 채널부터** 한 칸씩 준다 (물채우기)

프롬프트 형식은 안 바꾼다 — 하나의 `[PREMISES]` 목록이다. 학습 재실행이 필요 없다.
"""
import json, math, collections

#: gold tactic 사전확률 — rand200 실측
PRIOR = {"ap": 0.320, "rw": 0.221, "ds": 0.171, "uf": 0.102, "dc": 0.043, "in": 0.023}
#: 채널별 CDF 측정점 — 나이브베이즈 랭커, CompCert
CDF = {"ap": {10: .750, 20: .817, 50: .850, 100: .917},
       "rw": {10: .667, 20: .754, 50: .807, 100: .860},
       "ds": {10: .460, 20: .620, 50: .800, 100: .860},
       "uf": {10: .985, 20: 1.0, 50: 1.0, 100: 1.0},
       "dc": {10: .545, 20: .636, 50: .636, 100: .818},
       "in": {10: 1.0, 20: 1.0, 50: 1.0, 100: 1.0}}


def _F(c, b):
    if b <= 0: return 0.0
    pts = sorted(CDF[c].items())
    if b <= pts[0][0]:
        return CDF[c][pts[0][0]] * (math.log1p(b) / math.log1p(pts[0][0]))
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if b <= x1:
            w = (math.log(b) - math.log(x0)) / (math.log(x1) - math.log(x0))
            return y0 + w * (y1 - y0)
    return pts[-1][1]


def waterfill(K, avail):
    """슬롯 K개를 한계이득 순으로 나눈다. `avail[c]` = 그 채널의 후보 수."""
    b = {c: 0 for c in PRIOR}
    for _ in range(K):
        best, gain = None, -1.0
        for c in PRIOR:
            if b[c] >= avail.get(c, 0): continue      # 후보가 동나면 제외
            g = PRIOR[c] * (_F(c, b[c] + 1) - _F(c, b[c]))
            if g > gain: best, gain = c, g
        if best is None: break
        b[best] += 1
    return b


def pick(chan, score_of, K=100):
    """채널별로 자기 순위를 매기고, 물채우기 배분만큼 뽑아 합친다.

    `chan`     {채널: [이름…]}
    `score_of` 이름 → 점수 (높을수록 위). 나이브베이즈 점수를 준다.
    """
    ranked = {c: sorted(set(v), key=lambda x: -score_of(x))
              for c, v in chan.items() if v}
    b = waterfill(K, {c: len(v) for c, v in ranked.items()})
    out, seen = [], set()
    # 채널을 번갈아 가며 뽑는다 — 앞쪽이 절단에서 살아남으므로 골고루 섞는다
    idx = {c: 0 for c in ranked}
    while len(out) < K:
        moved = False
        for c in sorted(PRIOR, key=lambda x: -PRIOR[x]):
            if c not in ranked: continue
            if idx[c] >= b.get(c, 0) or idx[c] >= len(ranked[c]): continue
            nm = ranked[c][idx[c]]; idx[c] += 1; moved = True
            if nm not in seen:
                seen.add(nm); out.append(nm)
                if len(out) >= K: break
        if not moved: break
    return out, b
