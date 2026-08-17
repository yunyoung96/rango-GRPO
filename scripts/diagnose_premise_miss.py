#!/usr/bin/env python3
"""gold lemma 를 **왜** 못 가져오는지 원인별로 나눈다.

앞선 측정: 후보를 1000개로 늘려도 TRAIN 의 58.8% 에서 gold 가 없다. 원인이 섞여 있으면
대책이 안 나오므로 갈라 본다.

  A  풀에 있고 검색 상위에 옴            → 문제 없음
  B  풀에 있는데 순위가 밀려 못 옴        → **검색 품질** 문제 (재랭킹·검색기 교체로 해결 가능)
  C1 풀에 있지만 proj-thm 필터가 배제     → **필터** 문제 (설정으로 해결 가능)
  C2 풀에 아예 없음                       → **데이터** 문제 (Coq Search 같은 다른 수단 필요)

C2 는 다시 출처로 나눈다: Coq 표준 라이브러리 / 같은 프로젝트 / 외부 라이브러리.
특히 **같은 프로젝트의 lemma 인데도 못 가져오는 경우**가 있는지가 관건이다 — 있다면
데이터 생성 자체(가용 premise 수집)에 구멍이 있다는 뜻이다.
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
from data_management.dataset_file import DatasetFile  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 600
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "train").upper()
CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")
cc = yaml.safe_load(open(CONF))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"]["num_premises"] = 1000
tdc["formatter_conf"].pop("proof_ret", None)          # BM25 는 이 측정에 불필요(예제당 수십 초)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), N)
sdb = SentenceDB.load(conf.sentence_db_loc)

from tactic_gen.gold_lemma import gold_lemma  # noqa: E402
_NAME = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                   r"Instance|Axiom|Proposition|Example|Let|Program\s+\w+)\s+"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")

from premise_selection.premise_filter import PremiseFilter, PremiseFilterConf  # noqa: E402
pf_conf = PremiseFilterConf.from_yaml(
    tdc["formatter_conf"]["premise"]["premise_filter"])
pfilter = PremiseFilter(pf_conf.coq_excludes, pf_conf.non_coq_excludes,
                        pf_conf.general_excludes)


def sname(s):
    t = getattr(s, "text", "") or ""
    m = _NAME.match(t)
    return m.group(1).split(".")[-1] if m else None


def origin(path: str, proj: str) -> str:
    p = path or ""
    if os.path.join("lib", "coq", "theories") in p:
        return "Coq 표준"
    if proj and proj in p:
        return "같은 프로젝트"
    return "외부 라이브러리"


cnt = collections.Counter()
c2_by_origin = collections.Counter()
c1_ex, c2_proj_ex = [], []
n_gold = 0

for i in range(N):
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    base = gold_lemma(tac)
    if base is None:
        continue
    n_gold += 1

    prems = [p if isinstance(p, str) else getattr(p, "text", str(p))
             for p in (getattr(e, "premises", None) or [])]
    rank = -1
    for j, t in enumerate(prems):
        m = _NAME.match(t)
        if m and m.group(1).split(".")[-1] == base:
            rank = j
            break
    if 0 <= rank < 100:
        cnt["A 상위100 안에 있음"] += 1
        continue
    if rank >= 100:
        cnt["B 풀에 있지만 순위 밀림(100위 밖)"] += 1
        continue

    # 검색 결과에 없다 → 풀(필터 전) 전체를 뒤진다
    sid = ds.shuffled_idx.get_idx(ds.split, i)
    try:
        dp = DatasetFile.load(conf.data_loc / "data_points" / sid.file, sdb)
    except Exception:
        cnt["? 파일 로드 실패"] += 1
        continue
    proj = sid.file.split("-")[0] if "-" in sid.file else ""
    pool = list(getattr(dp, "out_of_file_avail_premises", []) or [])
    try:
        pool += list(dp.get_in_file_premises_before(dp.proofs[sid.proof_idx]))
    except Exception:
        pass
    found = None
    for s in pool:
        if sname(s) == base:
            found = s
            break
    if found is None:
        cnt["C2 풀에 아예 없음"] += 1
        o = "?"
        c2_by_origin[o] += 1
        if len(c2_proj_ex) < 8:
            c2_proj_ex.append((base, tac[:44]))
        continue
    if not pfilter.filter_premise(found):
        cnt["C1 풀엔 있지만 필터가 배제"] += 1
        if len(c1_ex) < 6:
            c1_ex.append((base, origin(getattr(found, "file_path", ""), proj),
                          str(getattr(found, "sentence_type", "?"))))
    else:
        cnt["B2 필터 통과했는데 검색이 못 뽑음"] += 1


print(f"\n■ {SPLIT} — gold 가 lemma 를 쓰는 {n_gold}건의 원인 분해\n")
for k in sorted(cnt, key=lambda x: -cnt[x]):
    print(f"   {k:36s} {cnt[k]:4d} = {cnt[k]/max(n_gold,1)*100:5.1f}%")
if c1_ex:
    print("\n   C1 예 (필터가 배제한 것):")
    for b, o, t in c1_ex:
        print(f"     · {b:26s} 출처={o:12s} 종류={t}")
if c2_proj_ex:
    print("\n   C2 예 (풀에 아예 없는 것):")
    for b, t in c2_proj_ex:
        print(f"     · {b:26s} ({t}…)")
