#!/usr/bin/env python3
"""★ 추론 정규화 왕복의 **Coq 확인** — 되돌리는 것이 필요하고 또 맞는가.

1단계(`exp_normalize_roundtrip.py`)는 문자열 왕복만 봤다. 여기서는 **실제 Coq** 에
물어 두 가지를 동시에 본다 — 대조군이 있어야 "필요하다"가 증명된다.

    Locate <원래이름>.   → 찾아야 한다   (되돌린 것이 Coq 에서 실제로 풀린다)
    Locate <익명이름>.   → **못 찾아야** 한다 (되돌리지 않으면 Coq 이 거부한다)

대상은 CompCert(held-out) 다 — 소스와 .vo 가 `raw-data/coqstoq-test/repos/compcert`
에 빌드되어 있다. 증명이 있던 **그 파일의 모듈을 Require** 한 뒤 이름을 조회한다.

※ 근사 하나: 파일 전체를 Require 하므로 그 파일의 **뒤쪽** 정의도 보인다.
  증명 시점보다 넓게 보는 것이라, 판정이 "찾음" 쪽으로 관대하다.

사용: PYTHONPATH=src python3 scripts/exp_normalize_coq.py [사례수]
"""
import collections
import copy
import logging
import os
import random
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUT_DROP_HOPELESS"] = "0"
os.environ["DROP_HALLUC"] = "0"

N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
CC = Path("raw-data/coqstoq-test/repos/compcert").resolve()
FLAGS = CC.joinpath("_CoqProject").read_text().split()

# _CoqProject 의 `-R <dir> <logical>` 로 경로 → 논리이름
RMAP = {}
i = 0
while i < len(FLAGS) - 2:
    if FLAGS[i] == "-R":
        RMAP[FLAGS[i + 1]] = FLAGS[i + 2]
        i += 3
    else:
        i += 1


def logical_name(rel: str):
    """`lib/Integers.v` → `compcert.lib.Integers`"""
    for d, lg in RMAP.items():
        if rel.startswith(d + "/"):
            rest = rel[len(d) + 1:].removesuffix(".v").replace("/", ".")
            return f"{lg}.{rest}"
    return None


def locate(mod: str, name: str, ltac: bool = False) -> bool:
    """그 모듈 문맥에서 이름이 풀리는가.

    ★ **Ltac 이름은 `Locate` 로 못 찾는다** — Ltac 은 term/notation 네임스페이스에
      없어서, 되돌리기가 맞았어도 `No object of basename` 이 나온다.
      실측: 실패 3건이 전부 `_K#` (TransfInstr · TrivialExists · mydestr) 였다.
      `Print Ltac <name>.` 으로 물어야 판정이 옳다.
    """
    q = f"Print Ltac {name}." if ltac else f"Locate {name}."
    src = f"Require Import {mod}.\n{q}\n"
    p = Path("/tmp/_loc_probe.v")
    p.write_text(src)
    try:
        r = subprocess.run(["coqc"] + FLAGS + [str(p)], cwd=CC,
                           capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        return None
    out = (r.stdout or "") + (r.stderr or "")
    if "No object of basename" in out or "is not a user defined tactic" in out:
        return False
    if "Error" in out:
        return None                       # 판정 불가(모듈 Require 실패 등)
    return True


import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer,
                                    last_inference_mapping)
from tactic_gen.normalize_names import apply_mapping, apply_inverse  # noqa: E402

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", "/tmp/roundtrip")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TEST, None)
coll = example_collator_from_conf(conf.collator_conf)
TOTAL = ds.shuffled_idx.split_length(Split.TEST)

print(f"■ CompCert 사례 수집 (목표 {N}건)\n", flush=True)
cases = []
random.seed(2025)
tried = 0
while len(cases) < N and tried < 40000:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        ex = ds.resolved_example(i)
    except Exception:
        continue
    fn = getattr(ex, "file_name", "") or ""
    if "AbsInt-CompCert" not in fn:
        continue
    rel = fn.split("AbsInt-CompCert/", 1)[-1]
    mod = logical_name(rel)
    if not mod:
        continue
    try:
        coll.collate_input(tok, ex, normalize=True)
        m = last_inference_mapping()
    except Exception:
        continue
    gold = (ex.next_steps[0] if getattr(ex, "next_steps", None) else "").strip()
    if not m or not gold:
        continue
    anon = apply_mapping(gold, m)
    if anon == gold:
        continue
    for orig, val in m.items():
        if re.search(r"(?<![\w'])" + re.escape(orig) + r"(?![\w'])", gold) and \
                re.search(r"(?<![\w'])" + re.escape(val) + r"(?![\w'])", anon):
            cases.append((rel, mod, orig, val, gold, apply_inverse(anon, m) == gold))
            break
    if len(cases) % 5 == 0 and cases:
        print(f"   … 수집 {len(cases)} (시도 {tried})", flush=True)

print(f"\n■ Coq 확인 ({len(cases)}건)\n", flush=True)
st = collections.Counter()
for rel, mod, orig, val, gold, rt in cases:
    # ★ 익명 이름의 접두사가 그 이름의 **종류**를 말해 준다 — _K# 는 Ltac.
    _is_ltac = bool(re.match(r"_K\d+$", val or ""))
    a = locate(mod, orig, ltac=_is_ltac)
    b = locate(mod, val, ltac=_is_ltac)
    st["검증"] += 1
    st["문자열 왕복 정확"] += bool(rt)
    if a is None or b is None:
        st["판정 불가(Require 실패 등)"] += 1
        continue
    if a and not b:
        st["✅ 원래이름 찾음 · 익명이름 없음 (기대대로)"] += 1
    elif a and b:
        st["★ 익명이름도 존재(우연 충돌)"] += 1
    elif not a:
        st["★ 원래이름을 못 찾음"] += 1
        # ★ 상한을 두지 않는다 — 3건에서 자르면 "나머지는 다른 원인" 인지
        #   "전부 같은 원인" 인지 구분이 안 된다(실제로 전부 Ltac 이었다).
        print(f"     \u2717 {orig} ({val}) @ {mod}", flush=True)
    if st["검증"] % 5 == 0:
        print(f"   … {st['검증']}/{len(cases)}", flush=True)

print()
for k in sorted(st, key=lambda x: -st[x]):
    print(f"   {k:44s} {st[k]}")
n = max(st["검증"] - st["판정 불가(Require 실패 등)"], 1)
print(f"\n   ✅ 기대대로 {st['✅ 원래이름 찾음 · 익명이름 없음 (기대대로)']}/{n} "
      f"= {st['✅ 원래이름 찾음 · 익명이름 없음 (기대대로)']/n*100:.1f}%")
