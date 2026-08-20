#!/usr/bin/env python3
"""★ cut 을 **미리 만들어 파일로** 저장한다 — 학습 머신(Vast.ai)에 Coq 이 없어도 되게.

## 용어

  · **cut**   증명에서 보조 명제를 세워 쓰는 것. Coq 에서는 `assert (P) as H`.
              논리학의 cut rule 과 같다. gold tactic 이 쓰는 lemma L 이 검색 결과에
              없으면, L 과 **같은 명제** L' 을 cut 으로 세우고 그것을 쓴다.
  · **gold tactic**  데이터셋의 정답 tactic.
  · **gold lemma**   그 tactic 이 참조하는 lemma.
  · **검색 실패**    gold lemma 가 프롬프트에 들어가는 상위 N 개 안에 없는 것.

## 왜 미리 만드나

cut 의 명제를 정확히 얻으려면 그 증명 지점에서 Coq 에 `Check (L a b).` 를 물어야 한다
(암묵인자·Section 변수가 인스턴스화된 형태가 나온다). Vast.ai 학습 머신에는 Coq 이 없고
opam 환경을 새로 만드는 것은 느리고 불안정하다. → **여기서 만들어 파일로 넘긴다.**

## 2단계 전략 (비용)

  ① **Coq 없는 경로**  `sentences.db` 의 premise 원문에서 명제를 뽑는다(`statement_of`).
                       인스턴스화가 안 돼 품질은 낮지만 **즉시** 만들어진다.
  ② **Coq 경로**       ①이 실패한 것만. 파일 단위로 묶어 한 번의 elaboration 으로
                       그 파일의 여러 지점을 처리한다(스텝마다 열면 10배 느리다).

이 스크립트는 ①만 한다(②는 `build_cuts_coq.py`). ①의 성공률을 보고 ②의 규모를 정한다.

## 출력 형식 (중복 제거)

같은 lemma 가 여러 스텝에서 빠지면 명제가 같다 → **사전 하나 + 스텝별 이름 목록**.

    {"kind":"stmt", "name":"Nat.add_comm", "ty":"forall n m : nat, n + m = m + n"}
    {"kind":"step", "sid":"파일#증명#스텝", "miss":["Nat.add_comm"], "tac":"rewrite ..."}

사용: python3 scripts/build_cuts.py [훑을 예제수] [train|val|test] [out.jsonl]
"""
import collections
import copy
import json
import re
import os
import sys
import time

# ★ 위험 필터를 기본으로 끈다. B 실측에서 필터별 실패율이 0~40% 라 막는 것보다
#   통과시키고 Coq 으로 검증해 거르는 편이 훨씬 많이 건진다.
#   ★★ 반드시 **import 보다 먼저** — assert_split 이 import 시점에 이 값을 읽는다.
#      (뒤에 두면 조용히 무시되고 SSReflect 가 전부 막힌다 — 실측으로 당했다)
os.environ.setdefault("ASSERT_RISK", "0")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import yaml  # noqa: E402
from data_management.splits import Split  # noqa: E402
from data_management.dataset_file import (DatasetFile, get_ids_from_goal,  # noqa: E402
                                          get_ids_from_sentence)
from data_management.sentence_db import SentenceDB  # noqa: E402
from proof_retrieval.tfidf import tf_idf  # noqa: E402
from premise_selection.premise_filter import PremiseFilter, PremiseFilterConf  # noqa: E402
from tactic_gen.tactic_data import TacticDataConf, LmDataset  # noqa: E402
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402
from tactic_gen.search_query import local_names  # noqa: E402
from tactic_gen.tier_rank import declname, structural_scores  # noqa: E402
from tactic_gen.assert_split import statement_of, transform  # noqa: E402
from tactic_gen.applicable import decompose  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
SPLIT = (sys.argv[2] if len(sys.argv) > 2 else "train").upper()
OUT = sys.argv[3] if len(sys.argv) > 3 else f"data/cuts_{SPLIT.lower()}.jsonl"
# ★ cut 대상 판정은 **검색 순위**가 아니라 **프롬프트에 실제로 들어가는가** 다.
#   `whole_number_allocate` 는 앞에서부터 담다가 예산이 넘으면 break 한다.
#   실측: 검색이 넘긴 100개 중 17~23개만 들어간다(길이 최소 16 · 중앙 147 · 최대 928 토큰).
#   순위 기준으로 재면 "검색은 됐는데 프롬프트엔 없는" 스텝을 통째로 놓친다.
BUDGET = int(os.environ.get("PREMISE_TOKENS", "896"))
from transformers import AutoTokenizer  # noqa: E402
_TOK = AutoTokenizer.from_pretrained(
    yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))["model_name"])
_TL: dict = {}



# ── cut 품질 게이트 ───────────────────────────────────────────────────────
#  ★ 예전에는 `cut_tac[:800]` 로 **잘랐다**. 잘린 assert 는 Coq 문법이 깨져서
#    학습이 깨진 문자열을 외운다. 자르지 말고 **버린다**(→ hopeless 로 떨어져
#    gold tactic + 정규화 OFF 로 학습된다).
_CUT_TOK = None


def _cut_ok(c: str) -> bool:
    """cut 이 학습에 넣어도 되는 형태인가."""
    import re as _re
    if not _re.match(r"^e?assert\s*\(", c):
        return False
    if not _re.search(r"\bas\s+H_asrt[a-z]*\d+\s*\.", c):
        return False   # 이름표가 없다 = 문장이 잘렸다
    if "{" not in c or "}" not in c:
        return False   # 증명 블록이 없다 = 잘렸다
    if c.count("(") != c.count(")"):
        return False   # 괄호 불균형 = 잘렸다
    # 출력 예산(out_tokens) 을 넘으면 collator 가 라벨을 잘라 깨뜨린다
    global _CUT_TOK
    if _CUT_TOK is None:
        try:
            from transformers import AutoTokenizer
            _CUT_TOK = AutoTokenizer.from_pretrained(
                os.environ.get("CUT_TOKENIZER", "Qwen/Qwen2.5-Coder-3B-Instruct"))
        except Exception:
            _CUT_TOK = False
    if _CUT_TOK:
        lim = int(os.environ.get("CUT_MAX_TOKENS", "128"))
        if len(_CUT_TOK.tokenize(c)) > lim:
            return False
    return True



# ── 선언 종류 사전 — cut 대상인 이름과 아닌 이름을 가른다 ────────────────────
#  ★ 왜 필요한가.  `gold_lemmas` 는 tactic 에서 **전역 이름**을 뽑는데, 그중에는
#    lemma 가 아니라 **함수·타입**이 섞인다(`unfold closure2`, `destruct (eq_dec a b)`,
#    `rewrite -/(app [a] _)`).  실측: need_coq 1,149개 중 1,054개(91.7%)가
#    Definition/Fixpoint 였다.
#
#    함수는 **명제가 아니라 assert 할 수 없다.**  게다가 후보 풀은 설계상
#    `PROJ_THM_FILTER_CONF` 가 DEFINITION·FIXPOINT·INDUCTIVE·RECORD·CLASS 를 전부
#    제외하므로 **함수 이름은 애초에 풀에 없다.**  그걸 "검색 실패"로 세면
#    고칠 수 없는 것을 고치려 드는 셈이다.
#
#    함수 이름은 검색이 아니라 goal 본문 · [TYPES] · [DEFS] 주입으로 모델에 도달한다.
#    그래서 여기서는 **명제인 이름만** cut 판정에 쓰고, 함수 이름은 goal 에 보이는지만
#    확인한다(안 보이면 그때는 진짜 가망 없음).
_PROVABLE = {
    "Lemma", "Theorem", "Corollary", "Proposition", "Fact", "Remark", "Property",
    "Axiom", "Parameter", "Hypothesis", "Variable", "Instance",
}
_DECL_HEAD = re.compile(
    r"^\s*(?:#\[[^\]]*\]\s*)?"
    r"(?:Global\s+|Local\s+|Program\s+|Polymorphic\s+|Monomorphic\s+|#\[global\]\s*)*"
    r"(Lemma|Theorem|Corollary|Proposition|Fact|Remark|Property|Definition|Fixpoint|"
    r"CoFixpoint|Inductive|CoInductive|Record|Class|Instance|Structure|Variant|"
    r"Axiom|Parameter|Hypothesis|Variable|Notation|Ltac|Let|Scheme)\b")
_KIND: dict = {}
_CTOR_PARENT: dict = {}   # 생성자 → 그것을 정의한 타입 (예: S → nat)


_CTOR_HEAD = re.compile(r"\b(Inductive|CoInductive|Variant|Record|Structure|Class)\b")


def _load_kinds(db_path) -> None:
    """`sentences.db` 전체를 훑어 이름 → 선언 종류 사전을 만든다(약 30초).

    ★ 선언 이름뿐 아니라 **생성자**도 넣는다.  `S`(nat) · `I`(True) · `eq_refl`(eq) ·
      `Zpos`(Z) · `Acc_intro`(Acc) 같은 것들이다.  이들은 lemma 가 아니고 후보 풀에도
      없다(풀은 정리만 담는다) — `[TYPES]` 로 Inductive 선언 전체가 주입되어 도달한다.
      생성자를 lemma 로 오인하면 "검색 실패"로 세어 고칠 수 없는 것을 고치려 든다.
    """
    import sqlite3
    con = sqlite3.connect(str(db_path))
    for (txt,) in con.execute("select text from sentence"):
        t = txt or ""
        m = _DECL_HEAD.match(t)
        if not m:
            continue
        d = declname(t)
        if d and d not in _KIND:
            _KIND[d] = m.group(1)
        # 생성자 추출 — `Inductive T := A | B : … | C : …`
        if ":=" in t and _CTOR_HEAD.search(t.split(":=", 1)[0]):
            for part in t.split(":=", 1)[1].split("|"):
                mc = re.match(r"\s*([A-Za-z_][\w']*)", part)
                if mc:
                    _KIND.setdefault(mc.group(1), "Constructor")
                    if d:
                        _CTOR_PARENT.setdefault(mc.group(1), d)
        # Record/Class 필드도 사영함수라 lemma 가 아니다 — `{ f1 : T; f2 : T }`
        if _CTOR_HEAD.search(t[:40]) and "{" in t:
            body = t[t.index("{") + 1:]
            for fld in re.finditer(r"([A-Za-z_][\w']*)\s*:(?!=)", body):
                _KIND.setdefault(fld.group(1), "Field")
    con.close()


def _is_provable(name: str) -> bool:
    """이 이름이 **명제**인가(= assert 대상이 될 수 있는가).

    ★ 사전에 **없으면 명제가 아니라고 본다.**  `sentences.db` 는 전 파일의 모든 문장을
      담으므로, 거기 선언이 없는 이름은 전역 이름이 아니다 — 지역 가설(`HH`)이거나
      `gold_lemmas` 의 오추출이다.  그런 이름을 "검색 실패"로 세면 고칠 수 없는 것을
      고치려 든다.  대신 **프롬프트에 보이는지**를 따로 확인하므로(아래 fn_unseen),
      정말 못 읽는 이름은 그때 가망 없음으로 잡힌다 — 놓치지 않는다.
    """
    k = _KIND.get(name)
    if k is None:
        k = _KIND.get(name.split(".")[-1])
    return k in _PROVABLE


def _tlen(t: str) -> int:
    v = _TL.get(t)
    if v is None:
        v = len(_TOK.tokenize(t))
        _TL[t] = v
    return v


def n_in_prompt(texts, order) -> int:
    """랭킹 순서대로 담았을 때 프롬프트에 들어가는 개수."""
    left, k = BUDGET, 0
    for j in order:
        left -= _tlen(texts[j])
        if left < 0:
            break
        k += 1
    return k

cc = yaml.safe_load(open("all_log/ft_qwen3b_v8_conf.yaml"))
tdc = copy.deepcopy(cc["tactic_data"])
tdc["formatter_conf"].pop("proof_ret", None)
tdc["formatter_conf"].pop("num_proofs", None)
conf = TacticDataConf.from_yaml(tdc)
ds = LmDataset.from_conf(conf, getattr(Split, SPLIT), 10 ** 9)
sdb = SentenceDB.load(conf.sentence_db_loc)
pf = PremiseFilterConf.from_yaml(tdc["formatter_conf"]["premise"]["premise_filter"])
pfilter = PremiseFilter(pf.coq_excludes, pf.non_coq_excludes, pf.general_excludes)

class _G:
    def __init__(self, g, h):
        self.goal, self.hyps = g, h


st = collections.Counter()
fail_why = collections.Counter()
stmts: dict[str, str] = {}
need_coq: list[dict] = []
# ★ 선언 종류 사전을 먼저 만든다(약 20초). 이게 없으면 함수 이름을 lemma 로 오인한다.
print("   선언 종류 사전 로딩…", flush=True)
_load_kinds(conf.sentence_db_loc)
print(f"   선언 종류 사전 {len(_KIND):,}개", flush=True)

t0 = time.time()
# ★ 원자적 쓰기 — 도중에 읽히면 반쪽 파일을 학습에 쓰게 된다(실측으로 당했다).
#   임시 이름으로 쓰고 **끝나면** 제자리로 옮긴다.
TMP = OUT + ".building"
fo = open(TMP, "w")

for i in range(min(N, len(ds))):
    try:
        e = ds.raw_example(i)
    except Exception:
        continue
    state = getattr(e, "proof_state", "") or ""
    tac = (e.next_steps[0] if getattr(e, "next_steps", None) else "").strip()
    golds_all = gold_lemmas(tac, local_names(state))
    if not golds_all:
        continue
    # ★ 명제인 이름만 cut 판정에 쓴다(§ _is_provable).  함수·타입 이름은 검색 대상이
    #   아니라 goal/[TYPES]/[DEFS] 로 도달한다 — goal 에 보이는지만 확인한다.
    golds = [g for g in golds_all if _is_provable(g)]
    fn_names = [g for g in golds_all if g not in golds]
    # 함수·타입·생성자가 **프롬프트에서 읽히는가**.
    #   ★ goal 만 보면 너무 엄격하다 — 프롬프트에는 [SCRIPT](지금까지의 증명)와
    #     [PREMISES] 도 들어간다.  실측: goal 만 볼 때 '안 보임' 170건이 대부분
    #     [SCRIPT] 나 premise 본문에서 읽혔다.
    #   · 이름 자체가 goal/가설/증명스크립트에 나오면 읽힌다
    #   · 생성자는 **부모 타입**이 나오면 [TYPES] 주입으로 선언 전체가 따라온다
    #     (`S` 는 안 보여도 `nat` 이 보이면 `Inductive nat := O | S …` 가 주입된다)
    #   · 프롬프트에 실제로 들어가는 premise 본문(아래 `_fit_text`)에 나와도 읽힌다
    _script = getattr(e, "proof_script", "") or ""
    _seen_txt = state + "\n" + _script

    def _visible(g: str, extra: str = "") -> bool:
        b = g.split(".")[-1]
        hay = _seen_txt + extra
        if re.search(r"(?<![\w'])" + re.escape(b) + r"(?![\w'])", hay):
            return True
        par = _CTOR_PARENT.get(g) or _CTOR_PARENT.get(b)
        return bool(par and re.search(r"(?<![\w'])" + re.escape(par) + r"(?![\w'])", hay))

    fn_unseen0 = [g for g in fn_names if not _visible(g)]
    if fn_names:
        st["함수·타입 이름 (cut 대상 아님)"] += len(fn_names)
    # ★ 여기서 끝내지 않는다. 프롬프트에 실제로 들어가는 premise 본문에도 이름이 나올 수
    #   있으므로, 랭킹까지 계산한 뒤(_fit_text) 다시 본다. 아래 `_finish_fn()` 참조.
    _fn_only = not golds
    if _fn_only and not fn_unseen0:
        # 명제도 없고 함수 이름도 전부 읽힌다 → 아무 문제 없다.
        st["명제 없음(함수 이름뿐) → cut 무관"] += 1
        continue
    if not _fn_only:
        st["gold 사용 스텝"] += 1
    sid = ds.shuffled_idx.get_idx(ds.split, i)
    try:
        dp = DatasetFile.load(conf.data_loc / "data_points" / sid.file, sdb)
        proof = dp.proofs[sid.proof_idx]
        step = proof.steps[sid.step_idx]
    except Exception:
        continue
    if not step.goals:
        continue
    pool = [p for p in dp.get_premises_before(proof) if pfilter.filter_premise(p)]
    if not pool:
        continue
    texts = [getattr(p, "text", "") or "" for p in pool]
    names = [declname(t) for t in texts]
    gset = {j for j, nm in enumerate(names) if nm and nm in golds}
    _key0 = (f"{getattr(e, 'file_name', '')}:"
             f"{getattr(e, 'proof_idx', '')}:{getattr(e, 'step_idx', '')}")
    if not gset and not _fn_only:
        # ★ gold 가 후보 풀에 아예 없다 → cut 도 못 만든다(how-to-learn §3 의 (3)).
        #   이런 스텝은 학습에서 뺀다(CUT_DROP_HOPELESS) — 정답이 프롬프트에 없는
        #   이름을 쓰므로, 넣으면 *볼 수 없는 이름을 지어내라*고 가르치는 셈이다.
        st["gold 가 풀에 없음"] += 1
        fo.write(json.dumps({"kind": "step", "sid": _key0, "hopeless": True,
                             "why": "gold 가 풀에 없음",
                             "miss": list(golds)}, ensure_ascii=False) + "\n")
        continue

    docs = [get_ids_from_sentence(p) for p in pool]
    h_ids, g_ids = get_ids_from_goal(step.goals[0])
    tf = tf_idf(h_ids + g_ids, docs)
    gl = state.split("\n\n")[-1] if "\n\n" in state else state
    hy = state.split("\n\n")[0].split("\n") if "\n\n" in state else []
    try:
        sc = structural_scores(gl, hy, texts, tf, query_ids=h_ids + g_ids, docs=docs)
    except Exception:
        sc = tf
    o = sorted(range(len(pool)), key=lambda j: -sc[j])
    nfit = n_in_prompt(texts, o)          # ★ 프롬프트에 들어가는 개수
    pos = {j: r for r, j in enumerate(o)}

    # ★ 프롬프트에 실제로 들어가는 premise 본문 — 함수 이름이 여기 나오면 읽힌다.
    _fit_text = "\n".join(texts[j] for j in o[:nfit])
    fn_unseen = [g for g in fn_names if not _visible(g, _fit_text)]
    if fn_unseen:
        st["  └ 그중 프롬프트에 안 보임"] += len(fn_unseen)
    if _fn_only:
        # 명제는 없고 함수 이름뿐인 스텝. 여기서 결론 낸다.
        st["명제 없음(함수 이름뿐) → cut 무관"] += 1
        if fn_unseen:
            st["  └ ★ 가망 없음(함수 이름이 안 보임)"] += 1
            fo.write(json.dumps({"kind": "step", "sid": _key0, "hopeless": True,
                                 "why": "함수·타입 이름이 프롬프트에 없음",
                                 "miss": fn_unseen}, ensure_ascii=False) + "\n")
        continue
    if fn_unseen:
        # 명제는 있는데 **함수 이름**이 안 보인다 → cut 을 만들어도 그 이름은 못 읽는다.
        st["명제는 되지만 함수 이름이 안 보임 → 가망 없음"] += 1
        fo.write(json.dumps({"kind": "step", "sid": _key0, "hopeless": True,
                             "why": "함수·타입 이름이 프롬프트에 없음",
                             "miss": fn_unseen}, ensure_ascii=False) + "\n")
        continue

    per_name: dict = {}
    for j in gset:
        per_name.setdefault(names[j], []).append(j)
    missing = [nm for nm, js in per_name.items() if min(pos[j] for j in js) >= nfit]
    if not missing:
        st["검색 성공 → cut 불필요"] += 1
        continue
    st["cut 필요 스텝"] += 1

    ok_names, bad_names = [], []
    for nm in missing:
        j = per_name[nm][0]
        if nm in stmts:
            ok_names.append(nm)
            continue
        s_ = statement_of(texts[j])
        if s_:
            stmts[nm] = s_
            ok_names.append(nm)
            st["① Coq 없이 명제 확보"] += 1
        else:
            bad_names.append(nm)
            st["② Coq 필요"] += 1
    # cut 문장을 실제로 조립해 본다 (문법이 서는지 — 여기서 실패하면 학습에 못 쓴다)
    cut_tac = None
    if ok_names and not bad_names:
        try:
            import tactic_gen.assert_split as _AS
            _AS.WHY.clear()
            cut_tac = transform(tac, [(nm, texts[per_name[nm][0]]) for nm in ok_names],
                                proof_script=getattr(e, "proof_script", "") or "",
                                state=state, premises=texts[:200])
            A_WHY = list(_AS.WHY)
        except Exception as ex:
            cut_tac = None
            A_WHY = [f"예외 {type(ex).__name__}"]
        st["cut tactic 조립 성공" if cut_tac else "cut tactic 조립 실패"] += 1
        if not cut_tac:
            for _w in (A_WHY or ["이유 미기록"]):
                fail_why[_w] += 1
    # ★ 키는 **collate 가 계산할 수 있는 형태**여야 한다.
    #   sid.file 은 평탄화된 이름(`a-b-c.v`)이고 example.file_name 은 원경로
    #   (`repos/a/b/c.v`)라 서로 다르다. collate 에는 file_name 만 있으므로 그쪽에 맞춘다.
    _key = (f"{getattr(e, 'file_name', '')}:"
            f"{getattr(e, 'proof_idx', '')}:{getattr(e, 'step_idx', '')}")
    # ★ cut 을 만들어도 **그 L' 를 goal 로 재검색했을 때 L 이 안 잡히면 소용이 없다.**
    #   (how-to-learn.txt §3) 그런 스텝은 cut 을 내보내지 않는다 → 학습은 원래 gold
    #   tactic 을 쓰고 환각을 감수한다. 여기서 걸러야 쓸모없는 cut 을 학습시키지 않는다.
    if cut_tac:
        for nm in ok_names:
            j0 = per_name[nm][0]
            d0 = decompose(texts[j0])
            if d0 is None:
                cut_tac = None
                fail_why["재검색: L' 명제를 못 만듦"] += 1
                break
            q = " ".join(d0[2])
            _, qi = get_ids_from_goal(_G(q, []))
            tf2 = tf_idf(qi, docs)
            try:
                sc2 = structural_scores(q, hy, texts, tf2, query_ids=qi, docs=docs)
            except Exception:
                sc2 = tf2
            o2 = sorted(range(len(pool)), key=lambda x: -sc2[x])
            nfit2 = n_in_prompt(texts, o2)     # ★ cut 후에도 프롬프트 기준
            p2 = {x: r for r, x in enumerate(o2)}
            if min(p2[x] for x in per_name[nm]) >= nfit2:
                cut_tac = None
                st["cut 해도 재검색 실패 → gold 유지"] += 1
                fail_why["재검색 실패(L' 로도 L 이 안 잡힘)"] += 1
                break
        if cut_tac:
            st["★ cut 유효(재검색 성공)"] += 1

    rec = {"kind": "step", "sid": _key,
           "miss": missing, "have": ok_names, "need_coq": bad_names,
           "tac": tac[:400]}
    if cut_tac and _cut_ok(cut_tac):
        rec["cut"] = cut_tac
    else:
        # ★ cut 을 못 만들었거나 만들어도 재검색이 안 된다 → 가망 없음.
        rec["hopeless"] = True
    fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if bad_names:
        need_coq.append(rec)
    if st["cut 필요 스텝"] % 200 == 0:
        print(f"   … cut {st['cut 필요 스텝']} ({time.time()-t0:.0f}s)", flush=True)

for nm, ty in stmts.items():
    fo.write(json.dumps({"kind": "stmt", "name": nm, "ty": ty},
                        ensure_ascii=False) + "\n")
fo.close()
os.replace(TMP, OUT)

print(f"\n■ {SPLIT} — cut 사전생성 ① Coq 없는 경로  ({time.time()-t0:.0f}s)")
print(f"   ★ 판정 기준: 프롬프트 포함(예산 {BUDGET}토큰) — 검색 순위 아님")
for k in ("gold 사용 스텝", "gold 가 풀에 없음", "검색 성공 → cut 불필요", "cut 필요 스텝",
          "함수·타입 이름 (cut 대상 아님)", "  └ 그중 프롬프트에 안 보임",
          "명제는 되지만 함수 이름이 안 보임 → 가망 없음",
          "명제 없음(함수 이름뿐) → cut 무관", "  └ ★ 가망 없음(함수 이름이 안 보임)",
          "① Coq 없이 명제 확보", "② Coq 필요", "cut tactic 조립 성공",
          "cut tactic 조립 실패"):
    print(f"   {k:26s} {st[k]:7d}")
c = max(st["① Coq 없이 명제 확보"] + st["② Coq 필요"], 1)
print(f"\n   ■ 3단계 판정 (how-to-learn.txt)")
print(f"     ① 검색 성공 → gold tactic 그대로   {st['검색 성공 → cut 불필요']:6d}")
print(f"     ② cut 유효  → cut 으로 치환        {st['★ cut 유효(재검색 성공)']:6d}")
print(f"     ③ cut 해도 재검색 실패 → gold 유지  {st['cut 해도 재검색 실패 → gold 유지']:6d}"
      f"   (환각 감수)")
print(f"\n   ① 만으로 명제를 얻은 비율   {st['① Coq 없이 명제 확보']/c*100:5.1f}%")
print(f"   ② Coq 이 필요한 스텝        {len(need_coq)}")
# ★ 분모를 정확히: Coq 이 필요한 스텝은 애초에 **조립을 시도하지 않는다**.
tried = st["cut tactic 조립 성공"] + st["cut tactic 조립 실패"]
n_cut = max(st["cut 필요 스텝"], 1)
print(f"\n   조립 시도               {tried}  (Coq 필요분 {n_cut - tried} 제외)")
print(f"   조립 성공률(시도분)      {st['cut tactic 조립 성공']/max(tried,1)*100:5.1f}%")
print(f"   cut 확보율(전체 대비)    {st['cut tactic 조립 성공']/n_cut*100:5.1f}%")
if fail_why:
    print(f"\n   ■ 조립 실패 이유")
    for k, v in fail_why.most_common(10):
        print(f"     [{v:5d}] {k}")
sz = os.path.getsize(OUT)
print(f"\n   → {OUT}  ({sz/1e6:.1f} MB · 고유 명제 {len(stmts)})")
