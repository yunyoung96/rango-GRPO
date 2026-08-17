#!/usr/bin/env python3
"""**retrieval 개선 연구용 실험대** — 여러 스코어링 방식을 같은 자로 재고 비교한다.

## 왜 이 틀이 필요한가

지금 gold 가 top50 에 드는 비율은 40.6% 이고, 원인의 38.4% 는 *"풀에는 있는데 검색이 못
뽑는다"* 이다. 즉 **후보를 더 긁어올 필요도, 토큰을 늘릴 필요도 없다** — 스코어링만 고치면
된다. 그러려면 여러 안을 같은 데이터·같은 지표로 비교할 수 있어야 한다.

## 현재 구현 (baseline)

    query   = 가설들의 **타입**에 나오는 식별자 + goal 결론의 식별자   (이름은 제외)
    premise = lemma **전체 텍스트**의 식별자
    score   = tf_idf(query, premise_docs)

여기서 의심스러운 지점 셋:

  ① 가설과 goal 을 그냥 이어붙인다 → 가설이 길면 goal 신호가 묻힌다
  ② premise 를 전체 텍스트로 본다 → 적용 여부를 좌우하는 건 **결론**인데 가설부가 노이즈
  ③ 구조를 안 본다 → `Z.succ 0 <= a` 와 `n < m -> Z.succ n <= m` 가 단어로만 비교된다

## 지표

  R@k  : gold 가 상위 k 에 드는 비율 (k=10/20/50) — **R@50 이 주지표**(프롬프트 정원 ~21)
  MRR  : 1/순위 평균 (0 = 못 찾음)

사용: python3 scripts/research_retrieval.py [n] [방식,방식,…]
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
from proof_retrieval.bm25 import bm25  # noqa: E402
from premise_selection.premise_filter import PremiseFilter, PremiseFilterConf  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
from tactic_gen.gold_lemma import _TACKW, _LOCALPAT, _IDRE  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
WANT = (sys.argv[2].split(",") if len(sys.argv) > 2 else None)
CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")

cc = yaml.safe_load(open(CONF))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, Split.TRAIN, N)
sdb = SentenceDB.load(conf.sentence_db_loc)

pf_conf = PremiseFilterConf.from_yaml(tdc["formatter_conf"]["premise"]["premise_filter"])
pfilter = PremiseFilter(pf_conf.coq_excludes, pf_conf.non_coq_excludes,
                        pf_conf.general_excludes)

_NAME = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                   r"Instance|Axiom|Proposition|Example|Let|Program\s+\w+)\s+"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")


def declname(t):
    m = _NAME.match(t or "")
    return m.group(1).split(".")[-1] if m else None


def gold_names(tac, loc):
    out = []
    for piece in re.split(r"\s*;\s*", (tac or "").strip()):
        toks = piece.split()
        if not toks:
            continue
        h = toks[0].lower().strip(";.")
        if h not in ("rewrite", "apply", "eapply", "erewrite"):
            continue
        rest = re.split(r"\bin\b", piece[len(h):])[0]
        for x in _IDRE.findall(rest):
            b = x.split(".")[-1]
            if b in _TACKW or b.isdigit() or _LOCALPAT.match(b) or b in loc:
                continue
            if len(b) < 3 and b.islower():
                continue
            if b not in out:
                out.append(b)
    return out


# ── premise 표현 ──────────────────────────────────────────────────────────
_CONCL_SPLIT = re.compile(r"->")


def prem_ids_full(s):
    """현재 방식: lemma 전체 텍스트의 식별자."""
    return get_ids_from_sentence(s)


def prem_ids_concl(s):
    """**결론만**. 적용 가능 여부를 좌우하는 건 결론이고 가설부는 노이즈라는 가설."""
    from tactic_gen.applicable import decompose
    d = decompose(getattr(s, "text", "") or "")
    if d is None:
        return get_ids_from_sentence(s)
    toks = [t for t in d[2] if re.match(r"^[A-Za-z_]", t)]
    return toks or get_ids_from_sentence(s)


def prem_ids_concl_boost(s):
    """결론을 2배 가중하고 전체도 섞는다 (결손 위험을 줄이면서 결론을 강조)."""
    return prem_ids_concl(s) * 2 + get_ids_from_sentence(s)


# ── 구조 신호: lemma 이름 subword + 연산자 정규화 ──────────────────────────
#   Coq 관례상 lemma 이름이 내용을 서술한다: Zlt_le_succ → {Zlt, le, succ}.
#   goal `Z.succ 0 <= a` 의 식별자는 {Z.succ, a} 이고 연산자는 `<=`(=le) 다.
#   → **이름을 쪼개고 연산자를 함수명으로 바꾸면** succ·le 가 맞아떨어진다.
#     TF-IDF 는 `Zlt_le_succ` 를 한 토큰으로 보므로 이 신호를 통째로 놓친다.
from tactic_gen.applicable import _OP2FN, _SWAP  # noqa: E402

_SUBW = re.compile(r"[._]")


def subwords(name: str) -> list[str]:
    """`Z.mul_comm` → [Z, mul, comm]. 1글자 조각은 노이즈라 버린다."""
    return [w for w in _SUBW.split(name or "") if len(w) >= 2]


def op_names(text: str) -> list[str]:
    """항 문자열에 나오는 notation 의 **함수 이름**. `<=` → le, `+` → add."""
    out = []
    for sym, fn in list(_OP2FN.items()) + list(_SWAP.items()):
        if sym in (text or ""):
            out.append(fn)
    return out


# ── 쿼리 표현 ─────────────────────────────────────────────────────────────
def q_hyp_goal(h, g):
    return h + g                       # 현재 구현


def q_goal(h, g):
    return g                           # 코드에 주석으로 남아 있던 대안


def q_goal_boost(h, g):
    return g * 3 + h                   # goal 을 3배 가중


def q_goal_boost5(h, g):
    return g * 5 + h


QUERIES = {"hyp+goal": q_hyp_goal, "goal만": q_goal,
           "goal×3+hyp": q_goal_boost, "goal×5+hyp": q_goal_boost5}
PREMS = {"전체": prem_ids_full, "결론만": prem_ids_concl, "결론×2+전체": prem_ids_concl_boost}

# 구조 신호를 쓰는 변형은 goal 원문·premise 원문을 봐야 하므로 별도 경로로 둔다.
GOAL_TEXT = {"cur": ""}


def q_struct(h, g):
    """goal 식별자 + 그 subword + 연산자 함수명."""
    out = list(h) + list(g)
    for x in g:
        out += subwords(x)
    out += op_names(GOAL_TEXT["cur"]) * 2          # 연산자는 강한 신호 → 2배
    return out


def q_struct_goalboost(h, g):
    out = list(g) * 3 + list(h)
    for x in g:
        out += subwords(x) * 2
    out += op_names(GOAL_TEXT["cur"]) * 3
    return out


def prem_name_subword(s):
    """전체 식별자 + **lemma 이름의 subword**(2배 가중)."""
    ids = get_ids_from_sentence(s)
    nm = declname(getattr(s, "text", "") or "")
    return list(ids) + (subwords(nm) * 2 if nm else [])


QUERIES["struct"] = q_struct
QUERIES["struct+goal×3"] = q_struct_goalboost
PREMS["이름subword"] = prem_name_subword

# 실험 조합: (이름, 쿼리방식, premise방식, 스코어러)
METHODS = [
    ("baseline (hyp+goal · 전체 · tfidf)", "hyp+goal", "전체", "tfidf"),
    ("goal만 · 전체 · tfidf", "goal만", "전체", "tfidf"),
    ("goal×3+hyp · 전체 · tfidf", "goal×3+hyp", "전체", "tfidf"),
    ("goal×5+hyp · 전체 · tfidf", "goal×5+hyp", "전체", "tfidf"),
    ("hyp+goal · 결론만 · tfidf", "hyp+goal", "결론만", "tfidf"),
    ("hyp+goal · 결론×2+전체 · tfidf", "hyp+goal", "결론×2+전체", "tfidf"),
    ("goal×3+hyp · 결론×2+전체 · tfidf", "goal×3+hyp", "결론×2+전체", "tfidf"),
    ("baseline · bm25", "hyp+goal", "전체", "bm25"),
    ("★ struct · 이름subword · tfidf", "struct", "이름subword", "tfidf"),
    ("★ struct+goal×3 · 이름subword · tfidf", "struct+goal×3", "이름subword", "tfidf"),
    ("★ hyp+goal · 이름subword · tfidf", "hyp+goal", "이름subword", "tfidf"),
    ("★ struct · 전체 · tfidf", "struct", "전체", "tfidf"),
]
if WANT:
    METHODS = [m for m in METHODS if any(w in m[0] for w in WANT)]

KS = (10, 20, 50)
hits = {m[0]: collections.Counter() for m in METHODS}
mrr = {m[0]: 0.0 for m in METHODS}
elapsed = {m[0]: 0.0 for m in METHODS}
n_case = 0
pool_sizes = []

for i in range(N):
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    st = getattr(e, "proof_state", "") or ""
    from tactic_gen.search_query import local_names
    loc = local_names(st)
    golds = gold_names(e.next_steps[0] if getattr(e, "next_steps", None) else "", loc)
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
    # gold 가 풀에 없으면 어떤 스코어링도 못 잡는다 → 비교에서 제외(방법 차이만 보려고)
    names = [declname(getattr(p, "text", "")) for p in pool]
    gidx = [j for j, nm in enumerate(names) if nm in golds]
    if not gidx:
        continue
    n_case += 1
    pool_sizes.append(len(pool))

    h_ids, g_ids = get_ids_from_goal(step.goals[0])
    GOAL_TEXT["cur"] = getattr(step.goals[0], "goal", "") or ""
    doc_cache: dict = {}
    for name, qk, pk, sc in METHODS:
        if pk not in doc_cache:
            doc_cache[pk] = [PREMS[pk](p) for p in pool]
        docs = doc_cache[pk]
        q = QUERIES[qk](h_ids, g_ids)
        t0 = time.time()
        scores = tf_idf(q, docs) if sc == "tfidf" else bm25(q, docs)
        elapsed[name] += time.time() - t0
        order = sorted(range(len(pool)), key=lambda j: -scores[j])
        rank = min((order.index(j) for j in gidx), default=10 ** 9)
        for k in KS:
            hits[name][k] += (rank < k)
        mrr[name] += 1.0 / (rank + 1) if rank < 10 ** 9 else 0.0

print(f"\n■ TRAIN — 비교 가능한 사례 {n_case}건 (gold 가 풀에 있는 것만)")
print(f"   풀 크기 중앙 {sorted(pool_sizes)[len(pool_sizes)//2] if pool_sizes else 0}개\n")


def ci(p, n):
    return 1.96 * math.sqrt(max(p * (1 - p), 1e-12) / max(n, 1)) * 100


print(f"   {'방식':38s} {'R@10':>8s} {'R@20':>8s} {'R@50':>9s} {'MRR':>7s} {'ms/건':>7s}")
base = None
for name, *_ in METHODS:
    r = [hits[name][k] / max(n_case, 1) * 100 for k in KS]
    m = mrr[name] / max(n_case, 1)
    if base is None:
        base = r[2]
    d = r[2] - base
    print(f"   {name:38s} {r[0]:7.1f}% {r[1]:7.1f}% {r[2]:7.1f}%"
          f"{'' if abs(d)<0.05 else f'{d:+5.1f}':>6s} {m:7.3f} {elapsed[name]/max(n_case,1)*1000:7.1f}")
print(f"\n   R@50 의 95% 오차: ±{ci(base/100, n_case):.1f}pp")
