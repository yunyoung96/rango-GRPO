#!/usr/bin/env python3
"""**이름을 안 쓰는 구조 기반 retrieval** 을 재고 이름 기반과 비교한다.

## 왜 이름을 버려야 하나

v8 은 premise lemma 이름을 `L0, L1, …` 로 익명화한다. 그러면 이름 기반 신호는
**모델이 쓸 수 없다** — 검색이 gold 를 top50 에 넣어줘도 모델은 `L3` 만 보고 왜 관련
있는지 알 수 없다. 게다가 이름 의존 검색은 다른 프로젝트로 전이하지 않는다
(`Zlt_le_succ` 라는 작명 관례는 그 라이브러리의 것이다).

`applicable.py` 는 이름 없이 **항 구조**만으로 판정한다. 그것을 검색 점수로 쓴다.

## 재는 방식

  · A 적용가능성    apply / rewrite 로 실제 단일화되는가 (0/1)
  · B head 일치     goal 결론과 lemma 결론의 최상위 head 가 같은가
  · C 연산자 프로파일  goal 과 lemma 결론에 쓰인 **연산자 집합**의 Jaccard
  · D 구조 깊이·모양  결론 트리의 노드수·깊이 유사도
  · E 위 조합 + TF-IDF prior

각 신호는 이름을 **하나도** 쓰지 않는다(연산자·구조만). 이름 기반 최고안과 나란히 둔다.

사용: python3 scripts/research_structural.py [n]
"""
import collections
import copy
import math
import os
import re
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from data_management.dataset_file import (DatasetFile, get_ids_from_goal,  # noqa: E402
                                          get_ids_from_sentence)
from data_management.sentence_db import SentenceDB  # noqa: E402
from proof_retrieval.tfidf import tf_idf  # noqa: E402
from premise_selection.premise_filter import PremiseFilter, PremiseFilterConf  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402
from tactic_gen.applicable import (decompose, parse, parse_toks, canon, as_eq,  # noqa: E402
                                   as_impl, match, subterms, goal_conclusion, _INFIX)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "train").upper()
CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")
POOL_CAP = int(os.environ.get("POOL_CAP", "1200"))   # 구조 판정을 거는 상위 후보 수

cc = yaml.safe_load(open(CONF))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), N)
sdb = SentenceDB.load(conf.sentence_db_loc)
pf_conf = PremiseFilterConf.from_yaml(tdc["formatter_conf"]["premise"]["premise_filter"])
pfilter = PremiseFilter(pf_conf.coq_excludes, pf_conf.non_coq_excludes,
                        pf_conf.general_excludes)

_NAME = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                   r"Instance|Axiom|Proposition|Example|Let|Program\s+\w+)\s+"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
_SUBW = re.compile(r"[._]")


def declname(t):
    m = _NAME.match(t or "")
    return m.group(1).split(".")[-1] if m else None


# ── 구조 특징 추출 (이름을 쓰지 않는다) ──────────────────────────────────────
def head_of(t):
    while t is not None and t[0] == "app":
        t = t[1]
    if t is None:
        return None
    return t[1] if t[0] in ("id", "op") else None


def ops_of(t, out=None):
    """트리에 쓰인 **연산자 심볼** 집합. 식별자는 안 본다 = 이름 무관."""
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
    """(노드수, 깊이). 이름과 무관한 구조 크기."""
    if t is None or t[0] in ("id", "opq"):
        return 1, d
    if t[0] == "app":
        a = shape(t[1], d + 1)
        b = shape(t[2], d + 1)
        return 1 + a[0] + b[0], max(a[1], b[1])
    a = shape(t[2], d + 1)
    b = shape(t[3], d + 1)
    return 1 + a[0] + b[0], max(a[1], b[1])


import functools  # noqa: E402


_HEADW = re.compile(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*|<->|->|/\\|\\/|"
                    r"<=|>=|<>|=|<|>|\+\+|\+|-|\*|/|\^|::|&&|\|\|")


def _fallback_heads(text: str):
    """결론 파싱이 안 될 때: 전체 텍스트의 식별자·연산자를 head 로 근사.

    ★ 이걸 안 두면 파싱 실패 premise 가 전부 0점이 되어 꼬리로 밀리고, C' 의 R@50 이
      baseline 보다 낮아진다(47% vs 56%). 상위 정확도는 지키면서 꼬리를 메운다.
    """
    out = collections.Counter()
    for x in _HEADW.findall(text or ""):
        out[x.split(".")[-1]] += 1
    return out


@functools.lru_cache(maxsize=300_000)
def prem_struct(text: str):
    """premise → (메타변수, 정규화 결론트리, head, 연산자집합, (노드수,깊이), head다중집합)."""
    d = decompose(text)
    c = parse_toks(d[2]) if d is not None else None
    if d is None or c is None:
        # 구조는 못 얻지만 head 근사는 준다 → 완전 탈락을 막는다
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
    for _ in range(6):
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


# ── 신호들 ────────────────────────────────────────────────────────────────
def sig_applicable(gs, ps):
    """A: 실제로 단일화되는가 (apply 또는 rewrite 양방향)."""
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
                continue
            if any(match(side, s, mv, {}) for s in subs):
                return 1.0
    return 0.0


def sig_head(gs, ps):
    """B: 결론 최상위 head 일치. (head 는 함수 이름이지만 **전역 상수**이고 정규화 대상이 아니다)"""
    return 1.0 if (ps[2] is not None and ps[2] == gs[2]) else 0.0


def sig_ops(gs, ps):
    """C: 연산자 집합 Jaccard — 순수 기호, 이름 무관."""
    a, b = ps[3], gs[3]
    if not a and not b:
        return 0.0
    u = len(a | b)
    return len(a & b) / u if u else 0.0


def sig_match_size(gs, ps):
    """A': 적용가능성을 **연속값**으로. 매칭된 부분항이 클수록 관련이 깊다.

    이진 신호(0/1)는 선택성이 56% 라 후보의 절반이 동점이 되어 순위를 못 정한다.
    매칭된 부분항의 노드 수를 goal 크기로 나눠 0~1 연속값으로 만든다.
    """
    mv, c = ps[0], ps[1]
    if c is None:
        return 0.0
    gts, subs, gn = gs[1], gs[5], gs[4][0]
    best = 0.0
    for x in gts:                                   # apply 방향: 전체 매칭이면 1.0
        if match(c, x, mv, {}):
            best = max(best, shape(x)[0] / max(gn, 1))
    eq = as_eq(c)
    if eq:
        for side in eq:
            if side[0] == "id" and side[1] in mv:
                continue
            for sub in subs:                        # rewrite: 매칭된 부분항 크기
                if match(side, sub, mv, {}):
                    best = max(best, shape(sub)[0] / max(gn, 1))
    return best


def _heads_multiset(t, out=None):
    """결론 트리의 **모든 부분항 head** 를 모은다.

    함수 이름을 쓰지만 **lemma 이름은 아니다** — `Z.succ`·`length` 같은 전역 상수이고
    v8 정규화 대상이 아니다(정규화는 lemma 이름 L#, 주입정의 T#/f#, 생성자 C# 만 바꾼다).
    TF-IDF 와 다른 점: **결론에서만** 뽑고 부분항 위치를 보므로 가설부 노이즈가 없다.
    """
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


def sig_concl_heads(gs, ps, idf):
    """C': 결론 부분항 head 의 **IDF 가중 코사인**. 연속값이고 위치를 반영한다."""
    a = ps[5]
    b = gs[6]
    if not a or not b:
        return 0.0
    num = sum(a[k] * b[k] * idf.get(k, 1.0) ** 2 for k in (a.keys() & b.keys()))
    na = math.sqrt(sum((v * idf.get(k, 1.0)) ** 2 for k, v in a.items()))
    nb = math.sqrt(sum((v * idf.get(k, 1.0)) ** 2 for k, v in b.items()))
    return num / (na * nb) if na and nb else 0.0


# ── F: 정렬 익명 구조 표현의 n-gram 유사도 (이름 0, 프로젝트 무관) ──────────
#   structural_repr.pair_tokens 가 goal·premise 를 닫힌 어휘 57개로 익명화한다.
#   공유 상수는 S0..S9, goal 전용 G, premise 전용 P, 지역 V, 메타 M.
#   그 토큰열의 n-gram 을 비교하면 **이름 없이** 구조 맞물림을 잰다.
from tactic_gen.structural_repr import pair_tokens  # noqa: E402


def _ngrams(toks, n=3):
    return collections.Counter(tuple(toks[i:i + n]) for i in range(len(toks) - n + 1))


def sig_struct_ngram(state, ptext):
    """goal 부분과 premise 부분의 n-gram 겹침. 결론끼리·가설끼리를 나눠 본다."""
    toks, _st = pair_tokens(state, ptext)
    try:
        sep = toks.index("[SEP]")
    except ValueError:
        return 0.0
    gpart, ppart = toks[:sep], toks[sep + 1:]

    def seg(ts, tag):
        out, on = [], False
        for t in ts:
            if t in ("[GH]", "[GC]", "[PH]", "[PC]"):
                on = (t == tag)
                continue
            if on:
                out.append(t)
        return out

    def jac(a, b):
        A, B = _ngrams(a), _ngrams(b)
        if not A or not B:
            return 0.0
        inter = sum((A & B).values())
        return inter / max(sum((A | B).values()), 1)

    concl = jac(seg(gpart, "[GC]"), seg(ppart, "[PC]"))
    hyp = jac(seg(gpart, "[GH]"), seg(ppart, "[PH]"))
    return concl * 0.75 + hyp * 0.25          # 결론이 주, 가설이 보조


# ── G: anti-unification (최소일반화) 기반 구조 유사도 ──────────────────────
#   두 항의 **가장 구체적인 공통 일반화**를 구해 그 크기를 본다.
#     au(f a b, f a c) = f a X   → 3/4 유지  (매우 유사)
#     au(f a b, g a b) = X       → 1/4 유지  (head 가 다르면 통째로 일반화)
#   C'(head 다중집합 코사인)는 **위치를 무시**하지만 AU 는 트리 모양을 그대로 반영한다.
#   이름은 "같은가/다른가" 만 쓰므로(문자열 자체를 안 씀) 프로젝트 무관하다.
def _au(a, b, cnt):
    """anti-unify. 공통 구조 노드 수를 cnt[0] 에 누적하고 트리 크기를 돌려준다."""
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
        cnt[0] += 2                      # 노드 + 연산자 심볼
        _au(a[2], b[2], cnt)
        _au(a[3], b[3], cnt)
        return
    return                                # 여기서 일반화(변수) — 더 안 센다


# ── H: 지역성 prior (이름 무관·프로젝트 무관) ──────────────────────────────
#   증명은 **가까운 곳의 정리**를 쓰는 경향이 있다: 같은 파일 > 같은 모듈 > 먼 파일.
#   이건 작명 관례가 아니라 코드 구성의 보편적 성질이라 새 프로젝트에도 그대로 통한다.
#   Sentence 에 file_path·module·line 이 있으므로 값싸게 계산된다.
def sig_locality(cur_file: str, _unused, p) -> float:
    """파일 경로 근접성. (줄 번호는 데이터에 없어서 못 쓴다 — step.term.line 이 None)

    같은 파일 > 같은 디렉토리 > 같은 프로젝트 > 무관.
    """
    fp = getattr(p, "file_path", "") or ""
    if not fp or not cur_file:
        return 0.0
    a = [x for x in fp.split("/") if x and x != ".."]
    b = [x for x in cur_file.split("/") if x and x != ".."]
    if a and b and a[-1] == b[-1]:
        return 1.0                              # 같은 파일
    k = 0
    for x, y in zip(a, b):
        if x != y:
            break
        k += 1
    return min(0.6, 0.1 * k)


# ── Coq 도메인 신호 (학습 불필요 · 이름 문자열이 아니라 증명시스템의 성질) ──────
#
#   I 타입-모듈 친화도 : goal 이 다루는 **타입**의 이름은 그 lemma 가 사는 **모듈/파일**에
#     나타난다. `a : Z` 를 다루는 증명은 `ZArith/BinInt.v` 의 lemma 를 쓴다.
#     이건 lemma 작명 관례가 아니라 **Coq 라이브러리가 타입별로 조직된다는 구조**이고,
#     타입 이름은 표준 라이브러리 어휘라 프로젝트를 건너 공유된다.
#
#   J evar 개수 : `apply X` 는 X 의 메타변수를 goal 과 단일화해 정한다. **결론에 안 나오는**
#     변수는 정할 수가 없어 evar 로 남고 `eapply` 가 필요해진다. 그런 변수가 적을수록
#     쓰기 쉬운 lemma다 — Coq 의 실제 동작을 그대로 반영한 난이도 지표.
#
#   K rewrite 방향 : 항 재작성 시스템은 보통 **항을 줄이는** 방향으로 쓴다(정지성).
#     `length (rev l) = length l` 는 왼쪽이 크다. goal 에 큰 쪽이 있으면 정방향이 유망.
_TYHEAD = re.compile(r"[A-Za-z_][\w']*")


def goal_type_names(state: str) -> set:
    """goal 가설의 **타입**에 나오는 이름들. `a, b : Z` → {Z}, `l : list A` → {list}."""
    body = (state or "").split("[GOAL]")[0]
    parts = re.split(r"\n\s*\n", body)
    out = set()
    if len(parts) > 1:
        for ln in parts[0].split("\n"):
            seg = ln.split(":", 1)
            if len(seg) == 2:
                for t in _TYHEAD.findall(seg[1])[:4]:
                    if len(t) >= 2:
                        out.add(t)
    return out


def sig_type_module(gtypes: set, p) -> float:
    """I: goal 의 타입 이름이 premise 의 모듈·파일경로에 나타나는가."""
    if not gtypes:
        return 0.0
    where = set()
    for m in (getattr(p, "module", None) or []):
        where |= set(_TYHEAD.findall(str(m)))
    fp = getattr(p, "file_path", "") or ""
    for seg in fp.replace("\\", "/").split("/"):
        where |= set(_TYHEAD.findall(seg.replace(".v", "")))
    if not where:
        return 0.0
    # 타입 이름과 모듈 이름의 겹침(부분 일치도 인정: Z ⊂ ZArith)
    hit = 0
    for t in gtypes:
        if any(t == w or (len(t) >= 2 and t in w) for w in where):
            hit += 1
    return hit / len(gtypes)


def _vars_in(t, out=None):
    if out is None:
        out = set()
    if t is None:
        return out
    if t[0] == "id":
        out.add(t[1])
    elif t[0] == "app":
        _vars_in(t[1], out)
        _vars_in(t[2], out)
    elif t[0] == "op":
        _vars_in(t[2], out)
        _vars_in(t[3], out)
    return out


def sig_evars(ps) -> float:
    """J: 결론에 안 나오는 메타변수(=evar)가 적을수록 1 에 가깝다."""
    mv, c = ps[0], ps[1]
    if c is None or not mv:
        return 1.0
    ev = set(mv) - _vars_in(c)
    return 1.0 / (1.0 + len(ev))


def sig_rewrite_dir(gs, ps) -> float:
    """K: 등식이면 **큰 쪽**이 goal 에 있는지(항을 줄이는 방향인지)."""
    c = ps[1]
    if c is None:
        return 0.0
    eq = as_eq(c)
    if not eq:
        return 0.0
    mv = ps[0]
    ls, rs = shape(eq[0])[0], shape(eq[1])[0]
    big, small = (eq[0], eq[1]) if ls >= rs else (eq[1], eq[0])
    if shape(big)[0] <= shape(small)[0]:
        return 0.0
    for sub in gs[5]:                      # goal 부분항에 큰 쪽이 맞물리나
        if match(big, sub, mv, {}):
            return 1.0
    return 0.0


def sig_anti_unify(gs, ps):
    """AU 유지 노드수 / 두 항 중 큰 쪽 크기. goal 결론 전체와 부분항 모두 시도."""
    c = ps[1]
    if c is None:
        return 0.0
    pn = shape(c)[0]
    best = 0.0
    for tgt in gs[5]:                     # goal 결론의 모든 부분항
        gn = shape(tgt)[0]
        if gn < 2 or pn < 2:
            continue
        cnt = [0]
        _au(c, tgt, cnt)
        if cnt[0] < 2:
            continue
        best = max(best, cnt[0] / max(gn, pn))
    # rewrite 는 등식 한 변이 부분항과 맞물린다 → 그쪽도 본다
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


def sig_hyp_match(gs, ps):
    """E: lemma **가설부**의 head 가 goal 가설블록에 이미 있는가.

    `apply X` 는 X 의 가설을 새 subgoal 로 남긴다. 그 가설이 goal 가설에 **이미 있으면**
    바로 닫히므로 훨씬 유망한 후보다. 결론만 보는 신호들이 놓치는 축이다.
    """
    ph = ps[6]
    if not ph:
        return 0.0
    gh = gs[7]
    if not gh:
        return 0.0
    return len(ph & gh) / len(ph)


def sig_shape(gs, ps):
    """D: 결론 크기·깊이 유사도."""
    (pn, pd), (gn, gd) = ps[4], gs[4]
    return (1.0 / (1 + abs(pn - gn) / max(gn, 1))) * 0.5 + \
           (1.0 / (1 + abs(pd - gd))) * 0.5


METHODS = [
    ("baseline tfidf (이름 포함)", "name"),
    ("이름subword (이름 의존)", "namesub"),
    ("★ A 적용가능성만", "A"),
    ("★ B head 일치만", "B"),
    ("★ C 연산자 Jaccard만", "C"),
    ("★ A+B+C 구조만 (이름 0)", "ABC"),
    ("★ A+B+C+D 구조만", "ABCD"),
    ("★ tfidf + A×30 (혼합)", "T+A"),
    ("★ tfidf + (A+B+C)×20 (혼합)", "T+ABC"),
    ("★★ A' 매칭크기(연속)만", "A2"),
    ("★★ C' 결론head IDF코사인만", "C2"),
    ("★★ A'+C' 구조만 (lemma이름 0)", "A2C2"),
    ("★★ A'+B+C'+D 구조만", "SALL"),
    ("★★ tfidf + (A'+C')×20", "T+A2C2"),
    ("★★ tfidf + A'×15 + C'×25", "T+MIX"),
    ("◆ RRF(tfidf, C')", "RRF2"),
    ("◆ RRF(tfidf, C', A')", "RRF3"),
    ("◆ RRF(tfidf, C') + A' 가산", "RRF2A"),
    ("◆ RRF 가중(tfidf×1, C'×2)", "RRFW"),
    ("◇ RRF(tfidf,C') K=10", "RRF_K10"),
    ("◇ RRF(tfidf,C') K=30", "RRF_K30"),
    ("◇ RRF(tfidf,C') K=120", "RRF_K120"),
    ("◇ RRF(tfidf,C') + E 가산", "RRF_E"),
    ("◇ RRF(tfidf,C',E)", "RRF_CE"),
    ("◇ RRF(tfidf,C',이름subword) 3-way", "RRF3W"),
    ("◇ RRF(tfidf,C',이름sub) + A'E 가산", "RRF3WAE"),
    ("▲ F 구조n-gram만 (이름 0·전이)", "F"),
    ("▲ RRF(tfidf, F)", "RRF_F"),
    ("▲ RRF(tfidf, C', F) 이름 0", "RRF_CF"),
    ("▲ RRF(tfidf, C', F) + A'E", "RRF_CFAE"),
    ("▲ RRF(tfidf, C', F, 이름sub)", "RRF4W"),
    ("● G anti-unify 만", "G"),
    ("● RRF(tfidf, G)", "RRF_G"),
    ("● RRF(tfidf, C', G) 이름 0", "RRF_CG"),
    ("● RRF(tfidf, C', G, 이름sub)", "RRF_CGN"),
    ("● RRF(tfidf,C',G,이름sub)+A'E", "RRF_CGNAE"),
    ("◐ H 지역성만", "H"),
    ("◐ RRF(tfidf, C', H) 이름 0", "RRF_CH"),
    ("◐ RRF(tfidf,C',H,이름sub)", "RRF_CHN"),
    ("◐ RRF(tfidf,C',H,이름sub)+A'E", "RRF_CHNAE"),
    ("★I 타입-모듈만", "I"),
    ("★J evar 적음만", "J"),
    ("★K rewrite 방향만", "K"),
    ("★ RRF(tfidf,C',H,I) 이름 0", "RRF_CHI"),
    ("★ RRF(tfidf,C',H,I)+JK 가산", "RRF_CHIJK"),
    ("★ RRF(tfidf,C',I) 이름 0", "RRF_CI"),
    ("▣ [필터] 적용가능만 → RRF3", "F_A_RRF3"),
    ("▣ [필터] 적용가능만 → RRF(C',H,I)", "F_A_CHI"),
    ("▣ [계층] 적용가능 우선 + RRF3", "L_A_RRF3"),
    ("▣ [필터] 적용가능+판정불가 → RRF3", "F_AU_RRF3"),
]
KS = (10, 20, 50)
hits = {m[0]: collections.Counter() for m in METHODS}
mrr = {m[0]: 0.0 for m in METHODS}
el = {m[0]: 0.0 for m in METHODS}
n_case = 0
cap_hit = 0

for i in range(N):
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    st = getattr(e, "proof_state", "") or ""
    loc = local_names(st)
    golds = gold_lemmas(e.next_steps[0] if getattr(e, "next_steps", None) else "", loc)
    if not golds:
        continue
    sid = ds.shuffled_idx.get_idx(ds.split, i)
    try:
        dp = DatasetFile.load(conf.data_loc / "data_points" / sid.file, sdb)
        proof = dp.proofs[sid.proof_idx]
        step = proof.steps[sid.step_idx]
    except Exception:
        continue
    if not step.goals:
        continue
    pool = [p for p in dp.get_premises_before(proof) if pfilter.filter_premise(p)]
    if not pool:
        continue
    names = [declname(getattr(p, "text", "")) for p in pool]
    gidx = [j for j, nm in enumerate(names) if nm in golds]
    if not gidx:
        continue

    gs = goal_struct(st)
    if gs is None:
        continue
    n_case += 1

    h_ids, g_ids = get_ids_from_goal(step.goals[0])
    docs_full = [get_ids_from_sentence(p) for p in pool]
    t0 = time.time()
    base_scores = tf_idf(h_ids + g_ids, docs_full)
    t_base = time.time() - t0

    # ★ 구조 판정은 비싸다 → tfidf 상위 POOL_CAP 개에만 걸고, 나머지는 0 으로 둔다.
    #   (gold 가 그 밖이면 구조 방식도 못 잡으므로 상한 도달 여부를 따로 센다)
    order0 = sorted(range(len(pool)), key=lambda j: -base_scores[j])
    cand = order0[:POOL_CAP]
    if not all(j in set(cand) for j in gidx):
        cap_hit += 1
    # 결론 head 의 IDF 는 **이 후보집합**에서 계산한다(문서빈도 = 그 head 를 쓰는 lemma 수)
    t1 = time.time()
    pss = {}
    df: collections.Counter = collections.Counter()
    for j in cand:
        ps = prem_struct(getattr(pool[j], "text", "") or "")
        pss[j] = ps
        if ps is not None:
            for k in ps[5]:
                df[k] += 1
    nd = max(len(cand), 1)
    idf = {k: math.log(nd / v) for k, v in df.items()}
    feats = {}
    for j in cand:
        ps = pss[j]
        if ps is None:
            feats[j] = (0.0,) * 7
            continue

        feats[j] = (sig_applicable(gs, ps), sig_head(gs, ps), sig_ops(gs, ps),
                    sig_shape(gs, ps), sig_match_size(gs, ps),
                    sig_concl_heads(gs, ps, idf), sig_hyp_match(gs, ps))
    t_struct = time.time() - t1

    # ── rank fusion 준비: 각 랭커의 순위를 미리 구한다 ──
    #   tfidf 와 C' 는 **실패 방식이 다르다**(단어 겹침 vs 결론 구조). 점수 스케일이 달라
    #   선형 합은 한쪽에 눌리므로, 순위의 역수를 더하는 RRF 로 합친다.
    def ranks_of(score_list):
        o = sorted(range(len(pool)), key=lambda j: -score_list[j])
        r = [0] * len(pool)
        for pos, j in enumerate(o):
            r[j] = pos
        return r

    r_tfidf = ranks_of(base_scores)
    c2_all = [0.0] * len(pool)
    a2_all = [0.0] * len(pool)
    for j in cand:
        a2_all[j] = feats[j][4]
        c2_all[j] = feats[j][5]
    e2_all = [0.0] * len(pool)
    for j in cand:
        e2_all[j] = feats[j][6]
    r_c2 = ranks_of(c2_all)
    r_a2 = ranks_of(a2_all)
    r_e2 = ranks_of(e2_all)
    f_all = [0.0] * len(pool)
    for j in cand:
        f_all[j] = sig_struct_ngram(st, getattr(pool[j], "text", "") or "")
    r_f = ranks_of(f_all)
    g_all = [0.0] * len(pool)
    for j in cand:
        ps = pss[j]
        g_all[j] = sig_anti_unify(gs, ps) if ps is not None else 0.0
    r_g = ranks_of(g_all)
    _cf = getattr(dp.file_context, "file", "") or ""
    # 현재 정리의 줄 번호: step 자체엔 없고 term(Sentence) 에 있다
    _cl = (getattr(getattr(step, "term", None), "line", 0)
           or getattr(getattr(proof, "theorem", None), "line", 0) or 0)
    h_all = [sig_locality(_cf, _cl, pool[j]) if j in set(cand) else 0.0
             for j in range(len(pool))]
    r_h = ranks_of(h_all)
    _gt = goal_type_names(st)
    i_all = [sig_type_module(_gt, pool[j]) if j in set(cand) else 0.0
             for j in range(len(pool))]
    j_all = [sig_evars(pss[j]) if (j in pss and pss[j] is not None) else 0.0
             for j in range(len(pool))]
    k_all = [sig_rewrite_dir(gs, pss[j]) if (j in pss and pss[j] is not None) else 0.0
             for j in range(len(pool))]
    r_i = ranks_of(i_all)
    # 이름subword 랭킹은 3-way RRF 에 필요하므로 미리 구한다
    _docs_ns = [list(d) + [w for w in _SUBW.split(nm or "") if len(w) >= 2] * 2
                for d, nm in zip(docs_full, names)]
    _ns_scores = tf_idf(h_ids + g_ids, _docs_ns)
    r_nsub = ranks_of(_ns_scores)
    RRF_K = 60.0                       # 표준값. 상위 몇 개에 얼마나 무게를 줄지 정한다

    nsub = None
    for name, kind in METHODS:
        t2 = time.time()
        if kind == "name":
            sc = base_scores
        elif kind == "namesub":
            sc = _ns_scores
        else:
            sc = [0.0] * len(pool)
            for j in cand:
                a, b, c, d, a2, c2, e2 = feats[j]
                if kind == "A2":
                    v = a2
                elif kind == "C2":
                    v = c2
                elif kind == "A2C2":
                    v = a2 * 2 + c2 * 3
                elif kind == "SALL":
                    v = a2 * 2 + b + c2 * 3 + d * 0.3
                elif kind == "T+A2C2":
                    v = base_scores[j] * 100 + (a2 * 2 + c2 * 3) * 20
                elif kind == "T+MIX":
                    v = base_scores[j] * 100 + a2 * 15 + c2 * 25
                elif kind == "RRF2":
                    v = 1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                elif kind == "RRF3":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + 1 / (RRF_K + r_a2[j]))
                elif kind == "RRF2A":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + a2 * 0.002)
                elif kind == "RRFW":
                    v = 1 / (RRF_K + r_tfidf[j]) + 2 / (RRF_K + r_c2[j])
                elif kind.startswith("RRF_K"):
                    kk = float(kind[5:])
                    v = 1 / (kk + r_tfidf[j]) + 1 / (kk + r_c2[j])
                elif kind == "RRF_E":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + e2 * 0.002)
                elif kind == "RRF_CE":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + 1 / (RRF_K + r_e2[j]))
                elif kind == "RRF3W":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + 1 / (RRF_K + r_nsub[j]))
                elif kind == "F":
                    v = f_all[j]
                elif kind == "RRF_F":
                    v = 1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_f[j])
                elif kind == "RRF_CF":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + 1 / (RRF_K + r_f[j]))
                elif kind == "RRF_CFAE":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + 1 / (RRF_K + r_f[j]) + (a2 + e2) * 0.001)
                elif kind == "RRF4W":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + 1 / (RRF_K + r_f[j]) + 1 / (RRF_K + r_nsub[j]))
                elif kind == "G":
                    v = g_all[j]
                elif kind == "RRF_G":
                    v = 1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_g[j])
                elif kind == "RRF_CG":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + 1 / (RRF_K + r_g[j]))
                elif kind == "RRF_CGN":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + 1 / (RRF_K + r_g[j]) + 1 / (RRF_K + r_nsub[j]))
                elif kind == "RRF_CGNAE":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + 1 / (RRF_K + r_g[j]) + 1 / (RRF_K + r_nsub[j])
                         + (a2 + e2) * 0.001)
                elif kind == "H":
                    v = h_all[j]
                elif kind == "RRF_CH":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + 1 / (RRF_K + r_h[j]))
                elif kind == "RRF_CHN":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + 1 / (RRF_K + r_h[j]) + 1 / (RRF_K + r_nsub[j]))
                elif kind == "RRF_CHNAE":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + 1 / (RRF_K + r_h[j]) + 1 / (RRF_K + r_nsub[j])
                         + (a2 + e2) * 0.001)
                elif kind == "I":
                    v = i_all[j]
                elif kind == "J":
                    v = j_all[j]
                elif kind == "K":
                    v = k_all[j]
                elif kind == "RRF_CHI":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + 1 / (RRF_K + r_h[j]) + 1 / (RRF_K + r_i[j]))
                elif kind == "RRF_CHIJK":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + 1 / (RRF_K + r_h[j]) + 1 / (RRF_K + r_i[j])
                         + (j_all[j] + k_all[j]) * 0.002)
                elif kind == "RRF_CI":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + 1 / (RRF_K + r_i[j]))
                elif kind in ("F_A_RRF3", "F_A_CHI", "L_A_RRF3", "F_AU_RRF3"):
                    # ▣ **"적용 가능한 것 먼저 찾고" 그 안에서 랭킹** — 지금까지는
                    #   적용가능성을 랭킹 신호로만 썼다(이진이라 절반이 동점 → R@50 3.1%).
                    #   여기서는 순서를 뒤집어 **필터를 먼저** 건다.
                    base_rrf = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                                + 1 / (RRF_K + r_nsub[j]))
                    chi = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                           + 1 / (RRF_K + r_h[j]) + 1 / (RRF_K + r_i[j]))
                    _ps = pss.get(j)
                    parsed = _ps is not None and _ps[1] is not None
                    usable = (a > 0) or (not parsed)     # 판정불가는 보수적으로 통과
                    if kind == "F_A_RRF3":
                        v = base_rrf if a > 0 else -1e9   # 적용불가는 완전 배제
                    elif kind == "F_A_CHI":
                        v = chi if a > 0 else -1e9
                    elif kind == "F_AU_RRF3":
                        v = base_rrf if usable else -1e9  # 판정불가까지 살림(재현율↑)
                    else:                                  # 계층: 배제하지 않고 뒤로
                        v = base_rrf + (1e6 if a > 0 else 0.0)
                elif kind == "RRF3WAE":
                    v = (1 / (RRF_K + r_tfidf[j]) + 1 / (RRF_K + r_c2[j])
                         + 1 / (RRF_K + r_nsub[j]) + (a2 + e2) * 0.001)
                elif kind == "A":
                    v = a
                elif kind == "B":
                    v = b
                elif kind == "C":
                    v = c
                elif kind == "ABC":
                    v = a * 3 + b * 2 + c
                elif kind == "ABCD":
                    v = a * 3 + b * 2 + c + d * 0.5
                elif kind == "T+A":
                    v = base_scores[j] * 100 + a * 30
                else:
                    v = base_scores[j] * 100 + (a * 3 + b * 2 + c) * 20
                sc[j] = v
        el[name] += time.time() - t2 + (
            t_base if kind.startswith(("name", "T+", "RRF")) else 0)
        if kind not in ("name", "namesub"):
            el[name] += t_struct
        order = sorted(range(len(pool)), key=lambda j: -sc[j])
        rank = min((order.index(j) for j in gidx), default=10 ** 9)
        for k in KS:
            hits[name][k] += (rank < k)
        mrr[name] += 1.0 / (rank + 1) if rank < 10 ** 9 else 0.0

print(f"\n■ {SPLIT} — 비교 사례 {n_case}건 (gold 가 풀에 있는 것만) · 구조판정 상위 {POOL_CAP}개")
print(f"   gold 가 tfidf 상위 {POOL_CAP} 밖이라 구조 방식이 원천적으로 못 본 경우: "
      f"{cap_hit}/{n_case}\n")
print(f"   {'방식':32s} {'R@10':>7s} {'R@20':>7s} {'R@50':>8s} {'MRR':>7s} {'ms/건':>8s}")
base = None
for name, _ in METHODS:
    r = [hits[name][k] / max(n_case, 1) * 100 for k in KS]
    if base is None:
        base = r[2]
    d = r[2] - base
    print(f"   {name:32s} {r[0]:6.1f}% {r[1]:6.1f}% {r[2]:6.1f}%"
          f"{'' if abs(d) < 0.05 else f'{d:+5.1f}':>6s} {mrr[name]/max(n_case,1):7.3f}"
          f" {el[name]/max(n_case,1)*1000:8.1f}")
print(f"\n   R@50 의 95% 오차: ±{1.96*math.sqrt(base/100*(1-base/100)/max(n_case,1))*100:.1f}pp")
