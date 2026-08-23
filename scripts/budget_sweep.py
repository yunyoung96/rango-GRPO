#!/usr/bin/env python3
"""★ premise 예산별로 **실제 프롬프트에 무엇이 살아남는지** 잰다.

## 왜 단순 증액이 답이 아닌가

  · 섹션 예산 합(896+640+1024+512+128+300+300 = 3800)이 `hard_seq_len=2048` 을 넘는다.
  · 조립 결과의 **11% 가 2048 을 초과**하고, `truncation_side="left"` 라
    **[PREMISES] 앞쪽부터 잘린다**.
  · `allocate_and_fmt(reverse=True)` 라 상위 premise 가 뒤에 놓이므로 잘리는 것은
    하위 premise 다 — 설계는 일관되지만, **예산을 늘려도 2048 에서 다시 잘린다.**
  · 게다가 컨텍스트가 길수록 어텐션이 희석된다(이 실험으로는 못 재고 학습으로만 확인 가능).

## 재는 것 (예산마다)

  · 프롬프트에 실제로 남는 premise 개수 (2048 절단까지 반영)
  · ★ gold 가 프롬프트에 남는 비율  ← A 의 진짜 값
  · 조립 길이 분포 · 2048 초과율
  · 무관 premise 개수(=주의 분산 대리 지표)

사용: python3 scripts/budget_sweep.py [n] [train|val|test]
"""
import collections
import copy
import os
import re
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("AUGMENT_V2", "1")
os.environ.setdefault("RERANK_PREMISES", "1")
os.environ.setdefault("INJECT_TYPES", "1")
os.environ.setdefault("INJECT_DEFS", "1")
# ★ HARD_SEQ_LEN 은 rango_defaults 기본값을 따른다 — 여기서 2048 로 못 박지 않는다
os.environ.setdefault("TYPES_TOKENS", "300")
os.environ.setdefault("DEFS_TOKENS", "300")
os.environ.setdefault("FUNC_DEFS_PATH", "data/func_defs_v3.json")
os.environ.setdefault("STRIP_TARGET_NL", "1")
sys.path.insert(0, "src")
import rango_defaults as _D
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402
from data_management.splits import Split  # noqa: E402
import tactic_gen.tactic_data as TD  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf)
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402
from tactic_gen.tier_rank import declname  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 600
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "train").upper()
BUDGETS = (640, 896, 1200, 1600, 2000)
HARD = int(os.environ["HARD_SEQ_LEN"])

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
tok = AutoTokenizer.from_pretrained(cc["model_name"])
tok.truncation_side = "left"

res = {}
for B in BUDGETS:
    tdc = copy.deepcopy(cc["tactic_data"])
    tdc["collator_conf"]["premise_tokens"] = B
    conf = TacticDataConf.from_yaml(tdc)
    ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), 10 ** 9)
    coll = example_collator_from_conf(conf.collator_conf)
    nprem, lens = [], []
    over = gold_ok = ngold = n = 0
    t0 = time.time()
    for i in range(N * 4):
        if n >= N:
            break
        try:
            e = ds.raw_example(i)
        except Exception:
            continue
        try:
            s = coll.collate(tok, e)
        except Exception:
            continue
        ids = tok(s, add_special_tokens=False)["input_ids"]
        lens.append(len(ids))
        over += (len(ids) > HARD)
        # ★ 2048 왼쪽 절단을 실제로 적용한 뒤의 프롬프트
        final = tok.decode(ids[-HARD:], skip_special_tokens=True) if len(ids) > HARD else s
        n += 1
        if "[PREMISES]" in final:
            seg = final.split("[PREMISES]", 1)[1]
            for sep in ("[PROOFS]", "[STATE]", "[SCRIPT]"):
                if sep in seg:
                    seg = seg.split(sep, 1)[0]
        else:
            seg = final.split("[PROOFS]")[0] if "[PROOFS]" in final else ""
        lines = [x for x in seg.split("\n") if x.strip()]
        nprem.append(len(lines))
        st = getattr(e, "proof_state", "") or ""
        tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
        golds = gold_lemmas(tac, local_names(st))
        if not golds:
            continue
        prem_all = [p if isinstance(p, str) else str(p)
                    for p in (getattr(e, "premises", None) or [])]
        if not any((declname(t) or "") in golds for t in prem_all):
            continue
        ngold += 1
        gset = {declname(x) for x in lines if declname(x)}
        if all(g in gset for g in golds):
            gold_ok += 1
    lens.sort()
    nprem.sort()
    res[B] = dict(n=n, nprem_med=nprem[len(nprem) // 2] if nprem else 0,
                  nprem_avg=sum(nprem) / max(len(nprem), 1),
                  len_med=lens[len(lens) // 2] if lens else 0,
                  len_p90=lens[len(lens) * 9 // 10] if lens else 0,
                  over=over / max(n, 1) * 100,
                  gold=gold_ok / max(ngold, 1) * 100, ngold=ngold,
                  sec=time.time() - t0)
    r = res[B]
    print(f"   예산 {B:5d} 완료 — premise 중앙 {r['nprem_med']}개 · "
          f"gold {r['gold']:.1f}% ({r['sec']:.0f}s)", flush=True)

print(f"\n■ {SPLIT} — premise 예산별 (각 {N}건 · hard_seq_len={HARD} 왼쪽절단 반영)")
print(f"\n   {'예산':>6s} {'프롬프트 premise':>16s} {'조립길이 중앙':>13s} {'p90':>7s} "
      f"{'2048초과':>9s} {'★gold 포함':>11s}")
for B in BUDGETS:
    r = res[B]
    mark = " ← 현재" if B == 896 else ""
    print(f"   {B:6d} {r['nprem_med']:9d} ({r['nprem_avg']:4.1f}) {r['len_med']:13d} "
          f"{r['len_p90']:7d} {r['over']:8.1f}% {r['gold']:10.1f}%{mark}")
print(f"\n   gold 판정 대상 {res[BUDGETS[0]]['ngold']}건")
print(f"\n   ※ 어텐션 희석은 이 실험으로 못 잰다 — 컨텍스트가 길수록 무관 premise 가")
print(f"     늘어나 모델이 헷갈릴 수 있고, 그것은 **학습·평가로만** 확인된다.")
