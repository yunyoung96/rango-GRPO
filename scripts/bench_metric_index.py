#!/usr/bin/env python3
"""경로집합 Jaccard 검색의 **시간**을 잰다 — 큰 프로젝트에서 쓸 수 있나.

## 무엇을 재나

    ① 인덱스 구축 시간          한 번만 드는 비용
    ② 질의당 검색 시간          이게 핵심 — 프로젝트가 커지면 후보가 는다
    ③ 정확도(재현율)            근사 인덱스가 정확 검색을 얼마나 재현하나

## 비교 대상

    linear      전 후보와 Jaccard 를 직접 계산 (정확, O(N))
    minhash     MinHash 서명으로 근사 (O(N) 이지만 상수가 훨씬 작다)
    lsh         MinHash + 밴드 LSH (부분선형 — 후보를 먼저 줄인다)
    tfidf       지금 쓰는 1차 필터 (기준선)

## 왜 MinHash 인가

Jaccard 는 **집합 유사도**라 MinHash 가 정확히 그것을 근사한다:

    P[ minhash_h(A) = minhash_h(B) ] = J(A, B)

서명 길이 `k` 개를 비교하면 표준오차가 `1/√k` 다. `k=128` 이면 ±8.8%.
그리고 서명을 밴드로 쪼개 해시하면(LSH) **비슷한 것만 후보로 뽑는다** —
전 후보를 볼 필요가 없어진다.

★ metric 이 아니면 LSH 도 VP-tree 도 정당화되지 않는다. 경로집합 Jaccard 는
  metric 이므로(verify_metric.py M4) 이 도구들을 쓸 수 있다.

사용: PYTHONPATH=src python3 scripts/bench_metric_index.py [후보수] [질의수]
"""
import glob
import json
import logging
import os
import random
import sys
import time

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from tactic_gen.tier_rank import path_set, alpha_stmt  # noqa: E402
from tactic_gen.applicable import decompose  # noqa: E402

NPOOL = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
NQ = int(sys.argv[2]) if len(sys.argv) > 2 else 200
K = int(os.environ.get("MINHASH_K", "128"))       # 서명 길이
BANDS = int(os.environ.get("LSH_BANDS", "16"))    # 밴드 수 (행 = K/BANDS)

# ── 후보 풀 ─────────────────────────────────────────────────────────────
tys = []
for f in sorted(glob.glob("data/cut_chunks_train/c_*.jsonl")):
    for ln in open(f, errors="ignore"):
        try:
            d = json.loads(ln)
        except Exception:
            continue
        if d.get("kind") == "stmt" and d.get("ty"):
            tys.append(d["ty"])
    if len(tys) >= NPOOL * 3:
        break
random.seed(0)
random.shuffle(tys)

t0 = time.time()
pool = []
for ty in tys:
    t = alpha_stmt(decompose(f"Lemma _x : {ty}."))
    if t is None:
        continue
    ps = path_set(t)
    if ps:
        pool.append(ps)
    if len(pool) >= NPOOL:
        break
t_parse = time.time() - t0
print(f"■ 후보 {len(pool):,}개 · 질의 {NQ}개 · MinHash k={K} · LSH 밴드={BANDS}")
print(f"   파싱+경로집합 추출  {t_parse:6.2f}s  ({t_parse/max(len(pool),1)*1000:.2f} ms/개)\n")

queries = [pool[random.randrange(len(pool))] for _ in range(NQ)]


def jac(a, b):
    u = len(a | b)
    return (len(a & b) / u) if u else 0.0


# ── ① 선형 스캔 (정확) ───────────────────────────────────────────────────
t0 = time.time()
exact = []
for q in queries:
    exact.append(sorted(range(len(pool)), key=lambda j: -jac(q, pool[j]))[:10])
t_lin = time.time() - t0
print(f"   ① linear  질의당 {t_lin/NQ*1000:8.2f} ms   (정확, O(N))")

# ── ② MinHash 서명 ──────────────────────────────────────────────────────
MASK = (1 << 61) - 1
seeds = [random.randrange(1, MASK) for _ in range(K)]


def sig(s):
    out = []
    hs = [hash(x) & MASK for x in s]
    for sd in seeds:
        out.append(min(((h * sd) & MASK) for h in hs) if hs else 0)
    return tuple(out)


t0 = time.time()
sigs = [sig(s) for s in pool]
t_sig = time.time() - t0
qsigs = [sig(q) for q in queries]
print(f"   ② minhash 서명 구축  {t_sig:6.2f}s  ({t_sig/len(pool)*1000:.2f} ms/개)")

t0 = time.time()
for qs in qsigs:
    est = [sum(1 for a, b in zip(qs, s) if a == b) for s in sigs]
    sorted(range(len(pool)), key=lambda j: -est[j])[:10]
t_mh = time.time() - t0
print(f"      minhash 검색  질의당 {t_mh/NQ*1000:8.2f} ms   (근사, O(N)·상수 작음)")

# ── ③ LSH (밴드 스윕) ───────────────────────────────────────────────────
#   밴드 b · 행 r = K/b 일 때, 유사도 s 인 쌍이 후보가 될 확률은
#       P(s) = 1 − (1 − s^r)^b
#   b 를 늘리면(= r 이 줄면) 느슨해져 재현율↑·후보↑. 이 곡선을 실측한다.
print()
print("   ③ LSH 밴드 스윕   b = 밴드 수 · r = K/b")
print(f"      {'b':>4}{'r':>4}{'구축(s)':>10}{'질의(ms)':>11}{'후보(중앙)':>12}"
      f"{'top10재현':>11}{'1위일치':>9}{'선형대비':>10}")
for BANDS in (8, 16, 32, 64, 128):
    rows = max(1, K // BANDS)
    t0 = time.time()
    buckets = [{} for _ in range(BANDS)]
    for j, sg in enumerate(sigs):
        for b in range(BANDS):
            buckets[b].setdefault(sg[b * rows:(b + 1) * rows], []).append(j)
    t_idx = time.time() - t0

    t0 = time.time()
    lsh_res, cand_sizes = [], []
    for qi, qs in enumerate(qsigs):
        cand = set()
        for b in range(BANDS):
            cand.update(buckets[b].get(qs[b * rows:(b + 1) * rows], ()))
        cand_sizes.append(len(cand))
        q = queries[qi]
        lsh_res.append(sorted(cand, key=lambda j: -jac(q, pool[j]))[:10])
    t_lsh = time.time() - t0
    r10 = sum(len(set(a) & set(b)) for a, b in zip(exact, lsh_res)) / (NQ * 10)
    r1 = sum(1 for a, b in zip(exact, lsh_res) if b and a[0] == b[0]) / NQ
    print(f"      {BANDS:>4}{rows:>4}{t_idx:>10.2f}{t_lsh/NQ*1000:>11.3f}"
          f"{sorted(cand_sizes)[len(cand_sizes)//2]:>12}"
          f"{r10*100:>10.1f}%{r1*100:>8.1f}%{t_lin/max(t_lsh,1e-9):>9.0f}x")

print(f"\n■ 규모 감각 — 후보 {len(pool):,}개 기준")
print(f"   linear 는 후보 수에 **비례**한다: 5만개면 질의당 "
      f"{t_lin/NQ*1000*50000/len(pool):.1f} ms")
print(f"   LSH 는 후보 수와 거의 무관하다(버킷 크기만 는다)")
