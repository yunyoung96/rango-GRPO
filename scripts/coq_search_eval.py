#!/usr/bin/env python3
"""★★★ **Coq 안에서** 적용가능성 색인을 쓴다 — `SearchPattern` / `SearchRewrite`.

## 왜 이것인가

바깥에서 만든 색인 8판본이 전부 gold 를 흘렸다(applicability-filter.md §4.10).
남은 벽이 **변환(delta/iota/beta)** 이었고, 그건 Coq 커널이 있어야 넘는다.
그런데 **Coq 이 이미 그 색인을 갖고 있다**:

    SearchPattern <패턴>   결론이 패턴과 매칭되는 lemma  → `apply` 후보
    SearchRewrite <항>     한 변이 그 항과 매칭되는 등식 → `rewrite` 후보

elaboration·변환·강제변환·타입클래스가 전부 적용된 상태로 판정한다.

## 핵심 규칙 — goal 의 **지역변수를 `_` 로** 바꿔야 한다

    ✗  SearchPattern (Int.and (Int.shl x n) … )   지역 x n 이 경직이라 아무것도 안 나옴
    ✓  SearchPattern (Int.and (Int.shl _ _) … )   → Int.and_shl

지역 이름(가설 목록)이 곧 lemma 의 전칭 변수가 채울 자리다.

## 방법

정리마다 한 파일 — 증명 접두사를 실행하다가 목표 스텝에서 질의를 끼운다:

    <스텝 0 … k-1>
    idtac "@@@k".
    SearchPattern (<추상화한 goal>).
    SearchRewrite (<추상화한 부분항>).      (rewrite 스텝이면)

사용: CS_N=120 CS_JOBS=4 python3 scripts/coq_search_eval.py
"""
import concurrent.futures as cf
import collections, json, os, re, subprocess, sys, tempfile, time, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split as CSSplit, get_theorem
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc

N = int(os.environ.get("CS_N", "120"))
JOBS = int(os.environ.get("CS_JOBS", "4"))
TMO = int(os.environ.get("CS_TIMEOUT", "300"))
MAXPT = int(os.environ.get("CS_MAX_PER_THM", "3"))
OUT = os.environ.get("CS_OUT", "all_log/coq_search.jsonl")
CC = "CoqStoq/test-repos/compcert"
t = open(os.path.join(CC, "_CoqProject"), errors="ignore").read().split()
ARGS, i = [], 0
while i < len(t):
    if t[i] in ("-R", "-Q") and i + 2 < len(t):
        ARGS += [t[i], os.path.abspath(os.path.join(CC, t[i + 1])), t[i + 2]]; i += 3
    else:
        i += 1
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))

def local_names(goal):
    """가설 줄에서 지역 이름을 뽑는다 — `H : P` · `x, y : T` · `m := e : T`."""
    out = set()
    for h in goal.hyps:
        lhs = re.split(r":=|:", h, 1)[0]
        out |= set(re.findall(r"[A-Za-z_][\w']*", lhs))
    return out

def abstract(term, locals_):
    """지역 이름을 `_` 로. lemma 의 전칭 변수가 채울 자리다."""
    def rep(m):
        w = m.group(0)
        return "_" if w in locals_ else w
    return re.sub(r"[A-Za-z_][\w']*", rep, term)

def subterms_of(s, maxn=6):
    """괄호로 묶인 부분항들 — `rewrite` 질의용. 큰 것부터."""
    out, st = [], []
    for i, ch in enumerate(s):
        if ch == "(":
            st.append(i)
        elif ch == ")" and st:
            a = st.pop()
            frag = s[a:i + 1]
            if 6 < len(frag) < 220:
                out.append(frag)
    out.sort(key=len, reverse=True)
    return out[:maxn]

def head_of_file(orig, thm_text):
    j = orig.find(thm_text.strip()[:60])
    if j >= 0: return orig[:j]
    m0 = re.match(r"\s*\w+\s+([\w']+)", thm_text)
    if m0:
        m = re.search(r"(?m)^\s*(?:Lemma|Theorem|Remark|Corollary|Proposition|Fact|Definition)\s+"
                      + re.escape(m0.group(1)) + r"\b", orig)
        if m: return orig[:m.start()]
    return None

def run(job):
    i, path, thm_text, chunks, ks, queries = job
    try:
        orig = open(path, errors="ignore").read()
    except OSError:
        return i, [], "파일 없음"
    head = head_of_file(orig, thm_text)
    if head is None:
        return i, [], "정리 위치 못 찾음"
    body = [head, thm_text]
    prev = 0
    for k in ks:
        body.append(chunks[prev])
        body.append(f'idtac "@@@{k}".')
        for q in queries[k]:
            body.append(q)
        prev = k
    body.append("Admitted.")
    src = "\n".join(body) + "\n"
    d = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=d, delete=False) as f:
        f.write(src); tmp = f.name
    try:
        t0 = time.time()
        p = subprocess.run(["coqc", "-q"] + ARGS + [tmp],
                           capture_output=True, text=True, timeout=TMO)
        dt = time.time() - t0
        out = p.stdout or ""
        blocks = re.split(r"@@@(\d+)\s*", out)
        recs = []
        for a in range(1, len(blocks) - 1, 2):
            k = int(blocks[a])
            names = re.findall(r"(?m)^(\w[\w'.]*):", blocks[a + 1])
            recs.append({"idx": i, "k": k, "found": sorted(set(names)), "sec": dt})
        return i, recs, None if recs else (p.stderr or "")[:150]
    except subprocess.TimeoutExpired:
        return i, [], "timeout"
    except Exception as e:
        return i, [], str(e)[:120]
    finally:
        b = os.path.splitext(tmp)[0]
        for ext in (".v", ".vo", ".vok", ".vos", ".glob"):
            try: os.unlink(b + ext)
            except OSError: pass

if __name__ == "__main__":
    ids = [int(x) for x in Path("data/compcert_bs2_rand200_idx.txt").read_text().split()][:N]
    jobs, meta = [], {}
    for i in ids:
        try:
            thm = get_theorem(CSSplit.TEST, i, Path("CoqStoq"))
            d = get_thm_desc(thm, Path("raw-data/coqstoq-test"), sdb)
            if d is None: continue
            proof = d.dp.proofs[d.idx]
            path = os.path.join(CC, str(thm.path))
            orig = open(path, errors="ignore").read()
        except Exception:
            continue
        if head_of_file(orig, proof.theorem.term.text) is None:
            continue
        ks = [k for k, st in enumerate(proof.steps)
              if HEADT.match(st.step.text or "")
              and HEADT.match(st.step.text).group(1) in ("apply", "eapply", "rewrite", "erewrite")
              and NAMED.search(st.step.text or "") and st.goals]
        if not ks: continue
        if len(ks) > MAXPT:
            stp = len(ks) / MAXPT
            ks = [ks[int(x * stp)] for x in range(MAXPT)]
        steps = [s.step.text for s in proof.steps]
        chunks, prev = {}, 0
        for k in ks:
            chunks[prev] = "".join(steps[prev:k]); prev = k
        queries = {}
        for k in ks:
            st = proof.steps[k]
            g = st.goals[0]
            loc = local_names(g)
            tac = HEADT.match(st.step.text).group(1)
            qs = []
            if tac.endswith("apply"):
                qs.append(f"SearchPattern ({abstract(g.goal, loc)}).")
            else:
                for sub in subterms_of(g.goal):
                    qs.append(f"SearchRewrite {abstract(sub, loc)}.")
                if not qs:
                    qs.append(f"SearchRewrite ({abstract(g.goal, loc)}).")
            queries[k] = qs
            meta[(i, k)] = dict(gold=NAMED.search(st.step.text).group(1),
                                tac="rewrite" if tac.endswith("rewrite") else "apply",
                                nq=len(qs))
        jobs.append((i, path, proof.theorem.term.text, chunks, ks, queries))
    jobs.sort(key=lambda j: len(open(j[1], errors="ignore").read()))
    print(f"■ 정리 {len(jobs)} · 질의지점 {len(meta)} · 병렬 {JOBS}", flush=True)
    S = collections.Counter(); T = []
    with open(OUT, "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for n, (i, recs, err) in enumerate(ex.map(run, jobs)):
            for r in recs:
                m = meta.get((r["idx"], r["k"]))
                if not m: continue
                gb = m["gold"].split(".")[-1]
                hit = any(x == m["gold"] or x.split(".")[-1] == gb for x in r["found"])
                S["지점"] += 1; S["후보"] += len(r["found"]); S["적중"] += hit
                S[f"{m['tac']} 지점"] += 1; S[f"{m['tac']} 적중"] += hit
                S[f"{m['tac']} 후보"] += len(r["found"])
                T.append(r["sec"])
                r.update(gold=m["gold"], tac=m["tac"], hit=hit, nq=m["nq"])
                fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            if err: S["실패"] += 1
            if (n + 1) % 10 == 0:
                print(f"   … {n+1}/{len(jobs)} · 지점 {S['지점']} · 적중 {S['적중']}", flush=True)
            fo.flush()
    n = max(S["지점"], 1)
    import statistics as st
    print(f"\n■ Coq 내장 색인 · 질의지점 {S['지점']} (정리 실패 {S['실패']})")
    print(f"   ① gold 적중   {S['적중']}/{n} = {S['적중']/n*100:.1f}%")
    print(f"   ② 후보 수     {S['후보']/n:.1f}개/지점   (현행 풀 ~2,100 대비 "
          f"{2100/max(S['후보']/n,0.01):.0f}배 축소)")
    for tac in ("apply", "rewrite"):
        m = S[f"{tac} 지점"]
        if m:
            print(f"   · {tac:8s} {m:3d} 지점 · 적중 {S[f'{tac} 적중']/m*100:5.1f}%"
                  f" · 후보 {S[f'{tac} 후보']/m:5.1f}개")
