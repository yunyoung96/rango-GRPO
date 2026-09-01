#!/usr/bin/env python3
"""★ **어느 질의가 파일을 죽이나** — 질의 유실의 범인을 특정한다.

coq_search_eval 은 지점마다 질의를 발행하고(`emitted`) 실제로 실행된 수(`ran`)를
센다. w7 실측: 발행 중앙 59 · 실행 중앙 32 — **절반이 실행되지 않는다.**
Coq 은 vernacular 오류가 나면 그 파일 처리를 **중단**하므로, `ran` 번째(0-기반)
질의가 곧 **범인**이다. 질의 생성은 결정적이니 다시 만들어 그 자리를 본다.

사용: python3 scripts/killer_query.py
"""
import collections, json, os, re, sys, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split as CSSplit, get_theorem
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc
from premise_selection.coq_query import (ladder, rewrite_targets, local_names,
                                         hyp_queries, symbol_queries,
                                         hyp_rewrite_queries, elab_subterms,
                                         wide_queries, notation_queries)

SRC   = "all_log/coq_search_w7.jsonl"
ELABF = "all_log/elab_goals_batch.jsonl"
LEVELS, RWN, FWDN, WIDEN = 3, 4, 3, 8

sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))
NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")

ELABG = {}
if os.path.exists(ELABF):
    for ln in open(ELABF):
        ln = ln.strip()
        if ln:
            d = json.loads(ln); ELABG[(d["idx"], d["k"])] = d.get("elab") or d.get("goal") or ""

def elab_concl(t):
    m = re.split(r"(?m)^=+\s*$", t or "")
    return (m[-1] if m else t or "").strip()

def build(g, tac, key):
    """coq_search_eval 과 **같은 순서**로 질의를 만든다."""
    loc = local_names(g); qs = []
    if tac.endswith("apply"):
        for p in ladder(g.goal, loc, max_levels=LEVELS): qs.append((f"SearchPattern ({p}).", "①사다리"))
        for p in hyp_queries(g, loc, maxn=FWDN):         qs.append((f"SearchPattern ({p}).", "④가설방향"))
    else:
        for q in symbol_queries(g.goal, loc, maxn=6):    qs.append((q, "③기호결합"))
        eg = ELABG.get(key)
        if eg:
            ec = elab_concl(eg)
            for q in symbol_queries(ec, loc, maxn=5):    qs.append((q, "③기호(elab)"))
            for t in elab_subterms(ec, maxn=6):          qs.append((f"SearchRewrite {t}.", "②부분항(elab)"))
        for p in rewrite_targets(g.goal, loc, maxn=RWN): qs.append((f"SearchRewrite ({p}).", "②부분항"))
        for q in hyp_rewrite_queries(g, loc, maxn=3):    qs.append((q, "⑤가설안"))
        for p in hyp_queries(g, loc, maxn=FWDN):         qs.append((f"SearchPattern ({p}).", "④가설방향"))
    for q in wide_queries(g.goal, loc, g.hyps, maxsym=WIDEN): qs.append((q, "⑥넓게"))
    eg2 = ELABG.get(key)
    if eg2:
        for q in wide_queries(elab_concl(eg2), loc, None, maxsym=WIDEN): qs.append((q, "⑥넓게(elab)"))
    for q in notation_queries(g.goal, loc, maxn=2):      qs.append((q, "⑦notation"))
    return qs

rows = [json.loads(l) for l in open(SRC)]
by_thm = collections.defaultdict(list)
for r in rows: by_thm[r["idx"]].append(r)

FAM = collections.Counter(); EX = collections.defaultdict(list); S = collections.Counter()
for idx, rs in sorted(by_thm.items()):
    hurt = [r for r in rs if r.get("ran", 0) < r.get("emitted", 0)]
    if not hurt: continue
    try:
        d = get_thm_desc(get_theorem(CSSplit.TEST, idx, Path("CoqStoq")),
                         Path("raw-data/coqstoq-test"), sdb)
        if d is None: continue
        proof = d.dp.proofs[d.idx]
    except Exception: continue
    for r in hurt:
        k = r["k"]
        try:
            st = proof.steps[k]; g = st.goals[0]
            tac = HEADT.match(st.step.text).group(1)
            qs = build(g, tac, (idx, k))
        except Exception: S["재생성 실패"] += 1; continue
        n = r["ran"]
        S["대상 지점"] += 1
        if not (0 <= n < len(qs)):
            S["자리 안 맞음"] += 1; continue
        q, fam = qs[n]
        FAM[fam] += 1
        if len(EX[fam]) < 4: EX[fam].append((idx, k, q[:190]))
        S["잃은 질의"] += r["emitted"] - r["ran"]

print(f"■ 질의를 잃은 지점 {S['대상 지점']} · 잃은 질의 {S['잃은 질의']}"
      f" · 자리 안 맞음 {S['자리 안 맞음']}")
print("\n── 범인 질의의 족(族) ──")
tot = max(1, sum(FAM.values()))
for fam, c in FAM.most_common():
    print(f"   {fam:16s} {c:5d}  {c/tot*100:5.1f}%")
print("\n── 보기 ──")
for fam, _ in FAM.most_common():
    print(f"  [{fam}]")
    for idx, k, q in EX[fam]: print(f"     idx {idx:5d} k {k:3d}  {q}")
