#!/usr/bin/env python3
"""반유니피케이션 점수의 **수학적 성질**을 진술하고 실측으로 확인한다.

## 유도 (생성)

포섭 순서 `s ⊑ t ⟺ ∃σ. σ(s)=t` 에서 반유니피케이션이 meet(⊓).
`m = size(concl ⊓ goal)` · `c = size_rigid(concl)` · `n = size(goal)` 로 두면

    P = m/c   premise 가 주장하는 것 중 쓰인 비율   (정밀도)
    R = m/n   goal 중 설명된 비율                   (재현율)

    F_β = (1+β²)PR/(β²P+R) = (1+β²)·m / (c + β²·n)          ← 기호계산으로 확인
    1 − F_β = [(c−m) + β²(n−m)] / (c + β²n) = (res + β²·gen)/(c + β²n)
    1 − F₁  = (c + n − 2m)/(c + n)                           ← 격자 대칭거리 d / (c+n)

**즉 `λ = β²`.** 손으로 쓴 `D_λ = res + λ·gen` 과 F-측도는 **같은 족**이고,
F 가 정준 정규화 `(c + λn)` 를 공짜로 준다. λ 를 따로 고를 필요가 없어진다.

## 확인하는 성질

  P1 치역        0 ≤ F_β ≤ 1
  P2 동일성      F_β = 1  ⟺  m = c = n   (concl 이 goal 과 α-동치)
  P3 공허 배제   R = 0 ⟹ F_β = 0  (β 무관)      ← λ=0 붕괴가 구조적으로 제거된다
  P4 단조성      m 에 증가 · c 에 감소 · n 에 감소
  P5 격자 단조성 p₁ ⊑ p₂ ⊑ g 이면 F(p₂,g) ≥ F(p₁,g)
                 (적용되는 것들 중 **더 구체적인** 쪽이 높다)
  P6 경계        β→0 이면 F→P (공허가 만점 = 붕괴) · β→∞ 이면 F→R
  P7 항등식      1 − F₁ = d/(c+n) · F_β = (1+β²)m/(c+β²n)
  P8 거리성      1−Dice 는 삼각부등식을 어긴다(반례 제시) · Jaccard 는 만족

사용: PYTHONPATH=src python3 scripts/verify_au_props.py [표본수]
"""
import itertools
import logging
import os
import random
import sys

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from tactic_gen.tier_rank import (au_pr, sig_au_f, goal_struct,  # noqa: E402
                                  prem_struct, _rigid_size, _au_dir, shape)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
BETAS = (0.25, 0.5, 1.0, 2.0, 4.0)
EPS = 1e-9
fails = []


def ok(cond, name, detail=""):
    print(f"   {'✓' if cond else '✗'} {name}" + (f"   {detail}" if detail else ""))
    if not cond:
        fails.append(name)


# ── 순수 대수 성질: m, c, n 을 직접 흔든다 ────────────────────────────────
def F(m, c, n, b):
    den = c + b * b * n
    return (1 + b * b) * m / den if den > 0 else 0.0


print("■ 대수 성질 (m ≤ min(c,n) 인 모든 조합을 훑는다)\n")
combos = [(m, c, n) for c in range(1, 13) for n in range(1, 13)
          for m in range(0, min(c, n) + 1)]
print(f"   조합 {len(combos):,}개 × β {len(BETAS)}종\n")

ok(all(-EPS <= F(m, c, n, b) <= 1 + EPS for m, c, n in combos for b in BETAS),
   "P1 치역  0 ≤ F_β ≤ 1")

ok(all((abs(F(m, c, n, b) - 1) < EPS) == (m == c == n)
       for m, c, n in combos for b in BETAS),
   "P2 동일성  F_β = 1 ⟺ m = c = n")

ok(all(F(0, c, n, b) == 0 for c in range(1, 13) for n in range(1, 13) for b in BETAS),
   "P3 공허 배제  m = 0 ⟹ F_β = 0  (β 무관)")

mono_m = all(F(m, c, n, b) <= F(m + 1, c, n, b) + EPS
             for m, c, n in combos if m < min(c, n) for b in BETAS)
mono_c = all(F(m, c + 1, n, b) <= F(m, c, n, b) + EPS
             for m, c, n in combos for b in BETAS)
mono_n = all(F(m, c, n + 1, b) <= F(m, c, n, b) + EPS
             for m, c, n in combos for b in BETAS)
ok(mono_m and mono_c and mono_n,
   "P4 단조성  m↑ 증가 · c↑ 감소 · n↑ 감소")

# P5: p₁ ⊑ p₂ ⊑ g  ⟹  m_i = c_i (둘 다 적용됨), c₁ ≤ c₂
p5 = all(F(c1, c1, n, b) <= F(c2, c2, n, b) + EPS
         for n in range(1, 13) for c1 in range(0, n + 1)
         for c2 in range(c1, n + 1) for b in BETAS)
ok(p5, "P5 격자 단조성  p₁ ⊑ p₂ ⊑ g ⟹ F(p₂) ≥ F(p₁)",
   "적용되는 것 중 더 구체적인 쪽이 높다")

lim0 = all(abs(F(m, c, n, 1e-4) - m / c) < 1e-3
           for m, c, n in combos if c > 0)
limI = all(abs(F(m, c, n, 1e4) - m / n) < 1e-3
           for m, c, n in combos if n > 0)
ok(lim0 and limI, "P6 경계  β→0 이면 F→P · β→∞ 이면 F→R",
   "β→0 에서 m=c(공허)면 F→1 — 붕괴 모드")

ok(all(abs((1 - F(m, c, n, 1.0)) - (c + n - 2 * m) / (c + n)) < EPS
       for m, c, n in combos),
   "P7 항등식  1 − F₁ = (c+n−2m)/(c+n) = d/(c+n)")


# ── P8 거리성: Dice 는 삼각부등식을 어긴다 (반례를 실제로 찾는다) ──────────
def dice_d(a, b_):
    inter = len(a & b_)
    s = len(a) + len(b_)
    return 1 - 2 * inter / s if s else 0.0


def jac_d(a, b_):
    u = len(a | b_)
    return 1 - len(a & b_) / u if u else 0.0


random.seed(0)
uni = list(range(6))
sets = [frozenset(s) for k in range(1, 5) for s in itertools.combinations(uni, k)]
dice_bad = jac_bad = 0
dice_ex = None
for a, b_, c_ in itertools.islice(itertools.product(sets, repeat=3), 60000):
    if dice_d(a, c_) > dice_d(a, b_) + dice_d(b_, c_) + EPS:
        dice_bad += 1
        if dice_ex is None:
            dice_ex = (set(a), set(b_), set(c_),
                       round(dice_d(a, c_), 3),
                       round(dice_d(a, b_) + dice_d(b_, c_), 3))
    if jac_d(a, c_) > jac_d(a, b_) + jac_d(b_, c_) + EPS:
        jac_bad += 1
print()
print("■ 거리성 (P8)\n")
print(f"   1−Dice  삼각부등식 위반 {dice_bad:,}건",
      f"— 예: A={dice_ex[0]} B={dice_ex[1]} C={dice_ex[2]}  "
      f"d(A,C)={dice_ex[3]} > {dice_ex[4]}" if dice_ex else "")
print(f"   1−Jaccard 위반 {jac_bad:,}건")
print("   → 진짜 metric 이 필요하면 Jaccard `m/(c+n−m)` 를 쓴다.")
print("     랭킹은 순위 비교만 쓰므로 Dice(=F₁)로 충분하다.")

# ── 실제 Coq 데이터로 성질 재확인 ─────────────────────────────────────────
print()
print("■ 실제 Coq 항으로 확인\n")
CASES = [
    ("완전 동일", "a + b = b + a", "Lemma foo : a + b = b + a."),
    ("인스턴스", "a + b = b + a", "Lemma add_comm x y : x + y = y + x."),
    ("더 구체적", "a + b = b + a", "Lemma c1 x : x + b = b + x."),
    ("rewrite 부분항", "f (a + b) = c", "Lemma ac x y : x + y = y + x."),
    ("연산자 다름", "a + b = b + a", "Lemma bar x y : x * y = y * x."),
    ("무관", "a + b = b + a", "Lemma unrel : bijection f."),
    ("공허", "a + b = b + a", "Lemma triv (P:Prop) : P."),
]
rows = []
for tag, g, p in CASES:
    gs, ps = goal_struct("\n" + g), prem_struct(p)
    if gs is None or ps is None:
        continue
    P, R = au_pr(gs, ps)
    rows.append((tag, P, R, [sig_au_f(gs, ps, b) for b in BETAS]))
hdr = "   {:16s} {:>6} {:>6} |".format("", "P", "R") + \
      "".join(f"{'F'+str(b):>7}" for b in BETAS)
print(hdr)
for tag, P, R, fs in rows:
    print(f"   {tag:16s} {P:6.3f} {R:6.3f} |" + "".join(f"{v:7.3f}" for v in fs))

# 실제 데이터에서도 순위가 β 에 무관한가
orders = {b: [t for t, *_ in sorted(rows, key=lambda r: -r[3][i])]
          for i, b in enumerate(BETAS)}
same = len({tuple(v) for v in orders.values()}) == 1
print()
ok(same, "P9 순위가 β 에 무관하다 (이 표본에서)",
   " > ".join(orders[1.0]))

vac = [r for r in rows if r[0] == "공허"]
ok(bool(vac) and all(v < EPS for v in vac[0][3]),
   "P3′ 공허 케이스가 모든 β 에서 0")

print()
print("=" * 62)
if fails:
    print("✗ 실패:", fails)
    sys.exit(1)
print("✓ 모든 성질 확인")
