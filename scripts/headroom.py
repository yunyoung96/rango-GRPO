#!/usr/bin/env python3
"""검색 개선의 **여지가 어디에 있나** — 아이디어를 고르기 전에 상한부터 잰다.

재는 것
  ① 파서 recall      premise·gold 가 파싱되는 비율 (구조 신호 전체의 상한)
  ② stage1 상한      gold 가 tfidf 상위 N 안에 드는 비율 (재랭킹이 손댈 수 있는 범위)
  ③ head 인덱스 여지  결론 head 가 goal 과 일치하는 premise 만 모으면 몇 개이고
                     gold 를 얼마나 담나 (tfidf 밖의 gold 를 건질 수 있는가)
  ④ R vs ALL 격차    다중 lemma 스텝에서 얼마나 잃나 (다양성 재랭킹 여지)
  ⑤ gold 종류        Lemma/Theorem 인가 Definition 인가 (구조 신호가 안 통하는 쪽)

사용: python3 scripts/headroom.py [n] [train|val|test]
"""
import collections
import copy
import os
import re
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
from tactic_gen.tier_rank import declname, goal_struct, prem_struct  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "test").upper()
CAPS = (100, 400, 1000, 2000, 5000)

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), 40000)
sdb = SentenceDB.load(conf.sentence_db_loc)
pf = PremiseFilterConf.from_yaml(tdc["formatter_conf"]["premise"]["premise_filter"])
pfilter = PremiseFilter(pf.coq_excludes, pf.non_coq_excludes, pf.general_excludes)

_KIND = re.compile(r"^\s*(\w+)")
st_ = collections.Counter()
cap_any = collections.Counter()
cap_all = collections.Counter()
kinds = collections.Counter()
head_sz = []
head_hit = 0
head_rescue = 0
n = 0
np_ok = np_all = 0

for i in range(40000):
    if n >= N:
        break
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    st = getattr(e, "proof_state", "") or ""
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    golds = gold_lemmas(tac, local_names(st))
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
    names = [declname(t) for t in texts]
    gset = {j for j, nm in enumerate(names) if nm and nm in golds}
    if not gset:
        continue
    n += 1

    # ① 파서 — gold 쪽
    gs = goal_struct(st)
    st_["goal 파싱 성공"] += (gs is not None)
    for j in gset:
        ps = prem_struct(texts[j])
        ok = ps is not None and ps[1] is not None
        st_["gold 파싱 성공"] += ok
        st_["gold 총"] += 1
        m = _KIND.match(texts[j])
        kinds[(m.group(1) if m else "?") + ("" if ok else " (파싱실패)")] += 1

    # ① 파서 — 풀 전체(표본)
    for j in range(0, len(pool), max(1, len(pool) // 50)):
        ps = prem_struct(texts[j])
        np_all += 1
        np_ok += (ps is not None and ps[1] is not None)

    # ② stage1 상한
    docs = [get_ids_from_sentence(p) for p in pool]
    h_ids, g_ids = get_ids_from_goal(step.goals[0])
    tf = tf_idf(h_ids + g_ids, docs)
    order = sorted(range(len(pool)), key=lambda j: -tf[j])
    pos = {j: r for r, j in enumerate(order)}
    per = {}
    for j in gset:
        per[names[j]] = min(per.get(names[j], 10 ** 9), pos[j])
    for c in CAPS:
        cap_any[c] += (min(per.values()) < c)
        cap_all[c] += (max(per.values()) < c)

    # ③ head 인덱스 — 결론 head 가 goal 과 같은 premise 만 모으면?
    if gs is not None and gs[2] is not None:
        gh = gs[2]
        idx = [j for j in range(len(pool))
               if (ps := prem_struct(texts[j])) is not None and ps[2] == gh]
        head_sz.append(len(idx))
        s_ = set(idx)
        head_hit += all(j in s_ for j in gset)
        # tfidf 2000 밖인데 head 인덱스에는 있는 gold 가 있나 (= 건질 수 있는가)
        out = [j for j in gset if pos[j] >= 2000]
        head_rescue += bool(out) and all(j in s_ for j in out)

    # ④ 다중 lemma
    st_["lemma 2개 이상 필요"] += (len(per) >= 2)

print(f"\n■ {SPLIT} — 검색 개선 여지 (n={n})")
print(f"\n① 파서 recall  (구조 신호 전체의 상한)")
print(f"   goal 파싱 성공            {st_['goal 파싱 성공']/max(n,1)*100:5.1f}%")
print(f"   gold premise 파싱 성공    {st_['gold 파싱 성공']/max(st_['gold 총'],1)*100:5.1f}%"
      f"  ({st_['gold 파싱 성공']}/{st_['gold 총']})")
print(f"   풀 전체 표본 파싱 성공     {np_ok/max(np_all,1)*100:5.1f}%  ({np_ok}/{np_all})")

print(f"\n② stage1 상한  (gold 가 tfidf 상위 N 안)")
print(f"   {'N':>6s} {'하나라도':>9s} {'전부':>9s}")
for c in CAPS:
    print(f"   {c:6d} {cap_any[c]/max(n,1)*100:8.1f}% {cap_all[c]/max(n,1)*100:8.1f}%")

if head_sz:
    head_sz.sort()
    print(f"\n③ head 인덱스  (결론 head 가 goal 과 같은 premise 만)")
    print(f"   크기 중앙값 {head_sz[len(head_sz)//2]}  평균 {sum(head_sz)/len(head_sz):.0f}")
    print(f"   gold 를 전부 담는 비율    {head_hit/max(len(head_sz),1)*100:5.1f}%")
    print(f"   tfidf 2000 밖 gold 를 건짐 {head_rescue/max(len(head_sz),1)*100:5.1f}%")

print(f"\n④ 다중 lemma 스텝           {st_['lemma 2개 이상 필요']/max(n,1)*100:5.1f}%")
print(f"\n⑤ gold 선언 종류 (많은 순)")
for k, v in kinds.most_common(10):
    print(f"   {k:26s} {v:5d}  ({v/max(st_['gold 총'],1)*100:4.1f}%)")
