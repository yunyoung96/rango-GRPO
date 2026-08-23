#!/usr/bin/env python3
"""★ 검색은 찾았는데 **패킹이 버린** 결손이 얼마나 되나.

`probe_admit_rank` 는 "검색 100개 안에 있나" 만 봤다. 그런데 실측 사례에서
`whiskerL_pp` 는 **검색 순위 4위**인데도 프롬프트에 없었다 — `rerank_premises` 와
896토큰 하이브리드 패킹을 거치며 탈락한 것이다.

이건 §1 의 원리적 한계가 아니라 **엔지니어링 문제**라 고칠 수 있다. 규모를 잰다.

    결손 이름을 담은 premise 가 검색 결과 몇 위인가
      · 상위 22위 안(=예산에 들어갈 자리)인데 프롬프트에 없다  → **패킹 손실**
      · 23위 밖                                              → 순위 문제
      · 100개 안에 없다                                       → 검색 도달 불가

사용: PYTHONPATH=src python3 scripts/probe_pack_loss.py [표본]
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
import rango_defaults as _D
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
PROJ_FILTER = os.environ.get("PROJ_FILTER", "")
SPLIT_NAME = os.environ.get("PROBE_SPLIT", "TRAIN").upper()
if SPLIT_NAME == "TEST":
    os.environ["CUT_DROP_HOPELESS"] = "0"
    os.environ.setdefault("DROP_HALLUC", "0")
STDLIB = set(json.load(open("data/stdlib_names.json")))
cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", "/tmp/hsource-cache")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT_NAME), None)
coll = example_collator_from_conf(conf.collator_conf)
HARD = _D.num("HARD_SEQ_LEN")
TOTAL = ds.shuffled_idx.split_length(getattr(Split, SPLIT_NAME))

st = collections.Counter()
samples = []
random.seed(4)
tried = 0
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
    if PROJ_FILTER and PROJ_FILTER not in (getattr(ex, "file_name", "") or ""):
        continue
    st["예제"] += 1
    prompt, target = full.rsplit("[TACTIC]", 1)
    ids = tok(full, add_special_tokens=False)["input_ids"]
    vis = tok.decode(ids[max(0, len(ids) - HARD):], skip_special_tokens=True)
    vp = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis
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
    prem = [(p if isinstance(p, str) else str(p))
            for p in (getattr(ex, "premises", None) or [])]
    for w in dict.fromkeys(re.findall(
            r"(?<![\w'.])([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)", tgt)):
        b = w.split(".")[-1]
        if (is_core(w) or b in local or w in local or b in intro or w in intro
                or w in tacn or b in tacn or b in STDLIB or w in STDLIB):
            continue
        if re.search(r"(?<![\w'])" + re.escape(b) + r"(?![\w'])", vp):
            continue
        st["★ 결손 이름"] += 1
        # 그 이름을 **선언하는** premise 를 찾는다
        r_decl = r_any = None
        for j, p in enumerate(prem):
            if r_any is None and re.search(
                    r"(?<![\w'])" + re.escape(b) + r"(?![\w'])", p):
                r_any = j + 1
            if r_decl is None and re.search(
                    r"(?:Lemma|Theorem|Definition|Fixpoint|Inductive|Record|Instance|"
                    r"Notation|Axiom|Corollary|Fact|Class|Variant)\s+" + re.escape(b)
                    + r"(?![\w'])", p):
                r_decl = j + 1
        if r_any is None:
            st["  ① 검색 100개 어디에도 없다"] += 1
        elif r_any <= 22:
            st["  ② ★패킹 손실 — 상위 22위 안인데 프롬프트에 없다"] += 1
            if len(samples) < 8:
                samples.append((b, r_any, r_decl, prem[r_any - 1][:90],
                                target.strip()[:60]))
        else:
            st["  ③ 23위 밖 — 순위 문제"] += 1
        if r_decl is not None:
            st["    (참고) 선언 자체가 검색에 있음"] += 1
    if st["예제"] % 250 == 0:
        print(f"   … {st['예제']}/{N} ({time.time()-t0:.0f}s)", flush=True)

print(f"\n■ 결과 (예제 {st['예제']})\n")
d = max(st["★ 결손 이름"], 1)
for k in sorted(st):
    pct = f"  {st[k]/d*100:5.1f}%" if k.startswith("  ") else ""
    print(f"   {k:46s} {st[k]:6d}{pct}")
print("\n   ■ 패킹 손실 표본")
for b, ra, rd, ptxt, tg in samples:
    print(f"      {b:22s} 순위 {ra:3d}(선언 {rd}) ← {tg}")
    print(f"        premise: {ptxt}")
