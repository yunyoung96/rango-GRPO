#!/usr/bin/env python3
"""경로집합 Jaccard 거리가 **진짜 metric** 인지 확인한다.

    d_J(s,t) = 1 − |S(s) ∩ S(t)| / |S(s) ∪ S(t)|          S = 루트→노드 심볼 경로

## 왜 이게 필요한가

지금 쓰는 `1 − F₁`(AU-Dice)은 **삼각부등식을 어긴다**(P8 에서 반례 확인). 그래서
"거리" 라고 부를 수 없고, 영집합(핵)만 쓸 수 있었다. metric 이면 두 가지가 생긴다.

    ① 수학적으로 **거리 공간**이 되어 값 자체에 의미가 생긴다
    ② VP-tree·cover-tree 로 가지치기가 되고, 집합 Jaccard 라 **MinHash+LSH** 를
       바로 쓸 수 있다 → 부분선형 검색 → `tfidf` 1차 필터가 필요 없어진다

## 검사

    M1 비음수      d ≥ 0
    M2 동일성      d(s,t) = 0  ⟺  s ≡α t          ← eqx 의 영집합과 **같아야** 한다
    M3 대칭성      d(s,t) = d(t,s)
    M4 삼각부등식  d(s,u) ≤ d(s,t) + d(t,u)        ← AU-Dice 가 어기던 것
    M5 유계        d ≤ 1
    M6 비교        같은 삼중쌍에서 1−F₁ 은 몇 번 어기나

사용: PYTHONPATH=src python3 scripts/verify_metric.py [표본 항 수]
"""
import itertools
import logging
import os
import random
import sys

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from tactic_gen.tier_rank import (path_set, jaccard_dist, prem_stmt,  # noqa: E402
                                  au_f_alpha, alpha_stmt)
from tactic_gen.applicable import decompose  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 120
EPS = 1e-12
fails = []


def ok(c, name, detail=""):
    print(f"   {'✓' if c else '✗'} {name}" + (f"   {detail}" if detail else ""))
    if not c:
        fails.append(name)


# ── 실제 Coq 명제로 항을 모은다 ──────────────────────────────────────────
import json  # noqa: E402
import glob  # noqa: E402

tys = []
for f in sorted(glob.glob("data/cut_chunks_train/c_*.jsonl"))[:4]:
    for ln in open(f, errors="ignore"):
        try:
            d = json.loads(ln)
        except Exception:
            continue
        if d.get("kind") == "stmt" and d.get("ty"):
            tys.append(d["ty"])
        if len(tys) >= N * 4:
            break
    if len(tys) >= N * 4:
        break
random.seed(0)
random.shuffle(tys)

terms = []
for ty in tys:
    t = alpha_stmt(decompose(f"Lemma _x : {ty}."))
    if t is not None:
        terms.append((ty, t, path_set(t)))
    if len(terms) >= N:
        break
print(f"■ 실제 Coq 명제 {len(terms)}개로 검사\n")

sizes = [len(ps) for _, _, ps in terms]
print(f"   경로집합 크기  중앙 {sorted(sizes)[len(sizes)//2]} · 최소 {min(sizes)} · 최대 {max(sizes)}\n")

# ── M1·M3·M5 ────────────────────────────────────────────────────────────
ok(all(jaccard_dist(a, b) >= -EPS for _, _, a in terms for _, _, b in terms),
   "M1 비음수  d ≥ 0")
ok(all(abs(jaccard_dist(a, b) - jaccard_dist(b, a)) < EPS
       for _, _, a in terms for _, _, b in terms),
   "M3 대칭성  d(s,t) = d(t,s)")
ok(all(jaccard_dist(a, b) <= 1 + EPS for _, _, a in terms for _, _, b in terms),
   "M5 유계  d ≤ 1")

# ── M2 동일성: d=0 ⟺ 항이 같다 (= α-동치) ────────────────────────────────
bad2 = []
for (t1, x1, a), (t2, x2, b) in itertools.combinations(terms, 2):
    z = jaccard_dist(a, b) < EPS
    same = (x1 == x2)
    if z != same:
        bad2.append((t1[:40], t2[:40], z, same))
ok(not bad2, "M2 동일성  d = 0  ⟺  s ≡α t   (eqx 의 영집합과 일치)",
   f"{len(terms)*(len(terms)-1)//2:,}쌍" if not bad2 else str(bad2[:1]))

# ── M4 삼각부등식 (전수) ─────────────────────────────────────────────────
tri_bad = 0
tri_ex = None
n_tri = 0
for (_, _, a), (_, _, b), (_, _, c) in itertools.islice(
        itertools.permutations(terms, 3), 400000):
    n_tri += 1
    if jaccard_dist(a, c) > jaccard_dist(a, b) + jaccard_dist(b, c) + 1e-9:
        tri_bad += 1
        if tri_ex is None:
            tri_ex = (round(jaccard_dist(a, c), 4),
                      round(jaccard_dist(a, b) + jaccard_dist(b, c), 4))
ok(tri_bad == 0, "M4 삼각부등식  d(s,u) ≤ d(s,t) + d(t,u)",
   f"{n_tri:,} 삼중쌍 전수" if not tri_bad else f"위반 {tri_bad}건 예: {tri_ex}")

# ── M6 비교: 같은 삼중쌍에서 1−F₁ 은? ────────────────────────────────────
f_bad = 0
f_ex = None
for (_, x1, _), (_, x2, _), (_, x3, _) in itertools.islice(
        itertools.permutations([t for t in terms], 3), 400000):
    dac = 1 - au_f_alpha(x1, x3)
    dab = 1 - au_f_alpha(x1, x2)
    dbc = 1 - au_f_alpha(x2, x3)
    if dac > dab + dbc + 1e-9:
        f_bad += 1
        if f_ex is None:
            f_ex = (round(dac, 4), round(dab + dbc, 4))
print()
print(f"■ M6 비교 — 같은 삼중쌍에서")
print(f"   경로집합 Jaccard   위반 {tri_bad:,} / {n_tri:,}")
print(f"   1 − F₁ (AU-Dice)   위반 {f_bad:,} / {n_tri:,}"
      + (f"   예: d(a,c)={f_ex[0]} > {f_ex[1]}" if f_ex else ""))
print(f"   → 그래서 F₁ 은 '거리' 가 아니라 **영집합만** 쓸 수 있었다.")

print()
print("=" * 66)
if fails:
    print("✗ 실패:", fails)
    sys.exit(1)
print("✓ 경로집합 Jaccard 는 metric 이다")
