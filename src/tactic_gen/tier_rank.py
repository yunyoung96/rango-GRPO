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
                 use_def: bool = True, use_mmr: bool = False,
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
