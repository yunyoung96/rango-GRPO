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
