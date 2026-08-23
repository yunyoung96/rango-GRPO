#!/usr/bin/env python3
"""★ **모의 학습** — 학습이 실제로 보게 될 데이터를 랜덤 순서로 훑어 점검한다.

HF `Trainer` 는 map-style dataset 에 `RandomSampler` 를 쓰므로 학습 순서는 랜덤이다.
여기서도 **무작위 인덱스**로 뽑아 같은 조건을 만든다.

보는 것
    · 파일 다양성      — 순차가 아니라 여러 파일에 흩어지는가
    · cut 주입         — assert/close/final 이 실제로 들어가는가 · 비율
    · 섹션 존재율      — PREMISES/PROOFS/STATE/SCRIPT/TYPES/DEFINITIONS/NOTATION/LTAC
    · 폐기율           — DROP_HALLUC · hopeless · uncovered
    · 길이             — hard_seq_len 초과율
    · 정규화 적용률

사용: PYTHONPATH=src python3 scripts/smoke_train_data.py [예제수]
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
apply_v9_env(verbose=True)
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
import tactic_gen.tactic_data as TD  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer,
                                    last_train_mapping)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
CONF = os.environ.get("SMOKE_CONF", "all_log/ft_qwen3b_v9_conf.yaml")
cc = yaml.safe_load(open(CONF))
_td = copy.deepcopy(cc["tactic_data"])
if os.environ.get("SMOKE_CACHE"):
    _td["cache_loc"] = os.environ["SMOKE_CACHE"]
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
HARD = int(os.environ.get("HARD_SEQ_LEN", str(cc.get("hard_seq_len", 2048))))
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)
print(f"■ TRAIN 총 {TOTAL:,} 스텝 · 표본 {N} · hard_seq_len {HARD}\n", flush=True)

st = collections.Counter()
files = collections.Counter()
lens = []
order = []
random.seed()                     # ★ 매 실행 다른 무작위 순서 (학습과 같은 조건)
t0 = time.time()
tried = 0
h0, u0 = TD._HALLUC_SKIPS[0], TD._UNCOVERED_SKIPS[0]
while st["예제"] < N and tried < N * 40:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        ex = ds.resolved_example(i)
    except Exception:
        st["resolved 예외"] += 1
        continue
    if ex is None:
        st["resolved None(폐기)"] += 1
        continue
    try:
        full = coll.collate(tok, ex)
        m = last_train_mapping()
    except Exception as e:
        st["collate 예외"] += 1
        continue
    if "[TACTIC]" not in full:
        st["[TACTIC] 없음"] += 1
        continue
    st["예제"] += 1
    fn = getattr(ex, "file_name", "?")
    files[fn] += 1
    if len(order) < 12:
        order.append(fn.split("/")[-1][:34])
    _, target = full.rsplit("[TACTIC]", 1)
    if m:
        st["정규화 적용"] += 1
    for sec in ("PREMISES", "PROOFS", "STATE", "SCRIPT", "TYPES",
                "DEFINITIONS", "NOTATION", "LTAC", "FACTS"):
        if f"[{sec}]" in full:
            st[f"  §{sec}"] += 1
    # cut 주입
    if "H_asrt" in target:
        st["★ cut — assert/final"] += 1
        if re.search(r"e?assert\s*\(.*\)\s*as\s+H_asrt", target, re.S):
            st["    ├ assert (명제를 세운다)"] += 1
        else:
            st["    └ final (H_asrt 를 쓴다)"] += 1
    elif re.match(r"^\s*e?exact\s+@?[\w'.]+\s*\.?\s*$", target.strip()):
        st["★ cut 후보 — close(exact L) 형태"] += 1
    n = len(tok(full, add_special_tokens=False)["input_ids"])
    lens.append(n)
    if n > HARD:
        st["  ⚠ hard_seq_len 초과"] += 1
    if st["예제"] % 100 == 0:
        print(f"   … {st['예제']}/{N} ({time.time()-t0:.0f}s)", flush=True)

print(f"\n■ 결과 (예제 {st['예제']} · {time.time()-t0:.0f}s)\n")
E = max(st["예제"], 1)
for k in sorted(st):
    print(f"   {k:34s} {st[k]:6d}  ({st[k]/E*100:5.1f}%)")
print(f"\n   ■ 무작위성 — 서로 다른 파일 **{len(files)}개** / 예제 {st['예제']}개"
      f"  (한 파일 최다 {files.most_common(1)[0][1]}회)")
print(f"      방문 순서 앞 12개: {' · '.join(order)}")
lens.sort()
q = lambda p: lens[min(len(lens) - 1, int(len(lens) * p))]
print(f"\n   ■ 길이  중앙 {q(.5)} · p90 {q(.9)} · p99 {q(.99)} · 최대 {lens[-1]}"
      f"   (상한 {HARD})")
print(f"\n   ■ 폐기  DROP_HALLUC {TD._HALLUC_SKIPS[0]-h0}건 · "
      f"uncovered {TD._UNCOVERED_SKIPS[0]-u0}건")
