#!/usr/bin/env python3
"""★ shell env 없이도 **같은 프롬프트**가 나오는가 — 파이썬 기본값 이관 검증.

설정을 `all_log/v9_env.sh` 의 export 에서 `src/rango_defaults.py` 로 옮겼다.
그 이관이 맞다면, **env 를 전부 비운 상태**와 **v9_env 를 읽은 상태**의 프롬프트가
바이트 단위로 같아야 한다. 다르면 어느 값이 안 옮겨졌다는 뜻이다.

    A. env 전부 해제 → 프롬프트 P0
    B. v9_env.sh 값 적용 → 프롬프트 P1
    P0 == P1 이어야 한다.

사용: PYTHONPATH=src python3 scripts/verify_defaults_equiv.py [표본]
"""
import collections
import copy
import logging
import os
import random
import sys

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
logging.disable(logging.CRITICAL)
import rango_defaults as RD  # noqa: E402
from _env_from_v9 import read_v9_env  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 120
V9 = read_v9_env()
KEYS = sorted(RD.PROD_DEFAULTS)
# 실험 시작 전에 **전부 해제**한다 (A 조건)
for k in KEYS:
    os.environ.pop(k, None)
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer)

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", "/tmp/equiv-cache")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)

# ── v9 와 파이썬 기본값이 다른 키가 있나 (있으면 그것부터 보고) ────────────────
diff = {k: (RD.PROD_DEFAULTS[k], V9[k]) for k in KEYS
        if k in V9 and str(V9[k]) != str(RD.PROD_DEFAULTS[k])}
print(f"■ 키 {len(KEYS)}개 · v9_env 와 값이 다른 것 {len(diff)}개")
for k, (a, b) in diff.items():
    print(f"   ★ {k:24s} 파이썬 {a!r} vs v9 {b!r}")
print()

st = collections.Counter()
random.seed(53)
tried = 0
bad = []
while st["예제"] < N and tried < N * 40:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        ex = ds.resolved_example(i)
    except Exception:
        continue
    st["예제"] += 1
    for k in KEYS:                       # A — env 없음
        os.environ.pop(k, None)
    a = coll.collate(tok, ex)
    for k, v in V9.items():              # B — v9_env 적용
        os.environ[k] = str(v)
    b = coll.collate(tok, ex)
    for k in KEYS:
        os.environ.pop(k, None)
    if a == b:
        st["동일"] += 1
    else:
        st["★다름"] += 1
        if len(bad) < 3:
            import difflib
            sm = difflib.SequenceMatcher(None, a, b)
            for tag, i1, i2, j1, j2 in sm.get_opcodes():
                if tag != "equal":
                    bad.append((tag, a[i1:i2][:80], b[j1:j2][:80]))
                    break

print(f"■ 결과 (예제 {st['예제']})")
for k in sorted(st):
    print(f"   {k:10s} {st[k]:5d}")
for t, x, y in bad:
    print(f"     [{t}] env없음: {x!r}")
    print(f"           v9적용 : {y!r}")
print(f"\n   {'✅ 이관 완료 — env 없이도 같은 프롬프트' if not st['★다름'] else '❌ 안 옮겨진 값이 있다'}")
