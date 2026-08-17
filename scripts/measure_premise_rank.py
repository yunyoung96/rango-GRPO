#!/usr/bin/env python3
"""**gold lemma 는 검색 순위 몇 위인가** — "정보를 얼마나 더 들어야 하나"에 숫자로 답한다.

## 배경

학습 타깃이 쓰는 lemma 가 프롬프트에 없으면, 그 예제는 **암기를 훈련**한다
(읽을 수 없는 이름을 뱉으라고 가르치므로). 이걸 없애려면 검색 커버리지를 올려야 하는데,
"몇 개까지 늘리면 되나"를 모르면 토큰만 낭비한다.

그래서 num_premises 를 크게 잡아 **한 번만** 검색하고, 상위 k 안에 gold 가 있는지를
모든 k 에 대해 동시에 센다. 곡선이 꺾이는 지점이 곧 필요한 후보 수다.

  · 순위가 100 위 안쪽에 몰려 있다 → 지금 설정으로 거의 다 잡고 있다. 늘려도 소용없다
  · 꼬리가 길다                    → 후보 수를 늘리면 커버리지가 오른다 (토큰 비용과 교환)
  · 아예 없다(검색 대상에 부재)     → 후보를 늘려도 못 잡는다. 검색 **대상**이 문제

사용: python3 scripts/measure_premise_rank.py [n] [num_premises] [train|test|val]
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
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    rerank_premises)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
BIG = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
SPLIT = (sys.argv[3] if len(sys.argv) > 3 else "train").upper()
CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")

cc = yaml.safe_load(open(CONF))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"]["num_premises"] = BIG          # ★ 크게 뽑아 순위 전체를 본다
# ★ [PROOFS] 용 BM25 유사증명 검색은 이 측정에 필요 없는데 **예제당 수십 초**를 먹는다
#   (py-spy 로 확인: 병목이 premise TF-IDF 가 아니라 proof_retriever 의 bm25 였다).
#   conf 에서 proof_ret 를 빼면 proof_retriever=None 이 되어 통째로 건너뛴다.
# 검색 **대상**을 바꿔본다: proj-thm 은 Coq 표준 라이브러리의 Theorem/Lemma/Definition 을
# 통째로 제외한다(premise_filter.PROJ_THM_FILTER_CONF 의 coq_excludes). 표준 lemma 를 쓰는
# tactic 은 검색으로 절대 못 얻으므로 암기에 의존하게 된다 → all 로 풀면 얼마나 회복되나.
_KF = os.environ.get("KNOWN_FILTER", "")
if _KF:
    tdc["formatter_conf"]["premise"]["premise_filter"]["known_filter"] = _KF
if os.environ.get("SKIP_PROOF_RET", "1") == "1":
    tdc["formatter_conf"].pop("proof_ret", None)
    tdc["formatter_conf"].pop("num_proofs", None)
ds = LmDataset.from_conf(TacticDataConf.from_yaml(tdc), getattr(Split, SPLIT), N)

_ID = re.compile(r"\b([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)\b")
_KW = {"rewrite", "apply", "eapply", "erewrite", "in", "with", "by", "at", "using",
       "auto", "eauto", "lia", "omega", "now", "intros", "destruct", "simpl", "unfold",
       "induction", "exact", "constructor", "reflexivity", "congruence", "discriminate"}
_NAME = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                   r"Instance|Axiom|Proposition|Example|Let)\s+"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
# 지역 가설(H, H0, IHl, e0 …)은 검색 대상이 아니므로 제외해야 수치가 왜곡되지 않는다
_LOCAL = re.compile(r"^(?:H\d*|H'+|IH\w*|Heq\w*|E\d*|e\d*|n\d*|l\d*|x\d*|y\d*|v\d*)$")

KS = [10, 25, 50, 100, 200, 500, 1000]
hit_raw = collections.Counter()
hit_rr = collections.Counter()
ranks_raw, ranks_rr = [], []
n_gold = n_absent = 0
n_scanned = 0
absent_ex = []

import time
_t0 = time.time()
for i in range(N):
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    n_scanned += 1
    if n_scanned % 25 == 0:
        print(f"  … {n_scanned}/{N} 훑음 · gold {n_gold}건 · {time.time()-_t0:.0f}s",
              flush=True)
    prems = list(getattr(e, "premises", None) or [])
    if not prems:
        continue
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    head = tac.split()[0].lower().strip(";.") if tac.split() else ""
    if head not in ("rewrite", "apply", "eapply", "erewrite"):
        continue
    cand = [x for x in _ID.findall(tac[len(head):])
            if x not in _KW and not x.isdigit() and not _LOCAL.match(x)]
    if not cand:
        continue
    base = cand[0].split(".")[-1]
    n_gold += 1

    def find(ps):
        for j, p in enumerate(ps):
            t = p if isinstance(p, str) else getattr(p, "text", str(p))
            m = _NAME.match(t)
            if m and m.group(1).split(".")[-1] == base:
                return j
        return -1

    r = find(prems)
    if r < 0:
        n_absent += 1
        if len(absent_ex) < 6:
            absent_ex.append((base, tac[:60], len(prems)))
        continue
    ranks_raw.append(r)
    for k in KS:
        hit_raw[k] += (r < k)
    rr = rerank_premises(e)
    r2 = find(rr) if rr else r
    ranks_rr.append(r2)
    for k in KS:
        hit_rr[k] += (r2 < k)

print(f"\n■ {SPLIT} — 훑은 예제 {n_scanned} · gold 가 lemma 를 쓰는 step {n_gold}건 "
      f"(후보 {BIG}개까지 검색)")
print(f"   후보 {BIG}개 안에도 **없음**: {n_absent}/{n_gold} = {n_absent/max(n_gold,1)*100:5.1f}%"
      f"   ← 이건 후보를 늘려도 못 잡는다")
if absent_ex:
    print("      예:", ", ".join(f"{b}({t[:26]}…)" for b, t, _ in absent_ex[:4]))
found = n_gold - n_absent
print(f"\n   상위 k 안에 gold 가 있는 비율 (전체 {n_gold}건 대비)")
print(f"     k      원순위(tfidf)    재랭킹 후")
for k in KS:
    print(f"     {k:<6d} {hit_raw[k]:4d} = {hit_raw[k]/max(n_gold,1)*100:5.1f}%"
          f"      {hit_rr[k]:4d} = {hit_rr[k]/max(n_gold,1)*100:5.1f}%")
if ranks_raw:
    rs = sorted(ranks_raw)
    print(f"\n   찾은 {found}건의 순위 분포: 중앙 {rs[len(rs)//2]} · "
          f"75% {rs[int(len(rs)*.75)]} · 90% {rs[int(len(rs)*.9)]} · 최대 {rs[-1]}")
