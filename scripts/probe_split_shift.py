#!/usr/bin/env python3
"""★ **정규화 후 TRAIN 과 TEST 의 외부 참조 패턴이 같은 분포인가** — 전이의 전제.

학습은 "프롬프트의 `L3` 를 복사하라" 를 가르친다. 그 기술이 TEST 로 옮겨가려면
**정답이 요구하는 것의 분포**가 비슷해야 한다. 다르면 배운 게 안 먹는다.

split 은 **프로젝트 단위**로 갈린다(시간순). 즉 TEST 는 학습에 없던 프로젝트다.

  ★ 두 설정을 구분해야 한다 — 같은 잣대로 재면 틀린다.
      학습 분포   CUT_DROP_HOPELESS=1 · DROP_HALLUC=1
                  (가망 없는 스텝·환각 스텝을 **이웃 인덱스로 치환**한다)
      평가 분포   CUT_DROP_HOPELESS=0 · DROP_HALLUC=0
                  추론에는 정답이 없으므로 **아무것도 버릴 수 없다.**
      그리고 cut 계획은 TRAIN+VAL 만 있다(test 범위 = (0,0)). 이건 버그가 아니라
      **cut 이 정답에서 나오기 때문**이다 — 평가에는 존재할 수 없다.

재는 것 (정답이 쓰는 외부 참조 이름마다)
    · 익명 토큰(L#/T#/C#/f#/K#/G#)  → 프롬프트에서 **읽어야** 하는 것
    · 실명이고 프롬프트에 있음        → 읽을 수는 있으나 익명화 대상이 아니었던 것
    · 실명이고 프롬프트에 없음        → **외워서 써야** 하는 것 (= 환각)

사용: PYTHONPATH=src python3 scripts/probe_split_shift.py [split] [표본] [모드]
      모드: train(=드롭 적용) | eval(=드롭 없음)
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
N = int(sys.argv[2]) if len(sys.argv) > 2 else 500
MODE = (sys.argv[3] if len(sys.argv) > 3 else "train").lower()
if MODE == "eval":                      # 추론에는 정답이 없으니 아무것도 못 버린다
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
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", "/tmp/shift-cache")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
sp = getattr(Split, SPLIT)
ds = LmDataset.from_conf(conf, sp, None)
coll = example_collator_from_conf(conf.collator_conf)
HARD = int(os.environ.get("HARD_SEQ_LEN", "2048"))
TOTAL = ds.shuffled_idx.split_length(sp)

st = collections.Counter()
pref = collections.Counter()
lidx = []
tacs = collections.Counter()
random.seed(17)
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
        st["예외"] += 1
        continue
    if "[TACTIC]" not in full:
        continue
    st["예제"] += 1
    anon = set(m.values())
    prompt, target = full.rsplit("[TACTIC]", 1)
    ids = tok(full, add_special_tokens=False)["input_ids"]
    vis = tok.decode(ids[max(0, len(ids) - HARD):], skip_special_tokens=True)
    vp = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis
    tgt = re.sub(r'"[^"]*"', " ", _strip_coq_comments(target))
    if m:
        st["정규화 적용"] += 1
    if "H_asrt" in target:
        st["cut 주입(assert/final)"] += 1
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
    f = re.match(r"^\s*([A-Za-z_][\w']*)", tgt.strip())
    if f:
        tacs[f.group(1)] += 1
    used_ext = False
    for w in dict.fromkeys(re.findall(
            r"(?<![\w'.])([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)", tgt)):
        b = w.split(".")[-1]
        if (is_core(w) or b in local or w in local or b in intro or w in intro
                or w in tacn or b in tacn):
            continue
        used_ext = True
        st["외부 참조 이름"] += 1
        if b in anon:
            st["  ① 익명 토큰 (프롬프트에서 읽는다)"] += 1
            pref[b[0]] += 1
            mm = re.match(r"^L(\d+)$", b)
            if mm:
                lidx.append(int(mm.group(1)))
        elif b in STDLIB or w in STDLIB:
            st["  ② stdlib 실명 (안다고 가정)"] += 1
        elif re.search(r"(?<![\w'])" + re.escape(b) + r"(?![\w'])", vp):
            st["  ③ 실명이지만 프롬프트에 있음"] += 1
        else:
            st["  ④ ★실명이고 프롬프트에 없음 (외워야 함)"] += 1
    if used_ext:
        st["외부 참조를 쓰는 예제"] += 1
    if st["예제"] % 200 == 0:
        print(f"   … {st['예제']}/{N} ({time.time()-t0:.0f}s)", flush=True)

print(f"\n■ {SPLIT} · 모드 {MODE} · 예제 {st['예제']} ({time.time()-t0:.0f}s)\n")
E = max(st["예제"], 1)
R = max(st["외부 참조 이름"], 1)
for k in sorted(st):
    base = R if k.startswith("  ") else E
    print(f"   {k:40s} {st[k]:6d}  ({st[k]/base*100:5.1f}%)")
print(f"\n   익명 접두사: {dict(pref)}")
if lidx:
    lidx.sort()
    qq = lambda p: lidx[min(len(lidx) - 1, int(len(lidx) * p))]
    print(f"   L# 인덱스: 중앙 {qq(.5)} · p75 {qq(.75)} · p90 {qq(.9)} · 최대 {lidx[-1]}")
print(f"   정답 첫 토큰 상위: {[f'{k}:{v}' for k, v in tacs.most_common(8)]}")
