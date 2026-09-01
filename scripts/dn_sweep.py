#!/usr/bin/env python3
"""★ 플러그인 설정 A/B — **같은 지점**에서 네 조합을 짝지어 잰다.

    rigid   판별트리의 TransparentState
              1 = Some empty (전부 경직) — 좁고 빠르다. delta 변환이 필요한 매칭을 놓친다
              0 = None       (정보 없음) — 넓지만 완전에 가깝다
    exact   검증 깊이
              1 = 트리가 알려준 깊이만 확인 (빠름)
              0 = 모든 화살표 접미사 재확인 (느리지만 완전)

한 .v 파일 안에서 네 조합을 순서대로 돌리므로 상태가 동일하고 Coq 기동이 1회다.
사용: python3 scripts/dn_sweep.py
"""
import concurrent.futures as cf
import signal
import collections, json, os, re, subprocess, sys, tempfile, time, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split as CSSplit, get_theorem
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc

N       = 40          # 정리 수 (짝비교라 적어도 된다)
JOBS    = 4
TIMEOUT = 2400
MAX_PT  = 2
OUT     = "all_log/dn_sweep.jsonl"
CC      = "CoqStoq/test-repos/compcert"
PLUG    = os.path.abspath("ocaml/applic")
CONFIGS = [("R1E1", 1, 1), ("R0E1", 0, 1), ("R1E0", 1, 0), ("R0E0", 0, 0)]

t = open(os.path.join(CC, "_CoqProject")).read().split(); ARGS = []; _i = 0
while _i < len(t):
    if t[_i] in ("-R", "-Q"):
        ARGS += [t[_i], os.path.abspath(os.path.join(CC, t[_i+1])), t[_i+2]]; _i += 3
    else: _i += 1
ARGS += ["-R", PLUG, "Applic", "-I", PLUG]
ENV = dict(os.environ); ENV["OCAMLPATH"] = os.path.join(PLUG, "findlib") + ":" + ENV.get("OCAMLPATH", "")

sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))
NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")
STAT = re.compile(r"APPLIC_STAT\s+cand=(\d+) pat=(\d+) build=([\d.]+) hyps=(\d+) "
                  r"redex=(\d+) raw=(\d+) apply=(\d+) applyin=(\d+) rewrite=(\d+) sec=([\d.]+)")

def _coqtop(cmd, stdin=None, env=None, timeout=None, **kw):
    """★ coqtop 을 **자기 프로세스 그룹**으로 띄운다.

    예전 판은 `subprocess.run` 을 그냥 썼는데, 파이썬 드라이버를 죽이면
    자식 coqtop 이 **살아남아** 기계를 포화시켰다(실측: 좀비 17개, 일부
    12시간·RSS 116GB). 그룹으로 묶어 timeout 때 그룹째 죽인다."""
    import subprocess as _sp
    # ★ 호출부가 `subprocess.run` 관례로 넘기는 인자는 여기서 걷어낸다.
    #   `Popen` 은 `capture_output` 을 모른다 — 넘기면 TypeError 가 나고
    #   바깥 `except` 에 먹혀 **모든 지점이 조용히 0** 이 된다(실측으로 당했다).
    kw.pop("capture_output", None); kw.pop("text", None)
    p = _sp.Popen(cmd, stdin=stdin, stdout=_sp.PIPE, stderr=_sp.PIPE,
                  text=True, env=env, start_new_session=True, **kw)
    try:
        out, err = p.communicate(timeout=timeout)
    except _sp.TimeoutExpired:
        try: os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except Exception: pass
        p.wait()
        raise
    return _sp.CompletedProcess(cmd, p.returncode, out, err)

def head_by_pos(orig, thm):
    ln = getattr(getattr(thm, "theorem_start_pos", None), "line", None)
    if not ln: return None
    parts = orig.splitlines(keepends=True)
    return "".join(parts[:ln - 1]) if ln - 1 <= len(parts) else None

def run(job):
    i, path, head, thm_text, chunks, ks, golds = job
    body = ["Require Import Applic."]
    for tag, rg, ex in CONFIGS:
        body += [head, thm_text]
        body.append(f"ApplicRigid {rg}."); body.append(f"ApplicExact {ex}.")
        prev = 0
        for k in ks:
            body.append(chunks[prev])
            body.append(f'idtac "@@@{tag}#{k}".')
            body.append(f'ApplicCanon {golds[k]}.')
            body.append("try applic_filter.")
            prev = k
        body.append("Admitted.")
    d = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=d, delete=False) as f:
        f.write("\n".join(body) + "\n"); tmp = f.name
    try:
        p = _coqtop(["coqtop", "-q"] + ARGS, stdin=open(tmp), env=ENV,
                           capture_output=True, text=True, timeout=TIMEOUT)
        blocks = re.split(r"@@@(\w+)#(\d+)\s*", p.stdout or ""); recs = []
        for a in range(1, len(blocks) - 2, 3):
            tag, k, seg = blocks[a], int(blocks[a+1]), blocks[a+2]
            m = STAT.search(seg)
            cn = re.search(r"(?m)^CANON \S+ -> (\S+)", seg)
            recs.append({"idx": i, "k": k, "cfg": tag,
                         "ap": sorted(set(re.findall(r"(?m)^APPLIC ([\w'.]+)", seg))),
                         "apin": sorted(set(re.findall(r"(?m)^APPLICIN ([\w'.]+)", seg))),
                         "rw": sorted(set(re.findall(r"(?m)^DNRW ([\w'.]+)", seg))),
                         "canon": cn.group(1) if cn else None,
                         "cand": int(m.group(1)) if m else None,
                         "build": float(m.group(3)) if m else None,
                         "raw": int(m.group(6)) if m else None,
                         "sec": float(m.group(10)) if m else None})
        return i, recs, None if recs else (p.stderr or "")[-200:]
    except subprocess.TimeoutExpired: return i, [], "timeout"
    except Exception as e: return i, [], str(e)[:120]
    finally:
        b = os.path.splitext(tmp)[0]
        for e in (".v", ".vo", ".vok", ".vos", ".glob"):
            try: os.unlink(b + e)
            except OSError: pass

if __name__ == "__main__":
    ids = [int(x) for x in Path("data/compcert_bs2_rand200_idx.txt").read_text().split()]
    jobs, meta = [], {}
    for i in ids:
        if len(jobs) >= N: break
        try:
            thm = get_theorem(CSSplit.TEST, i, Path("CoqStoq"))
            d = get_thm_desc(thm, Path("raw-data/coqstoq-test"), sdb)
            if d is None: continue
            proof = d.dp.proofs[d.idx]
            path = os.path.join(CC, str(thm.path)); orig = open(path, errors="ignore").read()
            head = head_by_pos(orig, thm)
        except Exception: continue
        if head is None: continue
        ks = [k for k, s in enumerate(proof.steps)
              if HEADT.match(s.step.text or "")
              and HEADT.match(s.step.text).group(1) in ("apply","eapply","rewrite","erewrite")
              and NAMED.search(s.step.text or "") and s.goals]
        if not ks: continue
        if len(ks) > MAX_PT:
            stp = len(ks)/MAX_PT; ks = [ks[int(x*stp)] for x in range(MAX_PT)]
        steps = [s.step.text for s in proof.steps]
        chunks, prev = {}, 0
        for k in ks: chunks[prev] = "".join(steps[prev:k]); prev = k
        golds = {k: NAMED.search(proof.steps[k].step.text).group(1) for k in ks}
        for k in ks:
            meta[(i, k)] = dict(gold=golds[k],
                                tac=("rewrite" if HEADT.match(proof.steps[k].step.text)
                                     .group(1).endswith("rewrite") else "apply"))
        jobs.append((i, path, head, proof.theorem.term.text, chunks, ks, golds))
    jobs.sort(key=lambda j: len(open(j[1], errors="ignore").read()))
    print(f"■ 정리 {len(jobs)} · 지점 {len(meta)} · 조합 {len(CONFIGS)} · 병렬 {JOBS}", flush=True)
    R = collections.defaultdict(list)
    with open(OUT, "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for n, (i, recs, err) in enumerate(ex.map(run, jobs)):
            for r in recs:
                m = meta.get((r["idx"], r["k"]))
                if not m: continue
                g = m["gold"]; gb = g.split(".")[-1]
                cn = r.get("canon"); cb = cn.split(".")[-1] if cn else None
                def has(l): return any(x == g or x.split(".")[-1] == gb
                                       or (cn and (x == cn or x.split(".")[-1] == cb)) for x in l)
                r["hit_ap"] = has(r["ap"]); r["hit_in"] = has(r["apin"]); r["hit_rw"] = has(r["rw"])
                r["hit"] = r["hit_ap"] or r["hit_in"] or r["hit_rw"]
                r["gold"] = g; r["tac"] = m["tac"]
                r["n"] = len(set(r["ap"]) | set(r["apin"]) | set(r["rw"]))
                R[r["cfg"]].append(r); fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            if (n+1) % 5 == 0:
                print(f"   … {n+1}/{len(jobs)}", flush=True)
            fo.flush()
    import statistics as st
    print(f"\n{'조합':6s} {'지점':>5s} {'적중':>7s} {'ap':>6s} {'in':>6s} {'rw':>6s} "
          f"{'후보중앙':>8s} {'raw중앙':>8s} {'구축':>6s} {'질의':>7s}")
    for tag, _, _ in CONFIGS:
        rs = R[tag]
        if not rs: continue
        f = lambda k: 100*sum(r[k] for r in rs)/len(rs)
        print(f"{tag:6s} {len(rs):5d} {f('hit'):6.1f}% {f('hit_ap'):5.1f}% "
              f"{f('hit_in'):5.1f}% {f('hit_rw'):5.1f}% "
              f"{st.median([r['n'] for r in rs]):8.0f} "
              f"{st.median([r['raw'] or 0 for r in rs]):8.0f} "
              f"{st.median([r['build'] or 0 for r in rs]):5.2f}s "
              f"{st.median([r['sec'] or 0 for r in rs])*1000:6.0f}ms")
