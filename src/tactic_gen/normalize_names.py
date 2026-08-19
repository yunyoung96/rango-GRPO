"""α-이름 정규화 — 암기를 무력화해 **[TYPES]/[DEFINITIONS] 를 읽어야만 풀리게** 만든다.

## 왜 (ablation 실측)

    clean(올바른 정의) 63/191 = 33.0%   vs   wrong(틀린 정의) 66/194 = 34.0%
    같은 정리 187개에서 차이 ±0, McNemar p = 1.000

올바른 정의를 줘도 틀린 정의를 줘도 결과가 같다 = **모델이 섹션을 안 읽는다.**
읽을 이유가 없기 때문이다: `destruct v as [|x|x|x|x|x x]` 는 학습 중 본 `val` 이라는
**이름에 대한 암기**로 낼 수 있다. 정의를 볼 필요가 없다.

## 무엇을 하나

프로젝트 정의 이름을 예제마다 **일관되게 치환**한다:

    val → T0,  Vundef → C0,  Vint → C1, ...      (goal · [TYPES] · [DEFINITIONS] · 정답 tactic 전부)

α-치환은 **의미 보존**이므로 gold 가 그대로 gold 다 — Coq 재검증이 필요 없다.
(정의를 조작하는 counterfactual 과 결정적으로 다른 점. 그쪽은 gold 를 다시 만들어야 한다.)

이제 `T0` 의 생성자 수는 **[TYPES] 를 읽어야만** 알 수 있다. 암기가 통하지 않는다.

## 안전장치

  · stdlib/전역 이름(nat, list, Z, S, O, cons …)은 **바꾸지 않는다** — 모델의 상식이고,
    바꾸면 goal 자체가 이해 불가능해진다.
  · tactic 이름·Coq 키워드는 절대 건드리지 않는다(`destruct`, `intros`, `auto` …).
  · 프롬프트와 정답에 **같은 매핑**을 적용한다. 어긋나면 그 자체가 학습 노이즈다.
  · NORMALIZE_RATE(기본 0.5)로 일부만 정규화한다 — 테스트는 실제 이름이므로,
    원본과 섞어야 모델이 '메커니즘'을 배우고 실제 이름에도 적용한다.

## 실현 가능성(gold 400 step 실측)

    goal 식별자 중 프로젝트 정의   중앙 8개 / 전체 12개
    ≥1개 치환 가능한 예제          378/400 = 94%
    정답 tactic 이 치환된 이름을 쓰는 예제  93/377 = 25%  ← 이 25%가 강한 압력을 받는다
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Optional

from tactic_gen.name_alloc import NameAllocator  # noqa: E402

_IDENT = re.compile(r"[A-Za-z_][\w']*")

# 절대 바꾸면 안 되는 것: Coq 키워드 · tactic · stdlib 상식
_PROTECTED = {
    # 키워드/문법
    "forall", "exists", "fun", "match", "with", "end", "let", "in", "if", "then", "else",
    "return", "as", "fix", "cofix", "Type", "Prop", "Set", "struct", "where", "at", "by",
    "Lemma", "Theorem", "Definition", "Fixpoint", "Inductive", "CoInductive", "Variant",
    "Record", "Proof", "Qed", "Defined", "Admitted", "Section", "End", "Import", "Require",
    # tactic
    "intro", "intros", "apply", "eapply", "exact", "destruct", "induction", "case", "simpl",
    "unfold", "rewrite", "erewrite", "reflexivity", "symmetry", "transitivity", "auto",
    "eauto", "trivial", "assumption", "constructor", "econstructor", "split", "left",
    "right", "exists", "omega", "lia", "ring", "field", "congruence", "discriminate",
    "contradiction", "inversion", "injection", "subst", "generalize", "specialize", "pose",
    "assert", "cut", "clear", "revert", "rename", "replace", "change", "red", "hnf", "cbv",
    "cbn", "lazy", "compute", "vm_compute", "now", "try", "repeat", "first", "solve",
    "idtac", "fail", "elim", "refine", "instantiate", "eexists", "eassumption", "f_equal",
    # stdlib 상식(모델이 이미 아는 것 — 바꾸면 goal 이 이해 불가)
    "nat", "bool", "list", "option", "prod", "sum", "unit", "Z", "N", "positive", "R", "Q",
    "True", "False", "and", "or", "not", "iff", "eq", "ex", "sig", "sigT", "comparison",
    "S", "O", "nil", "cons", "None", "Some", "pair", "true", "false", "tt", "byte",
    "string", "ascii", "int", "int64", "float", "float32", "le", "lt", "ge", "gt",
}

_IDX: Optional[dict] = None


def _index() -> dict:
    """정의 인덱스 — '프로젝트 정의'인지 판정하는 데 쓴다."""
    global _IDX
    if _IDX is None:
        path = os.environ.get("FUNC_DEFS_PATH", "data/func_defs_v3.json")
        try:
            with open(path) as f:
                _IDX = json.load(f)
        except OSError:
            _IDX = {}
    return _IDX


def renameable(name: str) -> bool:
    """이 이름을 바꿔도 되나 — 프로젝트 정의이고 보호대상이 아닐 때만."""
    if name in _PROTECTED or len(name) <= 1:
        return False
    slot = _index().get(name)
    if not isinstance(slot, dict):
        return False
    return any(k != "stdlib" for k in slot)      # stdlib 전용 이름은 제외


# 프롬프트 섹션 헤더 — 절대 치환 대상이 아니다(치환되면 포맷이 깨진다)
_HEADERS = {"PREMISES", "PROOFS", "STATE", "SCRIPT", "TYPES", "DEFINITIONS",
            "ATTEMPT", "ERROR", "TACTIC", "USES"}


_PREM_DECL = re.compile(
    r"(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Instance|Axiom|Parameter)\s+"
    r"([A-Za-z_][\w']*)")


def premise_names(premises) -> list:
    """[PREMISES] 블록에 실린 **lemma 이름**들. v7 에서 정규화 대상에 추가한다.

    ## 왜 (실측 근거)

        gold 상태에서 다음 한 수를 물었을 때, 고른 lemma 가 **프롬프트 안에 있는 비율**

            1.3B base(SFT 없음)   5.9%     ← [PREMISES] 를 사실상 안 본다
            1.3B rango SFT       26.5%
            3B v5 SFT            47.1%
            3B v6 SFT(5k)        67.6%

      "검색 결과를 읽어 고르는" 능력은 사전학습에 없고 **SFT 로만** 생긴다.
      그러면 그 능력은 학습 분포(CompCert)에 묶이고 다른 프로젝트로 전이되지 않는다.
      이름을 익명화하면 "본 적 있는 이름"으로는 못 풀고 **문장을 읽어 goal 과 맞추는**
      것 외에 방법이 없어진다 — 이름에 의존하지 않으므로 전이 가능성이 높다.

    ## 대가

      gold 가 쓴 lemma 중 프롬프트에 있는 비율은 77% 다. 나머지 23% 는 사전학습 기억으로
      맞히던 것인데 정규화하면 그 경로가 막힌다. 그래서 NORMALIZE_RATE(0.5)로 섞는다.

    ## 중복 이름은 제외한다

    CompCert 는 모듈마다 같은 이름을 쓴다(PTree.gss 와 PMap.gss). 한 [PREMISES] 안에
    **명제가 다른 동명 정리**가 실리는 일이 잦다(예제의 41.1%). 치환은 텍스트 단위라
    둘이 같은 L# 로 합쳐지는데, 정답이 어느 쪽을 가리키는지는 **데이터에 정보가 없다**.
    서로 다른 이름을 억지로 주면 정답을 임의로 한쪽에 붙이게 되어 잘못된 신호가 된다.
    → 중복된 이름은 실제 이름 그대로 둔다. 비용은 premise 이름의 1.7% 뿐이다.
    """
    seen = []
    for p in (premises or []):
        m = _PREM_DECL.match((p or "").strip())
        if m and m.group(1) not in _PROTECTED:
            seen.append(m.group(1))
    cnt = {}
    for n in seen:
        cnt[n] = cnt.get(n, 0) + 1
    return [n for n in dict.fromkeys(seen) if cnt[n] == 1]


_THM_DECL = re.compile(
    r"(?:Lemma|Theorem|Remark|Corollary|Fact|Proposition|Definition)\s+([A-Za-z_][\w']*)")


# 동명 충돌로 매핑에 못 넣은 정리 이름 — collate 가 선언부만 치환한다(같은 스레드·같은 예제)
LAST_THM_DECL: Optional[str] = None

_DECL_HEAD = re.compile(
    r"((?:Lemma|Theorem|Remark|Corollary|Fact|Proposition|Definition)\s+)"
    r"({name})(?![\w'])")


def substitute_theorem_decl(text: str, name: str, new: str) -> str:
    """정리 **선언부 한 곳만** 바꾼다. 같은 이름의 premise 는 건드리지 않는다."""
    pat = re.compile(_DECL_HEAD.pattern.replace("{name}", re.escape(name)))
    return pat.sub(lambda m: m.group(1) + new, text, count=1)


def theorem_name(proof_script: str) -> Optional[str]:
    """지금 증명 중인 정리의 이름. v8 에서 익명화 대상에 추가한다.

    ## 왜 (실측 근거)

    CompCert 는 공개 저장소라 **사전학습에 실제 증명이 들어 있다**. 문맥을 전혀 안 주고
    `apply ` 다음 이름을 고르게 했을 때 SFT 안 한 Qwen3B 가 실재 CompCert 이름을 가짜보다
    **65.2%** 선호했다(Δlogp +1.55) — 사전학습이 이 프로젝트를 기억한다는 직접 증거다.

    정리 이름은 그 기억을 여는 열쇠다. `lessdef_list_trans` 를 보면 증명 전체를 떠올릴 수
    있고, 이름 자체가 방향을 담는다(`_trans`, `_comm`, `_sound`). 실측: gold step 의 54.5% 에서
    정리 이름이 프롬프트에 노출된다.

    익명화하면 goal 과 premise 를 **실제로 읽어야만** 풀리고, rand200 성적에서 사전학습
    회상 기여분이 빠져 **오염 없는 측정**이 된다. 대가로 성적 자체는 떨어질 수 있다.
    """
    m = _THM_DECL.search(proof_script or "")
    if m and m.group(1) not in _PROTECTED:
        return m.group(1)
    return None


def build_mapping(injected: dict, seed_key: str, avoid_text: str = "",
                  premises: Optional[list] = None,
                  proof_script: Optional[str] = None) -> dict:
    """**실제로 주입된 정의**의 이름과 그 생성자만 치환 대상으로 삼는다.

    ★ 왜 좁히나 (실측 실패): 처음엔 텍스트의 모든 식별자 중 인덱스에 있는 것을 바꿨더니
      섹션 헤더(`[ERROR]` → `[T7]`)와 Coq 에러 문장의 영어 단어(`pattern` → `f11`,
      `branches` → `f12`)까지 치환됐다. 흔한 영단어가 어느 프로젝트에선 정의 이름이기 때문이다.
      → 목적은 "**주입한 정의의 이름 암기**를 무력화"하는 것이므로, 대상을 딱 그것으로 좁힌다.

    injected: augment_v2_section 이 실제로 프롬프트에 넣은 {이름: 정의문}.
    avoid_text: 프롬프트+정답 전체. **여기 이미 있는 이름은 새 이름으로 쓰지 않는다.**

    ★ 충돌 방지가 필수다(실측 사고): goal 에 이미 `f, f0: float` 라는 변수가 있는데 우리가
      만든 이름도 `f0` 이면 **서로 다른 개체가 같은 이름**이 되어 예제가 망가진다.
      섹션의 `Class BinOp {S1 S2 S3 T1 T2 T3:Type}` 같은 타입변수도 같은 위험이 있다.
    반환: {원래이름: T0/C0/f0}. 타입·생성자는 T/C, 함수는 f.
    """
    # ★ 주입 정의가 없어도 premise·정리 이름은 정규화 대상이다(v7/v8).
    #   예전엔 여기서 즉시 반환해 [TYPES]/[DEFINITIONS] 가 빈 예제는 premise 정규화가
    #   **조용히 건너뛰어졌다**.
    if not injected and os.environ.get("NORMALIZE_PREMISES", "0") != "1" \
            and os.environ.get("NORMALIZE_THEOREM", "0") != "1":
        return {}
    injected = injected or {}
    names = []
    ctors = []
    for name, defn in injected.items():
        if name in _PROTECTED or name in _HEADERS or not renameable(name):
            continue
        names.append(name)
        # 정의문 안의 생성자도 함께 바꿔야 goal 의 `Vint` 와 [TYPES] 의 `Vint` 가 어긋나지 않는다
        if ":=" in defn and re.search(r"\b(Inductive|CoInductive|Variant)\b", defn.split(":=", 1)[0]):
            for part in defn.split(":=", 1)[1].split("|"):
                m = re.match(r"\s*([A-Za-z_][\w']*)", part)
                if m and m.group(1) not in _PROTECTED and m.group(1) not in _HEADERS:
                    ctors.append(m.group(1))
    # ★ v7: [PREMISES] 의 lemma 이름도 대상에 넣는다(NORMALIZE_PREMISES=1 일 때만).
    #   주입 정의 이름과 겹치면 그쪽 매핑을 따른다(중복 금지).
    prem_names = []
    if os.environ.get("NORMALIZE_PREMISES", "0") == "1":
        for pn in premise_names(premises):
            # ★ renameable() 을 쓰면 안 된다 — 그건 **정의 인덱스(func_defs)** 에 있는 이름만
            #   허용하는데 premise 는 lemma 라 인덱스에 없다(실측: 235건 중 134건이 이 필터에
            #   걸려 하나도 치환되지 않았다). premise 이름은 `Lemma X :` 선언에서 직접 뽑은
            #   것이라 출처가 확실하므로 보호목록·길이만 확인하면 된다.
            if (pn not in names and pn not in ctors
                    and pn not in _PROTECTED and pn not in _HEADERS and len(pn) > 1):
                prem_names.append(pn)
    # ★ v8: 증명 중인 정리 이름 (NORMALIZE_THEOREM=1 일 때만)
    #
    #   ★ 동명 충돌 처리: CompCert 는 모듈마다 같은 이름의 보조정리를 둔다
    #     (Val.sub_zero_r 와 Int.sub_zero_r). 그래서 증명 중인 정리 이름이
    #     [PREMISES] 에도 나타나는 일이 있다(실측 601건 중 8건 = 1.3%).
    #     텍스트 치환은 **같은 문자열을 두 이름으로 바꿀 수 없으므로**, 둘 다 L# 가
    #     되어 "증명 대상"과 "주어진 사실"을 구분할 수 없게 된다.
    #     → 충돌 시엔 매핑에 넣지 않고 전역에 기록해, collate 가 **선언부만** G# 로 바꾼다.
    global LAST_THM_DECL
    LAST_THM_DECL = None
    thm = None
    if os.environ.get("NORMALIZE_THEOREM", "0") == "1":
        t = theorem_name(proof_script or "")
        if t and t not in names and t not in ctors:
            if t in prem_names:
                LAST_THM_DECL = t          # 충돌 — 선언부만 따로 처리
            else:
                thm = t
    names = list(dict.fromkeys(names))
    ctors = [c for c in dict.fromkeys(ctors) if c not in names]
    prem_names = [p for p in dict.fromkeys(prem_names) if p not in names and p not in ctors]
    if not names and not ctors and not prem_names and not thm:
        return {}
    # ★ 충돌 검사는 **T\d+/f\d+/C\d+ 형태만** 훑으면 된다.
    #   프롬프트 전체(~8KB)를 일반 식별자 정규식으로 훑으면 예제마다 비용이 크다.
    # ★ 이름 할당은 `name_alloc.NameAllocator` 한 곳으로 통합했다 (assert 와 공통).
    #   여기서는 **가벼운 모드** — 프롬프트가 8KB 라 매 예제마다 일반 식별자 정규식으로
    #   훑으면 비용이 크다. 정해진 형태(`[TfCLG]\d+`)만 본다.
    alloc = NameAllocator.from_pattern(
        avoid_text or "", r"\b[TfCLG]\d+\b",
        extra=set(names) | set(ctors) | set(prem_names) | ({thm} if thm else set()))

    def fresh(prefix, k):
        """겹치면 **다음 인덱스로** 건너뛴 첫 이름과 다음 인덱스."""
        nm = alloc.alloc(prefix, start=k)
        return nm, int(nm[len(prefix):]) + 1

    # 결정적 순서(등장순) — 해시로 섞으면 예제마다 달라져 학습이 불안정
    mapping = {}
    n_t = n_f = n_c = 0
    for n in names:
        if n[0].isupper():
            mapping[n], n_t = fresh("T", n_t)
        else:
            mapping[n], n_f = fresh("f", n_f)
    for c in ctors:
        mapping[c], n_c = fresh("C", n_c)
    # ★ premise lemma 는 **L** 접두사 — 타입(T)·함수(f)·생성자(C)와 구분해 모델이
    #   "이건 인용할 lemma 다"를 형태로 알 수 있게 한다.
    n_l = 0
    for pn in prem_names:
        mapping[pn], n_l = fresh("L", n_l)
    # 증명 중인 정리는 **G**(goal) — 하나뿐이라 번호는 0 에서 시작
    if thm:
        mapping[thm], _ = fresh("G", 0)
    return mapping


def apply_mapping(text: str, mapping: dict) -> str:
    """단어 경계 기준 일괄 치환. 부분 문자열 오염 방지(`val` 이 `value` 를 건드리지 않게)."""
    if not text or not mapping:
        return text
    return _IDENT.sub(lambda m: mapping.get(m.group(0), m.group(0)), text)


def invert(mapping: dict) -> dict:
    """정규화 매핑을 뒤집는다: {원래이름: L0} → {L0: 원래이름}.

    ★ 매핑은 **단사**다(`fresh` 가 이미 쓰인 이름을 건너뛴다) → 역이 잘 정의된다.
      혹시라도 값이 겹치면 **먼저 나온 것**을 남긴다(결정적 순서 유지).
    """
    out: dict = {}
    for k, v in (mapping or {}).items():
        out.setdefault(v, k)
    return out


def apply_inverse(text: str, mapping: dict) -> str:
    """생성된 tactic 의 정규화 이름을 **원래 이름으로 되돌린다**.

    ★ 왜 필요한가: 추론에서도 정규화를 켜면 모델은 `apply L0.` 를 생성한다. 그런데
      Coq 은 `L0` 를 모른다 — 실행 전에 반드시 되돌려야 한다.
      (지금 기본 경로는 추론에서 정규화를 하지 않으므로 이 함수가 안 불린다.)

    ★ 매핑에 없는 `L99` 같은 것은 **그대로 둔다**. 모델이 지어낸 이름이고, Coq 에서
      실패하는 것이 맞다 — 조용히 다른 이름으로 바꾸면 환각을 숨기게 된다.
    """
    inv = invert(mapping)
    if not text or not inv:
        return text
    return _IDENT.sub(lambda m: inv.get(m.group(0), m.group(0)), text)


def should_normalize(key: str) -> bool:
    """이 예제를 정규화할지 — NORMALIZE_RATE 비율만큼, key 해시로 결정적으로 고른다.

    ★ 전부 정규화하면 테스트(실제 이름)와 분포가 어긋난다. 섞어야 모델이 메커니즘을 배우고
      실제 이름에도 적용한다.
    """
    rate = float(os.environ.get("NORMALIZE_RATE", "0.5"))
    if rate <= 0:
        return False
    if rate >= 1:
        return True
    h = int(hashlib.md5((key or "").encode()).hexdigest()[:8], 16)
    return (h % 1000) < rate * 1000
