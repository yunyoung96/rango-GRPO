#!/usr/bin/env python3
"""cut 을 미리 만들어 넘길 때의 **규모**를 잰다 — 파일 크기와 Coq 실행 시간.

  · 전체 스텝 중 gold lemma 를 쓰는 비율
  · 그중 검색이 실패해 cut 이 필요한 비율
  · 스텝당 cut 개수 (다중 lemma)
  · cut 문장 길이 → 파일 크기 추정
  · 파일당 스텝 수 → Coq 호출을 파일 단위로 묶었을 때의 절감

사용: python3 scripts/size_cuts.py [훑을 예제수] [train|val|test]
"""
import collections
import copy
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
from tactic_gen.tier_rank import declname, structural_scores  # noqa: E402
from tactic_gen.assert_split import statement_of  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "train").upper()
TOPN = int(os.environ.get("TOPN", "100"))       # 프롬프트에 들어가는 premise 수

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), 10 ** 7)
sdb = SentenceDB.load(conf.sentence_db_loc)
pf = PremiseFilterConf.from_yaml(tdc["formatter_conf"]["premise"]["premise_filter"])
pfilter = PremiseFilter(pf.coq_excludes, pf.non_coq_excludes, pf.general_excludes)

try:
    TOTAL = len(ds)
except Exception:
    TOTAL = -1

st = collections.Counter()
cut_lens = []
per_step = collections.Counter()
files = collections.Counter()
scanned = 0

for i in range(N):
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    scanned += 1
    state = getattr(e, "proof_state", "") or ""
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    golds = gold_lemmas(tac, local_names(state))
    if not golds:
        continue
    st["gold lemma 사용 스텝"] += 1
    sid = ds.shuffled_idx.get_idx(ds.split, i)
    files[sid.file] += 1
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
        st["gold 가 풀에 없음"] += 1
        continue
    st["gold 가 풀에 있음"] += 1
    docs = [get_ids_from_sentence(p) for p in pool]
    h_ids, g_ids = get_ids_from_goal(step.goals[0])
    tf = tf_idf(h_ids + g_ids, docs)
    gl = state.split("\n\n")[-1] if "\n\n" in state else state
    hy = state.split("\n\n")[0].split("\n") if "\n\n" in state else []
    try:
        sc = structural_scores(gl, hy, texts, tf, query_ids=h_ids + g_ids, docs=docs)
    except Exception:
        sc = tf
    o = sorted(range(len(pool)), key=lambda j: -sc[j])
    pos = {j: r for r, j in enumerate(o)}
    per_name = {}
    for j in gset:
        per_name.setdefault(names[j], []).append(j)
    missing = [nm for nm, js in per_name.items() if min(pos[j] for j in js) >= TOPN]
    if not missing:
        st["검색 성공 → cut 불필요"] += 1
        continue
    st["★ cut 필요 스텝"] += 1
    per_step[len(missing)] += 1
    for nm in missing:
        j = per_name[nm][0]
        s_ = statement_of(texts[j])
        cut_lens.append(len(s_ or texts[j]))

g = max(st["gold lemma 사용 스텝"], 1)
ncut = sum(k * v for k, v in per_step.items())
print(f"\n■ {SPLIT} — cut 사전생성 규모 (프롬프트 상위 {TOPN}개 기준)")
print(f"   전체 스텝 {TOTAL if TOTAL > 0 else '?'} · 훑은 예제 {scanned}")
print(f"\n   gold lemma 사용 스텝     {st['gold lemma 사용 스텝']:6d}  "
      f"({st['gold lemma 사용 스텝']/max(scanned,1)*100:5.1f}% of 전체)")
print(f"   ├ gold 가 풀에 있음       {st['gold 가 풀에 있음']:6d}")
print(f"   ├ gold 가 풀에 없음       {st['gold 가 풀에 없음']:6d}  (cut 불가 — 원리적 한계)")
print(f"   ├ 검색 성공 → cut 불필요   {st['검색 성공 → cut 불필요']:6d}  "
      f"({st['검색 성공 → cut 불필요']/g*100:5.1f}%)")
print(f"   └ ★ cut 필요             {st['★ cut 필요 스텝']:6d}  "
      f"({st['★ cut 필요 스텝']/g*100:5.1f}%)")
print(f"\n   cut 개수 총 {ncut}  (스텝당 {ncut/max(st['★ cut 필요 스텝'],1):.2f}개)")
for k in sorted(per_step):
    print(f"     cut {k}개 필요: {per_step[k]:5d} 스텝")
if cut_lens:
    cut_lens.sort()
    avg = sum(cut_lens) / len(cut_lens)
    print(f"\n   cut 문장 길이  평균 {avg:.0f}자 · 중앙 {cut_lens[len(cut_lens)//2]}자 "
          f"· 최대 {cut_lens[-1]}자")

if TOTAL > 0 and scanned:
    sc_r = TOTAL / scanned
    tot_cut = ncut * sc_r
    print(f"\n■ 전체 {SPLIT} 로 환산 (×{sc_r:.1f})")
    print(f"   cut 필요 스텝  약 {st['★ cut 필요 스텝']*sc_r:,.0f}")
    print(f"   cut 총 개수    약 {tot_cut:,.0f}")
    if cut_lens:
        mb = tot_cut * (avg + 120) / 1e6
        print(f"   파일 크기      약 {mb:,.0f} MB   ← 전송은 문제 없음")
    print(f"\n   Coq 시간 (스텝당 한 번 호출, 8초 가정)")
    hrs = st['★ cut 필요 스텝'] * sc_r * 8 / 3600
    print(f"     단일 프로세스 {hrs:,.0f} 시간   ← ★ 여기가 병목")
    print(f"     8 병렬        {hrs/8:,.0f} 시간")
    nf = len(files)
    print(f"\n   파일당 gold 스텝 {st['gold lemma 사용 스텝']/max(nf,1):.1f}개 "
          f"(고유 파일 {nf}) — 파일 단위로 묶으면 그만큼 절감")
