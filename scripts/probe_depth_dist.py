#!/usr/bin/env python3
"""★ `ultlex` 가 A 를 무너뜨리는지 **기전으로** 확인한다.

## 위험 가설

사전식 랭킹은 "깊이가 큰 쪽이 무조건 앞" 이다. 그런데 초거리의 깊이 1 은
**"최상위 연산자만 같다"** 이다 — 등식 goal 이면 `_ = _` 인 premise 가 **전부**
깊이 ≥ 1 을 받는다. 후보 5,000개 중 수천 개가 깊이 ≥ 1 이면, tfidf 순위가
그 안에서만 작동하고 **깊이 잡음이 어휘 신호를 덮는다.**

`jac` 이 A 를 −12.8pp 무너뜨린 것과 같은 형태다.

## 무엇을 재나

A 국면(=일반 goal) 표본마다
  · 후보 중 깊이 ≥ k 인 비율 (k = 1,2,3,4,∞)
  · **gold 의 깊이** — gold 가 깊이로 위로 올라오는가, 아니면 잡음에 묻히는가
  · 사전식으로 정렬했을 때 gold 보다 **위에 오는 잡음 개수**

사용: PYTHONPATH=src python3 scripts/probe_depth_dist.py [표본수]
"""
import collections
import logging
import os
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
logging.disable(logging.CRITICAL)
from _env_from_v9 import apply_v9_env  # noqa: E402
apply_v9_env(verbose=True)

import yaml  # noqa: E402
from data_management.dataset_file import DatasetFile  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402
from premise_selection.premise_filter import PremiseFilter, PROJ_THM_FILTER_CONF  # noqa: E402
from tactic_gen.tier_rank import (goal_stmt, prem_stmt, ultra_sim,  # noqa: E402
                                  au_f_alpha, declname)
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 60
cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
td = cc["tactic_data"]
DATA = Path(td["data_loc"]) / "data_points"
sdb = SentenceDB.load(Path(td["sentence_db_loc"]))
pf = PremiseFilter.from_conf(PROJ_THM_FILTER_CONF)


def depth_of(sim):
    """ultra_sim = 1 − 2^(−k) → k 를 되돌린다. sim=1 이면 ∞(완전일치)."""
    if sim >= 1.0 - 1e-12:
        return 99
    if sim <= 0.0:
        return 0
    import math
    return int(round(math.log2(1.0 / (1.0 - sim))))


files = sorted(p.name for p in DATA.iterdir())
random.Random(5).shuffle(files)
hist = collections.Counter()
rows = []
done = 0
for fn in files:
    if done >= N:
        break
    try:
        dp = DatasetFile.load(DATA / fn, sdb)
    except Exception:
        continue
    taken = 0
    for proof in dp.proofs:
        if done >= N or taken >= 2:
            break
        for step in proof.steps:
            if done >= N or taken >= 2 or not step.goals:
                continue
            g = step.goals[0]
            tac = (step.step.text or "").strip()
            golds = gold_lemmas(tac, local_names("\n".join(g.hyps) + "\n\n" + g.goal))
            if not golds:
                continue                      # A 국면 판정: gold lemma 를 쓰는 스텝만
            fr = pf.get_pos_and_avail_premises(step, proof, dp)
            prem = fr.avail_premises
            if len(prem) < 50:
                continue
            gq = goal_stmt("\n\n" + g.goal)
            if gq is None:
                continue
            taken += 1
            done += 1
            sims, texts = [], []
            for p in prem[:5000]:
                t = getattr(p, "text", "") or ""
                texts.append(t)
                sims.append(ultra_sim(prem_stmt(t), gq))
            ds = [depth_of(s) for s in sims]
            for d in ds:
                hist[min(d, 5) if d < 99 else 99] += 1
            # gold 의 깊이와 사전식 순위
            gi = [j for j, t in enumerate(texts)
                  if (declname(t) or "").split(".")[-1] in golds]
            if gi:
                gd = max(ds[j] for j in gi)
                above = sum(1 for j in range(len(ds))
                            if ds[j] > gd)
                rows.append((len(prem), gd, above))
            if done % 20 == 0:
                print(f"   … {done}/{N}", flush=True)

tot = sum(hist.values())
print(f"\n■ 후보의 깊이 분포  (A 국면 질의 {done}건 · 후보 {tot:,}개)\n")
print(f"   {'깊이':>6} {'개수':>10} {'비율':>8}   누적(≥)")
cum = 0
for k in sorted(hist, reverse=True):
    cum += hist[k]
    lbl = "∞(일치)" if k == 99 else (">=5" if k == 5 else str(k))
    print(f"   {lbl:>6} {hist[k]:10,} {hist[k]/max(tot,1)*100:7.2f}%   {cum/max(tot,1)*100:7.2f}%")

if rows:
    print(f"\n■ gold 는 깊이로 올라오는가  (gold 를 찾은 {len(rows)}건)\n")
    gd = collections.Counter(r[1] for r in rows)
    print("   gold 의 깊이 분포:", dict(sorted(gd.items())))
    ab = sorted(r[2] for r in rows)
    n2 = len(ab)
    print(f"\n   사전식 정렬에서 gold **위에** 오는 후보 수")
    print(f"     중앙 {ab[n2//2]:,} · p25 {ab[n2//4]:,} · p75 {ab[3*n2//4]:,} · 최대 {ab[-1]:,}")
    print(f"     0개(=gold 가 최상위 등급) {sum(1 for x in ab if x == 0)}/{n2} "
          f"= {sum(1 for x in ab if x == 0)/n2*100:.1f}%")
    print(f"     50개 초과(=프롬프트에서 밀려남) {sum(1 for x in ab if x > 50)}/{n2} "
          f"= {sum(1 for x in ab if x > 50)/n2*100:.1f}%")
    print("\n   ※ '위에 오는 후보' 가 50 을 넘으면 사전식만으로는 gold 가 top-50 밖이다.")
    print("     그 안에서 RRF 가 다시 정렬하지만, **등급이 RRF 를 지배**하므로 못 끌어올린다.")
