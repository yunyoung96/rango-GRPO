#!/usr/bin/env python3
"""★ 풀에 넣은 premise 가 **몇 위**에 오는가 — 풀 확대의 값어치를 가르는 유일한 질문.

`PREMISE_ADMIT_USED=1` 은 제외 종류(Definition·Inductive·Record·Fixpoint·축약 Notation)
중 **실제로 tactic 인자로 쓰인 것**을 풀에 되살린다. 풀은 +15.9% 커진다.

그런데 **풀에 있는 것과 프롬프트에 실리는 것은 다르다** — 검색 100개 중 896토큰
예산에 들어가는 상위 ~22개 안에 들어야 한다. 그래서 재는 것:

    결손 이름이 검색 결과 100개 안에 **들어왔는가**, 들어왔다면 **몇 위인가**

들어오지도 않으면 풀 확대는 무의미하고, 80위면 예산을 늘려도 못 싣는다.
상위 20위 안이면 값어치가 있다.

사용: PYTHONPATH=src PREMISE_ADMIT_USED=1 python3 scripts/probe_admit_rank.py [표본]
"""
import collections
import copy
import json
import logging
import os
import random
import re
import sys

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
logging.disable(logging.CRITICAL)
from _env_from_v9 import apply_v9_env  # noqa: E402
apply_v9_env(verbose=False)
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer,
                                    _strip_coq_comments)
from tactic_gen.normalize_names import introduced_names  # noqa: E402
from _coq_vocab import is_core  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1500
try:
    STDLIB = set(json.load(open("data/stdlib_names.json")))
except Exception:
    STDLIB = set()

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", "/tmp/admitrank-cache")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
HARD = int(os.environ.get("HARD_SEQ_LEN", "2048"))
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)

st = collections.Counter()
ranks = []
kinds = collections.Counter()
random.seed(4)
tried = 0
import time  # noqa: E402
t0 = time.time()
while st["예제"] < N and tried < N * 40:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        ex = ds.resolved_example(i)
        full = coll.collate(tok, ex)
    except Exception:
        continue
    if "[TACTIC]" not in full:
        continue
    st["예제"] += 1
    prompt, target = full.rsplit("[TACTIC]", 1)
    ids = tok(full, add_special_tokens=False)["input_ids"]
    vis = tok.decode(ids[max(0, len(ids) - HARD):], skip_special_tokens=True)
    vp = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis
    tgt = re.sub(r'"[^"]*"', " ", _strip_coq_comments(target))
    local = set()
    m = re.search(r"\[STATE\]\n(.*?)(?=\n\[[A-Z]+\]|\Z)", prompt, re.S)
    if m:
        for ln in m.group(1).split("\n"):
            mm = re.match(r"^([A-Za-z_][\w', ]*?)\s*:", ln)
            if mm:
                local |= {x.strip() for x in mm.group(1).split(",") if x.strip()}
    try:
        intro = introduced_names(tgt)
    except Exception:
        intro = set()
    tacn = set()
    for seg in re.split(r";|\bby\b", tgt):
        seg = seg.strip().lstrip("[](){}| \t")
        for _ in range(3):
            seg = re.sub(r"^(?:now|try|repeat|by|first|solve|progress|do\s+\d+|"
                         r"abstract|once|time)\b\s*\[?\s*", "", seg)
        mm = re.match(r"([A-Za-z_][\w']*)", seg)
        if mm:
            tacn.add(mm.group(1))
    prem = [(p if isinstance(p, str) else str(p)) for p in (getattr(ex, "premises", None) or [])]
    for w in dict.fromkeys(re.findall(r"(?<![\w'.])([A-Za-z_][\w']*)", tgt)):
        if is_core(w) or w in local or w in intro or w in tacn:
            continue
        if w in STDLIB:
            continue
        if re.search(r"(?<![\w'])" + re.escape(w) + r"(?![\w'])", vp):
            continue                      # 이미 보임 — 환각 아님
        st["★ 결손 이름"] += 1
        # 검색 결과 100개 안에 있나 · 몇 위인가
        r = None
        for k, p in enumerate(prem):
            if re.search(r"(?:Lemma|Theorem|Definition|Fixpoint|Inductive|Record|"
                         r"Instance|Notation|Axiom|Corollary|Fact)\s+" + re.escape(w)
                         + r"(?![\w'])", p):
                r = k + 1
                break
        if r is None:
            # ★ 정규식(선언 키워드 + 이름)이 놓쳤을 가능성을 배제한다 —
            #   **문자열로라도** 100개 안에 나오는지 느슨하게 다시 본다.
            loose = None
            for k, p_ in enumerate(prem):
                if re.search(r"(?<![\w'])" + re.escape(w) + r"(?![\w'])", p_):
                    loose = k + 1
                    break
            if loose is None:
                st["  검색 100개 안에도 없음(느슨해도)"] += 1
            else:
                st["  선언은 못 찾았지만 문자열로는 있음"] += 1
                if st["샘플"] < 5:
                    st["샘플"] += 1
                    print(f"     [느슨히트] {w} @{loose}: {prem[loose-1][:90]}", flush=True)
        else:
            ranks.append(r)
            st["  검색에는 있음"] += 1
            if r <= 22:
                st["    ├ 상위 22위 안 (예산에 들어갈 자리)"] += 1
            elif r <= 50:
                st["    ├ 23~50위"] += 1
            else:
                st["    └ 51위 밖"] += 1
    if st["예제"] % 200 == 0:
        print(f"   … {st['예제']}/{N} ({time.time()-t0:.0f}s)", flush=True)

print(f"\n■ 결과 (예제 {st['예제']}) · PREMISE_ADMIT_USED="
      f"{os.environ.get('PREMISE_ADMIT_USED','0')}\n")
for k in sorted(st):
    print(f"   {k:40s} {st[k]:6d}")
if ranks:
    ranks.sort()
    q = lambda p: ranks[min(len(ranks) - 1, int(len(ranks) * p))]
    print(f"\n   순위 분포  중앙 {q(.5)} · p25 {q(.25)} · p75 {q(.75)} · 최대 {ranks[-1]}")
