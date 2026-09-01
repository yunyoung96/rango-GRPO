#!/usr/bin/env python3
"""★ §7 형식 완전 보고서 — results/<버전>.md 로 저장 (requirements §6·§7).

행 = 5계열 (apply/apply-in/rewrite/rewrite-in/그외) · 스플릿 = TRAIN/VAL/TEST
열 = 필터후 회수 + [@10,@20,@50] × [Any(하나라도) · All(모든 lemma)]
랭커 = BLEND(공식 동결식) vs TFIDF(rango 식) 비교.

그외 계열 정의: gold tactic 이 4형태 밖 → 채널 미상 →
  회수 = 4채널 합집합에 gold 존재 · 순위 = 채널별 순위의 최선(정렬은 채널별 유지)
별칭: r11_alias_map.json 으로 옛 stdlib 이름을 정규 basename 에 매핑.
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

VER = sys.argv[1] if len(sys.argv) > 1 else "r15"
OUT = f"all_log/docs/applicability/results/{VER}.md"
ALIAS = {}
if os.path.exists("all_log/r11_alias_map.json"):
    ALIAS = json.load(open("all_log/r11_alias_map.json"))
CH4 = ("ap", "in", "rw", "rwh")
FORM_CH = PR.FORM_CH
SPLITS = {
 "TRAIN": ["all_log/r11_pool_train.jsonl", "all_log/r11_pool_train_onlyin.jsonl"],
 "VAL": ["all_log/r11_poolin_coqealgraphtheoryfourcolorreglang_val.jsonl",
         "all_log/r11_poolonlyin_coqealgraphtheoryfourcolorreglangmathclasses_val.jsonl"],
 "TEST": ["all_log/r11_poolin_coqealgraphtheoryfourcolorreglang_test.jsonl",
          "all_log/r11_poolonlyin_coqealgraphtheoryfourcolorreglangmathclasses_test.jsonl",
          "all_log/r11_poolin_buchberger_test.jsonl"],
}


def basenames(g):
    """gold 하나가 허용하는 basename 집합 (별칭 포함)."""
    out = {g, g.split(".")[-1]}
    a = ALIAS.get(g) or ALIAS.get(g.split(".")[-1])
    if a: out.add(a)
    return out


def match(n, bs):
    return n in bs or n.split(".")[-1] in bs


def gold_masks(names, golds):
    return [np.array([match(n, basenames(g)) for n in names]) for g in golds]


def ranks_in(names, scores, Ms):
    order = sorted(range(len(names)), key=lambda i: (-scores[i], names[i]))
    pos = {j: i + 1 for i, j in enumerate(order)}
    per = [min(pos[j] for j in np.where(m)[0]) for m in Ms if m.any()]
    if not per: return None, None
    return min(per), (max(per) if all(m.any() for m in Ms) else None)


def build_tfidf(tr_rows):
    df = collections.Counter(); N = 0
    for r in tr_rows:
        for s_ in (r.get("stmts") or {}).values():
            if s_:
                N += 1
                for t in set(AR._TOK.findall(s_)): df[t] += 1
    idf = {t: math.log((N + 1) / (v + 1)) for t, v in df.items()}
    return idf, math.log(N + 1)


def eval_split(rows, W, idf, maxi, ranker):
    """계열별 (n, 회수, anyR, allR 리스트)."""
    R = {f: {"n": 0, "rec": 0, "any": [], "all": []} for f in
         ("apply", "apply-in", "rewrite", "rewrite-in", "그외")}
    for r in rows:
        f = r.get("tac")
        form = f if f in FORM_CH else "그외"
        golds = PR.golds_of(r)
        SC = AR.sig_by_chan(r)
        sig = r.get("sig") or {}
        gsz = float((list(sig.values()) or [{}])[0].get("g", 1) or 1)
        gt_txt = PR.GOALS.get((r.get("proj"), r.get("thm"),
                               r.get("thmi"), r.get("k")), "")
        gt = collections.Counter(AR._TOK.findall(gt_txt))
        gset = set(gt)
        gmass = sum(idf.get(t, maxi) for t in gset) or 1.0
        stmts = r.get("stmts") or {}
        chans = [FORM_CH[f]] if form != "그외" else list(CH4)
        best_any = best_all = None; rec = False
        for c in chans:
            names = sorted(set((r.get("chan") or {}).get(c, [])))
            if not names: continue
            Ms = gold_masks(names, golds)
            if any(m.any() for m in Ms): rec = True
            cs = SC.get(c, sig)
            rk_eff = ranker
            if ranker == "piece":
                rk_eff = "rrf" if c == "rwh" else "blend"
            if ranker == "rrf0":
                rk_eff = "rrf0"
            if rk_eff in ("blend",):
                sc = []
                for n in names:
                    x = PR.pfeats(n, cs.get(n) or {}, gsz)
                    stk = set(AR._TOK.findall(stmts.get(n) or ""))
                    lx = sum(idf.get(t, maxi) for t in stk & gset) / gmass
                    sc.append(x[0] + W["beta"] * x[1] + W["lam"] * x[2]
                              + W["mu"] * x[3] + W["rho"] * lx)
            else:
                sc_tf = []
                for n in names:
                    stk = collections.Counter(AR._TOK.findall(stmts.get(n) or ""))
                    num = sum(gt[t] * stk[t] * idf.get(t, maxi) ** 2
                              for t in gt.keys() & stk.keys())
                    na = math.sqrt(sum((v * idf.get(t, maxi)) ** 2 for t, v in gt.items()))
                    nb = math.sqrt(sum((v * idf.get(t, maxi)) ** 2 for t, v in stk.items()))
                    sc_tf.append(num / (na * nb) if na and nb else 0.0)
                if rk_eff in ("rrf", "rrf0"):
                    sc_bl = []
                    for n in names:
                        x = PR.pfeats(n, cs.get(n) or {}, gsz)
                        if rk_eff == "rrf0":
                            sc_bl.append(x[0] + x[1] + x[2])   # 고정식(학습0)
                        else:
                            stk2 = set(AR._TOK.findall(stmts.get(n) or ""))
                            lx = sum(idf.get(t, maxi) for t in stk2 & gset) / gmass
                            sc_bl.append(x[0] + W["beta"] * x[1] + W["lam"] * x[2]
                                         + W["mu"] * x[3] + W["rho"] * lx)
                    r1 = np.argsort(np.argsort(-np.array(sc_bl))) + 1
                    r2 = np.argsort(np.argsort(-np.array(sc_tf))) + 1
                    sc = list(1.0 / (60 + r1) + 1.0 / (60 + r2))
                else:
                    sc = sc_tf
            a_, l_ = ranks_in(names, np.array(sc), Ms)
            if a_ is not None and (best_any is None or a_ < best_any): best_any = a_
            if l_ is not None and (best_all is None or l_ < best_all): best_all = l_
        R[form]["n"] += 1
        R[form]["rec"] += rec
        if best_any: R[form]["any"].append(best_any)
        if best_all: R[form]["all"].append(best_all)
    return R


def md_table(R):
    hdr = ("| 계열 | 지점 | 회수 | @10 Any | @10 All | @20 Any | @20 All "
           "| @50 Any | @50 All |\n|---|---|---|---|---|---|---|---|---|\n")
    rows = []
    tot = {"n": 0, "rec": 0, "any": [], "all": []}
    for f in ("apply", "apply-in", "rewrite", "rewrite-in", "그외"):
        d = R[f]; n = d["n"]
        if not n: continue
        for k in ("n", "rec"): tot[k] += d[k]
        tot["any"] += d["any"]; tot["all"] += d["all"]
        at = lambda L, K: sum(1 for x in L if x <= K) / n * 100
        rows.append(f"| {f} | {n} | {d['rec']/n*100:.1f}% | "
                    f"{at(d['any'],10):.1f}% | {at(d['all'],10):.1f}% | "
                    f"{at(d['any'],20):.1f}% | {at(d['all'],20):.1f}% | "
                    f"{at(d['any'],50):.1f}% | {at(d['all'],50):.1f}% |")
    n = tot["n"]
    at = lambda L, K: sum(1 for x in L if x <= K) / n * 100
    rows.append(f"| **전체** | {n} | {tot['rec']/n*100:.1f}% | "
                f"{at(tot['any'],10):.1f}% | {at(tot['all'],10):.1f}% | "
                f"{at(tot['any'],20):.1f}% | {at(tot['all'],20):.1f}% | "
                f"{at(tot['any'],50):.1f}% | {at(tot['all'],50):.1f}% |")
    return hdr + "\n".join(rows)


if __name__ == "__main__":
    tr, _ = PR.load_merge(SPLITS["TRAIN"])
    idf, maxi = build_tfidf(tr)
    #: 공식 동결 (r15c 별칭 반영 · K=4 첫 선택 — std 가 CV 문턱을 넘었다)
    W = {"beta": 1.002, "lam": 1.026, "mu": -0.998, "rho": 8.021}
    out = [f"# {VER} 결과 (§7 형식)\n",
           f"- 동결식: share + {W['beta']}·overlap + {W['lam']}·rig "
           f"{W['mu']:+}·std + {W['rho']}·nlex (TRAIN 5겹 CV 선택 K=4)",
           f"- 별칭 해석: {len(ALIAS)}건 (옛 stdlib 이름 → 정규 basename)",
           "- 그외 = 4형태 밖 gold: 회수 = 4채널 합집합 · 순위 = 채널별 최선",
           "- All = 다중 gold 전부 / Any = 하나라도\n"]
    for sp in ("TRAIN", "VAL", "TEST"):
        rows, _ = PR.load_merge(SPLITS[sp])
        print(f"{sp} {len(rows)}행 평가…", flush=True)
        # ★ PIECE = 채널별 랭커 종류. 선택은 **TRAIN CV 만**으로:
        #   ap/in/rw → BLEND (구조+어휘 혼합이 우세)
        #   rwh → RRF(BLEND⊕TFIDF 순위 상호역수융합, 1/(60+r)) — 학습 0,
        #        TRAIN CV 52.1 > tfidf 47.5. TEST rwh 42.6→55.3 실측
        # ★ RRF0 = 최종 채택 단일식 (학습 0 · 전 채널 공통):
        #   score = 1/(60+r_구조) + 1/(60+r_어휘), 구조 = share+overlap+rig
        for ranker, lab in (("rrf0", "RRF-0(최종·단일식)"),
                            ("blend", "BLEND(혼합식)"), ("tfidf", "TFIDF(rango식)"),
                            ("piece", "PIECE(참고: 채널별)")):
            R = eval_split(rows, W, idf, maxi, ranker)
            out.append(f"\n## {sp} · {lab}\n\n" + md_table(R))
    open(OUT, "w").write("\n".join(out) + "\n")
    print("보고서:", OUT)
    print("REPORT_DONE")
