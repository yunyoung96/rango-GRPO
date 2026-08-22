#!/usr/bin/env python3
"""★ 큰 프로젝트(CompCert)에서 검색 비용이 **어디에** 쓰이는지 나눠 잰다.

## 왜

`eqx` 재랭킹만 재면 1.87 ms 다(구조 랭커 중 가장 빠르다). 그런데 그 값은
**top-`stage1` 후보에만** 건 비용이라 풀 크기와 무관하다. 실제 추론 한 스텝의 비용은

    ① 풀 조립      out-of-file + in-file premise 를 모으고 거른다
    ② premise 토큰화  `get_ids_from_sentence` — 풀 **전량**
    ③ tfidf        `tf_idf(query, docs)` — 풀 **전량** (O(N))
    ④ 재랭킹       `structural_scores(..., stage1=5000)` — 상한이 걸린다 (O(min(N,5000)))

이고, ②③ 은 풀에 비례하는데 ④ 는 안 그렇다. **풀이 커질수록 tfidf 쪽이 지배한다.**
CompCert 는 rango 데이터셋에서 가장 큰 축(214 파일)이라 여기서 재는 것이 맞다.

## 무엇을 보여 주나

프로젝트별로 풀 크기와 ①②③④ 를 나눠 찍는다. "eqx 가 비싸서 추론이 느려진다" 가
맞는지, 아니면 "tfidf 가 이미 지배적이라 eqx 를 빼도 별 차이 없다" 인지 가른다.

사용: PYTHONPATH=src python3 scripts/bench_compcert_retrieval.py [스텝수] [프로젝트키워드…]
"""
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
logging.disable(logging.CRITICAL)
from _env_from_v9 import apply_v9_env  # noqa: E402
apply_v9_env(verbose=True)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import yaml  # noqa: E402
from data_management.dataset_file import DatasetFile, get_ids_from_goal, get_ids_from_sentence  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402
from proof_retrieval.tfidf import tf_idf  # noqa: E402
from premise_selection.premise_filter import PremiseFilter, PROJ_THM_FILTER_CONF  # noqa: E402
from tactic_gen.tier_rank import structural_scores, STAGE1  # noqa: E402

N_STEP = int(sys.argv[1]) if len(sys.argv) > 1 else 30
KEYS = [k.lower() for k in sys.argv[2:]] or ["compcert"]

CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v9_conf.yaml")
cc = yaml.safe_load(open(CONF))
td = cc["tactic_data"]
DATA = Path(td["data_loc"]) / "data_points"
sdb = SentenceDB.load(Path(td["sentence_db_loc"]))
pf = PremiseFilter.from_conf(PROJ_THM_FILTER_CONF)
STG = int(os.environ.get("RETRIEVAL_STAGE1", str(STAGE1)))

allf = sorted(p.name for p in DATA.iterdir())
print(f"■ 검색 비용 분해   data_points {len(allf):,} 파일 · stage1={STG:,}\n", flush=True)


def bench(files, tag, per_file=3):
    """★ 파일 **전반에 퍼뜨려** 뽑는다.

    알파벳 순으로 앞 파일만 훑으면 CompCert 의 경우 MenhirLib(의존성이 적다)만 보게 되어
    풀 크기가 1 로 나온다 — 실제 CompCert 파일의 필터 후 풀은 2,600~2,800 이다.
    파일당 몇 스텝만 가져와 파일 다양성을 확보한다.
    """
    import random as _r
    rows = []
    done = 0
    fl = list(files)
    _r.Random(7).shuffle(fl)
    for fn in fl:
        if done >= N_STEP:
            break
        try:
            dp = DatasetFile.load(DATA / fn, sdb)
        except Exception:
            continue
        taken = 0
        for pi, proof in enumerate(dp.proofs):
            if done >= N_STEP or taken >= per_file:
                break
            for si, step in enumerate(proof.steps):
                if done >= N_STEP or taken >= per_file or not step.goals:
                    continue
                taken += 1
                goal = step.goals[0]
                t0 = time.perf_counter()
                fr = pf.get_pos_and_avail_premises(step, proof, dp)
                prem = fr.avail_premises
                t1 = time.perf_counter()                      # ① 풀 조립
                docs = [get_ids_from_sentence(p) for p in prem]
                t2 = time.perf_counter()                      # ② 토큰화
                qh, qg = get_ids_from_goal(goal)
                q = qh + qg
                base = tf_idf(q, docs)
                t3 = time.perf_counter()                      # ③ tfidf
                texts = [getattr(p, "text", "") or "" for p in prem]
                try:
                    structural_scores(goal.goal, goal.hyps, texts, base,
                                      query_ids=q, docs=docs, stage1=STG,
                                      use_eq=False, use_cov=False, use_def=False,
                                      use_eqx=True)
                except Exception:
                    pass
                t4 = time.perf_counter()                      # ④ eqx 재랭킹
                rows.append((len(prem), t1 - t0, t2 - t1, t3 - t2, t4 - t3))
                done += 1
    if not rows:
        print(f"   {tag}: 표본 없음")
        return None
    n = len(rows)
    pool = sorted(r[0] for r in rows)
    tot = [sum(r[1:]) for r in rows]
    avg = [sum(r[k] for r in rows) / n * 1000 for k in range(1, 5)]
    T = sum(avg)
    print(f"   ── {tag}  (스텝 {n})")
    print(f"      풀 크기   중앙 {pool[n//2]:,} · 최소 {pool[0]:,} · 최대 {pool[-1]:,}")
    names = ["① 풀 조립", "② premise 토큰화", "③ tfidf", "④ eqx 재랭킹"]
    for nm, v in zip(names, avg):
        print(f"      {nm:20s} {v:8.2f} ms   {v/max(T,1e-9)*100:5.1f}%")
    print(f"      {'합계':20s} {T:8.2f} ms   (중앙 {sorted(tot)[n//2]*1000:.1f} ms)")
    return dict(tag=tag, n=n, pool_med=pool[n // 2], avg=avg, total=T)


def bench_warm(files, tag, n_file=3, n_step=25):
    """★ **캐시가 더워진 뒤**의 비용 — 추론의 실제 조건.

    증명 탐색은 한 파일에서 수백 노드를 돈다. `prem_stmt`/`prem_struct` 는
    lru_cache(300k) 라 첫 스텝에서만 파싱하고 이후에는 조회다. 그래서 콜드 1회 측정은
    추론 비용을 **과대평가**한다. 같은 파일의 스텝들을 두 번 돌려 2회차를 잰다.
    """
    import random as _r
    fl = list(files)
    _r.Random(7).shuffle(fl)
    print(f"   ── {tag} (캐시 워밍 후)", flush=True)
    cold_t = warm_t = 0.0
    cold_e = warm_e = 0.0
    cnt = 0
    for fn in fl[:n_file]:
        try:
            dp = DatasetFile.load(DATA / fn, sdb)
        except Exception:
            continue
        steps = []
        for proof in dp.proofs:
            for step in proof.steps:
                if step.goals and len(steps) < n_step:
                    steps.append((step, proof))
        if not steps:
            continue
        for rnd in (0, 1):
            for step, proof in steps:
                goal = step.goals[0]
                t0 = time.perf_counter()
                fr = pf.get_pos_and_avail_premises(step, proof, dp)
                prem = fr.avail_premises
                docs = [get_ids_from_sentence(p) for p in prem]
                qh, qg = get_ids_from_goal(goal)
                q = qh + qg
                base = tf_idf(q, docs)
                t3 = time.perf_counter()
                texts = [getattr(p, "text", "") or "" for p in prem]
                try:
                    structural_scores(goal.goal, goal.hyps, texts, base,
                                      query_ids=q, docs=docs, stage1=STG,
                                      use_eq=False, use_cov=False, use_def=False,
                                      use_eqx=True)
                except Exception:
                    pass
                t4 = time.perf_counter()
                if rnd == 0:
                    cold_t += t4 - t0; cold_e += t4 - t3; cnt += 1
                else:
                    warm_t += t4 - t0; warm_e += t4 - t3
    if not cnt:
        print("      표본 없음"); return
    print(f"      스텝 {cnt} × 2회")
    print(f"      1회차  전체 {cold_t/cnt*1000:6.2f} ms · eqx {cold_e/cnt*1000:6.2f} ms")
    print(f"      2회차  전체 {warm_t/cnt*1000:6.2f} ms · eqx {warm_e/cnt*1000:6.2f} ms"
          f"   ← 추론의 실제 조건")
    print(f"      eqx 비중  1회차 {cold_e/max(cold_t,1e-9)*100:.1f}%  →  "
          f"2회차 {warm_e/max(warm_t,1e-9)*100:.1f}%", flush=True)


res = []
for k in KEYS:
    fs = [f for f in allf if k in f.lower()]
    print(f"   [{k}] 파일 {len(fs)}개", flush=True)
    r = bench(fs, k)
    if r:
        res.append(r)
    print(flush=True)

# 대조군 — 전체에서 무작위
import random  # noqa: E402
random.seed(1)
sample = random.sample(allf, min(400, len(allf)))
r = bench(sample, "전체 무작위(대조)")
if r:
    res.append(r)

print()
print("■ 캐시 워밍 후 (추론 조건)\n")
for k in KEYS:
    fs = [f for f in allf if k in f.lower()]
    bench_warm(fs, k)

print()
print("■ 요약")
print(f"   {'프로젝트':22s} {'풀(중앙)':>10} {'③ tfidf':>10} {'④ eqx':>10} {'합계':>10}  eqx 비중")
for r in res:
    print(f"   {r['tag']:22s} {r['pool_med']:10,} {r['avg'][2]:9.2f}ms {r['avg'][3]:9.2f}ms "
          f"{r['total']:9.2f}ms {r['avg'][3]/max(r['total'],1e-9)*100:7.1f}%")
print()
print("   ※ ④ 는 stage1 상한이 걸려 풀이 커져도 안 는다. ②③ 은 풀에 비례한다.")
print("     → 풀이 클수록 eqx 비중은 **줄어든다**. eqx 를 빼도 그만큼밖에 못 줄인다.")
