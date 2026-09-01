#!/usr/bin/env python3
"""★ **search.md 용 전사(轉寫) 뜨기** — 실제 goal 에 실제 질의를 쏘고 실제 출력을 받는다.

지점 하나를 골라 (1) goal, (2) 생성된 질의 전부, (3) 각 질의의 **Coq 실제 출력**,
(4) gold 이 어느 질의에서 처음 나왔는지를 그대로 남긴다.

사용: python3 scripts/search_demo.py 472 5
"""
import json, os, re, subprocess, sys, tempfile, logging
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
                                         hyp_rewrite_queries, wide_queries,
                                         notation_queries)

CC = "CoqStoq/test-repos/compcert"
LEVELS, RWN, FWDN, WIDEN = 3, 4, 3, 8
MAXOUT = 6          # 질의당 보여줄 결과 줄수 상한

t = open(os.path.join(CC, "_CoqProject")).read().split(); ARGS = []; _i = 0
while _i < len(t):
    if t[_i] in ("-R", "-Q"):
        ARGS += [t[_i], os.path.abspath(os.path.join(CC, t[_i+1])), t[_i+2]]; _i += 3
    else: _i += 1

sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))
NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")

def head_by_pos(orig, thm):
    """★ CoqStoq 가 **정확한 줄번호**를 준다 — 텍스트 검색보다 이걸 먼저 쓴다.

    `Maps.v` 에는 `Theorem gso` 가 **셋**(PTree·PMap·…) 있어서 텍스트로 찾으면
    첫 번째(Module PTree 안)에 걸린다. 거기서는 `PTree.gso` 가 아직 존재하지
    않으므로 질의도 검증도 통째로 어긋난다. 실측 199 중 1건(0.5%).
    """
    ln = getattr(getattr(thm, "theorem_start_pos", None), "line", None)
    if not ln:
        return None
    parts = orig.splitlines(keepends=True)
    if ln - 1 > len(parts):
        return None
    return "".join(parts[:ln - 1])


def head_of_file(orig, thm_text):
    j = orig.find(thm_text.strip()[:60])
    if j >= 0: return orig[:j]
    m0 = re.match(r"\s*\w+\s+([\w']+)", thm_text)
    if m0:
        m = re.search(r"(?m)^\s*(?:Lemma|Theorem|Remark|Corollary|Proposition|Fact|Definition)\s+"
                      + re.escape(m0.group(1)) + r"\b", orig)
        if m: return orig[:m.start()]
    return None

def build(g, tac):
    loc = local_names(g); qs = []
    if tac.endswith("apply"):
        for p in ladder(g.goal, loc, max_levels=LEVELS): qs.append(("①사다리", f"SearchPattern ({p})."))
        for p in hyp_queries(g, loc, maxn=FWDN):         qs.append(("④가설방향", f"SearchPattern ({p})."))
    else:
        for q in symbol_queries(g.goal, loc, maxn=6):    qs.append(("③기호결합", q))
        for p in rewrite_targets(g.goal, loc, maxn=RWN): qs.append(("②부분항", f"SearchRewrite ({p})."))
        for q in hyp_rewrite_queries(g, loc, maxn=3):    qs.append(("⑤가설안", q))
        for p in hyp_queries(g, loc, maxn=FWDN):         qs.append(("④가설방향", f"SearchPattern ({p})."))
    for q in wide_queries(g.goal, loc, g.hyps, maxsym=WIDEN): qs.append(("⑥넓게", q))
    for q in notation_queries(g.goal, loc, maxn=2):      qs.append(("⑦notation", q))
    return loc, qs

def main(idx, k):
    thm = get_theorem(CSSplit.TEST, idx, Path("CoqStoq"))
    d = get_thm_desc(thm, Path("raw-data/coqstoq-test"), sdb)
    proof = d.dp.proofs[d.idx]
    path = os.path.join(CC, str(thm.path)); orig = open(path, errors="ignore").read()
    head = head_by_pos(orig, thm) or head_of_file(orig, proof.theorem.term.text)
    st = proof.steps[k]; g = st.goals[0]
    gold = NAMED.search(st.step.text).group(1)
    tac = HEADT.match(st.step.text).group(1)
    loc, qs = build(g, tac)

    body = [head, proof.theorem.term.text, "".join(s.step.text for s in proof.steps[:k])]
    for n, (fam, q) in enumerate(qs):
        body.append(f'idtac "@@@{n}".'); body.append(q)
    body.append("Admitted.")
    dd = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=dd, delete=False) as f:
        f.write("\n".join(body) + "\n"); tmp = f.name
    try:
        p = subprocess.run(["coqtop", "-q"] + ARGS, stdin=open(tmp),
                           capture_output=True, text=True, timeout=600)
        out = p.stdout or ""
    finally:
        for e in (".v", ".vo", ".vok", ".vos", ".glob"):
            try: os.unlink(os.path.splitext(tmp)[0] + e)
            except OSError: pass

    blocks = re.split(r"@@@(\d+)\s*", out)
    seg = {}
    for a in range(1, len(blocks) - 1, 2):
        seg[int(blocks[a])] = blocks[a + 1]

    print("=" * 78)
    print(f"■ idx {idx} · step {k} · 파일 {thm.path}")
    print(f"■ gold tactic : {st.step.text.strip()}")
    print(f"■ 지역 이름   : {sorted(loc)}")
    print("■ 가설")
    for h in (g.hyps or [])[:8]: print("     " + h.strip()[:150])
    print("■ goal")
    for ln in g.goal.strip().splitlines()[:10]: print("     " + ln[:150])
    print(f"\n■ 발행 질의 {len(qs)}개 — 하나씩 실제 출력\n")
    gb = gold.split(".")[-1]; firsthit = None; allnames = set()
    for n, (fam, q) in enumerate(qs):
        s = seg.get(n, "")
        # coqtop 이 앞에 붙이는 프롬프트/에코를 걷어낸다
        s = re.sub(r"(?m)^Coq < ", "", s)
        s = re.sub(r"(?m)^> .*$", "", s)
        lines = [l.rstrip() for l in s.splitlines() if l.strip()]
        names = re.findall(r"(?m)^([A-Za-z_][\w'.]*):\s*$|^([A-Za-z_][\w'.]*):\s", s)
        nm = [a or b for a, b in names]
        allnames |= set(nm)
        hit = any(x == gold or x.split(".")[-1] == gb for x in nm)
        if hit and firsthit is None: firsthit = n
        err = "Error" in s or "Syntax error" in s
        mark = "★gold" if hit else ("✗오류" if err else f"{len(nm)}개")
        print(f"  [{n:2d}] {fam:10s} {mark:>7s}  {q[:120]}")
        if err:
            e = [l for l in lines if "Error" in l or "Syntax" in l][:1]
            print(f"        └ {e[0][:120] if e else ''}")
        elif nm:
            for l in lines[:MAXOUT]:
                print(f"        │ {l[:120]}")
            if len(lines) > MAXOUT: print(f"        │ … ({len(lines)-MAXOUT}줄 더)")
    print(f"\n■ 합집합 후보 {len(allnames)}개 · gold `{gold}` "
          + (f"→ 질의 [{firsthit}] 에서 처음 등장" if firsthit is not None else "→ **못 찾음**"))

if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
