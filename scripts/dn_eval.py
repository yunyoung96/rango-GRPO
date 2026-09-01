#!/usr/bin/env python3
"""★★★ **OCaml 플러그인 평가** — 판별트리 + 커널 단일화 vs 지금까지의 모든 방법.

`ocaml/applic` 플러그인이 하는 일:
    · `Environ.fold_constants` 로 **환경 전체**를 훑는다 (후보 목록을 밖에서 안 받는다)
    · `Btermdn` (Coq 자신의 판별트리) 로 redex 후보를 좁힌다 — **커널 항 위에서**
    · `Unification.w_unify` 로 확정한다
    · `shortest_qualid_of_global` 로 **그 지점에서 유효한 이름**을 낸다

비교 대상:
    Coq Search(w8)   재현 96.5% · 후보 5,973 · 2.0s
    assert_succeeds  후보 목록 필요 · 후보당 0.11ms
    이 플러그인      환경 전체 · 후보당 ~3µs

사용: python3 scripts/dn_eval.py
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

# ── 설정은 파이썬 변수다 ──
N       = 200
JOBS    = 3
TIMEOUT = 1200
MAX_PT  = 3
OUT     = "all_log/dn_eval.jsonl"
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
_SAMPLE_CHECK = ("CHECK ver=r9 PTree.gso ap=1 in=1 rw=1 dnA=1 dnR=1 indexed=1        "
                 "          nap=227 nin=432 nrw=275 redex=20 raw=32371 "
                 "keypass=4812 sec=0.307")

assert re.search(r"APPLIC_STAT\s+ver=(\S+)\s+cand=(\d+)", _SAMPLE_STAT)


def head_by_pos(orig, thm):
    ln = getattr(getattr(thm, "theorem_start_pos", None), "line", None)
    if not ln: return None
    parts = orig.splitlines(keepends=True)
    return "".join(parts[:ln - 1]) if ln - 1 <= len(parts) else None

def run(job):
    i, path, head, thm_text, chunks, ks, golds = job
    body = ["Require Import Applic.", head, thm_text]; prev = 0
    for k in ks:
        body.append(chunks[prev])
        body.append(f'idtac "@@@{k}".')
        # ★ 정답 이름을 플러그인과 **같은 함수**로 정규화해 둔다 (별칭 대응)
        body.append(f'ApplicCanon {golds[k]}.')
        body.append("try applic_filter.")   # 세 색인을 한 번에
        prev = k
    body.append("Admitted.")
    d = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=d, delete=False) as f:
        f.write("\n".join(body) + "\n"); tmp = f.name
    try:
        t0 = time.time()
        p = _coqtop(["coqtop", "-q"] + ARGS, stdin=open(tmp), env=ENV,
                           capture_output=True, text=True, timeout=TIMEOUT)
        dt = time.time() - t0
        out = p.stdout or ""
        blocks = re.split(r"@@@(\d+)\s*", out); recs = []
        for a in range(1, len(blocks) - 1, 2):
            k = int(blocks[a]); seg = blocks[a + 1]
            cn = re.search(r"(?m)^CANON \S+ -> (\S+)", seg)
            rw = re.findall(r"(?m)^DNRW ([\w'.]+)", seg)
            ap = re.findall(r"(?m)^APPLIC ([\w'.]+)", seg)
            apin = re.findall(r"(?m)^APPLICIN ([\w'.]+)", seg)
            ds = re.search(r"APPLIC_STAT\s+ver=(\S+)\s+cand=(\d+)\s+pat=(\d+)\s+build=([\d.]+)\s+"
                           r"hyps=(\d+)\s+redex=(\d+)\s+raw=(\d+)\s+keypass=(\d+)\s+apply=(\d+)\s+"
                           r"applyin=(\d+)\s+rewrite=(\d+)\s+sec=([\d.]+)", seg)
            asx = ds
            recs.append({"idx": i, "k": k, "sec": dt,
                         "rw": sorted(set(rw)), "ap": sorted(set(ap)),
                         "apin": sorted(set(apin)),
                         "canon": cn.group(1) if cn else None,
                         "ver": ds.group(1), "nconst": int(ds.group(2)) if ds else None,
                         "dn_build": float(ds.group(4)) if ds else None,
                         "dn_raw": int(ds.group(7)) if ds else None,
                         "dn_sec": float(ds.group(12)) if ds else None,
                         "ap_scanned": int(ds.group(2)) if ds else None,
                         "ap_sec": float(ds.group(12)) if ds else None})
        return i, recs, None if recs else (p.stderr or out)[-200:]
    except subprocess.TimeoutExpired: return i, [], "timeout"
    except Exception as e: return i, [], str(e)[:120]
    finally:
        b = os.path.splitext(tmp)[0]
        for e in (".v", ".vo", ".vok", ".vos", ".glob"):
            try: os.unlink(b + e)
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
        for k in ks:
            meta[(i, k)] = dict(gold=NAMED.search(proof.steps[k].step.text).group(1),
                                tac=("rewrite" if HEADT.match(proof.steps[k].step.text)
                                     .group(1).endswith("rewrite") else "apply"))
        jobs.append((i, path, head, proof.theorem.term.text, chunks, ks,
                     {k: NAMED.search(proof.steps[k].step.text).group(1) for k in ks}))
    jobs.sort(key=lambda j: len(open(j[1], errors="ignore").read()))
    print(f"■ 정리 {len(jobs)} · 지점 {len(meta)} · 병렬 {JOBS}", flush=True)
    S = collections.Counter(); C = collections.defaultdict(list)
    _first_ok = False
    with open(OUT, "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for n, (i, recs, err) in enumerate(ex.map(run, jobs)):
            for r in recs:
                m = meta.get((r["idx"], r["k"]))
                if not m: continue
                g = m["gold"]; gb = g.split(".")[-1]
                cn = r.get("canon"); cb = cn.split(".")[-1] if cn else None
                def has(lst):
                    return any(x == g or x.split(".")[-1] == gb
                               or (cn and (x == cn or x.split(".")[-1] == cb))
                               for x in lst)
                hrw, hap, hin = has(r["rw"]), has(r["ap"]), has(r.get("apin", []))
                hap = hap or hin
                S["지점"] += 1
                S["rw적중"] += hrw; S["ap적중"] += hap; S["합집합적중"] += (hrw or hap)
                S["in적중"] += hin
                C["apin"].append(len(r.get("apin", [])))
                S[f"{m['tac']}지점"] += 1
                S[f"{m['tac']}적중"] += (hrw or hap)
                C["rw"].append(len(r["rw"])); C["ap"].append(len(r["ap"]))
                C["union"].append(len(set(r["rw"]) | set(r["ap"]) | set(r.get("apin", []))))
                if r["dn_sec"] is not None: C["dn_sec"].append(r["dn_sec"])
                if r["ap_sec"] is not None: C["ap_sec"].append(r["ap_sec"])
                if r["nconst"]: C["nconst"].append(r["nconst"])
                r.update(gold=g, tac=m["tac"], hit_rw=hrw, hit_ap=hap)
                fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            if recs: _first_ok = True
            if err: S["실패"] += 1
            # ★ 앞 10개에서 한 지점도 못 얻으면 배선이 깨진 것이다 — 즉시 멈춘다.
            assert not (n >= 9 and not _first_ok), \
                "정리 10개를 돌았는데 지점이 0 — 플러그인 출력/정규식을 확인하라"
            if (n+1) % 10 == 0:
                print(f"   … {n+1}/{len(jobs)} · 지점 {S['지점']} · 적중 {S['합집합적중']}", flush=True)
            fo.flush()
    import statistics as st
    nn = max(S["지점"], 1)
    def dist(v):
        v = sorted(v)
        if not v: return "—"
        q = lambda p: v[min(len(v)-1, int(p*len(v)))]
        return (f"중앙 {st.median(v):,.0f} · p25 {q(.25):,.0f} · p75 {q(.75):,.0f} "
                f"· p90 {q(.90):,.0f} · max {max(v):,.0f}")
    U = C["union"]; NC = C["nconst"]
    base = st.median(NC) if NC else 0
    print(f"\n■ OCaml 플러그인 (CompCert {S['지점']} 지점 · 실패 {S['실패']})")
    print(f"\n── ① 필터링 비율 ──")
    print(f"   후보 우주 (환경 전체)   {base:,.0f}개")
    print(f"   필터 통과              {dist(U)}")
    if U and base:
        rat = sorted(100.0*u/base for u in U)
        red = sorted(base/max(1,u) for u in U)
        print(f"   남는 비율              중앙 {st.median(rat):.2f}%  "
              f"· p25 {rat[len(rat)//4]:.2f}%  · p90 {rat[int(.9*len(rat))]:.2f}%")
        print(f"   축소 배수              중앙 {st.median(red):,.0f}배 "
              f"· p25 {red[len(red)//4]:,.0f}배 · p75 {red[3*len(red)//4]:,.0f}배")
    print(f"\n── ② 정답(gold) 포함률 ──")
    print(f"   ★ 전체                 {S['합집합적중']/nn*100:.1f}%")
    print(f"       · apply 경로       {S['ap적중']/nn*100:.1f}%")
    print(f"       · rewrite 경로     {S['rw적중']/nn*100:.1f}%")
    print(f"       · 전방추론 경로     {S['in적중']/nn*100:.1f}%")
    for tc in ("apply", "rewrite"):
        n2 = max(S[f"{tc}지점"], 1)
        print(f"   · gold tactic {tc:8s} {S[f'{tc}지점']:4d}지점 → {S[f'{tc}적중']/n2*100:5.1f}%")
    print(f"\n── ③ 남는 적용 가능한 lemma/axiom 개수 (지점마다 다르다) ──")
    print(f"   apply    로 적용 가능   {dist(C['ap'])}")
    print(f"   apply…in H (전방추론)   {dist(C['apin'])}")
    print(f"   rewrite  로 적용 가능   {dist(C['rw'])}")
    print(f"   합집합                 {dist(U)}")
    print(f"\n── ④ 비용 ──")
    print(f"   색인 구축 (파일당 1회)  {st.median(C['dn_build'])if C['dn_build'] else 0:.2f}s")
    print(f"   지점당 질의            {dist([x*1000 for x in C['dn_sec']])} ms")
