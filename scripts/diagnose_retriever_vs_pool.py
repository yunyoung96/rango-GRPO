#!/usr/bin/env python3
"""top-50 에 gold premise 가 없는 이유가 **retriever 탓인가 풀 구성 탓인가**를 가른다.

## 왜 갈라야 하나

둘은 고치는 방법이 완전히 다르다.

  · retriever 탓  → 검색기를 바꾸거나(TF-IDF→학습형) 재랭킹·SearchPattern 을 붙인다
  · 풀 구성 탓    → 데이터 생성 시 의존 라이브러리 수집 로직을 고쳐야 한다(재생성 필요)

## 어떻게 가르나

gold lemma 이름을 세 곳에서 차례로 찾는다. 각 단계가 하나의 원인에 대응한다.

  ① 검색 결과 top-K            있으면 정상
  ② avail_premises 풀(필터 전)  풀엔 있는데 ①에 없다     → **retriever 성능**
  ③ sentences.db(데이터셋 전체) 데이터셋엔 있는데 ②에 없다 → **수집 로직**(이 파일에서 안 보임)
  ④ 어디에도 없음                                        → 데이터셋 밖(표준/외부 라이브러리)

③ 은 다시 나눈다: **같은 프로젝트의 다른 파일**에 있으면 수집 로직의 명백한 구멍이고,
다른 프로젝트에 있으면 애초에 그 파일에서 접근 불가능한 게 맞다(정상).

사용: python3 scripts/diagnose_retriever_vs_pool.py [n] [topk] [train|test|val]
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
from tactic_gen.gold_lemma import gold_lemma  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 800
TOPK = int(sys.argv[2]) if len(sys.argv) > 2 else 50
SPLIT = (sys.argv[3] if len(sys.argv) > 3 else "train").upper()
CONF = os.environ.get("CONF", "all_log/ft_qwen3b_v8_conf.yaml")

cc = yaml.safe_load(open(CONF))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"]["num_premises"] = max(TOPK, 100)
tdc["formatter_conf"].pop("proof_ret", None)      # BM25 는 불필요한데 예제당 수십 초를 먹는다
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), N)
sdb = SentenceDB.load(conf.sentence_db_loc)

_NAME = re.compile(r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|"
                   r"Instance|Axiom|Proposition|Example|Let|Program\s+\w+)\s+"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")


def declname(t):
    m = _NAME.match(t or "")
    return m.group(1).split(".")[-1] if m else None


# ── 데이터셋 전체 색인: 이름 → {file_path} ────────────────────────────────────
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
    """파일 경로 → 프로젝트 식별자.

    실제 형식은 세 가지다(sentences.db 확인):
      /coq-dataset/repos/<owner>-<repo>/…      · ../coq-dataset/repos/<owner>-<repo>/…
      /root/.opam/…/lib/coq/theories/…         (Coq 표준 라이브러리)
      /root/.opam/…/lib/<pkg>/…                (opam 외부 패키지)
    ★ "coq-dataset" 을 먼저 매칭하면 프로젝트가 전부 "repos" 로 뭉개져 **항상 같은 프로젝트**가
      된다 — repos 를 우선 본다.
    """
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


n_scanned = 0
cnt = collections.Counter()
retr_src = collections.Counter()
ex = collections.defaultdict(list)
n_gold = 0

for i in range(N):
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    n_scanned += 1
    base = gold_lemma(e.next_steps[0] if getattr(e, "next_steps", None) else "")
    if base is None:
        continue
    # ★ goal 의 가설 블록에 선언된 이름이면 **지역 가설**이지 lemma 가 아니다.
    #   (H_bt22'_node, Hi, Hloc1 처럼 정규식만으로는 못 거르는 것들이 여기서 걸린다.)
    if base in local_names(getattr(e, "proof_state", "") or ""):
        continue
    n_gold += 1

    prems = [p if isinstance(p, str) else getattr(p, "text", str(p))
             for p in (getattr(e, "premises", None) or [])]
    if any(declname(t) == base for t in prems[:TOPK]):
        cnt[f"① top{TOPK} 안에 있음 (정상)"] += 1
        continue

    sid = ds.shuffled_idx.get_idx(ds.split, i)
    try:
        dp = DatasetFile.load(conf.data_loc / "data_points" / sid.file, sdb)
    except Exception:
        cnt["? 파일 로드 실패"] += 1
        continue
    pool = list(getattr(dp, "out_of_file_avail_premises", []) or [])
    try:
        pool += list(dp.get_in_file_premises_before(dp.proofs[sid.proof_idx]))
    except Exception:
        pass
    hit = next((s for s in pool if declname(getattr(s, "text", "")) == base), None)
    if hit is not None:
        cnt["② 풀엔 있는데 검색이 못 뽑음 → **retriever**"] += 1
        # ★ 이 41% 가 표준 라이브러리인지 프로젝트 lemma 인지에 따라 대책이 다르다.
        #   표준이면 "모델이 이미 아는 것"일 수 있고, 프로젝트면 순수 검색 실패다.
        src = proj_of(getattr(hit, "file_path", ""))
        myp = proj_of(getattr(dp.file_context, "file", ""))
        kind = ("Coq 표준" if src == "COQ_STDLIB"
                else "opam 외부" if src.startswith("opam:")
                else "같은 프로젝트" if src == myp
                else f"다른 프로젝트({src})")
        retr_src[kind.split("(")[0]] += 1
        if len(ex["retr"]) < 8:
            ex["retr"].append((base, f"{kind:16s} 풀 {len(pool)}개"))
        continue

    where = idx.get(base)
    if not where:
        cnt["④ 데이터셋에도 없음 → 표준/외부 라이브러리"] += 1
        if len(ex["out"]) < 8:
            ex["out"].append((base, ""))
        continue

    myproj = proj_of(getattr(dp.file_context, "file", ""))
    projs = {proj_of(w) for w in where}
    if myproj and myproj in projs:
        cnt["③a 같은 프로젝트 다른 파일에 있음 → **수집 로직**"] += 1
        if len(ex["same"]) < 8:
            ex["same"].append((base, myproj))
    else:
        cnt["③b 다른 프로젝트에만 있음 (접근 불가, 정상)"] += 1
        if len(ex["other"]) < 6:
            ex["other"].append((base, ",".join(list(projs)[:2])))

import math
print(f"\n■ {SPLIT} — 훑은 예제 {n_scanned}개 중 gold 가 lemma 를 쓰는 {n_gold}건 "
      f"({n_gold/max(n_scanned,1)*100:.1f}%) · top{TOPK} 기준\n")
for k in sorted(cnt, key=lambda x: -cnt[x]):
    p_ = cnt[k] / max(n_gold, 1)
    ci = 1.96 * math.sqrt(p_ * (1 - p_) / max(n_gold, 1)) * 100   # 표본이 작으니 오차를 같이 낸다
    print(f"   {k:48s} {cnt[k]:4d} = {p_*100:5.1f}%  ±{ci:4.1f}pp")
if retr_src:
    tot_r = sum(retr_src.values())
    print(f"\n   ② retriever 가 놓친 {tot_r}건의 **출처**:")
    for k in sorted(retr_src, key=lambda x: -retr_src[x]):
        print(f"     {k:20s} {retr_src[k]:4d} = {retr_src[k]/tot_r*100:5.1f}%"
              f"   (전체 대비 {retr_src[k]/max(n_gold,1)*100:4.1f}%)")
for tag, title in (("retr", "② retriever 가 놓친 예"),
                   ("same", "③a 같은 프로젝트인데 풀에 없는 예"),
                   ("other", "③b 다른 프로젝트에만 있는 예"),
                   ("out", "④ 데이터셋 밖 예")):
    if ex[tag]:
        print(f"\n   {title}:")
        for a, b in ex[tag]:
            print(f"     · {a:30s} {b}")
