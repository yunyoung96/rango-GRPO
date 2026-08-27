#!/usr/bin/env python3
"""★ **elaborate 된 goal** 을 뽑는다 — `Set Printing All` + `Show.`

## 왜

색인(lemma)은 `Set Printing All` 로 펼쳤는데 goal 은 여전히 출력 형태다.
그 경계를 넘는 비교는 본질적으로 헐겁다(applicability-filter.md §4.8).
양쪽을 같은 형태로 맞춰야 판별트리·지문색인이 제 일을 한다.

## 방법

원본 `.v` 를 잘라 **그 정리의 그 스텝까지만** 컴파일한다:

    Set Printing All.                    ← 파일 맨 앞
    <원본 파일: 정리 시작 전까지>
    <정리 선언>
    <스텝 0 … k-1>                        ← proof_prefix_to_string
    Show.                                 ← ★ 여기 goal 이 elaborate 되어 찍힌다
    Admitted.

뒤를 잘라내므로 파일 전체를 컴파일하지 않는다. 의존 모듈은 이미 `.vo` 가 있어야 한다.

사용: EG_N=40 EG_JOBS=4 python3 scripts/elab_goals.py
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

N = int(os.environ.get("EG_N", "40"))
JOBS = int(os.environ.get("EG_JOBS", "4"))
TMO = int(os.environ.get("EG_TIMEOUT", "300"))
MAXPT = int(os.environ.get("EG_MAX_PER_THM", "3"))
OUT = os.environ.get("EG_OUT", "all_log/elab_goals.jsonl")
CC = "CoqStoq/test-repos/compcert"

def coq_args(root):
    a, pr = [], os.path.join(root, "_CoqProject")
    t = open(pr, errors="ignore").read().split()
    i = 0
    while i < len(t):
        if t[i] in ("-R", "-Q") and i + 2 < len(t):
            a += [t[i], os.path.abspath(os.path.join(root, t[i + 1])), t[i + 2]]; i += 3
        else:
            i += 1
    return a
ARGS = coq_args(CC)
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))

def src_path(thm):
    return os.path.join(CC, thm.path)

def build_one(args):
    """(thm_idx, k) 하나에 대해 elaborate 된 goal 을 뽑는다."""
    i, path, prefix_text, thm_text = args
    try:
        orig = open(path, errors="ignore").read()
    except OSError:
        return i, None, "파일 없음"
    # 정리 선언문을 원문에서 찾아 그 **앞까지**를 머리로 쓴다
    key = " ".join(thm_text.split())
    head = None
    for m in re.finditer(re.escape(thm_text.strip()[:60]), orig):
        head = orig[:m.start()]; break
    if head is None:                      # 공백이 달라 못 찾으면 느슨하게
        nm = re.match(r"\s*\w+\s+([\w']+)", thm_text)
        if nm:
            m = re.search(r"(?m)^\s*(?:Lemma|Theorem|Remark|Corollary|Proposition|Fact)\s+"
                          + re.escape(nm.group(1)) + r"\b", orig)
            if m:
                head = orig[:m.start()]
    if head is None:
        return i, None, "정리 위치 못 찾음"
    body = "Set Printing All.\n" + head + "\n" + prefix_text + "\nShow.\nAdmitted.\n"
    d = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=d, delete=False) as f:
        f.write(body); tmp = f.name
    try:
        t = time.time()
        p = subprocess.run(["coqc", "-q"] + ARGS + [tmp],
                           capture_output=True, text=True, timeout=TMO)
        dt = time.time() - t
        out = p.stdout or ""
        # `Show.` 출력 = 마지막 goal 블록
        m = re.findall(r"(?:^|\n)((?:.*\n)*?)\s*=+\n(.*?)(?=\n\n|\Z)", out, re.S)
        g = out.strip()
        return i, (g, dt), None if g else (p.stderr or "")[:200]
    except subprocess.TimeoutExpired:
        return i, None, "timeout"
    except Exception as e:
        return i, None, str(e)[:150]
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
        except Exception:
            continue
        ks = [k for k, st in enumerate(proof.steps)
              if HEADT.match(st.step.text or "")
              and HEADT.match(st.step.text).group(1) in ("apply", "eapply", "rewrite", "erewrite")
              and NAMED.search(st.step.text or "")]
        if not ks: continue
        if len(ks) > MAXPT:
            stp = len(ks) / MAXPT
            ks = [ks[int(x * stp)] for x in range(MAXPT)]
        for k in ks:
            jobs.append(((i, k), src_path(thm),
                         proof.proof_prefix_to_string(proof.steps[k]),
                         proof.theorem.term.text))
    print(f"■ 대상 {len(jobs)} (정리 {len(ids)}) · 병렬 {JOBS}", flush=True)
    ok = 0; T = []
    with open(OUT, "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for n, (key, res, err) in enumerate(ex.map(build_one, jobs)):
            if res:
                g, dt = res; ok += 1; T.append(dt)
                fo.write(json.dumps(dict(idx=key[0], k=key[1], goal_elab=g),
                                    ensure_ascii=False) + "\n"); fo.flush()
            if (n + 1) % 10 == 0:
                print(f"   … {n+1}/{len(jobs)} · 성공 {ok}", flush=True)
    import statistics as st
    print(f"\n  성공 {ok}/{len(jobs)} = {ok/max(len(jobs),1)*100:.1f}%"
          f" · 건당 중앙 {st.median(T) if T else 0:.1f}s → {OUT}")
