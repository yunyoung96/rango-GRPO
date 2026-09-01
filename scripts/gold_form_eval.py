#!/usr/bin/env python3
"""★ **gold 위음성 해부** — gold 이 커널 검증을 왜 통과 못 하나.

밤 체인(av_top2000)에서 `gold 이 풀에 있는데 검증 통과 27.9% 실패` 가 나왔다.
gold 은 **정의상 그 지점에서 실제로 쓰인 lemma** 다. 즉 통과해야 정상이고,
못 통과하면 **배터리가 부족**하거나 **이름이 그 지점에서 안 풀린다**는 뜻이다.

그래서 gold 하나만 놓고 **형태별로 따로** 시험한다. 어떤 형태가 살리는지,
아무 형태도 안 되면 이름 자체가 안 풀리는지(RESOLVE)를 분리해서 본다.

사용: python3 scripts/gold_form_eval.py
"""
import concurrent.futures as cf
import collections, json, os, re, subprocess, sys, tempfile, time, yaml, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
sys.path.insert(0, "src"); sys.path.insert(0, "CoqStoq")
logging.disable(logging.CRITICAL)
from pathlib import Path
from coqstoq import Split as CSSplit, get_theorem
from data_management.sentence_db import SentenceDB
from evaluation.find_coqstoq_idx import get_thm_desc

# ── 설정은 파이썬 변수다 (환경변수 안 씀) ──
N        = 200
JOBS     = 4
TIMEOUT  = 900
MAX_PT   = 3
OUT      = "all_log/gold_form.jsonl"
CC       = "CoqStoq/test-repos/compcert"

t = open(os.path.join(CC, "_CoqProject")).read().split(); ARGS = []; _i = 0
while _i < len(t):
    if t[_i] in ("-R", "-Q"):
        ARGS += [t[_i], os.path.abspath(os.path.join(CC, t[_i+1])), t[_i+2]]; _i += 3
    else: _i += 1

sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))
NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")

# ── 시험할 형태들 — 하나씩 따로 판정한다 ──
#   `apply L in H` 는 **유효한 문법**이다(`in *` 만 apply 에서 문법 오류).
#   가설 순회는 `match goal` 의 역추적으로 한다.
FORMS = [
    ("eapply",      "eapply {n}"),
    ("apply",       "apply {n}"),
    ("erw",         "erewrite {n}"),
    ("erw_rev",     "erewrite <- {n}"),
    ("rw",          "rewrite {n}"),
    ("rw_rev",      "rewrite <- {n}"),
    ("erw_star",    "erewrite {n} in *"),
    ("erw_rev_star","erewrite <- {n} in *"),
    ("apply_in",    "match goal with H : _ |- _ => apply {n} in H end"),
    ("eapply_in",   "match goal with H : _ |- _ => eapply {n} in H end"),
    ("erw_in",      "match goal with H : _ |- _ => erewrite {n} in H end"),
    ("erw_rev_in",  "match goal with H : _ |- _ => erewrite <- {n} in H end"),
    ("unshelve",    "unshelve eapply {n}"),
    ("specialize",  "match goal with H : _ |- _ => specialize ({n} H) end"),
]

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
    i, path, thm_text, chunks, ks, golds = job
    try: orig = open(path, errors="ignore").read()
    except OSError: return i, [], "파일 없음"
    head = head_of_file(orig, thm_text)
    if head is None: return i, [], "정리 위치 못 찾음"
    body = [head, thm_text]; prev = 0
    for k in ks:
        body.append(chunks[prev]); body.append(f'idtac "@@@{k}".')
        n = golds[k]
        # 이름이 이 지점에서 풀리기는 하나
        body.append(f'first [ assert_succeeds (pose {n}); idtac "RESOLVE" | idtac ].')
        for tag, pat in FORMS:
            body.append(f'first [ assert_succeeds ({pat.format(n=n)}); '
                        f'idtac "OK {tag}" | idtac ].')
        prev = k
    body.append("Admitted.")
    d = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=d, delete=False) as f:
        f.write("\n".join(body) + "\n"); tmp = f.name
    try:
        p = subprocess.run(["coqc", "-q"] + ARGS + [tmp],
                           capture_output=True, text=True, timeout=TIMEOUT)
        out = p.stdout or ""
        blocks = re.split(r"@@@(\d+)\s*", out); recs = []
        for a in range(1, len(blocks) - 1, 2):
            k = int(blocks[a]); seg = blocks[a+1]
            recs.append({"idx": i, "k": k, "gold": golds[k],
                         "resolve": bool(re.search(r"(?m)^RESOLVE$", seg)),
                         "ok": re.findall(r"(?m)^OK (\w+)", seg)})
        return i, recs, None if recs else (p.stderr or "")[:200]
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
        except Exception: continue
        if head_of_file(orig, proof.theorem.term.text) is None: continue
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
        jobs.append((i, path, proof.theorem.term.text, chunks, ks, golds))
    jobs.sort(key=lambda j: len(open(j[1], errors="ignore").read()))
    print(f"■ 정리 {len(jobs)} · 병렬 {JOBS} · 형태 {len(FORMS)}종", flush=True)
    S = collections.Counter(); F = collections.Counter(); dead = []
    with open(OUT, "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for n, (i, recs, err) in enumerate(ex.map(run, jobs)):
            for r in recs:
                S["지점"] += 1
                S["이름풀림"] += r["resolve"]
                for tag in set(r["ok"]): F[tag] += 1
                if r["ok"]: S["하나라도통과"] += 1
                else: dead.append((r["idx"], r["k"], r["gold"], r["resolve"]))
                fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            if err: S["실패"] += 1
            if (n+1) % 20 == 0:
                print(f"   … {n+1}/{len(jobs)} · 지점 {S['지점']} · 통과 {S['하나라도통과']}", flush=True)
            fo.flush()
    nn = max(S["지점"], 1)
    print(f"\n■ gold 위음성 해부 (CompCert {S['지점']} 지점 · 실패 {S['실패']})")
    print(f"   이름이 풀린다            {S['이름풀림']/nn*100:.1f}%")
    print(f"   ★ 어떤 형태로든 통과     {S['하나라도통과']/nn*100:.1f}%")
    print(f"   ── 형태별 단독 통과율 ──")
    for tag, _ in FORMS:
        print(f"      {tag:14s} {F[tag]/nn*100:5.1f}%")
    # 누적: 현행 배터리 vs 확장 배터리
    cur = {"eapply","erw","erw_rev","erw_star","apply","rw"}
    import itertools
    rows = [json.loads(l) for l in open(OUT)]
    c1 = sum(1 for r in rows if set(r["ok"]) & cur)
    print(f"\n   현행 배터리(6종)  {c1/max(1,len(rows))*100:.1f}%")
    print(f"   확장 배터리({len(FORMS)}종) {sum(1 for r in rows if r['ok'])/max(1,len(rows))*100:.1f}%")
    print(f"\n   ── 아무 형태도 안 되는 gold {len(dead)}개 (앞 25) ──")
    for idx, k, g, rs in dead[:25]:
        print(f"      idx {idx:5d} step {k:3d}  {g:35s} 이름풀림={rs}")
