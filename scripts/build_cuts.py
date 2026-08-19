#!/usr/bin/env python3
"""★ cut 을 **미리 만들어 파일로** 저장한다 — 학습 머신(Vast.ai)에 Coq 이 없어도 되게.

## 용어

  · **cut**   증명에서 보조 명제를 세워 쓰는 것. Coq 에서는 `assert (P) as H`.
              논리학의 cut rule 과 같다. gold tactic 이 쓰는 lemma L 이 검색 결과에
              없으면, L 과 **같은 명제** L' 을 cut 으로 세우고 그것을 쓴다.
  · **gold tactic**  데이터셋의 정답 tactic.
  · **gold lemma**   그 tactic 이 참조하는 lemma.
  · **검색 실패**    gold lemma 가 프롬프트에 들어가는 상위 N 개 안에 없는 것.

## 왜 미리 만드나

cut 의 명제를 정확히 얻으려면 그 증명 지점에서 Coq 에 `Check (L a b).` 를 물어야 한다
(암묵인자·Section 변수가 인스턴스화된 형태가 나온다). Vast.ai 학습 머신에는 Coq 이 없고
opam 환경을 새로 만드는 것은 느리고 불안정하다. → **여기서 만들어 파일로 넘긴다.**

## 2단계 전략 (비용)

  ① **Coq 없는 경로**  `sentences.db` 의 premise 원문에서 명제를 뽑는다(`statement_of`).
                       인스턴스화가 안 돼 품질은 낮지만 **즉시** 만들어진다.
  ② **Coq 경로**       ①이 실패한 것만. 파일 단위로 묶어 한 번의 elaboration 으로
                       그 파일의 여러 지점을 처리한다(스텝마다 열면 10배 느리다).

이 스크립트는 ①만 한다(②는 `build_cuts_coq.py`). ①의 성공률을 보고 ②의 규모를 정한다.

## 출력 형식 (중복 제거)

같은 lemma 가 여러 스텝에서 빠지면 명제가 같다 → **사전 하나 + 스텝별 이름 목록**.

    {"kind":"stmt", "name":"Nat.add_comm", "ty":"forall n m : nat, n + m = m + n"}
    {"kind":"step", "sid":"파일#증명#스텝", "miss":["Nat.add_comm"], "tac":"rewrite ..."}

사용: python3 scripts/build_cuts.py [훑을 예제수] [train|val|test] [out.jsonl]
"""
import collections
import copy
import json
import os
import sys
import time

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
from tactic_gen.assert_split import statement_of, transform  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "train").upper()
OUT = sys.argv[3] if len(sys.argv) > 3 else f"data/cuts_{SPLIT.lower()}.jsonl"
TOPN = int(os.environ.get("TOPN", "100"))

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), 10 ** 9)
sdb = SentenceDB.load(conf.sentence_db_loc)
pf = PremiseFilterConf.from_yaml(tdc["formatter_conf"]["premise"]["premise_filter"])
pfilter = PremiseFilter(pf.coq_excludes, pf.non_coq_excludes, pf.general_excludes)

st = collections.Counter()
stmts: dict[str, str] = {}
need_coq: list[dict] = []
t0 = time.time()
fo = open(OUT, "w")

for i in range(min(N, len(ds))):
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    state = getattr(e, "proof_state", "") or ""
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    golds = gold_lemmas(tac, local_names(state))
    if not golds:
        continue
    st["gold 사용 스텝"] += 1
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
        st["gold 가 풀에 없음"] += 1
        continue

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
    per_name: dict = {}
    for j in gset:
        per_name.setdefault(names[j], []).append(j)
    missing = [nm for nm, js in per_name.items() if min(pos[j] for j in js) >= TOPN]
    if not missing:
        st["검색 성공 → cut 불필요"] += 1
        continue
    st["cut 필요 스텝"] += 1

    ok_names, bad_names = [], []
    for nm in missing:
        j = per_name[nm][0]
        if nm in stmts:
            ok_names.append(nm)
            continue
        s_ = statement_of(texts[j])
        if s_:
            stmts[nm] = s_
            ok_names.append(nm)
            st["① Coq 없이 명제 확보"] += 1
        else:
            bad_names.append(nm)
            st["② Coq 필요"] += 1
    # cut 문장을 실제로 조립해 본다 (문법이 서는지 — 여기서 실패하면 학습에 못 쓴다)
    cut_tac = None
    if ok_names and not bad_names:
        try:
            cut_tac = transform(tac, [(nm, texts[per_name[nm][0]]) for nm in ok_names],
                                proof_script=getattr(e, "proof_script", "") or "",
                                state=state, premises=texts[:200])
        except Exception:
            cut_tac = None
        st["cut tactic 조립 성공" if cut_tac else "cut tactic 조립 실패"] += 1
    rec = {"kind": "step", "sid": f"{sid.file}#{sid.proof_idx}#{sid.step_idx}",
           "miss": missing, "have": ok_names, "need_coq": bad_names,
           "tac": tac[:400]}
    if cut_tac:
        rec["cut"] = cut_tac[:800]
    fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if bad_names:
        need_coq.append(rec)
    if st["cut 필요 스텝"] % 200 == 0:
        print(f"   … cut {st['cut 필요 스텝']} ({time.time()-t0:.0f}s)", flush=True)

for nm, ty in stmts.items():
    fo.write(json.dumps({"kind": "stmt", "name": nm, "ty": ty},
                        ensure_ascii=False) + "\n")
fo.close()

print(f"\n■ {SPLIT} — cut 사전생성 ① Coq 없는 경로  ({time.time()-t0:.0f}s)")
for k in ("gold 사용 스텝", "gold 가 풀에 없음", "검색 성공 → cut 불필요", "cut 필요 스텝",
          "① Coq 없이 명제 확보", "② Coq 필요", "cut tactic 조립 성공",
          "cut tactic 조립 실패"):
    print(f"   {k:26s} {st[k]:7d}")
c = max(st["① Coq 없이 명제 확보"] + st["② Coq 필요"], 1)
print(f"\n   ① 만으로 명제를 얻은 비율   {st['① Coq 없이 명제 확보']/c*100:5.1f}%")
print(f"   ② Coq 이 필요한 스텝        {len(need_coq)}")
n_cut = max(st["cut 필요 스텝"], 1)
print(f"   cut tactic 조립 성공률      "
      f"{st['cut tactic 조립 성공']/n_cut*100:5.1f}%")
sz = os.path.getsize(OUT)
print(f"\n   → {OUT}  ({sz/1e6:.1f} MB · 고유 명제 {len(stmts)})")
