#!/usr/bin/env python3
"""★ `U1` 전용 검사 — **cut 이 적용된 예제만** 모아 `exact L` 의 L 이 프롬프트에 있는지 본다.

## 왜 따로 만드나

`scan_prompts.py` 는 무작위 예제를 훑으므로 cut 비율(12%)만큼만 cut 을 본다 —
300건을 훑어야 cut 14건이고, 그 14건으로 "U1 이 사라졌다"고 말할 수는 없다.
여기서는 계획 파일에서 **cut 인 인덱스만 골라** 그것만 프롬프트를 짓는다.
같은 시간에 cut 표본이 20배 이상 늘어난다.

## 무엇을 보나

cut 은 `assert (P) as H. { exact L. }` 이고, 하위스텝으로 쪼개면 `close` 스텝이
`{ exact L. }` 만 정답으로 갖는다. 그 스텝은 **P 를 goal 로 삼아 검색을 다시 돌리므로**
L 이 프롬프트에 들어와야 한다 — 그게 하위스텝 설계의 존재 이유다.
안 들어오면 모델에게 "안 보이는 이름을 쓰라"고 가르치는 것이고, 그게 U1 이다.

  U1  ★ exact 의 대상이 프롬프트에 없다      ← 치명
  U1b   정규화 이름(L#/T#)으로 들어와 있다     ← 정상(같은 것을 가리킨다)
  U2  ★ 괄호 불일치
  U3  ★ H_asrt 이름이 이미 STATE 에 있다

사용: PYTHONPATH=src python3 scripts/verify_u1.py [cut 표본수]
"""
import collections
import copy
import json
import logging
import os
import random
import re
import sys

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
# ★ 설정의 출처는 `all_log/v9_env.sh` **하나**다. 여기에 값을 다시 적으면 반드시
#   어긋나고, 어긋나도 오류가 안 난다 — 조용히 다른 실험을 재게 된다(실제로 겪었다:
#   옛 CUTS_PATH 로 U1 을 재고, structural 로 "학습과 같은 설정" 감사를 돌렸다).
sys.path.insert(0, "scripts")
from _env_from_v9 import apply_v9_env  # noqa: E402
apply_v9_env(verbose=True)
# ★ 표본 측정은 **요청된 예제만** 만든다. 캐시는 파일(페이지) 단위라 미스 한 번이
#   그 파일의 모든 proof×step 을 짓는데, 표본은 파일당 한두 건만 쓰므로 순 낭비다.
#   실측: 페이지 빌드 경로 7분에 27건 → 요청 예제만 만들면 56초에 50건.
#   (학습은 한 파일을 여러 번 쓰므로 페이지 빌드가 이득이다 — 거기선 바꾸지 않는다.)
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer)

N_WANT = int(sys.argv[1]) if len(sys.argv) > 1 else 200
CUTS = os.environ.get("CUTS_PATH", "data/cut_plans_all.jsonl")

# ── 계획 파일에서 cut 인 sid 를 모은다 ────────────────────────────────────
#   sid 는 `repos/proj/a/b.v:pi:si` 인데 StepID.file 은 `proj-a-b.v` 다.
#   두 표현을 잇는다(옛 검증 스크립트가 이걸 안 해서 "질의 0건인데 통과" 를 냈다).
plan_key = set()
for ln in open(CUTS):
    try:
        d = json.loads(ln)
    except Exception:
        continue
    if d.get("kind") == "plan" and d.get("cut"):
        sid = d["sid"]
        m = re.match(r"^(.*\.v):(\d+):(\d+)$", sid)
        if m:
            dashed = m.group(1).split("repos/", 1)[-1].replace("/", "-")
            plan_key.add((dashed, int(m.group(2)), int(m.group(3))))
print(f"■ 계획 cut {len(plan_key):,}건  ({CUTS})", flush=True)

CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v9_conf.yaml")
cc = yaml.safe_load(open(CONF))
_td = copy.deepcopy(cc["tactic_data"])
# ★ 측정 스크립트는 **전용 캐시**를 쓴다. 학습 캐시를 같이 쓰면 두 가지가 깨진다:
#   ① 코드를 고친 뒤 옛 프로세스가 남아 있으면 옛 내용을 새 스탬프 아래에 써 넣는다
#      (실제로 겪었다 — 캐시를 지운 직후 옛 코드 프로세스가 계속 쓰고 있었다).
#   ② 측정하려고 만든 페이지가 학습 캐시에 섞인다.
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", "/tmp/verify-u1-cache")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)

# ── cut 인 인덱스만 고른다 (프롬프트를 안 지으므로 싸다) ────────────────
random.seed(3)
picked = []
probed = 0
while len(picked) < N_WANT * 3 and probed < 2_000_000:
    i = random.randrange(TOTAL)
    probed += 1
    try:
        s = ds.shuffled_idx.get_idx(Split.TRAIN, i)
    except Exception:
        continue
    if (s.file, s.proof_idx, s.step_idx) in plan_key:
        picked.append(i)
print(f"   인덱스 {probed:,}개 훑어 cut 후보 {len(picked):,}개 "
      f"(적중률 {len(picked)/max(probed,1)*100:.2f}%)\n", flush=True)

st = collections.Counter()
bad = collections.defaultdict(list)
NORMNAME = re.compile(r"^[TfCLG]\d+$")
# ★ stdlib 은 "모델이 안다고 가정" — 환각에서 분리해 센다 (풀에서 구조적으로 빠져 있다)
try:
    STDLIB = set(json.load(open("data/stdlib_names.json")))
except Exception:
    STDLIB = set()


def note(k, s):
    st[k] += 1
    if len(bad[k]) < 5:
        bad[k].append(s[:180])


import time  # noqa: E402
t0 = time.time()
for i in picked:
    if st["cut 프롬프트"] >= N_WANT:
        break
    st["시도"] += 1
    try:
        full = coll.collate(tok, ds.resolved_example(i))
    except Exception as ex:
        note(f"E ★ 예외 {type(ex).__name__}", f"idx={i} {ex}")
        continue
    if "[TACTIC]" not in full:
        continue
    prompt, target = full.rsplit("[TACTIC]", 1)
    # ★★★ 하위스텝 종류를 **텍스트로 추측하지 않는다.** 두 번 틀렸다:
    #   ① `H_asrt` 유무로 판정 → close 의 정답은 `exact L.` 뿐이라 전부 놓쳤다
    #   ② `^\{\s*exact` 로 판정 → close 에는 **중괄호가 없다**(`exact Nadd_alt.`)
    #   학습이 쓰는 것과 **같은 함수**(`_substep_plan`)에 물어 pick 을 그대로 읽는다.
    #   cut 은 런타임에 "안 보이는 lemma" 만으로 다시 조립되므로 계획 파일만으로는
    #   pick 을 계산할 수 없다 — 데이터셋에 물어야 한다.
    tg = target.strip()
    kind = None
    try:
        _raw = ds.raw_example(i)
        _sp = ds._substep_plan(_raw, i)
        if _sp:
            kind = _sp["subs"][_sp["pick"]][1]          # assert | close | final
    except Exception as ex:
        note(f"P ★ _substep_plan 예외 {type(ex).__name__}", f"idx={i} {ex}")
    if kind is None:
        # 하위스텝이 없다 = cut 미적용(gold 가 전부 보였다) 이거나 통짜
        if "H_asrt" in target:
            st["  통짜 cut (쪼개지 않음)"] += 1
            st["cut 프롬프트"] += 1
        else:
            st["계획은 있으나 cut 미적용(gold 가 보였다)"] += 1
            continue
    else:
        st["cut 프롬프트"] += 1
        st[f"  하위스텝 {kind}" + ("  ← exact 가 여기 산다" if kind == "close" else "")] += 1

    if target.count("(") != target.count(")"):
        note("U2 ★ cut 괄호 불일치", f"idx={i} {tg[:90]}")

    for m in re.finditer(r"exact\s+@?([\w'.]+?)\s*[.)]", target):
        nm = m.group(1)
        base = nm.split(".")[-1]
        st["exact 대상"] += 1
        if re.search(r"(?<![\w'])" + re.escape(base) + r"(?![\w'])", prompt):
            st["  ✓ 프롬프트에 있다"] += 1
        elif base in STDLIB:
            st["  ○ stdlib (안다고 가정)"] += 1
        elif NORMNAME.match(base):
            # 정규화 이름인데 프롬프트에 없다 = 진짜 문제 (이름이 어디에도 안 뜬다)
            note("U1 ★ exact 대상(정규화 이름)이 프롬프트에 없다", f"idx={i} {nm} ← {tg[:80]}")
        else:
            note("U1 ★ exact 대상이 프롬프트에 없다", f"idx={i} {nm} ← {tg[:80]}")

    body = dict(re.findall(r"\[(\w+)\]\n(.*?)(?=\n\[\w+\]|\Z)", prompt, re.S))
    for h in re.findall(r"as\s+(H_asrt\w*)", target):
        if re.search(r"(?<![\w'])" + h + r"\s*:", body.get("STATE", "")):
            note("U3 ★ H_asrt 이름 충돌", f"idx={i} {h}")

    if st["cut 프롬프트"] % 50 == 0:
        el = time.time() - t0
        print(f"   … cut {st['cut 프롬프트']}건 ({el:.0f}s)", flush=True)

print(f"\n■ 결과 (cut 프롬프트 {st['cut 프롬프트']}건 / 시도 {st['시도']}건)\n")
for k in sorted(st):
    if k in ("시도",):
        continue
    print(f"   {k:46s} {st[k]:5d}")
    for x in bad[k]:
        print(f"        {x}")

ne = max(st["exact 대상"], 1)
print(f"\n   exact 대상 가시율 {st['  ✓ 프롬프트에 있다']}/{st['exact 대상']} "
      f"= {st['  ✓ 프롬프트에 있다']/ne*100:.1f}%")
fatal = sorted(k for k in st if "★" in k)
print()
if fatal:
    print("★ 치명 항목:")
    for f in fatal:
        print(f"   · {f}  ({st[f]}건)")
    sys.exit(1)
print("✓ 치명 항목 없음")
