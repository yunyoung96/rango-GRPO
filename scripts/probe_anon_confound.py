#!/usr/bin/env python3
"""★ **익명화 때문에 "못 찾았다" 고 잘못 신고한 것이 있나** — 측정 버그 점검.

의심: `[DEFINITIONS]`·`[TYPES]`·`[PREMISES]` 의 이름은 v8 정규화로 `T0`·`f5`·`L9` 가 된다.
      프롬프트는 `f5` 인데 정답은 `foo` 로 남아 있으면, 검사기는 `foo` 를 찾다 못 찾고
      **환각으로 오신고**한다. 그건 환각이 아니라 버그다.

이론상으로는 `collate` 가 프롬프트와 정답에 **같은 매핑**을 적용하므로 생길 수 없다.
그러나 이론이 아니라 실측으로 확인한다. `last_train_mapping()` 으로 그 매핑을 꺼내
결손 이름마다 네 가지를 본다.

    ① 결손 이름이 **익명 토큰**인가 (`T0`/`f5`/`L9`/`C2`/`K1`/`G0`)
    ② 결손 이름이 **매핑의 키**인가 → 정답에 실명이 남았다는 뜻 = **버그**
    ③ 그 이름의 **익명형**이 프롬프트에 있나 → 익명화 탓 오탐 = **버그**
    ④ 그 익명 토큰의 **원래 이름**이 프롬프트에 있나 (반대 방향)

사용: PYTHONPATH=src python3 scripts/probe_anon_confound.py [표본]
"""
import collections
import copy
import json
import logging
import os
import random
import re
import sys
import time

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
                                    _strip_coq_comments, last_train_mapping)
from tactic_gen.normalize_names import introduced_names  # noqa: E402
from _coq_vocab import is_core  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
STDLIB = set(json.load(open("data/stdlib_names.json")))
_ANON = re.compile(r"^[TfCLGK]\d+$")

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", "/tmp/hsource-cache")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
HARD = int(os.environ.get("HARD_SEQ_LEN", "2048"))
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)

st = collections.Counter()
bugs = []
random.seed(4)
tried = 0
t0 = time.time()
while st["예제"] < N and tried < N * 40:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        ex = ds.resolved_example(i)
        full = coll.collate(tok, ex)
        m = last_train_mapping()
    except Exception:
        continue
    if "[TACTIC]" not in full:
        continue
    st["예제"] += 1
    if m:
        st["  정규화가 적용된 예제"] += 1
        st["  매핑 항목 수"] += len(m)
    inv = {v: k for k, v in m.items()}
    prompt, target = full.rsplit("[TACTIC]", 1)
    ids = tok(full, add_special_tokens=False)["input_ids"]
    vis = tok.decode(ids[max(0, len(ids) - HARD):], skip_special_tokens=True)
    vp = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis
    tgt = re.sub(r'"[^"]*"', " ", _strip_coq_comments(target))
    local = set()
    mm_ = re.search(r"\[STATE\]\n(.*?)(?=\n\[[A-Z]+\]|\Z)", prompt, re.S)
    if mm_:
        for ln in mm_.group(1).split("\n"):
            g = re.match(r"^([A-Za-z_][\w', ]*?)\s*:", ln)
            if g:
                local |= {x.strip() for x in g.group(1).split(",") if x.strip()}
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
        g = re.match(r"([A-Za-z_][\w']*)", seg)
        if g:
            tacn.add(g.group(1))
    for w in dict.fromkeys(re.findall(
            r"(?<![\w'.])([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)", tgt)):
        b = w.split(".")[-1]
        if (is_core(w) or b in local or w in local or b in intro or w in intro
                or w in tacn or b in tacn or b in STDLIB or w in STDLIB):
            continue
        if re.search(r"(?<![\w'])" + re.escape(b) + r"(?![\w'])", vp):
            continue
        st["★ 결손 이름"] += 1
        if _ANON.match(b):
            st["  ① 결손 이름이 익명 토큰"] += 1
            orig = inv.get(b)
            if orig and re.search(r"(?<![\w'])" + re.escape(orig) + r"(?![\w'])", vp):
                st["  ④ ★버그: 정답은 익명인데 프롬프트엔 실명"] += 1
                bugs.append(("④", b, orig, target.strip()[:70]))
        if b in m:
            st["  ② ★버그: 정답에 실명이 남음(매핑 키인데)"] += 1
            bugs.append(("②", b, m[b], target.strip()[:70]))
        anon = m.get(b)
        if anon and re.search(r"(?<![\w'])" + re.escape(anon) + r"(?![\w'])", vp):
            st["  ③ ★버그: 익명형은 프롬프트에 있음"] += 1
            bugs.append(("③", b, anon, target.strip()[:70]))
    if st["예제"] % 250 == 0:
        print(f"   … {st['예제']}/{N} ({time.time()-t0:.0f}s)", flush=True)

print(f"\n■ 결과 (예제 {st['예제']})\n")
for k in sorted(st):
    print(f"   {k:44s} {st[k]:6d}")
nb = st["  ② ★버그: 정답에 실명이 남음(매핑 키인데)"] + \
     st["  ③ ★버그: 익명형은 프롬프트에 있음"] + \
     st["  ④ ★버그: 정답은 익명인데 프롬프트엔 실명"]
d = max(st["★ 결손 이름"], 1)
print(f"\n   ★★ 익명화 탓 오신고  {nb}/{st['★ 결손 이름']} = {nb/d*100:.2f}%")
for b in bugs[:12]:
    print(f"      {b[0]} {b[1]:20s} ↔ {b[2]:20s} ← {b[3]}")
