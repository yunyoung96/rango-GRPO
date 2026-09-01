#!/usr/bin/env python3
"""★ **무엇이 막고 있나** — 판별트리가 정답을 놓치는 자리의 상수를 실측한다.

지점마다 정답 lemma 를 직접 주고 `applic_why` 를 돌린다. 나오는 것:

    WHY <이름> ok depth=<d> goalhead=<H1> lemhead=<H2> dn=<0|1>

`dn=0` 이면 트리가 그 후보를 안 돌려준 것이고, 그때 `H1 ≠ H2` 면
**둘 중 하나가 펼쳐져야 하는 상수**다. 그것만 투명으로 넣으면
`None`(전부 투명, 40배 느림) 없이 재현율을 되찾는다.
Coq 의 `Hint Unfold` · Lean 의 `@[reducible]` 과 같은 자리다.

사용: python3 scripts/dn_why.py
"""
import concurrent.futures as cf
import signal
import collections, json, os, re, subprocess, sys, tempfile, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split as CSSplit, get_theorem
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc

N       = 200
JOBS    = 3
TIMEOUT = 1800
MAX_PT  = 3
OUT     = "all_log/dn_why.jsonl"
CC      = "CoqStoq/test-repos/compcert"
PLUG    = os.path.abspath("ocaml/applic")

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
# ★ OCaml 문자열 줄바꿈이 **공백을 남긴다**. 필드 사이를 `\s+` 로 둔다 —
#   단일 공백으로 짜면 조용히 0 지점이 된다(실측으로 두 번 당했다).
WHY = re.compile(r"CHECK\s+ver=(\S+)\s+(\S+)\s+ap=(\d)\s+in=(\d)\s+rw=(\d)\s+dnA=(\d)\s+"
                 r"dnR=(\d)\s+indexed=(\d)\s+sides=(-?\d+)\s+headm=(\d)\s+unifm=(\d)\s+"
                 r"nap=(\d+)\s+nin=(\d+)\s+nrw=(\d+)\s+"
                 r"redex=(\d+)\s+raw=(\d+)\s+keypass=(\d+)\s+sec=([\d.]+)")

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

# ── ★ 시동 자가검사 ────────────────────────────────────────────────────────
#   이 세션에서 **조용한 0** 에 세 번 당했다:
#     ① OCaml 문자열 줄바꿈이 공백을 남겨 정규식이 안 맞음 → 전 지점 0
#     ② `capture_output` 을 `Popen` 에 넘겨 TypeError → 바깥 except 가 삼킴
#     ③ head_of_file 이 순진해서 200 중 183 을 버림
#   그래서 **실제 출력 표본**으로 정규식을 시동 시에 검사한다.
_SAMPLE_STAT = ("APPLIC_STAT ver=r9 cand=12652 pat=77060 build=0.593 hyps=1 redex=20 "
                "raw=32371 keypass=4812 apply=227 applyin=432 rewrite=275 sec=0.3114")
assert 'WHY' in globals() or True
_SAMPLE_CHECK = ("CHECK ver=r9 PTree.gso ap=1 in=1 rw=1 dnA=1 dnR=1 indexed=1 sides=0 "
                 "headm=1 unifm=1 nap=227 nin=432 nrw=275 redex=20 raw=32371 "
                 "keypass=4812 sec=0.322")

assert WHY.search(_SAMPLE_CHECK), "CHECK 정규식이 실제 출력과 어긋난다"


def head_by_pos(orig, thm):
    ln = getattr(getattr(thm, "theorem_start_pos", None), "line", None)
    if not ln: return None
    parts = orig.splitlines(keepends=True)
    return "".join(parts[:ln - 1]) if ln - 1 <= len(parts) else None

def run(job):
    i, path, head, thm_text, chunks, ks, golds = job
    body = ["Require Import Applic.", head, thm_text]; prev = 0
    for k in ks:
        body.append(chunks[prev]); body.append(f'idtac "@@@{k}".')
        body.append(f"try applic_check {golds[k]}.")
        # ★ **그 자리에서 실제 tactic 이 되기는 하는가.**
        #   재구성한 상태가 원본과 어긋나면 정답도 안 먹는다. 그러면 그건
        #   필터의 미검출이 아니라 **측정 장치의 문제**다. 분모를 가른다.
        _g = golds[k]
        body.append(
            f'first [ assert_succeeds (first [ eapply {_g} | apply {_g} '
            f'| erewrite {_g} | erewrite <- {_g} | rewrite {_g} | rewrite <- {_g} '
            f'| erewrite {_g} in * | erewrite <- {_g} in * '
            f'| match goal with H : _ |- _ => apply {_g} in H end '
            f'| match goal with H : _ |- _ => erewrite {_g} in H end ]); '
            f'idtac "REAL 1" | idtac "REAL 0" ].')
        prev = k
    body.append("Admitted.")
    d = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=d, delete=False) as f:
        f.write("\n".join(body) + "\n"); tmp = f.name
    try:
        p = _coqtop(["coqtop", "-q"] + ARGS, stdin=open(tmp), env=ENV,
                           capture_output=True, text=True, timeout=TIMEOUT)
        blocks = re.split(r"@@@(\d+)\s*", p.stdout or ""); recs = []
        for a in range(1, len(blocks) - 1, 2):
            k = int(blocks[a]); m = WHY.search(blocks[a + 1])
            if not m: continue
            g = m.groups()
            assert len(g) == 18, g
            _r = re.search(r"(?m)^REAL (\d)", blocks[a + 1])
            recs.append({"idx": i, "k": k, "ver": g[0], "name": g[1],
                         "ap": int(g[2]), "in": int(g[3]), "rw": int(g[4]),
                         "dnA": int(g[5]), "dnR": int(g[6]), "indexed": int(g[7]),
                         "sides": int(g[8]), "headm": int(g[9]), "unifm": int(g[10]),
                         "nap": int(g[11]), "nin": int(g[12]), "nrw": int(g[13]),
                         "redex": int(g[14]), "raw": int(g[15]),
                         "keypass": int(g[16]), "sec": float(g[17]),
                         "real": int(_r.group(1)) if _r else None})
        return i, recs, None
    except subprocess.TimeoutExpired: return i, [], "timeout"
    except Exception as e: return i, [], str(e)[:120]
    finally:
        b = os.path.splitext(tmp)[0]
        for e in (".v", ".vo", ".vok", ".vos", ".glob"):
            try: os.unlink(b + e)
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
        jobs.append((i, path, head, proof.theorem.term.text, chunks, ks, golds))
    jobs.sort(key=lambda j: len(open(j[1], errors="ignore").read()))
    assert jobs, "정리를 하나도 못 골랐다 — head_by_pos/필터를 의심하라"
    print(f"■ 정리 {len(jobs)} · 병렬 {JOBS}", flush=True)
    _first_ok = False
    S = collections.Counter(); BLOCK = collections.Counter()
    with open(OUT, "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for n, (i, recs, err) in enumerate(ex.map(run, jobs)):
            for r in recs:
                S["지점"] += 1
                fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            if recs: _first_ok = True
            # ★ 앞 10개 정리에서 한 지점도 못 얻으면 배선이 깨진 것이다 — 즉시 멈춘다.
            assert not (n >= 9 and not _first_ok), \
                "정리 10개를 돌았는데 지점이 0 — 플러그인 출력/정규식을 확인하라"
            if (n+1) % 20 == 0: print(f"   … {n+1}/{len(jobs)} · 지점 {S['지점']}", flush=True)
            fo.flush()
    nn = max(S["지점"], 1)
    print(f"\n■ 트리가 왜 놓치나 ({S['지점']} 지점)")
    print("   (요약은 dn_why 분석기로)")
