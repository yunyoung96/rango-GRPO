#!/usr/bin/env python3
"""★ knapsack 이 TRAIN 에서만 gold 를 잃는 이유를 밝힌다.

실측: gold 포함률 변화 (greedy 대비)
    TRAIN -5.6p · TEST +7.7p · VAL +15.1p

가설: knapsack 은 **가치/무게** 비로 담으므로 **길고 순위 낮은 gold** 를 버린다.
      TRAIN 의 gold 가 유독 길거나, greedy 로도 이미 잘 담기고 있어(baseline 84.4%)
      개선 여지가 없고 손해만 본다.

## 재는 것

  · greedy 는 담았는데 knapsack 이 버린 gold — 그 gold 의 **순위와 토큰 길이**
  · 반대 경우(knapsack 만 담음)도 같이
  · 스플릿별 gold 길이 분포 비교

사용: python3 scripts/knapsack_diag.py [n] [train|test|val]
"""
import collections
import copy
import os
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
                                    rerank_premises)
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402
from tactic_gen.tier_rank import declname  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 800
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "train").upper()
BUDGET = 896

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
conf = TacticDataConf.from_yaml(copy.deepcopy(cc["tactic_data"]))
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), 10 ** 9)
tok = AutoTokenizer.from_pretrained(cc["model_name"])
_L = {}


def tl(t):
    v = _L.get(t)
    if v is None:
        v = len(tok.tokenize(t))
        _L[t] = v
    return v


def pack_greedy(texts, skip=True):
    left, out = BUDGET, []
    for i, t in enumerate(texts):
        n = tl(t)
        if n > left:
            if skip:
                continue
            break
        left -= n
        out.append(i)
    return out


def pack_knap(texts):
    n = len(texts)
    order = sorted(range(n), key=lambda i: -((n - i) / max(tl(texts[i]), 1)))
    left, out = BUDGET, []
    for i in order:
        w = tl(texts[i])
        if w <= left:
            left -= w
            out.append(i)
    return out


g_only, k_only, both = [], [], []
gold_len, gold_rank = [], []
n = 0
for i in range(N * 4):
    if n >= N:
        break
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    prem = list(getattr(e, "premises", None) or [])
    if len(prem) < 5:
        continue
    try:
        prem = rerank_premises(e)
    except Exception:
        pass
    texts = [p if isinstance(p, str) else str(p) for p in prem]
    st = getattr(e, "proof_state", "") or ""
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    golds = gold_lemmas(tac, local_names(st))
    if not golds:
        continue
    names = [declname(t) for t in texts]
    gidx = [j for j, nm in enumerate(names) if nm and nm in golds]
    if not gidx:
        continue
    n += 1
    G = set(pack_greedy(texts))
    K = set(pack_knap(texts))
    for j in gidx:
        gold_len.append(tl(texts[j]))
        gold_rank.append(j)
        ing, ink = j in G, j in K
        if ing and not ink:
            g_only.append((j, tl(texts[j])))
        elif ink and not ing:
            k_only.append((j, tl(texts[j])))
        elif ing and ink:
            both.append((j, tl(texts[j])))


def stat(v, key):
    if not v:
        return "없음"
    xs = sorted(x[key] for x in v)
    return f"중앙 {xs[len(xs)//2]} · 평균 {sum(xs)/len(xs):.0f}"


print(f"\n■ {SPLIT} — knapsack vs greedy(skip) 의 gold 처리 ({n}건)")
print(f"\n   gold 전체:  순위 {stat([(r,l) for r,l in zip(gold_rank,gold_len)],0)}"
      f" · 길이 {stat([(r,l) for r,l in zip(gold_rank,gold_len)],1)} 토큰")
print(f"\n   {'경우':28s} {'건수':>6s} {'gold 순위':>18s} {'gold 길이(토큰)':>20s}")
print(f"   {'둘 다 담음':28s} {len(both):6d} {stat(both,0):>18s} {stat(both,1):>20s}")
print(f"   {'★ greedy만 담음(knap 손해)':28s} {len(g_only):6d} {stat(g_only,0):>18s} "
      f"{stat(g_only,1):>20s}")
print(f"   {'knapsack만 담음(knap 이득)':28s} {len(k_only):6d} {stat(k_only,0):>18s} "
      f"{stat(k_only,1):>20s}")
net = len(k_only) - len(g_only)
print(f"\n   순이득 {net:+d}건  ({'knapsack 우세' if net > 0 else 'greedy 우세'})")
