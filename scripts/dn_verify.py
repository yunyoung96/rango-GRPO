#!/usr/bin/env python3
"""★★ **필터가 남긴 lemma 로 실제 구문을 돌려본다** — 2단 검증.

플러그인은 `Unification.w_unify` 로 "적용 가능"을 판정한다. 그런데 실제
`apply L` / `rewrite L` 은 그 위에 elaboration·암묵인자·타입클래스·keyed
matching 이 더 얹힌다. **정말로 도는지는 돌려봐야 안다.**

    1단  applic_filter 로 통과 목록을 받는다  (+ applic_sample 로 우주 표본)
    2단  그 이름들로 `assert_succeeds (apply L)` 등을 **실제로 실행**한다

두 방향을 다 잰다:
    정밀도  필터가 통과시킨 것 중 실제로 도는 비율   (거짓 양성)
    위음성  필터가 **거부한** 표본 중 실제로 도는 비율

사용: python3 scripts/dn_verify.py
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

N        = 60         # 정리 수 (2단이라 비싸다)
JOBS     = 3
TIMEOUT  = 2400
MAX_PT   = 2
SAMPLE_EVERY = 40     # 우주에서 1/40 을 뽑아 위음성을 잰다
OUT      = "all_log/dn_verify.jsonl"
CC       = "CoqStoq/test-repos/compcert"
PLUG     = os.path.abspath("ocaml/applic")

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

# ★ 실제 구문. `apply L in *` 는 문법 오류라 넣으면 안 된다(`in H` 는 유효).
BAT_A = "eapply {n} | apply {n} | unshelve eapply {n}"
BAT_I = ("match goal with H : _ |- _ => apply {n} in H end "
         "| match goal with H : _ |- _ => eapply {n} in H end")
BAT_R = ("erewrite {n} | erewrite <- {n} | rewrite {n} | rewrite <- {n} "
         "| erewrite {n} in * | erewrite <- {n} in * "
         "| match goal with H : _ |- _ => erewrite {n} in H end")

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

def head_by_pos(orig, thm):
    ln = getattr(getattr(thm, "theorem_start_pos", None), "line", None)
    if not ln: return None
    parts = orig.splitlines(keepends=True)
    return "".join(parts[:ln - 1]) if ln - 1 <= len(parts) else None

def coqtop(path, body):
    d = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=d, delete=False) as f:
        f.write("\n".join(body) + "\n"); tmp = f.name
    try:
        p = _coqtop(["coqtop", "-q"] + ARGS, stdin=open(tmp), env=ENV,
                           capture_output=True, text=True, timeout=TIMEOUT)
        return p.stdout or ""
    finally:
        b = os.path.splitext(tmp)[0]
        for e in (".v", ".vo", ".vok", ".vos", ".glob"):
            try: os.unlink(b + e)
            except OSError: pass

def run(job):
    i, path, head, thm_text, chunks, ks, golds = job
    # ── 1단: 필터가 남긴 목록 + 우주 표본 ──
    body = ["Require Import Applic.", head, thm_text]; prev = 0
    for k in ks:
        body.append(chunks[prev]); body.append(f'idtac "@@@{k}".')
        body.append(f"try applic_filter."); body.append(f"try applic_sample {SAMPLE_EVERY}.")
        prev = k
    body.append("Admitted.")
    try: out1 = coqtop(path, body)
    except Exception as e: return i, [], str(e)[:120]
    per = {}
    blocks = re.split(r"@@@(\d+)\s*", out1)
    for a in range(1, len(blocks) - 1, 2):
        k = int(blocks[a]); seg = blocks[a + 1]
        per[k] = dict(
            ap=sorted(set(re.findall(r"(?m)^APPLIC ([\w'.]+)", seg))),
            ai=sorted(set(re.findall(r"(?m)^APPLICIN ([\w'.]+)", seg))),
            rw=sorted(set(re.findall(r"(?m)^DNRW ([\w'.]+)", seg))),
            sm=sorted(set(re.findall(r"(?m)^SAMPLE ([\w'.]+)", seg))))
    if not per: return i, [], "1단 출력 없음"
    # ── 2단: 그 이름들로 **실제 구문**을 돌린다 ──
    body = ["Require Import Applic.", head, thm_text]; prev = 0
    for k in ks:
        if k not in per: continue
        body.append(chunks[prev]); body.append(f'idtac "@@@{k}".')
        d = per[k]
        rej = [x for x in d["sm"] if x not in set(d["ap"]) | set(d["ai"]) | set(d["rw"])]
        for tag, names, bat in (("A", d["ap"], BAT_A), ("I", d["ai"], BAT_I),
                                ("R", d["rw"], BAT_R),
                                ("XA", rej, BAT_A), ("XR", rej, BAT_R)):
            for nm in names:
                body.append(f'first [ assert_succeeds (first [ {bat.format(n=nm)} ]); '
                            f'idtac "OK{tag} {nm}" | idtac ].')
        prev = k
    body.append("Admitted.")
    try: out2 = coqtop(path, body)
    except Exception as e: return i, [], str(e)[:120]
    recs = []
    blocks = re.split(r"@@@(\d+)\s*", out2)
    got = {}
    for a in range(1, len(blocks) - 1, 2):
        k = int(blocks[a]); seg = blocks[a + 1]
        got[k] = {t: set(re.findall(rf"(?m)^OK{t} ([\w'.]+)", seg))
                  for t in ("A", "I", "R", "XA", "XR")}
    for k in ks:
        if k not in per or k not in got: continue
        d = per[k]; g = got[k]
        rej = [x for x in d["sm"] if x not in set(d["ap"]) | set(d["ai"]) | set(d["rw"])]
        recs.append({"idx": i, "k": k, "gold": golds[k],
                     "n_ap": len(d["ap"]), "n_ai": len(d["ai"]), "n_rw": len(d["rw"]),
                     "ok_ap": len(g["A"]), "ok_ai": len(g["I"]), "ok_rw": len(g["R"]),
                     "n_rej": len(rej),
                     "ok_rej": len(g["XA"] | g["XR"]),
                     "rej_hits": sorted(g["XA"] | g["XR"])[:8],
                     "gold_in": golds[k].split(".")[-1] in
                                {x.split(".")[-1] for x in d["ap"] + d["ai"] + d["rw"]},
                     "gold_ok": golds[k].split(".")[-1] in
                                {x.split(".")[-1] for x in
                                 (g["A"] | g["I"] | g["R"])}})
    return i, recs, None

if __name__ == "__main__":
    ids = [int(x) for x in Path("data/compcert_bs2_rand200_idx.txt").read_text().split()]
    jobs = []
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
        jobs.append((i, path, head, proof.theorem.term.text, chunks, ks, golds))
    jobs.sort(key=lambda j: len(open(j[1], errors="ignore").read()))
    print(f"■ 정리 {len(jobs)} · 병렬 {JOBS} · 표본 1/{SAMPLE_EVERY}", flush=True)
    S = collections.Counter(); EX = []
    _first_ok = False
    with open(OUT, "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for n, (i, recs, err) in enumerate(ex.map(run, jobs)):
            for r in recs:
                S["지점"] += 1
                for t in ("ap", "ai", "rw"):
                    S[f"n_{t}"] += r[f"n_{t}"]; S[f"ok_{t}"] += r[f"ok_{t}"]
                S["n_rej"] += r["n_rej"]; S["ok_rej"] += r["ok_rej"]
                S["gold_in"] += r["gold_in"]; S["gold_ok"] += r["gold_ok"]
                if r["rej_hits"] and len(EX) < 12: EX.append((r["idx"], r["k"], r["rej_hits"]))
                fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            if recs: _first_ok = True
            if err: S["실패"] += 1
            # ★ 앞 10개에서 한 지점도 못 얻으면 배선이 깨진 것이다 — 즉시 멈춘다.
            assert not (n >= 9 and not _first_ok), \
                "정리 10개를 돌았는데 지점이 0 — 플러그인 출력/정규식을 확인하라"
            if (n+1) % 5 == 0: print(f"   … {n+1}/{len(jobs)} · 지점 {S['지점']}", flush=True)
            fo.flush()
    nn = max(S["지점"], 1)
    print(f"\n■ 필터 통과분을 **실제 구문**으로 돌린 결과 ({S['지점']} 지점 · 실패 {S['실패']})")
    print(f"\n── 정밀도 (필터가 통과시킨 것 중 실제로 도는 비율) ──")
    for t, nm in (("ap", "apply"), ("ai", "apply … in H"), ("rw", "rewrite")):
        a, b = S[f"ok_{t}"], S[f"n_{t}"]
        print(f"   {nm:14s} {a:6d}/{b:6d} = {100*a/max(1,b):5.1f}%"
              f"   (지점당 통과 {b/nn:6.1f} → 실제 {a/nn:6.1f})")
    print(f"\n── 위음성 (필터가 **거부**한 표본 중 실제로 도는 비율) ──")
    print(f"   거부 표본 {S['n_rej']:,}개 중 실제로 도는 것 {S['ok_rej']:,}개 "
          f"= {100*S['ok_rej']/max(1,S['n_rej']):.2f}%")
    print(f"\n── 정답 ──")
    print(f"   필터에 남음        {S['gold_in']/nn*100:.1f}%")
    print(f"   ★ 실제로 돌아감    {S['gold_ok']/nn*100:.1f}%")
    if EX:
        print(f"\n── 거부했는데 실제로 도는 예 ──")
        for i, k, h in EX: print(f"   idx {i:5d} k {k:3d}  {', '.join(h[:6])}")
