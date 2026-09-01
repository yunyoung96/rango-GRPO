#!/usr/bin/env python3
"""★ **필터를 했는데 왜 @10 이 떨어지나** — gold 위에 있는 것을 직접 꺼낸다.

실측: gold = rewrite 에서
    현행   풀에 84.6%  @10 53.8%
    필터후 풀에 96.2%  @10 23.1%   ← 도달성은 올랐는데 상위 정밀도가 떨어졌다

가설 셋을 데이터로 가른다:
    ① stdlib 잡음   — 필터후 풀에는 stdlib 이 들어온다 (현행 풀엔 없다)
    ② 보편 lemma    — `f_equal`·`eq_sym` 처럼 어디에나 적용되는 것이 위로 뜬다
    ③ idf 통계 변화 — 풀이 바뀌면 tf-idf 의 idf 도 바뀐다

사용: python3 scripts/why_rank_drop.py [지점수]
"""
import json, os, re, sys, collections, logging, yaml
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

NSHOW = int(sys.argv[1]) if len(sys.argv) > 1 else 8
_T = "raw-data/coqstoq-test/coqstoq-test-sentences.db"
CONF = yaml.safe_load(open("all_log/ft_qwen3b_v10_conf.yaml"))
CONF["tactic_data"]["sentence_db_loc"] = _T
CONF["tactic_data"]["data_loc"] = "raw-data/coqstoq-test"
CONF["tactic_data"]["formatter_conf"]["premise"]["sentence_db_loc"] = _T
CONF["tactic_data"]["formatter_conf"]["proof_ret"]["sentence_db_loc"] = _T
CONF["tactic_data"]["formatter_conf"]["proof_ret"]["data_loc"] = "raw-data/coqstoq-test"
td = TacticDataConf.from_yaml(CONF["tactic_data"])
sdb = SentenceDB.load(Path(_T))
pc = formatter_from_conf(td.formatter_conf).premise_client

DECL = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                  r"(?:Lemma|Theorem|Corollary|Remark|Definition|Fixpoint|Inductive|"
                  r"Proposition|Instance|Record|Axiom|Fact|Property)\s+([A-Za-z_][\w'.]*)")
NAMED = re.compile(r"\b(?:e?apply|e?rewrite|unfold|destruct|induction|case|elim"
                   r"|e?exact)\s+(?:<-\s*)?\(?\s*([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
HEADT = re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?([A-Za-z_][\w']*)")

#: stdlib 판정 — 이 접두사로 시작하면 Coq 표준 라이브러리다
STD = ("Coq.", "Nat.", "N.", "Z.", "Pos.", "BinInt.", "BinNat.", "BinPos.",
       "BinPosDef.", "List.", "Vector.", "VectorDef.", "Ascii.", "Byte.",
       "Eqdep", "EqdepFacts.", "JMeq.", "Ring", "Field", "Morphisms",
       "CMorphisms.", "CRelationClasses.", "RelationClasses.", "Equivalence.",
       "Classical", "ProofIrrelevance", "Setoid", "Basics.", "Combinators.",
       "Datatypes.", "Specif.", "Logic.", "Init.", "Bool.", "Decidable.",
       "OrderedType", "POrderedType.", "Raxioms", "Rdefinitions", "R", "Rbase")


def is_std(nm):
    return any(nm.startswith(p) for p in STD) or "." not in nm and nm.islower() and len(nm) <= 4


def nm_of(p):
    m = DECL.match(getattr(p, "text", "") or "")
    return m.group(1) if m else ""


rows = [json.loads(l) for l in open("all_log/dn_pool.jsonl")]
assert rows, "dn_pool.jsonl 이 비었다"
by = collections.defaultdict(list)
for r in rows: by[r["idx"]].append(r)

# 보편 lemma (필터를 90% 지점에서 통과) 집합
cnt = collections.Counter()
for r in rows:
    seen = set()
    for ch in ("ap", "in", "rw"): seen |= set((r.get("chan") or {}).get(ch, []))
    for x in seen: cnt[x] += 1
UNI = {k for k, v in cnt.items() if v / max(1, len(rows)) >= 0.9}
print(f"■ 보편 lemma {len(UNI)}개 (전체 지점의 90% 이상에서 필터 통과)\n")

S = collections.Counter(); shown = 0
for i, rs in sorted(by.items()):
    if shown >= NSHOW: break
    try:
        d = get_thm_desc(get_theorem(CSSplit.TEST, i, Path("CoqStoq")),
                         Path("raw-data/coqstoq-test"), sdb)
        if d is None: continue
        dp, pidx = d.dp, d.idx; proof = dp.proofs[pidx]
    except Exception:
        continue
    for r in rs:
        k = r["k"]
        try:
            st = proof.steps[k]; t = st.step.text or ""
            h = HEADT.match(t)
            if not h or not h.group(1).endswith("rewrite"): continue
            gold = NAMED.search(t).group(1)
            if gold in set(r.get("hyps") or []): continue
            base = list(pc.premise_filter.get_pos_and_avail_premises(st, proof, dp).avail_premises)
            filt = CSP.as_sentences([f"Lemma {a} : {b}." for a, b in
                                     (r.get("stmts") or {}).items() if b])
            if not filt: continue
            gb = gold.split(".")[-1]
            out = {}
            for lab, pool in (("현행", base), ("필터후", filt)):
                ranked = pc.get_ranked_premises(k, proof, dp, pool, False)
                names = [nm_of(p) for p in ranked]
                pos = next((j for j, x in enumerate(names)
                            if x == gold or x.split(".")[-1] == gb), None)
                out[lab] = (names[:10], pos, len(pool))
                for x in names[:10]:
                    S[f"{lab}|top10"] += 1
                    S[f"{lab}|stdlib"] += is_std(x)
                    S[f"{lab}|보편"] += (x in UNI)
            if out["현행"][1] is not None and (out["필터후"][1] is None
                                              or out["필터후"][1] > out["현행"][1] + 5):
                shown += 1
                print(f"── idx {i} step {k} · gold `{gold}` · {t.strip()[:50]}")
                for lab in ("현행", "필터후"):
                    names, pos, n = out[lab]
                    print(f"   [{lab}] 풀 {n:,} · gold 순위 {pos}")
                    for x in names:
                        tag = ("★gold" if (x == gold or x.split(".")[-1] == gb)
                               else ("보편" if x in UNI else ("std" if is_std(x) else "")))
                        print(f"        {tag:5s} {x}")
                print()
        except Exception:
            continue

for lab in ("현행", "필터후"):
    n = max(1, S[f"{lab}|top10"])
    print(f"■ {lab} 의 top10 구성 — stdlib {S[f'{lab}|stdlib']/n*100:.1f}%"
          f" · 보편 {S[f'{lab}|보편']/n*100:.1f}%  ({n} 칸)")
