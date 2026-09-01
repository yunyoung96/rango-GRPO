#!/usr/bin/env python3
"""★★★ **커널 단일화로 직접 검증** — `assert_succeeds (eapply L)` / `(rewrite L)`.

## 왜 이것인가

experiment.txt §36-4 가 "A 국면에는 값싼 **결정적** 술어가 없다 — 진짜 결정적 술어는
`apply` 가 실제로 성공하는가이고 그건 **Coq 을 돌려야** 안다" 고 적었다.
그런데 **Coq 안에서는 그게 한 줄이다**:

    first [ assert_succeeds (eapply L); idtac "OK L" | idtac ].

`assert_succeeds` 는 tactic 을 **실제로 실행해 보고 상태를 되돌린다**. 즉 판정이
elaboration·변환·evar·타입클래스까지 전부 포함한 **커널 단일화 그 자체**다.

## 비용 (실측)

    후보 263개 검증 496ms (그중 ~470ms 는 Coq 기동) → **후보당 0.11ms**
    263 → 7개 (**37배 축소**)

노드 예산 300ms 면 후보 ~2,700개를 검증할 수 있다.

## 무엇을 재나

    풀(현행 rango) → assert_succeeds 검증 → 남는 개수 · gold 생존
    검색 기반 필터(4배 축소·88% 재현)와 정면 비교한다.

사용: AV_N=200 AV_JOBS=4 AV_TOPK=400 python3 scripts/apply_verify_eval.py
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

N = int(os.environ.get("AV_N", "200"))
JOBS = int(os.environ.get("AV_JOBS", "4"))
TMO = int(os.environ.get("AV_TIMEOUT", "600"))
TOPK = int(os.environ.get("AV_TOPK", "400"))     # 랭킹 상위 몇 개를 검증할까
MAXPT = int(os.environ.get("AV_MAX_PER_THM", "3"))
OUT = os.environ.get("AV_OUT", "all_log/apply_verify.jsonl")
CC = "CoqStoq/test-repos/compcert"
t = open(os.path.join(CC, "_CoqProject")).read().split(); ARGS = []; i = 0
while i < len(t):
    if t[i] in ("-R", "-Q"): ARGS += [t[i], os.path.abspath(os.path.join(CC, t[i+1])), t[i+2]]; i += 3
    else: i += 1

_TESTDB = "raw-data/coqstoq-test/coqstoq-test-sentences.db"
CONF = yaml.safe_load(open("all_log/ft_qwen3b_v10_conf.yaml"))
CONF["tactic_data"]["sentence_db_loc"] = _TESTDB
CONF["tactic_data"]["data_loc"] = "raw-data/coqstoq-test"
CONF["tactic_data"]["formatter_conf"]["premise"]["sentence_db_loc"] = _TESTDB
CONF["tactic_data"]["formatter_conf"]["proof_ret"]["sentence_db_loc"] = _TESTDB
CONF["tactic_data"]["formatter_conf"]["proof_ret"]["data_loc"] = "raw-data/coqstoq-test"
td = TacticDataConf.from_yaml(CONF["tactic_data"])
sdb = SentenceDB.load(Path(_TESTDB))
fm = formatter_from_conf(td.formatter_conf); pc = fm.premise_client

DECL = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                  r"(?:Lemma|Theorem|Definition|Corollary|Fixpoint|Inductive|Remark|"
                  r"Proposition|Instance|Record|Axiom|Fact|Property)\s+([A-Za-z_][\w'.]*)")
NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")

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
        body.append(f'idtac "@@@{k}".')
        tac, names = cands[k]
        for nm in names:
            # ★ 커널 단일화 판정 — 실행해 보고 상태를 되돌린다.
            #   ★★ **형태를 하나만 시험하면 안 된다.** `eapply L` 만 보면
            #   `rewrite L` · `rewrite <- L` · `rewrite L in H` 로 쓰이는 것을 놓친다
            #   (실측: gold 생존 73.1%, rewrite 는 29.4% 였다).
            #   배터리로 한 번에 시험한다 — 검증 1회가 0.11ms 라 비용이 거의 없다.
            body.append(
                f'first [ assert_succeeds (first ['
                f'eapply {nm} | erewrite {nm} | erewrite <- {nm} '
                f'| erewrite {nm} in * '
                f'| apply {nm} | rewrite {nm} ]); idtac "OK {nm}" | idtac ].')
            # ★ `eapply L in *` 은 **문법 오류**다(`in` 은 rewrite 계열만).
            #   하나라도 파싱이 깨지면 파일 전체가 죽어 전부 0 이 된다 — 실측으로 걸렸다.
        prev = k
    body.append("Admitted.")
    d = os.path.dirname(os.path.abspath(path))
    with tempfile.NamedTemporaryFile("w", suffix=".v", dir=d, delete=False) as f:
        f.write("\n".join(body) + "\n"); tmp = f.name
    try:
        t0 = time.time()
        p = subprocess.run(["coqc", "-q"] + ARGS + [tmp], capture_output=True, text=True, timeout=TMO)
        dt = time.time() - t0
        out = p.stdout or ""
        blocks = re.split(r"@@@(\d+)\s*", out)
        recs = []
        for a in range(1, len(blocks) - 1, 2):
            k = int(blocks[a])
            ok = re.findall(r"(?m)^OK ([\w'.]+)", blocks[a + 1])
            recs.append({"idx": i, "k": k, "ok": sorted(set(ok)), "sec": dt,
                         "ncand": len(cands[k][1])})
        return i, recs, None if recs else (p.stderr or "")[:150]
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
            dp, pidx = d.dp, d.idx; proof = dp.proofs[pidx]
            path = os.path.join(CC, str(thm.path)); orig = open(path, errors="ignore").read()
        except Exception: continue
        if head_of_file(orig, proof.theorem.term.text) is None: continue
        ks = [k for k, st in enumerate(proof.steps)
              if HEADT.match(st.step.text or "")
              and HEADT.match(st.step.text).group(1) in ("apply","eapply","rewrite","erewrite")
              and NAMED.search(st.step.text or "") and st.goals]
        if not ks: continue
        if len(ks) > MAXPT:
            stp = len(ks)/MAXPT; ks = [ks[int(x*stp)] for x in range(MAXPT)]
        steps = [s.step.text for s in proof.steps]
        chunks, prev = {}, 0
        for k in ks: chunks[prev] = "".join(steps[prev:k]); prev = k
        cands = {}
        for k in ks:
            st = proof.steps[k]
            try:
                pool = list(pc.premise_filter.get_pos_and_avail_premises(st, proof, dp).avail_premises)
                ranked = pc.get_ranked_premises(k, proof, dp, pool, False)
            except Exception:
                continue
            nm = [x for x in (qname(pp) for pp in ranked[:TOPK]) if x]
            tac = HEADT.match(st.step.text).group(1)
            cands[k] = ("rewrite" if tac.endswith("rewrite") else "apply", list(dict.fromkeys(nm)))
            meta[(i, k)] = dict(gold=NAMED.search(st.step.text).group(1),
                                tac=cands[k][0], npool=len(pool),
                                inTopK=any(x == meta.get("_", None) for x in []) )
            gb = meta[(i,k)]["gold"].split(".")[-1]
            meta[(i,k)]["inTopK"] = any(x == meta[(i,k)]["gold"] or x.split(".")[-1]==gb
                                        for x in cands[k][1])
        ks = [k for k in ks if k in cands and cands[k][1]]
        if ks: jobs.append((i, path, proof.theorem.term.text, chunks, ks, cands))
    jobs.sort(key=lambda j: len(open(j[1], errors="ignore").read()))
    print(f"■ 정리 {len(jobs)} · 지점 {len(meta)} · top{TOPK} 검증 · 병렬 {JOBS}", flush=True)
    S = collections.Counter(); T = []
    with open(OUT, "w") as fo, cf.ThreadPoolExecutor(JOBS) as ex:
        for n, (i, recs, err) in enumerate(ex.map(run, jobs)):
            for r in recs:
                m = meta.get((r["idx"], r["k"]))
                if not m: continue
                gb = m["gold"].split(".")[-1]
                hit = any(x == m["gold"] or x.split(".")[-1] == gb for x in r["ok"])
                S["지점"] += 1; S["검증대상"] += r["ncand"]; S["통과"] += len(r["ok"])
                S["gold 상위K에"] += m["inTopK"]; S["gold 통과"] += hit
                if m["inTopK"]: S["상위K중 gold생존"] += hit
                S[f"{m['tac']} 지점"] += 1; S[f"{m['tac']} 통과"] += len(r["ok"])
                S[f"{m['tac']} gold"] += hit
                T.append(r["sec"])
                r.update(gold=m["gold"], tac=m["tac"], hit=hit, inTopK=m["inTopK"], npool=m["npool"])
                fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            if err: S["실패"] += 1
            if (n+1) % 10 == 0:
                print(f"   … {n+1}/{len(jobs)} · 지점 {S['지점']} · gold {S['gold 통과']}", flush=True)
            fo.flush()
    nn = max(S["지점"], 1); import statistics as st
    print(f"\n■ 커널 단일화 검증 (CompCert {S['지점']} 지점 · 실패 {S['실패']})")
    print(f"   검증 대상   {S['검증대상']/nn:8.0f}개/지점")
    print(f"   ★ 통과      {S['통과']/nn:8.1f}개/지점   ({S['검증대상']/max(S['통과'],1):.0f}배 축소)")
    print(f"   gold 이 상위{TOPK} 에 있던 비율 {S['gold 상위K에']/nn*100:.1f}%")
    print(f"   ★ 그중 검증 통과            {S['상위K중 gold생존']/max(S['gold 상위K에'],1)*100:.1f}%")
    print(f"   전체 지점 기준 gold 통과     {S['gold 통과']/nn*100:.1f}%")
    for tc in ("apply","rewrite"):
        m2 = S[f"{tc} 지점"]
        if m2: print(f"   · {tc:8s} {m2:3d}지점 · 통과 {S[f'{tc} 통과']/m2:6.1f}개 · gold {S[f'{tc} gold']/m2*100:5.1f}%")
    if T: print(f"   정리당 {st.median(T):.1f}s")
