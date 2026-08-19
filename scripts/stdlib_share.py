#!/usr/bin/env python3
"""★ premise·gold 중 **표준 라이브러리** 비중 — 익명화에서 빼야 할 대상이 얼마나 되나.

## 왜

익명화의 목적은 "그 프로젝트에만 통하는 이름을 외워서 찍는 습관"을 끊는 것이다.
그런데 `Nat.add_comm` 같은 **표준 라이브러리** lemma 를 아는 것은 암기가 아니라
**어느 프로젝트에서나 통하는 진짜 지식**이다. 익명화하면 그 지식을 못 쓰게 된다.

현재 `build_mapping` 은 premise lemma 이름을 **출처 구분 없이 전부** `L#` 로 바꾼다
(`renameable()` 은 정의 인덱스에만 있는 이름을 허용해 premise 에는 못 쓴다 —
실측 235건 중 134건이 걸려 하나도 치환 안 됐다는 주석이 있다).

## 판정

premise 의 **출처 파일 경로**로 나눈다.
  · stdlib   경로에 coq/theories · stdlib · Coq/... 가 있는 것
  · 프로젝트  그 외

사용: python3 scripts/stdlib_share.py [n] [train|test|val]
"""
import collections
import copy
import os
import re
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("AUGMENT_V2", "1")
os.environ.setdefault("RERANK_PREMISES", "1")
os.environ.setdefault("HARD_SEQ_LEN", "2048")
os.environ.setdefault("FUNC_DEFS_PATH", "data/func_defs_v3.json")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from data_management.dataset_file import DatasetFile  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402
from premise_selection.premise_filter import PremiseFilter, PremiseFilterConf  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402
from tactic_gen.tier_rank import declname  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 800
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "train").upper()

_STD = re.compile(r"(coq/theories|/stdlib/|coq-8|/Coq/|theories/(Init|Lists|Arith|ZArith|"
                  r"NArith|Bool|Logic|Reals|QArith|Sets|Relations|Classes|Numbers|"
                  r"Strings|Sorting|Structures|Program|Wellfounded|FSets|MSets|Vectors)/)",
                  re.I)
# 이름 접두사로도 판정 (경로가 없을 때)
_STD_PREFIX = re.compile(r"^(Nat|N|Z|Q|R|Pos|List|Bool|Ascii|String|Vector|Fin|"
                         r"Ensembles|Rel|Morphisms|Setoid|CRelation|PeanoNat|BinInt|"
                         r"BinNat|BinPos|ZArith|NArith)\.")

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
conf = TacticDataConf.from_yaml(copy.deepcopy(cc["tactic_data"]))
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), 10 ** 9)
sdb = SentenceDB.load(conf.sentence_db_loc)
pf = PremiseFilterConf.from_yaml(
    copy.deepcopy(cc["tactic_data"])["formatter_conf"]["premise"]["premise_filter"])
pfilter = PremiseFilter(pf.coq_excludes, pf.non_coq_excludes, pf.general_excludes)


def is_std(path: str, name: str) -> bool:
    if path and _STD.search(path):
        return True
    return bool(name and _STD_PREFIX.match(name))


c = collections.Counter()
gold_std_ex = []
n = 0
for i in range(N * 4):
    if n >= N:
        break
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    prem = list(getattr(e, "premises", None) or [])
    if not prem:
        continue
    sid = ds.shuffled_idx.get_idx(ds.split, i)
    try:
        dp = DatasetFile.load(conf.data_loc / "data_points" / sid.file, sdb)
        proof = dp.proofs[sid.proof_idx]
    except Exception:
        continue
    pool = [p for p in dp.get_premises_before(proof) if pfilter.filter_premise(p)]
    if not pool:
        continue
    n += 1
    for p in pool:
        nm = declname(getattr(p, "text", "") or "")
        if not nm:
            continue
        c["풀 premise"] += 1
        c["풀 stdlib" if is_std(getattr(p, "file_path", "") or "", nm) else "풀 프로젝트"] += 1
    st = getattr(e, "proof_state", "") or ""
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    golds = gold_lemmas(tac, local_names(st))
    if not golds:
        continue
    for p in pool:
        nm = declname(getattr(p, "text", "") or "")
        if nm and nm in golds:
            c["gold"] += 1
            s_ = is_std(getattr(p, "file_path", "") or "", nm)
            c["gold stdlib" if s_ else "gold 프로젝트"] += 1
            if s_ and len(gold_std_ex) < 8:
                gold_std_ex.append((nm, (getattr(p, "file_path", "") or "")[-52:]))

print(f"\n■ {SPLIT} — stdlib 비중 ({n:,}건)")
tp = max(c["풀 premise"], 1)
tg = max(c["gold"], 1)
print(f"\n   후보 풀 premise   {c['풀 premise']:8,}")
print(f"     stdlib          {c['풀 stdlib']:8,}  ({c['풀 stdlib']/tp*100:5.1f}%)")
print(f"     프로젝트         {c['풀 프로젝트']:8,}  ({c['풀 프로젝트']/tp*100:5.1f}%)")
print(f"\n   ★ gold lemma      {c['gold']:8,}")
print(f"     stdlib          {c['gold stdlib']:8,}  ({c['gold stdlib']/tg*100:5.1f}%)"
      f"   ← 익명화에서 빼면 이만큼이 '진짜 지식'으로 남는다")
print(f"     프로젝트         {c['gold 프로젝트']:8,}  ({c['gold 프로젝트']/tg*100:5.1f}%)")
if gold_std_ex:
    print(f"\n   stdlib gold 표본:")
    for nm, path in gold_std_ex:
        print(f"     {nm:28s} {path}")
