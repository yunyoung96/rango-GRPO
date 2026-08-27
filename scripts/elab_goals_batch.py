#!/usr/bin/env python3
"""★ elaborate 된 goal 을 **정리당 1회 컴파일**로 뽑는다.

앞 판본(`elab_goals.py`)은 (정리, 스텝) 쌍마다 파일을 처음부터 다시 컴파일했다 —
같은 접두사를 3번 재컴파일해서 건당 4~5분이 걸렸다. 여기서는 한 정리의 목표 스텝을
**한 파일에 몰아** 넣는다:

    Set Printing All.
    <원본 파일: 정리 시작 전까지>          ← 여기가 비용의 대부분
    <정리 선언>
    <스텝 0 … k1-1>
    idtac "@@@k1". Show.                  ← 표식 + goal
    <스텝 k1 … k2-1>
    idtac "@@@k2". Show.
    …
    Admitted.

`idtac "…"` 는 무연산 tactic 이라 증명을 안 바꾸고 stdout 에 표식을 찍는다.
`Show.` 도 goal 을 소비하지 않는다.

★ 정리가 파일 **앞쪽**에 있을수록 싸다(머리를 적게 컴파일한다). 그래서 머리 크기
  오름차순으로 돌고, 어디까지 왔는지 기록한다 — 표본 편향을 숨기지 않기 위해서다.

사용: EGB_N=200 EGB_JOBS=4 EGB_TIMEOUT=600 EGB_MAX_HEAD=200000 python3 scripts/elab_goals_batch.py
"""
import concurrent.futures as cf
import json, os, re, subprocess, sys, tempfile, time, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split as CSSplit, get_theorem
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc

N = int(os.environ.get("EGB_N", "200"))
JOBS = int(os.environ.get("EGB_JOBS", "4"))
TMO = int(os.environ.get("EGB_TIMEOUT", "600"))
MAXPT = int(os.environ.get("EGB_MAX_PER_THM", "4"))
MAXHEAD = int(os.environ.get("EGB_MAX_HEAD", "10000000"))
OUT = os.environ.get("EGB_OUT", "all_log/elab_goals_batch.jsonl")
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

def head_of_file(orig, thm_text):
    """정리 선언이 시작되는 위치 앞까지."""
    probe = thm_text.strip()[:60]
    j = orig.find(probe)
    if j >= 0:
        return orig[:j]
    m0 = re.match(r"\s*\w+\s+([\w']+)", thm_text)
    if m0:
        m = re.search(r"(?m)^\s*(?:Lemma|Theorem|Remark|Corollary|Proposition|Fact|Definition)\s+"
                      + re.escape(m0.group(1)) + r"\b", orig)
        if m:
            return orig[:m.start()]
    return None

def run(job):
    i, path, thm_text, prefixes, ks = job
    try:
        orig = open(path, errors="ignore").read()
    except OSError:
        return i, [], 0.0, "파일 없음"
    head = head_of_file(orig, thm_text)
    if head is None:
        return i, [], 0.0, "정리 위치 못 찾음"
    # 스텝을 이어 붙이며 목표 지점마다 표식+Show
    body = ["Set Printing All.", head, thm_text]
    prev = 0
    for k, pref in zip(ks, prefixes):
        body.append(pref[prev])                # 직전 목표부터 이번 목표 직전까지
        body.append(f'idtac "@@@{k}".')
        body.append("Show.")
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
        out = (p.stdout or "")
        blocks = re.split(r"@@@(\d+)\s*", out)
        recs = []
        for a in range(1, len(blocks) - 1, 2):
            k = int(blocks[a]); g = blocks[a + 1].strip()
            if g:
                recs.append({"idx": i, "k": k, "goal_elab": g})
        return i, recs, dt, None if recs else (p.stderr or out or "")[:200]
    except subprocess.TimeoutExpired:
        return i, [], TMO, "timeout"
    except Exception as e:
        return i, [], 0.0, str(e)[:150]
    finally:
        b = os.path.splitext(tmp)[0]
        for ext in (".v", ".vo", ".vok", ".vos", ".glob"):
            try: os.unlink(b + ext)
            except OSError: pass

if __name__ == "__main__":
    ids = [int(x) for x in Path("data/compcert_bs2_rand200_idx.txt").read_text().split()][:N]
    jobs = []
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
        h = head_of_file(orig, proof.theorem.term.text)
        if h is None or len(h) > MAXHEAD:
            continue
        ks = [k for k, st in enumerate(proof.steps)
              if HEADT.match(st.step.text or "")
              and HEADT.match(st.step.text).group(1) in ("apply", "eapply", "rewrite", "erewrite")
              and NAMED.search(st.step.text or "")]
        if not ks: continue
        if len(ks) > MAXPT:
            stp = len(ks) / MAXPT
            ks = [ks[int(x * stp)] for x in range(MAXPT)]
        # prefixes[j] = 스텝 j 직전까지의 **원문 조각**(직전 목표 이후분)
        allsteps = [s.step.text for s in proof.steps]
        pre = {}
        prev = 0
        for k in ks:
            pre[prev] = "".join(allsteps[prev:k]); prev = k
        jobs.append((i, path, proof.theorem.term.text,
                     [pre for _ in ks], ks))
        jobs[-1] = (i, path, proof.theorem.term.text, [pre] * len(ks), ks)
    jobs.sort(key=lambda j: len(open(j[1], errors="ignore").read()))
    print(f"■ 정리 {len(jobs)} · 병렬 {JOBS} · 정리당 상한 {TMO}s "
          f"(머리 상한 {MAXHEAD:,}B)", flush=True)
    ok = nrec = 0; T = []; errs = {}
    t0 = time.time()
    with open(OUT, "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for n, (i, recs, dt, err) in enumerate(ex.map(run, jobs)):
            if recs:
                ok += 1; nrec += len(recs); T.append(dt)
                for r in recs:
                    fo.write(json.dumps(r, ensure_ascii=False) + "\n")
                fo.flush()
            elif err:
                errs[err[:40]] = errs.get(err[:40], 0) + 1
            if (n + 1) % 10 == 0:
                import statistics as st
                print(f"   … {n+1}/{len(jobs)} · 정리 {ok} · goal {nrec}"
                      f" · 중앙 {st.median(T) if T else 0:.0f}s", flush=True)
    import statistics as st
    print(f"\n  정리 {ok}/{len(jobs)} · goal {nrec} · {time.time()-t0:.0f}s"
          f" · 정리당 중앙 {st.median(T) if T else 0:.0f}s → {OUT}")
    for e, c in sorted(errs.items(), key=lambda x: -x[1])[:5]:
        print(f"    실패 ×{c}: {e}")
