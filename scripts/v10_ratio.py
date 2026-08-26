#!/usr/bin/env python3
"""외부 lemma 참조가 있는 스텝에서 **gold 가 검색되나** — 비율만 잰다. GPU 불필요.

`v10_dryrun.py` 는 주입 후 검증까지 하지만, 여기서는 **주입 전 상태**만 본다:

  스텝 단위   전부 보임 / 일부만 보임 / 하나도 안 보임
  lemma 단위  보임 / 안 보임          (스텝당 lemma 개수가 다르므로 따로 센다)

★ 판정은 **절단 후 프롬프트**로 한다. `example.premises` 100개 중 프롬프트에 실제로
  담기는 것은 20~40개다. 전부로 재면 "보인다" 고 낙관한다(build_cuts 가 당한 버그).

사용: VR_N=1000 VR_SHARD/VR_NSHARD python3 scripts/v10_ratio.py [conf]
"""
import collections, os, re, sys, yaml, logging
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["V10_PREMISE_INJECT"] = "0"      # ★ 주입 **전** 상태를 재는 것이 목적
sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
import rango_defaults as _D
from tactic_gen.tactic_data import LmDataset, TacticDataConf
from tactic_gen import v10_inject as V10
from data_management.splits import Split

CONF = yaml.safe_load(open(sys.argv[1] if len(sys.argv) > 1 else "all_log/ft_qwen3b_v10_conf.yaml"))
N = int(os.environ.get("VR_N", "600"))
SHARD = int(os.environ.get("VR_SHARD", "0"))
NSHARD = int(os.environ.get("VR_NSHARD", "1"))
SPLIT = getattr(Split, os.environ.get("VR_SPLIT", "TRAIN"))
td = TacticDataConf.from_yaml(CONF["tactic_data"])
ds = LmDataset.from_conf(td, SPLIT)
tok, col = ds.tokenizer, ds.example_collator
print(f"■ {SPLIT.name} · 표본 {N} · 샤드 {SHARD}/{NSHARD}", flush=True)

S = collections.Counter()
per_lemma_missing = collections.Counter()
step = max(1, len(ds) // N)
idxs = [i for j, i in enumerate(range(0, min(len(ds), N * step), step)) if j % NSHARD == SHARD]
for c, i in enumerate(idxs):
    try:
        ex = ds.raw_example(i)
        lems = V10.plan_lemmas(ex) or []
        if not lems:
            S["외부참조 없음"] += 1
            continue
        # ★★ `collate()` 로 재면 안 된다 — NORMALIZE_NAMES 가 이름을 `_L0` 로 바꾸므로
        #   원래 이름으로 찾으면 **항상 실패**한다. 프로덕션의 가시성 판정
        #   `v10_inject.visible()` 을 그대로 쓴다(정규화 전 프롬프트 + 하드 절단 재현).
        ok = [nm for nm, _ in lems if V10.visible(col, tok, ex, nm)]
    except Exception:
        S["오류"] += 1
        continue
    S["외부참조 있음"] += 1
    S["lemma 총"] += len(lems)
    S["lemma 검색됨"] += len(ok)
    if len(ok) == len(lems):
        S["스텝: 전부 보임"] += 1
    elif ok:
        S["스텝: 일부만 보임"] += 1
    else:
        S["스텝: 하나도 안 보임"] += 1
    for nm, _ in lems:
        if nm not in ok:
            per_lemma_missing[("한정이름" if "." in nm else "맨이름")] += 1
    S[f"lemma개수 {min(len(lems),4)}"] += 1
    if (c + 1) % 100 == 0:
        print(f"   … {c+1}/{len(idxs)}", flush=True)

tot = S["외부참조 있음"] + S["외부참조 없음"]
print(f"\n■ 전체 {tot} 스텝")
print(f"   외부 lemma 참조 없음   {S['외부참조 없음']:5d}  {S['외부참조 없음']/max(tot,1)*100:5.1f}%")
print(f"   외부 lemma 참조 있음   {S['외부참조 있음']:5d}  {S['외부참조 있음']/max(tot,1)*100:5.1f}%")
e = max(S["외부참조 있음"], 1)
print(f"\n■ ★ 외부 참조가 있는 {S['외부참조 있음']} 스텝 안에서")
for k in ("스텝: 전부 보임", "스텝: 일부만 보임", "스텝: 하나도 안 보임"):
    print(f"   {k:20s} {S[k]:5d}  {S[k]/e*100:5.1f}%")
print(f"   → 검색됨 {S['스텝: 전부 보임']/e*100:.1f}%  ·  "
      f"뭔가 빠짐 {(S['스텝: 일부만 보임']+S['스텝: 하나도 안 보임'])/e*100:.1f}%")
L = max(S["lemma 총"], 1)
print(f"\n■ lemma 단위 (총 {S['lemma 총']}개, 스텝당 {S['lemma 총']/e:.2f}개)")
print(f"   검색됨    {S['lemma 검색됨']:5d}  {S['lemma 검색됨']/L*100:5.1f}%")
print(f"   안 됨     {L-S['lemma 검색됨']:5d}  {(L-S['lemma 검색됨'])/L*100:5.1f}%")
if per_lemma_missing:
    print(f"   못 찾은 것의 형태: {dict(per_lemma_missing)}")
print(f"\n■ 스텝당 lemma 개수 분포")
for k in range(1, 5):
    v = S[f"lemma개수 {k}"]
    if v:
        print(f"   {k}{'+' if k == 4 else ''}개  {v:5d}  {v/e*100:5.1f}%")
if S["오류"]:
    print(f"\n(오류 {S['오류']})")
