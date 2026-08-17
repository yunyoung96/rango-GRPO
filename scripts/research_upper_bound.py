#!/usr/bin/env python3
"""**얼마나 더 올릴 수 있나** — 상한과 실패 원인을 잰다 + 학습된 결합을 시도한다.

## 세 가지를 본다

### ① oracle 상한
지금 쓰는 신호들(A' 매칭크기 · B head · C' 결론head코사인 · D 모양 · E 가설매칭 · tfidf)
중 **어느 하나라도** gold 를 상위 k 에 넣는 비율. 이것이 "현재 신호 집합으로 도달 가능한
천장" 이다. RRF 결과와의 차이가 **결합 방식으로 더 먹을 수 있는 몫**이다.

### ② 실패 원인
어떤 신호로도 못 잡는 gold 는 왜 안 잡히나 — 결론 파싱 실패? head 불일치? 구조가 아예 다름?

### ③ 학습된 선형 결합 (contrastive 의 값싼 버전)
RRF 는 가중치가 고정이다. (goal, gold) 를 positive, 같은 풀의 나머지를 negative 로 두고
**로지스틱 회귀**로 가중치를 배우면 얼마나 나아지나. GPU 없이 즉시 된다.
학습/평가를 나눠 과적합을 피한다.

사용: python3 scripts/research_upper_bound.py [n]
"""
import collections
import copy
import math
import os
import random
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

sys.path.insert(0, "scripts")
import research_structural as RS  # noqa: E402   (신호 함수·구조 파서를 그대로 쓴다)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 2500
CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")
NEG = int(os.environ.get("NEG", "60"))          # 학습용 negative 표본 수/사례

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
rng = random.Random(0)

cases = []          # (feats[j] 리스트, tfidf점수, 순위, gold 인덱스집합, 풀크기)
skipped = collections.Counter()

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
    names = [RS.declname(getattr(p, "text", "")) for p in pool]
    gidx = {j for j, nm in enumerate(names) if nm in golds}
    if not gidx:
        continue
    gs = RS.goal_struct(st)
    if gs is None:
        skipped["goal 파싱 실패"] += 1
        continue

    h_ids, g_ids = get_ids_from_goal(step.goals[0])
    docs = [get_ids_from_sentence(p) for p in pool]
    tf = tf_idf(h_ids + g_ids, docs)
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
    feats = []
    for j, ps in enumerate(pss):
        if ps is None:
            feats.append([0.0] * 6)
            continue
        feats.append([RS.sig_match_size(gs, ps), RS.sig_head(gs, ps),
                      RS.sig_ops(gs, ps), RS.sig_shape(gs, ps),
                      RS.sig_concl_heads(gs, ps, idf), RS.sig_hyp_match(gs, ps)])
    # 이름subword 점수도 후보 신호로 둔다
    ns_docs = [list(d) + [w for w in RS._SUBW.split(nm or "") if len(w) >= 2] * 2
               for d, nm in zip(docs, names)]
    ns = tf_idf(h_ids + g_ids, ns_docs)
    cases.append((feats, tf, ns, gidx, len(pool)))

print(f"■ 사례 {len(cases)}건 수집 (건너뜀: {dict(skipped)})\n")

SIGNAMES = ["A' 매칭크기", "B head일치", "C 연산자", "D 모양", "C' 결론head", "E 가설매칭",
            "tfidf", "이름subword"]
KS = (10, 20, 50)


def ranks_of(sc):
    o = sorted(range(len(sc)), key=lambda j: -sc[j])
    r = [0] * len(sc)
    for pos, j in enumerate(o):
        r[j] = pos
    return r


def best_rank(sc, gidx):
    r = ranks_of(sc)
    return min(r[j] for j in gidx)


# ── ① 개별 신호와 oracle 상한 ─────────────────────────────────────────────
per_sig = {s: collections.Counter() for s in SIGNAMES}
oracle = collections.Counter()
rrf = collections.Counter()
for feats, tf, ns, gidx, npool in cases:
    cols = [[f[c] for f in feats] for c in range(6)] + [tf, ns]
    rs = []
    for si, sc in enumerate(cols):
        br = best_rank(sc, gidx)
        rs.append(br)
        for k in KS:
            per_sig[SIGNAMES[si]][k] += (br < k)
    for k in KS:
        oracle[k] += any(r < k for r in rs)
    # 참고: 현재 최선안(RRF 3-way)
    r_tf, r_c2, r_ns = ranks_of(tf), ranks_of(cols[4]), ranks_of(ns)
    fused = [1 / (60 + r_tf[j]) + 1 / (60 + r_c2[j]) + 1 / (60 + r_ns[j])
             for j in range(npool)]
    br = best_rank(fused, gidx)
    for k in KS:
        rrf[k] += (br < k)

n = len(cases)
print(f"   {'신호':16s} {'R@10':>8s} {'R@20':>8s} {'R@50':>8s}")
for s in SIGNAMES:
    print(f"   {s:16s} " + " ".join(f"{per_sig[s][k]/n*100:7.1f}%" for k in KS))
print(f"   {'─'*16} " + "─" * 26)
print(f"   {'RRF 3-way (현재)':16s} " + " ".join(f"{rrf[k]/n*100:7.1f}%" for k in KS))
print(f"   {'★ oracle 상한':16s} " + " ".join(f"{oracle[k]/n*100:7.1f}%" for k in KS))
print(f"\n   ⇒ 결합을 완벽히 하면 R@50 {rrf[50]/n*100:.1f}% → {oracle[50]/n*100:.1f}% "
      f"(여지 {(oracle[50]-rrf[50])/n*100:+.1f}pp)")

# ── ② 어떤 신호로도 못 잡는 경우 ──────────────────────────────────────────
lost = 0
why = collections.Counter()
for feats, tf, ns, gidx, npool in cases:
    cols = [[f[c] for f in feats] for c in range(6)] + [tf, ns]
    if any(best_rank(sc, gidx) < 50 for sc in cols):
        continue
    lost += 1
    g = next(iter(gidx))
    f = feats[g]
    if f[4] == 0.0:
        why["결론 head 겹침 0 (구조가 아예 다름)"] += 1
    elif f[1] == 0.0 and f[0] == 0.0:
        why["head 불일치 + 단일화 실패"] += 1
    else:
        why["신호는 있으나 경쟁자에 밀림"] += 1
print(f"\n   어떤 신호로도 top50 에 못 넣은 경우: {lost}/{n} = {lost/n*100:.1f}%")
for k, v in why.most_common():
    print(f"     {k:34s} {v:4d}")

# ── ③ 학습된 선형 결합 ────────────────────────────────────────────────────
split = int(n * 0.6)
train, test = cases[:split], cases[split:]


def featvec(feats, tf, ns, r_tf, r_c2, r_ns, j):
    f = feats[j]
    return f + [tf[j] * 10, ns[j] * 10,
                1 / (60 + r_tf[j]) * 100, 1 / (60 + r_c2[j]) * 100,
                1 / (60 + r_ns[j]) * 100]


D = 11
w = [0.0] * D
b = 0.0
lr = 0.3
for epoch in range(12):
    rng.shuffle(train)
    for feats, tf, ns, gidx, npool in train:
        r_tf = ranks_of(tf)
        r_c2 = ranks_of([f[4] for f in feats])
        r_ns = ranks_of(ns)
        pos = list(gidx)
        negs = [j for j in rng.sample(range(npool), min(NEG, npool)) if j not in gidx]
        for j in pos + negs:
            x = featvec(feats, tf, ns, r_tf, r_c2, r_ns, j)
            z = sum(wi * xi for wi, xi in zip(w, x)) + b
            p = 1 / (1 + math.exp(-max(-30, min(30, z))))
            y = 1.0 if j in gidx else 0.0
            g = (p - y) * (8.0 if y else 1.0)          # positive 를 8배 가중(1:60 불균형)
            for d in range(D):
                w[d] -= lr * g * x[d] / len(pos + negs)
            b -= lr * g / len(pos + negs)

learned = collections.Counter()
rrf_test = collections.Counter()
for feats, tf, ns, gidx, npool in test:
    r_tf = ranks_of(tf)
    r_c2 = ranks_of([f[4] for f in feats])
    r_ns = ranks_of(ns)
    sc = [sum(wi * xi for wi, xi in
              zip(w, featvec(feats, tf, ns, r_tf, r_c2, r_ns, j))) for j in range(npool)]
    br = best_rank(sc, gidx)
    fused = [1 / (60 + r_tf[j]) + 1 / (60 + r_c2[j]) + 1 / (60 + r_ns[j])
             for j in range(npool)]
    br2 = best_rank(fused, gidx)
    for k in KS:
        learned[k] += (br < k)
        rrf_test[k] += (br2 < k)

m = max(len(test), 1)
print(f"\n■ 학습된 선형 결합 (train {len(train)} / test {len(test)})\n")
print(f"   {'방식':16s} {'R@10':>8s} {'R@20':>8s} {'R@50':>8s}")
print(f"   {'RRF 3-way':16s} " + " ".join(f"{rrf_test[k]/m*100:7.1f}%" for k in KS))
print(f"   {'학습된 결합':16s} " + " ".join(f"{learned[k]/m*100:7.1f}%" for k in KS))
print(f"\n   학습된 가중치:")
FN = SIGNAMES[:6] + ["tfidf점수", "이름sub점수", "RRF_tfidf", "RRF_C'", "RRF_이름sub"]
for nm, wi in sorted(zip(FN, w), key=lambda x: -abs(x[1])):
    print(f"     {nm:14s} {wi:+8.3f}")
