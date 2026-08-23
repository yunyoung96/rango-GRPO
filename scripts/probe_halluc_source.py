#!/usr/bin/env python3
"""★ 환각이 **gold 원본 스텝**에서 나온 건가, **우리가 만든 cut** 에서 나온 건가.

이걸 갈라야 하는 이유: 둘은 처방이 정반대다.
    gold 원본  — 사람이 쓴 tactic 이 프롬프트에 없는 이름을 부른다.
                 우리가 만든 게 아니므로 **데이터의 성질**이고, 고칠 길은 주입·풀·학습뿐.
    cut 생성   — 우리 `assert_split` 이 만든 하위스텝이 이름을 부른다.
                 **우리가 만든 문제**이므로 생성 규칙을 바꿔 없앨 수 있다.

분류 표지
    target 에 `H_asrt` 가 있다              → cut 생성 (assert 또는 final)
    cut 계획이 있고 target 이 `exact L.` 뿐  → cut 생성 (close)
    그 외                                   → gold 원본

환각 이름마다 함께 기록하는 것
    · 선언 종류(decl_kinds)          · 풀에서 제외되는 종류인가
    · 검색 100개 안 순위             · 프로젝트 내 tactic 사용 횟수(롱테일 판정)

사용: PYTHONPATH=src python3 scripts/probe_halluc_source.py [표본]
"""
import collections
import copy
import json
import logging
import os
import random
import re
import sys
import time

sys.path.insert(0, "src")
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
from tactic_gen import cut_lookup  # noqa: E402
from _coq_vocab import is_core  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
STDLIB = set(json.load(open("data/stdlib_names.json")))
KINDS = json.load(open("data/decl_kinds.json")).get("kind", {})
USED = json.load(open("data/used_names.json"))
# rango 가 **프로젝트 파일**에서 풀에서 빼는 종류
POOL_EXCLUDED = {"Definition", "Constructor", "Field", "Fixpoint", "Inductive",
                 "Record", "Class", "Instance", "Notation", "CoFixpoint", "Variant"}

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
_td = copy.deepcopy(cc["tactic_data"])
_td["cache_loc"] = os.environ.get("VERIFY_CACHE", "/tmp/hsource-cache")
conf = TacticDataConf.from_yaml(_td)
tok = get_tokenizer(cc["model_name"])
ds = LmDataset.from_conf(conf, Split.TRAIN, None)
coll = example_collator_from_conf(conf.collator_conf)
HARD = int(os.environ.get("HARD_SEQ_LEN", "2048"))
TOTAL = ds.shuffled_idx.split_length(Split.TRAIN)
_EXACT_ONLY = re.compile(r"^\s*e?exact\s+@?[\w'.]+\s*\.?\s*$")
_PROJ = re.compile(r"(?:^|/)repos/([^/]+)/")

st = collections.Counter()
src_tot = collections.Counter()      # 출처별 외부참조 예제 수
src_hal = collections.Counter()      # 출처별 환각 예제 수
kind_by_src = collections.defaultdict(collections.Counter)
rank_by_src = collections.defaultdict(list)
uses_by_src = collections.defaultdict(list)
pool_by_src = collections.Counter()
samples = collections.defaultdict(list)

random.seed(4)
tried = 0
t0 = time.time()
while st["예제"] < N and tried < N * 40:
    i = random.randrange(TOTAL)
    tried += 1
    try:
        ex = ds.resolved_example(i)
        full = coll.collate(tok, ex)
    except Exception:
        continue
    if "[TACTIC]" not in full:
        continue
    st["예제"] += 1
    prompt, target = full.rsplit("[TACTIC]", 1)
    ids = tok(full, add_special_tokens=False)["input_ids"]
    vis = tok.decode(ids[max(0, len(ids) - HARD):], skip_special_tokens=True)
    vp = vis.rsplit("[TACTIC]", 1)[0] if "[TACTIC]" in vis else vis
    tgt = re.sub(r'"[^"]*"', " ", _strip_coq_comments(target))

    # ── 출처 분류 ──────────────────────────────────────────────────────────
    key = (f"{getattr(ex, 'file_name', '')}:"
           f"{getattr(ex, 'proof_idx', '')}:{getattr(ex, 'step_idx', '')}")
    has_plan = False
    try:
        has_plan = bool(cut_lookup.plan_for(key))
    except Exception:
        pass
    if "H_asrt" in target:
        src = "cut 생성"
        sub = "assert/final"
    elif has_plan and _EXACT_ONLY.match(tgt.strip()):
        src = "cut 생성"
        sub = "close(exact L)"
    else:
        src = "gold 원본"
        sub = "gold"
    st[f"출처·{src}"] += 1
    st[f"  세부·{sub}"] += 1

    # ── 외부 참조 · 환각 판정 (probe_extref_halluc 와 같은 규칙) ────────────
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
    pm = _PROJ.search(getattr(ex, "file_name", "") or "")
    used = USED.get(pm.group(1), {}) if pm else {}

    ext, miss = [], []
    for w in dict.fromkeys(re.findall(
            r"(?<![\w'.])([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)", tgt)):
        base = w.split(".")[-1]
        if (is_core(w) or base in local or w in local or base in intro or w in intro
                or w in tacn or base in tacn):
            continue
        ext.append(w)
        if not re.search(r"(?<![\w'])" + re.escape(base) + r"(?![\w'])", vp):
            if base in STDLIB or w in STDLIB:
                st["  stdlib(안다고 가정)"] += 1
            else:
                miss.append(w)
    if not ext:
        continue
    src_tot[src] += 1
    if not miss:
        continue
    src_hal[src] += 1
    if len(samples[src]) < 6:
        samples[src].append(f"{miss[0]:22s} ← {target.strip()[:66]}")
    for w in miss:
        b = w.split(".")[-1]
        k = KINDS.get(w) or KINDS.get(b) or "미상"
        kind_by_src[src][k] += 1
        if k in POOL_EXCLUDED:
            pool_by_src[src] += 1
        r = None
        for j, p in enumerate(prem):
            if re.search(r"(?<![\w'])" + re.escape(b) + r"(?![\w'])", p):
                r = j + 1
                break
        rank_by_src[src].append(r if r else 999)
        v = used.get(b)
        uses_by_src[src].append(v[0] if isinstance(v, list) else (v or 0))
    if st["예제"] % 250 == 0:
        print(f"   … {st['예제']}/{N} ({time.time()-t0:.0f}s)", flush=True)

# ── 출력 ────────────────────────────────────────────────────────────────────
print(f"\n■ 표본 {st['예제']}   (환각 판정은 probe_extref_halluc 와 같은 규칙)\n")
print("── 예제 출처 구성 ─────────────────────────────────────────────")
for k in sorted(st):
    if k.startswith("출처·") or k.startswith("  세부·"):
        print(f"   {k:26s} {st[k]:6d}  ({st[k]/max(st['예제'],1)*100:5.1f}%)")
print("\n── 출처별 환각률 ──────────────────────────────────────────────")
print(f"   {'출처':12s} {'외부참조 예제':>12s} {'환각':>6s} {'환각률':>8s}")
for s in ("gold 원본", "cut 생성"):
    t_, h_ = src_tot[s], src_hal[s]
    print(f"   {s:12s} {t_:12d} {h_:6d} {h_/max(t_,1)*100:7.1f}%")
T = sum(src_tot.values()) or 1
H = sum(src_hal.values()) or 1
print(f"   {'합계':12s} {sum(src_tot.values()):12d} {sum(src_hal.values()):6d} "
      f"{sum(src_hal.values())/T*100:7.1f}%")
print(f"\n   환각 예제 중  gold 원본 {src_hal['gold 원본']/H*100:.1f}% · "
      f"cut 생성 {src_hal['cut 생성']/H*100:.1f}%")

for s in ("gold 원본", "cut 생성"):
    tot = sum(kind_by_src[s].values())
    if not tot:
        continue
    print(f"\n── [{s}] 환각 이름 {tot}개 ────────────────────────────────")
    print("   종류별:")
    for k, v in kind_by_src[s].most_common(8):
        mark = " ←풀제외" if k in POOL_EXCLUDED else ""
        print(f"      {k:14s} {v:4d}  {v/tot*100:5.1f}%{mark}")
    print(f"   풀에서 제외되는 종류  {pool_by_src[s]}/{tot} = "
          f"{pool_by_src[s]/tot*100:.1f}%")
    rr = sorted(rank_by_src[s])
    inlist = [x for x in rr if x != 999]
    print(f"   검색 100개 안에 있음  {len(inlist)}/{tot} = {len(inlist)/tot*100:.1f}%"
          + (f"  (순위 중앙 {sorted(inlist)[len(inlist)//2]})" if inlist else ""))
    uu = sorted(uses_by_src[s])
    if uu:
        print(f"   프로젝트 내 사용 횟수  중앙 {uu[len(uu)//2]} · "
              f"1회 이하 {sum(1 for x in uu if x <= 1)/len(uu)*100:.0f}%")
    for line in samples[s]:
        print(f"      · {line}")
