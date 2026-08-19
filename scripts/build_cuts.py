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

# ★ 위험 필터를 기본으로 끈다. B 실측에서 필터별 실패율이 0~40% 라 막는 것보다
#   통과시키고 Coq 으로 검증해 거르는 편이 훨씬 많이 건진다.
#   ★★ 반드시 **import 보다 먼저** — assert_split 이 import 시점에 이 값을 읽는다.
#      (뒤에 두면 조용히 무시되고 SSReflect 가 전부 막힌다 — 실측으로 당했다)
os.environ.setdefault("ASSERT_RISK", "0")
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
from tactic_gen.applicable import decompose  # noqa: E402

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

class _G:
    def __init__(self, g, h):
        self.goal, self.hyps = g, h


st = collections.Counter()
fail_why = collections.Counter()
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
            import tactic_gen.assert_split as _AS
            _AS.WHY.clear()
            cut_tac = transform(tac, [(nm, texts[per_name[nm][0]]) for nm in ok_names],
                                proof_script=getattr(e, "proof_script", "") or "",
                                state=state, premises=texts[:200])
            A_WHY = list(_AS.WHY)
        except Exception as ex:
            cut_tac = None
            A_WHY = [f"예외 {type(ex).__name__}"]
        st["cut tactic 조립 성공" if cut_tac else "cut tactic 조립 실패"] += 1
        if not cut_tac:
            for _w in (A_WHY or ["이유 미기록"]):
                fail_why[_w] += 1
    # ★ 키는 **collate 가 계산할 수 있는 형태**여야 한다.
    #   sid.file 은 평탄화된 이름(`a-b-c.v`)이고 example.file_name 은 원경로
    #   (`repos/a/b/c.v`)라 서로 다르다. collate 에는 file_name 만 있으므로 그쪽에 맞춘다.
    _key = (f"{getattr(e, 'file_name', '')}:"
            f"{getattr(e, 'proof_idx', '')}:{getattr(e, 'step_idx', '')}")
    # ★ cut 을 만들어도 **그 L' 를 goal 로 재검색했을 때 L 이 안 잡히면 소용이 없다.**
    #   (how-to-learn.txt §3) 그런 스텝은 cut 을 내보내지 않는다 → 학습은 원래 gold
    #   tactic 을 쓰고 환각을 감수한다. 여기서 걸러야 쓸모없는 cut 을 학습시키지 않는다.
    if cut_tac:
        for nm in ok_names:
            j0 = per_name[nm][0]
            d0 = decompose(texts[j0])
            if d0 is None:
                cut_tac = None
                fail_why["재검색: L' 명제를 못 만듦"] += 1
                break
            q = " ".join(d0[2])
            _, qi = get_ids_from_goal(_G(q, []))
            tf2 = tf_idf(qi, docs)
            try:
                sc2 = structural_scores(q, hy, texts, tf2, query_ids=qi, docs=docs)
            except Exception:
                sc2 = tf2
            o2 = sorted(range(len(pool)), key=lambda x: -sc2[x])
            p2 = {x: r for r, x in enumerate(o2)}
            if min(p2[x] for x in per_name[nm]) >= TOPN:
                cut_tac = None
                st["cut 해도 재검색 실패 → gold 유지"] += 1
                fail_why["재검색 실패(L' 로도 L 이 안 잡힘)"] += 1
                break
        if cut_tac:
            st["★ cut 유효(재검색 성공)"] += 1

    rec = {"kind": "step", "sid": _key,
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
print(f"\n   ■ 3단계 판정 (how-to-learn.txt)")
print(f"     ① 검색 성공 → gold tactic 그대로   {st['검색 성공 → cut 불필요']:6d}")
print(f"     ② cut 유효  → cut 으로 치환        {st['★ cut 유효(재검색 성공)']:6d}")
print(f"     ③ cut 해도 재검색 실패 → gold 유지  {st['cut 해도 재검색 실패 → gold 유지']:6d}"
      f"   (환각 감수)")
print(f"\n   ① 만으로 명제를 얻은 비율   {st['① Coq 없이 명제 확보']/c*100:5.1f}%")
print(f"   ② Coq 이 필요한 스텝        {len(need_coq)}")
# ★ 분모를 정확히: Coq 이 필요한 스텝은 애초에 **조립을 시도하지 않는다**.
tried = st["cut tactic 조립 성공"] + st["cut tactic 조립 실패"]
n_cut = max(st["cut 필요 스텝"], 1)
print(f"\n   조립 시도               {tried}  (Coq 필요분 {n_cut - tried} 제외)")
print(f"   조립 성공률(시도분)      {st['cut tactic 조립 성공']/max(tried,1)*100:5.1f}%")
print(f"   cut 확보율(전체 대비)    {st['cut tactic 조립 성공']/n_cut*100:5.1f}%")
if fail_why:
    print(f"\n   ■ 조립 실패 이유")
    for k, v in fail_why.most_common(10):
        print(f"     [{v:5d}] {k}")
sz = os.path.getsize(OUT)
print(f"\n   → {OUT}  ({sz/1e6:.1f} MB · 고유 명제 {len(stmts)})")
