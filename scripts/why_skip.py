#!/usr/bin/env python3
"""**포기 이유**를 Coq 없이 빠르게 집계한다.

`risky_tactic` 은 gold tactic 문자열만 보고, `statement_of` 는 premise 원문만 본다 —
둘 다 Coq 실행이 필요 없다. 전체 포기 중 이 둘이 차지하는 비중을 먼저 알면
"필터가 과한가"를 즉시 판단할 수 있다(동적 검증은 스텝당 수 초라 표본이 작다).

사용: python3 scripts/why_skip.py [스텝수] [train|val|test]
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
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402
from tactic_gen import assert_split as A  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "test").upper()

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), N * 4)

stat = collections.Counter()
tac_kind = collections.Counter()
ty_kind = collections.Counter()

for i in range(N * 4):
    if stat["gold lemma 사용 스텝"] >= N:
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
    prems = getattr(e, "premises", None) or []
    ptexts = [p if isinstance(p, str) else getattr(p, "text", str(p)) for p in prems]
    # (premise 매칭은 아래에서 따로)
    stat["gold lemma 사용 스텝"] += 1

    # ① tactic 만 보고 걸리는 것 — Coq 불필요
    if A.risky_tactic(tac):
        stat["risky_tactic 에 걸림"] += 1
        tac_kind[A._tac_kind(tac)] += 1
    # ② premise 원문에서 statement 를 못 뽑는 것
    hit_prem = [pt for pt in ptexts if any(
        pt.split(":")[0].strip().endswith(" " + g.split(".")[-1]) for g in golds)]
    if hit_prem:
        stmt = A.statement_of(hit_prem[0])
        if not stmt:
            stat["statement 추출 실패(정의 등)"] += 1
        elif A.risky_type(stmt):
            stat["premise 원문이 risky_type"] += 1
            ty_kind[A._ty_kind(stmt)] += 1

n = max(stat["gold lemma 사용 스텝"], 1)
print(f"\n■ {SPLIT} — 포기 이유 (정적, n={n})")
for k in ("risky_tactic 에 걸림", "premise 원문이 risky_type", "statement 추출 실패(정의 등)"):
    print(f"   {k:26s} {stat[k]:5d}  ({stat[k]/n*100:5.1f}%)")
if tac_kind:
    print(f"\n   risky_tactic 세부:")
    for k, v in tac_kind.most_common(12):
        print(f"     [{v:4d}] {k}")
if ty_kind:
    print(f"\n   risky_type 세부:")
    for k, v in ty_kind.most_common(12):
        print(f"     [{v:4d}] {k}")
