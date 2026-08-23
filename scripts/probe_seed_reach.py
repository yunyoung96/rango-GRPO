#!/usr/bin/env python3
"""★ 결정적 질문 — **안 보이는 이름이 애초에 씨앗으로 닿을 수 있나.**

주입 확장도, 개수 상한 해제도, 예산 상향(300→600)도 환각률을 17.6% 에서 못 내렸다.
가설: **그 이름들이 어떤 씨앗 출처에도 안 나온다.**

씨앗은 정답과 무관한 곳에서만 온다 — goal · 가설 · 검색된 premise · 증명 스크립트.
그런데 결손 이름은 **정답에만** 나올 수 있다. 그러면 어떤 주입으로도 못 닿는다.
그게 사실이면 (b) 는 원리적으로 한계가 있고, 남는 선택지는 (a) 제외뿐이다.

각 결손 이름마다 판정한다:
    ① goal/가설에 나오나
    ② 검색된 premise **본문**에 나오나 (프롬프트에 담긴 것 말고 100개 전부)
    ③ 증명 스크립트에 나오나
    ④ [PROOFS](유사 증명) 본문에 나오나
    ⑤ 어디에도 없나                    ← 주입 불가 · 원리적 한계

사용: PYTHONPATH=src python3 scripts/probe_seed_reach.py [표본수]
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
import rango_defaults as _D
sys.path.insert(0, "scripts")
logging.disable(logging.CRITICAL)
from _env_from_v9 import apply_v9_env  # noqa: E402
apply_v9_env(verbose=True)
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer)
from tactic_gen.normalize_names import introduced_names  # noqa: E402
from _coq_vocab import is_core  # noqa: E402
try:
    STDLIB = set(json.load(open("data/stdlib_names.json")))
except Exception:
    STDLIB = set()
FD = json.load(open(os.environ.get("FUNC_DEFS_PATH", "data/func_defs_v3.json")))


def _strip_comments(t: str) -> str:
    """Coq 주석 `(* … *)` 를 지운다 — 주석 안 낱말은 **이름이 아니다**.

    실측 오탐: `(* Caso Indutivo *)` 의 Indutivo,
    `(* move both quantifiers into the context: *)` 의 quantifiers,
    `(* We choose a preimage by [grp_quotient_map]. *)` 의 preimage·merely
    를 전부 "프롬프트에 없는 이름" 으로 신고했다. 중첩 주석까지 처리한다.
    """
    out, depth, i = [], 0, 0
    while i < len(t):
        if t.startswith("(*", i):
            depth += 1; i += 2; continue
        if t.startswith("*)", i) and depth:
            depth -= 1; i += 2; continue
        if not depth:
            out.append(t[i])
        i += 1
    return "".join(out)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = "/tmp/seedreach-cache"
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
HARD = _D.num("HARD_SEQ_LEN")
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)

st = collections.Counter()
ex = []
random.seed(4)
tried = 0
while st["예제"] < N and tried < N * 25:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        e = ds.resolved_example(i)
        full = coll.collate(tok, e)
    except RuntimeError as _re:
        sys.stderr.write(f"\n★★ 중단: {str(_re)[:300]}\n"); sys.exit(3)
    except Exception:
        continue
    if "[TACTIC]" not in full:
        continue
    st["예제"] += 1
    prompt, target = full.rsplit("[TACTIC]", 1)
    ids = tok(full, add_special_tokens=False)["input_ids"]
    vis = tok.decode(ids[max(0, len(ids) - HARD):], skip_special_tokens=True)
    vp = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis

    state = getattr(e, "proof_state", "") or ""
    script = getattr(e, "proof_script", "") or ""
    prem_all = " ".join((p if isinstance(p, str) else str(p))
                        for p in (getattr(e, "premises", None) or []))
    proofs_all = " ".join((p if isinstance(p, str) else str(p))
                          for p in (getattr(e, "proofs", None) or []))
    local = set()
    m = re.search(r"\[STATE\]\n(.*?)(?=\n\[[A-Z]+\]|\Z)", prompt, re.S)
    if m:
        for ln in m.group(1).split("\n"):
            mm = re.match(r"^([A-Za-z_][\w', ]*?)\s*:", ln)
            if mm:
                local |= {x.strip() for x in mm.group(1).split(",") if x.strip()}
    try:
        intro = introduced_names(target)
    except Exception:
        intro = set()
    _tgt = _strip_comments(target)          # ★ 주석 제거 후 판정
    first = re.match(r"^\s*([A-Za-z_][\w']*)", _tgt.strip())
    tacname = first.group(1) if first else None

    miss = []
    for w in dict.fromkeys(re.findall(
            r"(?<![\w'.])([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)", _tgt)):
        base = w.split(".")[-1]
        if (is_core(w) or base in local or w in local or base in intro or w in intro
                or w == tacname or len(base) < 3
                or base in STDLIB or w in STDLIB):
            continue
        if re.search(r"(?<![\w'])" + re.escape(base) + r"(?![\w'])", vp):
            continue
        miss.append(w)
    if not miss:
        continue
    st["★ 결손 있는 예제"] += 1
    for w in miss:
        b = w.split(".")[-1]
        pat = re.compile(r"(?<![\w'])" + re.escape(b) + r"(?![\w'])")
        st["결손 이름"] += 1
        srcs = []
        if pat.search(state):
            srcs.append("goal/가설")
        if pat.search(prem_all):
            srcs.append("premise본문")
        if pat.search(script):
            srcs.append("스크립트")
        if pat.search(proofs_all):
            srcs.append("PROOFS본문")
        if srcs:
            st[f"  ✓ 씨앗으로 닿음: {'+'.join(srcs[:2])}"] += 1
            st["  ✓ 닿음(합계)"] += 1
            st["    └ func_defs 에 있음" if b in FD else "    └ func_defs 에 없음"] += 1
        else:
            st["★★ 어디에도 없음 — 주입 불가"] += 1
            if len(ex) < 10:
                ex.append(f"{w:26s} ← {target.strip()[:56]}")
    if st["예제"] % 100 == 0:
        print(f"   … {st['예제']}/{N}", flush=True)

print(f"\n■ 결과 (예제 {st['예제']})\n")
for k in sorted(st):
    print(f"   {k:44s} {st[k]:6d}")
M = max(st["결손 이름"], 1)
print(f"\n   ★★ **주입으로 닿을 수 없는 비율** "
      f"{st['★★ 어디에도 없음 — 주입 불가']}/{st['결손 이름']} "
      f"= {st['★★ 어디에도 없음 — 주입 불가']/M*100:.1f}%")
print(f"   ✓ 씨앗으로 닿는 비율 {st['  ✓ 닿음(합계)']/M*100:.1f}% "
      f"— 이 몫만 주입으로 고칠 수 있다")
if ex:
    print("\n   ■ 어디에도 없는 예")
    for x in ex:
        print(f"     {x}")
