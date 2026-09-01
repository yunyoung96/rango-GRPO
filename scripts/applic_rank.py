#!/usr/bin/env python3
"""★★ **추측이 필요한 것만 남기는 랭커** — 필터가 준 신호로 순위를 매긴다.

## 왜 tf-idf 만으로는 안 되나 (실측)

필터후 풀은 @50·@100 에서 크게 이기는데 **@10 에서 진다**(36.4% vs 현행 47.0%).
필터가 남긴 것 중 상당수가 `f_equal`·`eq_sym`·귀납원리처럼 **어느 goal 에나
적용되는** lemma 이고, 텍스트로도 일반적이라 tf-idf 가 위로 올린다.

## 세 신호 (전부 파이프라인이 이미 계산한다)

    e     evar 수 — `eapply` 가 몇 개를 **추측**해야 하나. e=0 이면 `exact` 가능
    lgg   반단일화 크기 — goal 과 공유하는 구조. 포섭 격자의 meet
          (Plotkin 1970 · Reynolds 1970; 필터는 join=단일화, 랭커는 meet)
    idf   **applic-idf** — `-log P(이 lemma 가 필터를 통과함)`
          모든 goal 에서 살아남으면 P≈1 → 0점. 정보가 없다는 뜻이다

## 결정적인 채널은 경쟁에서 뺀다

`unfold`(4개) · `destruct`(3개) 는 goal 만 보면 결정된다 — 추측이 없다.
랭킹 예산을 쓸 이유가 없으므로 **전량 그대로 싣고** 경쟁에서 제외한다.

사용: python3 scripts/applic_rank.py [pool.jsonl]
"""
import json, math, os, re, sys, collections, statistics as st
import logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split as CSSplit, get_theorem
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc

SRC = sys.argv[1] if len(sys.argv) > 1 else "all_log/dn_pool.jsonl"
# ── ★ 범위 ────────────────────────────────────────────────────────────────
#   apply 와 rewrite 만 다룬다 (goal 쪽 + 가설 쪽 = 네 채널).
#
#   `unfold`·`destruct`·`decide` 는 **플러그인이 계속 계산하고 풀에도 남지만**
#   여기서 랭킹·평가 대상에서 뺀다. 되돌리려면 ACTIVE_CH / ACTIVE_TAC 만 넓히면
#   된다 — 데이터는 그대로다.
#
#   왜 뺐나:
#     destruct  이름이 아니라 **항**을 골라야 한다 (인자 조합이 폭발).
#               우리는 머리 이름만 주므로 지표가 실제 성공률을 과대평가한다.
#               → docs/applicability/concepts/destruct.md
#     unfold    반대로 너무 쉽다(후보 3~7개, @10 100%). 랭킹 문제가 아니다.
#               ※ 현행 tf-idf 는 이걸 0.0% 로 놓친다 — 버리는 게 아니라
#                 **랭킹 밖으로 뺀 것**이다. 프롬프트에는 전량 실어도 된다.
ALL_CH    = ("ap", "in", "rw", "rwh", "uf", "ds", "dc")
ACTIVE_CH = ("ap", "in", "rw", "rwh")    # ← 범위. 넓히려면 여기만 고친다
ACTIVE_TAC = ("apply", "rewrite")        # ← 평가 대상 gold tactic

GUESS_CH = ACTIVE_CH               # 추측이 필요한 채널 — 랭킹이 필요하다
FREE_CH = ("uf", "ds")             # 결정적인 채널 — 전량 싣는다 (경쟁 없음)

#: gold tactic → 그 정답이 나와야 할 채널 (범위 밖 채널은 chans_for 가 걸러낸다)
#
#  ★ `destruct (zle a b)` 에 필요한 것은 `sumbool`(귀납형)이 아니라 **`zle`**
#    라는 함수다 — 그건 `uf`(goal 에 나타나는 상수) 채널에 있다. 실측에서
#    `ds` 로 보냈다가 0% 가 나왔고, 그건 배선 오류였다.
CH_OF = {"unfold": ("uf",), "fold": ("uf",),
         "destruct": ("uf", "ds", "dc", "ap"), "case": ("uf", "ds", "dc", "ap"),
         "induction": ("uf", "ds", "ap"), "elim": ("ap", "uf", "ds"),
         "apply": ("ap", "in"), "rewrite": ("rw", "rwh", "ap", "in"),
         "exact": ("ap",), "eexact": ("ap",)}


# ── ★ 시동 자가검사 — 채널 배선이 조용히 어긋나는 것을 막는다 ─────────────
assert set(ACTIVE_CH) <= set(ALL_CH), f"모르는 활성 채널: {set(ACTIVE_CH)-set(ALL_CH)}"
assert len(set(ALL_CH)) == len(ALL_CH), "ALL_CH 에 중복"
for _t, _cs in CH_OF.items():
    assert set(_cs) <= set(ALL_CH), f"CH_OF[{_t}] 에 모르는 채널: {set(_cs)-set(ALL_CH)}"
for _t in ACTIVE_TAC:
    assert _t in CH_OF, f"평가 대상 tactic '{_t}' 가 CH_OF 에 없다"


def chans_for(tac, active=ACTIVE_CH):
    """그 tactic 이 쓸 채널 — **범위 안의 것만**."""
    out = tuple(c for c in CH_OF.get(tac, GUESS_CH) if c in active)
    assert set(out) <= set(active), "chans_for 가 범위를 벗어났다"
    return out


def in_scope(r, active_tac=ACTIVE_TAC):
    """이 지점이 평가 대상인가. 지역 변수를 인자로 쓴 스텝은 검색 대상이 아니다."""
    return (not r.get("local")) and (r.get("tac") in active_tac)


#: 신호 하나만 쓰는 점수들 — 각각의 변별력을 따로 본다
def s_idf(nm, sig, idf, g): return idf.get(nm, 0.0)
def s_lgg(nm, sig, idf, g):
    return float((sig.get(nm) or {}).get("lgg", 1)) / max(1.0, g)
def s_evar(nm, sig, idf, g):
    return 1.0 / (1.0 + float((sig.get(nm) or {}).get("e", 8)))


def s_lcp(nm, sig, idf, g):
    """★ Baire 초거리 — 판별트리 **자신의** 거리.

    트리는 항을 전위 순회 문자열의 트라이로 본다. 그 위의 자연스러운 거리가
    최장 공통 접두사이고 초거리다: d(s,t)=2^(-LCP). "goal 과 가장 늦게
    갈라지는 후보" 가 가장 가깝다 — 자료구조를 더 만들 필요가 없다."""
    return float((sig.get(nm) or {}).get("lcp", 0)) / max(1.0, g)


def build_idf(rows):
    """applic-idf — 각 lemma 가 몇 %의 지점에서 필터를 통과하나."""
    cnt = collections.Counter()
    for r in rows:
        seen = set()
        for ch in GUESS_CH:
            seen |= set((r.get("chan") or {}).get(ch, []))
        for nm in seen:
            cnt[nm] += 1
    n = max(1, len(rows))
    assert cnt, "build_idf: 후보가 하나도 안 잡혔다 — chan 키를 확인하라"
    assert max(cnt.values()) <= n, "통과 횟수가 지점 수를 넘는다 — 중복 집계"
    # 라플라스 보정 — 한 번만 나온 것이 무한대가 되지 않게
    out = {k: -math.log((v + 0.5) / (n + 1.0)) for k, v in cnt.items()}
    assert all(v > 0 for v in out.values()), "idf 가 음수 — 보정식을 확인하라"
    return out, cnt, n


def score(nm, sig, idf, gsize):
    """높을수록 위. 세 신호를 곱이 아니라 합으로 — 각각이 독립적인 근거다."""
    s = sig.get(nm, {})
    e = float(s.get("e", 8))
    lgg = float(s.get("lgg", 1))
    g = float(s.get("g", gsize) or gsize or 1)
    # ① 추측량: evar 가 적을수록 goal 이 lemma 를 결정한다
    s_e = 1.0 / (1.0 + e)
    # ② 공유 구조: lgg / |goal| ∈ (0,1]
    s_l = lgg / max(1.0, g)
    # ③ 정보량: 흔한 것일수록 0 에 가깝다
    s_i = idf.get(nm, 0.0) / 8.0
    # ④ Baire: 트라이에서 갈라지는 깊이
    s_b = float(s.get("lcp", 0)) / max(1.0, g)
    return 2.0 * s_i + 1.0 * s_l + 0.5 * s_e + 1.5 * s_b


# ══════════════════════════════════════════════════════════════════════════
# ★★ 정보이론 랭커 — 모든 신호를 **비트**로 바꿔 더한다 (가중치 없음)
# ══════════════════════════════════════════════════════════════════════════
#
# 가중치를 손으로 고르는 것은 임의다. 대신 각 신호를 **놀라움(surprisal)** 으로
# 환산하면 단위가 같아져 그냥 더할 수 있다.
#
#   bits(사건) = −log2 P(사건)
#
# ① applic-idf   −log2 P(L 이 필터를 통과함)
#      어디에나 적용되는 lemma 는 P≈1 → 0 비트. **정보가 없다.**
#
# ② Baire LCP     −log2 P(무작위 후보의 lcp ≥ k)
#      트라이에서 접두사를 k 만큼 공유하는 것이 얼마나 드문가.
#      가지치기 계수가 b 면 대략 k·log2(b) 비트다 — 즉 **LCP 는 이미 로그우도**다.
#
# ③ lgg 크기      −log2 P(무작위 후보의 lgg ≥ m)     (포섭 격자의 meet)
#
# ④ evar 비용     +log2 P(무작위 후보의 e ≤ x) 의 부호 반전
#      evar 하나는 "이 인자를 찍어야 한다"는 뜻이고, 그만큼 **비용**이다.
#
# 총점 = ① + ② + ③ − ④   (전부 비트)
#
# 그리고 이 틀은 **전체 예산을 비트로 말하게** 해 준다:
#   우주 N 개에서 gold 하나를 짚는 데 필요한 정보 = log2 N
#   필터가 N→n 으로 줄이면 log2(N/n) 비트를 준 것이고,
#   랭커가 gold 을 r 위에 놓으면 추가로 log2(n/r) 비트를 준 것이다.
# 필터와 랭커의 기여를 **같은 단위로 비교**할 수 있다.

def survival_bits(values):
    """값 v 에 대해 −log2 P(무작위 후보가 v 이상) 을 주는 함수를 만든다."""
    import bisect
    xs = sorted(values)
    assert all(isinstance(x, (int, float)) for x in xs), "survival_bits: 수가 아닌 값"
    n = len(xs)
    if n == 0:
        return lambda v: 0.0
    def f(v):
        # P(X >= v)
        i = bisect.bisect_left(xs, v)
        p = (n - i + 0.5) / (n + 1.0)
        return -math.log2(max(p, 1e-9))
    return f


def build_bits(rows, idf):
    """말뭉치에서 각 신호의 생존함수를 추정한다."""
    L, G, E = [], [], []
    for r in rows:
        for nm, sg in (r.get("sig") or {}).items():
            L.append(float(sg.get("lcp", 0)))
            G.append(float(sg.get("lgg", 0)))
            E.append(float(sg.get("e", 0)))
    return survival_bits(L), survival_bits(G), survival_bits(E)


def make_bit_score(rows, idf):
    fl, fg, fe = build_bits(rows, idf)
    LOG2 = math.log(2.0)
    def sc(nm, sig, _idf, g):
        s = sig.get(nm) or {}
        b_idf = idf.get(nm, 0.0) / LOG2          # nat → bit
        b_lcp = fl(float(s.get("lcp", 0)))
        b_lgg = fg(float(s.get("lgg", 0)))
        # evar 는 **비용** — 흔할수록(=많이 찍어야 할수록) 깎는다
        b_e = fe(float(s.get("e", 0)))
        return b_idf + b_lcp + b_lgg - b_e
    return sc


def budget_report(rows, idf, sc, chans_for_fn):
    """필터와 랭커의 기여를 **비트**로 나눠 보고한다."""
    import statistics as _st
    tot_bits, filt_bits, rank_bits, n = [], [], [], 0
    for r in rows:
        gold = r.get("gold")
        if not gold or not in_scope(r): continue
        cand = set()
        for ch in chans_for_fn(r.get("tac", "")):
            cand |= set((r.get("chan") or {}).get(ch, []))
        if not cand: continue
        N = float(r.get("cand") or 0)
        if N <= 0: continue
        gb = gold.split(".")[-1]
        sig = r.get("sig") or {}
        gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
        ranked = sorted(cand, key=lambda x: -sc(x, sig, idf, gsz))
        pos = next((j for j, x in enumerate(ranked)
                    if x == gold or x.split(".")[-1] == gb), None)
        if pos is None: continue
        n += 1
        tot_bits.append(math.log2(N))
        filt_bits.append(math.log2(N / max(1, len(cand))))
        rank_bits.append(math.log2(max(1, len(cand)) / (pos + 1)))
    if not n: return
    print(f"\n■ 정보 예산 (비트) — {n} 지점")
    print(f"   gold 하나를 짚는 데 필요한 정보   {_st.median(tot_bits):5.2f} bit"
          f"   (우주 {2**_st.median(tot_bits):,.0f}개)")
    print(f"   ① 필터가 준 것                    {_st.median(filt_bits):5.2f} bit")
    print(f"   ② 랭커가 준 것                    {_st.median(rank_bits):5.2f} bit")
    print(f"   남은 것 (모델이 해야 할 몫)        "
          f"{_st.median(tot_bits) - _st.median(filt_bits) - _st.median(rank_bits):5.2f} bit")


# ══════════════════════════════════════════════════════════════════════════
# ★★★ 나이브 베이즈 랭커 — 가중치를 **데이터에서** 얻는다
# ══════════════════════════════════════════════════════════════════════════
#
# 앞의 비트합은 각 신호를 놀라움으로 환산해 더했다. 옳은 방향이지만 두 문제가
# 남는다: (a) 신호끼리 **상관**이 있어(lcp 와 lgg 는 거의 같은 것을 본다)
# 이중 계산이 되고, (b) "이 신호가 gold 을 얼마나 가리키는가" 를 안 쓴다.
#
# 정석은 **로그 가능도비**다. 특징 f 에 대해
#
#     w(f) = log [ P(f | gold) / P(f | not gold) ]                (bit)
#     score(L | g) = Σ_f w(f)
#
# 이것은 나이브 베이즈의 로그 오즈이고, **주변 통계만 주어졌을 때의
# 최대엔트로피 결합**이다. 즉 가중치를 손으로 고르지 않고 말뭉치가 정한다.
# (Kühlwein 등의 MaSh 가 기호 겹침에 대해 하는 것을, 우리는 **판별트리가 만든
#  적용가능성 특징**에 대해 한다.)
#
# 특징은 전부 필터가 이미 계산한 것을 구간화한 것이다:
#     lcp/|g|   트라이 접두사 공유 비율 (Baire)
#     lgg/|g|   포섭 격자 meet 비율      (Plotkin)
#     e         찍어야 할 evar 수
#     z/|g|     rewrite 가 건드리는 goal 비율
#     nm        맞은 redex 개수 (적을수록 특정적)
#     idf       applic-idf 구간
#     ch        어느 채널에서 왔나
#
# ★ 평가는 **정리 단위 leave-one-out** 으로 한다. 같은 정리의 지점으로
#   학습하고 그 정리를 맞히면 과적합이다.

def _bucket(x, edges):
    for i, e in enumerate(edges):
        if x < e: return i
    return len(edges)


#: 토큰화 — 식별자만 뽑는다
_TOK = re.compile(r"[A-Za-z_][\w']*")


def lex_overlap(stmt, goal_toks, tok_idf):
    """★ 어휘 신호를 **특징 하나**로 넣는다.

    tf-idf 를 랭커 전체로 쓰면 우리 모집단에서 무너진다(필터후 top10 의 43%가
    stdlib, 19%가 보편 lemma 였다). 하지만 **버릴 신호는 아니다** — 구조 신호가
    못 보는 것을 본다. 나이브 베이즈가 가중치를 정하게 특징으로만 준다.

    점수 = goal 과 겹치는 토큰의 idf 합 / (lemma 토큰 수)^0.5
    분모의 제곱근은 짧은 lemma 가 유리해지는 것을 눌러 준다."""
    if not stmt: return 0.0
    ts = set(_TOK.findall(stmt))
    if not ts: return 0.0
    inter = ts & goal_toks
    num = sum(tok_idf.get(t, 1.0) for t in inter)
    return num / (len(ts) ** 0.5)


#: stdlib 접두사
_STDP = ("Coq.", "Nat.", "N.", "Z.", "Pos.", "BinInt.", "BinNat.", "BinPos.",
         "BinPosDef.", "List.", "Vector.", "VectorDef.", "Ascii.", "Byte.",
         "Eqdep", "JMeq.", "Ring", "Field", "Morphisms", "CMorphisms.",
         "CRelationClasses.", "RelationClasses.", "Equivalence.", "Classical",
         "ProofIrrelevance", "Setoid", "Basics.", "Combinators.", "Datatypes.",
         "Specif.", "Logic.", "Init.", "Bool.", "Decidable.", "OrderedType",
         "POrderedType.", "Wf", "Znumtheory.", "Zpower", "Zdiv")


def _is_std(x):
    return any(x.startswith(p) for p in _STDP)


def _name_toks(x):
    """이름을 밑줄·점·대소문자 경계로 쪼갠다. `repr_canonical` → {repr, canonical}."""
    x = x.split(".")[-1]
    parts = re.split(r"[_']+", x)
    out = set()
    for p in parts:
        if not p: continue
        out.add(p.lower())
        for q in re.findall(r"[A-Z]?[a-z0-9]+", p):
            if len(q) > 2: out.add(q.lower())
    return out


#: ★ 쓸 특징 — **`idf` 를 뺐다.**
#
#   `applic-idf` 는 **이름별 조회표**라 스플릿을 넘어가면 항목이 없다.
#   학습 겹에 없던 lemma 는 `idf=0.0` → `('idf',0)` → 가중치 **−4.60** 을 먹는데,
#   새 프로젝트의 gold 은 대부분 미관측이라 **gold 만 골라서 감점**하는 꼴이다.
#
#   절제 실측 (VAL 110지점 · 프로젝트 leave-one-out · @10):
#       전체 13특징            39.1%
#       −idf                  49.1%   ← +10.0pp
#       핵심 5개(lgg/lcp/e/ch/std)  45.5%
#       핵심 + idf            38.2%   ← idf 가 망친다
#
#   ※ 앞서 보고한 74.5% 는 평가 지점까지 세어 gold 에 idf 값을 준 **누출**이었다.
#   ※ `idf` 를 살리려면 이름별 표가 아니라 **말뭉치 없이 계산되는 보편성 지표**
#     (진술문 길이·바인더 수 등)로 바꿔야 한다 — `slen`·`nbind`·`nsym` 이 후보다.
#: ★ 최종 특징 4개 · **14 파라미터** (v5 VAL 절제·조합·굵히기 실측):
#     lgg 4구간 + lcp 4구간 + rig 4구간 + std 2값 = 14
#     @10 69.1% — 57파라 전체(59.1%)·21파라(69.1%)와 같거나 낫다.
#     빠진 것들의 근거: idf −10pp(누출성 조회표) · slen/nsym −3.6pp(해악)
#     · e/z/lcp… ±0 · ing 은 굵힌 뒤 0pp (rig 가 흡수).
#     학습0 고정식(lgg/g+lcp/g+0.2·rig)도 65.5% — 하한 참조.
KEEP = {"lgg", "lcp", "rig", "std"}


#: ★ 구간 경계 — 특징당 하나. 파라미터 수 = Σ(경계수+1) + 문자열 특징 값수.
#   실험(구간 굵히기)에서 통째로 바꿔 낄 수 있게 모듈 상수로 뺐다.
BUCKETS = {
    "lcp": (0.15, 0.4, 0.7),          # ★ 굵힘 — 6구간과 동률, 파라미터 −2
    "lgg": (0.15, 0.4, 0.7),
    "e":   (1, 2, 4, 7, 12),
    "z":   (0.02, 0.08, 0.2, 0.4),
    "nm":  (2, 3, 6),
    "hp":  (1, 2, 4, 8),
    "occ": (1, 2, 4, 8),
    "idf": (0.5, 1.5, 3.0, 5.0, 7.0),
    "rig": (1, 2, 4),
    "slen": (6, 12, 22, 40),
    "nbind": (1, 2, 4),
    "nsym": (5, 9, 15, 25),
    "lex": (0.3, 1.0, 2.5, 5.0, 9.0),
    "nov": (1, 2, 3),
}


def sig_by_chan(r, chans=("ap", "in", "rw", "rwh")):
    """★ 채널 c 를 정렬할 때 쓸 이름→신호 dict.

    같은 lemma 가 두 채널에 나오면 신호가 **채널마다 다르다** (ap 의 lgg 는
    goal·결론, rw 의 lcp 는 redex·패턴). 예전 `sig` 는 마지막 줄이 이겨서
    채널 정렬이 남의 채널 신호로 점수를 매겼다. `sigc` 가 있으면 그 채널
    것을 우선하고, 없으면(구버전 풀) 병합본으로 떨어진다."""
    base = r.get("sig") or {}
    sc = r.get("sigc") or {}
    return {c: {**base, **(sc.get(c) or {})} for c in chans}


def feats(nm, sig, idf, g, chan_of, lex=None, gname=None, keep=None, stmts=None):
    s = sig.get(nm) or {}
    f = float(g) if g else 1.0
    out = []
    out.append(("lcp", _bucket(float(s.get("lcp", 0)) / f, BUCKETS["lcp"])))
    out.append(("lgg", _bucket(float(s.get("lgg", 0)) / f, BUCKETS["lgg"])))
    out.append(("e", _bucket(float(s.get("e", 8)), BUCKETS["e"])))
    out.append(("z", _bucket(float(s.get("z", 0)) / f, BUCKETS["z"])))
    out.append(("nm", _bucket(float(s.get("nm", 1)), BUCKETS["nm"])))
    # ★ redex 가 goal 안인가 (가설 안이 아니라) — `rewrite L` 이 기본형이다
    out.append(("ing", int(float(s.get("ing", 1)))))
    # ★ `hp` — 가설 rewrite 에서 **끝에서부터의 가설 위치**. 1이 가장 최근이다.
    #   증명은 대개 방금 만든 가설을 재작성한다. `rwh` 채널에만 값이 있다.
    #   (예전엔 `rwh` 도 goal 크기로 `z` 를 정규화해 신호가 무의미했다.)
    out.append(("hp", _bucket(float(s.get("hp", 0)), BUCKETS["hp"])))
    # ★ unfold: 그 상수가 goal 에 몇 번 나타나나
    out.append(("occ", _bucket(float(s.get("occ", 0)), BUCKETS["occ"])))
    out.append(("idf", _bucket(idf.get(nm, 0.0), BUCKETS["idf"])))
    # ★ **구조적 IDF** — 말뭉치 없이 lemma 모양에서 유도한 보편성.
    #   `rig` = 결론 전위순회 라벨 중 경직(`*` 아님) 개수.
    #   Î(L) = rig · log₂b  (Baire: k층 경직이면 b^(−k) 만 살아남는다)
    #   `f_equal` 은 머리가 유연해 rig 가 작고 `PTree.gso` 는 크다.
    #   이름별 조회표가 아니라 **구조**라 스플릿을 넘어가도 뜻이 유지된다.
    out.append(("rig", _bucket(float(s.get("rig", 0)), BUCKETS["rig"])))
    # ★ `idf` 대체 — **말뭉치를 안 보고** lemma 하나만으로 "보편성" 을 잰다.
    #   `applic-idf` 는 이름별 조회표라 스플릿을 넘어가면 항목이 없어
    #   미관측 lemma 가 `('idf',0)` → −4.60 감점을 먹는다(실측 −10.9pp).
    #   대신 진술문 자체의 성질을 쓴다 — 어디에나 맞는 lemma 는 짧고 추상적이다.
    #     slen  진술문 토큰 수     `f_equal` 은 짧고 `PTree.gso` 는 길다
    #     nbind `forall`·`->` 수   보편 lemma 는 바인더가 적다
    #     nsym  서로 다른 식별자 수  구체적일수록 많다
    _st = (stmts or {}).get(nm, "") if stmts else ""
    if _st:
        _tk = _TOK.findall(_st)
        out.append(("slen", _bucket(len(_tk), BUCKETS["slen"])))
        out.append(("nbind", _bucket(_st.count("forall") + _st.count("->"), BUCKETS["nbind"])))
        out.append(("nsym", _bucket(len(set(_tk)), BUCKETS["nsym"])))
    out.append(("ch", chan_of.get(nm, "?")))
    if lex is not None:
        out.append(("lex", _bucket(lex.get(nm, 0.0), BUCKETS["lex"])))
    # ★ 이름 겹침 — `repr_canonical` 이 goal 의 `repr_*` 와 어휘를 나눈다.
    #   Coq 프로젝트의 명명 관습을 그대로 신호로 쓴다.
    if gname is not None:
        nt = _name_toks(nm)
        out.append(("nov", _bucket(len(nt & gname), BUCKETS["nov"])))
    out.append(("std", 1 if _is_std(nm) else 0))
    # ★ 특징 개수는 lex·gname 이 주어졌는지에 달렸다. **조용히 줄면 안 된다** —
    #   lex·nov 는 학습 가중치 2·3위(+8.19 · +6.94)라 빠지면 @10 이 13pp 떨어진다.
    k = keep if keep is not None else KEEP
    if k is not None:
        out = [(a, b) for a, b in out if a in k]
        assert out, f"keep={k} 로 특징이 전부 사라졌다"
        return out
    _want = 12 + (lex is not None) + (gname is not None) + 3 * bool(_st)
    assert len(out) == _want, (
        f"특징이 {len(out)}개 (기대 {_want}) — lex={lex is not None} "
        f"gname={gname is not None}. feats 배선을 확인하라")
    assert len({k for k, _ in out}) == len(out), "특징 이름이 중복됐다"
    return out


def train_nb(rows, idf, chans_for_fn, skip_idx=None, skip_set=None):
    """P(f|gold) · P(f|¬gold) 를 센다. Laplace 보정."""
    import math as _m
    pos = collections.Counter(); neg = collections.Counter()
    npos = nneg = 0
    for r in rows:
        if skip_idx is not None and r["idx"] == skip_idx: continue
        if skip_set is not None and r["idx"] in skip_set: continue
        gold = r.get("gold")
        if not gold or not in_scope(r): continue
        gb = gold.split(".")[-1]
        chan = r.get("chan") or {}
        chan_of = {}
        for ch in ALL_CH:
            for x in chan.get(ch, []): chan_of.setdefault(x, ch)
        cand = set()
        for ch in chans_for_fn(r.get("tac", "")): cand |= set(chan.get(ch, []))
        if not cand: continue
        sig = r.get("sig") or {}
        SC = sig_by_chan(r)                     # ★ 후보의 자기 채널 신호로 센다
        g = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
        lexmap = r.get("lex") or {}
        gname = set(r.get("gnames") or [])
        for x in cand:
            isg = (x == gold or x.split(".")[-1] == gb)
            fs = feats(x, SC.get(chan_of.get(x, "ap"), sig), idf, g,
                       chan_of, lexmap, gname)
            if isg:
                npos += 1
                for kv in fs: pos[kv] += 1
            else:
                nneg += 1
                for kv in fs: neg[kv] += 1
    assert npos > 0, "train_nb: 양성 표본이 0 — gold 이 후보에 없다"
    assert nneg > 0, "train_nb: 음성 표본이 0"
    W = {}
    keys = set(pos) | set(neg)
    for kv in keys:
        p = (pos[kv] + 1.0) / (npos + 2.0)
        q = (neg[kv] + 1.0) / (nneg + 2.0)
        W[kv] = _m.log2(p / q)
    return W, npos, nneg


def nb_score_fn(W, idf, chan_of, lexmap=None, gname=None):
    def sc(nm, sig, _idf, g):
        return sum(W.get(kv, 0.0)
                   for kv in feats(nm, sig, idf, g, chan_of, lexmap, gname))
    return sc


if __name__ == "__main__":
    rows = [json.loads(l) for l in open(SRC)]
    assert rows, f"{SRC} 가 비었다"
    # ★ 정답은 원본에서 되읽는다 (1단 출력에는 없다)
    sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))
    HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
    NAMED = re.compile(r"\b(?:e?apply|e?rewrite|unfold|destruct|induction|case|elim"
                       r"|e?exact)\s+(?:<-\s*)?\(?\s*"
                       r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
    by = collections.defaultdict(list)
    for r in rows: by[r["idx"]].append(r)
    # ★ 어휘 특징 준비 — 말뭉치 전체에서 토큰 idf 를 한 번 센다
    _df = collections.Counter(); _ndoc = 0
    for r in rows:
        for stmt in (r.get("stmts") or {}).values():
            if stmt:
                _ndoc += 1
                for t in set(_TOK.findall(stmt)): _df[t] += 1
    _tok_idf = {t: math.log((_ndoc + 1.0) / (v + 1.0)) for t, v in _df.items()}

    for i, rs in by.items():
        try:
            d = get_thm_desc(get_theorem(CSSplit.TEST, i, Path("CoqStoq")),
                             Path("raw-data/coqstoq-test"), sdb)
            if d is None: continue
            proof = d.dp.proofs[d.idx]
        except Exception:
            continue
        for r in rs:
            try:
                t = proof.steps[r["k"]].step.text or ""
                m = NAMED.search(t); h = HEADT.match(t)
                if m:
                    g0 = m.group(1)
                    r["gold"] = g0
                    # ★ 지역 변수를 인자로 쓰면 검색 대상이 아니다
                    r["local"] = g0 in set(r.get("hyps") or [])
                if h:
                    g1 = h.group(1)
                    r["tac"] = ("rewrite" if g1.endswith("rewrite") else
                                "apply" if g1 in ("apply", "eapply") else g1)
                # ★ 어휘 겹침 — goal 텍스트 대 각 후보 진술문
                _gl = ""
                try:
                    _gs = proof.steps[r["k"]].goals
                    if _gs: _gl = _gs[0].goal or ""
                except Exception:
                    pass
                _gt = set(_TOK.findall(_gl))
                r["lex"] = {nm: lex_overlap(stmt, _gt, _tok_idf)
                            for nm, stmt in (r.get("stmts") or {}).items() if stmt}
                # goal 에 나오는 이름들의 어휘 조각
                _gn = set()
                for _x in _gt: _gn |= _name_toks(_x)
                r["gnames"] = sorted(_gn)
            except Exception:
                pass
    idf, cnt, n = build_idf(rows)
    print(f"■ applic-idf ({n} 지점 · 서로 다른 lemma {len(cnt):,}개)")
    freq = sorted(v / n for v in cnt.values())
    q = lambda p: freq[min(len(freq) - 1, int(p * len(freq)))]
    print(f"   생존빈도  중앙 {st.median(freq):.3f} · p75 {q(.75):.3f}"
          f" · p90 {q(.90):.3f} · p99 {q(.99):.3f} · max {max(freq):.3f}")
    uni = [k for k, v in cnt.items() if v / n >= 0.9]
    print(f"   ★ 90% 이상 지점에서 살아남는 것 {len(uni)}개 (= 정보 없음)")
    for k in sorted(uni, key=lambda x: -cnt[x])[:12]:
        print(f"      {k:<52s} {cnt[k]/n:.2f}")

    # 지점당: 보편 lemma 가 후보의 몇 %를 차지하나
    U = set(uni); tot = ub = 0
    for r in rows:
        a = set()
        for ch in GUESS_CH: a |= set((r.get("chan") or {}).get(ch, []))
        tot += len(a); ub += len(a & U)
    print(f"   지점당 후보 중 보편 비중 {100*ub/max(1,tot):.1f}%  ({ub:,}/{tot:,})")

    # gold 가 이 랭커에서 몇 위인가
    S = collections.Counter(); RK = []
    for r in rows:
        gold = r.get("gold")
        if not gold or not in_scope(r): continue
        gb = gold.split(".")[-1]
        cand = set()
        for ch in GUESS_CH: cand |= set((r.get("chan") or {}).get(ch, []))
        if not cand: continue
        sig = r.get("sig") or {}
        gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
        ranked = sorted(cand, key=lambda x: -score(x, sig, idf, gsz))
        pos = next((j for j, x in enumerate(ranked)
                    if x == gold or x.split(".")[-1] == gb), None)
        S["지점"] += 1
        if pos is not None:
            RK.append(pos)
            for K in (10, 20, 50, 100): S[f"@{K}"] += (pos < K)
    # ── 신호별 변별력 ──
    def eval_ranker(fn, name):
        S2 = collections.Counter(); RK2 = []
        for r in rows:
            gold = r.get("gold")
            if not gold or not in_scope(r): continue
            gb = gold.split(".")[-1]
            cand = set()
            for ch in chans_for(r.get("tac", "")):
                cand |= set((r.get("chan") or {}).get(ch, []))
            if not cand: continue
            sig = r.get("sig") or {}
            gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
            ranked = sorted(cand, key=lambda x: -fn(x, sig, idf, gsz))
            pos = next((j for j, x in enumerate(ranked)
                        if x == gold or x.split(".")[-1] == gb), None)
            S2["n"] += 1
            if pos is not None:
                RK2.append(pos)
                for K in (10, 20, 50, 100): S2[f"@{K}"] += (pos < K)
        m = max(1, S2["n"])
        print(f"   {name:14s}{S2['n']:6d}{100*len(RK2)/m:7.1f}%"
              f"{100*S2['@10']/m:7.1f}%{100*S2['@20']/m:7.1f}%"
              f"{100*S2['@50']/m:7.1f}%{100*S2['@100']/m:7.1f}%"
              f"{(st.median(RK2) if RK2 else 0):10,.0f}")

    # ── 무엇을 재는지 명시한다 ──
    nloc = sum(1 for r in rows if r.get("local"))
    noos = sum(1 for r in rows if r.get("gold") and not r.get("local")
               and r.get("tac") not in ACTIVE_TAC)
    tacs = collections.Counter(r.get("tac", "?") for r in rows
                               if in_scope(r) and r.get("gold"))
    print(f"\n■ 신호별 변별력")
    print(f"   ▸ 재는 것 : **필터 통과분 안에서의 순위만** "
          f"(프롬프트 진입 아님 — 그건 dn_rank_eval 의 ④ 표)")
    print(f"   ▸ 모집단 : 각 gold tactic 에 맞는 채널의 합집합")
    print(f"   ▸ 대상 tactic : "
          + " · ".join(f"{k} {v}" for k, v in tacs.most_common()))
    print(f"   ▸ 범위 : 채널 {'/'.join(ACTIVE_CH)} · gold tactic {'/'.join(ACTIVE_TAC)}"
          f"   (넓히려면 applic_rank.ACTIVE_CH / ACTIVE_TAC)")
    print(f"   ▸ 제외 : 지역 변수를 인자로 쓰는 스텝 {nloc}개"
          f"  (`destruct l`·`elim H` — 검색 대상이 아니다)")
    print(f"   ▸ 제외 : 범위 밖 tactic {noos}개"
          f"  (unfold·destruct·case·induction — 코드·풀에는 남아 있다)")
    print(f"   {'랭커':14s}{'지점':>6s}{'풀에':>8s}{'@10':>8s}{'@20':>8s}"
          f"{'@50':>8s}{'@100':>8s}{'순위중앙':>10s}")
    eval_ranker(lambda *a: 0.0, "무작위(기준)")
    eval_ranker(s_idf, "① applic-idf")
    eval_ranker(s_lgg, "② lgg/|goal|")
    eval_ranker(s_evar, "③ 1/(1+evar)")
    eval_ranker(s_lcp, "④ Baire LCP")
    eval_ranker(score, "가중합(임의)")
    _bit = make_bit_score(rows, idf)
    eval_ranker(_bit, "비트합(정보이론)")

    # ── ★★ 나이브 베이즈 (정리 단위 leave-one-out) ──
    #   같은 정리의 지점으로 학습하고 그 정리를 맞히면 과적합이다.
    #   정리 하나를 빼고 학습해서 그 정리만 채점한다.
    S3 = collections.Counter(); RK3 = []; T3 = collections.defaultdict(list)
    _idxs = sorted({r["idx"] for r in rows})
    _Wall, _np, _nn = train_nb(rows, idf, chans_for)
    # ★ 정리 단위 **5-겹** 교차검증. 정리마다 재학습(LOO)은 O(정리수 × 말뭉치)
    #   라 너무 느리다. 같은 정리가 학습·평가에 동시에 들어가지 않으면 충분하다.
    _NF = 5
    _fold = {x: j % _NF for j, x in enumerate(_idxs)}
    for _f in range(_NF):
        _te = {x for x in _idxs if _fold[x] == _f}
        W, _, _ = train_nb(rows, idf, chans_for, skip_set=_te)
        for r in rows:
            if r["idx"] not in _te: continue
            gold = r.get("gold")
            if not gold or not in_scope(r): continue
            gb = gold.split(".")[-1]
            chan = r.get("chan") or {}
            chan_of = {}
            for ch in ALL_CH:
                for x in chan.get(ch, []): chan_of.setdefault(x, ch)
            cand = set()
            for ch in chans_for(r.get("tac", "")): cand |= set(chan.get(ch, []))
            if not cand: continue
            sig = r.get("sig") or {}
            g = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
            sc = nb_score_fn(W, idf, chan_of, r.get("lex") or {},
                             set(r.get("gnames") or []))
            ranked = sorted(cand, key=lambda x: -sc(x, sig, idf, g))
            pos = next((j for j, x in enumerate(ranked)
                        if x == gold or x.split(".")[-1] == gb), None)
            S3["n"] += 1
            T3[r.get("tac", "?")].append(pos)
            if pos is not None:
                RK3.append(pos)
                for K in (10, 20, 50, 100): S3[f"@{K}"] += (pos < K)
    m3 = max(1, S3["n"])
    print(f"   {'★ 나이브베이즈(5겹)':14s}{S3['n']:6d}{100*len(RK3)/m3:7.1f}%"
          f"{100*S3['@10']/m3:7.1f}%{100*S3['@20']/m3:7.1f}%"
          f"{100*S3['@50']/m3:7.1f}%{100*S3['@100']/m3:7.1f}%"
          f"{(st.median(RK3) if RK3 else 0):10,.0f}")
    print(f"\n   ── 학습된 로그가능도비 (bit) 상위 ──")
    for kv, w in sorted(_Wall.items(), key=lambda x: -x[1])[:10]:
        print(f"      {str(kv):28s} {w:+6.2f}")
    print(f"   ── 하위 ──")
    for kv, w in sorted(_Wall.items(), key=lambda x: x[1])[:6]:
        print(f"      {str(kv):28s} {w:+6.2f}")
    print(f"\n   ── 나이브베이즈 · tactic 별 (순위만) ──")
    print(f"   {'tac':10s}{'지점':>6s}{'풀에':>8s}{'@10':>8s}{'@20':>8s}{'@50':>8s}"
          f"{'@100':>8s}{'순위중앙':>10s}")
    for tac in sorted(T3, key=lambda x: -len(T3[x])):
        v = T3[tac]; got = [x for x in v if x is not None]; mm = max(1, len(v))
        pc = lambda K: 100*sum(1 for x in got if x < K)/mm
        print(f"   {tac:10s}{len(v):6d}{100*len(got)/mm:7.1f}%{pc(10):7.1f}%"
              f"{pc(20):7.1f}%{pc(50):7.1f}%{pc(100):7.1f}%"
              f"{(st.median(got) if got else 0):10,.0f}")
    budget_report(rows, idf, _bit, chans_for)

    if S["지점"]:
        m = S["지점"]
        print(f"\n■ 이 랭커로 gold 순위 ({m} 지점) — 순위만, 프롬프트 아님")
        print(f"   풀에 {100*len(RK)/m:.1f}%  @10 {100*S['@10']/m:.1f}%"
              f"  @20 {100*S['@20']/m:.1f}%  @50 {100*S['@50']/m:.1f}%"
              f"  @100 {100*S['@100']/m:.1f}%  순위중앙 {st.median(RK) if RK else 0:.0f}")
    # ── tactic 별 ──
    _BIT = make_bit_score(rows, idf)
    print(f"\n■ tactic 별 (★비트합 랭커 · **순위만**, 프롬프트 아님)")
    print(f"   {'tac':10s}{'지점':>6s}{'풀에':>8s}{'@10':>8s}{'@20':>8s}{'@50':>8s}"
          f"{'@100':>8s}{'순위중앙':>10s}")
    T = collections.defaultdict(list)
    for r in rows:
        gold = r.get("gold")
        if not gold or not in_scope(r): continue
        gb = gold.split(".")[-1]
        cand = set()
        for ch in GUESS_CH: cand |= set((r.get("chan") or {}).get(ch, []))
        if not cand: continue
        sig = r.get("sig") or {}
        gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
        ranked = sorted(cand, key=lambda x: -_BIT(x, sig, idf, gsz))
        pos = next((j for j, x in enumerate(ranked)
                    if x == gold or x.split(".")[-1] == gb), None)
        T[r.get("tac", "기타")].append(pos)
    for tac in sorted(T, key=lambda x: -len(T[x])):
        v = T[tac]; got = [x for x in v if x is not None]; m2 = len(v)
        pc = lambda K: 100*sum(1 for x in got if x < K)/m2
        print(f"   {tac:10s}{m2:6d}{100*len(got)/m2:7.1f}%{pc(10):7.1f}%{pc(20):7.1f}%"
              f"{pc(50):7.1f}%{pc(100):7.1f}%"
              f"{(st.median(got) if got else 0):10,.0f}")




