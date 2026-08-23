#!/usr/bin/env python3
"""`_fit_premises` 의 판정과 **최종 프롬프트**가 얼마나 어긋나는지 잰다.

## 왜

cut 을 넣을지는 `_fit_premises(example)` 로 "gold 가 보이나" 를 판정한다. 그런데 그건
premise 예산(896토큰)만 본 값이고, 최종 프롬프트는 `hard_seq_len`(2,048)로 **앞에서부터**
잘린다(truncation_side="left", [PREMISES] 가 맨 앞). 섹션 예산 합이 3,416 이라 넘칠 수 있다.

  → `_fit_premises` 가 "보인다" 고 한 premise 가 실제로는 잘려 사라질 수 있고,
    그러면 cut 을 안 만든 채 모델에게 **안 보이는 이름**을 내라고 가르친다.
    실측 P4 `idx=1692662 subst_arr` 가 그 형태다.

## 무엇을 재나

표본마다
  ① `_fit_premises` 가 담은 premise 이름 집합
  ② 최종(절단 후) 프롬프트의 [PREMISES] 에 실제로 남은 이름 집합
을 만들어 ① − ② (사라진 것)을 센다.

사용: PYTHONPATH=src python3 scripts/audit_fit_gap.py [표본수]
"""
import copy
import logging
import os
import random
import re
import sys

sys.path.insert(0, "src")
import rango_defaults as _D
sys.path.insert(0, "scripts")
logging.disable(logging.CRITICAL)
from _env_from_v9 import apply_v9_env  # noqa: E402
apply_v9_env(verbose=True)
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
# ★★ 정규화를 **끈다.** 켜면 [PREMISES] 의 선언 이름이 `L0`·`L3` 로 바뀌는데
#   `_fit_premises` 는 정규화 **전** 원문을 준다. 그대로 비교하면 이름이 안 맞아
#   "75% 가 절단으로 사라졌다" 는 **거짓 수치**가 나온다(실제로 그렇게 나왔다).
#   여기서 보려는 것은 절단 하나뿐이므로 정규화만 끄면 사과 대 사과가 된다.
os.environ["NORMALIZE_NAMES"] = "0"

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 150
cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", "/tmp/fitgap-cache")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
HARD = _D.num("HARD_SEQ_LEN")
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)
DECL = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                  r"Instance|Axiom|Proposition|Example|Let|Inductive|Record|Class)\s+"
                  r"([A-Za-z_][\w']*)", re.M)

print(f"■ _fit_premises vs 최종 프롬프트   표본 {N}\n", flush=True)
random.seed(11)
n = over = 0
lost_tot = fit_tot = 0
trunc = 0
examples = []
for _ in range(N * 4):
    if n >= N:
        break
    i = random.randrange(TOTAL)
    try:
        ex = ds.resolved_example(i)
        fit = ds._fit_premises(ex)
        s = coll.collate(tok, ex)
    except Exception:
        continue
    n += 1
    ids = tok(s, add_special_tokens=False)["input_ids"]
    if len(ids) > HARD:
        trunc += 1
    vis = tok.decode(ids[max(0, len(ids) - HARD):], skip_special_tokens=True)
    vp = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis
    fit_names = set(DECL.findall(fit))
    if not fit_names:
        continue
    lost = {x for x in fit_names
            if not re.search(r"(?<![\w'])" + re.escape(x) + r"(?![\w'])", vp)}
    fit_tot += len(fit_names)
    lost_tot += len(lost)
    if lost:
        over += 1
        # ★ 손실이 정말 **절단**에서 오는지 분해한다. 안 넘치는 예제에서 손실이 나면
        #   내 비교가 틀린 것이다(정규화·이름 경계 등).
        if len(ids) > HARD:
            globals()["lost_trunc"] = globals().get("lost_trunc", 0) + 1
        else:
            globals()["lost_notrunc"] = globals().get("lost_notrunc", 0) + 1
            if len(globals().setdefault("bad_ex", [])) < 3:
                globals()["bad_ex"].append(f"idx={i} (안 넘침, {len(ids)}토큰) 사라짐 {sorted(lost)[:3]}")
        if len(examples) < 5:
            examples.append(f"idx={i} 담김 {len(fit_names)} · 사라짐 {len(lost)} "
                            f"({sorted(lost)[:3]})")

print(f"   표본 {n} · 2048 초과 {trunc} ({trunc/max(n,1)*100:.1f}%)")
print(f"   `_fit_premises` 가 담은 이름 총 {fit_tot:,}")
print(f"   그중 절단으로 **사라진** 이름 {lost_tot:,}  ({lost_tot/max(fit_tot,1)*100:.1f}%)")
print(f"   하나라도 사라진 예제 {over}/{n}  ({over/max(n,1)*100:.1f}%)")
print()
for x in examples:
    print(f"      {x}")
print()
print(f"   손실 분해:  절단 때문 {globals().get('lost_trunc',0)}  ·  "
      f"★ 절단이 아닌데 손실 {globals().get('lost_notrunc',0)}")
for x in globals().get("bad_ex", []):
    print(f"      {x}")
print()
print("   ※ '절단이 아닌데 손실' 이 있으면 비교 자체가 틀린 것이다 — 먼저 그걸 고친다.")
print("   ※ 절단 때문인 몫만큼 cut 판정이 낙관적이다.")
