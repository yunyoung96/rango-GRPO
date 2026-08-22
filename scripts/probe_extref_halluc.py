#!/usr/bin/env python3
"""★ **외부 이름을 쓰는 정답** 중 환각이 몇 %인가 — 올바른 분모로.

`scan_prompts` 의 `L6 11.50%` 는 **전체 예제** 기준이다. "외부 참조를 쓰는 tactic 중
몇 %가 환각인가" 를 알려면 분모를 그것으로 바꿔야 한다.

분류(정답이 쓰는 이름마다):
    ① tactic 키워드 / Coq 기본 어휘        → 외부 참조 아님
    ② [STATE] 의 가설·바인더 이름          → 지역 이름. 외부 참조 아님
    ③ 이 tactic 이 **도입하는** 이름        → 외부 참조 아님 (introduced_names)
    ④ 나머지 = **외부 참조**                → 보이나 안 보이나를 센다

그리고 안 보이는 것을 `decl_kinds` 로 종류별로 나눈다 —
Lemma/Axiom 은 cut 으로, Definition/Constructor 는 주입으로, 나머지는 제외로 간다.

사용: PYTHONPATH=src python3 scripts/probe_extref_halluc.py [표본수]
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
                                    example_collator_from_conf, get_tokenizer)
from tactic_gen.normalize_names import introduced_names  # noqa: E402
from _coq_vocab import is_core  # noqa: E402

# ★ stdlib 선언 이름 — "모델이 안다고 가정" 대상.
#   rango 의 PremiseFilter 가 lib/coq/theories 를 풀에서 통째로 빼므로 stdlib 은
#   **검색으로 도달 불가**다. 그런데 파일 하나에 stdlib premise 가 11,196개씩
#   딸려 오므로 전부 보여 줄 수도 없다. 그래서 환각 집계에서 분리해 센다.
try:
    STDLIB = set(json.load(open("data/stdlib_names.json")))
except Exception:
    STDLIB = set()


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
_dk = json.load(open("data/decl_kinds.json"))
KINDS = _dk.get("kind", {})

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", "/tmp/extref-cache")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
HARD = int(os.environ.get("HARD_SEQ_LEN", "2048"))
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)

st = collections.Counter()
tac_kind = collections.defaultdict(collections.Counter)
kind_miss = collections.Counter()
kind_seen = collections.Counter()
unk = []
random.seed(4)
import time  # noqa: E402
t0 = time.time()
tried = 0
while st["예제"] < N and tried < N * 40:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        full = coll.collate(tok, ds.resolved_example(i))
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

    # ② [STATE] 의 지역 이름
    local = set()
    m = re.search(r"\[STATE\]\n(.*?)(?=\n\[[A-Z]+\]|\Z)", prompt, re.S)
    if m:
        for ln in m.group(1).split("\n"):
            mm = re.match(r"^([A-Za-z_][\w', ]*?)\s*:", ln)
            if mm:
                local |= {x.strip() for x in mm.group(1).split(",") if x.strip()}
    # ③ 이 tactic 이 도입하는 이름
    try:
        intro = introduced_names(target)
    except Exception:
        intro = set()

    # ★ 정답의 **첫 토큰**은 tactic 이름이다 — 프로젝트 정의 Ltac(srapply·eqapply 등)도
    #   여기 온다. 이름이 아니라 문법이므로 외부 참조에서 뺀다. 다만 그 자체가
    #   "볼 수 없는 Ltac" 문제이긴 하므로 **따로 센다.**
    _tgt = _strip_comments(target)          # ★ 주석 제거 후 판정
    _first = re.match(r"^\s*([A-Za-z_][\w']*)", _tgt.strip())
    _tacname = _first.group(1) if _first else None
    if _tacname and not is_core(_tacname):
        st["  (참고) 정답 첫 토큰이 비표준 tactic"] += 1
        if not re.search(r"(?<![\w'])" + re.escape(_tacname) + r"(?![\w'])", vp):
            st["  (참고) 그 tactic 이름도 안 보임"] += 1

    ext, miss, stdmiss = [], [], []
    for w in dict.fromkeys(re.findall(r"(?<![\w'.])([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)", _tgt)):
        base = w.split(".")[-1]
        if is_core(w) or base in local or w in local or base in intro or w in intro:
            continue
        if w == _tacname:                 # tactic 이름은 위에서 따로 셌다
            continue
        if len(base) < 3:
            continue
        ext.append(w)
        if not re.search(r"(?<![\w'])" + re.escape(base) + r"(?![\w'])", vp):
            if base in STDLIB or w in STDLIB:
                st["  (stdlib — 안다고 가정)"] += 1
                stdmiss.append(w)
            else:
                miss.append(w)
    # ★ tactic 종류별 분해 — 어떤 tactic 에서 환각이 나는지
    _tk = (_tacname or "?").lower()
    if _tk.startswith("e") and _tk[1:] in ("apply", "xact", "assumption", "destruct",
                                           "induction", "constructor", "exists"):
        _tk = _tk[1:]                      # eapply → apply
    if not ext:
        st["  외부 참조 없음"] += 1
        tac_kind[_tk]["없음"] += 1
        continue
    st["★ 외부 참조를 쓰는 예제"] += 1
    tac_kind[_tk]["씀"] += 1
    st["  외부 참조 이름 수"] += len(ext)
    for w in ext:
        k = KINDS.get(w) or KINDS.get(w.split(".")[-1]) or "미상"
        (kind_miss if w in miss else kind_seen)[k] += 1
    if miss or stdmiss:
        st["  (참고) stdlib 포함하면 결손 있는 예제"] += 1
    if miss:
        st["★★ 그중 환각(하나라도 안 보임)"] += 1
        tac_kind[_tk]["환각"] += 1
        st["  안 보이는 이름 수"] += len(miss)
        for w in miss:
            if (KINDS.get(w) or KINDS.get(w.split(".")[-1])) is None and len(unk) < 12:
                unk.append(f"{w:24s} ← {target.strip()[:60]}")
    if st["예제"] % 100 == 0:
        print(f"   … {st['예제']}/{N} ({time.time()-t0:.0f}s)", flush=True)

print(f"\n■ 결과 (예제 {st['예제']})\n")
for k in sorted(st):
    print(f"   {k:34s} {st[k]:6d}")
E = max(st["★ 외부 참조를 쓰는 예제"], 1)
print(f"\n   ★★ **외부 참조를 쓰는 예제 중 환각** "
      f"{st['★★ 그중 환각(하나라도 안 보임)']}/{st['★ 외부 참조를 쓰는 예제']} "
      f"= {st['★★ 그중 환각(하나라도 안 보임)']/E*100:.1f}%")
print(f"   (참고) 전체 예제 대비 "
      f"{st['★★ 그중 환각(하나라도 안 보임)']/max(st['예제'],1)*100:.1f}%")
NM = max(sum(kind_miss.values()), 1)
print(f"\n   ■ 이름 종류별  (안 보임 / 전체)")
allk = set(kind_miss) | set(kind_seen)
for k in sorted(allk, key=lambda x: -kind_miss[x]):
    tot = kind_miss[k] + kind_seen[k]
    print(f"     {k:16s} {kind_miss[k]:5d} / {tot:5d}  "
          f"({kind_miss[k]/max(tot,1)*100:5.1f}% 안 보임)  "
          f"결손 중 {kind_miss[k]/NM*100:5.1f}%")
if unk:
    print("\n   ■ tactic 종류별  (외부참조 쓰는 예제 / 환각 / 비율)")
    rows = sorted(tac_kind.items(), key=lambda kv: -kv[1]["씀"])
    print(f"     {'tactic':16s} {'씀':>7} {'환각':>7} {'환각률':>8}   {'외부참조 없음':>10}")
    for k, c in rows[:22]:
        if c["씀"] < 3:
            continue
        print(f"     {k[:16]:16s} {c['씀']:7d} {c['환각']:7d} "
              f"{c['환각']/max(c['씀'],1)*100:7.1f}% {c['없음']:12d}")
    print("\n   ■ '미상' 실제 예 (오탐 확인용)")
    for x in unk:
        print(f"     {x}")
