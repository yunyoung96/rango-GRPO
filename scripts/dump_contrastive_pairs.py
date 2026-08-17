#!/usr/bin/env python3
"""contrastive 학습용 (goal, premise) 쌍을 덤프한다.

각 사례에서 **gold + hard negative(tfidf 상위)** 를 뽑아 원문을 저장한다.
토큰화는 학습 때 `structural_repr.pair_tokens` 로 하므로 여기서는 원문만 남긴다
(표현을 바꿔가며 재학습할 수 있게).

사용: python3 scripts/dump_contrastive_pairs.py <train|val|test> [n] [neg]
"""
import copy
import json
import os
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from data_management.dataset_file import (DatasetFile, get_ids_from_goal,  # noqa: E402
                                          get_ids_from_sentence)
from data_management.sentence_db import SentenceDB  # noqa: E402
from proof_retrieval.tfidf import tf_idf  # noqa: E402
from premise_selection.premise_filter import PremiseFilter, PremiseFilterConf  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402
import re  # noqa: E402

SPLIT = (sys.argv[1] if len(sys.argv) > 1 else "train").upper()
N = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
NEG = int(sys.argv[3]) if len(sys.argv) > 3 else 48
OUT = f"data/cpairs_{SPLIT.lower()}.jsonl"

_NAME = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                   r"Instance|Axiom|Proposition|Example|Let|Program\s+\w+)\s+"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")


def declname(t):
    m = _NAME.match(t or "")
    return m.group(1).split(".")[-1] if m else None


cc = yaml.safe_load(open(os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), N)
sdb = SentenceDB.load(conf.sentence_db_loc)
pf = PremiseFilterConf.from_yaml(tdc["formatter_conf"]["premise"]["premise_filter"])
pfilter = PremiseFilter(pf.coq_excludes, pf.non_coq_excludes, pf.general_excludes)

n_out = 0
with open(OUT, "w") as fo:
    for i in range(N):
        try:
            e = ds.raw_example(i)
        except Exception:
            continue
        st = getattr(e, "proof_state", "") or ""
        golds = gold_lemmas(e.next_steps[0] if getattr(e, "next_steps", None) else "",
                            local_names(st))
        if not golds:
            continue
        sid = ds.shuffled_idx.get_idx(ds.split, i)
        try:
            dp = DatasetFile.load(conf.data_loc / "data_points" / sid.file, sdb)
            proof = dp.proofs[sid.proof_idx]
            step = proof.steps[sid.step_idx]
        except Exception:
            continue
        if not step.goals:
            continue
        pool = [p for p in dp.get_premises_before(proof) if pfilter.filter_premise(p)]
        if not pool:
            continue
        texts = [getattr(p, "text", "") or "" for p in pool]
        gidx = [j for j, t in enumerate(texts) if declname(t) in golds]
        if not gidx:
            continue
        h, g = get_ids_from_goal(step.goals[0])
        tf = tf_idf(h + g, [get_ids_from_sentence(p) for p in pool])
        order = sorted(range(len(pool)), key=lambda j: -tf[j])
        negs = [j for j in order if j not in set(gidx)][:NEG]
        fo.write(json.dumps({
            "goal": st[:4000],
            "pos": [texts[j][:600] for j in gidx[:3]],
            "neg": [texts[j][:600] for j in negs],
            "pos_rank": [order.index(j) for j in gidx[:3]],
        }) + "\n")
        n_out += 1
        if n_out % 100 == 0:
            print(f"  {n_out}건", flush=True)
print(f"\n■ {SPLIT}: {n_out}건 → {OUT}")
