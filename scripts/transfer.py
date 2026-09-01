#!/usr/bin/env python3
"""★★ 가중치 전이 — TRAIN 에서 굳힌 21개 파라미터가 VAL/TEST 에서 먹히나.

실사용 조건과 같다: 학습 스플릿(coq-art 등 TRAIN 저장소)에서 나이브
베이즈 가중치를 **한 번** 굳히고, 처음 보는 프로젝트(VAL/TEST)에 그대로
쓴다. in-split leave-one-out 과 나란히 보여 "전이 손실"을 잰다.

특징은 전부 말뭉치-자유(lgg·lcp·rig·std·ing)라 TRAIN 밖 통계가 필요 없다.

사용: python3 scripts/transfer.py [TRAIN풀] [평가풀들…]
"""
import collections, json, math, os, sys, statistics as st
sys.path.insert(0, "scripts")
import logging; logging.disable(logging.CRITICAL)
import applic_rank as AR

TRAIN = sys.argv[1] if len(sys.argv) > 1 else "all_log/r11_pool_train.jsonl"
EVALS = sys.argv[2:] if len(sys.argv) > 2 else [
    "all_log/r11_poolin_coqealgraphtheoryfourcolorreglang_val.jsonl",
    "all_log/r11_poolin_coqealgraphtheoryfourcolorreglang_test.jsonl"]
CH4 = ("ap", "in", "rw", "rwh")
FORMS = ("apply", "apply-in", "rewrite", "rewrite-in")
KEEP = {"lgg", "lcp", "rig", "std"}     # ★ 최종 4특징·14파라 (v5 굵히기)


def load(p):
    rows = [json.loads(l) for l in open(p)]
    return [r for r in rows if r.get("gold") and not r.get("local")]


def chan_of(r):
    d = {}
    for c in AR.ALL_CH:
        for x in (r.get("chan") or {}).get(c, []): d.setdefault(x, c)
    return d


def train_w(tr, keep):
    """닫힌형 MLE — 한 번 훑고 나눗셈. gold/비gold 특징 빈도의 log 승산비."""
    pos = collections.Counter(); neg = collections.Counter(); npos = nneg = 0
    for r in tr:
        g = r["gold"]; gb = g.split(".")[-1]
        co = chan_of(r); SC = AR.sig_by_chan(r)
        sig = r.get("sig") or {}
        gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
        cand = set()
        for c in CH4: cand |= set((r.get("chan") or {}).get(c, []))
        for x in cand:
            fs = AR.feats(x, SC.get(co.get(x, "ap"), sig), {}, gsz, co,
                          keep=keep, stmts=r.get("stmts"))
            if x == g or x.split(".")[-1] == gb:
                npos += 1
                for kv in fs: pos[kv] += 1
            else:
                nneg += 1
                for kv in fs: neg[kv] += 1
    assert npos > 0 and nneg > 0, f"표본 부족 npos={npos} nneg={nneg}"
    W = {}
    for kv in set(pos) | set(neg):
        p = (pos[kv] + 1.0) / (npos + 2.0); q = (neg[kv] + 1.0) / (nneg + 2.0)
        W[kv] = math.log2(p / q)
    return W, npos, nneg


def rank_with(rows, W, keep):
    N = collections.Counter(); RK = collections.defaultdict(list)
    for r in rows:
        f = r.get("tac")
        if f not in FORMS: continue
        N[f] += 1; N["전체"] += 1
        g = r["gold"]; gb = g.split(".")[-1]
        co = chan_of(r); SC = AR.sig_by_chan(r)
        sig = r.get("sig") or {}
        gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
        best = None
        for c in CH4:
            cs = SC.get(c, sig)
            def score(x):
                return sum(W.get(kv, 0.0) for kv in
                           AR.feats(x, cs, {}, gsz, co, keep=keep,
                                    stmts=r.get("stmts")))
            v = sorted(set((r.get("chan") or {}).get(c, [])),
                       key=lambda x: (-score(x), x))
            p_ = next((i + 1 for i, x in enumerate(v)
                       if x == g or x.split(".")[-1] == gb), None)
            if p_ is not None and (best is None or p_ < best): best = p_
        if best is not None:
            RK[f].append(best); RK["전체"].append(best)
    return N, RK


def show(tag, N, RK):
    print(f"\n■ {tag}  (분모=전체지점)")
    print(f"   {'gold 형태':12s}{'지점':>6s}{'@5':>8s}{'@10':>8s}{'@20':>8s}{'중앙':>7s}")
    for f in ("전체",) + FORMS:
        n = N.get(f, 0); rk = RK.get(f, [])
        if not n: continue
        at = lambda K: sum(1 for x in rk if x <= K) / n * 100
        print(f"   {f:12s}{n:6d}{at(5):8.1f}%{at(10):8.1f}%{at(20):8.1f}%"
              f"{(st.median(rk) if rk else 0):7.0f}")


if __name__ == "__main__":
    tr = load(TRAIN)
    assert tr, f"TRAIN 풀이 비었다: {TRAIN}"
    print(f"■ TRAIN {TRAIN} · {len(tr)}지점 · 특징 {sorted(KEEP)}")
    W, npos, nneg = train_w(tr, KEEP)
    print(f"   양성 {npos} · 음성 {nneg} · 파라미터 {len(W)}")
    for kv, w in sorted(W.items(), key=lambda x: -abs(x[1]))[:12]:
        print(f"     w{kv} = {w:+.2f} bit")
    for ev in EVALS:
        if not os.path.exists(ev): print(f"   (없음: {ev})"); continue
        rows = load(ev)
        N, RK = rank_with(rows, W, KEEP)
        show(f"{os.path.basename(ev)} ← TRAIN 고정 가중치", N, RK)
    print("TRANSFER_DONE")
