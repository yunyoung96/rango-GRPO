#!/usr/bin/env python3
"""★ `assert (P) as H.` 의 **P 안에 나오는 이름**이 프롬프트에 보이는가.

## 왜

`U1` 은 `close` 하위스텝(`exact L.`)의 **L** 만 봤다. 그런데 `assert` 하위스텝은
모델이 **명제 P 를 직접 써야** 하고, P 에는 타입 이름·함수 이름이 들어간다.

    assert (forall n m, n + m = Nat.iter (N.to_nat n) N.succ m) as H_asrt0.
                                 └─ Nat.iter · N.to_nat · N.succ ─┘

이 이름들이 프롬프트에 없으면 모델은 **볼 수 없는 이름으로 명제를 지어내야** 한다.
`exact L` 이 안 보이는 것과 똑같은 문제인데, 지금까지 측정하지 않았다.

  ★ 직관: "gold lemma 를 쓰는 스텝이니 goal/가설에 그 타입이 나올 것" —
    맞을 수도 있지만 **확인해야 한다.** lemma 는 goal 에 없는 보조 개념을
    끌어올 수 있다(위 예의 `Nat.iter`·`N.to_nat` 이 그렇다).

## 무엇을 세나

P 의 **자유 식별자**(P 안에서 바인딩되지 않은 것)마다 어디서 보이는지 분류한다.

    [STATE]  goal·가설            ← 가장 자연스러운 출처
    [TYPES]  주입된 inductive     ← INJECT_TYPES=1
    [DEFINITIONS] 주입된 정의     ← INJECT_DEFS=1
    [PREMISES] / [PROOFS] / [SCRIPT]
    ★ 어디에도 없음               ← 환각

절단 **후** 프롬프트로 본다 — 모델이 보는 것이 그것이다.

사용: PYTHONPATH=src python3 scripts/verify_assert_ids.py [표본수]
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
apply_v9_env(verbose=True)
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer)

N_WANT = int(sys.argv[1]) if len(sys.argv) > 1 else 200
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
print(f"■ 계획 cut {len(plan_key):,}건", flush=True)

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", "/tmp/assert-ids-cache")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
HARD = int(os.environ.get("HARD_SEQ_LEN", "2048"))
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)

# P 안에서 **바인딩되는** 이름 — 자유 식별자에서 뺀다
_BIND = re.compile(
    r"(?:forall|fun|exists|∀|∃|λ)\s+([^,]*?)\s*[,.]|"
    r"\(\s*([A-Za-z_][\w']*(?:\s+[A-Za-z_][\w']*)*)\s*:", re.S)
_ID = re.compile(r"(?<![\w'.])([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
# Coq 기본 어휘 — 모델이 원래 아는 것
from _coq_vocab import is_core  # noqa: E402
_KW = set("""forall exists fun let in if then else match with end return as
Type Prop Set fix cofix struct where""".split())

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
print(f"   cut 후보 {len(picked):,}개 확보\n", flush=True)

st = collections.Counter()
where = collections.Counter()
miss_ex = []
import time  # noqa: E402
t0 = time.time()
for i in picked:
    if st["assert 스텝"] >= N_WANT:
        break
    try:
        full = coll.collate(tok, ds.resolved_example(i))
    except Exception:
        continue
    if "[TACTIC]" not in full:
        continue
    prompt, target = full.rsplit("[TACTIC]", 1)
    tg = target.strip()
    m = re.match(r"^e?assert\s*\((.*)\)\s*as\s+H_asrt", tg, re.S)
    if not m:
        continue
    st["assert 스텝"] += 1
    P = m.group(1)

    # 절단 후 보이는 프롬프트
    ids_all = tok(full, add_special_tokens=False)["input_ids"]
    vis = tok.decode(ids_all[max(0, len(ids_all) - HARD):], skip_special_tokens=True)
    vp = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis
    body = dict(re.findall(r"\[(\w+)\]\n(.*?)(?=\n\[\w+\]|\Z)", vp, re.S))

    bound = set()
    for b in _BIND.finditer(P):
        for g in b.groups():
            if g:
                bound |= set(re.findall(r"[A-Za-z_][\w']*", g))
    free = []
    for nm in _ID.findall(P):
        base = nm.split(".")[0]
        if nm in _KW or base in bound or nm in bound:
            continue
        if is_core(nm):
            st["  기본 어휘(모델이 앎)"] += 1
            continue
        free.append(nm)
    _miss_here = 0
    for nm in dict.fromkeys(free):
        st["자유 식별자"] += 1
        pat = re.compile(r"(?<![\w'])" + re.escape(nm.split(".")[-1]) + r"(?![\w'])")
        hit = [sec for sec in ("STATE", "TYPES", "DEFINITIONS", "PREMISES",
                               "PROOFS", "SCRIPT") if pat.search(body.get(sec, ""))]
        if hit:
            st["  ✓ 보임"] += 1
            where["+".join(hit[:2])] += 1
        else:
            st["★ 안 보임"] += 1
            _miss_here += 1
            if len(miss_ex) < 8:
                miss_ex.append(f"idx={i} {nm}  ←  {P[:70]}")
    # ★ **예제 단위** — 하나라도 안 보이면 그 assert 는 쓸 수 없다
    if _miss_here:
        st["★★ 예제: 하나라도 안 보임"] += 1
        st[f"   (그 예제의 결손 개수 {min(_miss_here,5)}{'+' if _miss_here>=5 else ''})"] += 1
    else:
        st["  예제: 전부 보임"] += 1
    if st["assert 스텝"] % 50 == 0:
        print(f"   … assert {st['assert 스텝']}건 ({time.time()-t0:.0f}s)", flush=True)

print(f"\n■ 결과 (assert 스텝 {st['assert 스텝']}건)\n")
for k in sorted(st):
    print(f"   {k:34s} {st[k]:6d}")
nf = max(st["자유 식별자"], 1)
print(f"\n   ★★ **예제 단위** 가시율 "
      f"{st['  예제: 전부 보임']}/{st['assert 스텝']} = "
      f"{st['  예제: 전부 보임']/max(st['assert 스텝'],1)*100:.1f}%")
print(f"   자유 식별자 가시율 {st['  ✓ 보임']}/{st['자유 식별자']} "
      f"= {st['  ✓ 보임']/nf*100:.1f}%")
print("\n   ■ 어디서 보이나 (상위)")
for k, v in where.most_common(8):
    print(f"     {k:28s} {v:5d}  {v/max(st['  ✓ 보임'],1)*100:5.1f}%")
if miss_ex:
    print("\n   ■ 안 보이는 예")
    for x in miss_ex:
        print(f"     {x}")
