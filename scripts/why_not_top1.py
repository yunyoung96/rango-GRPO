#!/usr/bin/env python3
"""gold L 의 **결론을 그대로 질의**로 써도 왜 1위가 아닌가 — 실제 사례를 뜯어본다.

직관: L 을 본떠 만든 L' 을 assert 하고 그걸 증명하려 하면, 질의가 곧 L 의 문장이므로
L 이 무조건 1위여야 한다. 그런데 실측 R@1 이 49% 다. 무엇이 L 을 이기는지 본다.

사용: python3 scripts/why_not_top1.py [n] [train|val|test]
"""
import collections
import copy
import math
import os
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
from tactic_gen.tier_rank import declname, prem_struct  # noqa: E402
from tactic_gen.applicable import canon, match, parse  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "test").upper()

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), 40000)
sdb = SentenceDB.load(conf.sentence_db_loc)
pf = PremiseFilterConf.from_yaml(tdc["formatter_conf"]["premise"]["premise_filter"])
pfilter = PremiseFilter(pf.coq_excludes, pf.non_coq_excludes, pf.general_excludes)


class _G:
    def __init__(self, g, h):
        self.goal, self.hyps = g, h


cause = collections.Counter()
RES = {m: collections.Counter() for m in ('tfidf', '구조우선')}
n = 0
shown = 0
r1 = 0

for i in range(40000):
    if n >= N:
        break
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    st = getattr(e, "proof_state", "") or ""
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    golds = gold_lemmas(tac, local_names(st))
    if not golds:
        continue
    sid = ds.shuffled_idx.get_idx(ds.split, i)
    try:
        dp = DatasetFile.load(conf.data_loc / "data_points" / sid.file, sdb)
        proof = dp.proofs[sid.proof_idx]
    except Exception:
        continue
    pool = [p for p in dp.get_premises_before(proof) if pfilter.filter_premise(p)]
    if not pool:
        continue
    texts = [getattr(p, "text", "") or "" for p in pool]
    names = [declname(t) for t in texts]
    gset = {j for j, nm in enumerate(names) if nm and nm in golds}
    if not gset:
        continue
    g0 = min(gset)

    # ★ 질의 = gold L 의 **결론 그대로** (상한 설정)
    d = decompose(texts[g0])
    if d is None:
        cause["gold 파싱 실패 → 질의를 못 만듦"] += 1
        continue
    q = " ".join(d[2])
    n += 1

    docs = [get_ids_from_sentence(p) for p in pool]
    _, q_ids = get_ids_from_goal(_G(q, []))
    tf = tf_idf(q_ids, docs)

    # ── ★ 구조 기반 랭킹 — "어쩔 수 없나" 를 확인한다 ──────────────────
    #   질의가 **lemma 의 문장 그 자체**인 상황이라면, 토큰 가방이 아니라
    #   **항 트리가 같은가** 를 물어야 한다. 그게 이 상황의 올바른 질문이다.
    qt = parse(q)
    qt = canon(qt) if qt is not None else None
    ex = [0.0] * len(pool)     # 결론 트리가 **완전히 같다**
    su = [0.0] * len(pool)     # premise 를 패턴으로 두면 질의에 **맞는다**(단방향)
    if qt is not None:
        for j in range(len(pool)):
            ps = prem_struct(texts[j])
            if ps is None or ps[1] is None:
                continue
            if ps[1] == qt:
                ex[j] = 1.0
            elif match(ps[1], qt, ps[0], {}):
                su[j] = 1.0
    mxtf = max(tf) or 1.0
    st_score = [3.0 * ex[j] + 1.0 * su[j] + tf[j] / mxtf for j in range(len(pool))]

    for nm_, sc_ in (("tfidf", tf), ("구조우선", st_score)):
        o_ = sorted(range(len(pool)), key=lambda j: -sc_[j])
        p_ = {j: r_ for r_, j in enumerate(o_)}
        rr_ = min(p_[j] for j in gset)
        for k_ in (1, 5, 10, 50):
            RES[nm_][k_] += (rr_ < k_)

    order = sorted(range(len(pool)), key=lambda j: -tf[j])
    pos = {j: r for r, j in enumerate(order)}
    r = min(pos[j] for j in gset)
    if r == 0:
        r1 += 1
        continue

    # ── 왜 졌나 ──────────────────────────────────────────────────────
    win = order[0]
    gl, wl = len(docs[g0]), len(docs[win])
    if tf[win] == tf[g0]:
        cause["동점 (tie)"] += 1
    elif wl < gl * 0.7:
        cause["이긴 쪽이 **훨씬 짧다** (길이 정규화)"] += 1
    elif set(docs[win]) >= set(q_ids) and not (set(docs[g0]) >= set(q_ids)):
        cause["질의 토큰을 이긴 쪽이 더 많이 포함"] += 1
    else:
        cause["기타"] += 1

    if shown < 6:
        shown += 1
        print(f"\n[{shown}] gold={names[g0]}  순위 {r}  (풀 {len(pool)})")
        print(f"    질의(=L 의 결론) : {q[:100]}")
        print(f"    질의 토큰        : {q_ids[:14]}")
        print(f"    gold 원문        : {texts[g0][:110]}")
        print(f"    gold 토큰 {len(docs[g0]):3d}개 · tfidf {tf[g0]:.4f}")
        for k in range(min(3, len(order))):
            j = order[k]
            print(f"    {k+1}위 {str(names[j])[:24]:26s} 토큰 {len(docs[j]):3d}개 "
                  f"tfidf {tf[j]:.4f}  {texts[j][:60]}")

print(f"\n■ {SPLIT} — gold 결론을 그대로 질의로 썼을 때 (n={n})")
print(f"   1위로 잡힘 {r1}/{n} = {r1/max(n,1)*100:.1f}%")
print(f"\n   {'랭커':10s} " + " ".join(f"{'R@'+str(k):>7s}" for k in (1, 5, 10, 50)))
for m in ("tfidf", "구조우선"):
    print(f"   {m:10s} " + " ".join(f"{RES[m][k]/max(n,1)*100:6.1f}%" for k in (1, 5, 10, 50)))
print(f"\n   1위가 아닌 이유:")
for k, v in cause.most_common():
    print(f"     [{v:4d}] {k}")
