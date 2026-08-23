#!/usr/bin/env python3
"""★ premise 가 프롬프트에서 사라지는 원인이 **패킹 예산**인가 **2048 절단**인가,
   그리고 그게 **rango 원본 문제**인가 **우리가 붙인 주입 때문**인가.

배경: CompCert(TEST)에서 결손 이름 131개 중 96개(73.3%)가 "검색 상위 22위 안인데
프롬프트에 없음" 이었다. TRAIN 은 결손 이름 35개 중 1개(2.9%)였다. 원인을 가른다.

세 지점을 구분한다
    검색 100개   → (premise 예산 896토큰 패킹) → 프롬프트 원본 → (2048 좌측 절단) → 모델이 보는 것
                        ①패킹에서 탈락                            ②절단에서 탈락

그리고 AUGMENT_V2 를 껐다 켜서(=우리 주입 유무) **우리 탓인지**를 본다.

사용: PYTHONPATH=src PROBE_SPLIT=TEST PROJ_FILTER=AbsInt-CompCert \
      python3 scripts/probe_truncation_blame.py [표본]
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
SPLIT = os.environ.get("PROBE_SPLIT", "TRAIN").upper()
PROJ = os.environ.get("PROJ_FILTER", "")
if SPLIT == "TEST":
    os.environ["CUT_DROP_HOPELESS"] = "0"
    os.environ.setdefault("DROP_HALLUC", "0")

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer,
                                    _strip_coq_comments)
from tactic_gen.normalize_names import introduced_names  # noqa: E402
from _coq_vocab import is_core  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
STDLIB = set(json.load(open("data/stdlib_names.json")))
cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", "/tmp/blame-cache")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
sp = getattr(Split, SPLIT)
ds = LmDataset.from_conf(conf, sp, None)
coll = example_collator_from_conf(conf.collator_conf)
HARD = int(os.environ.get("HARD_SEQ_LEN", "2048"))
TOTAL = ds.shuffled_idx.split_length(sp)

st = collections.Counter()
samples = []
random.seed(7)
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
    if PROJ and PROJ not in (getattr(ex, "file_name", "") or ""):
        continue
    st["예제"] += 1
    prompt = full.rsplit("[TACTIC]", 1)[0]
    ids = tok(full, add_special_tokens=False)["input_ids"]
    st["토큰 합계"] += len(ids)
    over = len(ids) > HARD
    st["2048 초과"] += over
    vis = tok.decode(ids[max(0, len(ids) - HARD):], skip_special_tokens=True)
    vp = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis
    # 섹션 존재
    a = "[PREMISES]" in prompt
    b = "[PREMISES]" in vp
    if a and not b:
        st["★ [PREMISES] 헤더가 절단됨"] += 1
    if not a:
        st["(원래 [PREMISES] 없음)"] += 1
    # 결손 이름의 책임 소재
    tgt = re.sub(r'"[^"]*"', " ", _strip_coq_comments(full.rsplit("[TACTIC]", 1)[1]))
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
        base = w.split(".")[-1]
        if (is_core(w) or base in local or w in local or base in intro or w in intro
                or w in tacn or base in tacn or base in STDLIB or w in STDLIB):
            continue
        pat = r"(?<![\w'])" + re.escape(base) + r"(?![\w'])"
        if re.search(pat, vp):
            continue
        st["★ 결손 이름"] += 1
        st["  (형태) 익명토큰" if re.match(r"^[TfCLGK]\d+$", base)
           else "  (형태) 실명"] += 1
        if len(samples) < 14:
            samples.append((base, tgt.strip()[:60]))
        in_prompt = bool(re.search(pat, prompt))
        in_search = any(re.search(pat, p) for p in prem)
        if in_prompt:
            st["  ② 절단에서 탈락 (프롬프트엔 있었다)"] += 1
        elif in_search:
            st["  ① 패킹에서 탈락 (검색엔 있었다)"] += 1
        else:
            st["  ③ 검색에도 없다"] += 1
    if st["예제"] % 200 == 0:
        print(f"   … {st['예제']}/{N} ({time.time()-t0:.0f}s)", flush=True)

E = max(st["예제"], 1)
R = max(st["★ 결손 이름"], 1)
tag = f"{SPLIT}{'/' + PROJ if PROJ else ''} · AUGMENT_V2={os.environ.get('AUGMENT_V2','0')}"
print(f"\n■ {tag} · 예제 {st['예제']}\n")
for k in sorted(st):
    if k == "토큰 합계":
        print(f"   {'평균 토큰':32s} {st[k]/E:8.0f}")
        continue
    base = R if k.startswith("  ") else E
    print(f"   {k:32s} {st[k]:6d}  ({st[k]/base*100:5.1f}%)")
for b, t in samples:
    print(f"      {b:22s} ← {t}")
