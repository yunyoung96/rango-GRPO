#!/usr/bin/env python3
"""학습 프롬프트에 [TYPES]·[DEFINITIONS] 등 각 섹션이 **실제로** 들어가는지 잰다.

★ 왜 따로 재나: `AUGMENT_V2=1` 이면 `collate_input` 이 조기 반환해서 옛 경로
  (`types_section`·`ind_constructors_clean.json`)가 **죽은 코드**가 된다. 그래서
  "코드가 있다" 는 것으로는 아무것도 보증되지 않는다 — 완성된 프롬프트를 봐야 한다.

인덱스 전 구간을 훑으면서 섹션별로
  · 존재율      섹션 헤더가 나오는 비율
  · 내용 있음   헤더 뒤에 실제 항목이 있는 비율 (빈 껍데기 배제)
  · 토큰 점유   그 섹션이 프롬프트에서 차지하는 토큰 수 (중앙값/최대)
를 낸다.

사용: PYTHONPATH=src python3 scripts/probe_sections.py [구간당 건수]
"""
import collections
import copy
import logging
import os
import re
import statistics
import sys

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

N_PER = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 40

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer)

CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v9_conf.yaml")
cc = yaml.safe_load(open(CONF))
conf = TacticDataConf.from_yaml(copy.deepcopy(cc["tactic_data"]))
tok = get_tokenizer(cc["model_name"])
assert tok.truncation_side == "left", "학습과 다른 절단 방향으로는 잴 수 없다"
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)

TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)
HARD = int(os.environ.get("HARD_SEQ_LEN", "2048"))
SECS = ["TYPES", "DEFINITIONS", "PREMISES", "PROOFS", "SCRIPT", "STATE"]
SPOTS = [0, TOTAL // 6, TOTAL // 3, TOTAL // 2, TOTAL * 2 // 3, TOTAL * 5 // 6,
         TOTAL - N_PER - 2]

print(f"■ 섹션 주입 실측   TRAIN {TOTAL:,} · 구간 {len(SPOTS)}곳 × {N_PER}건 "
      f"= {len(SPOTS)*N_PER}건\n", flush=True)

have = collections.Counter()
nonempty = collections.Counter()
toks = collections.defaultdict(list)
items = collections.defaultdict(list)
trunc_lost = collections.Counter()
n = 0
sample = None

HDR = re.compile(r"\[(" + "|".join(SECS) + r")\]")

for sp in SPOTS:
    for i in range(sp, min(sp + N_PER, TOTAL)):
        try:
            s = coll.collate(tok, ds.resolved_example(i))
        except Exception:
            continue
        n += 1
        prompt = s.rsplit("[TACTIC]", 1)[0]
        # 섹션을 헤더 위치로 잘라 낸다
        pos = [(m.start(), m.group(1)) for m in HDR.finditer(prompt)]
        for k, (st, name) in enumerate(pos):
            end = pos[k + 1][0] if k + 1 < len(pos) else len(prompt)
            body = prompt[st:end].split("]", 1)[1].strip()
            have[name] += 1
            if body:
                nonempty[name] += 1
                toks[name].append(len(tok(body, add_special_tokens=False)["input_ids"]))
                items[name].append(len([x for x in body.split("\n") if x.strip()]))
        # 잘림으로 섹션이 통째로 사라지나 (truncation_side=left 라 앞쪽부터)
        enc = tok(s, max_length=HARD, truncation=True)
        cut = tok.decode(enc["input_ids"], skip_special_tokens=True)
        for name in SECS:
            if f"[{name}]" in prompt and f"[{name}]" not in cut:
                trunc_lost[name] += 1
        if sample is None and "[TYPES]" in prompt and "[DEFINITIONS]" in prompt:
            sample = prompt

print(f"■ 결과 (완성 프롬프트 {n}건)\n")
print(f"   {'섹션':14s} {'헤더':>7} {'내용있음':>9} {'항목수(중앙)':>13} "
      f"{'토큰(중앙/최대)':>17} {'잘림소실':>9}")
for name in SECS:
    h = have[name] / max(n, 1) * 100
    ne = nonempty[name] / max(n, 1) * 100
    tv = toks[name]
    iv = items[name]
    tm = f"{int(statistics.median(tv))}/{max(tv)}" if tv else "-"
    im = f"{statistics.median(iv):.0f}" if iv else "-"
    print(f"   {name:14s} {h:6.1f}% {ne:8.1f}% {im:>13s} {tm:>17s} "
          f"{trunc_lost[name]/max(n,1)*100:8.1f}%")

if sample:
    print("\n■ 예시 — [TYPES]/[DEFINITIONS] 부분만\n")
    for name in ("TYPES", "DEFINITIONS"):
        m = HDR.search(sample[sample.find(f"[{name}]"):])
        seg = sample[sample.find(f"[{name}]"):]
        nx = HDR.search(seg[1:])
        seg = seg[:nx.start() + 1] if nx else seg
        for ln in seg.strip().split("\n")[:9]:
            print("   " + ln[:110])
        print()
