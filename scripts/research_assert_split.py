#!/usr/bin/env python3
"""**assert 로 쪼개면 검색이 쉬워지는가** — 검색 실패를 두 단계로 나누는 아이디어의 검증.

## 아이디어

gold lemma 가 검색 top-K 밖이면, 익명화된 프롬프트에서 모델은 **읽을 수 없는 이름**을
지어내야 한다 — 불가능하다. 대신 이렇게 쪼갠다.

    ① assert (필요한 명제) as H.     ← 이름이 아니라 **명제**를 쓴다(프롬프트에서 읽을 수 있음)
    ② 원래 tactic 은 H 를 쓴다
    ③ 그 다음 H 를 증명한다 — 이때 **goal 이 곧 그 lemma 의 statement** 다

③ 에서는 goal 과 lemma 결론이 (거의) 같으므로 검색이 훨씬 쉬워야 한다.

## 재는 것

gold 가 top-K 밖인 사례만 모아, **그 lemma 의 결론을 goal 로 바꿔** 같은 풀에서 재검색한다.
순위가 얼마나 오르는지가 곧 이 아이디어의 상한이다.

  · 원래 순위 (실제 goal 기준)
  · assert 후 순위 (lemma 결론이 goal 인 상황)

사용: python3 scripts/research_assert_split.py [n] [topk] [train|test|val]
"""
import collections
import copy
import math
import os
import re
import sys

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
from tactic_gen.applicable import decompose  # noqa: E402

_argv = sys.argv
sys.argv = [_argv[0], "1", "train"]
os.environ.setdefault("POOL_CAP", "100000")
sys.path.insert(0, "scripts")
import research_structural as RS  # noqa: E402
sys.argv = _argv

N = int(_argv[1]) if len(_argv) > 1 else 3000
TOPK = int(_argv[2]) if len(_argv) > 2 else 50
SPLIT = (_argv[3] if len(_argv) > 3 else "test").upper()

cc = yaml.safe_load(open(os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), N)
sdb = SentenceDB.load(conf.sentence_db_loc)
pf = PremiseFilterConf.from_yaml(tdc["formatter_conf"]["premise"]["premise_filter"])
pfilter = PremiseFilter(pf.coq_excludes, pf.non_coq_excludes, pf.general_excludes)


def as_goal_text(ptext: str) -> str:
    """premise 를 **goal 처럼** 만든다: forall 을 벗기고 결론만 남긴다.

    `assert` 로 세울 명제는 goal 문맥에 맞게 인스턴스화되지만, 검색 관점에서는 결론의
    **모양**이 같으므로 이 근사로 충분하다.
    """
    d = decompose(ptext)
    if d is None:
        return ptext
    return " ".join(d[2])


def rank_of(goal_text: str, hyp_block: str, pool, gset, use_rrf=True) -> int:
    """주어진 goal 로 검색했을 때 gold 의 순위."""
    state = (hyp_block + "\n\n" + goal_text) if hyp_block else ("\n\n" + goal_text)

    class _G:                       # get_ids_from_goal 이 기대하는 최소 인터페이스
        def __init__(self, g, h):
            self.goal = g
            self.hyps = h

    hyps = [ln for ln in hyp_block.split("\n") if ln.strip()] if hyp_block else []
    h_ids, g_ids = get_ids_from_goal(_G(goal_text, hyps))
    docs = [get_ids_from_sentence(p) for p in pool]
    tf = tf_idf(h_ids + g_ids, docs)
    if not use_rrf:
        order = sorted(range(len(pool)), key=lambda j: -tf[j])
        return min(order.index(j) for j in gset)

    gs = RS.goal_struct(state)
    if gs is None:
        order = sorted(range(len(pool)), key=lambda j: -tf[j])
        return min(order.index(j) for j in gset)
    df: collections.Counter = collections.Counter()
    pss = []
    for p in pool:
        ps = RS.prem_struct(getattr(p, "text", "") or "")
        pss.append(ps)
        if ps is not None:
            for k in ps[5]:
                df[k] += 1
    nd = max(len(pool), 1)
    idf = {k: math.log(nd / v) for k, v in df.items()}
    c2 = [RS.sig_concl_heads(gs, ps, idf) if ps is not None else 0.0 for ps in pss]

    def ranks(v):
        o = sorted(range(len(v)), key=lambda j: -v[j])
        r = [0] * len(v)
        for p_, j in enumerate(o):
            r[j] = p_
        return r

    rt, rc = ranks(tf), ranks(c2)
    sc = [1 / (60 + rt[j]) + 1 / (60 + rc[j]) for j in range(len(pool))]
    order = sorted(range(len(pool)), key=lambda j: -sc[j])
    return min(order.index(j) for j in gset)


KS = (1, 5, 10, 20, 50)
before = collections.Counter()
after = collections.Counter()
n = 0
n_all = 0

for i in range(N):
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    st = getattr(e, "proof_state", "") or ""
    golds = gold_lemmas(e.next_steps[0] if getattr(e, "next_steps", None) else "",
                        local_names(st))
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
    names = [RS.declname(getattr(p, "text", "")) for p in pool]
    gset = {j for j, nm in enumerate(names) if nm in golds}
    if not gset:
        continue
    n_all += 1

    r0 = rank_of(RS.goal_conclusion(st), st.split("\n\n")[0] if "\n\n" in st else "",
                 pool, gset)
    if r0 < TOPK:
        continue                     # 이미 잡히는 건 볼 필요 없다
    n += 1
    gtext = as_goal_text(getattr(pool[min(gset)], "text", "") or "")
    r1 = rank_of(gtext, "", pool, gset)
    for k in KS:
        before[k] += (r0 < k)
        after[k] += (r1 < k)
    if n <= 6:
        print(f"  [{n}] {names[min(gset)]:26s} 순위 {r0} → {r1}", flush=True)
    if n >= 250:
        break

print(f"\n■ {SPLIT} — gold 가 top{TOPK} **밖**인 사례 {n}건 (전체 {n_all}건 중)")
print(f"   {'':10s} " + " ".join(f"{'R@'+str(k):>7s}" for k in KS))
print(f"   {'원래 goal':10s} " + " ".join(f"{before[k]/max(n,1)*100:6.1f}%" for k in KS))
print(f"   {'assert 후':10s} " + " ".join(f"{after[k]/max(n,1)*100:6.1f}%" for k in KS))
print(f"\n   ⇒ 검색 실패 사례의 {after[20]/max(n,1)*100:.1f}% 가 assert 로 쪼개면 "
      f"top20 안에 들어온다")
