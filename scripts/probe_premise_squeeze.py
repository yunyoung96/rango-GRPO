#!/usr/bin/env python3
"""★ [TYPES]/[DEFINITIONS] 주입이 **premise 를 밀어내는가**.

## 왜

섹션 예산 합이 상한을 넘는다:
    premise 896 + state 1024 + script 512 + proof 256 + TYPES 300 + DEFS 300 + out 128
    = 3,416  >  hard_seq_len 2,048
프롬프트는 `truncation_side="left"` 로 잘리고 **[PREMISES] 가 맨 앞**이다.
그러면 주입한 만큼 premise 가 밀려 나가고, 결국 **rango 원본보다 premise 를 덜 보여
주는** 결과가 될 수 있다 — 목적과 정반대다.

코드 주석은 "밀어내지 않는다" 고 주장한다(`augment_v2_section` 이 남은 자리를 계산해
자기 블록만 자른다). **실측으로 확인한다.**

## 무엇을 재나

같은 예제를 세 조건으로 만들어 **절단 후 살아남은 premise 선언 수**를 센다.

    ① rango 기준   INJECT_TYPES=0 INJECT_DEFS=0
    ② 지금 설정     INJECT_TYPES=1 INJECT_DEFS=1  (AUGMENT_V2=1)
    ③ v1 위치      AUGMENT_V2=0                    (섹션을 [STATE] 앞에 넣던 옛 방식)

사용: PYTHONPATH=src python3 scripts/probe_premise_squeeze.py [표본수]
"""
import collections
import copy
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

N = int(sys.argv[1]) if len(sys.argv) > 1 else 120
cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = "/tmp/squeeze-cache"
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
HARD = int(os.environ.get("HARD_SEQ_LEN", "2048"))
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)
DECL = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                  r"Instance|Axiom|Parameter|Proposition|Example|Let)\s+"
                  r"([A-Za-z_][\w']*)", re.M)

CONDS = [("① rango 기준 (주입 없음)", {"INJECT_TYPES": "0", "INJECT_DEFS": "0", "AUGMENT_V2": "1"}),
         ("② 지금 (v2 · 맨 뒤 주입)", {"INJECT_TYPES": "1", "INJECT_DEFS": "1", "AUGMENT_V2": "1"}),
         ("③ v1 위치 (STATE 앞)",     {"INJECT_TYPES": "1", "INJECT_DEFS": "1", "AUGMENT_V2": "0"})]

acc = {c[0]: collections.Counter() for c in CONDS}
lens = {c[0]: [] for c in CONDS}
prem = {c[0]: [] for c in CONDS}
random.seed(2)
idxs, tried = [], 0
while len(idxs) < N and tried < N * 20:
    i = random.randrange(TOTAL)
    tried += 1
    idxs.append(i)

import time  # noqa: E402
t0 = time.time()
done = 0
for i in idxs:
    row = {}
    ok = True
    for name, env in CONDS:
        for k, v in env.items():
            os.environ[k] = v
        try:
            full = coll.collate(tok, ds.resolved_example(i))
        except RuntimeError as _re:
            # ★ 캐시 스탬프 불일치 같은 설정 오류는 삼키면 안 된다 — 0건으로 조용히 끝난다
            sys.stderr.write(f"\n★★ 중단: {str(_re)[:300]}\n")
            sys.exit(3)
        except Exception:
            ok = False
            break
        ids = tok(full, add_special_tokens=False)["input_ids"]
        vis = tok.decode(ids[max(0, len(ids) - HARD):], skip_special_tokens=True)
        vp = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis
        m = re.search(r"\[PREMISES\]\n(.*?)(?=\n\[[A-Z]+\]|\Z)", vp, re.S)
        row[name] = (len(ids), len(set(DECL.findall(m.group(1)))) if m else 0)
    if not ok:
        continue
    done += 1
    for name, _ in CONDS:
        L, P = row[name]
        lens[name].append(L)
        prem[name].append(P)
        acc[name]["초과"] += (L > HARD)
    if done % 40 == 0:
        print(f"   … {done}/{N} ({time.time()-t0:.0f}s)", flush=True)

print(f"\n■ 결과 (예제 {done})\n")
print(f"   {'조건':26s} {'전체토큰(중앙)':>14} {'2048초과':>9} {'절단후 premise 수':>18}")
for name, _ in CONDS:
    L = sorted(lens[name]); P = sorted(prem[name]); n = len(L)
    if not n:
        continue
    print(f"   {name:26s} {L[n//2]:14,} {acc[name]['초과']/n*100:8.1f}% "
          f"  중앙 {P[n//2]:3d} · 평균 {sum(P)/n:5.1f}")
base = CONDS[0][0]
for name, _ in CONDS[1:]:
    a = sum(prem[base]) / max(len(prem[base]), 1)
    b = sum(prem[name]) / max(len(prem[name]), 1)
    print(f"\n   {name} vs {base}:  premise {a:.1f} → {b:.1f}  ({b-a:+.1f})")
