#!/usr/bin/env python3
"""★ 특징 절제 — 어느 특징이 실제로 일하나.

가중치표를 보면 몇 특징은 구간이 1개뿐이라 아무 일도 안 한다
(`nm`·`occ`·`lex`·`nov`). 파라미터가 43개라 리뷰어가 과적합을 지적할 수 있어
**일 안 하는 것을 버려** 서술도 쉽게 만든다.

절제 = 그 특징을 빼고 다시 학습·평가해 @10 이 얼마나 떨어지나 본다.
떨어지지 않으면 그 특징은 없어도 된다.

★ `idf` 는 **겹마다 학습 겹으로만** 계산한다 — 전체로 구우면 누출이다
  (실측: 전체 idf @10 74.5% vs 겹 idf 36.4%).

사용: python3 scripts/ablate.py <풀.jsonl> [split]
"""
import collections, json, math, os, sys, statistics as st
os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq"); sys.path.insert(0, "scripts")
import logging; logging.disable(logging.CRITICAL)
import applic_rank as AR

SRC = sys.argv[1] if len(sys.argv) > 1 else \
    "all_log/r11_poolin_coqealgraphtheoryfourcolorreglang_val.jsonl"
CH4 = ("ap", "in", "rw", "rwh")
FORMS = ("apply", "apply-in", "rewrite", "rewrite-in")
ALL_F = ["lcp", "lgg", "e", "z", "nm", "ing", "hp", "occ", "idf", "ch",
         "lex", "nov", "std", "slen", "nbind", "nsym", "rig"]
assert os.path.exists(SRC), f"풀이 없다: {SRC}"


def chan_of(r):
    d = {}
    for c in AR.ALL_CH:
        for x in (r.get("chan") or {}).get(c, []): d.setdefault(x, c)
    return d


def train(tr, idf, keep):
    pos = collections.Counter(); neg = collections.Counter(); npos = nneg = 0
    for r in tr:
        g = r["gold"]; gb = g.split(".")[-1]
        cand = set()
        for c in CH4: cand |= set((r.get("chan") or {}).get(c, []))
        if not cand: continue
        co = chan_of(r); sig = r.get("sig") or {}
        SC = AR.sig_by_chan(r)                      # ★ 채널별 신호
        gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
        for x in cand:
            fs = AR.feats(x, SC.get(co.get(x, "ap"), sig), idf, gsz, co,
                          r.get("lex"),
                          set(r.get("gnames") or []), keep=keep,
                          stmts=r.get("stmts"))
            if x == g or x.split(".")[-1] == gb:
                npos += 1
                for kv in fs: pos[kv] += 1
            else:
                nneg += 1
                for kv in fs: neg[kv] += 1
    W = {}
    for kv in set(pos) | set(neg):
        p = (pos[kv] + 1.0) / (npos + 2.0); q = (neg[kv] + 1.0) / (nneg + 2.0)
        W[kv] = math.log2(p / q)
    return W, npos, len(W)


def evaluate(rows, keep):
    """그룹 leave-one-out. idf 도 겹마다."""
    grps = sorted({r["_g"] for r in rows}, key=str)
    RK = []; n = 0; nparam = 0
    for gp in grps:
        tr = [r for r in rows if r["_g"] != gp]
        te = [r for r in rows if r["_g"] == gp]
        if not tr or not te: continue
        idf, _, _ = AR.build_idf(tr)
        W, _np, npar = train(tr, idf, keep)
        nparam = max(nparam, npar)
        for r in te:
            if r.get("tac") not in FORMS: continue
            n += 1
            g = r["gold"]; gb = g.split(".")[-1]
            sig = r.get("sig") or {}
            SC = AR.sig_by_chan(r)
            gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
            co = chan_of(r)

            def sc(x, _s=None):
                return sum(W.get(kv, 0.0) for kv in
                           AR.feats(x, _s if _s is not None else sig, idf, gsz,
                                    co, r.get("lex"),
                                    set(r.get("gnames") or []), keep=keep,
                          stmts=r.get("stmts")))
            best = None
            for c in CH4:
                _cs = SC.get(c, sig)                # ★ 이 채널의 신호로 정렬
                v = sorted(set((r.get("chan") or {}).get(c, [])),
                           key=lambda x: (-sc(x, _cs), x))
                p_ = next((i + 1 for i, x in enumerate(v)
                           if x == g or x.split(".")[-1] == gb), None)
                if p_ is not None and (best is None or p_ < best): best = p_
            if best is not None: RK.append(best)
    return n, RK, nparam


if __name__ == "__main__":
    rows = [json.loads(l) for l in open(SRC)]
    rows = [r for r in rows if r.get("gold") and not r.get("local")]
    for r in rows: r["_g"] = r.get("proj") or r.get("idx")
    assert rows, "지점이 없다"
    print(f"■ {SRC}\n   {len(rows)}지점 · 그룹 {len({r['_g'] for r in rows})}", flush=True)

    def show(lab, keep):
        n, RK, npar = evaluate(rows, keep)
        row = (f"   {lab:26s}{npar:5d}{n:6d}"
               + "".join(f"{sum(1 for x in RK if x <= K)/max(n,1)*100:8.1f}%"
                         for K in (5, 10, 20))
               + f"{(st.median(RK) if RK else 0):9,.0f}")
        print(row, flush=True)
        return sum(1 for x in RK if x <= 10) / max(n, 1) * 100

    print(f"\n   {'설정':26s}{'파라':>5s}{'지점':>6s}{'@5':>8s}{'@10':>8s}{'@20':>8s}{'중앙':>9s}")
    # ★ 기준 = idf 뺀 집합. 절제도 **여기서** 하나씩 뺀다 — ALL_F 에서 빼면
    #   idf 가 모든 행에 섞여 들어가 (−8pp) 진짜 기여가 안 보인다. 실측으로 당했다.
    BASE_F = [f for f in ALL_F if f != "idf"]
    base = show("기준 (전체−idf)", set(BASE_F))
    show("+ idf (누출성)", set(ALL_F))
    print()
    drops = []
    for f in BASE_F:
        keep = set(BASE_F) - {f}
        v = show(f"− {f}", keep)
        drops.append((f, v - base))
    print(f"\n■ 빼면 @10 이 얼마나 변하나 (기준 {base:.1f}%)")
    for f, d in sorted(drops, key=lambda x: x[1]):
        mark = "★필수" if d < -2 else ("유용" if d < -0.5 else
               ("무해" if abs(d) <= 0.5 else "★빼면 좋음"))
        print(f"   {f:6s}{d:+7.1f}pp   {mark}")
    print(f"\n■ 조합 — 말뭉치 없는 특징만으로")
    print(f"   {'설정':26s}{'파라':>5s}{'지점':>6s}{'@5':>8s}{'@10':>8s}{'@20':>8s}{'중앙':>9s}")
    CORE = {"lgg", "lcp", "e", "ch", "std"}
    show("① 핵심 5개", CORE)
    show("② 핵심 + slen/nbind/nsym", CORE | {"slen", "nbind", "nsym"})
    show("③ 핵심 + idf", CORE | {"idf"})
    show("④ 전체 − idf", set(ALL_F) - {"idf"})
    show("⑤ lgg 단독", {"lgg"})
    show("⑥ lgg + lcp", {"lgg", "lcp"})
    print("ABLATE_DONE", flush=True)
