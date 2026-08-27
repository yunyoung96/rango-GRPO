#!/usr/bin/env python3
"""★ **필터 후 랭킹** — Coq 이 남긴 집합 안에서 premise retrieval 을 하면 gold 순위가 오르나.

필터는 재현율을 사되 후보를 많이 남긴다(중앙 5,033 · p90 11,265). 그 자체로는 못 쓴다.
그런데 **랭킹의 모집단을 그 집합으로 바꾸면** 경쟁자가 "적용 가능한 것들"로 한정되므로
gold 가 위로 올라와야 한다. 그걸 잰다.

  A 현행         rango 풀(≈1,333) 을 afh70 로 랭킹
  B 필터 후 랭킹  Coq 필터 결과를 afh70 로 랭킹
  C 합집합 랭킹   (A ∪ B) 를 afh70 로 랭킹

지표는 gold 의 top-k 진입률.

사용: FR_N=120 FR_SRC=all_log/coq_search_w5.jsonl python3 scripts/filtered_rank_eval.py
"""
import collections, json, os, re, sys, yaml, logging
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

N = int(os.environ.get("FR_N", "120"))
SRC = os.environ.get("FR_SRC", "all_log/coq_search_w5.jsonl")
SHARD = int(os.environ.get("FR_SHARD", "0"))
NSHARD = int(os.environ.get("FR_NSHARD", "1"))
CONF = yaml.safe_load(open("all_log/ft_qwen3b_v10_conf.yaml"))
# ★ conf 의 sentence_db 는 TRAIN(`/tmp/coq-dataset`) 을 가리킨다. 여기서는 TEST 를 잰다.
_TESTDB = "raw-data/coqstoq-test/coqstoq-test-sentences.db"
CONF["tactic_data"]["sentence_db_loc"] = _TESTDB
CONF["tactic_data"]["formatter_conf"]["premise"]["sentence_db_loc"] = _TESTDB
CONF["tactic_data"]["formatter_conf"]["proof_ret"]["sentence_db_loc"] = _TESTDB
CONF["tactic_data"]["formatter_conf"]["proof_ret"]["data_loc"] = "raw-data/coqstoq-test"
CONF["tactic_data"]["data_loc"] = "raw-data/coqstoq-test"
td = TacticDataConf.from_yaml(CONF["tactic_data"])
sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))
fm = formatter_from_conf(td.formatter_conf)
pc = fm.premise_client

# ★ `Search` 출력에서 **타입까지** 거둬 뒀다. 이름만 있으면 선언문을 다시 조회해야
#   하는데 전역 환경에는 stdlib 등 우리 색인에 없는 것이 많아 5,000 중 189 만 복원됐다.
FOUND = {}
for ln in open(SRC):
    ln = ln.strip()
    if ln:
        d = json.loads(ln)
        ty = d.get("types") or {}
        FOUND[(d["idx"], d["k"])] = [f"Lemma {k} : {v}." for k, v in ty.items() if v]
print(f"■ 필터 결과 {len(FOUND):,} 지점", flush=True)

DECL = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                  r"(?:Lemma|Theorem|Definition|Corollary|Fixpoint|Inductive|Remark|"
                  r"Proposition|Instance|Record|Axiom|Fact|Property)\s+([A-Za-z_][\w'.]*)")
NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")

def rank_of(ranked, gold):
    gb = gold.split(".")[-1]
    for j, p in enumerate(ranked):
        m = DECL.match(getattr(p, "text", "") or "")
        if m and (m.group(1) == gold or m.group(1).split(".")[-1] == gb):
            return j
    return None

S = collections.Counter()
ids = sorted({k[0] for k in FOUND})
ids = [i for j, i in enumerate(ids) if j % NSHARD == SHARD][:N]
for c, i in enumerate(ids):
    try:
        d = get_thm_desc(get_theorem(CSSplit.TEST, i, Path("CoqStoq")),
                         Path("raw-data/coqstoq-test"), sdb)
        if d is None: continue
        dp, pidx = d.dp, d.idx
        proof = dp.proofs[pidx]
    except Exception:
        continue
    for (ii, k) in [x for x in FOUND if x[0] == i]:
        try:
            step = proof.steps[k]
            gold = NAMED.search(step.step.text).group(1)
            base = list(pc.premise_filter.get_pos_and_avail_premises(step, proof, dp).avail_premises)
            texts = CSP.extra("__none__", have=set()) if False else None
            filt = CSP.as_sentences(FOUND[(ii, k)])
            if not filt:
                S["필터 비어있음"] += 1
            pools = {"A 현행": base, "B 필터후": filt, "C 합집합": list(base) + filt}
            S["지점"] += 1
            for lab, pool in pools.items():
                if not pool:
                    continue
                try:
                    ranked = pc.get_ranked_premises(k, proof, dp, pool, False)
                except Exception:
                    continue
                r = rank_of(ranked, gold)
                S[f"{lab}|n"] += 1
                S[f"{lab}|풀"] += len(pool)
                if r is not None:
                    for t in (10, 25, 50, 100):
                        S[f"{lab}@{t}"] += (r < t)
                    S[f"{lab}|있음"] += 1
        except Exception:
            S["오류"] += 1
    if (c + 1) % 10 == 0:
        print(f"   … {c+1}/{len(ids)} · 지점 {S['지점']}", flush=True)

n = max(S["지점"], 1)
print(f"\n■ 필터 후 랭킹 (CompCert {S['지점']} 지점 · 오류 {S['오류']})\n")
print(f"  {'':10s}{'풀 크기':>9s}{'gold 있음':>10s}{'@10':>8s}{'@25':>8s}{'@50':>8s}{'@100':>8s}")
for lab in ("A 현행", "B 필터후", "C 합집합"):
    m = max(S[f"{lab}|n"], 1)
    print(f"  {lab:10s}{S[f'{lab}|풀']/m:9,.0f}{S[f'{lab}|있음']/m*100:9.1f}%"
          + "".join(f"{S[f'{lab}@{t}']/m*100:7.1f}%" for t in (10, 25, 50, 100)))
