#!/usr/bin/env python3
"""★ 채널별 독립 랭커 — "채널마다 잘 되는 랭킹이 따로 있다" 가설의 정면 시험.

채널 c 마다 자기 형태의 TRAIN 지점만으로:
  후보 = K-사다리 {K1(λ), K2(λ,ρ), K3(β,λ,ρ), K4(β,λ,μ,ρ)} + TFIDF(이산)
  5겹(파일 그룹) CV 로 선택 (1pp 규칙: 최고 대비 1pp 이내 최소 파라미터)
동결 후 VAL/TEST 는 1회. 그외 계열은 채널 미상이라 각 채널의 동결 랭커로
채널별 순위를 내고 최선을 취한다.
"""
import collections, json, math, os, sys, statistics as st
import numpy as np
sys.path.insert(0, "scripts")
import logging; logging.disable(logging.CRITICAL)
_A = sys.argv[:]
sys.argv = ["pretty_rank.py", "x", "--", "y", "--", "z"]
import pretty_rank as PR
import applic_rank as AR
sys.argv = _A
from report_r15 import (SPLITS, gold_masks, ranks_in, build_tfidf, basenames)

FORM_CH = PR.FORM_CH
CH_FORM = {v: k for k, v in FORM_CH.items()}
CH4 = ("ap", "in", "rw", "rwh")
LADDER = [("K1", ("lam",)), ("K2", ("lam", "rho")),
          ("K3", ("beta", "lam", "rho")), ("K4", ("beta", "lam", "mu", "rho"))]
DEF = {"beta": 1.0, "lam": 0.2, "mu": 0.0, "rho": 0.0}
GRID = {"beta": (0.0, 0.5, 1.0, 2.0), "lam": (0.05, 0.2, 0.5, 1.0, 2.0),
        "mu": (-1.0, -0.5, 0.0, 0.5), "rho": (0.0, 0.5, 1.0, 2.0, 4.0, 8.0)}

tr_rows, _ = PR.load_merge(SPLITS["TRAIN"])
IDF, MAXI = build_tfidf(tr_rows)


def cpoint(r, c):
    """지점 → (names, X구조행렬, lex벡터, tfidf점수, Ms)."""
    names = sorted(set((r.get("chan") or {}).get(c, [])))
    if not names: return None
    golds = PR.golds_of(r)
    Ms = gold_masks(names, golds)
    SC = AR.sig_by_chan(r); sig = r.get("sig") or {}
    gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
    cs = SC.get(c, sig)
    gt_txt = PR.GOALS.get((r.get("proj"), r.get("thm"), r.get("thmi"), r.get("k")), "")
    gtc = collections.Counter(AR._TOK.findall(gt_txt)); gset = set(gtc)
    gmass = sum(IDF.get(t, MAXI) for t in gset) or 1.0
    stmts = r.get("stmts") or {}
    X = []; LX = []; TF = []
    na = math.sqrt(sum((v * IDF.get(t, MAXI)) ** 2 for t, v in gtc.items()))
    for n in names:
        x = PR.pfeats(n, cs.get(n) or {}, gsz)
        X.append([x[0], x[1], x[2], x[3]])
        stk = set(AR._TOK.findall(stmts.get(n) or ""))
        LX.append(sum(IDF.get(t, MAXI) for t in stk & gset) / gmass)
        sc = collections.Counter(AR._TOK.findall(stmts.get(n) or ""))
        num = sum(gtc[t] * sc[t] * IDF.get(t, MAXI) ** 2 for t in gtc.keys() & sc.keys())
        nb = math.sqrt(sum((v * IDF.get(t, MAXI)) ** 2 for t, v in sc.items()))
        TF.append(num / (na * nb) if na and nb else 0.0)
    return names, np.array(X), np.array(LX), np.array(TF), Ms


def score_of(cp, kind, th):
    names, X, LX, TF, Ms = cp
    if kind == "tfidf": return TF
    d = dict(DEF); d.update(th)
    return (X[:, 0] + d["beta"] * X[:, 1] + d["lam"] * X[:, 2]
            + d["mu"] * X[:, 3] + d["rho"] * LX)


def rank_any(cp, kind, th):
    names, X, LX, TF, Ms = cp
    if not any(m.any() for m in Ms): return None
    s = score_of(cp, kind, th)
    a, _ = ranks_in(names, s, Ms)
    return a


def mrr(cps, kind, th):
    v = [1.0 / r if (r := rank_any(cp, kind, th)) else 0.0 for cp in cps]
    return float(np.mean(v)) if v else 0.0


def fit_params(cps, kp):
    import itertools
    best, bv = None, -1
    for combo in itertools.product(*[GRID[k] for k in kp]):
        th = dict(zip(kp, combo))
        v = mrr(cps, "w", th)
        if v > bv: bv, best = v, th
    return best


def at10(cps, kind, th):
    if not cps: return 0.0
    h = sum(1 for cp in cps if (r := rank_any(cp, kind, th)) and r <= 10)
    return h / len(cps) * 100


print("■ 채널별 독립 K-사다리 (TRAIN 5겹 CV · +TFIDF 이산 후보)", flush=True)
CHOICE = {}
for c in CH4:
    f = CH_FORM[c]
    pts = [(r.get("thm"), cpoint(r, c)) for r in tr_rows if r.get("tac") == f]
    pts = [(g, cp) for g, cp in pts if cp]
    files = sorted({g for g, _ in pts})
    folds = {fl: i % 5 for i, fl in enumerate(files)}
    results = {}
    for lab, kp in LADDER + [("TFIDF", None)]:
        accs = []
        for fd in range(5):
            tr_i = [cp for g, cp in pts if folds[g] != fd]
            te_i = [cp for g, cp in pts if folds[g] == fd]
            if not tr_i or not te_i: continue
            if lab == "TFIDF":
                accs.append(at10(te_i, "tfidf", None))
            else:
                th = fit_params(tr_i, kp)
                accs.append(at10(te_i, "w", th))
        results[lab] = float(np.mean(accs)) if accs else 0.0
    best_lab = max(results, key=lambda k: results[k])
    # 1pp 규칙: 최고 대비 1pp 이내 중 파라미터 최소 (TFIDF=0개 취급)
    order = ["TFIDF", "K1", "K2", "K3", "K4"]
    pick = next(l for l in order if results[l] >= results[best_lab] - 1.0)
    th = None if pick == "TFIDF" else fit_params([cp for _, cp in pts],
                                                 dict(LADDER)[pick])
    CHOICE[c] = (pick, th)
    print(f"  {c:4s}({f}): " + " ".join(f"{l}={results[l]:.1f}" for l in order)
          + f" → 선택 {pick} {th or ''}", flush=True)

# ── 동결 평가: 3스플릿 × 5계열 ──────────────────────────────────────────
for sp in ("TRAIN", "VAL", "TEST"):
    rows, _ = PR.load_merge(SPLITS[sp])
    R = {f: {"n": 0, "rec": 0, "rk": []} for f in
         ("apply", "apply-in", "rewrite", "rewrite-in", "그외")}
    for r in rows:
        f = r.get("tac"); form = f if f in FORM_CH else "그외"
        chans = [FORM_CH[f]] if form != "그외" else list(CH4)
        best = None; rec = False
        for c in chans:
            cp = cpoint(r, c)
            if not cp: continue
            if any(m.any() for m in cp[4]): rec = True
            kind, th = CHOICE[c]
            a = rank_any(cp, "tfidf" if kind == "TFIDF" else "w", th)
            if a and (best is None or a < best): best = a
        R[form]["n"] += 1; R[form]["rec"] += rec
        if best: R[form]["rk"].append(best)
    print(f"\n■ {sp} · PERCHAN(채널별 독립)")
    print(f"   {'계열':12s}{'지점':>5s}{'회수':>8s}{'@10':>8s}{'@20':>8s}{'@50':>8s}")
    tot = {"n": 0, "rec": 0, "rk": []}
    for f in ("apply", "apply-in", "rewrite", "rewrite-in", "그외"):
        d = R[f]; n = d["n"]
        if not n: continue
        tot["n"] += n; tot["rec"] += d["rec"]; tot["rk"] += d["rk"]
        at = lambda K: sum(1 for x in d["rk"] if x <= K) / n * 100
        print(f"   {f:12s}{n:5d}{d['rec']/n*100:7.1f}%{at(10):7.1f}%"
              f"{at(20):7.1f}%{at(50):7.1f}%", flush=True)
    n = tot["n"]; at = lambda K: sum(1 for x in tot["rk"] if x <= K) / n * 100
    print(f"   {'전체':12s}{n:5d}{tot['rec']/n*100:7.1f}%{at(10):7.1f}%"
          f"{at(20):7.1f}%{at(50):7.1f}%")
print("PERCHAN_DONE")
