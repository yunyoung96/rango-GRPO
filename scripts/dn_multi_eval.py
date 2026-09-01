#!/usr/bin/env python3
"""★★ **프로젝트를 넘어서 재현율이 유지되는가** — CompCert 밖에서 잰다.

지금까지 모든 수치는 CompCert 하나였다. 그런데 CompCert 는 rango 의 **held-out**
이고 스타일도 특수하다(대규모 컴파일러 검증, 무거운 모듈·notation). 방법이
프로젝트에 특화된 것인지 일반적인지는 **다른 프로젝트에서 재야** 안다.

컴파일된 저장소가 있는 것만 잰다:
    VAL     graph-theory · coqeal · qarith-stern-brocot · stalmarck · sudoku · bertrand
    CUTOFF  pnvrocqlib · bb5
    TEST    compcert 외 fourcolor · math-classes · buchberger · reglang · poltac · huffman · zfc

지점마다 `applic_check <gold>` 를 돌려 **실제 파이프라인**에서 정답이 살아남는지 본다.

사용: python3 scripts/dn_multi_eval.py [split] [프로젝트당_정리수]
"""
import concurrent.futures as cf
import collections, json, os, re, signal, subprocess, sys, tempfile, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split, get_theorem_list
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc

SPLIT_NAME = sys.argv[1] if len(sys.argv) > 1 else "VAL"
PER_PROJ = int(sys.argv[2]) if len(sys.argv) > 2 else 25
JOBS = 2
TIMEOUT = 1800
MAX_PT = 3
OUT = f"all_log/dn_multi_{SPLIT_NAME.lower()}.jsonl"
PLUG = os.path.abspath("ocaml/applic")

_SPLIT = {"VAL": Split.VAL, "CUTOFF": Split.CUTOFF, "TEST": Split.TEST}[SPLIT_NAME]
_DIR = {"VAL": "val-repos", "CUTOFF": "cutoff-repos", "TEST": "test-repos"}[SPLIT_NAME]
_DATA = {"VAL": "raw-data/coqstoq-val", "CUTOFF": "raw-data/coqstoq-cutoff",
         "TEST": "raw-data/coqstoq-test"}[SPLIT_NAME]
_SDB = {"VAL": "raw-data/coqstoq-val/coqstoq-val-sentences.db",
        "CUTOFF": "raw-data/coqstoq-cutoff/coqstoq-cutoff-sentences.db",
        "TEST": "raw-data/coqstoq-test/coqstoq-test-sentences.db"}[SPLIT_NAME]

sdb = SentenceDB.load(Path(_SDB))
NAMED = re.compile(r"\b(?:e?apply|e?rewrite|unfold|destruct|induction|case|elim"
                   r"|e?exact)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
CHK = re.compile(r"CHECK\s+ver=(\S+)\s+(\S+)\s+ap=(\d)\s+in=(\d)\s+rw=(\d)")
HYPL = re.compile(r"(?m)^HYPS ?(.*)$")
GBL = re.compile(r"(?m)^GBIND ?(.*)$")
_SAMPLE = "CHECK ver=r9 PTree.gso ap=1 in=1 rw=1 dnA=1"
assert CHK.search(_SAMPLE), "CHECK 정규식이 실제 출력과 어긋난다"


def proj_args(pdir):
    """프로젝트의 `_CoqProject` 에서 로드 경로를 만든다. 없으면 -R . 하나."""
    cp = os.path.join(pdir, "_CoqProject")
    args = []
    if os.path.exists(cp):
        t = open(cp).read().split(); i = 0
        while i < len(t):
            if t[i] in ("-R", "-Q") and i + 2 < len(t):
                args += [t[i], os.path.abspath(os.path.join(pdir, t[i+1])), t[i+2]]; i += 3
            else: i += 1
    if not args:
        args = ["-R", os.path.abspath(pdir), ""]
    return args + ["-R", PLUG, "Applic", "-I", PLUG]


def _coqtop(cmd, stdin=None, env=None, timeout=None):
    p = subprocess.Popen(cmd, stdin=stdin, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, env=env,
                         start_new_session=True)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try: os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except Exception: pass
        p.wait(); raise
    return out or ""


def head_by_pos(orig, thm):
    ln = getattr(getattr(thm, "theorem_start_pos", None), "line", None)
    if not ln: return None
    parts = orig.splitlines(keepends=True)
    return "".join(parts[:ln - 1]) if ln - 1 <= len(parts) else None


def run(job):
    proj, path, head, thm_text, chunks, ks, golds = job
    env = dict(os.environ)
    env["OCAMLPATH"] = os.path.join(PLUG, "findlib") + ":" + env.get("OCAMLPATH", "")
    body = ["Require Import Applic.", head, thm_text]; prev = 0
    for k in ks:
        body.append(chunks[prev]); body.append(f'idtac "@@@{k}".')
        body.append(f"try applic_check {golds[k]}."); prev = k
    body.append("Admitted.")
    d = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=d, delete=False) as f:
        f.write("\n".join(body) + "\n"); tmp = f.name
    try:
        out = _coqtop(["coqtop", "-q"] + proj_args(proj), stdin=open(tmp),
                      env=env, timeout=TIMEOUT)
        blocks = re.split(r"@@@(\d+)\s*", out); recs = []
        for a in range(1, len(blocks) - 1, 2):
            k = int(blocks[a]); seg = blocks[a + 1]
            m = CHK.search(seg)
            if not m: continue
            hm = HYPL.search(seg); gm = GBL.search(seg)
            loc = ((hm.group(1).split() if hm else [])
                   + (gm.group(1).split() if gm else []))
            recs.append({"proj": os.path.basename(proj), "k": k,
                         "ver": m.group(1), "name": m.group(2),
                         "ap": int(m.group(3)), "in": int(m.group(4)),
                         "rw": int(m.group(5)), "gold": golds[k],
                         "local": golds[k] in set(loc)})
        return recs
    except Exception:
        return []
    finally:
        b = os.path.splitext(tmp)[0]
        for e in (".v", ".vo", ".vok", ".vos", ".glob"):
            try: os.unlink(b + e)
            except OSError: pass


if __name__ == "__main__":
    thms = get_theorem_list(_SPLIT, Path("CoqStoq"))
    byp = collections.defaultdict(list)
    for t in thms: byp[str(t.project.dir_name)].append(t)
    jobs = []
    for proj, ts in sorted(byp.items()):
        pdir = os.path.join("CoqStoq", _DIR, proj)
        if not os.path.isdir(pdir): continue
        if not any(True for _ in Path(pdir).rglob("*.vo")): continue
        got = 0
        for thm in ts:
            if got >= PER_PROJ: break
            try:
                d = get_thm_desc(thm, Path(_DATA), sdb)
                if d is None: continue
                proof = d.dp.proofs[d.idx]
                path = os.path.join(pdir, str(thm.path))
                orig = open(path, errors="ignore").read()
                head = head_by_pos(orig, thm)
            except Exception:
                continue
            if head is None: continue
            ks = [k for k, s in enumerate(proof.steps)
                  if HEADT.match(s.step.text or "")
                  and HEADT.match(s.step.text).group(1) in (
                      "apply", "eapply", "rewrite", "erewrite", "unfold",
                      "destruct", "induction", "case", "elim", "exact", "eexact")
                  and NAMED.search(s.step.text or "") and s.goals]
            if not ks: continue
            if len(ks) > MAX_PT:
                stp = len(ks)/MAX_PT; ks = [ks[int(x*stp)] for x in range(MAX_PT)]
            steps = [s.step.text for s in proof.steps]
            chunks, prev = {}, 0
            for k in ks: chunks[prev] = "".join(steps[prev:k]); prev = k
            golds = {k: NAMED.search(proof.steps[k].step.text).group(1) for k in ks}
            jobs.append((pdir, path, head, proof.theorem.term.text, chunks, ks, golds))
            got += 1
    assert jobs, "정리를 하나도 못 골랐다 — 컴파일된 저장소가 있는지 확인하라"
    print(f"■ {SPLIT_NAME} · 정리 {len(jobs)} · 프로젝트 "
          f"{len({j[0] for j in jobs})} · 병렬 {JOBS}", flush=True)
    S = collections.defaultdict(collections.Counter); nrec = 0
    with open(OUT, "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for n, recs in enumerate(ex.map(run, jobs)):
            for r in recs:
                nrec += 1
                if r["local"]:
                    S[r["proj"]]["지역"] += 1; continue
                S[r["proj"]]["지점"] += 1
                S[r["proj"]]["생존"] += bool(r["ap"] or r["in"] or r["rw"])
                fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            if (n+1) % 10 == 0:
                print(f"   … {n+1}/{len(jobs)} · 기록 {nrec}", flush=True)
            fo.flush()
    print(f"\n■ 프로젝트별 gold 생존 (실제 파이프라인 · 지역변수 인자 제외)")
    print(f"   {'프로젝트':24s}{'지점':>7s}{'생존':>9s}{'지역제외':>9s}")
    tot = collections.Counter()
    for p, c in sorted(S.items(), key=lambda x: -x[1]["지점"]):
        n = max(1, c["지점"])
        print(f"   {p:24s}{c['지점']:7d}{c['생존']/n*100:8.1f}%{c['지역']:9d}")
        tot["지점"] += c["지점"]; tot["생존"] += c["생존"]; tot["지역"] += c["지역"]
    n = max(1, tot["지점"])
    print(f"   {'—— 합계':24s}{tot['지점']:7d}{tot['생존']/n*100:8.1f}%{tot['지역']:9d}")
