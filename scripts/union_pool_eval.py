#!/usr/bin/env python3
"""★ ①∪② 를 실제 파이프라인에 태우고 **gold 가 어디까지 가나** 잰다.

    ① 현행 rango 풀 (proj-thm + functor_expand)
    ② Coq 내장 색인(`SearchPattern`/`SearchRewrite`) 결과   ← coq_search_pool 로 주입

세 지점을 잰다:
    A. 풀에 있나        (avail_premises)
    B. 랭킹 top-100 에 드나
    C. **프롬프트에 실리나** (premise_tokens 예산 + hard 절단)  ← 이게 최종 목표

사용: UP_N=200 UP_SRC=all_log/coq_search_v10.jsonl python3 scripts/union_pool_eval.py
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
from tactic_gen.tactic_data import (TacticDataConf, example_collator_from_conf,
                                    example_collator_conf_from_yaml, get_tokenizer)
from premise_selection import coq_search_pool as CSP
from premise_selection.fingerprint import parse  # noqa

N = int(os.environ.get("UP_N", "200"))
SRC = os.environ.get("UP_SRC", "all_log/coq_search_v10.jsonl")
SHARD = int(os.environ.get("UP_SHARD", "0"))
NSHARD = int(os.environ.get("UP_NSHARD", "1"))
CONF = yaml.safe_load(open("all_log/ft_qwen3b_v10_conf.yaml"))
td = TacticDataConf.from_yaml(CONF["tactic_data"])
DATA_LOC = Path("raw-data/coqstoq-test")
sdb = SentenceDB.load(Path("raw-data/coqstoq-test/coqstoq-test-sentences.db"))
fm = formatter_from_conf(td.formatter_conf)
col = example_collator_from_conf(example_collator_conf_from_yaml(CONF["tactic_data"]["collator_conf"]))
tok = get_tokenizer(td.model_name)

FOUND = {}
for ln in open(SRC):
    ln = ln.strip()
    if ln:
        d = json.loads(ln)
        FOUND[(d["idx"], d["k"])] = d.get("found", [])
print(f"■ Coq Search 결과 {len(FOUND):,} 지점 ({SRC})", flush=True)

NAMED = re.compile(r"\b(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
DECL = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                  r"(?:Lemma|Theorem|Definition|Corollary|Fixpoint|Inductive|Remark|"
                  r"Proposition|Instance|Record|Axiom|Fact|Property)\s+([A-Za-z_][\w'.]*)")

def seen(nm, text):
    return re.search(r"(?<![\w'])" + re.escape(nm) + r"(?![\w'])", text) is not None

S = collections.Counter()
ids = sorted({k[0] for k in FOUND})
ids = [i for j, i in enumerate(ids) if j % NSHARD == SHARD][:N]
for c, i in enumerate(ids):
    try:
        d = get_thm_desc(get_theorem(CSSplit.TEST, i, Path("CoqStoq")), DATA_LOC, sdb)
        if d is None: continue
        dp, pidx = d.dp, d.idx
    except Exception:
        continue
    for (ii, k) in [x for x in FOUND if x[0] == i]:
        try:
            gold = NAMED.search(dp.proofs[pidx].steps[k].step.text).group(1)
        except Exception:
            continue
        gb = gold.split(".")[-1]
        key = (getattr(dp, "dp_name", "") or
               getattr(getattr(dp, "file_context", None), "file", ""), pidx, k)
        for mode in ("현행", "합집합"):
            CSP.clear()
            if mode == "합집합":
                CSP.put(key, FOUND[(ii, k)])
            try:
                ex = fm.example_from_step(k, pidx, dp, training=False)
            except Exception:
                S[f"{mode}|오류"] += 1
                continue
            prem = list(ex.premises or [])
            names = [DECL.match(t).group(1) if DECL.match(t) else "" for t in prem]
            inpool = any(x == gold or x.split(".")[-1] == gb for x in names)
            top100 = any((x == gold or x.split(".")[-1] == gb)
                         for x in names[:100])
            try:
                s_in = col.collate_input(tok, ex, normalize=False)
            except TypeError:
                s_in = col.collate_input(tok, ex)
            # ★ **[PREMISES] 구간만** 본다. 프롬프트 전체를 보면 [STATE]·[DEFINITIONS]
            #   에 우연히 같은 이름이 있어 과대 계상된다(실측: 83% 로 부풀었다).
            _seg = s_in.split("[PROOFS]")[0] if "[PROOFS]" in s_in else s_in
            _seg = _seg.split("[PREMISES]")[-1]
            inprompt = seen(gold, _seg) or seen(gb, _seg)
            S[f"{mode}|지점"] += 1
            S[f"{mode}|풀"] += inpool
            S[f"{mode}|top100"] += top100
            S[f"{mode}|프롬프트"] += inprompt
            S[f"{mode}|후보"] += len(prem)
        S["지점"] += 1
    if (c + 1) % 10 == 0:
        print(f"   … {c+1}/{len(ids)} · 지점 {S['지점']}", flush=True)

print(f"\n■ ①∪② 파이프라인 실측 (CompCert {S['지점']} 지점)\n")
print(f"  {'':10s}{'풀에':>9s}{'top100':>9s}{'프롬프트':>10s}{'후보수':>9s}")
for mode in ("현행", "합집합"):
    n = max(S[f"{mode}|지점"], 1)
    print(f"  {mode:10s}{S[f'{mode}|풀']/n*100:8.1f}%{S[f'{mode}|top100']/n*100:8.1f}%"
          f"{S[f'{mode}|프롬프트']/n*100:9.1f}%{S[f'{mode}|후보']/n:8.0f}")
a = max(S["현행|지점"], 1); b = max(S["합집합|지점"], 1)
print(f"\n  Δ 풀 {(S['합집합|풀']/b - S['현행|풀']/a)*100:+.1f}pp"
      f" · top100 {(S['합집합|top100']/b - S['현행|top100']/a)*100:+.1f}pp"
      f" · 프롬프트 {(S['합집합|프롬프트']/b - S['현행|프롬프트']/a)*100:+.1f}pp")
