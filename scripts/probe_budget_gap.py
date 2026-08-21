#!/usr/bin/env python3
"""**예산 두 개가 어긋나는 자리**를 잰다.

  · `build_cuts.py` 는 `PREMISE_TOKENS=896` 만 보고 "gold 가 프롬프트에 들어간다" 를 판정한다.
  · 실제 프롬프트는 그 뒤에 `HARD_SEQ_LEN=2048` 로 **한 번 더** 잘린다.

    섹션 예산 합 = 896(premise) + 256(proof) + 512(script) + 1024(state)
                 + 300(types) + 300(defs) + 128(out) = 3,416  >  2,048

  넘치면 `truncation_side="left"` 가 **앞쪽부터** 지운다. premise 는 `[::-1]` 로
  **나쁜 것이 앞**이라 최상위는 살아남지만, 하위 premise 는 사라진다.
  → build_cuts 가 "들어간다" 고 본 gold 가 실제로는 없을 수 있다(낙관 편향).

무엇을 재나
  · nfit_896   896 예산으로 담기는 premise 개수 (build_cuts 의 가정)
  · nfit_real  2048 절단 후 실제로 남는 premise 개수
  · 손실       nfit_896 − nfit_real · 그리고 **몇 위까지 안전한가**

부수적으로 정규화가 **모듈 한정 이름**(`O.eq`)의 꼬리를 건드리는 빈도도 센다.

사용: PYTHONPATH=src python3 scripts/probe_budget_gap.py [구간당 건수]
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
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)

TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)
HARD = int(os.environ.get("HARD_SEQ_LEN", "2048"))
SPOTS = [0, TOTAL // 6, TOTAL // 3, TOTAL // 2, TOTAL * 2 // 3, TOTAL * 5 // 6,
         TOTAL - N_PER - 2]
print(f"■ 예산 어긋남 실측   TRAIN {TOTAL:,} · {len(SPOTS)}곳 × {N_PER}건\n", flush=True)

# 모듈 한정 이름의 꼬리가 정규화 이름으로 바뀐 흔적: `X.T3` `X.f0` `X.L7`
QUAL_NORM = re.compile(r"(?<![\w'])[A-Za-z_][\w']*\.([TfCLG]\d+)(?![\w'])")

lost = []
safe_n = []
overflow = 0
qual_hits = collections.Counter()
n = 0
nfit_all = []

# 모듈 한정 이름의 꼬리가 정규화 이름으로 바뀐 흔적: `X.T3` `X.f0` `X.L7`
QUAL_NORM = re.compile(r"(?<![\w'])[A-Za-z_][\w']*\.([TfCLG]\d+)(?![\w'])")

for sp in SPOTS:
    for i in range(sp, min(sp + N_PER, TOTAL)):
        try:
            s = coll.collate(tok, ds.resolved_example(i))
        except Exception:
            continue
        n += 1
        for m in QUAL_NORM.finditer(s):
            qual_hits[m.group(1)[0]] += 1
        if "[PREMISES]" not in s:
            continue

        # ── premise 줄의 **문자 구간**을 정확히 잡는다 ────────────────────
        #   `allocate_and_fmt` 가 "\n".join 이므로 한 줄 = 한 premise 다.
        p0 = s.index("[PREMISES]") + len("[PREMISES]")
        p1 = len(s)
        for h in ("[PROOFS]", "[SCRIPT]", "[STATE]", "[TYPES]", "[DEFINITIONS]",
                  "[TACTIC]"):
            k = s.find(h, p0)
            if k != -1:
                p1 = min(p1, k)
        spans, off = [], p0
        for ln in s[p0:p1].split("\n"):
            if ln.strip():
                spans.append((off, off + len(ln)))
            off += len(ln) + 1
        nfit = len(spans)
        nfit_all.append(nfit)

        # ── 절단으로 **완전히 사라지는** premise 를 센다 ──────────────────
        #   토큰 오프셋으로 잰다. 문자열 포함으로 세면 디코딩이 공백을 바꿔
        #   멀쩡한 premise 도 '사라졌다' 고 잘못 세게 된다(실제로 그랬다).
        enc = tok(s, add_special_tokens=False, return_offsets_mapping=True)
        ids = enc["input_ids"]
        full = len(ids)
        if full <= HARD:
            lost.append(0)
            safe_n.append(nfit)
            continue
        overflow += 1
        drop = full - HARD                       # 앞에서 이만큼 잘린다
        cut_char = enc["offset_mapping"][drop][0] if drop < len(ids) else len(s)
        gone = sum(1 for a, b in spans if b <= cut_char)
        lost.append(gone)
        safe_n.append(nfit - gone)

print(f"■ 결과 (프롬프트 {n}건)\n")
print(f"   2048 초과              {overflow:4d}건  {overflow/max(n,1)*100:5.1f}%")
if lost:
    nz = [x for x in lost if x > 0]
    print(f"   premise 손실 있음      {len(nz):4d}건  {len(nz)/max(n,1)*100:5.1f}%")
    if nz:
        print(f"   손실 개수 (중앙/최대)  {statistics.median(nz):.0f} / {max(nz)}")
    print(f"   nfit(896 예산으로 담긴 개수) 중앙 "
          f"{statistics.median(nfit_all):.0f} · 최대 {max(nfit_all)}")
    # ★ premise 가 아예 없는 예제(약 18%)를 섞으면 분포가 왜곡된다 — 빼고 본다.
    pos = [(a, b) for a, b in zip(nfit_all, safe_n) if a > 0]
    print(f"   premise 가 있는 예제 {len(pos)}건 / 전체 {len(nfit_all)}건")
    print(f"   ★ **상위 몇 위까지 살아남나** — build_cuts 는 nfit 위까지 다 산다고 본다")
    sr = sorted(b for _, b in pos)
    for q, lab in ((1, "1%"), (5, "5%"), (10, "10%"), (25, "25%"), (50, "중앙")):
        k = max(0, len(sr) * q // 100 - 1)
        print(f"        {lab:6s} {sr[k]:3d}위까지")
    # 이 값으로 자르면 몇 %의 예제에서 build_cuts 판정이 맞아지나
    print(f"   ★ nfit 상한을 K 로 걸었을 때 **판정이 맞는 예제 비율**")
    for K in (8, 12, 16, 20, 24, 999):
        okc = sum(1 for a, b in pos if min(a, K) <= b)
        cut_up = sum(1 for a, b in pos if a > K)
        print(f"        K={K if K < 999 else '제한없음':>6}  정확 {okc/len(pos)*100:5.1f}%"
              f"   ·  cut 이 늘어나는 예제 {cut_up/len(pos)*100:5.1f}%")
print()
print(f"■ 모듈 한정 이름의 꼬리가 정규화된 흔적 (`X.f0` 꼴)")
tot = sum(qual_hits.values())
print(f"   총 {tot}회 · 프롬프트당 {tot/max(n,1):.2f}회   {dict(qual_hits)}")
