#!/usr/bin/env python3
"""★ 평가 경로 검증 — 프롬프트 정규화 + 역익명화가 학습과 **일치**하는가.

모델은 `L0`·`T2`·`K1` 기준으로 학습된다. 평가에서 실명 프롬프트를 넣으면 어긋난다.
그래서 `NORMALIZE_INFERENCE=1` 로 추론 프롬프트도 정규화하고, 생성된 tactic 은
`apply_inverse` 로 되돌린다(Coq 은 `L0` 를 모른다).

검사 넷
    A. 추론 프롬프트에 매핑이 실제로 적용되는가 (익명 토큰이 보이는가)
    B. 왕복 무결 — `apply L0.` → apply_inverse → `apply <원래이름>.`
    C. 매핑에 없는 이름(`L999`)은 **그대로 둔다** (환각을 숨기지 않는다)
    D. ★ 학습 프롬프트(`collate`)와 평가 프롬프트(`collate_input`)가 **같은가**
       — 매핑 산출 방식이 달라(avoid_text·premise 필터) 번호가 어긋날 수 있다.

사용: PYTHONPATH=src python3 scripts/verify_infer_normalize.py [SPLIT] [표본]
"""
import collections
import copy
import difflib
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
os.environ["NORMALIZE_INFERENCE"] = "1"

SPLIT = (sys.argv[1] if len(sys.argv) > 1 else "TEST").upper()
N = int(sys.argv[2]) if len(sys.argv) > 2 else 200
if SPLIT == "TEST":
    os.environ["CUT_DROP_HOPELESS"] = "0"
    os.environ["DROP_HALLUC"] = "0"

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer,
                                    last_inference_mapping, last_train_mapping)
from tactic_gen.normalize_names import apply_inverse  # noqa: E402

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", f"/tmp/infnorm-{SPLIT}")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
sp = getattr(Split, SPLIT)
ds = LmDataset.from_conf(conf, sp, None)
coll = example_collator_from_conf(conf.collator_conf)
TOTAL = ds.shuffled_idx.split_length(sp)

st = collections.Counter()
diffs = []
random.seed(41)
tried = 0
while st["예제"] < N and tried < N * 40:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        ex = ds.resolved_example(i)
        p_inf = coll.collate_input(tok, ex)
        m_inf = last_inference_mapping()
    except Exception:
        st["collate_input 예외"] += 1
        continue
    st["예제"] += 1
    if not m_inf:
        st["  매핑 없음"] += 1
        continue
    st["  매핑 있음"] += 1
    st["  매핑 항목"] += len(m_inf)
    # A. 익명 토큰이 프롬프트에 실제로 있는가
    seen = sum(1 for v in m_inf.values()
               if re.search(r"(?<![\w'])" + re.escape(v) + r"(?![\w'])", p_inf))
    st["A 프롬프트에 보이는 익명 토큰"] += seen
    # B. 왕복
    orig, anon = next(iter(m_inf.items()))
    back = apply_inverse(f"apply {anon}.", m_inf)
    if back.strip() == f"apply {orig}.":
        st["B 왕복 성공"] += 1
    else:
        st["B ★왕복 실패"] += 1
    # C. 없는 이름은 그대로
    if apply_inverse("apply L999zz.", m_inf).strip() == "apply L999zz.":
        st["C 미지 이름 보존"] += 1
    else:
        st["C ★미지 이름이 바뀜"] += 1
    # E. ★ 불변식 — 프롬프트에 나타나는 모든 익명 토큰이 **선언을 갖는가**
    pm = re.search(r"\[PREMISES\]\n(.*?)(?=\n\[[A-Z]+\]|\Z)", p_inf, re.S)
    prem_blk = pm.group(1) if pm else ""
    for t_ in set(re.findall(r"(?<![\w'])(L\d+)(?![\w'])", p_inf)):
        st["E 프롬프트의 L# 토큰"] += 1
        if re.search(r"(?:Lemma|Theorem|Definition|Fixpoint|Corollary|Fact|Axiom|"
                     r"Proposition|Instance|Notation|Remark|Property)\s+" + t_ + r"\b",
                     prem_blk):
            st["  └ 선언 있음"] += 1
        else:
            st["  └ ★선언 없음"] += 1
    # D. 학습 프롬프트와 같은가
    try:
        full = coll.collate(tok, ex)
        m_tr = last_train_mapping()
        p_tr = full.rsplit("[TACTIC]", 1)[0] + "[TACTIC]"
        a = re.sub(r"\s+", " ", p_tr).strip()
        b = re.sub(r"\s+", " ", p_inf).strip()
        # E' 학습 쪽 불변식 (공정 비교용 기준선)
        pm2 = re.search(r"\[PREMISES\]\n(.*?)(?=\n\[[A-Z]+\]|\Z)", p_tr, re.S)
        blk2 = pm2.group(1) if pm2 else ""
        for t2 in set(re.findall(r"(?<![\w'])(L\d+)(?![\w'])", p_tr)):
            st["E' 학습 프롬프트의 L# 토큰"] += 1
            if re.search(r"(?:Lemma|Theorem|Definition|Fixpoint|Corollary|Fact|Axiom|"
                         r"Proposition|Instance|Notation|Remark|Property)\s+" + t2 + r"\b",
                         blk2):
                st["  └ 학습 선언 있음"] += 1
            else:
                st["  └ ★학습 선언 없음"] += 1
        if a == b:
            st["D 학습 프롬프트와 동일"] += 1
        else:
            st["D ★프롬프트 불일치"] += 1
            if m_tr != m_inf:
                st["    ├ 매핑 자체가 다름"] += 1
            if len(diffs) < 3:
                sm = difflib.SequenceMatcher(None, a, b)
                for tag, i1, i2, j1, j2 in sm.get_opcodes():
                    if tag != "equal" and (i2 - i1 or j2 - j1):
                        diffs.append((tag, a[i1:i2][:90], b[j1:j2][:90]))
                        break
    except Exception:
        st["D collate 예외"] += 1

print(f"\n■ {SPLIT} · 예제 {st['예제']}\n")
E = max(st["  매핑 있음"], 1)
for k in sorted(st):
    print(f"   {k:34s} {st[k]:6d}")
print(f"\n   매핑 있는 예제 {st['  매핑 있음']}/{st['예제']} · "
      f"항목 평균 {st['  매핑 항목']/E:.1f}")
for d in diffs:
    print(f"     [{d[0]}] 학습: {d[1]!r}")
    print(f"           평가: {d[2]!r}")
