#!/usr/bin/env python3
"""★ 씨앗을 넓혔는데 왜 주입이 안 늘었나 — 어느 단계에서 떨어지는지 센다.

실측: 씨앗 확장 후에도 환각률이 17.2% → 17.6% 로 그대로였고, 개수 상한을 8→20 으로
올려도 나오는 정의 수가 5·3·2 로 동일했다. 즉 **상한에 닿지도 않았다** —
씨앗이 후보를 못 만들어 내고 있다.

`_expand` 의 각 관문에서 몇 개가 떨어지는지 센다:

    씨앗 총수
      → _bad_head / _STDLIB 에서 탈락
      → index.get(name) 없음            (func_defs 인덱스 결손)
      → pick_def 가 None                (동명 모호 · 프로젝트 불일치)
      → _is_type_def 불일치             (DEFINITIONS 인데 타입이거나 반대)
      → _ALIAS_DEF (모듈 별칭)
      → 길이 초과로 스킵
      → **살아남음**

사용: PYTHONPATH=src python3 scripts/probe_seed_drop.py [표본수]
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
                                    example_collator_from_conf, get_tokenizer, _it_index)
from tactic_gen import augment as AUG  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 150
FD = json.load(open(os.environ.get("FUNC_DEFS_PATH", "data/func_defs_v3.json")))
cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = "/tmp/seeddrop-cache"
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)


def ntok(s):
    return len(tok(s or "", add_special_tokens=False)["input_ids"])


st = collections.Counter()
ex_bad = []
random.seed(7)
tried = 0
while st["예제"] < N and tried < N * 25:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        ex = ds.resolved_example(i)
    except Exception:
        continue
    st["예제"] += 1
    goal = getattr(ex, "proof_state", "") or ""
    proj = getattr(ex, "file_name", None)
    # augment_v2_section 과 **같은 방식**으로 씨앗을 만든다
    hyp = goal.split("\n\n")[0] if "\n\n" in goal else ""
    seeds = []
    for src, txt in (("결론", goal.split("\n\n")[-1]),
                     ("가설", hyp),
                     ("premise", " ".join(
                         (p if isinstance(p, str) else str(p))[:400]
                         for p in (getattr(ex, "premises", None) or [])[:12])),
                     ("스크립트", (getattr(ex, "proof_script", "") or "")[-1200:])):
        for t in re.findall(r"[A-Za-z_][\w']*", txt or "")[:80]:
            seeds.append((src, t))
    seen = set()
    for src, nm in seeds:
        if nm in seen:
            continue
        seen.add(nm)
        st["씨앗(중복제거)"] += 1
        st[f"  씨앗출처 {src}"] += 1
        if AUG._bad_head(nm):
            st["  ① _bad_head 탈락"] += 1
            continue
        if nm in AUG._STDLIB:
            st["  ② _STDLIB 탈락"] += 1
            continue
        cands = FD.get(nm)
        if not cands:
            st["  ③ 인덱스에 없음"] += 1
            continue
        d = AUG.pick_def(cands, proj)
        if not d:
            st["  ④ pick_def 실패(동명 모호·프로젝트 불일치)"] += 1
            if len(ex_bad) < 10:
                ex_bad.append(f"{nm:22s} 후보 {len(cands) if isinstance(cands,dict) else 1:3d}개 · proj={str(proj)[-40:]}")
            continue
        if AUG._ALIAS_DEF.match(d):
            st["  ⑤ 모듈 별칭"] += 1
            continue
        st["  ✓ 살아남음"] += 1
        st[f"    (출처 {src})"] += 1
    if st["예제"] % 50 == 0:
        print(f"   … {st['예제']}/{N}", flush=True)

print(f"\n■ 결과 (예제 {st['예제']})\n")
for k in sorted(st):
    print(f"   {k:44s} {st[k]:7d}")
S = max(st["씨앗(중복제거)"], 1)
print(f"\n   씨앗 → 정의 생존율  {st['  ✓ 살아남음']}/{st['씨앗(중복제거)']} "
      f"= {st['  ✓ 살아남음']/S*100:.2f}%")
print(f"   예제당 살아남은 정의  {st['  ✓ 살아남음']/max(st['예제'],1):.1f}개")
if ex_bad:
    print("\n   ■ pick_def 실패 예")
    for x in ex_bad:
        print(f"     {x}")
