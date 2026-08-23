#!/usr/bin/env python3
"""★ "어디에도 없는" 결손 이름의 **전체 맥락**을 덤프한다.

`probe_seed_reach` 가 43.8% 를 "주입 불가" 로 셌는데, 그게 정말인지 눈으로 봐야 한다.
각 사례마다 다음을 전부 찍는다:

    · 정답(tactic)
    · goal / 가설
    · 그 이름이 [PREMISES]·[PROOFS]·[SCRIPT]·[TYPES]·[DEFINITIONS] 각각에 있는가
    · premise **원본 100개**·proofs **원본**에도 없는가
    · func_defs / decl_kinds 에 있는가 (있으면 '주입할 재료는 있는데 씨앗이 못 닿은' 것)
    · 파일 경로 (그 프로젝트에 선언이 있는지 짐작용)

사용: PYTHONPATH=src python3 scripts/dump_unreachable.py [표본수] [덤프개수]
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
sys.path.insert(0, "scripts")
logging.disable(logging.CRITICAL)
from _env_from_v9 import apply_v9_env  # noqa: E402
apply_v9_env(verbose=True)
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer,
                                    _strip_coq_comments)
from tactic_gen.normalize_names import introduced_names  # noqa: E402
from _coq_vocab import is_core  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
DUMP = int(sys.argv[2]) if len(sys.argv) > 2 else 15
STDLIB = set(json.load(open("data/stdlib_names.json")))
FD = json.load(open("data/func_defs_v3.json"))
KINDS = json.load(open("data/decl_kinds.json")).get("kind", {})

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = "/tmp/unreach-cache"
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
HARD = int(os.environ.get("HARD_SEQ_LEN", "2048"))
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)

st = collections.Counter()
shown = 0
random.seed(4)
tried = 0
print(f"■ TRAIN {N:,} 표본에서 '어디에도 없는' 사례 {DUMP}개 덤프\n", flush=True)
while st["예제"] < N and tried < N * 25 and shown < DUMP:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        e = ds.resolved_example(i)
        full = coll.collate(tok, e)
    except Exception:
        continue
    if "[TACTIC]" not in full:
        continue
    st["예제"] += 1
    prompt, target = full.rsplit("[TACTIC]", 1)
    ids = tok(full, add_special_tokens=False)["input_ids"]
    vis = tok.decode(ids[max(0, len(ids) - HARD):], skip_special_tokens=True)
    vp = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis
    body = dict(re.findall(r"\[(\w+)\]\n(.*?)(?=\n\[\w+\]|\Z)", vp, re.S))
    tgt = _strip_coq_comments(target)
    local = set()
    m = re.search(r"\[STATE\]\n(.*?)(?=\n\[[A-Z]+\]|\Z)", prompt, re.S)
    if m:
        for ln in m.group(1).split("\n"):
            mm = re.match(r"^([A-Za-z_][\w', ]*?)\s*:", ln)
            if mm:
                local |= {x.strip() for x in mm.group(1).split(",") if x.strip()}
    try:
        intro = introduced_names(tgt)
    except Exception:
        intro = set()
    first = re.match(r"^\s*([A-Za-z_][\w']*)", tgt.strip())
    tacname = first.group(1) if first else None
    state = getattr(e, "proof_state", "") or ""
    script = getattr(e, "proof_script", "") or ""
    prem_all = "\n".join((p if isinstance(p, str) else str(p))
                         for p in (getattr(e, "premises", None) or []))
    proofs_all = "\n".join((p if isinstance(p, str) else str(p))
                           for p in (getattr(e, "proofs", None) or []))
    for w in dict.fromkeys(re.findall(
            r"(?<![\w'.])([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)", tgt)):
        base = w.split(".")[-1]
        if (is_core(w) or base in local or w in local or base in intro or w in intro
                or w == tacname or len(base) < 3
                or base in STDLIB or w in STDLIB):
            continue
        pat = re.compile(r"(?<![\w'])" + re.escape(base) + r"(?![\w'])")
        if pat.search(vp):
            continue
        st["결손"] += 1
        srcs = [nm for nm, txt in (("goal/가설", state), ("premise원본", prem_all),
                                   ("스크립트", script), ("PROOFS원본", proofs_all))
                if pat.search(txt)]
        if srcs:
            st["  씨앗으로 닿음"] += 1
            continue
        st["★ 어디에도 없음"] += 1
        if shown >= DUMP:
            continue
        shown += 1
        cands = FD.get(base)
        print("─" * 96)
        print(f"[{shown}] idx={i}   이름 = {w}   종류 = {KINDS.get(base, '미상')}")
        print(f"   파일   {getattr(e, 'file_name', '?')}")
        print(f"   정답   {target.strip()[:150]}")
        gl = state.split("\n\n")[-1] if "\n\n" in state else state
        print(f"   goal   {gl.strip()[:150]}")
        hy = state.split("\n\n")[0] if "\n\n" in state else ""
        print(f"   가설   {hy.strip()[:120] if hy.strip() else '(없음)'}")
        print(f"   섹션별 존재:  " + " · ".join(
            f"{k}={'O' if pat.search(body.get(k, '')) else 'X'}"
            for k in ("PREMISES", "PROOFS", "SCRIPT", "TYPES", "DEFINITIONS", "LTAC")))
        print(f"   원본에도 없음: premise {len(getattr(e,'premises',None) or [])}개 · "
              f"proofs {len(getattr(e,'proofs',None) or [])}개")
        print(f"   func_defs: {('후보 ' + str(len(cands)) + '개') if isinstance(cands, dict) else ('있음' if cands else '없음')}"
              f"   → {'주입 재료는 있다(씨앗이 못 닿았을 뿐)' if cands else '인덱스에도 없다'}")
    if st["예제"] % 500 == 0:
        print(f"   … {st['예제']}/{N} · 결손 {st['결손']} · 어디에도없음 {st['★ 어디에도 없음']}",
              flush=True)

print("\n" + "=" * 96)
for k in sorted(st):
    print(f"   {k:28s} {st[k]:6d}")
