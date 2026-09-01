#!/usr/bin/env python3
"""★★ **①∪② 풀 + 커널 검증** — 밤 체인의 천장이 어디였는지 가른다.

밤 체인(av_top2000)은 풀을 `avail_premises`(rango 기본) 로만 잡았다. 그래서
`gold 이 풀에 60.4%` 가 천장이 됐고, top200→top2000 으로 10배 늘려도
42.4%→43.5% 밖에 안 올랐다. **랭킹이 아니라 풀이 병목이었다.**

여기서는 같은 지점을 **두 풀로 짝지어(paired)** 잰다:

    A 현행    avail_premises
    C 합집합  avail_premises ∪ Coq 내장 색인(SearchPattern/SearchRewrite) 결과

같은 .v 파일 안에서 둘 다 검증하므로 Coq 기동 비용이 한 번이고 짝지은 비교가 된다.

사용: python3 scripts/av_union_eval.py
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
from tactic_gen.lm_example import formatter_from_conf
from tactic_gen.tactic_data import TacticDataConf
from premise_selection import coq_search_pool as CSP

# ── 설정은 파이썬 변수다 ──
SRC      = "all_log/coq_search_w6.jsonl"   # types 를 가진 판본 (재현 87.9%)
N        = 200
JOBS     = 4
TIMEOUT  = 1800
TOPK     = 1200          # 각 풀에서 검증할 상위 개수
MAX_PT   = 2             # 정리당 지점 (파일이 커져서 2로 줄인다)
OUT      = "all_log/av_union.jsonl"
CC       = "CoqStoq/test-repos/compcert"

# ★ 확장 배터리 — `apply L in H` 는 유효 문법이다(`in *` 만 apply 에서 오류).
BATTERY = ("eapply {n} | apply {n} | erewrite {n} | erewrite <- {n} "
           "| rewrite {n} | erewrite {n} in * | erewrite <- {n} in * "
           "| match goal with H : _ |- _ => apply {n} in H end "
           "| match goal with H : _ |- _ => erewrite {n} in H end "
           "| match goal with H : _ |- _ => erewrite <- {n} in H end")

t = open(os.path.join(CC, "_CoqProject")).read().split(); ARGS = []; _i = 0
while _i < len(t):
    if t[_i] in ("-R", "-Q"):
        ARGS += [t[_i], os.path.abspath(os.path.join(CC, t[_i+1])), t[_i+2]]; _i += 3
    else: _i += 1

_TESTDB = "raw-data/coqstoq-test/coqstoq-test-sentences.db"
CONF = yaml.safe_load(open("all_log/ft_qwen3b_v10_conf.yaml"))
CONF["tactic_data"]["sentence_db_loc"] = _TESTDB
CONF["tactic_data"]["data_loc"] = "raw-data/coqstoq-test"
CONF["tactic_data"]["formatter_conf"]["premise"]["sentence_db_loc"] = _TESTDB
CONF["tactic_data"]["formatter_conf"]["proof_ret"]["sentence_db_loc"] = _TESTDB
CONF["tactic_data"]["formatter_conf"]["proof_ret"]["data_loc"] = "raw-data/coqstoq-test"
td = TacticDataConf.from_yaml(CONF["tactic_data"])
sdb = SentenceDB.load(Path(_TESTDB))
fm = formatter_from_conf(td.formatter_conf)
pc = fm.premise_client

DECL = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                  r"(?:Lemma|Theorem|Corollary|Remark|Definition|"
                  r"Proposition|Instance|Record|Axiom|Fact|Property)\s+([A-Za-z_][\w'.]*)")
NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")

FOUND = {}
for ln in open(SRC):
    ln = ln.strip()
    if not ln: continue
    d = json.loads(ln); ty = d.get("types") or {}
    FOUND[(d["idx"], d["k"])] = [f"Lemma {k} : {v}." for k, v in ty.items() if v]
print(f"■ 필터 결과 {len(FOUND):,} 지점", flush=True)

def qname(pp):
    """★ 모듈 정규화 이름. `Module PTree` 안의 `Lemma gso` 는 선언문엔 `gso` 지만
    쓸 때는 `PTree.gso` 여야 한다. 풀의 34.7% 가 모듈 안에 있어서, 맨이름을 쏘면
    그만큼이 **항상 실패**로 잡힌다(밤 체인이 정확히 이 함정에 빠졌다)."""
    m = DECL.match(getattr(pp, "text", "") or "")
    if not m: return None
    mod = list(getattr(pp, "module", None) or [])
    return ".".join(mod + [m.group(1)])

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
    i, path, thm_text, chunks, ks, cands = job
    try: orig = open(path, errors="ignore").read()
    except OSError: return i, [], "파일 없음"
    head = head_of_file(orig, thm_text)
    if head is None: return i, [], "정리 위치 못 찾음"
    body = [head, thm_text]; prev = 0
    for k in ks:
        body.append(chunks[prev])
        for lab in ("A", "C"):
            body.append(f'idtac "@@@{k}#{lab}".')
            for nm in cands[k][lab]:
                # ★ 이름이 이 지점에서 해결되나 — "적용 불가" 와 "이름 없음" 을 가른다.
                body.append(f'first [ assert_succeeds (pose {nm}); idtac "R {nm}" | idtac ].')
                body.append(f'first [ assert_succeeds (first [ '
                            + BATTERY.format(n=nm)
                            + f' ]); idtac "OK {nm}" | idtac ].')
        prev = k
    body.append("Admitted.")
    d = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=d, delete=False) as f:
        f.write("\n".join(body) + "\n"); tmp = f.name
    try:
        t0 = time.time()
        p = subprocess.run(["coqc", "-q"] + ARGS + [tmp],
                           capture_output=True, text=True, timeout=TIMEOUT)
        dt = time.time() - t0
        blocks = re.split(r"@@@(\d+)#([AC])\s*", p.stdout or "")
        recs = []
        for a in range(1, len(blocks) - 2, 3):
            k = int(blocks[a]); lab = blocks[a+1]
            ok = re.findall(r"(?m)^OK ([\w'.]+)", blocks[a+2])
            rs = re.findall(r"(?m)^R ([\w'.]+)", blocks[a+2])
            recs.append({"idx": i, "k": k, "pool": lab, "sec": dt,
                         "ok": sorted(set(ok)), "nres": len(set(rs)),
                         "ncand": len(cands[k][lab])})
        return i, recs, None if recs else (p.stderr or "")[:200]
    except subprocess.TimeoutExpired: return i, [], "timeout"
    except Exception as e: return i, [], str(e)[:120]
    finally:
        b = os.path.splitext(tmp)[0]
        for e in (".v", ".vo", ".vok", ".vos", ".glob"):
            try: os.unlink(b + e)
            except OSError: pass

if __name__ == "__main__":
    ids = sorted({k[0] for k in FOUND})[:N]
    jobs, meta = [], {}
    for i in ids:
        try:
            thm = get_theorem(CSSplit.TEST, i, Path("CoqStoq"))
            d = get_thm_desc(thm, Path("raw-data/coqstoq-test"), sdb)
            if d is None: continue
            dp, pidx = d.dp, d.idx; proof = dp.proofs[pidx]
            path = os.path.join(CC, str(thm.path)); orig = open(path, errors="ignore").read()
        except Exception: continue
        if head_of_file(orig, proof.theorem.term.text) is None: continue
        ks = [k for (ii, k) in FOUND if ii == i and k < len(proof.steps)]
        ks = [k for k in ks
              if HEADT.match(proof.steps[k].step.text or "")
              and NAMED.search(proof.steps[k].step.text or "") and proof.steps[k].goals]
        ks = sorted(set(ks))
        if not ks: continue
        if len(ks) > MAX_PT:
            stp = len(ks)/MAX_PT; ks = [ks[int(x*stp)] for x in range(MAX_PT)]
        steps = [s.step.text for s in proof.steps]
        chunks, prev = {}, 0
        for k in ks: chunks[prev] = "".join(steps[prev:k]); prev = k
        cands = {}
        for k in ks:
            st = proof.steps[k]
            try:
                base = list(pc.premise_filter.get_pos_and_avail_premises(st, proof, dp).avail_premises)
                filt = CSP.as_sentences(FOUND[(i, k)])
            except Exception:
                continue
            got = {}
            for lab, pool in (("A", base), ("C", list(base) + list(filt))):
                if not pool: got[lab] = []; continue
                try: ranked = pc.get_ranked_premises(k, proof, dp, pool, False)
                except Exception: got[lab] = []; continue
                nm = [qname(pp) for pp in ranked[:TOPK]]
                got[lab] = list(dict.fromkeys(x for x in nm if x))
            if not got.get("A") and not got.get("C"): continue
            cands[k] = got
            gold = NAMED.search(st.step.text).group(1); gb = gold.split(".")[-1]
            meta[(i, k)] = dict(gold=gold,
                                tac=("rewrite" if HEADT.match(st.step.text).group(1).endswith("rewrite")
                                     else "apply"),
                                nbase=len(base), nfilt=len(filt),
                                inA=any(x == gold or x.split(".")[-1] == gb for x in got.get("A", [])),
                                inC=any(x == gold or x.split(".")[-1] == gb for x in got.get("C", [])))
        ks = [k for k in ks if k in cands]
        if ks: jobs.append((i, path, proof.theorem.term.text, chunks, ks, cands))
    jobs.sort(key=lambda j: len(open(j[1], errors="ignore").read()))
    print(f"■ 정리 {len(jobs)} · 지점 {len(meta)} · top{TOPK} · 병렬 {JOBS}", flush=True)
    S = collections.Counter(); paired = collections.Counter()
    per = collections.defaultdict(dict)
    with open(OUT, "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for n, (i, recs, err) in enumerate(ex.map(run, jobs)):
            for r in recs:
                m = meta.get((r["idx"], r["k"]))
                if not m: continue
                gb = m["gold"].split(".")[-1]
                hit = any(x == m["gold"] or x.split(".")[-1] == gb for x in r["ok"])
                lab = r["pool"]
                S[f"{lab}|지점"] += 1; S[f"{lab}|대상"] += r["ncand"]
                S[f"{lab}|통과"] += len(r["ok"]); S[f"{lab}|gold"] += hit
                S[f"{lab}|해결"] += r.get("nres", 0)
                S[f"{lab}|풀에"] += m["inA"] if lab == "A" else m["inC"]
                S[f"{lab}|{m['tac']}n"] += 1; S[f"{lab}|{m['tac']}gold"] += hit
                per[(r["idx"], r["k"])][lab] = hit
                r.update(gold=m["gold"], tac=m["tac"], hit=hit,
                         inA=m["inA"], inC=m["inC"], nbase=m["nbase"], nfilt=m["nfilt"])
                fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            if err: S["실패"] += 1
            if (n+1) % 10 == 0:
                print(f"   … {n+1}/{len(jobs)} · A {S['A|gold']} / C {S['C|gold']}", flush=True)
            fo.flush()
    import statistics as stt
    print(f"\n■ ①∪② + 커널검증 (CompCert · 실패 {S['실패']})")
    for lab, nm in (("A", "현행 avail_premises"), ("C", "합집합 ∪ Coq색인")):
        nn = max(S[f"{lab}|지점"], 1)
        print(f"   [{lab}] {nm}")
        print(f"       지점 {S[f'{lab}|지점']} · 검증대상 {S[f'{lab}|대상']/nn:.0f}개 "
              f"· 이름해결 {S[f'{lab}|해결']/nn:.0f}개 "
              f"({S[f'{lab}|해결']/max(1,S[f'{lab}|대상'])*100:.1f}%) "
              f"· 통과 {S[f'{lab}|통과']/nn:.1f}개")
        print(f"       gold 이 상위{TOPK} 에 {S[f'{lab}|풀에']/nn*100:.1f}%"
              f" · ★ gold 통과 {S[f'{lab}|gold']/nn*100:.1f}%")
        for tc in ("apply", "rewrite"):
            n2 = max(S[f"{lab}|{tc}n"], 1)
            print(f"       · {tc:8s} {S[f'{lab}|{tc}n']:4d}지점 gold {S[f'{lab}|{tc}gold']/n2*100:5.1f}%")
    b = sum(1 for v in per.values() if v.get("A") and not v.get("C"))
    c = sum(1 for v in per.values() if v.get("C") and not v.get("A"))
    print(f"\n   ── 짝지은 비교 (McNemar) ──  A만 {b} · C만 {c} · 짝 {len(per)}")
