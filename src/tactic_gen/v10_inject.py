"""v10 — **gold lemma 를 프롬프트에 끼워 넣어** 조립을 가르친다.

## 왜 바꾸나

v9 는 gold lemma 가 검색에 안 잡히면 `assert (P) as H` 로 **명제를 세우는 법**을
가르쳤다(cut/CUT_SUBSTEP). 실측 결과 그게 독이었다:

  · 모델이 만든 assert 의 절반 이상이 **gold lemma 명제의 재진술**이다
    (선언문 토큰 커버리지 중앙 43%, 상위 17.5% 는 80% 이상, 여러 건 100% 일치).
  · 그런데 세운 명제를 **스스로 못 닫는다** — 이름을 몰라서 세운 것이니 당연하다.
    rand200 실측: assert 뒤 close 의 99.8% 가 "name not found" 로 INVALID.
  · 결국 `assert` 는 **이름을 모를 때 빠져나갈 구멍**이 됐다. 구멍이 없었으면
    틀린 이름이라도 시도했을 텐데, 구멍이 있으니 명제를 베끼고 만다.

오라클 실험이 가리키는 곳은 하나다 — **이름만 정해 주면 70~74% 는 조립한다.**
못하는 것은 조립이 아니라 **고르기**다. 그러면 학습에서 할 일은
"고를 것이 반드시 거기 있는" 예제를 주는 것이다.

## v10 알고리즘

    (1) 이 스텝이 **외부 참조를 안 쓴다**            → 그대로 fine-tuning
    (2) 외부 참조를 쓴다
        (2-a) gold lemma 가 **이미 프롬프트에 보인다**  → 그대로 fine-tuning
              (잘못된 게 아니다 — 검색이 제 일을 한 예제다)
        (2-b) gold lemma 가 **안 보인다**              → 프롬프트에 실리는 premise
              중 하나를 **무작위로 빼고** 그 자리에 gold 선언문을 끼운다

(2-b) 가 핵심이다. 정답이 항상 프롬프트 안에 있으므로 모델이 배우는 것은
**"주어진 목록에서 맞는 것을 골라 인자를 조립한다"** 하나로 좁혀진다.
검색이 못 찾는 문제는 학습이 아니라 검색에서 풀 일이다.

## 빼는 대상을 왜 "실리는 것 중에서" 고르나

`example.premises` 는 100개지만 프롬프트 예산(`premise_tokens`, 기본 896)에
실제로 담기는 것은 ~25개다. 목록 뒤쪽에서 빼면 **아무것도 안 바뀐다** —
어차피 안 실리던 것이다. 반드시 `whole_number_allocate` 가 고른 인덱스
안에서 빼야 한 자리가 실제로 난다.

## 결정성

무작위는 **스텝 키로 시드된 결정적 난수**다. 같은 스텝은 언제 돌려도 같은
premise 를 뺀다 — 캐시·재개·재현이 어긋나면 안 된다.
"""
from __future__ import annotations

import hashlib
import random
import re
from typing import Any, Optional

import rango_defaults as _D

# 분기 통계 (모의학습·점검에서 읽는다)
STATS: dict[str, int] = {
    "스텝": 0,
    "(1) 외부참조 없음": 0,
    "(2-a) gold 이미 보임": 0,
    "(2-b) gold 끼워 넣음": 0,
    "(2-b) 끼웠으나 창 밖": 0,
    "(2-b) 실패(포기)": 0,
    "빼낸 premise": 0,
    "계획 없음": 0,
    "폴백 조회 성공": 0,
    "폴백 조회 실패": 0,
    "명제 아님(제외)": 0,
    "(2-b) 못 넣어 예제 폐기": 0,
    "못 넣음(치명)": 0,
    "못 넣음(stdlib·면제)": 0,
}

# ★ 직전 `inject()` 가 **끼우지 못한** gold lemma 이름. 비어 있지 않으면 그 예제는
#   정답이 프롬프트에 없는 이름을 쓴다 = v9 의 hopeless 와 같은 상태다.
#   `LmDataset._hallucinates` 가 이걸 보고 예제를 **버린다**(V10_REQUIRE_ALL=1).
#   안 버리면 "볼 수 없는 이름을 지어내라" 고 가르치게 된다 — v10 이 없애려던 바로 그 해악.
LAST_UNPLACED: list = []


def _seen(name: str, text: str) -> bool:
    return re.search(r"(?<![\w'])" + re.escape(name) + r"(?![\w'])", text) is not None


_DECLKW = (r"(?:Local\s+|Global\s+|Program\s+)?"
           r"(?:Lemma|Theorem|Corollary|Remark|Proposition|Definition|Fixpoint|Axiom)")


_REL = re.compile(r"(?:<=|>=|<>|<->|=|<|>|~|/\\|\\/|≤|≥|≠|↔)")
_BARE = re.compile(r"^[A-Za-z_][\w'.]*$")


def is_prop(ty: str) -> bool:
    """이 `ty` 를 `Lemma <name> : ty.` 로 쓸 수 있나 — **명제인가.**

    ★ 계획(`plan["lem"]`)은 lemma 만 담고 있지 않다. 실측으로 `pow` 의 값이
      `R → Z → R` 였다 — **함수 타입**이다(정답은 `unfold pow` 로 쓴다).
      그대로 끼우면 `Lemma pow : R → Z → R.` 이라는 **문법은 유효하지만 거짓인
      선언**이 프롬프트에 들어간다. 모델에게 거짓을 가르치는 것이 최악이다.

    판정은 **결론**으로 한다 — 화살표로 쪼갠 마지막 조각:

        R → Z → R                      결론 `R`         맨이름  → 명제 아님
        nat -> nat                     결론 `nat`       맨이름  → 명제 아님
        S n <= S m -> n <= m           결론 `n <= m`     관계   → 명제
        Even n -> Odd (S n)            결론 `Odd (S n)`  적용   → 명제
        forall r:R, 1 * r = r          forall           → 명제

    정의·생성자·필드 계열은 v10 의 대상이 아니다(README §6.3) —
    `DROP_HALLUC` 이 그 몫을 거른다.
    """
    t = (ty or "").strip().rstrip(".")
    if not t:
        return False
    if re.search(r"\b(?:forall|exists)\b|∀|∃", t):
        return True
    concl = re.split(r"->|→", t)[-1].strip()
    if _BARE.match(concl):
        return False                       # 맨 타입이름 하나 = 명제 아님
    return True                            # 관계식이거나 적용된 술어


def _decl(name: str, ty: str) -> str:
    """gold lemma 의 **선언문** 한 줄. 풀의 premise 와 같은 형식이어야 한다.

    `ty` 가 두 형태로 온다:
      · 명제만 (`forall n m, …`)      — cut 계획의 `lem` — `Lemma <name> : <ty>.` 로 감싼다
      · 완전한 선언문 (`Lemma foo n m : …`) — sentence DB — **원문 그대로** 쓰고 이름만 바꾼다

    ★ 후자를 재작성하면 안 된다. `Lemma le_S_n n m : S n <= S m -> n <= m.` 처럼
      바인더가 콜론 앞에 오거나 `Definition … := 본문` 이면, 콜론으로 쪼개 다시
      조립하는 순간 **문법이 깨진 거짓 선언**이 된다(실측으로 걸렸다).
    """
    t = (ty or "").strip()
    if re.match(r"^\s*" + _DECLKW + r"\s", t):
        return re.sub(r"^(\s*" + _DECLKW + r"\s+)[A-Za-z_][\w']*",
                      lambda m: m.group(1) + name, t, count=1).strip()
    return f"Lemma {name} : {t.rstrip('.')}."


def _window(collator, tokenizer, premises: list[str]) -> tuple[list[str], list[int]]:
    """프롬프트에 **실제로 담기는** premise 와 그 인덱스 — collator 와 같은 경로.

    ★ collator 는 예산을 적용하기 **전에** `rerank_premises` 를 건다. 여기서
      빼먹으면 모델이 보는 것과 다른 목록으로 판정하게 된다.
    """
    from tactic_gen.tactic_data import rerank_premises, whole_number_allocate

    class _Shim:
        pass

    n = getattr(collator, "premise_tokens", 896)
    ranked = premises
    if _D.get("RERANK_PREMISES") == "1":
        try:
            sh = _Shim()
            sh.premises = premises
            sh.proof_state = getattr(_window, "_state", "") or ""
            ranked = rerank_premises(sh) or premises
        except Exception:
            ranked = premises
    try:
        idxs = whole_number_allocate(tokenizer, ranked, n, return_idx=True)
    except Exception:
        idxs = list(range(min(len(ranked), 25)))
    return ranked, list(idxs)


NAMED = re.compile(r"\b(?:e?apply|e?rewrite|exact|unfold|specialize|generalize|refine|"
                   r"pose\s+proof|inversion)\s+(?:<-\s*|->\s*)?\(?\s*"
                   r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)")
_LOCAL = re.compile(r"^(?:H\d*|IH\w*|Heq\w*|[A-Z]\d*)$")

_DBCON = None
_DBCACHE: dict = {}


def _db_decl(name: str):
    """sentence DB 에서 lemma **선언문**을 찾는다 — 계획(cut_plans)이 없을 때의 폴백.

    실측: 계획이 없는 스텝 중 6.7% 는 정답이 **실제 프로젝트 lemma 를 부른다**
    (`build_cuts` 가 Coq `Check` 실패로 못 만든 것들). 그대로 두면 v10 이
    가장 필요한 예제를 놓친다.

    ★ 맨 이름 조회는 모호하다(`gso` 는 PTree/PMap/IMap/EMap 에 전부 있다).
      한정자가 있으면 module 로 먼저 좁힌다 — 오라클 실험과 같은 방식.
    """
    global _DBCON
    if name in _DBCACHE:
        return _DBCACHE[name]
    if len(_DBCACHE) > 200000:
        _DBCACHE.clear()
    if _DBCON is None:
        import sqlite3
        try:
            _DBCON = sqlite3.connect(_D.get("V10_SENTENCE_DB",
                                            "/tmp/coq-dataset/sentences.db"),
                                     check_same_thread=False)
            _DBCON.execute("PRAGMA query_only=1")
        except Exception:
            _DBCON = False
    if not _DBCON:
        _DBCACHE[name] = None
        return None
    parts = name.split(".")
    bare, qual = parts[-1], (parts[-2] if len(parts) > 1 else None)
    pats = [f"{k} {bare}{c}" for k in ("Lemma", "Theorem", "Corollary", "Remark",
                                       "Proposition", "Definition")
            for c in (":%", " %")]

    def q(extra, args):
        for pat in pats:
            try:
                r = _DBCON.execute(
                    "SELECT text FROM sentence WHERE text LIKE ?" + extra + " LIMIT 1",
                    (pat,) + args).fetchone()
            except Exception:
                return None
            if r:
                return r[0]
        return None

    got = q(" AND module LIKE ?", ("%" + qual + "%",)) if qual else None
    if got is None:
        got = q("", ())
    # ★★ SQLite `LIKE` 는 ASCII 에서 **대소문자를 구분하지 않는다.**
    #   그래서 `pow` 로 찾으면 `Definition Pow : Set := Ssig Desc.` 가 잡힌다 —
    #   엉뚱한 선언문을 gold 이름으로 끼우면 모델에게 **거짓을 가르친다.**
    #   실측으로 걸렸다(사전점검 200 표본 중 1건). 이름이 정확히 일치하는지 확인한다.
    if got is not None:
        m = re.match(r"^\s*(?:Local\s+|Global\s+|Program\s+)?\w+\s+([A-Za-z_][\w']*)", got)
        if not m or m.group(1) != bare:
            got = None
    _DBCACHE[name] = got
    return got


def visible(collator, tokenizer, example, name: str) -> bool:
    """이 이름이 **모델이 실제로 보는 프롬프트**에 남는가 — 프로덕션과 같은 경로로 본다.

    `_window()` 는 창 계산을 다시 구현한 것이라 프로덕션과 어긋날 수 있다
    (rerank 의 `proof_state` 전달, `allocate_and_fmt` 의 reverse 등).
    최종 판정은 `collate_input` **그 자체**로 해야 한다.

    ★ 그리고 창에 들었다고 끝이 아니다. 학습은
      `tok(s, max_length=HARD_SEQ_LEN, truncation=True)` 이고 토크나이저의
      `truncation_side="left"` 다. `[PREMISES]` 가 프롬프트 **맨 앞**이므로
      넘치면 **premise 가 먼저 잘린다.** 그래서 절단까지 재현해서 확인한다.
      정답(`out_tokens`)이 뒤에 붙으므로 그만큼 보수적으로 뺀다.
    """
    try:
        s = collator.collate_input(tokenizer, example, normalize=False)
    except TypeError:
        s = collator.collate_input(tokenizer, example)
    if not _seen(name, s):
        return False
    hard = _D.num("HARD_SEQ_LEN", 3072) - _D.num("OUT_TOKENS", 256)
    try:
        ids = tokenizer(s, add_special_tokens=False)["input_ids"]
    except Exception:
        return True
    if len(ids) <= hard:
        return True
    return _seen(name, tokenizer.decode(ids[-hard:], skip_special_tokens=True))


def plan_lemmas(example) -> Optional[list[tuple[str, str]]]:
    """이 스텝이 쓰는 **외부 lemma (이름, 명제)** 목록. 외부 참조가 없으면 `[]`.

    1차 출처는 `data/cut_plans_all.jsonl` 의 `plan` 레코드 — v9 의 cut 이 쓰던
    바로 그 재료인데, v10 은 그것으로 **assert 를 만들지 않고 premise 를 끼운다**.
    계획이 없으면 정답에서 이름을 뽑아 **sentence DB** 로 선언문을 찾는다.
    """
    if not _D.get("CUTS_PATH"):
        return None
    from tactic_gen import cut_lookup
    sid = (f"{getattr(example, 'file_name', '')}:"
           f"{getattr(example, 'proof_idx', '')}:{getattr(example, 'step_idx', '')}")
    plan = cut_lookup.plan_for(sid)
    if plan is not None:
        out = []
        for nm, ty in (plan.get("lem") or []):
            if not (nm and ty):
                continue
            if is_prop(ty) or re.match(r"^\s*" + _DECLKW + r"\s", str(ty).strip()):
                out.append((nm, ty))
            else:
                STATS["명제 아님(제외)"] += 1
        return out

    if not _D.flag("V10_DB_FALLBACK"):
        return None
    steps = getattr(example, "next_steps", None) or []
    tgt = steps[0] if steps else ""
    out = []
    for nm in dict.fromkeys(m.group(1) for m in NAMED.finditer(tgt)):
        if len(nm) <= 2 or _LOCAL.match(nm):
            continue
        ty = _db_decl(nm)          # ★ 원문 그대로 — _decl 이 이름만 갈아 끼운다
        if ty:
            out.append((nm, ty))
            STATS["폴백 조회 성공"] += 1
        else:
            STATS["폴백 조회 실패"] += 1
    return out


def _is_stdlib(name: str) -> bool:
    """stdlib 이름인가 — **모델의 상식**으로 보고 익명화도 안 하는 것들.

    `NORMALIZE_SKIP_STDLIB=1` 이라 정규화에서 빠지고, `_hallucinates` 의 어휘 필터도
    같은 이유로 면제한다. 그러니 stdlib gold 를 못 끼웠다고 예제를 버리면 안 된다 —
    **판정 기준을 세 곳에서 같게** 맞춘다(안 맞추면 학습과 측정이 어긋난다).
    """
    try:
        from tactic_gen.normalize_names import is_stdlib_name
        return is_stdlib_name(name)
    except Exception:
        return False


def _fail(name: str) -> None:
    """끼우지 못한 것을 기록한다. stdlib 은 기록하지 않는다(§_is_stdlib)."""
    STATS["못 넣음(stdlib·면제)" if _is_stdlib(name) else "못 넣음(치명)"] += 1
    if not _is_stdlib(name):
        LAST_UNPLACED.append(name)


def inject(collator, tokenizer, example, input_str: str) -> tuple[Any, str]:
    """v10 본체. `(새 example, 분기이름)` 을 돌려준다. example 은 필요할 때만 복사한다.

    `input_str` 은 **주입 전** 프롬프트다 — "gold 가 보이나" 를 이걸로 판정한다.
    """
    import copy as _cp

    STATS["스텝"] += 1
    LAST_UNPLACED.clear()
    lems = plan_lemmas(example)
    if lems is None:
        STATS["계획 없음"] += 1
        return example, "계획 없음"
    if not lems:
        STATS["(1) 외부참조 없음"] += 1
        return example, "(1)"

    miss = [(nm, ty) for nm, ty in lems if not _seen(nm, input_str)]
    if not miss:
        STATS["(2-a) gold 이미 보임"] += 1
        return example, "(2-a)"

    prem = list(getattr(example, "premises", None) or [])
    if not prem:
        STATS["(2-b) 실패(포기)"] += 1
        return example, "(2-b)실패"

    sid = (f"{getattr(example, 'file_name', '')}:"
           f"{getattr(example, 'proof_idx', '')}:{getattr(example, 'step_idx', '')}")
    rng = random.Random(int(hashlib.sha1(sid.encode()).hexdigest()[:12], 16))
    _window._state = getattr(example, "proof_state", "") or ""

    # ★ 정답이 **한정이름**을 쓰면 그 형태로 끼운다.
    #   계획/DB 는 bare 이름(`clos_trans_tn1`)을 주는데 정답은
    #   `Operators_Properties.clos_trans_tn1` 이라 부르는 경우가 있다. bare 로 끼우면
    #   프롬프트에 그 이름이 없는 것과 같다 — 정확히 functor-names.md 의 문제다.
    _tgt = (getattr(example, "next_steps", None) or [""])[0]
    _tnames = [m.group(1) for m in NAMED.finditer(_tgt)]
    _asused = {n.split(".")[-1]: n for n in _tnames if "." in n}

    done = 0
    for nm, ty in miss[: max(1, _D.num("V10_INJECT_MAX", 3))]:
        nm = _asused.get(nm.split(".")[-1], nm)
        decl = _decl(nm, ty)
        placed = False
        for attempt in range(6):
            ranked, idxs = _window(collator, tokenizer, prem)
            if not idxs:
                prem = [decl] + prem
                placed = True
                break
            if attempt == 0:
                # ① 실리는 것 중 하나를 무작위로 빼고 그 자리에 끼운다
                victim = ranked[rng.choice(idxs)]
                try:
                    j = prem.index(victim)
                except ValueError:
                    j = 0
                prem[j] = decl
                STATS["빼낸 premise"] += 1
            elif attempt == 1:
                # ② 창 밖으로 밀렸다 → 맨 앞으로 옮긴다
                prem = [decl] + [p for p in prem if p != decl]
            else:
                # ③ 그래도 안 되면 창 안의 **가장 긴 것**을 마저 빼서 자리를 만든다
                longest = max((ranked[i] for i in idxs if ranked[i] != decl),
                              key=len, default=None)
                if longest is not None:
                    prem = [p for p in prem if p != longest]
                prem = [decl] + [p for p in prem if p != decl]
            # 검증 — **프로덕션 경로**로 정말 프롬프트에 남는가 (절단까지)
            _probe = _cp.copy(example)
            _probe.premises = prem
            if visible(collator, tokenizer, _probe, nm):
                placed = True
                break
        if placed:
            done += 1
        else:
            STATS["(2-b) 끼웠으나 창 밖"] += 1
            _fail(nm)

    # ★ 상한(V10_INJECT_MAX)에 걸려 **손도 못 댄** 것도 못 넣은 것이다.
    for nm, _ in miss[max(1, _D.num("V10_INJECT_MAX", 3)):]:
        _fail(nm)

    if done == 0:
        STATS["(2-b) 실패(포기)"] += 1
        return example, "(2-b)실패"

    ex2 = _cp.copy(example)
    ex2.premises = prem
    STATS["(2-b) gold 끼워 넣음"] += 1
    return ex2, "(2-b)"


def format_stats() -> str:
    n = max(STATS["스텝"], 1)
    ks = ["(1) 외부참조 없음", "(2-a) gold 이미 보임", "(2-b) gold 끼워 넣음",
          "(2-b) 끼웠으나 창 밖", "(2-b) 실패(포기)", "계획 없음", "명제 아님(제외)"]
    body = "  ".join(f"{k} {STATS[k]} ({STATS[k]/n*100:.1f}%)" for k in ks)
    return f"[v10] 스텝 {STATS['스텝']} · {body} · 빼낸 premise {STATS['빼낸 premise']}"
