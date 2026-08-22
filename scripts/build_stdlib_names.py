#!/usr/bin/env python3
"""stdlib 선언 **이름 집합**을 만든다 — "이건 모델이 안다고 가정" 판정용.

## 왜 필요한가

rango 의 `PremiseFilter` 는 `lib/coq/theories` 의 premise 를 **풀에서 통째로 뺀다**.
그래서 `negb_involutive`·`pos_INR` 같은 stdlib lemma 는 검색으로 도달 불가고,
정답이 그걸 부르면 우리 검사기는 "환각" 으로 센다.

그런데 stdlib 은 **전부 보여 줄 수 없다**(파일 하나에 11,196개가 딸려 온다).
현실적인 선택은 "stdlib 은 모델이 안다고 가정하고 환각에서 뺀다" 이다.
그러려면 **어떤 이름이 stdlib 인지** 알아야 한다.

`func_defs_v3.json` 은 **정의만** 인덱싱해서 lemma 가 없다(pos_INR·map_length 부재).
그래서 DatasetFile 의 `file_context.avail_premises` 에서 경로가 `lib/coq/theories`
인 것들의 **선언 이름**을 모은다.

사용: PYTHONPATH=src python3 scripts/build_stdlib_names.py [파일수] [출력]
"""
import json
import logging
import os
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
from data_management.dataset_file import DatasetFile  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402

NFILE = int(sys.argv[1]) if len(sys.argv) > 1 else 60
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/stdlib_names.json"
D = Path("/tmp/coq-dataset/data_points")
sdb = SentenceDB.load(Path("/tmp/coq-dataset/sentences.db"))
STD = os.path.join("lib", "coq", "theories")
DECL = re.compile(
    r"^\s*(?:Global\s+|Local\s+|Program\s+|#\[[^\]]*\]\s*)*"
    r"(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|CoFixpoint|"
    r"Instance|Axiom|Parameter|Proposition|Property|Example|Let|Inductive|"
    r"CoInductive|Variant|Record|Class|Notation|Ltac)\s+"
    r"([A-Za-z_][\w']*)")

files = sorted(p.name for p in D.iterdir())
random.Random(0).shuffle(files)
names = set()
seen_paths = set()
done = 0
for fn in files:
    if done >= NFILE:
        break
    try:
        dp = DatasetFile.load(D / fn, sdb)
    except Exception:
        continue
    done += 1
    for p in dp.file_context.avail_premises:
        fp = getattr(p, "file_path", "") or ""
        if STD not in fp:
            continue
        seen_paths.add(fp)
        m = DECL.match((getattr(p, "text", "") or "").strip())
        if m:
            names.add(m.group(1))
    if done % 15 == 0:
        print(f"   … {done}/{NFILE} 파일 · 이름 {len(names):,}", flush=True)

json.dump(sorted(names), open(OUT, "w"))
print(f"\n■ stdlib 선언 이름 {len(names):,}개 · 파일 {len(seen_paths):,}개 → {OUT}")
for n in ["negb_involutive", "pos_INR", "map_length", "CRplus_0_r",
          "Forall_impl", "Rinv_0_lt_compat", "proof_irrelevance",
          "circonscrit", "holds", "app_nil_r"]:
    print(f"   {n:22s} {'stdlib ✓' if n in names else '아님'}")
