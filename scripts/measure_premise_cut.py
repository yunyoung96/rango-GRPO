#!/usr/bin/env python3
"""★ premise 가 토큰 예산에 얼마나 잘리는지, 그래서 gold 를 잃는지 잰다.

## 배경

검색이 gold 를 상위에 올려도 **프롬프트에 못 들어가면 소용없다.** `premise_tokens=896`
예산 안에 들어가는 것만 들어간다(`whole_number_allocate` 가 앞에서부터 채운다).

## 재는 것

  ① 검색이 넘긴 premise 수  vs  프롬프트에 실제로 들어간 수
  ② ★ gold 가 목록에는 있는데 **잘려 나가는** 비율 (= 검색 성공인데 프롬프트엔 없음)
  ③ 잘린 premise 가 **정규화 매핑에는 남는** 비율
     (매핑은 `example.premises` 전부를 대상으로 한다 → 프롬프트에 없는 `L92` 가 생긴다)
  ④ 예산을 늘리면 얼마나 개선되나

사용: python3 scripts/measure_premise_cut.py [n]
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
from transformers import AutoTokenizer  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    whole_number_allocate, rerank_premises)
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402
from tactic_gen.tier_rank import declname  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
BUDGETS = (896, 1200, 1600, 2400)

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
conf = TacticDataConf.from_yaml(copy.deepcopy(cc["tactic_data"]))
ds = LmDataset.from_conf(conf, Split.TRAIN, 10 ** 9)
tok = AutoTokenizer.from_pretrained(cc["model_name"])
BASE = conf.collator_conf.premise_tokens

st = collections.Counter()
n_in, n_fit = [], []
keep_at = {b: 0 for b in BUDGETS}
gold_at = {b: 0 for b in BUDGETS}
n = ngold = 0

for i in range(N * 5):
    if n >= N:
        break
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    prem = list(getattr(e, "premises", None) or [])
    if not prem:
        continue
    n += 1
    if os.environ.get("RERANK_PREMISES", "0") == "1":
        try:
            prem = rerank_premises(e)
        except Exception:
            pass
    n_in.append(len(prem))
    for b in BUDGETS:
        fit = whole_number_allocate(tok, prem, b)
        keep_at[b] += len(fit)
        if b == BASE:
            n_fit.append(len(fit))

    # ② gold 가 목록엔 있는데 잘리는가
    state = getattr(e, "proof_state", "") or ""
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    golds = gold_lemmas(tac, local_names(state))
    if not golds:
        continue
    names = [declname(p if isinstance(p, str) else getattr(p, "text", "")) for p in prem]
    if not any(nm and nm in golds for nm in names):
        continue                      # 목록에 아예 없음 → 잘림 문제가 아니다
    ngold += 1
    for b in BUDGETS:
        fit = whole_number_allocate(tok, prem, b)
        fnames = {declname(x) for x in fit}
        if all(g in fnames for g in golds):
            gold_at[b] += 1

n_in.sort()
n_fit.sort()
print(f"\n■ premise 토큰 예산에 의한 잘림 (TRAIN {n}건 · 현재 예산 {BASE} 토큰)")
print(f"\n① 개수")
print(f"   검색이 넘긴 premise   중앙 {n_in[len(n_in)//2]}개 · 평균 {sum(n_in)/len(n_in):.0f}개"
      f" · 최대 {n_in[-1]}개")
print(f"   프롬프트에 들어간 것   중앙 {n_fit[len(n_fit)//2]}개 · 평균 {sum(n_fit)/len(n_fit):.0f}개")
cut = sum(n_in) - sum(n_fit)
print(f"   ★ 잘려나간 비율        {cut/max(sum(n_in),1)*100:.1f}%  "
      f"({cut:,} / {sum(n_in):,})")

print(f"\n② gold 가 **목록엔 있는데 잘리는가** (해당 {ngold}건)")
print(f"   {'예산':>8s} {'평균 유지 premise':>18s} {'gold 전부 살아남음':>20s}")
for b in BUDGETS:
    mark = " ← 현재" if b == BASE else ""
    print(f"   {b:8d} {keep_at[b]/max(n,1):18.1f} "
          f"{gold_at[b]/max(ngold,1)*100:19.1f}%{mark}")

lost = 100 - gold_at[BASE] / max(ngold, 1) * 100
print(f"\n   ★ 현재 예산에서 gold 를 잃는 비율: {lost:.1f}%")
print(f"      (검색은 성공했는데 프롬프트에 못 들어간 것 — 검색 개선으로는 못 고친다)")
print(f"\n③ 잘린 premise 도 **정규화 매핑에는 들어간다** → 프롬프트에 없는 `L92` 가 생긴다.")
print(f"   `build_mapping` 이 example.premises 전부를 대상으로 하기 때문. 근본 수정은")
print(f"   **프롬프트에 살아남은 premise 만 매핑**하는 것이다.")
