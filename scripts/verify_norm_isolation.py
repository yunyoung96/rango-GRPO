#!/usr/bin/env python3
"""★ 추론 정규화가 **학습 경로로 새지 않는가** — 구조 검증.

오늘 사고: `NORMALIZE_INFERENCE=1` 을 전역 env 로 켜자 `collate`(학습)가 내부에서
부르는 `collate_input` 이 프롬프트를 먼저 익명화했고, 뒤이어 collate 가 **이미
익명화된 텍스트**로 매핑을 다시 만들어 정답을 못 바꿨다. 프롬프트는 `Lemma L##`,
정답은 `ltu_inv` — 어긋난 채 학습된다(CompCert 결손 27 → 99).

이제 추론 정규화는 **명시 인자**(`collate_input(..., normalize=True)`)로만 켜진다.
env 가 켜져 있어도 학습은 영향받지 않아야 한다. 그것을 검사한다.

    A. env=1 이어도 `collate`(학습) 프롬프트 == env=0 일 때와 동일한가
    B. `collate_input(normalize=False)` 는 정규화하지 않는가
    C. `collate_input(normalize=True)` 는 정규화하는가
    D. 학습에서 프롬프트와 정답이 **같은 매핑**으로 익명화되는가
       (정답의 익명 토큰이 프롬프트에 선언과 함께 있는가)

사용: PYTHONPATH=src python3 scripts/verify_norm_isolation.py [SPLIT] [표본]
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
apply_v9_env(verbose=False)
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
SPLIT = (sys.argv[1] if len(sys.argv) > 1 else "TRAIN").upper()
N = int(sys.argv[2]) if len(sys.argv) > 2 else 150
if SPLIT == "TEST":
    os.environ["CUT_DROP_HOPELESS"] = "0"
    os.environ["DROP_HALLUC"] = "0"

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer,
                                    last_train_mapping, last_inference_mapping)

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", f"/tmp/iso-{SPLIT}")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), None)
coll = example_collator_from_conf(conf.collator_conf)
TOTAL = ds.shuffled_idx.split_length(getattr(Split, SPLIT))
_ANON = re.compile(r"(?<![\w'])([TfCLGK]\d+)(?![\w'])")
_DECLKW = (r"(?:Lemma|Theorem|Definition|Fixpoint|Corollary|Fact|Axiom|Proposition|"
           r"Instance|Notation|Remark|Property|Inductive|Record|Class|Ltac)\s+")

st = collections.Counter()
random.seed(31)
tried = 0
while st["예제"] < N and tried < N * 40:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        ex = ds.resolved_example(i)
    except Exception:
        continue
    st["예제"] += 1
    # A. env 켬/끔에서 학습 프롬프트가 같은가
    os.environ["NORMALIZE_INFERENCE"] = "1"
    a = coll.collate(tok, ex)
    ma = last_train_mapping()
    os.environ["NORMALIZE_INFERENCE"] = "0"
    b = coll.collate(tok, ex)
    if a == b:
        st["A 학습 프롬프트 env 무관 (동일)"] += 1
    else:
        st["A ★env 가 학습에 샌다"] += 1
    # B/C. collate_input 파라미터
    os.environ["NORMALIZE_INFERENCE"] = "1"
    coll.collate_input(tok, ex, normalize=False)
    m_off = last_inference_mapping()
    coll.collate_input(tok, ex)          # ★ 기본값 = 정규화 켬
    m_on = last_inference_mapping()
    st["B normalize=False 는 매핑 없음" if not m_off else "B ★False 인데 정규화됨"] += 1
    st["C 기본값이 정규화 켬" if m_on else "C (매핑할 이름 없음/꺼짐)"] += 1
    # D. 학습에서 정답의 익명 토큰이 프롬프트에 선언과 함께 있는가
    if "[TACTIC]" in a:
        prompt, target = a.rsplit("[TACTIC]", 1)
        for t in set(_ANON.findall(target)):
            st["D 정답의 익명 토큰"] += 1
            if re.search(_DECLKW + t + r"\b", prompt):
                st["  └ 프롬프트에 선언 있음"] += 1
            elif re.search(r"(?<![\w'])" + t + r"(?![\w'])", prompt):
                st["  └ 선언은 없지만 프롬프트엔 있음"] += 1
            else:
                st["  └ ★프롬프트 어디에도 없음"] += 1

print(f"\n■ {SPLIT} · 예제 {st['예제']}\n")
for k in sorted(st):
    print(f"   {k:38s} {st[k]:6d}")
bad = sum(v for k, v in st.items() if "★" in k)
print(f"\n   {'✅ 이상 없음' if bad == 0 else f'❌ 이상 {bad}건'}")
