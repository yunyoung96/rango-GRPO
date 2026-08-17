#!/usr/bin/env python3
"""검색 실패 원인 분해를 **gold lemma 개수별로** 나눠 본다.

## 왜 나눠야 하나

앞선 분해(diagnose_retriever_vs_pool.py)는 tactic 의 **첫 lemma 하나**만 분류했다.
그런데 tactic 의 약 1/5 는 lemma 를 2개 이상 쓰고, 그런 경우 **하나만 빠져도 못 쓴다**.
따라서 두 가지를 갈라 봐야 실상이 보인다.

  · lemma 1개짜리 : 그 하나가 어디 있나 (기존 분해와 동일)
  · lemma 2개+    : **개별 lemma** 가 각각 어디 있나 + tactic 단위로 **전부** 갖췄나

## 분류 (각 lemma 마다)

  ①  top-K 검색 결과 안에 있음                  정상
  ②  avail_premises 풀엔 있는데 검색이 못 뽑음   → retriever 성능
  ③a 데이터셋의 같은 프로젝트 다른 파일에 있음    → 수집 로직
  ③b 다른 프로젝트에만 있음                      → 접근 불가(정상)
  ④  데이터셋 어디에도 없음                      → 표준/외부 라이브러리

사용: python3 scripts/diagnose_by_lemma_count.py [n] [topk]
"""
import collections
import copy
import math
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
from tactic_gen.gold_lemma import _TACKW, _LOCALPAT, _IDRE  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
TOPK = int(sys.argv[2]) if len(sys.argv) > 2 else 50
CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")

cc = yaml.safe_load(open(CONF))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"]["num_premises"] = max(TOPK, 100)
tdc["formatter_conf"].pop("proof_ret", None)      # BM25 는 불필요한데 예제당 수십 초를 먹는다
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, Split.TRAIN, N)
sdb = SentenceDB.load(conf.sentence_db_loc)

_NAME = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                   r"Instance|Axiom|Proposition|Example|Let|Program\s+\w+)\s+"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")


def declname(t):
    m = _NAME.match(t or "")
    return m.group(1).split(".")[-1] if m else None


def all_gold_lemmas(tac: str, loc: set) -> list[str]:
    """tactic 전체에서 쓰인 전역 lemma 이름을 **전부**.

    `;` 조각마다 rewrite/apply 계열이면 인자를 훑는다. ` in ` 뒤(대상 가설)와
    tactic 키워드·지역가설·짧은 소문자는 뺀다.
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
            if b in _TACKW or b.isdigit() or _LOCALPAT.match(b) or b in loc:
                continue
            if len(b) < 3 and b.islower():
                continue
            if b not in out:
                out.append(b)
    return out


print("sentences.db 색인 중…", flush=True)
idx: dict[str, set] = collections.defaultdict(set)
db = sqlite3.connect(str(conf.sentence_db_loc))
for text, fp in db.execute("select text, file_path from sentence"):
    n = declname(text)
    if n:
        idx[n].add(fp or "")
db.close()
print(f"  이름 {len(idx)}개 색인", flush=True)


def proj_of(path: str) -> str:
    parts = [x for x in (path or "").replace("\\", "/").split("/") if x]
    if "repos" in parts:
        i = parts.index("repos")
        if i + 1 < len(parts):
            return parts[i + 1]
    if "theories" in parts and "coq" in parts:
        return "COQ_STDLIB"
    if "lib" in parts:
        i = parts.index("lib")
        if i + 1 < len(parts):
            return "opam:" + parts[i + 1]
    return parts[0] if parts else ""


ORDER = ["①", "②", "③a", "③b", "④"]
LABEL = {"①": "top50 안에 있음 (정상)",
         "②": "풀엔 있는데 검색이 못 뽑음 → retriever",
         "③a": "같은 프로젝트 다른 파일에 → 수집 로직",
         "③b": "다른 프로젝트에만 (접근 불가)",
         "④": "데이터셋에도 없음 (표준/외부)"}

by_cnt = {1: collections.Counter(), 2: collections.Counter()}   # 2 = "2개 이상"
tac_all = {1: collections.Counter(), 2: collections.Counter()}  # tactic 단위 전부/일부/전무
src_by_cnt = {1: collections.Counter(), 2: collections.Counter()}
n_tac = collections.Counter()
n_scanned = 0

for i in range(N):
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    n_scanned += 1
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    loc = local_names(getattr(e, "proof_state", "") or "")
    golds = all_gold_lemmas(tac, loc)
    if not golds:
        continue
    grp = 1 if len(golds) == 1 else 2
    n_tac[grp] += 1

    prems = [p if isinstance(p, str) else getattr(p, "text", str(p))
             for p in (getattr(e, "premises", None) or [])]
    top = {declname(t) for t in prems[:TOPK]}
    top.discard(None)

    # 풀·데이터셋 조회는 top50 에 없는 것이 하나라도 있을 때만 (DatasetFile 로드가 비싸다)
    dp = pool = None
    if any(g not in top for g in golds):
        sid = ds.shuffled_idx.get_idx(ds.split, i)
        try:
            dp = DatasetFile.load(conf.data_loc / "data_points" / sid.file, sdb)
            pool = list(getattr(dp, "out_of_file_avail_premises", []) or [])
            try:
                pool += list(dp.get_in_file_premises_before(dp.proofs[sid.proof_idx]))
            except Exception:
                pass
        except Exception:
            pool = None

    n_ok = 0
    for g in golds:
        if g in top:
            by_cnt[grp]["①"] += 1
            n_ok += 1
            continue
        if pool is None:
            continue
        hit = next((s for s in pool if declname(getattr(s, "text", "")) == g), None)
        if hit is not None:
            by_cnt[grp]["②"] += 1
            src = proj_of(getattr(hit, "file_path", ""))
            myp = proj_of(getattr(dp.file_context, "file", ""))
            src_by_cnt[grp]["Coq 표준" if src == "COQ_STDLIB"
                            else "opam 외부" if src.startswith("opam:")
                            else "같은 프로젝트" if src == myp else "다른 프로젝트"] += 1
            continue
        where = idx.get(g)
        if not where:
            by_cnt[grp]["④"] += 1
            continue
        myp = proj_of(getattr(dp.file_context, "file", ""))
        by_cnt[grp]["③a" if myp and myp in {proj_of(w) for w in where} else "③b"] += 1

    tac_all[grp]["전부 있음" if n_ok == len(golds)
                 else ("일부만" if n_ok else "하나도 없음")] += 1


def ci(p, n):
    return 1.96 * math.sqrt(max(p * (1 - p), 1e-12) / max(n, 1)) * 100


tot_tac = sum(n_tac.values())
print(f"\n■ TRAIN — 훑은 예제 {n_scanned}개 중 lemma 를 쓰는 tactic {tot_tac}건 (top{TOPK} 기준)")
print(f"   lemma 1개짜리 {n_tac[1]}건 ({n_tac[1]/max(tot_tac,1)*100:.1f}%)"
      f" · 2개 이상 {n_tac[2]}건 ({n_tac[2]/max(tot_tac,1)*100:.1f}%)")

for grp, title in ((1, "lemma 1개짜리 tactic"), (2, "lemma 2개 이상 tactic")):
    tot = sum(by_cnt[grp].values())
    print(f"\n── {title} — **개별 lemma** {tot}개의 소재 ──")
    for k in ORDER:
        v = by_cnt[grp][k]
        p = v / max(tot, 1)
        print(f"   {k:3s} {LABEL[k]:38s} {v:5d} = {p*100:5.1f}%  ±{ci(p, tot):4.1f}pp")
    if src_by_cnt[grp]:
        s = sum(src_by_cnt[grp].values())
        print(f"       ② 의 출처: " + " · ".join(
            f"{k} {src_by_cnt[grp][k]/s*100:.1f}%" for k in sorted(
                src_by_cnt[grp], key=lambda x: -src_by_cnt[grp][x])))

print(f"\n── ★ tactic 단위: **필요한 lemma 를 전부 갖췄나** ──")
print(f"   {'':14s} {'전부 있음':>10s} {'일부만':>8s} {'하나도 없음':>10s}")
for grp, title in ((1, "lemma 1개"), (2, "lemma 2개+")):
    t = sum(tac_all[grp].values())
    print(f"   {title:14s} {tac_all[grp]['전부 있음']/max(t,1)*100:9.1f}%"
          f" {tac_all[grp]['일부만']/max(t,1)*100:7.1f}%"
          f" {tac_all[grp]['하나도 없음']/max(t,1)*100:9.1f}%   (n={t})")
tot_all = collections.Counter()
for grp in (1, 2):
    tot_all.update(tac_all[grp])
t = sum(tot_all.values())
p_all = tot_all["전부 있음"] / max(t, 1)
print(f"   {'합계':14s} {p_all*100:9.1f}% {tot_all['일부만']/max(t,1)*100:7.1f}%"
      f" {tot_all['하나도 없음']/max(t,1)*100:9.1f}%   (n={t})")
print(f"\n   ⇒ **필요한 lemma 를 전부 갖춘 tactic: {p_all*100:.1f}% ±{ci(p_all, t):.1f}pp**")
