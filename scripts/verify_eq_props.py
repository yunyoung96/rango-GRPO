#!/usr/bin/env python3
"""`eq` 랭커의 **수학적 성질**을 진술하고 확인한다.

    score_eq(p) = 1/(K+rank_tfidf(p)) + 1/(K+rank_C'(p)) + W·1[canon(concl p) = canon(g)]

주장은 셋이다.

  L (사전식)   W 는 가중치가 아니라 **사전식 분리자**다.
               RRF 두 항의 합은 (0, 2/K] 에 갇히므로 W > 2/K 인 한 순위가 같다.
               ⟹ score_eq 는 다음 순서와 **순서동형**이다.
                     key(p) = ( 1[d₀(p,g)=0] , RRF(p) )   사전식 내림차순
               튜닝할 상수가 없다. (structural 의 0.5·def 도 같은 이유로 사전식 키지만,
               키가 하나 더 늘고 그 키가 정규식 휴리스틱이라는 점이 다르다.)

  Z (영집합)   완전일치는 AU-Dice 의 **영집합**이다 — 강성(rigid) 읽기에서.
                     m₀=|p ⊓ g| · c₀=|p| · n₀=|g| ·  F₁⁰ = 2m₀/(c₀+n₀)
                     2m₀ ≤ c₀+n₀ 이고 등호 ⟺ m₀=c₀=n₀ ⟺ 두 트리가 같다
               ⟹ 1[eq] = 1[F₁⁰=1] = 1[d₀=0].
               ★ 우리는 d₀ 의 **거리 구조를 전혀 쓰지 않는다** — 핵(kernel)만 쓴다.
                 1−Dice 는 삼각부등식을 어기지만(P8), 핵 d₀⁻¹(0) 은 정직한 **동치관계**다.
                 그래서 '거리가 metric 이 아니다' 라는 흠이 eq 에는 닿지 않는다.

  S (자기게이팅) τ(g) = max_p (1−d₀(p,g)) 를 국면 지표로 두면
                     1[d₀(p,g)=0] ≠ 0  ⟹  τ(g) = 1.
               즉 이 항의 **받침(support)이 C 국면에 정확히 갇힌다.**
               τ₀ 도 ω 도 필요 없다 — 지시자가 스스로를 게이팅한다.
               (게이트 모형 ω·(…) 의 특수해이면서 매개변수가 0개다.)

사용: PYTHONPATH=src python3 scripts/verify_eq_props.py
"""
import itertools
import logging
import os
import sys

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from tactic_gen.tier_rank import RRF_K, EQ_W, canon, prem_struct, goal_struct  # noqa: E402
from tactic_gen.applicable import parse  # noqa: E402

EPS = 1e-12
fails = []


def ok(c, name, detail=""):
    print(f"   {'✓' if c else '✗'} {name}" + (f"   {detail}" if detail else ""))
    if not c:
        fails.append(name)


# ══ L. 사전식 ═══════════════════════════════════════════════════════════════
print("■ L  W 는 가중치가 아니라 사전식 분리자다\n")
SPREAD = 2.0 / RRF_K                      # RRF 두 항 각각 ≤ 1/K
print(f"   K = {RRF_K} · RRF 두 항의 합 ∈ (0, {SPREAD:.4f}] · W = {EQ_W}\n")
ok(EQ_W > SPREAD, f"W > 2/K  ({EQ_W} > {SPREAD:.4f})",
   "⟹ eq 항이 RRF 를 항상 압도 = 사전식 1순위 키")


def order_of(w, rrfs, eqs):
    s = [rrfs[j] + w * eqs[j] for j in range(len(rrfs))]
    return tuple(sorted(range(len(s)), key=lambda j: (-s[j], j)))


# W 를 2/K 위에서 아무리 흔들어도 순위가 같은가 — 무작위 대신 전수로 확인한다
import random  # noqa: E402
random.seed(0)
same = True
lex_same = True
for _ in range(3000):
    n = random.randint(2, 8)
    rrfs = [1.0 / (RRF_K + random.randint(0, 400)) + 1.0 / (RRF_K + random.randint(0, 400))
            for _ in range(n)]
    eqs = [1.0 if random.random() < 0.25 else 0.0 for _ in range(n)]
    ref = order_of(EQ_W, rrfs, eqs)
    for w in (SPREAD + 1e-6, 0.5, 1.0, 3.0, 100.0, 1e6):
        if order_of(w, rrfs, eqs) != ref:
            same = False
    # 사전식 키와 같은 순서를 주는가
    lex = tuple(sorted(range(n), key=lambda j: (-eqs[j], -rrfs[j], j)))
    if lex != ref:
        lex_same = False
ok(same, "W > 2/K 이면 W 값에 관계없이 순위가 동일 (3,000 무작위 사례)",
   "튜닝할 상수가 없다")
ok(lex_same, "score_eq 의 순위 = ( 1[eq], RRF ) 사전식 순위",
   "순서동형 — 점수는 구현 편의일 뿐")

# 반례 방향: W 가 2/K 아래면 사전식이 깨진다 (분리자라는 주장이 공허하지 않음을 보인다)
broke = any(order_of(1.0 / (2 * RRF_K), r_, e_) != tuple(sorted(range(len(r_)),
            key=lambda j: (-e_[j], -r_[j], j)))
            for r_, e_ in [([1.0 / (RRF_K + a) + 1.0 / (RRF_K + b) for a, b in
                            [(0, 0), (300, 300)]], [0.0, 1.0])])
ok(broke, "W < 2/K 이면 실제로 깨진다 (주장이 공허하지 않다)")

# ══ Z. 영집합 ═══════════════════════════════════════════════════════════════
print("\n■ Z  완전일치 = AU-Dice 의 영집합 (강성 읽기)\n")


def au0(a, b, cnt):
    """metavariable 없이 순수 AU — 모든 식별자가 상수다."""
    if a is None or b is None:
        return
    if a[0] == b[0] == "id" and a[1] == b[1]:
        cnt[0] += 1
        return
    if a[0] == b[0] == "app":
        cnt[0] += 1
        au0(a[1], b[1], cnt)
        au0(a[2], b[2], cnt)
        return
    if a[0] == b[0] == "op" and a[1] == b[1]:
        cnt[0] += 2
        au0(a[2], b[2], cnt)
        au0(a[3], b[3], cnt)
        return
    if a == b:
        cnt[0] += 1
    return


def size0(t):
    c = [0]
    au0(t, t, c)
    return c[0]


def f1_0(p, g):
    c = [0]
    au0(p, g, c)
    m, cc, nn = c[0], size0(p), size0(g)
    return 2.0 * m / (cc + nn) if cc + nn else 0.0


# 대수: 2m ≤ c+n, 등호 ⟺ m=c=n
combos = [(m, c, n) for c in range(1, 14) for n in range(1, 14)
          for m in range(0, min(c, n) + 1)]
ok(all(2 * m <= c + n for m, c, n in combos), "2m ≤ c + n  (m ≤ min(c,n) 이므로)")
ok(all((abs(2 * m / (c + n) - 1) < EPS) == (m == c == n) for m, c, n in combos),
   "F₁⁰ = 1  ⟺  m = c = n")

# 실제 Coq 항으로: eq 지시자와 1[F₁⁰=1] 이 같은가
CASES = [
    ("완전 동일",        "a + b = b + a", "Lemma foo : a + b = b + a."),
    ("모듈 접두사만 다름", "Nat.add a b = c", "Lemma foo : add a b = c."),
    ("중위/함수 표기",    "a + b = c", "Lemma foo : Nat.add a b = c."),
    ("변수명만 다름(α)",  "a + b = b + a", "Lemma foo x y : x + y = y + x."),
    ("인스턴스",          "1 + b = b + 1", "Lemma foo x y : x + y = y + x."),
    ("연산자 다름",       "a + b = b + a", "Lemma bar : a * b = b * a."),
    ("공허",              "a + b = b + a", "Lemma triv (P:Prop) : P."),
]
print()
print("   {:20s} {:>8} {:>8}   {}".format("", "eq", "1[F₁⁰=1]", "F₁⁰"))
agree = True
for tag, g, p in CASES:
    ps = prem_struct(p)
    qt = canon(parse(g))
    if ps is None or ps[1] is None or qt is None:
        print(f"   {tag:20s} {'파싱실패':>8}")
        continue
    e = 1 if ps[1] == qt else 0
    f = f1_0(ps[1], qt)
    z = 1 if abs(f - 1) < 1e-9 else 0
    if e != z:
        agree = False
    print(f"   {tag:20s} {e:>8} {z:>8}   {f:.3f}")
print()
ok(agree, "실제 Coq 항에서 1[eq] = 1[F₁⁰=1] 이 일치")

# 핵이 동치관계인가 — 반사·대칭·추이
TS = [canon(parse(x)) for x in
      ["a + b = b + a", "b + a = a + b", "a + b = b + a", "a * b = b * a",
       "Nat.add a b = c", "add a b = c", "f (a + b) = c"]]
TS = [t for t in TS if t is not None]
ker = lambda x, y: abs(f1_0(x, y) - 1) < 1e-9        # noqa: E731
refl = all(ker(t, t) for t in TS)
symm = all(ker(a, b) == ker(b, a) for a in TS for b in TS)
tran = all((not (ker(a, b) and ker(b, c))) or ker(a, c)
           for a, b, c in itertools.product(TS, repeat=3))
ok(refl and symm and tran, "핵 d₀⁻¹(0) 이 동치관계 (반사·대칭·추이)",
   "1−Dice 자체는 삼각부등식을 어기지만 핵은 멀쩡하다")

# ══ S. 자기게이팅 ═══════════════════════════════════════════════════════════
print("\n■ S  지시자가 스스로를 게이팅한다\n")
#   τ(g) = max_p (1−d₀(p,g)) = max_p F₁⁰(p,g)
#   1[d₀(p,g)=0] ≠ 0  ⟹  F₁⁰(p,g)=1  ⟹  τ(g)=1.
pool = [canon(parse(x)) for x in
        ["a * b = b * a", "f (a+b) = c", "a + b = b + a", "bijection f"]]
pool = [t for t in pool if t is not None]
gs_ = [canon(parse(x)) for x in ["a + b = b + a", "sqrt x >= 0"]]
gs_ = [t for t in gs_ if t is not None]
sup_ok = True
for g in gs_:
    tau = max(f1_0(p, g) for p in pool)
    fires = any(abs(f1_0(p, g) - 1) < 1e-9 for p in pool)
    print(f"   goal τ(g) = {tau:.3f} · eq 발화 = {fires}")
    if fires and abs(tau - 1) > 1e-9:
        sup_ok = False
ok(sup_ok, "eq 발화 ⟹ τ(g)=1  — 받침이 C 국면에 갇힌다",
   "게이트 모형 ω·(…) 의 매개변수 0개짜리 특수해")

# ══ X. eqx — 전체 명제의 α-정규형 ═════════════════════════════════════════
print("\n■ X  eqx = 전체 명제의 α-정규형 — `exact` 를 정확히 특징짓는다\n")

from tactic_gen.tier_rank import (prem_stmt, goal_stmt, alpha_canon,  # noqa: E402
                                  _mk_impl)
from tactic_gen.applicable import decompose, match, parse_toks  # noqa: E402


def raw_stmt(d):
    """α-정규화 **전** 의 전체 명제 트리와 메타변수. 포섭 판정에 쓴다."""
    if d is None:
        return None, None
    c = parse_toks(d[2])
    if c is None:
        return None, None
    hs = []
    for h in d[1]:
        ht = parse_toks(h)
        if ht is None:
            return None, None
        hs.append(canon(ht))
    return _mk_impl(hs, canon(c)), set(d[0])


def subsumes(a, amv, b):
    """a ⊑ b — a 의 메타변수를 채워 b 를 만들 수 있는가."""
    return a is not None and b is not None and match(a, b, amv, {})


DECLS = [
    "Lemma add_comm x y : x + y = y + x.",
    "Lemma add_comm2 (p q : nat) : p + q = q + p.",     # 위와 α-동치
    "Lemma mul_comm x y : x * y = y * x.",
    "Lemma foo : forall x, P x -> Q x.",
    "Lemma foo2 : forall y, P y -> Q y.",               # 위와 α-동치
    "Lemma bar : forall x, Q x.",                       # 가설이 없다
    "Lemma triv (P : Prop) (h : P) : P.",               # 바닥 ⊥
    "Lemma refl : forall (A : Type) (a : A), a = a.",
    "Lemma add_0_r n : n + 0 = n.",
]
STS = []
for t in DECLS:
    tr, mv = raw_stmt(decompose(t))
    if tr is not None:
        STS.append((t, tr, mv, prem_stmt(t)))

# X1 — 강제성: α-정규형 동일 ⟺ 서로 포섭 (⊑ ∩ ⊒)
bad = []
for na, ta, mva, aa in STS:
    for nb, tb, mvb, ab in STS:
        lhs = (aa == ab)
        rhs = bool(subsumes(ta, mva, tb)) and bool(subsumes(tb, mvb, ta))
        if lhs != rhs:
            bad.append((na[:28], nb[:28], lhs, rhs))
ok(not bad, "X1 강제성  ⟦p⟧ = ⟦g⟧  ⟺  p ⊑ g ∧ g ⊑ p",
   f"{len(STS)}² = {len(STS)**2}쌍 전수" if not bad else str(bad[:2]))

# X2 — 동치관계
refl = all(a == a for _, _, _, a in STS)
symm = all((a == b) == (b == a) for _, _, _, a in STS for _, _, _, b in STS)
tran = all((not ((a == b) and (b == c))) or (a == c)
           for _, _, _, a in STS for _, _, _, b in STS for _, _, _, c in STS)
ok(refl and symm and tran, "X2 동치관계  반사·대칭·추이",
   "선순서 ⊑ 를 부분순서로 만드는 표준 몫")

# X3 — 바닥 ⊥ 는 모두를 포섭하지만 어떤 것과도 동치가 아니다
bot = [x for x in STS if "triv" in x[0]]
if bot:
    _, tb_, mvb_, ab_ = bot[0]
    subs_all = sum(1 for _, t, _, _ in STS if subsumes(tb_, mvb_, t))
    eq_all = sum(1 for _, _, _, a in STS if a == ab_)
    ok(subs_all >= len(STS) - 1 and eq_all == 1,
       "X3 바닥 ⊥ 은 ⊑ 로는 거의 전부를 포섭하나 ≡α 로는 자기 자신뿐",
       f"⊑ {subs_all}/{len(STS)} · ≡α {eq_all}/{len(STS)}  ← A 붕괴의 원인이 여기서 제거된다")

# X4 — 몫 위에서 잘 정의되는가: α-변형을 줘도 값이 안 바뀌는가
ren = {"x": "u", "y": "v", "p": "u", "q": "v", "n": "u", "a": "u", "A": "U"}
import re as _re  # noqa: E402


def rename(txt):
    return _re.sub(r"(?<![\w'])([A-Za-z])(?![\w'])", lambda m: ren.get(m.group(1), m.group(1)), txt)


wd = all(prem_stmt(t) == prem_stmt(rename(t)) for t in DECLS)
ok(wd, "X4 몫 위에서 잘 정의됨  p ≡α p′ ⟹ ⟦p⟧ = ⟦p′⟧",
   "결론만 보던 d₀ 는 이 성질이 없었다 — 이름을 바꾸면 값이 바뀐다")

# X5 — 결론만 비교하면 건전성이 깨진다 (eqa 의 흠을 반례로 명시)
c_foo, mv_foo = parse_toks(decompose("Lemma foo : forall x, P x -> Q x.")[2]), {"x"}
c_bar = parse_toks(decompose("Lemma bar : forall z, Q z.")[2])
concl_same = alpha_canon(canon(c_foo), mv_foo) == alpha_canon(canon(c_bar), {"z"})
stmt_same = prem_stmt("Lemma foo : forall x, P x -> Q x.") == prem_stmt("Lemma bar : forall z, Q z.")
ok(concl_same and not stmt_same,
   "X5 결론만 비교하면 `∀x,P x→Q x` 와 `∀z,Q z` 가 같아진다 — 전체 명제는 안 그렇다",
   "exact 가 실패하는데 발화하던 자리")

print()
print("=" * 66)
if fails:
    print("✗ 실패:", fails)
    sys.exit(1)
print("✓ L · Z · S · X 모두 확인")
