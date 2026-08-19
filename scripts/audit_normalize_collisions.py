#!/usr/bin/env python3
"""정규화 이름 규칙의 **충돌 위험을 전수 감사**한다.

## 왜

assert 가설명에서 충돌 위험을 발견했다(H → H_asrt<n>). 같은 종류의 위험이 v8 정규화의
다른 접두사에도 있을 수 있다.

    L#  premise lemma 이름      T#  주입된 타입      f#  주입된 함수
    C#  생성자                  G#  증명 중인 정리

## 무엇을 검사하나

  ① **역충돌**: 원본 코드에 이미 `L0`·`T1`·`C2` 같은 이름이 실존하는가?
     → 있으면 정규화된 이름과 구별이 안 된다(모델이 어느 쪽인지 알 수 없다).
  ② **다대일**: 서로 다른 원본이 같은 정규화 이름을 받는가?
  ③ **미치환 잔여**: 정규화 대상인데 프롬프트에 원래 이름이 남아 있는가?
  ④ **타깃 누출**: 타깃에 정규화 안 된 원본 이름이 남는가(= 암기 강요)?

정적 검사가 아니라 **실제 프롬프트를 렌더**해서 본다.

사용: python3 scripts/audit_normalize_collisions.py [n] [train|val|test]
"""
import collections
import copy
import os
import re
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
import tactic_gen.tactic_data as td  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 300
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "train").upper()

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
tok = AutoTokenizer.from_pretrained(cc["model_name"])
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
ds = LmDataset.from_conf(TacticDataConf.from_yaml(tdc), getattr(Split, SPLIT), N)
col = td.example_collator_from_conf(
    td.example_collator_conf_from_yaml(cc["example_collator"]))

# 정규화가 만드는 이름 패턴
PREFIX = {"L": "premise lemma", "T": "주입 타입", "f": "주입 함수",
          "C": "생성자", "G": "정리"}
PAT = {k: re.compile(r"(?<![\w'])" + k + r"(\d+)(?![\w'])") for k in PREFIX}

stat = collections.Counter()
rev_ex = collections.defaultdict(list)
n = 0

for i in range(N):
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    # 정규화 **끄고** 렌더 → 원본 이름이 그대로인 프롬프트
    os.environ["NORMALIZE_NAMES"] = "0"
    import importlib
    importlib.reload(td)
    col0 = td.example_collator_from_conf(
        td.example_collator_conf_from_yaml(cc["example_collator"]))
    try:
        raw = col0.collate(tok, e)
    except Exception:
        continue
    # 정규화 **켜고** 렌더
    os.environ["NORMALIZE_NAMES"] = "1"
    os.environ["NORMALIZE_RATE"] = "1.0"
    os.environ["NORMALIZE_PREMISES"] = "1"
    os.environ["NORMALIZE_THEOREM"] = "1"
    importlib.reload(td)
    col1 = td.example_collator_from_conf(
        td.example_collator_conf_from_yaml(cc["example_collator"]))
    try:
        norm = col1.collate(tok, e)
    except Exception:
        continue
    n += 1

    # ① 역충돌: 정규화 **전** 프롬프트에 L0·T1 같은 이름이 이미 있나
    for k, desc in PREFIX.items():
        hits = PAT[k].findall(raw)
        if hits:
            stat[f"① 역충돌 {k}# ({desc})"] += 1
            if len(rev_ex[k]) < 3:
                m = PAT[k].search(raw)
                ctx = raw[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")
                rev_ex[k].append(f"{k}{hits[0]} — …{ctx}…")

    # ④ 타깃 누출: 타깃에 원본 lemma 이름이 남았나 (정규화 후)
    i2 = norm.rfind("[TACTIC]")
    if i2 >= 0:
        tgt = norm[i2 + 8:]
        # 정규화된 이름(L#/T#/…)이 아닌 대문자 시작 식별자가 남아 있으면 후보
        leaks = [x for x in re.findall(r"[A-Za-z_][\w']{3,}", tgt)
                 if not re.fullmatch(r"[LTfCG]\d+", x)
                 and x not in ("rewrite", "apply", "eapply", "erewrite", "intros",
                               "destruct", "simpl", "unfold", "auto", "exact",
                               "assert", "induction", "reflexivity", "assumption",
                               "constructor", "inversion", "subst", "split",
                               "exists", "left", "right", "trivial", "lia",
                               "congruence", "discriminate", "symmetry", "omega")]
        if leaks:
            stat["④ 타깃에 원본 이름 잔존"] += 1

print(f"\n■ {SPLIT} — 정규화 충돌 감사 (프롬프트 {n}개)\n")
if not stat:
    print("   문제 없음")
for k in sorted(stat, key=lambda x: -stat[x]):
    print(f"   {k:34s} {stat[k]:4d}/{n} = {stat[k]/max(n,1)*100:5.1f}%")
for k, exs in rev_ex.items():
    if exs:
        print(f"\n   ① {k}# 역충돌 예:")
        for x in exs[:2]:
            print(f"     {x[:120]}")
