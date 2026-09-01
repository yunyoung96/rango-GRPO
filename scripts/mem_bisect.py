#!/usr/bin/env python3
"""★ 어느 정리에서 메모리가 터지는지 좁힌다.

`dn_rank_eval` 이 CompCert 에서 coqtop 하나를 71→112GB 까지 키웠다.
정리를 **하나씩** 돌리되 `ulimit -v` 로 상한을 걸어, 터지는 것만 기록한다.
상한을 넘으면 coqtop 이 Out of memory 로 죽고 우리는 그 정리를 안다.

사용: python3 scripts/mem_bisect.py [상한GB] [정리수]
"""
import collections, json, os, re, resource, subprocess, sys, tempfile, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split as CSSplit, get_theorem
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc

CAP_GB = int(sys.argv[1]) if len(sys.argv) > 1 else 8
N = int(sys.argv[2]) if len(sys.argv) > 2 else 60
CC = "CoqStoq/test-repos/compcert"
PLUG = os.path.abspath("ocaml/applic")
OUT = "all_log/mem_bisect.jsonl"
TIMEOUT = 600

t = open(os.path.join(CC, "_CoqProject")).read().split(); ARGS = []; _i = 0
while _i < len(t):
    if t[_i] in ("-R", "-Q"):
        ARGS += [t[_i], os.path.abspath(os.path.join(CC, t[_i+1])), t[_i+2]]; _i += 3
    else: _i += 1
ARGS += ["-R", PLUG, "Applic", "-I", PLUG]
ENV = dict(os.environ)
ENV["OCAMLPATH"] = os.path.join(PLUG, "findlib") + ":" + ENV.get("OCAMLPATH", "")

sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))
NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
STAT = re.compile(r"APPLIC_STAT\s+ver=\S+\s+cand=(\d+)\s+pat=(\d+)")


assert 1 <= CAP_GB <= 256, f"상한이 이상하다: {CAP_GB}GB"
assert N > 0
assert os.path.isdir(CC), f"CompCert 가 없다: {CC}"
assert os.path.isdir(PLUG), f"플러그인이 없다: {PLUG}"
assert STAT.search("APPLIC_STAT ver=r11 cand=1 pat=2"), "STAT 정규식 어긋남"


def _limit():
    """★ 자식에게만 가상메모리 상한을 건다 — 부모(파이썬)는 안 건드린다."""
    b = CAP_GB * 1024 ** 3
    resource.setrlimit(resource.RLIMIT_AS, (b, b))


def head_by_pos(orig, thm):
    ln = getattr(getattr(thm, "theorem_start_pos", None), "line", None)
    if not ln: return None
    parts = orig.splitlines(keepends=True)
    return "".join(parts[:ln - 1]) if ln - 1 <= len(parts) else None


if __name__ == "__main__":
    ids = [int(x) for x in Path("data/compcert_bs2_rand200_idx.txt").read_text().split()][:N]
    rows = []; C = collections.Counter()
    print(f"■ CompCert · 정리 {len(ids)} · 메모리 상한 {CAP_GB}GB", flush=True)
    for n, i in enumerate(ids, 1):
        try:
            thm = get_theorem(CSSplit.TEST, i, Path("CoqStoq"))
            d = get_thm_desc(thm, Path("raw-data/coqstoq-test"), sdb)
            if d is None: continue
            proof = d.dp.proofs[d.idx]
            path = os.path.join(CC, str(thm.path))
            orig = open(path, errors="ignore").read()
            head = head_by_pos(orig, thm)
        except Exception:
            continue
        if head is None: continue
        ks = [k for k, s in enumerate(proof.steps)
              if HEADT.match(s.step.text or "")
              and HEADT.match(s.step.text).group(1) in
                 ("apply", "eapply", "rewrite", "erewrite")
              and NAMED.search(s.step.text or "") and s.goals]
        if not ks: continue
        ks = ks[:3]
        steps = [s.step.text for s in proof.steps]
        body = ["Require Import Applic.", head, proof.theorem.term.text]; prev = 0
        for k in ks:
            body.append("".join(steps[prev:k])); prev = k
            body.append(f'idtac "@@@{k}".'); body.append("try applic_filter.")
        body.append("Admitted.")
        dd = os.path.dirname(os.path.abspath(path))
        with tempfile.NamedTemporaryFile("w", suffix=".v", dir=dd, delete=False) as f:
            f.write("\n".join(body) + "\n"); tmp = f.name
        rc, out, why = None, "", ""
        try:
            p = subprocess.run(["coqtop", "-q"] + ARGS, stdin=open(tmp),
                               capture_output=True, text=True, env=ENV,
                               timeout=TIMEOUT, preexec_fn=_limit)
            rc = p.returncode; out = (p.stdout or "") + (p.stderr or "")
        except subprocess.TimeoutExpired:
            why = "timeout"
        except Exception as e:
            why = type(e).__name__
        finally:
            b = os.path.splitext(tmp)[0]
            for e in (".v", ".vo", ".vok", ".vos", ".glob"):
                try: os.unlink(b + e)
                except OSError: pass
        oom = ("Out of memory" in out or "Stack overflow" in out
               or "out of memory" in out or (rc not in (0, None) and not out.strip()))
        nstat = len(STAT.findall(out))
        tag = "timeout" if why == "timeout" else ("★OOM" if oom else
              ("정상" if nstat else "지점0"))
        C[tag] += 1
        rows.append({"idx": i, "file": str(thm.path), "thm": proof.theorem.term.text[:70],
                     "tag": tag, "nstat": nstat, "rc": rc})
        if tag != "정상":
            print(f"   {n:3d}/{len(ids)} idx={i:4d} {tag:8s} {str(thm.path)[-40:]:42s}"
                  f" {proof.theorem.term.text[:46]}", flush=True)
        if n % 10 == 0:
            print(f"   … {n}/{len(ids)}  {dict(C)}", flush=True)
    assert rows, "정리를 하나도 못 돌렸다"
    assert C["정상"] + C["★OOM"] + C["timeout"] + C["지점0"] <= len(rows) + 1
    with open(OUT, "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n■ 결과 ({len(rows)}정리)")
    for k, v in C.most_common(): print(f"   {k:10s}{v:4d}")
    bad = [r for r in rows if r["tag"] == "★OOM"]
    if bad:
        print(f"\n■ 터진 정리 {len(bad)}개")
        for r in bad: print(f"   idx={r['idx']:4d} {r['file']:44s} {r['thm']}")
    print("MEM_BISECT_DONE", flush=True)
