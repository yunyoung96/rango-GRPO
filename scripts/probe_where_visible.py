#!/usr/bin/env python3
"""★ 정답이 쓰는 외부 이름은 프롬프트의 **어느 섹션**에서 읽히나.

익명화는 `[PREMISES]` 의 lemma 이름을 `L#` 로 바꾼다. 그런데 실측에서 정답이 쓰는
외부 이름 중 익명 토큰은 7.1% 뿐이고 44.3% 는 **실명인데 프롬프트에 있는** 것이었다.
그 44.3% 를 어디서 읽는지 알아야 "무엇을 가르치고 있는가" 가 정해진다.

    [PREMISES] 에서 읽는다  → 검색 결과를 보고 고르는 능력
    [PROOFS]  에서 읽는다  → **유사 증명을 모방**하는 능력
    [SCRIPT]  에서 읽는다  → 자기 증명의 앞부분을 이어가는 능력
    [STATE]/[TYPES]/[DEFINITIONS] → 문맥에서 이름을 집는 능력

사용: PYTHONPATH=src python3 scripts/probe_where_visible.py [SPLIT] [표본]
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

SPLIT = (sys.argv[1] if len(sys.argv) > 1 else "TRAIN").upper()
N = int(sys.argv[2]) if len(sys.argv) > 2 else 1200
if SPLIT == "TEST":
    os.environ["CUT_DROP_HOPELESS"] = "0"
    os.environ["DROP_HALLUC"] = "0"

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer,
                                    _strip_coq_comments, last_train_mapping)
from tactic_gen.normalize_names import introduced_names  # noqa: E402
from _coq_vocab import is_core  # noqa: E402

STDLIB = set(json.load(open("data/stdlib_names.json")))
cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", f"/tmp/where-{SPLIT}")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
sp = getattr(Split, SPLIT)
ds = LmDataset.from_conf(conf, sp, None)
coll = example_collator_from_conf(conf.collator_conf)
HARD = int(os.environ.get("HARD_SEQ_LEN", "2048"))
TOTAL = ds.shuffled_idx.split_length(sp)
SECS = ("PREMISES", "PROOFS", "STATE", "SCRIPT", "TYPES", "DEFINITIONS",
        "NOTATION", "LTAC")

st = collections.Counter()
where = collections.Counter()
solo = collections.Counter()
random.seed(29)
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
    anon = set(m.values())
    prompt, target = full.rsplit("[TACTIC]", 1)
    ids = tok(full, add_special_tokens=False)["input_ids"]
    vis = tok.decode(ids[max(0, len(ids) - HARD):], skip_special_tokens=True)
    vp = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis
    body = dict(re.findall(r"\[(\w+)\]\n(.*?)(?=\n\[\w+\]|\Z)", vp, re.S))
    tgt = re.sub(r'"[^"]*"', " ", _strip_coq_comments(target))
    local = set()
    g = re.search(r"\[STATE\]\n(.*?)(?=\n\[[A-Z]+\]|\Z)", prompt, re.S)
    if g:
        for ln in g.group(1).split("\n"):
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
    for w in dict.fromkeys(re.findall(
            r"(?<![\w'.])([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)", tgt)):
        b = w.split(".")[-1]
        if (is_core(w) or b in local or w in local or b in intro or w in intro
                or w in tacn or b in tacn):
            continue
        st["외부 참조 이름"] += 1
        if b in anon:
            st["  ① 익명 토큰"] += 1
            continue
        if b in STDLIB or w in STDLIB:
            st["  ② stdlib"] += 1
            continue
        hit = [s for s in SECS
               if s in body and re.search(r"(?<![\w'])" + re.escape(b) + r"(?![\w'])",
                                          body[s])]
        if not hit:
            st["  ④ 프롬프트에 없음"] += 1
            continue
        st["  ③ 실명·프롬프트에 있음"] += 1
        for s in hit:
            where[s] += 1
        if len(hit) == 1:
            solo[hit[0]] += 1
        else:
            solo["(둘 이상 섹션)"] += 1
    if st["예제"] % 300 == 0:
        print(f"   … {st['예제']}/{N} ({time.time()-t0:.0f}s)", flush=True)

print(f"\n■ {SPLIT} · 예제 {st['예제']} ({time.time()-t0:.0f}s)\n")
R = max(st["외부 참조 이름"], 1)
for k in sorted(st):
    base = R if k.startswith("  ") else max(st["예제"], 1)
    print(f"   {k:30s} {st[k]:6d}  ({st[k]/base*100:5.1f}%)")
S = max(st["  ③ 실명·프롬프트에 있음"], 1)
print(f"\n   ■ ③ 이 나타나는 섹션 (중복 허용 · 분모 = ③ {st['  ③ 실명·프롬프트에 있음']}개)")
for k, v in where.most_common():
    print(f"      {k:14s} {v:5d}  ({v/S*100:5.1f}%)")
print(f"\n   ■ **그 섹션에서만** 보이는 경우 (배타적)")
for k, v in solo.most_common():
    print(f"      {k:14s} {v:5d}  ({v/S*100:5.1f}%)")
