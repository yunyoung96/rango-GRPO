#!/usr/bin/env python3
"""★ **추론 정규화 왕복 실험** — 익명화해서 넣고, 생성물을 되돌려 Coq 에 넣는 것이 되는가.

추론은 프롬프트를 `L0`·`T3`·`K1` 로 익명화해 넣는다. 모델은 그 이름으로 답한다.
그런데 Coq 은 `L0` 를 모른다 — 실행 전에 **되돌려야** 한다. 그게 무결한지 잰다.

## 설계

모델이 아직 제대로 못 만들므로 **완벽한 모델의 출력을 시뮬레이션**한다.
익명화된 프롬프트를 읽은 완벽한 모델은 gold 를 그 이름으로 쓸 것이다:

    gold_anon = apply_mapping(gold, m)      ← 완벽한 모델의 출력
    back      = apply_inverse(gold_anon, m) ← 우리가 Coq 에 넣는 것
    back == gold 여야 한다.

## 재는 것

  1단계 (Coq 없이 · 대규모)
      익명화 발생   gold 가 실제로 바뀌었나 (안 바뀌면 시험이 공허하다)
      왕복 정확     back == gold  (바이트 동일)
      단사          매핑값에 중복이 없는가 (있으면 역이 정의되지 않는다)
      ★ 충돌        매핑값이 **원본 프롬프트에 이미 있는 다른 이름**과 겹치는가
                    — 실제 Coq 이름이 `T0`·`f0` 처럼 익명 토큰과 똑같이 생겼다
                      (실측: goal 40건 중 3건에 그런 이름이 있었다)

  2단계 (Coq · 소규모 · **대조군 포함**)
      원본 파일 끝에 탐침을 붙여 이름이 풀리는지 본다
          Check <원래이름>.   → 통과해야 한다 (되돌린 것이 맞다)
          Check <익명이름>.   → **실패해야 한다** (되돌리지 않으면 Coq 이 거부한다)
      둘 다 확인해야 "되돌리는 것이 **필요하다**" 가 증명된다.

사용: PYTHONPATH=src python3 scripts/exp_normalize_roundtrip.py [1단계표본] [2단계표본]
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
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")
os.environ["CUT_DROP_HOPELESS"] = "0"
os.environ["DROP_HALLUC"] = "0"

N1 = int(sys.argv[1]) if len(sys.argv) > 1 else 800
N2 = int(sys.argv[2]) if len(sys.argv) > 2 else 24

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
REPOS = Path("/tmp/coq-dataset/repos")

st = collections.Counter()
bad = []
cands = []          # 2단계 후보 (파일, 원래이름, 익명이름)
random.seed(2024)
tried = 0
print(f"■ 1단계 — 왕복 정확성 (TEST {N1} 예제)\n", flush=True)
while st["예제"] < N1 and tried < N1 * 40:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        ex = ds.resolved_example(i)
        p_on = coll.collate_input(tok, ex, normalize=True)
        m = last_inference_mapping()
        p_off = coll.collate_input(tok, ex, normalize=False)
    except Exception:
        continue
    st["예제"] += 1
    if not m:
        st["  매핑 없음"] += 1
        continue
    st["  매핑 있음"] += 1
    # 단사
    if len(set(m.values())) != len(m):
        st["★ 매핑이 단사가 아님"] += 1
    # ★ 충돌 — 매핑값이 **원본**(정규화 전) 텍스트에 이미 다른 이름으로 있는가
    for orig, val in m.items():
        if re.search(r"(?<![\w'])" + re.escape(val) + r"(?![\w'])", p_off):
            st["★ 충돌: 매핑값이 원본에 이미 있음"] += 1
            if len(bad) < 5:
                bad.append(("충돌", orig, val))
            break
    gold = (ex.next_steps[0] if getattr(ex, "next_steps", None) else "").strip()
    if not gold:
        continue
    anon = apply_mapping(gold, m)
    back = apply_inverse(anon, m)
    if anon == gold:
        st["  gold 가 안 바뀜(시험 공허)"] += 1
        continue
    st["★★ gold 가 익명화됨"] += 1
    if back == gold:
        st["  ✓ 왕복 정확"] += 1
        # 2단계 후보: gold 에 실제로 쓰인 매핑 이름
        for orig, val in m.items():
            if re.search(r"(?<![\w'])" + re.escape(val) + r"(?![\w'])", anon) and \
                    re.search(r"(?<![\w'])" + re.escape(orig) + r"(?![\w'])", gold):
                cands.append((getattr(ex, "file_name", ""), orig, val))
                break
    else:
        st["  ✗ 왕복 실패"] += 1
        if len(bad) < 5:
            bad.append(("왕복", gold[:60], back[:60]))
    if st["예제"] % 200 == 0:
        print(f"   … {st['예제']}/{N1}", flush=True)

E = max(st["예제"], 1)
for k in sorted(st):
    print(f"   {k:34s} {st[k]:5d}")
G = max(st["★★ gold 가 익명화됨"], 1)
print(f"\n   왕복 정확률  {st['  ✓ 왕복 정확']}/{st['★★ gold 가 익명화됨']} "
      f"= {st['  ✓ 왕복 정확']/G*100:.1f}%")
for t, a, b in bad:
    print(f"     [{t}] {a!r} ↔ {b!r}")

# ── 2단계 — Coq 실행 (대조군 포함) ──────────────────────────────────────────
print(f"\n■ 2단계 — Coq 이름 해석 (대조군 포함 · 후보 {len(cands)}건 중 {N2}건)\n",
      flush=True)
from coqpyt.coq.base_file import CoqFile  # noqa: E402

c2 = collections.Counter()
seen = set()
for fn, orig, val in cands:
    if c2["검증"] >= N2:
        break
    if (fn, orig) in seen:
        continue
    seen.add((fn, orig))
    rel = fn.replace("repos/", "", 1)
    p = REPOS / rel
    if not p.exists():
        c2["소스 없음"] += 1
        continue
    src = p.read_text(errors="ignore")
    ws = REPOS / Path(rel).parts[0]
    res = {}
    for tag, name in (("원래이름", orig), ("익명이름", val)):
        bak = p.parent / (p.name + ".rtbak")
        try:
            p.rename(bak)
            p.write_text(src + f"\nCheck {name}.\n")
            cf = CoqFile(str(p), timeout=120, workspace=str(ws))
            cf.run()
            errs = [getattr(x, "message", "") for x in cf.errors]
            cf.close()
        except Exception as ex_:
            errs = [f"예외 {type(ex_).__name__}"]
        finally:
            p.unlink(missing_ok=True)
            if bak.exists():
                bak.rename(p)
        res[tag] = errs
    c2["검증"] += 1
    ok_orig = not res["원래이름"]
    ok_anon = not res["익명이름"]
    if ok_orig and not ok_anon:
        c2["✅ 원래이름 통과 · 익명이름 거부 (기대대로)"] += 1
    elif ok_orig and ok_anon:
        c2["★ 둘 다 통과 (익명이름이 우연히 존재)"] += 1
    elif not ok_orig:
        c2["★ 원래이름이 안 풀림"] += 1
        if c2["★ 원래이름이 안 풀림"] <= 2:
            print(f"     ✗ {orig} @ {rel[:50]} : "
                  f"{' '.join(res['원래이름'][0].split())[:70]}", flush=True)
    if c2["검증"] % 5 == 0:
        print(f"   … {c2['검증']}/{N2}", flush=True)

print()
for k in sorted(c2, key=lambda x: -c2[x]):
    print(f"   {k:44s} {c2[k]}")
n2 = max(c2["검증"], 1)
print(f"\n   ✅ 기대대로 {c2['✅ 원래이름 통과 · 익명이름 거부 (기대대로)']}/{n2} "
      f"= {c2['✅ 원래이름 통과 · 익명이름 거부 (기대대로)']/n2*100:.1f}%")
