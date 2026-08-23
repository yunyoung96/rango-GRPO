#!/usr/bin/env python3
"""★ `assert (P)` 의 **안 보이는 이름**을 프롬프트에 넣어 줄 수 있나 — 실현 가능성.

## 왜

`verify_assert_ids.py` 로 재니 assert 하위스텝의 **10.4%** 가 볼 수 없는 이름을
명제에 포함한다. 두 가지 대응이 있다:

  (a) **버린다** — 그 스텝을 hopeless 로. 학습량 1.28% 손실.
  (b) **넣어 준다** — 그 이름의 선언을 `[DEFINITIONS]` 에 주입. 손실 0, 오히려 학습.

(b) 가 되려면 세 가지가 필요하다:
  ① 그 이름의 선언이 **인덱스에 있어야** 한다        (func_defs_v3 / ind_constructors)
  ② `pick_def` 가 **맞는 프로젝트 것**을 골라야 한다 (동명이 흔하다)
  ③ **토큰이 감당 가능**해야 한다                    (예산 합이 이미 3,416 > 2,048)

이 스크립트가 셋을 잰다.

사용: PYTHONPATH=src python3 scripts/probe_assert_inject.py [표본수]
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
import rango_defaults as _D
sys.path.insert(0, "scripts")
logging.disable(logging.CRITICAL)
from _env_from_v9 import apply_v9_env  # noqa: E402
apply_v9_env(verbose=True)
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer)
from tactic_gen.augment import pick_def  # noqa: E402
from _coq_vocab import is_core  # noqa: E402

N_WANT = int(sys.argv[1]) if len(sys.argv) > 1 else 200
FD = json.load(open(os.environ.get("FUNC_DEFS_PATH", "data/func_defs_v3.json")))
print(f"■ func_defs {len(FD):,} 항목", flush=True)

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = "/tmp/inject-probe-cache"
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
HARD = _D.num("HARD_SEQ_LEN")   # ★ 프로덕션 단일 출처. 2048 하드코딩은 기본값이 3072 로 오른 뒤 조용히 틀린 수치를 냈다
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)

CUTS = os.environ.get("CUTS_PATH", "data/cut_plans_all.jsonl")
plan_key = set()
for ln in open(CUTS):
    try:
        d = json.loads(ln)
    except Exception:
        continue
    if d.get("kind") == "plan" and d.get("cut"):
        m = re.match(r"^(.*\.v):(\d+):(\d+)$", d["sid"])
        if m:
            plan_key.add((m.group(1).split("repos/", 1)[-1].replace("/", "-"),
                          int(m.group(2)), int(m.group(3))))

_BIND = re.compile(r"(?:forall|fun|exists|∀|∃|λ)\s+([^,]*?)\s*[,.]|"
                   r"\(\s*([A-Za-z_][\w']*(?:\s+[A-Za-z_][\w']*)*)\s*:", re.S)
_ID = re.compile(r"(?<![\w'.])([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
_KW = set("forall exists fun let in if then else match with end return as Type Prop Set".split())

random.seed(9)
picked = []
probed = 0
while len(picked) < N_WANT * 6 and probed < 2_000_000:
    i = random.randrange(TOTAL)
    probed += 1
    try:
        s = ds.shuffled_idx.get_idx(Split.TRAIN, i)
    except Exception:
        continue
    if (s.file, s.proof_idx, s.step_idx) in plan_key:
        picked.append(i)

st = collections.Counter()
tok_cost = []
examples = []
for i in picked:
    if st["assert 스텝"] >= N_WANT:
        break
    try:
        ex = ds.resolved_example(i)
        full = coll.collate(tok, ex)
    except Exception:
        continue
    if "[TACTIC]" not in full:
        continue
    prompt, target = full.rsplit("[TACTIC]", 1)
    m = re.match(r"^e?assert\s*\((.*)\)\s*as\s+H_asrt", target.strip(), re.S)
    if not m:
        continue
    st["assert 스텝"] += 1
    P = m.group(1)
    ids_all = tok(full, add_special_tokens=False)["input_ids"]
    vis = tok.decode(ids_all[max(0, len(ids_all) - HARD):], skip_special_tokens=True)
    vp = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis

    bound = set()
    for b in _BIND.finditer(P):
        for g in b.groups():
            if g:
                bound |= set(re.findall(r"[A-Za-z_][\w']*", g))
    miss = []
    for nm in dict.fromkeys(_ID.findall(P)):
        if nm in _KW or nm.split(".")[0] in bound or nm in bound or is_core(nm):
            continue
        if not re.search(r"(?<![\w'])" + re.escape(nm.split(".")[-1]) + r"(?![\w'])", vp):
            miss.append(nm)
    if not miss:
        st["  전부 보임"] += 1
        continue
    st["★ 결손 있는 예제"] += 1
    where = getattr(ex, "file_name", None)
    got, cost = [], 0
    for nm in miss:
        st["결손 이름"] += 1
        base = nm.split(".")[-1]
        cands = FD.get(base)
        if not cands:
            st["  ① 인덱스에 없음"] += 1
            continue
        st["  ① 인덱스에 있음"] += 1
        d = pick_def(cands, where)
        if not d:
            st["  ② pick_def 가 못 고름(동명 모호)"] += 1
            continue
        st["  ② pick_def 성공"] += 1
        got.append((nm, d))
        cost += len(tok.tokenize(d))
    if got:
        tok_cost.append(cost)
        if len(examples) < 4:
            examples.append(f"idx={i}\n        결손 {miss}\n        "
                            + "\n        ".join(f"{n} → {d[:80]}" for n, d in got[:3]))
    if st["assert 스텝"] % 50 == 0:
        print(f"   … {st['assert 스텝']}/{N_WANT}", flush=True)

print(f"\n■ 결과 (assert 스텝 {st['assert 스텝']}건)\n")
for k in sorted(st):
    print(f"   {k:34s} {st[k]:6d}")
nm_ = max(st["결손 이름"], 1)
print(f"\n   ★ 주입 가능률 (결손 이름 기준) {st['  ② pick_def 성공']}/{st['결손 이름']} "
      f"= {st['  ② pick_def 성공']/nm_*100:.1f}%")
if tok_cost:
    tok_cost.sort()
    n2 = len(tok_cost)
    print(f"\n   ③ 토큰 비용 (결손 있는 예제당)")
    print(f"      중앙 {tok_cost[n2//2]} · p90 {tok_cost[int(n2*0.9)]} · 최대 {tok_cost[-1]}")
    print(f"      현재 DEFS_TOKENS={os.environ.get('DEFS_TOKENS','300')} 예산 대비")
if examples:
    print("\n   ■ 예")
    for x in examples:
        print(f"     {x}")
