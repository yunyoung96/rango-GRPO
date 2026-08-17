#!/usr/bin/env python3
"""검색 특징을 **한 번만 추출해 디스크에 저장**한다 (학습 실험을 빠르게 반복하려고).

특징 추출이 139ms/건이라 학습안을 바꿀 때마다 다시 뽑으면 실험이 느리다. 사례당
(후보별 특징 벡터 + gold 인덱스)를 jsonl 로 떨궈두고, 학습 스크립트는 이것만 읽는다.

저장하는 특징 (후보마다):
    0 A' 매칭크기   1 B head일치   2 C 연산자   3 D 모양
    4 C' 결론head  5 E 가설매칭   6 tfidf점수  7 이름subword점수

용량을 줄이려고 **tfidf 상위 CAP 개**만 저장한다(그 밖에 gold 가 있으면 사례를 버린다).

사용: python3 scripts/dump_retrieval_features.py <train|val|test> [n] [out.jsonl]
"""
import collections
import copy
import json
import math
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

sys.path.insert(0, "scripts")
os.environ.setdefault("POOL_CAP", "100000")
# ★ research_structural 은 **모듈 레벨에서** LmDataset 을 만든다. 그대로 import 하면
#   데이터를 두 번 로드해 몇 분을 버린다 → argv 를 잠시 바꿔 최소 크기로 로드시킨다.
_argv = sys.argv
sys.argv = [_argv[0], "1", "train"]
import research_structural as RS  # noqa: E402
sys.argv = _argv

SPLIT = (_argv[1] if len(_argv) > 1 else "train").upper()
N = int(_argv[2]) if len(_argv) > 2 else 3000
OUT = _argv[3] if len(_argv) > 3 else f"data/retfeat_{SPLIT.lower()}.jsonl"
CAP = int(os.environ.get("CAP", "400"))

cc = yaml.safe_load(open(os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), N)
sdb = SentenceDB.load(conf.sentence_db_loc)
pf_conf = PremiseFilterConf.from_yaml(tdc["formatter_conf"]["premise"]["premise_filter"])
pfilter = PremiseFilter(pf_conf.coq_excludes, pf_conf.non_coq_excludes,
                        pf_conf.general_excludes)

n_out = 0
n_cap = 0
with open(OUT, "w") as fo:
    for i in range(N):
        try:
            e = ds.raw_example(i)
        except Exception:
            continue
        st = getattr(e, "proof_state", "") or ""
        loc = local_names(st)
        golds = gold_lemmas(e.next_steps[0] if getattr(e, "next_steps", None) else "", loc)
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
        names = [RS.declname(getattr(p, "text", "")) for p in pool]
        gset = {j for j, nm in enumerate(names) if nm in golds}
        if not gset:
            continue
        gs = RS.goal_struct(st)
        if gs is None:
            continue

        h_ids, g_ids = get_ids_from_goal(step.goals[0])
        docs = [get_ids_from_sentence(p) for p in pool]
        tf = tf_idf(h_ids + g_ids, docs)
        ns_docs = [list(d) + [w for w in RS._SUBW.split(nm or "") if len(w) >= 2] * 2
                   for d, nm in zip(docs, names)]
        ns = tf_idf(h_ids + g_ids, ns_docs)

        order = sorted(range(len(pool)), key=lambda j: -tf[j])[:CAP]
        oset = set(order)
        if not (gset & oset):
            n_cap += 1
            continue
        keep = list(order)
        for j in gset:                      # gold 는 CAP 밖이어도 반드시 넣는다
            if j not in oset:
                keep.append(j)

        df: collections.Counter = collections.Counter()
        pss = {}
        for j in keep:
            ps = RS.prem_struct(getattr(pool[j], "text", "") or "")
            pss[j] = ps
            if ps is not None:
                for k in ps[5]:
                    df[k] += 1
        nd = max(len(keep), 1)
        idf = {k: math.log(nd / v) for k, v in df.items()}

        rows = []
        for j in keep:
            ps = pss[j]
            if ps is None:
                f = [0.0] * 6
            else:
                f = [RS.sig_match_size(gs, ps), RS.sig_head(gs, ps), RS.sig_ops(gs, ps),
                     RS.sig_shape(gs, ps), RS.sig_concl_heads(gs, ps, idf),
                     RS.sig_hyp_match(gs, ps)]
            f += [tf[j], ns[j]]
            rows.append([round(x, 5) for x in f])
        fo.write(json.dumps({
            "feats": rows,
            "gold": [keep.index(j) for j in gset if j in keep],
            "npool": len(pool),
        }) + "\n")
        n_out += 1
        if n_out % 50 == 0:
            print(f"  {n_out}건 저장 ({i}/{N} 훑음)", flush=True)

print(f"\n■ {SPLIT}: {n_out}건 저장 → {OUT} (gold 가 tfidf 상위 {CAP} 밖이라 버림: {n_cap})")
