#!/usr/bin/env python3
"""★ premise 를 프롬프트에 **더 많이 담는 방법**들을 비교한다.

## 지금 방식의 문제

`whole_number_allocate` 는 순위대로 담다가 예산이 넘으면 **break** 한다.
실측: 100개 중 17개. 긴 premise 하나(175토큰)가 짧은 것(20토큰) 여러 개를 밀어낸다.
길이 편차가 극심하다 — 최소 16 · 중앙 147 · 최대 928 토큰.

## 비교하는 방식

  ① greedy(현재)   순위대로 담다가 넘치면 **중단**
  ② skip           넘치는 것은 **건너뛰고** 다음 것을 시도 (한 줄 수정)
  ③ knapsack       가치(=순위 점수) / 길이 비로 담는다 (배낭 근사)
  ④ ★ 정규화 후    **먼저 이름을 정규화하고** 나서 담는다
                   (지금은 자른 뒤에 정규화한다 — 순서가 거꾸로다)
  ⑤ 정규화+skip    ④+②

## 지표

  · 담긴 개수
  · **gold 생존율** — 개수가 늘어도 gold 를 놓치면 소용없다

사용: python3 scripts/premise_packing.py [n] [train|val|test]
"""
import collections
import copy
import os
import re
import sys
import time

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
from tactic_gen.name_alloc import NameAllocator  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 500
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


def normalize_premises(texts):
    """★ premise **이름만** L0,L1,… 로 바꾼다 (자르기 전에 하면 더 많이 들어간다).

    지금 파이프라인은 자른 **뒤에** 정규화하므로 이 이득을 못 본다.
    """
    alloc = NameAllocator(set())
    m = {}
    for t in texts:
        nm = declname(t)
        if nm and nm not in m:
            m[nm] = alloc.alloc("L")
    if not m:
        return texts, m
    pat = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(m, key=len, reverse=True)) + r")\b")
    return [pat.sub(lambda x: m[x.group(1)], t) for t in texts], m


def pack_greedy(texts, budget, skip=False):
    left, out = budget, []
    for i, t in enumerate(texts):
        n = tl(t)
        if n > left:
            if skip:
                continue
            break
        left -= n
        out.append(i)
    return out


def pack_knapsack(texts, budget):
    """가치/무게 비로 담는 근사. 가치는 순위(앞일수록 높다)."""
    n = len(texts)
    items = sorted(range(n), key=lambda i: -((n - i) / max(tl(texts[i]), 1)))
    left, out = budget, []
    for i in items:
        w = tl(texts[i])
        if w <= left:
            left -= w
            out.append(i)
    return sorted(out)


def pack_hybrid(texts, budget, topk=8):
    """★ 상위 topk 는 **순위대로** 담고(긴 gold 를 지킨다), 남은 예산을 knapsack 으로.

    근거(TRAIN gold 261건 진단):
      · knapsack 이 버리는 gold = 순위 중앙 3위 · 길이 중앙 64토큰 (36건 손해)
      · knapsack 이 건지는 gold = 순위 중앙 34위 · 길이 중앙 22토큰 (21건 이득)
    상위 K 를 지키면 손해를 막고 이득은 남는다.
    """
    left, out = budget, []
    for i in range(min(topk, len(texts))):
        n = tl(texts[i])
        if n > left:
            continue
        left -= n
        out.append(i)
    rest = list(range(min(topk, len(texts)), len(texts)))
    N = len(texts)
    for i in sorted(rest, key=lambda j: -((N - j) / max(tl(texts[j]), 1))):
        w = tl(texts[i])
        if w <= left:
            left -= w
            out.append(i)
    return sorted(out)


METH = ["① greedy(현재)", "② skip", "③ knapsack", "④ 정규화+greedy",
        "⑤ 정규화+skip", "⑥ 정규화+knapsack",
        "⑦ ★hybrid(K=4)", "⑧ ★hybrid(K=8)", "⑨ ★hybrid(K=16)",
        "⑩ 정규화+hybrid(K=8)"]
cnt = {m: [] for m in METH}
gold_ok = {m: 0 for m in METH}
ngold = 0
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
    if len(prem) < 5:
        continue
    try:
        prem = rerank_premises(e)
    except Exception:
        pass
    texts = [p if isinstance(p, str) else str(p) for p in prem]
    n += 1
    ntexts, _ = normalize_premises(texts)

    sel = {
        "① greedy(현재)": pack_greedy(texts, BUDGET),
        "② skip": pack_greedy(texts, BUDGET, skip=True),
        "③ knapsack": pack_knapsack(texts, BUDGET),
        "④ 정규화+greedy": pack_greedy(ntexts, BUDGET),
        "⑤ 정규화+skip": pack_greedy(ntexts, BUDGET, skip=True),
        "⑥ 정규화+knapsack": pack_knapsack(ntexts, BUDGET),
        "⑦ ★hybrid(K=4)": pack_hybrid(texts, BUDGET, 4),
        "⑧ ★hybrid(K=8)": pack_hybrid(texts, BUDGET, 8),
        "⑨ ★hybrid(K=16)": pack_hybrid(texts, BUDGET, 16),
        "⑩ 정규화+hybrid(K=8)": pack_hybrid(ntexts, BUDGET, 8),
    }
    for m in METH:
        cnt[m].append(len(sel[m]))

    st = getattr(e, "proof_state", "") or ""
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    golds = gold_lemmas(tac, local_names(st))
    if not golds:
        continue
    names = [declname(t) for t in texts]
    gidx = {j for j, nm in enumerate(names) if nm and nm in golds}
    if not gidx:
        continue
    ngold += 1
    for m in METH:
        s_ = set(sel[m])
        gn = {names[j] for j in gidx}
        got = {names[j] for j in gidx if j in s_}
        if gn <= got:
            gold_ok[m] += 1
    if n % 200 == 0:
        print(f"   … {n}/{N} ({time.time()-t0:.0f}s)", flush=True)


def med(v):
    v = sorted(v)
    return v[len(v) // 2]


print(f"\n■ {SPLIT} — premise 담기 방식 비교 ({n:,}건 · 예산 {BUDGET}토큰)")
print(f"\n   {'방식':20s} {'중앙 개수':>9s} {'평균':>7s} {'gold 전부 포함':>14s}")
base = None
for m in METH:
    g = gold_ok[m] / max(ngold, 1) * 100
    if base is None:
        base = g
    print(f"   {m:20s} {med(cnt[m]):9d} {sum(cnt[m])/len(cnt[m]):7.1f} "
          f"{g:13.1f}%{'' if m == METH[0] else f'  ({g-base:+.1f}p)'}")
print(f"\n   gold 판정 대상 {ngold:,}건")
