#!/usr/bin/env python3
"""★ CompCert **여러 파일에 걸쳐** tfidf 대비 랭커 비용이 얼마나 드나.

기존 `bench_compcert_retrieval.py` 의 워밍 측정은 **파일 3개**만 썼다. CompCert 는
파일마다 의존 규모가 극단적으로 다르다(MenhirLib 은 풀이 거의 0, backend 는 4,000+).
그래서 파일을 넓게 잡고 **풀 크기 구간별로** 나눠 잰다.

한 스텝의 검색 비용은 넷이다.
    ① 풀 조립      out-of-file + in-file premise 수집·필터   O(N)
    ② 토큰화       get_ids_from_sentence — 풀 전량           O(N)
    ③ tfidf        tf_idf(query, docs) — 풀 전량             O(N)
    ④ 재랭킹       structural_scores(stage1) — 상한 있음     O(min(N, stage1))

`tfidf` (rango 원본) = ①②③.  `afh70`/`eqx` = ①②③④.
④ 만 랭커에 따라 다르므로, **④ 를 뺀 나머지가 이미 얼마인지**가 판단의 핵심이다.

★ 캐시 워밍: 실제 추론은 같은 파일을 계속 두드리므로 2회차가 실제 조건이다.

사용: PYTHONPATH=src python3 scripts/bench_ranker_scale.py [파일수] [파일당스텝]
"""
import collections
import os
import random
import sys
import time

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
import logging  # noqa: E402
logging.disable(logging.CRITICAL)
from _env_from_v9 import apply_v9_env  # noqa: E402
apply_v9_env(verbose=False)

from pathlib import Path  # noqa: E402
from data_management.dataset_file import (DatasetFile, get_ids_from_goal,  # noqa: E402
                                          get_ids_from_sentence)
from data_management.sentence_db import SentenceDB  # noqa: E402
from premise_selection.premise_filter import PremiseFilter, PROJ_THM_FILTER_CONF  # noqa: E402
from proof_retrieval.tfidf import tf_idf  # noqa: E402
import tactic_gen.tier_rank as TR  # noqa: E402
from tactic_gen.tier_rank import structural_scores, STAGE1  # noqa: E402

N_FILE = int(sys.argv[1]) if len(sys.argv) > 1 else 40
PER_FILE = int(sys.argv[2]) if len(sys.argv) > 2 else 4
DATA = Path("/tmp/coq-dataset/data_points")
sdb = SentenceDB.load(Path("/tmp/coq-dataset/sentences.db"))
pf = PremiseFilter.from_conf(PROJ_THM_FILTER_CONF)
STG = int(os.environ.get("RETRIEVAL_STAGE1", str(STAGE1)))

allf = [f for f in os.listdir(DATA) if "compcert" in f.lower()]
random.Random(11).shuffle(allf)
print(f"■ CompCert 파일 {len(allf)}개 중 {N_FILE}개 · 파일당 {PER_FILE}스텝 · "
      f"stage1={STG:,}\n", flush=True)

# ── 스텝 수집 (풀 조립까지 미리 해두고, 랭커만 갈아 끼워 잰다) ────────────────
steps = []
for fn in allf[:N_FILE]:
    try:
        dp = DatasetFile.load(DATA / fn, sdb)
    except Exception:
        continue
    taken = 0
    for proof in dp.proofs:
        if taken >= PER_FILE:
            break
        for step in proof.steps:
            if taken >= PER_FILE or not step.goals:
                continue
            steps.append((fn, dp, proof, step))
            taken += 1
print(f"   수집 {len(steps)} 스텝", flush=True)


def bucket(n):
    if n < 500:
        return "① <500"
    if n < 1500:
        return "② 500~1.5k"
    if n < 2500:
        return "③ 1.5k~2.5k"
    if n < 3500:
        return "④ 2.5k~3.5k"
    return "⑤ 3.5k+"


def run(tau, warm_round):
    """tau=None 이면 ④ 재랭킹을 아예 안 한다(= rango 원본 tfidf 경로)."""
    if tau is not None:
        TR.EQX_TAU = tau
    acc = collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0, 0])  # t1..t4, n, pool
    for fn, dp, proof, step in steps:
        goal = step.goals[0]
        t0 = time.perf_counter()
        fr = pf.get_pos_and_avail_premises(step, proof, dp)
        prem = fr.avail_premises
        t1 = time.perf_counter()
        docs = [get_ids_from_sentence(p) for p in prem]
        t2 = time.perf_counter()
        qh, qg = get_ids_from_goal(goal)
        q = qh + qg
        base = tf_idf(q, docs)
        t3 = time.perf_counter()
        if tau is not None:
            texts = [getattr(p, "text", "") or "" for p in prem]
            try:
                structural_scores(goal.goal, goal.hyps, texts, base,
                                  query_ids=q, docs=docs, stage1=STG,
                                  use_eq=False, use_cov=False, use_def=False,
                                  use_eqx=True)
            except Exception:
                pass
        t4 = time.perf_counter()
        b = bucket(len(prem))
        a = acc[b]
        a[0] += t1 - t0
        a[1] += t2 - t1
        a[2] += t3 - t2
        a[3] += t4 - t3
        a[4] += 1
        a[5] += len(prem)
    return acc


CONFS = [("tfidf (rango 원본)", None), ("eqx (τ=1.0)", 1.0), ("afh70 (τ=0.7)", 0.7)]
res = {}
for name, tau in CONFS:
    run(tau, 0)                      # 1회차 — 캐시 워밍
    res[name] = run(tau, 1)          # 2회차 — 추론의 실제 조건
    print(f"   [{name}] 완료", flush=True)

BUCKETS = ["① <500", "② 500~1.5k", "③ 1.5k~2.5k", "④ 2.5k~3.5k", "⑤ 3.5k+"]
print(f"\n■ 풀 크기 구간별 · 스텝당 ms (캐시 워밍 후)\n")
print(f"   {'구간':14s} {'스텝':>5s} {'풀중앙':>7s} | "
      + " ".join(f"{n.split()[0]:>10s}" for n, _ in CONFS) + "   ④재랭킹만")
tot = {n: [0.0, 0] for n, _ in CONFS}
for b in BUCKETS:
    if all(b not in res[n] for n, _ in CONFS):
        continue
    line = f"   {b:14s}"
    a0 = res[CONFS[0][0]].get(b)
    if not a0 or a0[4] == 0:
        continue
    line += f" {a0[4]:5d} {a0[5]//max(a0[4],1):7,d} |"
    rr = []
    for n, _ in CONFS:
        a = res[n].get(b)
        if not a or a[4] == 0:
            line += f" {'-':>10s}"
            rr.append(0.0)
            continue
        ms = sum(a[:4]) / a[4] * 1000
        rr.append(ms)
        line += f" {ms:10.1f}"
        tot[n][0] += sum(a[:4]) * 1000
        tot[n][1] += a[4]
    a = res[CONFS[2][0]].get(b)
    line += f"   {a[3]/max(a[4],1)*1000:7.1f}" if a and a[4] else ""
    print(line)
print(f"\n   {'전체 평균':14s} {tot[CONFS[0][0]][1]:5d} {'':7s} |"
      + "".join(f" {tot[n][0]/max(tot[n][1],1):10.1f}" for n, _ in CONFS))
base = tot[CONFS[0][0]][0] / max(tot[CONFS[0][0]][1], 1)
print(f"\n   노드 300ms(Coq) 기준 검색 비중")
for n, _ in CONFS:
    ms = tot[n][0] / max(tot[n][1], 1)
    print(f"      {n:20s} {ms:6.1f} ms  →  {ms/(300+ms)*100:5.1f}%"
          f"   (tfidf 대비 +{ms-base:5.1f} ms)")
