#!/usr/bin/env python3
"""★★ 전이 종합 — TRAIN 에서 굳힌 가중치(4방식)를 VAL/TEST 에 그대로.

  NB-14       나이브 베이즈 (세기, 닫힌형)
  LOG-14      쌍별 로지스틱 one-hot     — 완전 학습형, 볼록
  LOG-4       쌍별 로지스틱 연속 4특징   — 구간 자체가 없음
  BO-4        GP-EI 로 TRAIN MRR 직접 최대화
  FIX-0       고정식 lgg/g+lcp/g+0.2·rig — 학습 0 하한

사용: python3 scripts/transfer2.py <TRAIN풀> <평가풀>…
"""
import collections, json, math, os, sys, statistics as st
import numpy as np
sys.path.insert(0, "scripts")
import logging; logging.disable(logging.CRITICAL)

TRAIN = sys.argv[1]
EVALS = sys.argv[2:]
assert EVALS, "평가 풀을 하나 이상"
_A = sys.argv[:]
sys.argv = ["trainable_rank.py", TRAIN, "x"]
import trainable_rank as TR
import applic_rank as AR
sys.argv = _A
FORMS = TR.FORMS; CH4 = TR.CH4


def nb14(tr):
    pos = collections.Counter(); neg = collections.Counter(); npos = nneg = 0
    for r in tr:
        g = r["gold"]; gb = g.split(".")[-1]
        SC = AR.sig_by_chan(r); sig = r.get("sig") or {}
        gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
        co = {}
        for c in AR.ALL_CH:
            for x in (r.get("chan") or {}).get(c, []): co.setdefault(x, c)
        cand = set()
        for c in CH4: cand |= set((r.get("chan") or {}).get(c, []))
        for x in cand:
            fs = AR.feats(x, SC.get(co.get(x, "ap"), sig), {}, gsz, co,
                          keep={"lgg", "lcp", "rig", "std"})
            if x == g or x.split(".")[-1] == gb:
                npos += 1
                for kv in fs: pos[kv] += 1
            else:
                nneg += 1
                for kv in fs: neg[kv] += 1
    assert npos and nneg, f"표본 부족 {npos}/{nneg}"
    W = {}
    for kv in set(pos) | set(neg):
        p = (pos[kv] + 1.0) / (npos + 2.0); q = (neg[kv] + 1.0) / (nneg + 2.0)
        W[kv] = math.log2(p / q)
    return W, npos


def nb_rank(pd_rows):
    """NB 가중치는 dict — one-hot 벡터로 변환해 같은 경로로 평가."""
    pass


if __name__ == "__main__":
    tr = TR.load(TRAIN)
    print(f"■ 전이 종합 · TRAIN={TRAIN} ({len(tr)}행)", flush=True)
    tr_pd = [(r, TR.point_data(r)) for r in tr]
    rng = np.random.default_rng(TR.SEED)

    # 가중치 4벌 학습 (TRAIN 만 본다)
    W_nb, npos = nb14(tr)
    wv = np.zeros(len(TR.COLS))
    for kv, w in W_nb.items():
        if kv in TR.COLS: wv[TR.COLS[kv]] = w
    wA = TR.fit_logistic(TR.pairs_of(tr_pd, True, rng))
    wB = TR.fit_logistic(TR.pairs_of(tr_pd, False, rng))
    wC, dev = TR.fit_bo(tr_pd)
    wF = np.array([1.0, 1.0, 0.2, 0.0])
    print(f"   TRAIN 양성 {npos} · BO dev-MRR {dev:.3f}")
    print("   LOG-4  [lgg/g lcp/g rig std] = "
          + " ".join(f"{x:+.3f}" for x in wB))
    print("   BO-4   [lgg/g lcp/g rig std] = "
          + " ".join(f"{x:+.3f}" for x in wC), flush=True)

    for ev in EVALS:
        if not os.path.exists(ev): print(f"   (없음: {ev})"); continue
        rows = TR.load(ev)
        PD = [(r, TR.point_data(r)) for r in rows]
        print(f"\n■ {os.path.basename(ev)} ← TRAIN 고정 가중치")
        print(f"   {'방식':30s}{'지점':>5s}{'@5':>8s}{'@10':>8s}{'@20':>8s}{'중앙':>7s}")
        for tag, w, oh in (("NB-14 (세기)", wv, True),
                           ("LOG-14 (쌍별로지스틱)", wA, True),
                           ("LOG-4 (연속·구간없음)", wB, False),
                           ("BO-4 (GP-EI)", wC, False),
                           ("FIX-0 (고정식)", wF, False)):
            n, rk = TR.metrics(PD, w, oh)
            TR.show(tag, n, rk)
        # 형태별 (최선 방식 = LOG-4 기준)
        NF = collections.Counter(); RF = collections.defaultdict(list)
        for r, pd in PD:
            f = r.get("tac")
            if f not in FORMS: continue
            NF[f] += 1
            b = TR.rank_of(pd, wB, use_oh=False)
            if b is not None: RF[f].append(b)
        for f in FORMS:
            if NF.get(f): TR.show(f"  LOG-4 · {f}", NF[f], RF[f])
    print("TRANSFER2_DONE", flush=True)
