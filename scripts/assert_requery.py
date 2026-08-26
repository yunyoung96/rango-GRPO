#!/usr/bin/env python3
"""★ 모델이 세운 `assert (P)` 의 **P 를 질의문으로 premise 를 다시 검색**하면
gold lemma 가 잡히는가.

지금 랭커는 **goal** 로 검색한다. goal 은 "무엇을 증명하나"고,
assert 명제는 "무엇이 필요한가"다. 후자가 lemma 검색에 더 직접적일 것이라는 가설.

`example_from_step(..., goal_override=Goal(hyps, P))` 가 이미 그 기능을 갖고 있다
(substep 용으로 만들어진 것). 그대로 쓴다. **생성 없음 · CPU 전용.**

사용: AR_SHARD/AR_NSHARD AR_OUT python3 scripts/assert_requery.py <what_instead jsonl...>
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
from data_management.dataset_file import Goal
from evaluation.find_coqstoq_idx import get_thm_desc
from tactic_gen.lm_example import formatter_from_conf
from tactic_gen.tactic_data import TacticDataConf

SHARD = int(os.environ.get("AR_SHARD", "0"))
NSHARD = int(os.environ.get("AR_NSHARD", "1"))
OUT = Path(os.environ.get("AR_OUT", "all_log/assert_requery.jsonl"))
CONF = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
td = TacticDataConf.from_yaml(CONF["tactic_data"])
DATA_LOC = Path("raw-data/coqstoq-test")
sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))
formatter = formatter_from_conf(td.formatter_conf)

DECL = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                  r"(?:Lemma|Theorem|Definition|Corollary|Fixpoint|Inductive|Remark|"
                  r"Proposition|Instance|Record|Axiom|Parameter)\s+([A-Za-z_][\w']*)")
ASS = re.compile(r"^\s*assert\s*\((.*)\)\s*(?:as\s+[\w']+)?\s*\.?\s*$", re.S)
ASS2 = re.compile(r"^\s*assert\s*\((.*?)\)\s*as\s+[\w']+", re.S)

def rank_of(name, prems):
    """prems 안에서 name 이 선언된 위치(1-base). 없으면 None."""
    bare = name.split(".")[-1]
    for j, p in enumerate(prems or []):
        m = DECL.match(p or "")
        if m and (m.group(1) == name or m.group(1) == bare):
            return j + 1
    return None

def assert_body(t):
    m = ASS2.match(t.strip()) or ASS.match(t.strip())
    return m.group(1).strip() if m else None

recs = []
for f in sys.argv[1:]:
    for ln in Path(f).open():
        ln = ln.strip()
        if ln:
            r = json.loads(ln)
            if "err" in r: continue
            body = None
            for o in r["outs"]:
                if re.match(r"^\s*assert\b", o["text"]):
                    body = assert_body(o["text"])
                    if body: break
            if body:
                r["_P"] = body; recs.append(r)
by_thm = collections.defaultdict(list)
for r in recs: by_thm[r["idx"]].append(r)
thms = sorted(by_thm)
mine = [t for j, t in enumerate(thms) if j % NSHARD == SHARD]
print(f"■ assert 스텝 {len(recs)} · 담당 {len(mine)}/{len(thms)} 정리", flush=True)

fout = OUT.open("w"); done = 0
for i in mine:
    try:
        thm = get_theorem(CSSplit.TEST, i, Path("CoqStoq"))
        desc = get_thm_desc(thm, DATA_LOC, sdb)
        if desc is None: continue
        dp, pidx = desc.dp, desc.idx
    except Exception:
        continue
    for r in by_thm[i]:
        try:
            k = r["k"]
            base = formatter.example_from_step(k, pidx, dp, training=False)
            rb = rank_of(r["gname"], base.premises)
            hyps = list(dp.proofs[pidx].steps[k].goals[0].hyps) if dp.proofs[pidx].steps[k].goals else []
            gov = Goal(hyps, r["_P"])
            req = formatter.example_from_step(k, pidx, dp, training=False, goal_override=gov)
            rq = rank_of(r["gname"], req.premises)
            fout.write(json.dumps(dict(
                idx=i, k=k, gold=r["gold"], gname=r["gname"], P=r["_P"],
                decl_how=r["decl_how"], okA=r["okA"], okB=r["okB"], okC=r["okC"],
                rank_base=rb, rank_requery=rq,
                n_base=len(base.premises or []), n_req=len(req.premises or []),
                top5_req=[(req.premises or [])[j][:90] for j in range(min(5, len(req.premises or [])))],
            ), ensure_ascii=False) + "\n")
        except Exception as e:
            fout.write(json.dumps(dict(idx=i, k=r["k"], err=str(e)[:150]), ensure_ascii=False) + "\n")
    done += 1; fout.flush()
    if done % 5 == 0: print(f"   … {done}/{len(mine)}", flush=True)
print("DONE", flush=True)
