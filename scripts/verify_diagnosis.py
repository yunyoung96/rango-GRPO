#!/usr/bin/env python3
"""앞선 분류가 **정말 맞는지** 케이스를 통째로 까서 확인한다 + 복수 lemma 를 센다.

## 왜

`diagnose_retriever_vs_pool.py` 의 ①②③④ 분류는 이름 문자열 매칭에 의존한다. 매칭이
틀리면 결론이 통째로 틀린다. 그래서 표본을 뽑아 **원자료를 그대로 출력**해 눈으로 검증한다.

  · gold tactic 원문과 추출한 이름이 맞는가
  · ② 로 분류된 것: top50 목록에 정말 없고 풀에는 정말 있는가 (양쪽 다 직접 확인)
  · ④ 로 분류된 것: sentences.db 에 정말 없는가 (LIKE 로 느슨하게도 찾아본다)

## 복수 lemma

앞선 측정은 **첫 lemma 하나**만 봤다. `rewrite A, B` 나 `apply A; apply B` 처럼 여러 개가
필요하면 실제 요구는 더 엄격하다 — 하나만 있어도 못 푼다. 그 비율과, 복수일 때 **전부**
검색에 들어오는 비율을 따로 센다.
"""
import collections
import copy
import os
import re
import sqlite3
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from data_management.dataset_file import DatasetFile  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
from tactic_gen.gold_lemma import gold_lemma, _TACKW, _LOCALPAT, _IDRE  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 900
TOPK = int(sys.argv[2]) if len(sys.argv) > 2 else 50
SHOW = int(sys.argv[3]) if len(sys.argv) > 3 else 3
CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")

cc = yaml.safe_load(open(CONF))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"]["num_premises"] = max(TOPK, 100)
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, Split.TRAIN, N)
sdb = SentenceDB.load(conf.sentence_db_loc)
db = sqlite3.connect(str(conf.sentence_db_loc))

_NAME = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                   r"Instance|Axiom|Proposition|Example|Let|Program\s+\w+)\s+"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")


def declname(t):
    m = _NAME.match(t or "")
    return m.group(1).split(".")[-1] if m else None


def all_gold_lemmas(tac: str, loc: set) -> list[str]:
    """tactic **전체**에서 쓰인 전역 lemma 이름을 전부. (첫 하나만 보던 것의 확장)

    `;` 로 이어진 모든 조각을 보고, 각 조각에서 rewrite/apply 계열이면 인자를 전부 훑는다.
    """
    out: list[str] = []
    for piece in re.split(r"\s*;\s*", (tac or "").strip()):
        toks = piece.split()
        if not toks:
            continue
        head = toks[0].lower().strip(";.")
        if head not in ("rewrite", "apply", "eapply", "erewrite"):
            continue
        rest = re.split(r"\bin\b", piece[len(head):])[0]
        for x in _IDRE.findall(rest):
            b = x.split(".")[-1]
            if b in _TACKW or b.isdigit() or _LOCALPAT.match(b):
                continue
            if len(b) < 3 and b.islower():
                continue
            if b in loc:                       # 지역 가설
                continue
            if b not in out:
                out.append(b)
    return out


def in_db(name: str) -> list:
    """sentences.db 에 그 이름의 **선언**이 있나. 정확매칭이 안 되면 LIKE 로 느슨하게 재확인."""
    rows = []
    for kw in ("Lemma", "Theorem", "Definition", "Corollary", "Fact", "Remark",
               "Fixpoint", "Instance", "Axiom", "Proposition", "Example"):
        q = f"{kw} {name}"
        for t, fp in db.execute(
                "select text, file_path from sentence where text like ? limit 3", (q + "%",)):
            if declname(t) == name:
                rows.append((t[:70], fp))
    return rows


multi = collections.Counter()
multi_cover = collections.Counter()
all_cover = collections.Counter()
one_cover = collections.Counter()
shown = collections.Counter()
n_scanned = n_gold = 0
mismatch = []

for i in range(N):
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    n_scanned += 1
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    loc = local_names(getattr(e, "proof_state", "") or "")
    first = gold_lemma(tac)
    allg = all_gold_lemmas(tac, loc)
    if first is not None and first in loc:
        first = None
    if not allg:
        continue
    n_gold += 1

    # ── 복수 lemma 통계 ──
    multi[min(len(allg), 4)] += 1
    prems = [p if isinstance(p, str) else getattr(p, "text", str(p))
             for p in (getattr(e, "premises", None) or [])]
    top = {declname(t) for t in prems[:TOPK]}
    top.discard(None)
    got = sum(1 for g in allg if g in top)
    lbl = "전부 있음" if got == len(allg) else ("일부만" if got else "하나도 없음")
    if len(allg) >= 2:
        multi_cover[lbl] += 1
    all_cover[lbl] += 1            # 1개짜리까지 포함한 **진짜** 커버리지
    if len(allg) == 1:
        one_cover[lbl] += 1

    # 첫-lemma 방식과 전체 방식이 어긋나는 경우를 모아 본다
    if first is not None and allg and first != allg[0] and len(mismatch) < 5:
        mismatch.append((tac[:70], first, allg))

    # ── 분류 검증용 원자료 덤프 ──
    if first is None:
        continue
    cls = None
    if first in top:
        cls = "①"
    else:
        sid = ds.shuffled_idx.get_idx(ds.split, i)
        try:
            dp = DatasetFile.load(conf.data_loc / "data_points" / sid.file, sdb)
        except Exception:
            continue
        pool = list(getattr(dp, "out_of_file_avail_premises", []) or [])
        try:
            pool += list(dp.get_in_file_premises_before(dp.proofs[sid.proof_idx]))
        except Exception:
            pass
        hit = next((s for s in pool if declname(getattr(s, "text", "")) == first), None)
        cls = "②" if hit is not None else "④?"
        if shown[cls] < SHOW:
            shown[cls] += 1
            print("=" * 78)
            print(f"[{cls}] tactic : {tac[:90]}")
            print(f"     추출한 이름 : {first}   (전체: {allg})")
            print(f"     지역 이름   : {sorted(loc)[:8]}")
            print(f"     top{TOPK} 목록에 있나 : {first in top}")
            print(f"     top{TOPK} 이름 앞 12개 : {sorted(x for x in top)[:12]}")
            print(f"     풀 크기 : {len(pool)}   풀에서 찾음 : {hit is not None}")
            if hit is not None:
                print(f"     풀의 그 문장 : {getattr(hit,'text','')[:110]}")
                print(f"     그 파일      : {getattr(hit,'file_path','')}")
            else:
                rows = in_db(first)
                print(f"     sentences.db 직접조회 : {len(rows)}건")
                for t, fp in rows[:2]:
                    print(f"        {t}  @{fp}")
        continue
    if shown[cls] < SHOW:
        shown[cls] += 1
        print("=" * 78)
        print(f"[{cls}] tactic : {tac[:90]}")
        print(f"     추출한 이름 : {first}   → top{TOPK} 안에 있음 ✓")

print("\n" + "=" * 78)
print(f"■ 훑은 예제 {n_scanned} · lemma 를 쓰는 {n_gold}건\n")
print("   한 tactic 이 요구하는 lemma 개수")
for k in sorted(multi):
    lbl = f"{k}개" + ("+" if k == 4 else "")
    print(f"     {lbl:5s} {multi[k]:4d} = {multi[k]/max(n_gold,1)*100:5.1f}%")
if multi_cover:
    tot = sum(multi_cover.values())
    print(f"\n   2개 이상인 {tot}건의 top{TOPK} 커버리지")
    for k in ("전부 있음", "일부만", "하나도 없음"):
        if k in multi_cover:
            print(f"     {k:8s} {multi_cover[k]:4d} = {multi_cover[k]/tot*100:5.1f}%")
tot_a = sum(all_cover.values())
print(f"\n   ★ **필요한 lemma 를 전부 갖춘 비율** (전체 {tot_a}건)")
for k in ("전부 있음", "일부만", "하나도 없음"):
    if k in all_cover:
        print(f"     {k:8s} {all_cover[k]:4d} = {all_cover[k]/max(tot_a,1)*100:5.1f}%")
t1 = sum(one_cover.values())
print(f"\n   참고 · lemma 1개짜리 {t1}건만: "
      + "  ".join(f"{k} {one_cover[k]/max(t1,1)*100:.1f}%" for k in one_cover))
if mismatch:
    print("\n   첫-lemma 방식과 전체 방식이 어긋난 예:")
    for t, f, a in mismatch:
        print(f"     · {t}\n         첫={f}  전체={a}")
