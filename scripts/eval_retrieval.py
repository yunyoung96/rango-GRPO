#!/usr/bin/env python3
"""★ 계층 랭커 성능 검사 — 현재 rango TF-IDF 대비 얼마나 나아지나.

## 재는 것

gold lemma 를 쓰는 스텝만 모아, 같은 후보 풀에서 두 랭킹을 비교한다.

  · **R@k**    gold 중 **하나라도** top-k 안 (검색 관점의 통상 지표)
  · **ALL@k**  그 tactic 이 필요한 gold 를 **전부** top-k 안 (프롬프트가 실제로 쓸모 있으려면
               전부 있어야 한다 — §14 의 "커버율" 이 이것)

랭커
  · tfidf  현재 rango (`SparseClient.get_premise_scores`) 와 **동일한 계산**
  · 계층   tfidf 순위 + 결론구조 C' 순위의 RRF 에, 적용가능성을 계층으로 가산

비용도 잰다 — 구조 판정은 비싸므로 tfidf 상위 `stage1` 개에만 건다.

사용: python3 scripts/eval_retrieval.py [스텝수] [train|val|test] [stage1]
"""
import collections
import copy
import os
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
from tactic_gen.tier_rank import TierRanker, declname  # noqa: E402
from tactic_gen import gbdt_rank  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "test").upper()
STAGE1 = int(sys.argv[3]) if len(sys.argv) > 3 else 400
KS = (1, 5, 10, 20, 50)

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


# 비교할 랭킹 변형
METHODS = ("tfidf", "RRF", "RRF+A.005", "GBDT")
R = {m: collections.Counter() for m in METHODS}
A = {m: collections.Counter() for m in METHODS}
n = 0
n_multi = 0
t_tf = t_ti = t_gb = 0.0
pool_sizes = []
diag = collections.Counter()
sel = []            # 후보 중 적용가능 판정 비율 (선택성)
t0 = time.time()

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
        step = proof.steps[sid.step_idx]
    except Exception:
        continue
    if not step.goals:
        continue
    pool = [p for p in dp.get_premises_before(proof) if pfilter.filter_premise(p)]
    if not pool:
        continue
    texts = [getattr(p, "text", "") or "" for p in pool]
    names = [declname(t) for t in texts]
    gset = {j for j, nm in enumerate(names) if nm and nm in golds}
    # gold 이름이 풀에 몇 종류나 실제로 있는지 (없는 것은 애초에 못 잡는다)
    found = {names[j] for j in gset}
    if not gset:
        continue
    n += 1
    n_multi += (len(found) >= 2)
    pool_sizes.append(len(pool))

    # ── ① tfidf (현재 rango 와 동일) ──────────────────────────────────
    ta = time.time()
    docs = [get_ids_from_sentence(p) for p in pool]
    h_ids, g_ids = get_ids_from_goal(step.goals[0])
    tf = tf_idf(h_ids + g_ids, docs)
    t_tf += time.time() - ta

    # ── ② 구조 신호 ───────────────────────────────────────────────────
    ta = time.time()
    tr = TierRanker(texts, stage1=STAGE1)
    base, c2r, ap, ms, au, cand = tr.signals(st, tf)
    t_ti += time.time() - ta

    # ── 진단 ──────────────────────────────────────────────────────────
    rt = {j: r for r, j in enumerate(sorted(range(len(tf)), key=lambda j: -tf[j]))}
    cs = set(cand)
    diag["gold 가 tfidf 상위 stage1 안"] += all(j in cs for j in gset)
    diag["gold 하나라도 stage1 안"] += any(j in cs for j in gset)
    if cand:
        sel.append(sum(1 for j in cand if ap[j] > 0) / len(cand))
    gin = [j for j in gset if j in cs]
    if gin:
        diag["stage1 안 gold 중 적용가능 판정됨"] += any(ap[j] > 0 for j in gin)
        diag["stage1 안 gold 있음"] += 1

    nn = len(tf)
    rrf = [base[j] + c2r[j] for j in range(nn)]
    # ★ RRF 한 항의 최대값은 1/60 ≈ 0.0167 이다. 가산 크기를 그 언저리로 두면
    #   "밀어 올리는 힌트" 가 되고, 1.0 처럼 크면 "계층" 이 되어 판정 못 받은 gold 를
    #   통째로 밀어낸다(실측: gold recall 46% 라서 손해가 크다).
    # ★ GBDT — 학습된 모델. 특징 12개를 학습 때와 **같은 순서**로 만들어야 한다.
    ta = time.time()
    ns_docs = gbdt_rank.name_docs(docs, names)
    ns = tf_idf(h_ids + g_ids, ns_docs)
    gb = gbdt_rank.score(st, texts, tf, ns,
                         cur_file=getattr(dp.file_context, "file", "") or "",
                         prem_files=[getattr(p_, "file_path", "") or "" for p_ in pool],
                         cand=cand)
    t_gb += time.time() - ta

    scores = {
        "tfidf": tf,
        "RRF": rrf,
        "RRF+A.005": [rrf[j] + 0.005 * (1.0 if ap[j] > 0 else 0.0) for j in range(nn)],
        "GBDT": gb,
    }
    for m, sc in scores.items():
        order = sorted(range(len(pool)), key=lambda j: -sc[j])
        pos = {j: r for r, j in enumerate(order)}
        best = min(pos[j] for j in gset)
        # 이름별로 **가장 잘 나온 순위**를 쓴다 (같은 이름이 여러 번 선언될 수 있다)
        per = {}
        for j in gset:
            per[names[j]] = min(per.get(names[j], 10 ** 9), pos[j])
        worst = max(per.values())
        for k in KS:
            R[m][k] += (best < k)
            A[m][k] += (worst < k)
    if n % 100 == 0:
        print(f"   … {n}건 ({time.time()-t0:.0f}s)", flush=True)

print(f"\n■ {SPLIT} — gold lemma 를 쓰는 {n}건 "
      f"(≥2개 필요 {n_multi}건 = {n_multi/max(n,1)*100:.1f}%)")
print(f"   풀 크기 중앙값 {sorted(pool_sizes)[len(pool_sizes)//2] if pool_sizes else 0}"
      f" · stage1={STAGE1}")
print(f"\n   {'':8s} " + " ".join(f"{'R@'+str(k):>7s}" for k in KS)
      + "   |" + " ".join(f"{'ALL@'+str(k):>8s}" for k in KS))
for m in METHODS:
    print(f"   {m:8s} " + " ".join(f"{R[m][k]/max(n,1)*100:6.1f}%" for k in KS)
          + "   |" + " ".join(f"{A[m][k]/max(n,1)*100:7.1f}%" for k in KS))
print()
for m in METHODS[1:]:
    d = {k: (R[m][k] - R['tfidf'][k]) / max(n, 1) * 100 for k in KS}
    da = {k: (A[m][k] - A['tfidf'][k]) / max(n, 1) * 100 for k in KS}
    print(f"   {m+' 차이':11s} " + " ".join(f"{d[k]:+6.1f}p" for k in KS)
          + "   |" + " ".join(f"{da[k]:+7.1f}p" for k in KS))

print(f"\n   ■ 진단 — 계층이 손댈 수 있는 한계")
for k in ("gold 하나라도 stage1 안", "gold 가 tfidf 상위 stage1 안",
          "stage1 안 gold 있음", "stage1 안 gold 중 적용가능 판정됨"):
    print(f"     {k:34s} {diag[k]:5d}  ({diag[k]/max(n,1)*100:5.1f}%)")
if diag["stage1 안 gold 있음"]:
    _r = diag["stage1 안 gold 중 적용가능 판정됨"] / diag["stage1 안 gold 있음"] * 100
    print(f"     → 적용가능 판정의 gold recall           {_r:5.1f}%")
if sel:
    sel.sort()
    print(f"     후보 중 적용가능 비율(선택성) 중앙값     "
          f"{sel[len(sel)//2]*100:5.1f}%  평균 {sum(sel)/len(sel)*100:5.1f}%")
print(f"\n   시간/스텝: tfidf {t_tf/max(n,1)*1000:.1f}ms · "
      f"구조신호 {t_ti/max(n,1)*1000:.1f}ms · GBDT {t_gb/max(n,1)*1000:.1f}ms")
