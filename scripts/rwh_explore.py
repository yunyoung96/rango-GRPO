#!/usr/bin/env python3
"""★ rwh 랭커 탐색 — tf-idf 를 이길 후보 6종 (TRAIN CV 선택 · VAL/TEST 1회).

  TFIDF    현행 (idf² 가중 코사인)
  BM25     포화 TF + 길이 정규화 (k1=1.2, b=0.75 고정 — 학습 0)
  SUBTOK   식별자 부분토큰(밑줄 분해: add_comm→add,comm) tf-idf
  HYPQ     질의 = 가설 블록만 (결론 제외) tf-idf
  TFSH     tfidf + ε·share (구조 미세 보정, ε 는 TRAIN 격자)
  RRF      BLEND 순위 ⊕ TFIDF 순위 상호역수융합 1/(60+r) — 학습 0
"""
import collections, json, math, os, sys
import numpy as np
sys.path.insert(0, "scripts")
import logging; logging.disable(logging.CRITICAL)
_A = sys.argv[:]
sys.argv = ["pretty_rank.py", "x", "--", "y", "--", "z"]
import pretty_rank as PR
import applic_rank as AR
sys.argv = _A
from report_r15 import SPLITS, gold_masks, ranks_in, build_tfidf

W = {"beta": 1.002, "lam": 1.026, "mu": -0.998, "rho": 8.021}
tr_rows, _ = PR.load_merge(SPLITS["TRAIN"])
IDF, MAXI = build_tfidf(tr_rows)
_SUB = None


def subtok(ts):
    out = []
    for t in ts:
        out.append(t)
        if "_" in t: out += [p for p in t.split("_") if len(p) > 1]
    return out


def build_sub_idf():
    df = collections.Counter(); N = 0
    for r in tr_rows:
        for s_ in (r.get("stmts") or {}).values():
            if s_:
                N += 1
                for t in set(subtok(AR._TOK.findall(s_))): df[t] += 1
    return {t: math.log((N + 1) / (v + 1)) for t, v in df.items()}, math.log(N + 1)


SIDF, SMAXI = build_sub_idf()
AVL = np.mean([len(AR._TOK.findall(s_)) for r in tr_rows
               for s_ in (r.get("stmts") or {}).values() if s_])


def cpoint(r):
    names = sorted(set((r.get("chan") or {}).get("rwh", [])))
    if not names: return None
    Ms = gold_masks(names, PR.golds_of(r))
    SC = AR.sig_by_chan(r); sig = r.get("sig") or {}
    gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
    cs = SC.get("rwh", sig)
    raw = PR.GOALS.get((r.get("proj"), r.get("thm"), r.get("thmi"), r.get("k")), "")
    hyps_fl, concl = PR.parse_goal(raw)
    stmts = r.get("stmts") or {}
    gtc = collections.Counter(AR._TOK.findall(raw))
    hq = collections.Counter(AR._TOK.findall(" ".join(t for _, t in hyps_fl) or raw))
    gsc = collections.Counter(subtok(AR._TOK.findall(raw)))
    gset = set(gtc); gmass = sum(IDF.get(t, MAXI) for t in gset) or 1.0
    na = math.sqrt(sum((v * IDF.get(t, MAXI)) ** 2 for t, v in gtc.items()))
    nah = math.sqrt(sum((v * IDF.get(t, MAXI)) ** 2 for t, v in hq.items()))
    nas = math.sqrt(sum((v * SIDF.get(t, SMAXI)) ** 2 for t, v in gsc.items()))
    F = {"tfidf": [], "bm25": [], "subtok": [], "hypq": [], "share": [], "blend": []}
    for n in names:
        stx = AR._TOK.findall(stmts.get(n) or "")
        sc = collections.Counter(stx)
        ssc = collections.Counter(subtok(stx))
        x = PR.pfeats(n, cs.get(n) or {}, gsz)
        lx = sum(IDF.get(t, MAXI) for t in set(stx) & gset) / gmass
        F["share"].append(x[0])
        F["blend"].append(x[0] + W["beta"] * x[1] + W["lam"] * x[2]
                          + W["mu"] * x[3] + W["rho"] * lx)
        def cos(q, d, idf, mx, qn):
            num = sum(q[t] * d[t] * idf.get(t, mx) ** 2 for t in q.keys() & d.keys())
            nb = math.sqrt(sum((v * idf.get(t, mx)) ** 2 for t, v in d.items()))
            return num / (qn * nb) if qn and nb else 0.0
        F["tfidf"].append(cos(gtc, sc, IDF, MAXI, na))
        F["hypq"].append(cos(hq, sc, IDF, MAXI, nah))
        F["subtok"].append(cos(gsc, ssc, SIDF, SMAXI, nas))
        dl = len(stx)
        bm = 0.0
        for t in gtc.keys() & sc.keys():
            tf = sc[t]
            bm += IDF.get(t, MAXI) * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * dl / AVL))
        F["bm25"].append(bm)
    return names, {k: np.array(v) for k, v in F.items()}, Ms


def rank_with(cp, mode, eps=0.0):
    names, F, Ms = cp
    if not any(m.any() for m in Ms): return None
    if mode == "tfsh": s = F["tfidf"] + eps * F["share"]
    elif mode == "rrf":
        r1 = np.argsort(np.argsort(-F["blend"])) + 1
        r2 = np.argsort(np.argsort(-F["tfidf"])) + 1
        s = 1.0 / (60 + r1) + 1.0 / (60 + r2)
    else: s = F[mode]
    a, _ = ranks_in(names, s, Ms)
    return a


def at10(cps, mode, eps=0.0, K=10):
    if not cps: return 0.0
    return sum(1 for cp in cps if (r := rank_with(cp, mode, eps)) and r <= K) \
        / len(cps) * 100


pts = [(r.get("thm"), cpoint(r)) for r in tr_rows if r.get("tac") == "rewrite-in"]
pts = [(g, cp) for g, cp in pts if cp]
files = sorted({g for g, _ in pts}); folds = {fl: i % 5 for i, fl in enumerate(files)}
print(f"■ rwh 랭커 탐색 · TRAIN rewrite-in {len(pts)}지점 · 5겹 CV", flush=True)
MODES = ["tfidf", "bm25", "subtok", "hypq", "rrf", "tfsh"]
cv = {}
for m in MODES:
    accs = []
    for fd in range(5):
        te = [cp for g, cp in pts if folds[g] == fd]
        if m == "tfsh":
            tr_i = [cp for g, cp in pts if folds[g] != fd]
            eps = max((0.0, 0.5, 1.0, 2.0, 4.0), key=lambda e: at10(tr_i, "tfsh", e))
            accs.append(at10(te, "tfsh", eps))
        else:
            accs.append(at10(te, m))
    cv[m] = float(np.mean(accs))
    print(f"  {m:7s} CV @10 = {cv[m]:.1f}%", flush=True)
best = max(cv, key=lambda k: cv[k])
# 1pp 규칙 · 학습0 우선순위: tfidf/bm25/subtok/hypq/rrf(0) < tfsh(1)
prio = ["tfidf", "bm25", "subtok", "hypq", "rrf", "tfsh"]
pick = next(m for m in prio if cv[m] >= cv[best] - 1.0)
eps_star = 0.0
if pick == "tfsh":
    eps_star = max((0.0, 0.5, 1.0, 2.0, 4.0),
                   key=lambda e: at10([cp for _, cp in pts], "tfsh", e))
print(f"★ TRAIN 선택: {pick}" + (f" (ε={eps_star})" if pick == "tfsh" else ""), flush=True)

for sp in ("VAL", "TEST"):
    rows, _ = PR.load_merge(SPLITS[sp])
    cps = [cpoint(r) for r in rows if r.get("tac") == "rewrite-in"]
    cps = [cp for cp in cps if cp]
    print(f"\n■ {sp} rewrite-in ({len(cps)}지점) — 전 후보 (동결 선택={pick})")
    for m in MODES:
        e = eps_star if m == "tfsh" else 0.0
        print(f"  {m:7s} @10 {at10(cps, m, e):5.1f}%  @20 {at10(cps, m, e, 20):5.1f}%"
              f"  @50 {at10(cps, m, e, 50):5.1f}%" + ("  ★" if m == pick else ""),
              flush=True)
print("RWHX_DONE")
