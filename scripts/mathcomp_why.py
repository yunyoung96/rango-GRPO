#!/usr/bin/env python3
"""★ mathcomp 계열에서 필터가 **어디서** 끊기는지 — `applic_check` 진단 필드로 본다.

실측(r11 VAL/TEST): coqeal apply 0% · graph-theory apply 14% · reglang rewrite 61%.
나머지 프로젝트는 73~100% 다. 즉 **mathcomp 만 무너진다.**

CHECK 가 주는 것:
    indexed  후보가 색인에 **들어가긴 했나** (0이면 index_cand 가 못 넣은 것)
    dnA/dnR  판별트리가 그 후보를 **돌려줬나** (0이면 트리가 거른 것)
    headm    머리 기호가 맞나
    unifm    커널 단일화가 됐나
    sides    rewrite 라면 좌(0)/우(1)/못찾음(-1)

사용: python3 scripts/mathcomp_why.py [프로젝트...]
"""
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

WANT = set(sys.argv[1:]) or {"graph-theory", "coqeal"}
PLUG = os.path.abspath("ocaml/applic")
PER_PROJ = 12
MAX_PT = 3
TIMEOUT = 1800
OUT = "all_log/mathcomp_why.jsonl"

_SPLIT = {"graph-theory": Split.VAL, "coqeal": Split.VAL, "bertrand": Split.VAL,
          "reglang": Split.TEST, "fourcolor": Split.TEST}
_DIRV = {Split.VAL: ("val-repos", "raw-data/coqstoq-val",
                     "raw-data/coqstoq-val/coqstoq-val-sentences.db"),
         Split.TEST: ("test-repos", "raw-data/coqstoq-test",
                      "raw-data/coqstoq-test/coqstoq-test-sentences.db")}

NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
# ★ 전 필드를 잡는다 — `ver` 는 비캡처(그룹이 밀리면 조용한 0이 된다)
CHK = re.compile(r"CHECK\s+ver=\S+\s+(\S+)\s+ap=(\d)\s+in=(\d)\s+rw=(\d)\s+dnA=(\d)\s+"
                 r"dnR=(\d)\s+indexed=(\d)\s+sides=(-?\d+)\s+headm=(\d)\s+unifm=(\d)")
assert CHK.search("CHECK ver=r11 x ap=0 in=0 rw=0 dnA=0 dnR=0 indexed=1 sides=-1 "
                  "headm=0 unifm=0 nap=1 nin=2 nrw=3 redex=4 raw=5 keypass=6 sec=0.1")


assert WANT, "프로젝트를 하나도 안 줬다"
for _p in WANT:
    assert _p in _SPLIT, f"스플릿을 모르는 프로젝트: {_p}"
assert PER_PROJ > 0 and MAX_PT > 0


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
    return out


def proj_args(pdir):
    cp = os.path.join(pdir, "_CoqProject")
    args = []
    if os.path.exists(cp):
        t = open(cp).read().split(); i = 0
        while i < len(t):
            if t[i] in ("-R", "-Q"):
                args += [t[i], os.path.abspath(os.path.join(pdir, t[i+1])), t[i+2]]; i += 3
            elif t[i] in ("-arg",): i += 2
            else: i += 1
    if not args: args = ["-R", os.path.abspath(pdir), "Top"]
    return args + ["-R", PLUG, "Applic", "-I", PLUG]


def head_by_pos(orig, thm):
    ln = getattr(getattr(thm, "theorem_start_pos", None), "line", None)
    if not ln: return None
    parts = orig.splitlines(keepends=True)
    return "".join(parts[:ln - 1]) if ln - 1 <= len(parts) else None


if __name__ == "__main__":
    env = dict(os.environ)
    env["OCAMLPATH"] = os.path.join(PLUG, "findlib") + ":" + env.get("OCAMLPATH", "")
    rows = []
    for proj in sorted(WANT):
        sp = _SPLIT.get(proj)
        if sp is None: print(f"  {proj}: 스플릿 모름"); continue
        dirn, dataloc, sdbloc = _DIRV[sp]
        pdir = os.path.join("CoqStoq", dirn, proj)
        if not os.path.isdir(pdir): print(f"  {proj}: 디렉토리 없음"); continue
        sdb = SentenceDB.load(Path(sdbloc))
        thms = [t for t in get_theorem_list(sp, Path("CoqStoq"))
                if str(t.project.dir_name) == proj]
        got = 0
        for thm in thms:
            if got >= PER_PROJ: break
            try:
                d = get_thm_desc(thm, Path(dataloc), sdb)
                if d is None: continue
                proof = d.dp.proofs[d.idx]
                path = os.path.join(pdir, str(thm.path))
                orig = open(path, errors="ignore").read()
                head = head_by_pos(orig, thm)
            except Exception: continue
            if head is None: continue
            ks = [k for k, s in enumerate(proof.steps)
                  if HEADT.match(s.step.text or "")
                  and HEADT.match(s.step.text).group(1) in
                     ("apply", "eapply", "rewrite", "erewrite")
                  and NAMED.search(s.step.text or "") and s.goals]
            if not ks: continue
            if len(ks) > MAX_PT:
                st = len(ks) / MAX_PT; ks = [ks[int(x*st)] for x in range(MAX_PT)]
            steps = [s.step.text for s in proof.steps]
            body = ["Require Import Applic.", head, proof.theorem.term.text]
            prev = 0; golds = {}
            for k in ks:
                body.append("".join(steps[prev:k])); prev = k
                golds[k] = NAMED.search(proof.steps[k].step.text).group(1)
                body.append(f'idtac "@@@{k}".')
                body.append(f"try applic_check {golds[k]}.")
            body.append("Admitted.")
            dd = os.path.dirname(os.path.abspath(path))
            with tempfile.NamedTemporaryFile("w", suffix=".v", dir=dd, delete=False) as f:
                f.write("\n".join(body) + "\n"); tmp = f.name
            try:
                out = _coqtop(["coqtop", "-q"] + proj_args(pdir), stdin=open(tmp),
                              env=env, timeout=TIMEOUT)
            except Exception:
                out = ""
            finally:
                b = os.path.splitext(tmp)[0]
                for e in (".v", ".vo", ".vok", ".vos", ".glob"):
                    try: os.unlink(b + e)
                    except OSError: pass
            blocks = re.split(r"@@@(\d+)\s*", out)
            for a in range(1, len(blocks) - 1, 2):
                k = int(blocks[a]); m = CHK.search(blocks[a + 1])
                if not m: continue
                g = m.groups()
                _h = HEADT.match(proof.steps[k].step.text or "")
                rows.append({"proj": proj, "k": k, "gold": g[0],
                             "tac": (_h.group(1) if _h else "?"),
                             "ap": int(g[1]), "in": int(g[2]), "rw": int(g[3]),
                             "dnA": int(g[4]), "dnR": int(g[5]),
                             "indexed": int(g[6]), "sides": int(g[7]),
                             "headm": int(g[8]), "unifm": int(g[9])})
            got += 1
            print(f"   {proj} {got}/{PER_PROJ} · 누적 {len(rows)}", flush=True)
    with open(OUT, "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    assert rows, "지점을 하나도 못 모았다"
    for _r in rows:
        assert _r["indexed"] in (0, 1) and _r["dnA"] in (0, 1)
        assert _r["sides"] in (-1, 0, 1), f"sides 값이 이상하다: {_r['sides']}"
    print(f"\n■ 어디서 끊기나 ({len(rows)}지점)")
    C = collections.Counter()
    for r in rows:
        if r["ap"] or r["in"] or r["rw"]: C["① 통과"] += 1
        elif not r["indexed"]:            C["② 색인에 없음 (index_cand 실패)"] += 1
        elif not (r["dnA"] or r["dnR"]):  C["③ 트리가 안 돌려줌 (구문 불일치)"] += 1
        elif not r["headm"]:              C["④ 머리 불일치"] += 1
        elif not r["unifm"]:              C["⑤ 커널 단일화 실패"] += 1
        else:                             C["⑥ 기타"] += 1
    for k, v in C.most_common():
        print(f"   {k:34s}{v:4d}  {v/len(rows)*100:5.1f}%")
    print("\n■ 실패 예시")
    n = 0
    for r in rows:
        if r["ap"] or r["in"] or r["rw"]: continue
        print(f"   {r['proj'][:13]:14s}{r['tac']:9s}{r['gold']:24s}"
              f"indexed={r['indexed']} dnA={r['dnA']} dnR={r['dnR']} "
              f"sides={r['sides']} headm={r['headm']} unifm={r['unifm']}")
        n += 1
        if n >= 20: break
    print("MATHCOMP_WHY_DONE", flush=True)
