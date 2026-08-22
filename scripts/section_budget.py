#!/usr/bin/env python3
"""★ 2048 절단으로 [PREMISES] 가 통째로 날아가는 15% 를 어떻게 줄이나.

## 문제

섹션 예산 합이 hard_seq_len 을 넘는다.

    premise 896 + proof 640 + state 1024 + script 512 + out 128 + types 300 + defs 300
    = 3800  >  hard_seq_len 2048

초과분은 truncation_side="left" 로 **맨 앞([PREMISES])부터** 잘린다.
실측(TRAIN 400건): 15.0% 가 [PREMISES] 섹션을 통째로 잃는다.

## 비교하는 설정

  · 현재                    premise 896 · proof 640 · state 1024 · script 512
  · proof 축소              proof 640 → 256   (비슷한 증명은 premise 보다 덜 중요할 수 있다)
  · state 축소              state 1024 → 640
  · proof+state 축소        둘 다
  · hard_seq_len 증액       2048 → 3072  (근본 해법, 학습 속도·메모리 대가)

## 지표

  · [PREMISES] 소실률
  · 프롬프트에 남는 premise 개수
  · ★ gold 프롬프트 포함률

사용: python3 scripts/section_budget.py [n] [train|val|test]
"""
import collections
import copy
import os
import sys
import time

# ★ 설정의 출처는 `all_log/v9_env.sh` **하나**다. 여기에 값을 다시 적으면 반드시
#   어긋나고, 어긋나도 오류가 안 난다 — 조용히 다른 실험을 재게 된다(실제로 겪었다:
#   옛 CUTS_PATH 로 U1 을 재고, structural 로 "학습과 같은 설정" 감사를 돌렸다).
sys.path.insert(0, "scripts")
from _env_from_v9 import apply_v9_env  # noqa: E402
apply_v9_env(verbose=True)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("AUGMENT_V2", "1")
os.environ.setdefault("RERANK_PREMISES", "1")
os.environ.setdefault("INJECT_TYPES", "1")
os.environ.setdefault("INJECT_DEFS", "1")
os.environ.setdefault("TYPES_TOKENS", "300")
os.environ.setdefault("DEFS_TOKENS", "300")
os.environ.setdefault("FUNC_DEFS_PATH", "data/func_defs_v3.json")
os.environ.setdefault("STRIP_TARGET_NL", "1")
os.environ.setdefault("RETRIEVAL_MODE", "eqx")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf)
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402
from tactic_gen.tier_rank import declname  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 600
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "train").upper()

# (라벨, premise, proof, state, script, hard)
CASES = [
    ("현재", 896, 640, 1024, 512, 2048),
    ("proof 640→256", 896, 256, 1024, 512, 2048),
    ("state 1024→640", 896, 640, 640, 512, 2048),
    ("proof+state 축소", 896, 256, 640, 512, 2048),
    ("hard 2048→3072", 896, 640, 1024, 512, 3072),
    ("hard 3072 + premise 1200", 1200, 640, 1024, 512, 3072),
]

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
tok = AutoTokenizer.from_pretrained(cc["model_name"])
tok.truncation_side = "left"

print(f"■ {SPLIT} — 섹션 예산 재배분 ({N}건)\n")
rows = []
for label, pb, pr, stt, sc, hard in CASES:
    os.environ["HARD_SEQ_LEN"] = str(hard)
    tdc = copy.deepcopy(cc["tactic_data"])
    tdc["collator_conf"].update(premise_tokens=pb, proof_tokens=pr,
                                state_tokens=stt, script_tokens=sc)
    tdc["hard_seq_len"] = hard
    conf = TacticDataConf.from_yaml(tdc)
    ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), 10 ** 9)
    coll = example_collator_from_conf(conf.collator_conf)
    lost = gold_ok = ngold = n = 0
    npr = []
    lens = []
    t0 = time.time()
    for i in range(N * 4):
        if n >= N:
            break
        try:
            e = ds.raw_example(i)
            s = coll.collate(tok, e)
        except Exception:
            continue
        n += 1
        ids = tok(s, add_special_tokens=False)["input_ids"]
        lens.append(len(ids))
        final = tok.decode(ids[-hard:], skip_special_tokens=True) if len(ids) > hard else s
        prem_all = [p if isinstance(p, str) else str(p)
                    for p in (getattr(e, "premises", None) or [])]
        if not prem_all:
            continue                       # 애초에 검색 결과가 없는 경우는 제외
        if "[PREMISES]" not in final:
            lost += 1
            lines = []
        else:
            seg = final.split("[PREMISES]", 1)[1]
            for sep in ("[PROOFS]", "[STATE]", "[SCRIPT]"):
                if sep in seg:
                    seg = seg.split(sep, 1)[0]
            lines = [x for x in seg.split("\n") if x.strip()]
        npr.append(len(lines))
        st = getattr(e, "proof_state", "") or ""
        tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
        golds = gold_lemmas(tac, local_names(st))
        if not golds or not any((declname(t) or "") in golds for t in prem_all):
            continue
        ngold += 1
        gset = {declname(x) for x in lines if declname(x)}
        if all(g in gset for g in golds):
            gold_ok += 1
    npr.sort()
    lens.sort()
    rows.append((label, lost / max(len(npr), 1) * 100,
                 npr[len(npr) // 2] if npr else 0,
                 gold_ok / max(ngold, 1) * 100, ngold,
                 lens[len(lens) // 2] if lens else 0, time.time() - t0))
    r = rows[-1]
    print(f"   {label:26s} 소실 {r[1]:5.1f}% · premise 중앙 {r[2]:3d} · "
          f"gold {r[3]:5.1f}%  ({r[6]:.0f}s)", flush=True)

print(f"\n   {'설정':26s} {'[PREMISES]소실':>13s} {'premise중앙':>11s} {'★gold포함':>10s} {'길이중앙':>9s}")
for label, l, m, g, ng, ln, _ in rows:
    print(f"   {label:26s} {l:12.1f}% {m:11d} {g:9.1f}% {ln:9d}")
print(f"\n   gold 판정 대상 {rows[0][4]}건")
