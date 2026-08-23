#!/usr/bin/env python3
"""★ cut 이 학습 데이터에 **제대로 들어가는지** GPU 없이 검증한다.

## 왜 GPU 없이

확인해야 할 것은 gradient 가 아니라 **collate 가 내놓는 문자열**이다. cut 치환이
제대로 되는지, 정규화와 순서가 맞는지, 토큰 예산을 넘지 않는지 — 전부 CPU 로 볼 수 있다.
(GPU 학습은 7B 작업이 쓰고 있어 지금 못 쓴다.)

## 검사 항목

  ① cut 적용률        cuts 파일에 있는 스텝이 실제로 치환되는가
  ② 형태 검증         치환된 정답이 `assert (…) as H_asrt<n>. { exact … }` 형태인가
  ③ ★ 읽기 가능성     cut 이 참조하는 이름이 **프롬프트에서 읽히는가**
                      (cut 의 존재 이유가 이것이다 — 안 읽히면 소용없다)
  ④ 이름 충돌         `H_asrt*` 가 프롬프트·정답의 기존 이름과 겹치지 않는가
  ⑤ 정규화 상호작용   cut 후 정규화가 cut 이름을 깨지 않는가 / hopeless 는 정규화가 꺼지는가
  ⑥ 토큰 예산         정답이 `out_tokens` 를 넘지 않는가 (넘으면 잘려 문법이 깨진다)

사용: python3 scripts/verify_cut_collate.py [n]
"""
import collections
import copy
import os
import re
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("AUGMENT_V2", "1")
os.environ.setdefault("RERANK_PREMISES", "1")
os.environ.setdefault("INJECT_TYPES", "1")
os.environ.setdefault("INJECT_DEFS", "1")
# ★ HARD_SEQ_LEN 은 rango_defaults 기본값(3072)을 따른다 — 여기서 못 박지 않는다
os.environ.setdefault("FUNC_DEFS_PATH", "data/func_defs_v3.json")
os.environ.setdefault("CUTS_PATH", "data/cut_plans_all.jsonl")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf)
from tactic_gen import cut_lookup  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
_ID = re.compile(r"[A-Za-z_][\w']*")

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
conf = TacticDataConf.from_yaml(copy.deepcopy(cc["tactic_data"]))
ds = LmDataset.from_conf(conf, Split.TRAIN, 10 ** 9)
tok = AutoTokenizer.from_pretrained(cc["model_name"])
coll = example_collator_from_conf(conf.collator_conf)
OUT_TOK = conf.collator_conf.out_tokens

print(f"■ cuts 파일: {cut_lookup.enabled()}  {cut_lookup.stats()}")

st = collections.Counter()
bad = collections.defaultdict(list)


def check(mode: str):
    """mode: 'norm' (정규화 켬) / 'plain' (끔)"""
    if mode == "norm":
        os.environ["NORMALIZE_NAMES"] = "1"
        os.environ["NORMALIZE_RATE"] = "1.0"
        os.environ["NORMALIZE_PREMISES"] = "1"
        os.environ["NORMALIZE_THEOREM"] = "1"
    else:
        os.environ["NORMALIZE_NAMES"] = "0"
    n = 0
    for i in range(N):
        try:
            e = ds.raw_example(i)
        except Exception:
            continue
        key = f"{e.file_name}:{e.proof_idx}:{e.step_idx}"
        expect = cut_lookup.cut_for(key)
        hopeless = cut_lookup.is_hopeless(key)
        try:
            s = coll.collate(tok, e)
        except Exception as ex:
            st[f"[{mode}] collate 예외"] += 1
            bad[f"[{mode}] collate 예외"].append(str(ex)[:80])
            continue
        if "[TACTIC]" not in s:
            continue
        prompt, target = s.rsplit("[TACTIC]", 1)
        n += 1
        st[f"[{mode}] 예제"] += 1

        if hopeless:
            st[f"[{mode}] hopeless 스텝"] += 1
            # ⑤ hopeless 는 정규화가 꺼져야 한다.
            #   ★ 정규식(`[TfCLG]\d+`)으로 판정하면 원본 식별자 f1/T1/C0 를
            #     정규화 산출물로 오인한다(실측 3건 전부 오탐). 정규화 OFF 로
            #     같은 예제를 한 번 더 만들어 **타깃이 동일한지**로 판정한다.
            if mode == "norm":
                _sv = os.environ.get("NORMALIZE_NAMES", "1")
                os.environ["NORMALIZE_NAMES"] = "0"
                try:
                    _s0 = coll.collate(tok, e)
                    _t0 = _s0.rsplit("[TACTIC]", 1)[1] if "[TACTIC]" in _s0 else None
                finally:
                    os.environ["NORMALIZE_NAMES"] = _sv
                if _t0 is not None and _t0.strip() != target.strip():
                    st[f"[{mode}] ★ hopeless 인데 정규화됨"] += 1
                    bad["hopeless 정규화"].append(
                        f"norm={target.strip()[:45]} | plain={_t0.strip()[:45]}")

        if not expect:
            continue
        st[f"[{mode}] cut 대상"] += 1

        # ① 적용 확인 — 정규화되면 이름이 바뀌므로 구조로 본다
        has_assert = ("assert" in target or "eassert" in target)
        if not has_assert:
            st[f"[{mode}] ★ cut 이 적용 안 됨"] += 1
            bad["미적용"].append(f"{target.strip()[:60]}  (기대: {expect[:50]})")
            continue
        st[f"[{mode}] ✓ cut 적용됨"] += 1

        # ② 형태
        if not re.search(r"e?assert\s*\(.+\)\s*as\s+\w+\.\s*\{", target, re.S):
            st[f"[{mode}] ★ 형태 이상"] += 1
            bad["형태"].append(target.strip()[:80])

        # ③ 읽기 가능성 — cut 의 `exact X` 에서 X 가 프롬프트에 있는가
        #   ★ 옛 정규식 `[A-Za-z_][\w'.]*` 는 **문장 끝 마침표까지 삼켰다**
        #     ("gupaco5_mon." ). 그러면 base = split(".")[-1] = "" 가 되고
        #     `"" in pset` 은 항상 False → 전부 "없음"으로 잡혔다(실측 189건 전부 오탐).
        #     한정이름(Nat.add_comm)은 살리고 종결 마침표만 빼도록 고쳤다.
        pset = set(_ID.findall(prompt))
        for m in re.finditer(r"exact\s+@?([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)", target):
            nm = m.group(1)
            base = nm.split(".")[-1]
            if nm in pset or base in pset:
                st[f"[{mode}] ✓ exact 대상이 프롬프트에 있음"] += 1
            else:
                st[f"[{mode}] ★ exact 대상이 프롬프트에 없음"] += 1
                bad["exact 미포함"].append(f"{nm}  ←  {target.strip()[:60]}")

        # ④ 이름 충돌 — H_asrt 이름이 프롬프트에 이미 있으면 안 된다
        for nm in set(re.findall(r"as\s+(H_asrt\w*\d+)", target)):
            if re.search(r"(?<![\w'])" + re.escape(nm) + r"(?![\w'])", prompt):
                st[f"[{mode}] ★★ 이름 침범"] += 1
                bad["이름 침범"].append(f"{nm}  ←  {target.strip()[:60]}")

        # ⑥ 토큰 예산
        ntok = len(tok(target, add_special_tokens=False)["input_ids"])
        if ntok > OUT_TOK:
            st[f"[{mode}] ★ 정답이 out_tokens({OUT_TOK}) 초과"] += 1
            bad["토큰초과"].append(f"{ntok}토큰  {target.strip()[:60]}")
    return n


for mode in ("plain", "norm"):
    check(mode)

print(f"\n■ cut collate 검증 (TRAIN {N} 예제 · out_tokens={OUT_TOK})")
for k in sorted(st, key=lambda x: (x.split("]")[0], -st[x])):
    mark = "★" if "★" in k else " "
    print(f"  {mark} {k:44s} {st[k]:6d}")
if bad:
    print(f"\n  ■ 문제 표본")
    for k, v in bad.items():
        print(f"    [{len(v)}] {k}")
        for x in v[:3]:
            print(f"        {x}")
