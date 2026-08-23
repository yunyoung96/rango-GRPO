#!/usr/bin/env python3
"""★ 환각 사례를 **프롬프트 전체 + gold tactic + 진단** 으로 덤프한다(md 조각).

`dump_unreachable.py` 는 goal 만 보여 줬다. 그런데 "왜 [TYPES]/[DEFINITIONS] 주입으로
안 잡히나" 를 설명하려면 **모델이 실제로 보는 것 전체**를 보여 줘야 한다.

각 사례마다 찍는 것
    · 모델이 보는 프롬프트 **전부** (절단 후 = 실제 입력)
    · gold tactic
    · 결손 이름마다:
        선언 종류 · rango 풀에서 빠지는 종류인가
        검색 100개 중 순위
        func_defs 인덱스에 **정의 재료가 있나**       ← 주입 가능성
        [DEFINITIONS]/[TYPES] 씨앗이 **닿을 수 있나**  ← 왜 안 들어갔나
        프로젝트 내 tactic 사용 횟수

사용: PYTHONPATH=src python3 scripts/dump_halluc_cases.py [표본] [덤프개수] > out.md
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
apply_v9_env(verbose=False)
os.environ.setdefault("CACHE_MAX_PAGE", "0")
os.environ.setdefault("CUTS_ALLOW_PARTIAL", "1")

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from tactic_gen.tactic_data import (TacticDataConf, LmDataset,  # noqa: E402
                                    example_collator_from_conf, get_tokenizer,
                                    _strip_coq_comments)
from tactic_gen.normalize_names import introduced_names  # noqa: E402
from tactic_gen.augment import pick_def  # noqa: E402
from tactic_gen import cut_lookup  # noqa: E402
from _coq_vocab import is_core  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
DUMP = int(sys.argv[2]) if len(sys.argv) > 2 else 10
STDLIB = set(json.load(open("data/stdlib_names.json")))
KINDS = json.load(open("data/decl_kinds.json")).get("kind", {})
USED = json.load(open("data/used_names.json"))
FD = json.load(open("data/func_defs_v3.json"))
POOL_EXCLUDED = {"Definition", "Constructor", "Field", "Fixpoint", "Inductive",
                 "Record", "Class", "Instance", "Notation", "CoFixpoint", "Variant"}

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", "/tmp/hsource-cache")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
HARD = _D.num("HARD_SEQ_LEN")
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)
_EXACT_ONLY = re.compile(r"^\s*e?exact\s+@?[\w'.]+\s*\.?\s*$")
_PROJ = re.compile(r"(?:^|/)repos/([^/]+)/")


def diagnose(name, ex, prem, vp):
    """왜 이 이름이 프롬프트에 없는가."""
    b = name.split(".")[-1]
    d = {"name": name, "kind": KINDS.get(name) or KINDS.get(b) or "미상"}
    d["pool_excluded"] = d["kind"] in POOL_EXCLUDED
    d["rank"] = None
    for j, p in enumerate(prem):
        if re.search(r"(?<![\w'])" + re.escape(b) + r"(?![\w'])", p):
            d["rank"] = j + 1
            break
    fp = getattr(ex, "file_name", "") or ""
    cand = FD.get(b)
    d["in_index"] = bool(cand)
    d["pickable"] = bool(cand and pick_def(cand, fp))
    d["defn"] = (pick_def(cand, fp) if cand else None)
    # 씨앗이 닿나 — [DEFINITIONS]/[TYPES] 씨앗의 출처 전부에 이름이 있는가
    goal = getattr(ex, "proof_state", "") or ""
    script = getattr(ex, "proof_script", "") or ""
    proofs = "\n".join(str(x) for x in (getattr(ex, "proofs", None) or []))
    premtxt = "\n".join(prem[:12])
    where = []
    for tag, txt in (("goal", goal), ("SCRIPT", script), ("PROOFS", proofs),
                     ("PREMISES(상위12)", premtxt)):
        if re.search(r"(?<![\w'])" + re.escape(b) + r"(?![\w'])", txt or ""):
            where.append(tag)
    d["seed_sources"] = where
    m = _PROJ.search(fp)
    v = USED.get(m.group(1), {}).get(b) if m else None
    d["uses"] = (v[0] if isinstance(v, list) else (v or 0))
    d["files"] = (v[1] if isinstance(v, list) else 0)
    return d


def cause_of(d):
    """한 줄 원인 분류."""
    if not d["in_index"] and d["rank"] is None:
        return "A. 인덱스에도 검색에도 없다 — 주입 재료 자체가 없다"
    if d["rank"] is not None:
        return f"B. 검색에는 있는데 **{d['rank']}위** 라 예산에 못 실린다"
    if d["in_index"] and not d["seed_sources"]:
        return "C. 주입 재료는 있는데 **씨앗이 닿지 않는다** (이름이 goal·script·proofs 어디에도 없다)"
    if d["in_index"] and d["seed_sources"]:
        return f"D. 씨앗은 닿는데({'·'.join(d['seed_sources'])}) 예산/캡에 밀렸다"
    return "E. 기타"


out = []
random.seed(11)
tried = seen_n = 0
by_cause = collections.Counter()
while seen_n < N and tried < N * 40 and len(out) < DUMP * 4:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        ex = ds.resolved_example(i)
        full = coll.collate(tok, ex)
    except Exception:
        continue
    if "[TACTIC]" not in full:
        continue
    seen_n += 1
    prompt, target = full.rsplit("[TACTIC]", 1)
    ids = tok(full, add_special_tokens=False)["input_ids"]
    vis = tok.decode(ids[max(0, len(ids) - HARD):], skip_special_tokens=True)
    vp = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis
    tgt = re.sub(r'"[^"]*"', " ", _strip_coq_comments(target))
    key = (f"{getattr(ex, 'file_name', '')}:"
           f"{getattr(ex, 'proof_idx', '')}:{getattr(ex, 'step_idx', '')}")
    has_plan = False
    try:
        has_plan = bool(cut_lookup.plan_for(key))
    except Exception:
        pass
    src = ("cut 생성" if ("H_asrt" in target
                       or (has_plan and _EXACT_ONLY.match(tgt.strip())))
           else "gold 원본")
    if src != "gold 원본":
        continue
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
    tacn = set()
    for seg in re.split(r";|\bby\b", tgt):
        seg = seg.strip().lstrip("[](){}| \t")
        for _ in range(3):
            seg = re.sub(r"^(?:now|try|repeat|by|first|solve|progress|do\s+\d+|"
                         r"abstract|once|time)\b\s*\[?\s*", "", seg)
        mm = re.match(r"([A-Za-z_][\w']*)", seg)
        if mm:
            tacn.add(mm.group(1))
    prem = [(p if isinstance(p, str) else str(p))
            for p in (getattr(ex, "premises", None) or [])]
    miss = []
    for w in dict.fromkeys(re.findall(
            r"(?<![\w'.])([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)", tgt)):
        b = w.split(".")[-1]
        if (is_core(w) or b in local or w in local or b in intro or w in intro
                or w in tacn or b in tacn or b in STDLIB or w in STDLIB):
            continue
        if not re.search(r"(?<![\w'])" + re.escape(b) + r"(?![\w'])", vp):
            miss.append(w)
    if not miss:
        continue
    ds_ = [diagnose(w, ex, prem, vp) for w in miss]
    c = cause_of(ds_[0])
    by_cause[c[0]] += 1
    out.append({"idx": i, "file": getattr(ex, "file_name", ""), "vp": vp,
                "target": target.strip(), "diag": ds_, "cause": c})

print(f"<!-- 표본 {seen_n} · gold 원본 환각 {len(out)}건 · 원인 분포 {dict(by_cause)} -->\n")
json.dump({"n": seen_n, "cases": out, "cause": dict(by_cause)},
          open(os.environ.get("DUMP_JSON", "/tmp/halluc_cases.json"), "w"),
          ensure_ascii=False)
for c in sorted(by_cause):
    print(f"원인 {c}: {by_cause[c]}건")
print(f"\n→ /tmp/halluc_cases.json 에 {len(out)}건 저장")
