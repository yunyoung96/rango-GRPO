"""★ 계층 랭커 — "적용 가능한 것을 먼저, 그 안에서 순위" 를 하는 premise 랭킹.

## 왜 필요한가

지금 rango 의 검색은 `ID_FORM` 토큰 TF-IDF 다 — **구조를 전혀 안 본다**.
goal `a + b = b + a` 는 가설 이름(a, b)이 제거돼 토큰이 `['+', '+']` 뿐이고,
`+` 가 셋인 결합법칙(**오답**)이 1위로 온다. 순수한 개수 세기다.

결론구조 C'(head 다중집합 IDF 코사인)도 이걸 못 가른다 — 다중집합이라 인자가 어떻게
맞물리는지를 안 보기 때문이다(정답 0.482 vs 오답 0.496).

실제로 가르는 것은 **단방향 유니피케이션**(`applicable.py`)이다. premise 를 패턴,
goal 을 고정 항으로 두고 패턴의 메타변수만 대입한다 — Coq 의 `apply` 와 같은 방향.

## 왜 필터가 아니라 계층인가

적용가능 신호는 0/1 이라 순위를 못 매기고(풀의 절반이 동점), 파서 recall 이 90% 라
**필터로 쓰면 gold 를 10% 통째로 잃는다**(§10 에서 R@50 0% 로 무너졌다).

그래서 큰 값을 **가산**한다. RRF 최대값이 1/60 ≈ 0.017 이라 1.0 을 못 넘으므로
적용가능한 것이 무조건 위로 가되, 파서가 놓친 것은 **탈락하지 않고** 아래 계층에 남는다.

    tier = RRF(tfidf, C') + 1.0·[적용가능] + 0.01·anti_unify

## 비용

구조 판정은 비싸다(파싱 + 매칭). 그래서 **tfidf 상위 `stage1` 개에만** 건다.
나머지는 tfidf 순서를 그대로 유지한다 — 2단계 검색과 같은 구조다.

신호 정의는 `scripts/research_structural.py` 의 실험대에서 가져왔다(A, C', AU).
"""
from __future__ import annotations

import os
import collections
import functools
import math
import re

from tactic_gen.applicable import (as_eq, as_impl, canon, decompose,  # noqa: F401
                                   goal_conclusion, match, parse, parse_toks,
                                   subterms)

_NAME = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                   r"Instance|Axiom|Proposition|Example|Let|Program\s+\w+)\s+"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
_HEADW = re.compile(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*|<->|->|/\\|\\/|"
                    r"<=|>=|<>|=|<|>|\+\+|\+|-|\*|/|\^|::|&&|\|\|")


def declname(t: str):
    m = _NAME.match(t or "")
    return m.group(1).split(".")[-1] if m else None


# ── 구조 특징 (이름 문자열을 쓰지 않는다) ────────────────────────────────────
def head_of(t):
    while t is not None and t[0] == "app":
        t = t[1]
    if t is None:
        return None
    return t[1] if t[0] in ("id", "op") else None


def ops_of(t, out=None):
    """트리에 쓰인 **연산자 심볼** 집합."""
    if out is None:
        out = set()
    if t is None:
        return out
    if t[0] == "op":
        out.add(t[1])
        ops_of(t[2], out)
        ops_of(t[3], out)
    elif t[0] == "app":
        ops_of(t[1], out)
        ops_of(t[2], out)
    return out


def shape(t, d=0):
    """(노드수, 깊이)."""
    if t is None or t[0] in ("id", "opq"):
        return 1, d
    if t[0] == "app":
        a, b = shape(t[1], d + 1), shape(t[2], d + 1)
        return 1 + a[0] + b[0], max(a[1], b[1])
    a, b = shape(t[2], d + 1), shape(t[3], d + 1)
    return 1 + a[0] + b[0], max(a[1], b[1])


def _fallback_heads(text: str):
    """결론 파싱이 안 될 때 전체 텍스트로 head 를 근사.

    ★ 이게 없으면 파싱 실패 premise 가 전부 0점이 되어 꼬리로 밀리고 C' 의 R@50 이
      baseline 보다 낮아진다(47% vs 56%).
    """
    out = collections.Counter()
    for x in _HEADW.findall(text or ""):
        out[x.split(".")[-1]] += 1
    return out


def _heads_multiset(t, out=None):
    """결론 트리의 모든 부분항 head. lemma 이름이 아니라 **전역 상수**라 정규화 무관."""
    if out is None:
        out = collections.Counter()
    if t is None:
        return out
    h = head_of(t)
    if h is not None:
        out[h] += 1
    if t[0] == "app":
        _heads_multiset(t[1], out)
        _heads_multiset(t[2], out)
    elif t[0] == "op":
        out[t[1]] += 1
        _heads_multiset(t[2], out)
        _heads_multiset(t[3], out)
    return out


@functools.lru_cache(maxsize=300_000)
def prem_struct(text: str):
    """premise → (메타변수, 정규화 결론트리, head, 연산자집합, 크기, head다중집합, 가설head)."""
    d = decompose(text)
    c = parse_toks(d[2]) if d is not None else None
    if d is None or c is None:
        return (frozenset(), None, None, frozenset(), (1, 0),
                _fallback_heads(text), frozenset())
    c = canon(c)
    hyp_heads = set()
    for h in d[1]:
        ht = parse_toks(h)
        if ht is not None:
            hyp_heads |= set(_heads_multiset(canon(ht)).keys())
    return (frozenset(d[0]), c, head_of(c), frozenset(ops_of(c)), shape(c),
            _heads_multiset(c), frozenset(hyp_heads))


def goal_struct(state: str):
    g = parse(goal_conclusion(state))
    if g is None:
        return None
    g = canon(g)
    gts = [g]
    gg = g
    for _ in range(6):                                  # 화살표를 벗겨가며
        im = as_impl(gg)
        if not im:
            break
        gg = im[1]
        gts.append(gg)
    gh = set()
    body = (state or "").split("[GOAL]")[0]
    parts = re.split(r"\n\s*\n", body)
    if len(parts) > 1:
        for ln in parts[0].split("\n"):
            seg = ln.split(":", 1)
            if len(seg) == 2:
                ht = parse(seg[1])
                if ht is not None:
                    gh |= set(_heads_multiset(canon(ht)).keys())
    return (g, gts, head_of(g), set(ops_of(g)), shape(g), list(subterms(g)),
            _heads_multiset(g), gh)


# ── 신호 ─────────────────────────────────────────────────────────────────
def sig_applicable(gs, ps) -> float:
    """A: 실제로 단일화되는가 — apply 방향, 또는 rewrite 양변."""
    mv, c = ps[0], ps[1]
    if c is None:
        return 0.0
    gts, subs = gs[1], gs[5]
    if any(match(c, x, mv, {}) for x in gts):
        return 1.0
    eq = as_eq(c)
    if eq:
        for side in eq:
            if side[0] == "id" and side[1] in mv:
                continue                              # 변수 하나짜리 변은 아무거나 맞는다
            if any(match(side, s, mv, {}) for s in subs):
                return 1.0
    return 0.0


def sig_match_size(gs, ps) -> float:
    """A': 적용가능성의 **연속판**. 매칭된 부분항이 클수록 관련이 깊다.

    이진 A 는 풀의 절반이 동점이 되어 순위를 못 정한다. 매칭된 부분항의 노드 수를
    goal 크기로 나눠 0~1 로 만든다.
    """
    mv, c = ps[0], ps[1]
    if c is None:
        return 0.0
    gts, subs, gn = gs[1], gs[5], gs[4][0]
    best = 0.0
    for x in gts:
        if match(c, x, mv, {}):
            best = max(best, shape(x)[0] / max(gn, 1))
    eq = as_eq(c)
    if eq:
        for side in eq:
            if side[0] == "id" and side[1] in mv:
                continue
            for sub in subs:
                if match(side, sub, mv, {}):
                    best = max(best, shape(sub)[0] / max(gn, 1))
    return best


# ══ α-동치 = 포섭 선순서의 표준 몫 ═══════════════════════════════════════
#
#   포섭 `s ⊑ t ⟺ ∃σ. σ(s)=t` 는 **선순서(preorder)** 이지 부분순서가 아니다.
#   선순서를 부분순서로 만드는 표준 구성은 **대칭화로 몫을 내는 것**이고,
#   항 대수에서 그 대칭화는 정확히 변항관계(variant) = α-동치다.
#
#       L ⊑ g  ∧  g ⊑ L   ⟺   L ≡α g            (Plotkin·Reynolds 1970)
#
#   그래서 (Terms/≡α, ⊑) 가 진짜 부분순서이고, 우리가 쓰던 `canon` 동일성은
#   그 몫을 **내지 않은** 채 대표원을 이름까지 비교하던 것이다 — 이름 의존은
#   설계 선택이 아니라 몫을 안 낸 부작용이다.
#
#   ★ 왜 ⊑ 하나만 쓰면 무너지나: ↓g = {L : L ⊑ g} 는 **이데알**이라 바닥(⊥,
#     헐벗은 메타변수 `∀P. P`)을 포함하고, 바닥은 모든 goal 을 포섭한다.
#     그래서 발화가 조밀해지고 A 가 붕괴한다(실측 ALL@50 45.4% → 18.2%).
#     ⊑ ∩ ⊒ 로 대칭화하면 발화가 **포셋의 한 점(α-류)** 으로 줄어 희소성이 산다.
#
#   ★ PL 대응: `Γ ⊢ φ` 와 `⊢ ∀Γ. φ` 는 ∀-intro/elim 으로 상호유도된다. 그래서
#     goal 쪽은 **지역 문맥 변수를 메타변수로 읽어야** premise 의 binder 와 대칭이다.

_HYP_NAMES = re.compile(r"^\s*([A-Za-z_][\w']*(?:\s+[A-Za-z_][\w']*)*)\s*:(?!=)")


def goal_locals(state: str) -> frozenset:
    """goal 의 지역 문맥 변수 이름 — `Γ ⊢ φ` 를 `⊢ ∀Γ. φ` 로 읽기 위한 것."""
    body = (state or "").split("[GOAL]")[0]
    parts = re.split(r"\n\s*\n", body)
    if len(parts) < 2:
        return frozenset()
    out: set[str] = set()
    for ln in parts[0].split("\n"):
        m = _HYP_NAMES.match(ln)
        if m:
            out |= set(m.group(1).split())
    return frozenset(out)


def alpha_canon(t, mv):
    """메타변수를 **첫 등장 순서**로 ?0,?1,… 로 바꾼 α-정규형.

    공유는 보존된다 — `?0 … ?0` 과 `?0 … ?1` 은 다른 항이다. 그래서 이 정규형의
    동일성이 정확히 α-동치이고, 이름에는 전혀 의존하지 않는다.
    """
    ren: dict = {}

    def go(x):
        if x is None:
            return None
        k = x[0]
        if k == "id":
            nm = x[1]
            if nm in mv:
                if nm not in ren:
                    ren[nm] = "?%d" % len(ren)
                return ("id", ren[nm])
            return x
        if k == "app":
            return ("app", go(x[1]), go(x[2]))
        if k == "op":
            return ("op", x[1], go(x[2]), go(x[3]))
        return x

    return go(t)


def goal_alpha(state: str):
    """goal 을 `⊢ ∀Γ.∀binders. φ` 로 읽고 **α-정규형**을 준다.

    ★ 구현이 곧 진술이다: goal 결론을 가짜 선언으로 감싸 `decompose` 에 넣으면
      goal 자신의 ∀-binder 가 premise 의 binder 와 **같은 경로로** 메타변수가 된다.
      거기에 지역 문맥 Γ 를 더하면 `Γ ⊢ φ  ⟺  ⊢ ∀Γ. φ` 가 그대로 실현된다.
    """
    concl = goal_conclusion(state)
    if not concl:
        return None
    d = decompose("Lemma _g : " + concl.rstrip(". ") + ".")
    if d is not None:
        t = parse_toks(d[2])
        mv = set(d[0]) | set(goal_locals(state))
    else:
        t = parse(concl)
        mv = set(goal_locals(state))
    if t is None:
        return None
    return alpha_canon(canon(t), mv)


def prem_alpha(ps):
    """premise 결론의 α-정규형. `ps` 는 `prem_struct` 의 결과."""
    if ps is None or ps[1] is None:
        return None
    return alpha_canon(ps[1], ps[0])


# ══ 전체 명제의 α-정규형 — `exact` 를 정확히 특징짓는다 ═════════════════
#
#   위의 `goal_alpha`/`prem_alpha` 는 **결론만** 비교한다. 그래서
#   `∀x, P x → Q x` 와 goal `Q a` 가 매치되는데 `exact` 는 실패한다 — 가설을
#   버렸기 때문이다. 그리고 goal 쪽 메타변수를 정규식(`goal_locals`)으로 추측한다.
#
#   두 흠을 한 번에 없애는 방법: **전체 명제**를 비교하고, goal 문맥은 건드리지 않는다.
#
#       ⟦d⟧ = α( ∀mv. h₁ → … → hₖ → c )      d = (mv, [h…], c) = decompose 결과
#
#   premise 와 goal 이 **같은 함수**를 통과하므로 비교가 완전히 대칭이고,
#   `goal_locals` 가 아예 필요 없어진다(휴리스틱 제거).
#
#   ★ 정리 (건전성).  ⟦p⟧ = ⟦g⟧  ⟹  `exact p` 가 goal g 를 닫는다.
#     Coq 은 항을 de Bruijn 으로 표현하므로 α-동치는 항의 **동일성**이다.
#   ★ 역은 변환(conversion, δβιζη)만큼 약하다 — `≡α` 는 변환의 **판정 가능한
#     구문적 핵**이고 O(n) 이다. 변환 전체는 커널 호출이 필요하다.
#
#   ★ 받침(성질 S)이 정리로 강해진다: goal 이 **닫힌 명제**일 때만 발화한다.
#     assert 직후의 subgoal 이 정확히 그것이고, 일반 goal(문맥 변수를 가진)에는
#     구조적으로 발화하지 않는다. 게이트가 필요 없는 이유가 여기서 완결된다.


def _mk_impl(hyps, concl):
    """가설을 화살표로 되감는다: h₁ → … → hₖ → c. `canon` 의 `impl` 표기를 쓴다."""
    t = concl
    for h in reversed(hyps):
        t = ("app", ("app", ("id", "impl"), h), t)
    return t


def alpha_stmt(d):
    """`decompose` 결과 → **전체 명제**의 α-정규형. 파싱 실패면 None."""
    if d is None:
        return None
    c = parse_toks(d[2])
    if c is None:
        return None
    hs = []
    for h in d[1]:
        ht = parse_toks(h)
        if ht is None:
            return None                       # 가설을 못 읽으면 비교를 포기한다
        hs.append(canon(ht))                  # ★ 버리지 않는다 — 버리면 건전성이 깨진다
    return alpha_canon(_mk_impl(hs, canon(c)), set(d[0]))


def prem_stmt(text: str):
    """premise 선언 → 전체 명제의 α-정규형."""
    return alpha_stmt(decompose(text or ""))


def goal_stmt(state: str):
    """goal → 전체 명제의 α-정규형. **premise 와 같은 경로**를 탄다."""
    c = goal_conclusion(state)
    if not c:
        return None
    return alpha_stmt(decompose("Lemma _g : " + c.rstrip(". ") + "."))


def alpha_eq(ga, ps) -> bool:
    """premise 결론과 goal 이 α-동치인가  (⟺ 서로 포섭한다: L ⊑ g ∧ g ⊑ L)."""
    if ga is None:
        return False
    pa = prem_alpha(ps)
    return pa is not None and pa == ga


def sig_concl_heads(gs, ps, idf) -> float:
    """C': 결론 부분항 head 의 IDF 가중 코사인."""
    a, b = ps[5], gs[6]
    if not a or not b:
        return 0.0
    num = sum(a[k] * b[k] * idf.get(k, 1.0) ** 2 for k in (a.keys() & b.keys()))
    na = math.sqrt(sum((v * idf.get(k, 1.0)) ** 2 for k, v in a.items()))
    nb = math.sqrt(sum((v * idf.get(k, 1.0)) ** 2 for k, v in b.items()))
    return num / (na * nb) if na and nb else 0.0


def _au(a, b, cnt):
    """anti-unification: 가장 구체적인 공통 일반화의 크기를 센다."""
    if a is None or b is None:
        return
    if a[0] == b[0] == "id":
        if a[1].split(".")[-1] == b[1].split(".")[-1]:
            cnt[0] += 1
        return
    if a[0] == b[0] == "app":
        cnt[0] += 1
        _au(a[1], b[1], cnt)
        _au(a[2], b[2], cnt)
        return
    if a[0] == b[0] == "op" and a[1] == b[1]:
        cnt[0] += 2
        _au(a[2], b[2], cnt)
        _au(a[3], b[3], cnt)
        return
    return                                            # 여기서 일반화 — 더 안 센다


def sig_anti_unify(gs, ps) -> float:
    """AU: 공통 구조 노드수 / 큰 쪽 크기. C' 와 달리 **트리 위치**를 반영한다."""
    c = ps[1]
    if c is None:
        return 0.0
    pn = shape(c)[0]
    best = 0.0
    for tgt in gs[5]:
        gn = shape(tgt)[0]
        if gn < 2 or pn < 2:
            continue
        cnt = [0]
        _au(c, tgt, cnt)
        if cnt[0] >= 2:
            best = max(best, cnt[0] / max(gn, pn))
    eq = as_eq(c)
    if eq:
        for side in eq:
            sn = shape(side)[0]
            if sn < 2:
                continue
            for tgt in gs[5]:
                gn = shape(tgt)[0]
                if gn < 2:
                    continue
                cnt = [0]
                _au(side, tgt, cnt)
                if cnt[0] >= 2:
                    best = max(best, cnt[0] / max(gn, sn))
    return best


# ══ 반유니피케이션 비유사도 D_λ (future-idea.md ⑮-A) ═══════════════════════
#
#  포섭 순서 `s ⊑ t ⟺ ∃σ. σ(s)=t` 에서 반유니피케이션이 meet(⊓) 이다.
#  `size(t)` = 고정 기호 노드 수(단조: s ⊑ t ⟹ size(s) ≤ size(t)).
#
#      res = size(concl) − size(⊓)     불일치  · res=0 ⟺ concl ⊑ goal ⟺ apply 가 맞는다
#      gen = size(goal)  − size(⊓)     일반성  · 크면 lemma 가 goal 을 설명 못 한다
#      D_λ = res + λ·gen
#
#  ★ 양 끝점이 우리가 아는 두 경우다.
#      λ=0  순수 적용가능성 — **예전에 A 를 45.4% → 18.2% 로 무너뜨린 그 설정**
#           (`forall A (x:A), P x` 같은 공허한 lemma 가 res=0 으로 만점을 받는다)
#      λ=1  대칭 — 트리 완전일치만 0 (지금 EQ_W 가 잡는 경우)
#      0<λ<1  적용 가능하면서 **구체적인** 것을 선호   ← 여기를 쓴다
#    λ>0 이면 `D_λ = 0 ⟺ α-동치` 가 유지되고, 공허한 lemma 는 gen 이 커서 자동으로 밀린다.
#
#  ※ "거리"가 아니라 **비유사도**다 — 삼각부등식은 증명되지 않았다(모듈러성이 깨진다).
#    랭킹은 순위 비교만 쓰므로 무관하다. future-idea.md ⑮-A 참조.
AU_LAM = float(os.environ.get("AU_LAM", "0.35"))     # λ
AU_DIST_W = float(os.environ.get("AU_DIST_W", "1.0"))  # RRF 항으로 쓰므로 1.0 기본


def _rigid_size(t, mv: frozenset) -> int:
    """고정 기호 노드 수 — **메타변수는 세지 않는다.**

    `size` 는 포섭 순서에 대해 단조여야 한다(`s ⊑ t ⟹ size(s) ≤ size(t)`).
    메타변수는 치환으로 무엇이든 되므로 "premise 가 주장하는 구조"에 포함되지 않는다.
    """
    if t is None:
        return 0
    if t[0] == "id":
        return 0 if t[1].split(".")[-1] in mv else 1
    if t[0] == "opq":
        return 1
    if t[0] == "app":
        return 1 + _rigid_size(t[1], mv) + _rigid_size(t[2], mv)
    return 2 + _rigid_size(t[2], mv) + _rigid_size(t[3], mv)


def _au_dir(p, g, mv: frozenset, cnt) -> None:
    """**방향 있는** 반유니피케이션 — premise 의 바인더를 메타변수로 본다.

    ★ 이게 없으면 `Lemma add_comm x y : x+y = y+x` 가 goal `a+b = b+a` 와
      **안 맞는다**(x ≠ a 이므로). 그러면 `res = 0 ⟺ concl ⊑ goal` 이라는
      성질 자체가 성립하지 않아 D_λ 의 근거가 무너진다.
      메타변수는 무엇과도 맞고(=premise 쪽 잔차 0), 그 자리가 삼킨 goal 부분은
      `gen` 으로 계산되어 "얼마나 일반적인가"의 벌점이 된다.
    """
    if p is None or g is None:
        return
    if p[0] == "id" and p[1].split(".")[-1] in mv:
        return                                   # 메타변수 — 맞음(고정 기호 기여 0)
    if p[0] == g[0] == "id":
        if p[1].split(".")[-1] == g[1].split(".")[-1]:
            cnt[0] += 1
        return
    if p[0] == g[0] == "app":
        cnt[0] += 1
        _au_dir(p[1], g[1], mv, cnt)
        _au_dir(p[2], g[2], mv, cnt)
        return
    if p[0] == g[0] == "op" and p[1] == g[1]:
        cnt[0] += 2
        _au_dir(p[2], g[2], mv, cnt)
        _au_dir(p[3], g[3], mv, cnt)
        return
    return                                       # 여기서 일반화 — 더 안 센다


def _au_size(a, b) -> int:
    """size(a ⊓ b) — 대칭 버전(기존 호출부 호환)."""
    cnt = [0]
    _au(a, b, cnt)
    return cnt[0]


def sig_au_dist(gs, ps, lam: float = None) -> float:
    """`1/(1+D_λ/size(goal))` — 크면 상위. D_λ=0(α-동치)이면 정확히 1.0.

    goal 의 **모든 부분항**과 premise 결론(등식이면 양변)을 맞춰 최소 D 를 취한다.
    부분항 양화가 `rewrite` 를 자연히 포함한다 — `rewrite L` 은 L 의 등식 한쪽이
    goal 의 부분항과 맞아야 하는데, 결론 전체만 보면 그 질문을 아예 못 던진다
    (lemma 를 쓰는 tactic 의 45.5% 가 rewrite 다).
    """
    if lam is None:
        lam = AU_LAM
    c = ps[1]
    if c is None or not gs[5]:
        return 0.0
    mv = ps[0] or frozenset()                # premise 바인더 = 메타변수
    cands = [c]
    eq = as_eq(c)
    if eq:
        cands.extend(eq)                     # 등식이면 양변도 후보(rewrite)
    best = None
    for src in cands:
        sn = _rigid_size(src, mv)            # 고정 기호만
        for tgt in gs[5]:
            gn = shape(tgt)[0]
            if gn < 1:
                continue
            cnt = [0]
            _au_dir(src, tgt, mv, cnt)
            m = cnt[0]
            res = max(sn - m, 0)             # 불일치: res=0 ⟺ concl ⊑ tgt
            gen = max(gn - m, 0)             # 일반성: lemma 가 못 채운 부분
            d = res + lam * gen
            v = 1.0 / (1.0 + d / max(gn, 1))
            if best is None or v > best:
                best = v
    return best or 0.0


def au_pr(gs, ps) -> tuple:
    """`(P, R)` — 항 구조에 대한 **정밀도·재현율**.

        P = size(⊓) / size_rigid(concl)   premise 가 주장하는 것 중 얼마나 쓰였나
        R = size(⊓) / size(goal)          goal 중 얼마나 설명됐나

    ★ 왜 이 형태인가 (future-idea.md ⑮-A2)
      앞서 쓴 두 잔차가 정확히 `res/|concl| = 1−P`, `gen/|goal| = 1−R` 이다.
      즉 `D_λ = res + λ·gen` 은 **정밀도·재현율의 가중합**이었다.
      그런데 이 둘을 합치는 **정준적인 방법이 이미 있다** — 조화평균(F-측도).
      그러면 λ 가 사라지고, 튜닝이 필요하면 `F_β` 의 β 로 옮겨간다.
      β 는 "재현율이 정밀도보다 β배 중요하다"는 **표준 해석**을 갖는다.

      · α-동치        P=1, R=1   → F₁=1
      · 인스턴스       P=1, R<1   → F₁ 중간
      · 공허(결론이 변수) P=1, R≈0  → F₁≈0     ← λ 없이도 자동으로 밀린다
    """
    c = ps[1]
    if c is None or not gs[5]:
        return (0.0, 0.0)
    mv = ps[0] or frozenset()
    cands = [c]
    eq = as_eq(c)
    if eq:
        cands.extend(eq)
    best = None
    for src in cands:
        sn = _rigid_size(src, mv)
        for tgt in gs[5]:
            gn = shape(tgt)[0]
            if gn < 1:
                continue
            cnt = [0]
            _au_dir(src, tgt, mv, cnt)
            m = cnt[0]
            P = m / sn if sn > 0 else 1.0     # 주장할 고정 구조가 없으면 P=1(공허)
            R = m / gn
            if best is None or (P + R) > (best[0] + best[1]):
                best = (P, R)
    return best or (0.0, 0.0)


def sig_au_f(gs, ps, beta: float = 1.0) -> float:
    """`F_β(P, R)` — 크면 상위. β=1 이 정준값(조화평균).

    `F_β = (1+β²)·P·R / (β²·P + R)`  — β 가 클수록 **재현율(goal 설명)** 을 중시한다.
    β→0 이면 P 만 보므로 **공허한 lemma 가 만점**을 받는다(= λ=0 붕괴와 같은 실패).
    """
    P, R = au_pr(gs, ps)
    if P <= 0 and R <= 0:
        return 0.0
    b2 = beta * beta
    den = b2 * P + R
    if den <= 0:
        return 0.0
    return (1.0 + b2) * P * R / den


def au_res_gen(gs, ps) -> tuple:
    """`(res, gen)` 을 정규화해 돌려준다 — λ 로 합치지 않은 **두 신호**.

    λ 를 손으로 정하는 대신 두 신호를 각각 순위로 융합(RRF)하면
    "노드 1개가 몇 배" 라는 질문 자체가 사라진다(future-idea.md ⑮-A).
    """
    c = ps[1]
    if c is None or not gs[5]:
        return (1.0, 1.0)
    mv = ps[0] or frozenset()
    cands = [c]
    eq = as_eq(c)
    if eq:
        cands.extend(eq)
    best = None
    for src in cands:
        sn = _rigid_size(src, mv)
        for tgt in gs[5]:
            gn = shape(tgt)[0]
            if gn < 1:
                continue
            cnt = [0]
            _au_dir(src, tgt, mv, cnt)
            m = cnt[0]
            res = max(sn - m, 0) / max(gn, 1)
            gen = max(gn - m, 0) / max(gn, 1)
            if best is None or (res + gen) < (best[0] + best[1]):
                best = (res, gen)
    return best or (1.0, 1.0)


def sig_head(gs, ps) -> float:
    """B: 결론 최상위 head 일치. head 는 lemma 이름이 아니라 **전역 상수**다."""
    return 1.0 if (ps[2] is not None and ps[2] == gs[2]) else 0.0


def sig_ops(gs, ps) -> float:
    """C: 연산자 집합 Jaccard — 순수 기호라 이름 무관."""
    a_, b_ = ps[3], gs[3]
    if not a_ and not b_:
        return 0.0
    u = len(a_ | b_)
    return len(a_ & b_) / u if u else 0.0


def sig_shape(gs, ps) -> float:
    """D: 결론 크기·깊이 유사도."""
    (pn, pd), (gn, gd) = ps[4], gs[4]
    return (1.0 / (1 + abs(pn - gn) / max(gn, 1))) * 0.5 + \
           (1.0 / (1 + abs(pd - gd))) * 0.5


def sig_hyp_match(gs, ps) -> float:
    """E: lemma **가설부** head 가 goal 가설블록에 이미 있는가.

    `apply X` 는 X 의 가설을 새 subgoal 로 남긴다. 그게 이미 있으면 바로 닫힌다 —
    결론만 보는 신호들이 통째로 놓치는 축이다.
    """
    ph = ps[6]
    if not ph:
        return 0.0
    gh = gs[7]
    if not gh:
        return 0.0
    return len(ph & gh) / len(ph)


def sig_locality(cur_file: str, prem_file: str) -> float:
    """H: 파일 경로 근접성. 같은 파일 > 같은 디렉토리 > 같은 프로젝트.

    (줄 번호 기반 거리도 넣고 싶었으나 데이터에 없다 — `step.term.line` 이 None.)
    """
    if not prem_file or not cur_file:
        return 0.0
    a_ = [x for x in prem_file.split("/") if x and x != ".."]
    b_ = [x for x in cur_file.split("/") if x and x != ".."]
    if a_ and b_ and a_[-1] == b_[-1]:
        return 1.0
    k = 0
    for x, y in zip(a_, b_):
        if x != y:
            break
        k += 1
    return min(0.6, 0.1 * k)


def n_hyps(text: str) -> float:
    """premise 가설 수 (0~8 정규화). 가설이 많으면 적용이 어렵다."""
    d = decompose(text)
    return min(float(len(d[1])), 8.0) / 8.0 if d else 0.0


# ── 랭커 ─────────────────────────────────────────────────────────────────
RRF_K = 60
TIER_W = 1.0            # 적용가능 계층 가산 — RRF 최대(1/60)보다 훨씬 커야 한다
AU_W = 0.01             # 계층 안에서의 미세 조정


class TierRanker:
    """한 증명 지점의 premise 풀. 구조 파싱은 한 번만 하고 질의만 바꿔 랭킹한다."""

    def __init__(self, texts: list[str], stage1: int = 400):
        self.texts = texts
        self.stage1 = stage1
        self._pss: dict[int, tuple] = {}
        self._idf: dict[str, float] | None = None

    def _struct(self, j: int):
        if j not in self._pss:
            self._pss[j] = prem_struct(self.texts[j])
        return self._pss[j]

    def _idfs(self, idxs):
        if self._idf is None:
            df = collections.Counter()
            for j in idxs:
                ps = self._struct(j)
                if ps is not None:
                    for k in ps[5]:
                        df[k] += 1
            nd = max(len(idxs), 1)
            self._idf = {k: math.log(nd / v) for k, v in df.items()}
        return self._idf

    @staticmethod
    def _ranks(vals):
        o = sorted(range(len(vals)), key=lambda j: -vals[j])
        r = [0] * len(vals)
        for pos, j in enumerate(o):
            r[j] = pos
        return r

    def signals(self, state: str, tfidf: list[float]):
        """랭킹에 쓸 신호를 한 번에 계산한다 — 변형 비교용.

        돌려주는 것: (base_rrf, c2랭크가산, 적용가능, 매칭크기A', AU, 후보집합)
        """
        n = len(tfidf)
        rt = self._ranks(tfidf)
        base = [1.0 / (RRF_K + rt[j]) for j in range(n)]
        gs = goal_struct(state)
        cand = sorted(range(n), key=lambda j: rt[j])[:self.stage1]
        if gs is None:
            z = [0.0] * n
            return base, z, z, z, z, cand
        idf = self._idfs(cand)
        c2 = [0.0] * n
        ap = [0.0] * n
        ms = [0.0] * n
        au = [0.0] * n
        for j in cand:
            ps = self._struct(j)
            if ps is None:
                continue
            c2[j] = sig_concl_heads(gs, ps, idf)
            ap[j] = sig_applicable(gs, ps)
            ms[j] = sig_match_size(gs, ps)
            au[j] = sig_anti_unify(gs, ps)
        rc = self._ranks(c2)
        c2r = [1.0 / (RRF_K + rc[j]) for j in range(n)]
        return base, c2r, ap, ms, au, cand

    def rerank(self, state: str, tfidf: list[float]) -> list[float]:
        """tfidf 점수를 받아 **계층 점수**로 바꾼다. 큰 값이 상위."""
        base, c2r, ap, ms, au, _ = self.signals(state, tfidf)
        return [base[j] + c2r[j] + TIER_W * (1.0 if ap[j] > 0 else 0.0)
                + AU_W * au[j] for j in range(len(tfidf))]


# ══ 최종 랭커 (final.md) ══════════════════════════════════════════════════
#   eqcov = RRF(tfidf 순위, 결론구조 C' 순위, 질의 포함률 순위)
#           + 3.0 × [premise 결론 트리 == goal 트리]
#
#   실측(각 스플릿 2,500건) 목표지표 ALL@50: TEST 95.6 / VAL 94.9 / TRAIN 97.2%
#   (현재 tfidf 는 86.4 / 86.5 / 87.8%)
#
#   ★ 트리 완전일치는 일반 goal 에서 거의 발화하지 않아 **무해**하고, assert 하위목표
#     (goal 이 곧 lemma 문장)에서는 정확히 그 질문이라 강력하다. 단방향 매칭까지 넣으면
#     일반 goal 이 무너진다(ALL@50 45.4% → 18.2%) — 그래서 완전일치만 쓴다.

# ★ 2000 → 5000. 재랭킹은 **후보 안에 gold 가 있어야** 손댈 수 있다.
#   실측(TEST 400건) gold 를 **전부** 담는 비율: 400→60.5% · 2000→80.0% · 5000→88.2%.
#   상한이 +8.2pp 오르고 비용은 구조 판정 2.5배(스텝당 ~57ms → ~140ms).
STAGE1 = 5000            # 구조 판정을 걸 tfidf 상위 개수
EQ_W = 3.0               # 트리 완전일치 가산. RRF 한 항의 최대(1/60)보다 훨씬 커야 한다


def _rrf_of(vals) -> list[float]:
    n = len(vals)
    o = sorted(range(n), key=lambda j: -vals[j])
    r = [0] * n
    for p, j in enumerate(o):
        r[j] = p
    return [1.0 / (RRF_K + r[j]) for j in range(n)]


_DEF_DECL = re.compile(r"^\s*(?:Definition|Fixpoint|CoFixpoint|Let|Program\s+\w+)\s+"
                      r"([A-Za-z_][\w']*)")


def sig_def_name(goal_ids: set, text: str) -> float:
    """정의(Definition/Fixpoint)의 **이름이 goal 에 나오는가**.

    ★ 왜 필요한가: gold 의 **36%가 Definition** 인데(실측 TEST), 정의는 결론이 명제가
      아니라 본문이라 구조 신호(C'·트리일치)가 원리적으로 안 통한다.
      `Definition ulp x := match … end.` 의 "결론" 은 명제가 아니다.
      정의는 `unfold f` · `rewrite f` 로 쓰이고, 그때 **f 가 goal 에 나타나 있다.**
      그래서 이름 등장 여부가 정의에 대한 올바른 질문이다.

    tfidf 도 이름 토큰을 세지만 다른 토큰에 희석된다. 별도 신호로 두면 선명해진다.
    """
    m = _DEF_DECL.match(text or "")
    if not m:
        return 0.0
    return 1.0 if m.group(1) in goal_ids else 0.0


def mmr_reorder(scores: list[float], texts: list[str], k: int = 50,
                lam: float = 0.35) -> list[float]:
    """**다중 lemma** 를 위한 다양성 재정렬 (MMR = Maximal Marginal Relevance).

    ★ 용어: MMR 은 "관련도가 높으면서 **이미 뽑은 것과 다른**" 항목을 차례로 고르는 방법이다.
      점수만으로 자르면 비슷한 것이 상위를 채운다.

    ★ 왜 필요한가: 한 tactic 이 lemma 를 2개 이상 쓰는 스텝이 24% 이고, 거기서
      R@50(하나라도) 54.6% 대비 ALL@50(전부) 45.4% 로 **9.2pp 를 잃는다**.
      두 lemma 의 성격이 다르면(하나는 rewrite 용 등식, 하나는 apply 용 함의)
      비슷한 것들이 상위를 채워 두 번째가 밀린다.

    유사도는 **결론 head 다중집합의 코사인** — 이미 구조 파싱을 했으므로 추가 비용이 작다.
    상위 k 개만 재정렬하고 나머지는 원래 순서를 유지한다.
    """
    n = len(scores)
    if n <= 2 or k <= 1:
        return scores
    cand = sorted(range(n), key=lambda j: -scores[j])[:min(k * 3, n)]
    hs = {}
    for j in cand:
        ps = prem_struct(texts[j])
        hs[j] = ps[5] if ps is not None else collections.Counter()

    def sim(a, b):
        x, y = hs[a], hs[b]
        if not x or not y:
            return 0.0
        num = sum(x[t] * y[t] for t in (x.keys() & y.keys()))
        na = math.sqrt(sum(v * v for v in x.values()))
        nb = math.sqrt(sum(v * v for v in y.values()))
        return num / (na * nb) if na and nb else 0.0

    picked, rest = [], list(cand)
    while rest and len(picked) < k:
        best, bv = None, -1e18
        for j in rest:
            pen = max((sim(j, q) for q in picked), default=0.0)
            v = scores[j] - lam * pen
            if v > bv:
                best, bv = j, v
        picked.append(best)
        rest.remove(best)
    out = list(scores)
    top = max(scores) if scores else 0.0
    for r, j in enumerate(picked):                    # 뽑힌 순서를 점수로 되돌린다
        out[j] = top + (len(picked) - r)
    return out


def structural_scores(goal_text: str, hyps, texts: list[str], tfidf: list[float],
                 query_ids=None, docs=None, stage1: int = STAGE1,
                 use_eq: bool = True, use_cov: bool = True,
                 use_def: bool = True, use_mmr: bool = False, use_au: bool = False,
                 mmr_k: int = 50, mmr_lam: float = 0.35) -> list[float]:
    """최종 랭킹 점수. 큰 값이 상위. `tfidf` 는 호출부가 이미 계산한 것을 넘긴다."""
    n = len(texts)
    if n == 0:
        return []
    out = _rrf_of(tfidf)
    cand = sorted(range(n), key=lambda j: -tfidf[j])[:stage1]

    state = ("\n".join(hyps or []) + "\n\n" + (goal_text or "")).strip("\n")
    gs = goal_struct("\n" + state if not state.startswith("\n") else state)
    if gs is not None:
        # C' — 결론 부분항 head 의 IDF 가중 코사인
        pss = {j: prem_struct(texts[j]) for j in cand}
        df: collections.Counter = collections.Counter()
        for j in cand:
            ps = pss[j]
            if ps is not None:
                for k in ps[5]:
                    df[k] += 1
        nd = max(len(cand), 1)
        idf = {k: math.log(nd / v) for k, v in df.items()}
        c2 = [0.0] * n
        for j in cand:
            ps = pss[j]
            if ps is not None:
                c2[j] = sig_concl_heads(gs, ps, idf)
        rc = _rrf_of(c2)
        for j in range(n):
            out[j] += rc[j]
        # ── au — 반유니피케이션 비유사도 D_λ (⑮-A) ────────────────────────
        #   `use_au=True` 면 이진 완전일치(EQ_W) **대신** 연속값을 RRF 항으로 넣는다.
        #   완전일치는 D=0 → 1.0 이라 이 신호가 그 경우를 **포함**한다.
        if use_au:
            au = [0.0] * n
            for j in cand:
                ps = pss[j]
                if ps is not None:
                    au[j] = sig_au_dist(gs, ps)
            ra = _rrf_of(au)
            for j in range(n):
                out[j] += AU_DIST_W * ra[j]
        # eq — 결론 트리 완전일치
        if use_eq:
            g = parse(goal_text or "")
            qt = canon(g) if g is not None else None
            if qt is not None:
                for j in cand:
                    ps = pss[j]
                    if ps is not None and ps[1] is not None and ps[1] == qt:
                        out[j] += EQ_W
    # cov — 질의 포함률 (tfidf 길이 정규화 편향을 겨눈다)
    if use_cov and query_ids and docs is not None:
        qs = set(query_ids)
        if qs:
            cov = [len(qs & set(docs[j])) / len(qs) for j in range(n)]
            rv = _rrf_of(cov)
            for j in range(n):
                out[j] += rv[j]
    # def — 정의 이름이 goal 에 나오는가 (구조 신호가 안 통하는 36% 를 위한 것)
    if use_def:
        gids = set(query_ids or [])
        if gids:
            for j in cand:
                out[j] += 0.5 * sig_def_name(gids, texts[j])
    # mmr — 다중 lemma 를 위한 다양성 재정렬
    if use_mmr:
        out = mmr_reorder(out, texts, k=mmr_k, lam=mmr_lam)
    return out


# 옛 이름 호환 (문서·실험 스크립트가 참조한다)
eqcov_scores = structural_scores
