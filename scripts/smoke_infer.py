#!/usr/bin/env python3
"""★ **모의 추론** — 학습한 형태 그대로 프롬프트를 만들고, 생성물을 되돌리는가.

학습은 이름을 `L#`·`T#`·`K#` 로 익명화한다. 추론도 같은 형태여야 하고, 생성된
tactic 은 Coq 에 넣기 전에 **되돌려야** 한다(Coq 은 `L0` 를 모른다).

검사
    A. `normalize_inference` 기본값이 켜져 있는가 (파이썬 인자)
    B. 모델에 들어가는 프롬프트가 실제로 익명화되는가
    C. 생성물의 익명 토큰이 **원래 이름으로 되돌아오는가**
    D. 매핑에 없는 이름(모델이 지어낸 것)은 **그대로 두는가** (환각을 숨기지 않는다)
    E. 정규화를 끄면 프롬프트에 실명이 보이는가 (대조군)

사용: PYTHONPATH=src python3 scripts/smoke_infer.py <checkpoint> [표본]
"""
import collections
import copy
import logging
import os
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

CKPT = Path(sys.argv[1] if len(sys.argv) > 1
            else "models/rango-qwen3b-smoke-final/checkpoint-12")
N = int(sys.argv[2]) if len(sys.argv) > 2 else 6

import yaml  # noqa: E402
import rango_defaults as RD  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    last_inference_mapping)
from tactic_gen.normalize_names import apply_inverse  # noqa: E402
from model_deployment.model_wrapper import DecoderLocalWrapper  # noqa: E402

print(f"■ 체크포인트 {CKPT}")
print(f"   랭커 {RD.get('RETRIEVAL_MODE')} · 정규화(학습) {RD.get('NORMALIZE_NAMES')}"
      f" · Ltac {RD.get('NORMALIZE_LTAC')}\n", flush=True)

w = DecoderLocalWrapper.from_checkpoint(CKPT)
print(f"   A. normalize_inference = {w.normalize_inference}"
      f"   {'✅' if w.normalize_inference else '❌ 꺼져 있다'}\n", flush=True)

# ── 평가 조건: cut 계획도 드롭도 없다 ────────────────────────────────────────
os.environ["CUT_DROP_HOPELESS"] = "0"
os.environ["DROP_HALLUC"] = "0"
cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", "/tmp/infer-smoke")
conf = TacticDataConf.from_yaml(_td)
ds = LmDataset.from_conf(conf, Split.TEST, None)
TOTAL = ds.shuffled_idx.split_length(Split.TEST)
_ANON = re.compile(r"(?<![\w'])([TfCLGK]\d+)(?![\w'])")

st = collections.Counter()
random.seed(97)
tried = 0
shown = 0
while st["예제"] < N and tried < N * 60:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        ex = ds.resolved_example(i)
    except Exception:
        continue
    st["예제"] += 1
    # B. 모델이 실제로 받는 프롬프트
    p_on = w.collator.collate_input(w.tokenizer, ex, normalize=True)
    m = last_inference_mapping()
    p_off = w.collator.collate_input(w.tokenizer, ex, normalize=False)
    st["B 프롬프트 익명화됨" if _ANON.search(p_on) else "B ★익명 토큰 없음"] += 1
    st["E 정규화 끄면 실명" if (p_off != p_on or not m) else "E ★끔/켬이 같다"] += 1
    if not m:
        st["  (매핑 없음 — 바꿀 이름이 없는 예제)"] += 1
        continue
    # C. 실제 생성 → 자동 역매핑
    res = w.get_recs(ex, 3, "", False, None)
    tacs = res.next_tactic_list
    left = [t for t in tacs for x in set(_ANON.findall(t)) if x in set(m.values())]
    st["C ★익명 토큰이 그대로 남음" if left else "C 생성물에 익명 토큰 없음"] += 1
    # D. 매핑에 없는 이름은 보존
    fake = "apply Lzz999_not_in_map."
    st["D 미지 이름 보존" if apply_inverse(fake, m).strip() == fake else "D ★바뀜"] += 1
    if shown < 3:
        shown += 1
        # ★ **실제로 바뀐 줄**을 골라 보여 준다(안 바뀐 줄을 보이면 증거가 안 된다)
        la = p_on.split("\n")
        lb = p_off.split("\n")
        pair = next(((x, y) for x, y in zip(la, lb) if x != y and x.strip()),
                    ("(차이 없음)", ""))
        print(f"── 예시 {shown} (idx={i})")
        print(f"   프롬프트[정규화 OFF] {pair[1][:96]}")
        print(f"   프롬프트[정규화 ON ] {pair[0][:96]}")
        print(f"   매핑 {len(m)}개 · 예: {list(m.items())[:3]}")
        print(f"   생성(역매핑 후)     {[t.strip()[:56] for t in tacs]}\n", flush=True)

print(f"■ 결과 (예제 {st['예제']})\n")
for k in sorted(st):
    print(f"   {k:36s} {st[k]:4d}")
bad = sum(v for k, v in st.items() if "★" in k)
print(f"\n   {'✅ 추론 경로 정상' if bad == 0 else f'❌ 이상 {bad}건'}")
