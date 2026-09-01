#!/usr/bin/env python3
"""★ r18 §7 보고서 — r17 + RRF 동률 평균순위(전 채널) — 최종 MIX17(채널별 RRF, k=20) vs TFIDF. results/r17.md."""
import collections, json, math, sys
import numpy as np
sys.path.insert(0, "scripts")
import logging; logging.disable(logging.CRITICAL)
_A = sys.argv[:]
sys.argv = ["pretty_rank.py", "x", "--", "y", "--", "z"]
import pretty_rank as PR
import applic_rank as AR
sys.argv = _A
from report_r15 import SPLITS, gold_masks, ranks_in, build_tfidf

K = 20
STRUCT = {"ap": "S1", "in": "S1", "rw": "S2", "rwh": "S1"}   # r17b TRAIN 선발
OUT = "all_log/docs/applicability/results/r18.md"
tr_rows, _ = PR.load_merge(SPLITS["TRAIN"])
IDF, MAXI = build_tfidf(tr_rows)
FORM_CH = dict(PR.FORM_CH); FORM_CH["exact"] = "ap"; FORM_CH["eexact"] = "ap"
CH4 = ("ap", "in", "rw", "rwh")


def cpoint(r, c):
    names = sorted(set((r.get("chan") or {}).get(c, [])))
    if not names: return None
    Ms = gold_masks(names, PR.golds_of(r))
    SC = AR.sig_by_chan(r); sig = r.get("sig") or {}
    gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
    cs = SC.get(c, sig)
    raw = PR.GOALS.get((r.get("proj"), r.get("thm"), r.get("thmi"), r.get("k")), "")
    stmts = r.get("stmts") or {}
    gtc = collections.Counter(AR._TOK.findall(raw))
    na = math.sqrt(sum((v * IDF.get(t, MAXI)) ** 2 for t, v in gtc.items()))
    SH = []; OV = []; RG = []; TF = []
    for n in names:
        x = PR.pfeats(n, cs.get(n) or {}, gsz)
        SH.append(x[0]); OV.append(x[1]); RG.append(x[2])
        scc = collections.Counter(AR._TOK.findall(stmts.get(n) or ""))
        num = sum(gtc[t]*scc[t]*IDF.get(t, MAXI)**2 for t in gtc.keys() & scc.keys())
        nb = math.sqrt(sum((v*IDF.get(t, MAXI))**2 for t, v in scc.items()))
        TF.append(num/(na*nb) if na and nb else 0.0)
    A = lambda v: np.array(v, dtype=float)
    return names, A(SH), A(OV), A(RG), A(TF), Ms


def rankdata_avg(v):
    """내림차순 평균순위 — 동률을 자의로 펼치던 argsort 왜곡 제거 (r18 핵심).
    실측(rwh): TRAIN @10 51.5→54.5 · TEST 51.1→53.2 · @20 전 구간 +2."""
    order = np.argsort(-v, kind="mergesort")
    r = np.empty(len(v)); r[order] = np.arange(1, len(v) + 1)
    out = r.copy()
    for val in np.unique(v):
        m = v == val
        if m.sum() > 1: out[m] = r[m].mean()
    return out


def scores(cp, c, mode):
    _, SH, OV, RG, TF, _ = cp
    if mode == "tfidf": return TF
    base = SH + OV + RG if STRUCT[c] == "S1" else SH + RG
    return 1.0/(K+rankdata_avg(base)) + 1.0/(K+rankdata_avg(TF))


#: ★ 그외 = **외부참조를 필요로 하는 것만**. unfold 는 프롬프트의
#   [TYPES]/[DEFINITIONS] 섹션이 정의 본문을 이미 주입하므로(augment.py)
#   retrieval 과제가 아니다 — 보고에서 제외하고 제외 수를 명시한다.
PROMPT_COVERED = {"unfold"}


def eval_split(rows, mode):
    R = collections.defaultdict(lambda: {"n": 0, "rec": 0, "any": [], "all": []})
    for r in rows:
        f = r.get("tac")
        if f in PROMPT_COVERED: continue
        form = ("apply" if f in ("exact", "eexact")
                else f if f in PR.FORM_CH else "그외")
        chans = [FORM_CH[f]] if f in FORM_CH else list(CH4)
        ba = bl = None; rec = False
        for c in chans:
            cp = cpoint(r, c)
            if not cp: continue
            if any(m.any() for m in cp[5]): rec = True
            a, l = ranks_in(cp[0], scores(cp, c, mode), cp[5])
            if a and (ba is None or a < ba): ba = a
            if l and (bl is None or l < bl): bl = l
        d = R[form]; d["n"] += 1; d["rec"] += rec
        if ba: d["any"].append(ba)
        if bl: d["all"].append(bl)
    return R


def md_table(R):
    hdr = ("| 계열 | 지점 | 회수 | @10 Any | @10 All | @20 Any | @20 All "
           "| @50 Any | @50 All |\n|---|---|---|---|---|---|---|---|---|\n")
    rows = []; tot = {"n": 0, "rec": 0, "any": [], "all": []}
    for f in ("apply", "apply-in", "rewrite", "rewrite-in", "그외"):
        d = R[f]; n = d["n"]
        if not n: continue
        for k in ("n", "rec"): tot[k] += d[k]
        tot["any"] += d["any"]; tot["all"] += d["all"]
        at = lambda L, Kk: sum(1 for x in L if x <= Kk) / n * 100
        rows.append(f"| {f} | {n} | {d['rec']/n*100:.1f}% | "
                    f"{at(d['any'],10):.1f}% | {at(d['all'],10):.1f}% | "
                    f"{at(d['any'],20):.1f}% | {at(d['all'],20):.1f}% | "
                    f"{at(d['any'],50):.1f}% | {at(d['all'],50):.1f}% |")
    n = tot["n"]; at = lambda L, Kk: sum(1 for x in L if x <= Kk) / n * 100
    rows.append(f"| **전체** | {n} | {tot['rec']/n*100:.1f}% | "
                f"{at(tot['any'],10):.1f}% | {at(tot['all'],10):.1f}% | "
                f"{at(tot['any'],20):.1f}% | {at(tot['all'],20):.1f}% | "
                f"{at(tot['any'],50):.1f}% | {at(tot['all'],50):.1f}% |")
    return hdr + "\n".join(rows)


out = ["# r18 결과 (§7 형식)\n",
       "> 용어·알고리즘: [versions/r18.md](../versions/r18.md)\n",
       "- 최종: score_c = 1/(20+r_구조c) + 1/(20+r_어휘) · 구조 ap/in/rwh=S1"
       "(share+overlap+rig), rw=S2(share+rig) · 학습 0",
       "- exact·eexact 는 apply 계열로 재분류 (결론 완전일치 = apply 특수형)",
       "- All=다중 gold 전부 / Any=하나라도 · 별칭 46건 해석\n"]
for sp in ("TRAIN", "VAL", "TEST"):
    rows, _ = PR.load_merge(SPLITS[sp])
    nexcl = sum(1 for r in rows if r.get("tac") in PROMPT_COVERED)
    print(f"{sp} {len(rows)}행 (unfold 제외 {nexcl})…", flush=True)
    for mode, lab in (("mix", "MIX17(최종)"), ("tfidf", "TFIDF(rango식)")):
        out.append(f"\n## {sp} · {lab}\n"
                   f"\n(프롬프트-해결형 unfold {nexcl}지점 제외 — "
                   f"그외 = 외부참조 필요분만)\n\n"
                   + md_table(eval_split(rows, mode)))
open(OUT, "w").write("\n".join(out) + "\n")
print("보고서:", OUT); print("R18_REPORT_DONE")
