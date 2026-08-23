#!/usr/bin/env python3
"""★ 역익명화가 **진짜 이름을 오염**시킬 잔여 위험이 얼마나 남았나.

익명 토큰(`T1`·`f0`·`L3`)은 실제 Coq 선언 이름과 같은 꼴이다. 코퍼스 전수 조사:
    익명형 선언 873개 · 서로 다른 이름 120종 · 91개 프로젝트
    상위: L1(73) L2(56) L3(49) L4(38) L5(32) … f1(27) f2(20)
그리고 할당기는 **낮은 인덱스부터** 쓴다 — 정확히 겹치는 구간이다.

수정(2026-08-23)으로 추론의 회피 집합을 프롬프트 + 검색 100개 + 유사 증명 +
스크립트까지 넓혔다. 그래도 **그 넷 어디에도 없는** 실명이 매핑값과 겹치면
모델이 옳게 그 이름을 뱉어도 역매핑이 다른 이름으로 바꾼다.

여기서 재는 것 (예제마다)
    V = 매핑값 집합
    R = 그 프로젝트에 **실재하는** 익명형 선언 이름
    잔여 = V ∩ R           ← 실명인데 할당돼 버린 것 (= 오염 가능)

사용: PYTHONPATH=src python3 scripts/probe_anon_collision.py [SPLIT] [표본]
"""
import collections
import copy
import logging
import os
import random
import re
import sqlite3
import sys

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUT_DROP_HOPELESS"] = "0"
os.environ["DROP_HALLUC"] = "0"

SPLIT = (sys.argv[1] if len(sys.argv) > 1 else "TEST").upper()
N = int(sys.argv[2]) if len(sys.argv) > 2 else 500

# ── 프로젝트별 익명형 실명 목록 ──────────────────────────────────────────────
_H = re.compile(r"^\s*(?:#\[[^\]]*\]\s*)?(?:Global\s+|Local\s+|Polymorphic\s+|Program\s+)*"
                r"(?:Lemma|Theorem|Definition|Fixpoint|Inductive|Record|Class|Instance|"
                r"Corollary|Fact|Axiom|Variant|Structure|Notation|Ltac)\s+([A-Za-z_][\w']*)")
ANON = re.compile(r"^_[TfCLGK]\d+$")
REAL = collections.defaultdict(set)
_c = sqlite3.connect("raw-data/coq-dataset/sentences.db")
for t, f in _c.execute("select text,file_path from sentence where file_path like '%/repos/%'"):
    m = _H.match(t or "")
    if not m or not ANON.match(m.group(1)):
        continue
    p = re.search(r"/repos/([^/]+)/", f or "")
    if p:
        REAL[p.group(1)].add(m.group(1))
print(f"■ 익명형 실명 보유 프로젝트 {len(REAL)}개\n", flush=True)

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer,
                                    last_inference_mapping)

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", "/tmp/roundtrip")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), None)
coll = example_collator_from_conf(conf.collator_conf)
TOTAL = ds.shuffled_idx.split_length(getattr(Split, SPLIT))
_PROJ = re.compile(r"(?:^|/)repos/([^/]+)/")

st = collections.Counter()
hits = []
random.seed(777)
tried = 0
while st["예제"] < N and tried < N * 40:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        ex = ds.resolved_example(i)
        coll.collate_input(tok, ex, normalize=True)
        m = last_inference_mapping()
    except Exception:
        continue
    st["예제"] += 1
    if not m:
        continue
    st["매핑 있음"] += 1
    pm = _PROJ.search(getattr(ex, "file_name", "") or "")
    real = REAL.get(pm.group(1), set()) if pm else set()
    if not real:
        st["  그 프로젝트에 익명형 실명 없음"] += 1
        continue
    st["  익명형 실명이 있는 프로젝트"] += 1
    bad = set(m.values()) & real
    if bad:
        st["★ 잔여 충돌 (실명이 매핑값으로 할당됨)"] += 1
        if len(hits) < 8:
            inv = {v: k for k, v in m.items()}
            hits.append((pm.group(1), sorted(bad)[:3],
                         [inv[b] for b in sorted(bad)[:3]]))
    if st["예제"] % 150 == 0:
        print(f"   … {st['예제']}/{N}", flush=True)

print(f"\n■ {SPLIT} · 예제 {st['예제']}\n")
for k in sorted(st):
    print(f"   {k:40s} {st[k]:5d}")
d = max(st["  익명형 실명이 있는 프로젝트"], 1)
print(f"\n   잔여 충돌률  {st['★ 잔여 충돌 (실명이 매핑값으로 할당됨)']}/{d} "
      f"= {st['★ 잔여 충돌 (실명이 매핑값으로 할당됨)']/d*100:.2f}%"
      f"  (전체 예제 대비 {st['★ 잔여 충돌 (실명이 매핑값으로 할당됨)']/max(st['예제'],1)*100:.2f}%)")
for p, b, o in hits:
    print(f"     {p[:30]:32s} 실명 {b} ← 원래 {o}")
