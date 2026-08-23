#!/usr/bin/env python3
"""★ 검색이 넘긴 premise 중 **몇 개가 프롬프트에 살아남는가** — 대규모 통계.

## 배경

`num_premises: 100` 으로 검색이 최대 100개를 넘기지만, 프롬프트에는 `premise_tokens: 896`
토큰 예산 안에 들어가는 것만 실린다(`whole_number_allocate` 가 앞에서부터 채운다).
**검색 순위(R@k)가 좋아도 프롬프트에 못 들어가면 소용이 없다.**

## 재는 것

  ① 살아남는 개수 분포 (백분위)
  ② ★ **순위별 생존율** — 검색 k 위 premise 가 프롬프트에 들어갈 확률
  ③ 예산을 바꾸면 어떻게 변하나
  ④ premise 길이 분포 (길이가 길면 몇 개 못 넣는다)

사용: python3 scripts/premise_survival.py [n] [train|val|test]
"""
import collections
import copy
import os
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("AUGMENT_V2", "1")
os.environ.setdefault("RERANK_PREMISES", "1")
# ★ HARD_SEQ_LEN 은 rango_defaults 기본값을 따른다 — 여기서 2048 로 못 박지 않는다
os.environ.setdefault("FUNC_DEFS_PATH", "data/func_defs_v3.json")
sys.path.insert(0, "src")
import rango_defaults as _D
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    whole_number_allocate, rerank_premises)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "train").upper()
BUDGETS = (896, 1400, 2000, 3000)

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
conf = TacticDataConf.from_yaml(copy.deepcopy(cc["tactic_data"]))
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), 10 ** 9)
tok = AutoTokenizer.from_pretrained(cc["model_name"])
BASE = conf.collator_conf.premise_tokens

n_in, n_fit = [], []
plens = []
surv = {b: collections.Counter() for b in BUDGETS}   # 순위 → 살아남은 횟수
seen_rank = collections.Counter()                     # 순위 → 등장 횟수
keep = {b: [] for b in BUDGETS}
n = 0
t0 = time.time()

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
    try:
        prem = rerank_premises(e)
    except Exception:
        pass
    n += 1
    n_in.append(len(prem))
    for k in range(len(prem)):
        seen_rank[k] += 1
    # 길이(토큰) 표본
    if n <= 300:
        for p in prem[:20]:
            plens.append(len(tok(p if isinstance(p, str) else str(p),
                                 add_special_tokens=False)["input_ids"]))
    for b in BUDGETS:
        fit = whole_number_allocate(tok, prem, b)
        keep[b].append(len(fit))
        fset = set(id(x) for x in fit)
        for k, p in enumerate(prem):
            if id(p) in fset:
                surv[b][k] += 1
        if b == BASE:
            n_fit.append(len(fit))
    if n % 250 == 0:
        print(f"   … {n}/{N} ({time.time()-t0:.0f}s)", flush=True)


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, int(len(v) * q))]


print(f"\n■ {SPLIT} — premise 생존 통계 ({n:,}건 · num_premises=100 · 예산 {BASE}토큰)")
print(f"\n① 개수")
print(f"   {'':14s} {'p10':>6s} {'p25':>6s} {'중앙':>6s} {'p75':>6s} {'p90':>6s} {'평균':>7s}")
print(f"   {'검색이 넘김':14s} " + " ".join(f"{pct(n_in,q):6d}" for q in (.1,.25,.5,.75,.9))
      + f" {sum(n_in)/len(n_in):7.1f}")
print(f"   {'프롬프트 포함':14s} " + " ".join(f"{pct(n_fit,q):6d}" for q in (.1,.25,.5,.75,.9))
      + f" {sum(n_fit)/len(n_fit):7.1f}")
print(f"\n   ★ 생존율(개수 기준)  {sum(n_fit)/max(sum(n_in),1)*100:.1f}%")

print(f"\n② ★ 순위별 생존율 — 검색 k 위가 프롬프트에 들어갈 확률")
print(f"   {'순위':>6s} " + " ".join(f"{('예산'+str(b)):>9s}" for b in BUDGETS))
for k in (0, 4, 9, 14, 19, 29, 39, 49, 69, 99):
    if seen_rank[k] == 0:
        continue
    row = f"   {k+1:5d}위 "
    for b in BUDGETS:
        row += f"{surv[b][k]/seen_rank[k]*100:8.1f}%"
    print(row)

print(f"\n③ 예산별 평균 포함 개수")
for b in BUDGETS:
    mark = "  ← 현재" if b == BASE else ""
    print(f"   {b:5d} 토큰 → 평균 {sum(keep[b])/max(len(keep[b]),1):5.1f}개"
          f"  (생존율 {sum(keep[b])/max(sum(n_in),1)*100:5.1f}%){mark}")

if plens:
    plens.sort()
    print(f"\n④ premise 길이(토큰)  p25 {pct(plens,.25)} · 중앙 {pct(plens,.5)} "
          f"· p75 {pct(plens,.75)} · p90 {pct(plens,.9)} · 최대 {plens[-1]}")
    print(f"   → 예산 {BASE} 토큰 ÷ 중앙 {pct(plens,.5)} 토큰 ≈ {BASE//max(pct(plens,.5),1)}개")
