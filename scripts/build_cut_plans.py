#!/usr/bin/env python3
"""cut **계획**을 만든다 — 검색과 무관하게, lemma 를 쓰는 **모든** 스텝에 대해.

## 옛 방식이 왜 틀렸나

`build_cuts.py` 는 생성 시점에 `structural_scores` 를 돌려 "gold 가 프롬프트에
들어가나" 를 판정하고, **안 들어갈 때만** cut 을 만들었다. 그러면 검색 정책이
cut 파일에 박힌다. 검색을 바꾸면(우리는 지금 structural → afh80 으로 바꾸는 중이다)

    structural 은 놓쳤는데 새 검색은 찾음 → 불필요한 cut (낭비, 안전)
    structural 은 찾았는데 새 검색은 놓침 → **cut 이 없어 환각 학습**  ★

두 번째가 위험하고, 검색을 바꿀 때마다 5시간짜리 재생성이 필요했다.

## 새 방식

여기서는 **사실만** 기록한다. 결정은 학습 시점에 **실제 프롬프트**를 보고 한다.

    {"kind":"plan","sid":…,"tac":"apply foo","lem":[["foo","forall n, …"]],"fn":["bar"]}

  · `lem`  이 스텝이 쓰는 **명제** gold 와 그 statement
  · `fn`   함수·타입·생성자 이름 (cut 으로 못 고친다)
  · `tac`  원래 gold tactic

학습 시점: 프롬프트를 만든 뒤 `lem` 중 **안 보이는 것**만 골라 그것들만 assert 한다.
검색을 바꿔도 이 파일은 그대로 쓴다.

## 검색과 무관하게 판정할 수 있는 것만 hopeless 로 찍는다

  · gold 가 **후보 풀에 아예 없다**       → 어떤 검색으로도 못 찾는다
  · statement 를 못 뽑는다(정의/본문)      → assert 를 못 만든다
  · `transform` 이 실패한다               → cut 조립 불가

사용: PYTHONPATH=src python3 scripts/build_cut_plans.py <N> <split> <out> [START]
"""
import collections
import copy
import json
import logging
import os
import re
import sys
import time

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ["CUTS_PATH"] = ""            # 자기 자신을 읽지 않는다

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "train").upper()
OUT = sys.argv[3] if len(sys.argv) > 3 else f"data/cut_plans_{SPLIT.lower()}.jsonl"
START = int(sys.argv[4]) if len(sys.argv) > 4 else 0

import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from data_management.dataset_file import DatasetFile  # noqa: E402
from data_management.sentence_db import SentenceDB  # noqa: E402
from premise_selection.premise_filter import PremiseFilter, PremiseFilterConf  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402
from tactic_gen.tier_rank import declname  # noqa: E402
from tactic_gen.assert_split import statement_of, transform  # noqa: E402
from tactic_gen.lm_example import fmt_goals  # noqa: E402

cc = yaml.safe_load(open("all_log/ft_qwen3b_v9_conf.yaml"))
tdc = copy.deepcopy(cc["tactic_data"])
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), None)
sdb = SentenceDB.load(conf.sentence_db_loc)
pf = PremiseFilterConf.from_yaml(tdc["formatter_conf"]["premise"]["premise_filter"])
pfilter = PremiseFilter(pf.coq_excludes, pf.non_coq_excludes, pf.general_excludes)

# ★ 옛 청크의 `stmt` 레코드를 **재사용**한다 — statement 추출은 검색과 무관한 사실이라
#   다시 뽑을 이유가 없다. 없는 것만 새로 뽑는다.
SEED = os.environ.get("SEED_STMTS", "data/cut_chunks_train")
seed_ty = {}
if os.path.isdir(SEED):
    for fn in sorted(os.listdir(SEED)):
        if not fn.endswith(".jsonl"):
            continue
        for ln in open(os.path.join(SEED, fn), errors="ignore"):
            try:
                d = json.loads(ln)
            except Exception:
                continue
            if d.get("kind") == "stmt" and d.get("name") and d.get("ty"):
                seed_ty.setdefault(d["name"], d["ty"])
print(f"■ cut 계획 생성  {SPLIT} [{START:,}, {START+N:,})", flush=True)
print(f"   재사용한 statement 사전: {len(seed_ty):,}개 ({SEED})", flush=True)

# ── 이름 → 선언 종류 사전 ────────────────────────────────────────────────
#   ★ 왜 필요한가: gold 이름에는 **명제**(Lemma/Theorem)와 **함수·타입·생성자**가 섞여
#     있다. 후자는 assert 대상이 아니고 **후보 풀에도 없다**(풀은 정리만 담는다) —
#     `[TYPES]`/`[DEFINITIONS]` 로 도달한다.
#     이걸 구분하지 않고 "풀에 없으면 hopeless" 라고 하면 함수 이름 하나 때문에
#     멀쩡한 스텝이 통째로 버려진다(실측: 741건 중 193건 = 26%가 그렇게 잘못 찍혔다).
#   ★ 사전은 `sentences.db` 전량 스캔(~30초)이라 청크마다 다시 만들면 낭비다.
#     한 번 만들어 JSON 으로 캐시하고 이후 청크는 읽기만 한다.
_KIND: dict = {}
_CTOR_PARENT: dict = {}
_PROVABLE = {"Lemma", "Theorem", "Corollary", "Remark", "Fact", "Proposition",
             "Property", "Axiom", "Instance"}
_DECL_HEAD = re.compile(
    r"^\s*(?:#\[[^\]]*\]\s*)?(?:Global\s+|Local\s+|Program\s+|#\[[^\]]*\]\s*)*"
    r"(Lemma|Theorem|Corollary|Remark|Fact|Proposition|Property|Definition|Fixpoint|"
    r"CoFixpoint|Inductive|CoInductive|Record|Class|Instance|Structure|Variant|"
    r"Axiom|Parameter|Hypothesis|Variable|Notation|Ltac|Let|Scheme)\b")
_CTOR_HEAD = re.compile(r"\b(Inductive|CoInductive|Variant|Record|Structure|Class)\b")
_KIND_CACHE = "data/decl_kinds.json"

if os.path.exists(_KIND_CACHE):
    with open(_KIND_CACHE) as _f:
        _d = json.load(_f)
    _KIND, _CTOR_PARENT = _d["kind"], _d["ctor"]
    print(f"   선언 종류 사전 {len(_KIND):,}개 (캐시)", flush=True)
else:
    import sqlite3
    _con = sqlite3.connect(str(conf.sentence_db_loc))
    for (_txt,) in _con.execute("select text from sentence"):
        _t = _txt or ""
        _m = _DECL_HEAD.match(_t)
        if not _m:
            continue
        _dn = declname(_t)
        if _dn and _dn not in _KIND:
            _KIND[_dn] = _m.group(1)
        if ":=" in _t and _CTOR_HEAD.search(_t.split(":=", 1)[0]):
            for _part in _t.split(":=", 1)[1].split("|"):
                _mc = re.match(r"\s*([A-Za-z_][\w']*)", _part)
                if _mc:
                    _KIND.setdefault(_mc.group(1), "Constructor")
                    if _dn:
                        _CTOR_PARENT.setdefault(_mc.group(1), _dn)
        if _CTOR_HEAD.search(_t[:40]) and "{" in _t:
            for _fld in re.finditer(r"([A-Za-z_][\w']*)\s*:(?!=)", _t[_t.index("{") + 1:]):
                _KIND.setdefault(_fld.group(1), "Field")
    _con.close()
    tmpk = _KIND_CACHE + ".tmp%d" % os.getpid()
    with open(tmpk, "w") as _f:
        json.dump({"kind": _KIND, "ctor": _CTOR_PARENT}, _f)
    os.replace(tmpk, _KIND_CACHE)
    print(f"   선언 종류 사전 {len(_KIND):,}개 (새로 만듦 → {_KIND_CACHE})", flush=True)


def _is_provable(name: str) -> bool:
    k = _KIND.get(name) or _KIND.get(name.split(".")[-1])
    return k in _PROVABLE


_ASSERT = re.compile(r"^\s*e?assert\s*\(")
_EXACT = re.compile(r"exact\s+@?([\w\'.]+?)\s*[.)]")
_EVAR = re.compile(r"(?<![\w])\?[A-Za-z_]")


def _cut_bad(cut, names) -> str:
    """cut 이 **쓸 수 있는 형태**인가. 문제가 있으면 그 이유를, 없으면 빈 문자열.

    ★ 여기서 하는 것은 **정적 검사**다 — 빠르고 전량에 걸 수 있다.
      원본 .v 는 `/tmp/coq-dataset/repos` 에 대부분 있으므로(표본 ~81%) TRAIN 도
      Coq 동적 검증이 **가능하다**. 다만 스텝당 ~25s 라 전량은 무리이므로
      표본으로 성공률을 재고(`hunt_assert_errors.py`), 전량은 이 정적 검사로 거른다.
      정적 검사를 통과해도 Coq 이 거부할 수 있다 — 여기서 걸리는 것은
      **확실히** 못 쓰는 것들이다.
    """
    if not cut or not isinstance(cut, str):
        return "cut 조립 실패"
    if not _ASSERT.match(cut):
        return "assert 로 시작하지 않음"
    if cut.count("(") != cut.count(")"):
        return "괄호 불일치"
    if cut.count("{") != cut.count("}"):
        return "중괄호 불일치"
    if "as H_asrt" not in cut:
        return "as H_asrt 없음"
    ex = [n.split(".")[-1] for n in _EXACT.findall(cut)]
    ex = [n for n in ex if not n.startswith("H_asrt")]
    if not ex:
        return "exact 대상 없음"
    miss = [n for n in names if n not in ex]
    if miss:
        return "exact 에 gold 가 빠짐"
    # `?x` 는 evar — assert 문에 들어가면 Coq 이 거부한다(eassert 면 허용)
    head = cut.split(" as ", 1)[0]
    if _EVAR.search(head) and not head.lstrip().startswith("eassert"):
        return "assert 문에 evar"
    return ""


st = collections.Counter()
why = collections.Counter()
seen_ty = {}
TMP = OUT + ".building"
fo = open(TMP, "w")
t0 = time.time()

# ★★ `ds.raw_example(i)` 를 쓰지 않는다.
#   그 함수는 premise 검색과 유사증명 검색을 **전부 수행**한다(스텝당 ~0.9s).
#   계획 생성에 필요한 것은 `tac`·`state`·`script` 셋뿐이고, 전부 `DatasetFile` 에서
#   바로 읽힌다 — `lm_example.example_from_step` 이 하는 것과 같은 방식이다.
#   (이걸 몰라서 전량 견적이 11시간으로 나왔다. 검색을 빼면 1/10 이하다.)
for i in range(START, min(START + N, len(ds))):
    sid = ds.shuffled_idx.get_idx(ds.split, i)
    try:
        dp = DatasetFile.load(conf.data_loc / "data_points" / sid.file, sdb)
        proof = dp.proofs[sid.proof_idx]
        step = proof.steps[sid.step_idx]
    except Exception:
        st["DatasetFile 로드 실패"] += 1
        continue
    tac = (step.step.text or "").strip()
    state = fmt_goals(step.goals)
    script = proof.proof_prefix_to_string(step)
    fpath = str(dp.file_context.file).split("/coq-dataset/", 1)[-1]
    key = f"{fpath}:{sid.proof_idx}:{sid.step_idx}"

    names = gold_lemmas(tac, local_names(state))
    if not names:
        st["gold 이름 없음 (cut 무관)"] += 1
        continue
    st["gold 사용 스텝"] += 1
    pool = [p for p in dp.get_premises_before(proof) if pfilter.filter_premise(p)]
    txt = {}
    for p in pool:
        t = getattr(p, "text", "") or ""
        nm = declname(t)
        if nm and nm not in txt:
            txt[nm] = t

    lem, fn, miss_pool = [], [], []
    for g in names:
        b = g.split(".")[-1]
        # ★★ 판정은 **이 프로젝트 풀에서 찾은 실제 원문**으로 한다.
        #   전역 종류 사전(`_KIND`)은 bare name 으로 만들어져 **프로젝트 간 이름이
        #   충돌한다**: 어느 프로젝트의 `Axiom union` 때문에 이 프로젝트의
        #   `Definition union := …` 이 '명제'로 분류되고, statement 추출에 실패해
        #   hopeless 로 떨어졌다(실측). 반대 방향 오분류도 같은 이유로 생긴다.
        #   원문이 있으면 원문이 진실이다 — 사전은 **원문이 없을 때만** 참고한다.
        pt = txt.get(g) or txt.get(b)
        if pt is not None:
            ty = seed_ty.get(b) or seen_ty.get(b) or statement_of(pt)
            if not ty:
                # 명제가 아니다(본문 있는 정의 등) → 함수 이름으로 본다.
                #   assert 할 명제가 없을 뿐이고, 이름은 [DEFINITIONS] 로 도달한다.
                #   여기서 hopeless 로 찍으면 **멀쩡한 스텝을 버리게 된다.**
                fn.append(b)
                continue
        else:
            # 풀에 없다 — 사전으로 명제인지 짐작한다.
            #   명제가 아니면 함수·타입·생성자이고, 그건 풀에 없는 것이 정상이다.
            if not _is_provable(b):
                fn.append(b)
                continue
            miss_pool.append(g)                      # 명제인데 풀에 없다 — 검색 무관
            continue
        if b not in seen_ty and b not in seed_ty:
            seen_ty[b] = ty
            fo.write(json.dumps({"kind": "stmt", "name": b, "ty": ty},
                                ensure_ascii=False) + "\n")
        lem.append([b, ty])

    if miss_pool:
        st["★ gold 가 풀에 없음 → hopeless"] += 1
        why["gold 가 풀에 없음"] += 1
        fo.write(json.dumps({"kind": "step", "sid": key, "hopeless": True,
                             "why": "gold 가 풀에 없음", "miss": miss_pool},
                            ensure_ascii=False) + "\n")
        continue
    if not lem:
        st["명제 gold 없음 (함수 이름뿐)"] += 1
        if fn:
            fo.write(json.dumps({"kind": "plan", "sid": key, "tac": tac,
                                 "lem": [], "fn": fn}, ensure_ascii=False) + "\n")
        continue

    # ★ **전부 assert 하는 최악의 경우**로 cut 을 실제로 만들어 둔다.
    #   부분집합은 더 쉬우므로, 이게 되면 학습 시점의 어떤 부분집합도 된다.
    #   그리고 만든 것을 **그대로 저장**한다 — 나중에 사람이 열어 볼 수 있어야 하고,
    #   검증기가 형태를 검사할 수 있어야 한다.
    cut = transform(tac, [(nm, f"Lemma {nm} : {ty}.") for nm, ty in lem],
                    proof_script=script, state=state)
    bad = _cut_bad(cut, [n for n, _ in lem])
    if bad:
        st[f"★ cut 실패 → hopeless"] += 1
        why[bad] += 1
        fo.write(json.dumps({"kind": "step", "sid": key, "hopeless": True,
                             "why": bad, "miss": [n for n, _ in lem]},
                            ensure_ascii=False) + "\n")
        continue

    st["계획 기록"] += 1
    fo.write(json.dumps({"kind": "plan", "sid": key, "tac": tac,
                         "lem": lem, "fn": fn, "cut": cut},
                        ensure_ascii=False) + "\n")

    if st["gold 사용 스텝"] % 200 == 0:
        el = time.time() - t0
        print(f"   계획 {st['계획 기록']}  ({el:.0f}s)", flush=True)

fo.write(json.dumps({"kind": "meta", "split": SPLIT, "scan_start": START,
                     "scan_end": min(START + N, len(ds)),
                     "mode": "plan"}, ensure_ascii=False) + "\n")
fo.close()
os.replace(TMP, OUT)

print(f"\n■ 결과 ({time.time()-t0:.0f}s)")
for k, v in st.most_common():
    print(f"   {k:44s} {v:8,}")
if why:
    print("\n■ hopeless 이유")
    for k, v in why.most_common():
        print(f"   [{v:7,}] {k}")
print(f"\n→ {OUT}  (새 statement {len(seen_ty):,}개)")
