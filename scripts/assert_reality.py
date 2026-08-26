#!/usr/bin/env python3
"""assert 가 **쓸모없는 명제**를 만드는가, **gold lemma 를 베끼는가** — 전체 proof 로 본다.

rand200 로그에서 모델이 세운 assert 를 뽑고,
  · 그 정리의 **gold proof 전체**
  · 모델이 **실제로 만든 proof 전체** (VALID 로 채택된 tactic 누적)
  · gold proof 가 쓰는 lemma 들의 **signature**
  · assert 명제 vs gold lemma signature 겹침
을 나란히 낸다. 생성 없음 · CPU 전용.

사용: AR2_OUT python3 scripts/assert_reality.py <logs 디렉토리> [최대 정리수]
"""
import json, os, re, sqlite3, sys, yaml, logging, collections
os.environ.setdefault("HF_HUB_OFFLINE", "1"); os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split as CSSplit, get_theorem
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc

LOGS = Path(sys.argv[1]); MAXT = int(sys.argv[2]) if len(sys.argv) > 2 else 8
OUT = Path(os.environ.get("AR2_OUT", "all_log/assert_reality.md"))
DATA_LOC = Path("raw-data/coqstoq-test")
SDB = Path("raw-data/coqstoq-test/coqstoq-test-sentences.db")
sdb = SentenceDB.load(SDB)
con = sqlite3.connect(str(SDB)); con.execute("PRAGMA query_only=1")

_c = {}
def sig(name):
    """lemma 이름 → 선언문(signature). 없으면 None."""
    if name in _c: return _c[name]
    parts = name.split("."); bare = parts[-1]; qual = parts[-2] if len(parts) > 1 else None
    pats = [f"{k} {bare}{c}" for k in ("Lemma","Theorem","Definition","Corollary",
                                        "Remark","Proposition","Fixpoint") for c in (":%", " %")]
    def q(extra, args):
        for p in pats:
            r = con.execute("SELECT text FROM sentence WHERE text LIKE ?" + extra + " LIMIT 1",
                            (p,) + args).fetchone()
            if r: return r[0]
    g = None
    if qual: g = q(" AND module LIKE ?", ("%" + qual + "%",))
    if g is None: g = q(" AND file_path LIKE ?", ("%compcert%",))
    if g is None: g = q("", ())
    _c[name] = g; return g

TOK = re.compile(r"[A-Za-z_][\w']*|<->|->|<=|>=|<>|[<>=~+*/-]")
STOP = {"forall", "exists", "fun", "Prop", "Type", "Set"}
toks = lambda s: {t for t in TOK.findall(s or "") if t not in STOP}
NAMED = re.compile(r"\b(?:e?apply|e?rewrite|exact|unfold|specialize|generalize|refine|"
                   r"pose\s+proof|inversion)\s+(?:<-\s*)?\(?\s*([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
CAND = re.compile(r"→ 후보 tactic: (['\"])(.*?)\1\s*$")
RES  = re.compile(r"→ 결과: TacticResult\.(\w+)")
ASS  = re.compile(r"^\s*assert\s*\((.*?)\)\s*as\s+[\w']+", re.S)

def parse_log(p):
    """(채택된 tactic 목록, 모든 assert 후보 목록)"""
    accepted, asserts, pend = [], [], None
    for line in p.read_text(errors="ignore").splitlines():
        m = CAND.search(line)
        if m:
            pend = m.group(2).encode().decode("unicode_escape") if "\\n" in m.group(2) else m.group(2)
            continue
        m = RES.search(line)
        if m and pend is not None:
            if re.match(r"^\s*assert\b", pend):
                asserts.append((pend, m.group(1)))
            if m.group(1) in ("VALID", "COMPLETE"):
                accepted.append(pend)
            pend = None
    return accepted, asserts

rows = []
for f in sorted(LOGS.glob("*.txt")):
    txt = f.read_text(errors="ignore")
    if "후보 tactic: 'assert" not in txt: continue
    idx = int(f.stem)
    try:
        thm = get_theorem(CSSplit.TEST, idx, Path("CoqStoq"))
        d = get_thm_desc(thm, DATA_LOC, sdb)
        if d is None: continue
        proof = d.dp.proofs[d.idx]
    except Exception:
        continue
    gold_steps = [s.step.text for s in proof.steps]
    gold_full = proof.theorem.term.text + "".join(gold_steps)
    gold_lemmas = []
    for s in gold_steps:
        for m in NAMED.finditer(s):
            n = m.group(1)
            if len(n) > 2 and not re.fullmatch(r"[A-Z]\d*", n) and n not in gold_lemmas:
                gold_lemmas.append(n)
    acc, asserts = parse_log(f)
    if not asserts: continue
    # assert 명제 vs gold lemma signature 겹침
    best = []
    for a, res in asserts:
        m = ASS.match(a.strip())
        P = m.group(1).strip() if m else None
        if not P: continue
        bs, bn = 0.0, None
        for gl in gold_lemmas:
            s = sig(gl)
            if not s: continue
            body = re.sub(r"^\s*\w+\s+[\w'.]+\s*:", "", s, count=1)
            c = len(toks(P) & toks(body)) / max(len(toks(body)), 1)
            if c > bs: bs, bn = c, gl
        best.append(dict(assert_text=a, result=res, P=P, best_lemma=bn, cov=bs))
    if not best: continue
    rows.append(dict(idx=idx, thm=proof.theorem.term.text.strip(),
                     gold_full=gold_full, gold_steps=gold_steps,
                     gold_lemmas=[(g, sig(g)) for g in gold_lemmas],
                     gen_steps=acc, asserts=best,
                     ncand=len(asserts),
                     maxcov=max(b["cov"] for b in best)))
rows.sort(key=lambda r: -r["maxcov"])
json.dump(rows, open(str(OUT) + ".json", "w"), ensure_ascii=False, indent=1)
print(f"정리 {len(rows)}개 · assert 후보 총 {sum(r['ncand'] for r in rows)}")
allc = [b["cov"] for r in rows for b in r["asserts"]]
import statistics as st
print(f"assert 명제 ↔ gold lemma signature 겹침: 중앙 {st.median(allc)*100:.0f}% · "
      f"≥80% {sum(1 for c in allc if c>=.8)}/{len(allc)} · ≥50% {sum(1 for c in allc if c>=.5)}/{len(allc)}")
print(f"→ {OUT}.json")
