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
import rango_defaults as _D   # ★ 프로덕션 기본값 단일 출처

import hashlib
import json
import os
import re
from typing import Optional

from tactic_gen.name_alloc import NameAllocator  # noqa: E402

# ★ 치환 단위 — 왜 이렇게 생겼나 (실측으로 드러난 두 사고)
#
#   ① **모듈 접두사를 건드리면 안 된다.**
#      `Mem.load` 의 `Mem` 은 모듈이지 우리가 매핑한 상수가 아니다. 그런데 옛 정규식은
#      식별자를 조각별로 매칭해서 `O.eq` → `tt.f0` 를 만들었다(실측: 프롬프트당 0.10회).
#      `tt` 는 stdlib 생성자 이름이라 **더 나쁜 이름으로 바뀐 것**이다.
#      → 뒤에 `.식별자` 가 오는 조각은 모듈 경로다. 절대 치환하지 않는다.
#
#   ② **문자열·주석 안을 건드리면 안 된다.**
#      `idtac "eq"` 의 `"eq"` 는 출력 문자열이지 이름이 아니다. 바꾸면 tactic 의 의미가
#      달라진다. `(* … *)` 도 마찬가지로 코드가 아니다.
#
#   꼬리(`M.x` 의 `x`)는 **계속 치환한다.** 접두사가 남아 서로 다른 상수가 합쳐지지 않고,
#   프롬프트(`Lemma L3 : …`)와 정답(`apply PTree.L3`)의 일관성이 유지되기 때문이다.
#   일관성이 깨지면 그 예제는 학습 신호가 아니라 노이즈가 된다.
_IDENT = re.compile(r"[A-Za-z_][\w']*")

#   조각 뒤에 `.식별자` 가 오면 모듈 경로 — 치환 금지
_MODPFX = re.compile(r"[A-Za-z_][\w']*(?=\.[A-Za-z_])")
#   건드리면 안 되는 구간: 문자열 리터럴 · 주석(중첩 없음 가정)
_SKIP = re.compile(r'"(?:[^"\\]|\\.)*"|\(\*.*?\*\)', re.S)

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
        path = _D.get("FUNC_DEFS_PATH")
        try:
            with open(path) as f:
                _IDX = json.load(f)
        except OSError:
            _IDX = {}
    return _IDX


# ★ 표준 라이브러리 이름은 익명화하지 않는다.
#
#   익명화의 목적은 "**그 프로젝트에만 통하는 이름**을 외워서 찍는 습관" 을 끊는 것이다.
#   stdlib 이름은 어느 프로젝트에서나 통하므로 바꿀 이유가 없다.
#   실측(TRAIN 800건): gold lemma 의 62.1% · 후보 풀의 92.7% 가 stdlib 이다.
#
#   ★ 주의: 프로브 실측으로 **모델이 stdlib lemma 진술을 아는 것은 아니다**
#     (F1 stdlib 0.292 vs 가짜이름 0.291 — 사실상 동일). 그러므로 "stdlib 이니
#     검색 없이도 된다" 는 성립하지 않는다. 여기서 제외하는 것은 **무해하기 때문**이지
#     사전학습 지식을 쓸 수 있어서가 아니다.
#
#   판정은 `data/stdlib_names.json`(sentences.db 의 file_path 로 만든 이름 집합).
#   양쪽에 있는 이름은 **프로젝트 우선** — 잘못 남기는 것보다 잘못 바꾸는 편이 위험하다.
_STDLIB_NAMES: Optional[set] = None


def _stdlib_names() -> set:
    global _STDLIB_NAMES
    if _STDLIB_NAMES is None:
        p = os.environ.get("STDLIB_NAMES_PATH", "data/stdlib_names.json")
        try:
            with open(p) as f:
                _STDLIB_NAMES = set(json.load(f))
        except Exception:
            _STDLIB_NAMES = set()
    return _STDLIB_NAMES


def is_stdlib_name(name: str) -> bool:
    """표준 라이브러리 전용 이름인가 (익명화 제외 대상)."""
    if (not _D.flag("NORMALIZE_SKIP_STDLIB")):
        return False
    n = (name or "").split(".")[-1]
    return n in _stdlib_names()


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
                  proof_script: Optional[str] = None,
                  ltac_names: Optional[list] = None) -> dict:
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
    if not injected and (not _D.flag("NORMALIZE_PREMISES")) \
            and (not _D.flag("NORMALIZE_THEOREM")) \
            and (not _D.flag("NORMALIZE_LTAC")):
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
    if _D.flag("NORMALIZE_PREMISES"):
        for pn in premise_names(premises):
            # ★ renameable() 을 쓰면 안 된다 — 그건 **정의 인덱스(func_defs)** 에 있는 이름만
            #   허용하는데 premise 는 lemma 라 인덱스에 없다(실측: 235건 중 134건이 이 필터에
            #   걸려 하나도 치환되지 않았다). premise 이름은 `Lemma X :` 선언에서 직접 뽑은
            #   것이라 출처가 확실하므로 보호목록·길이만 확인하면 된다.
            if (pn not in names and pn not in ctors
                    and pn not in _PROTECTED and pn not in _HEADERS and len(pn) > 1
                    and not is_stdlib_name(pn)):     # ★ stdlib 은 익명화 제외
                prem_names.append(pn)
    # ★ v8: 증명 중인 정리 이름 (NORMALIZE_THEOREM=1 일 때만)
    #
    #   ★ 동명 충돌 처리: CompCert 는 모듈마다 같은 이름의 보조정리를 둔다
    #     (Val.sub_zero_r 와 Int.sub_zero_r). 그래서 증명 중인 정리 이름이
    #     [PREMISES] 에도 나타나는 일이 있다(실측 601건 중 8건 = 1.3%).
    #     텍스트 치환은 **같은 문자열을 두 이름으로 바꿀 수 없으므로**, 둘 다 L# 가
    #     되어 "증명 대상"과 "주어진 사실"을 구분할 수 없게 된다.
    #     → 충돌 시엔 매핑에 넣지 않고 전역에 기록해, collate 가 **선언부만** G# 로 바꾼다.
    # ★★ v9: **파일 내 Ltac 이름**도 대상 (NORMALIZE_LTAC=1 일 때만).
    #
    #   근거(실측, Qwen2.5-Coder-3B · n=400 · 가짜는 `_` 조각 섞기라 토큰 구성 동일):
    #       프로젝트 Lemma        실명 선호 61.8%  (4.7σ)
    #       프로젝트 Ltac         실명 선호 61.5%  (4.6σ)   ← Lemma 와 사실상 같다
    #       notation 이 가린 이름  실명 선호 53.5%  (1.4σ)   ← 우연과 구분 안 됨
    #   프로젝트 전용이라 사전학습에 없을 줄 알았는데 **아니었다.** 막을 지름길이 있다.
    #   익명화하면 `[LTAC]` 섹션이 그 이름의 **유일한 경로**가 되어 실제로 읽힌다.
    #
    #   notation 이 가린 이름은 반대로 회상이 없으므로 **대상에 넣지 않는다** —
    #   막을 게 없는데 "뜻 있는 이름" 신호만 잃는 순손실이다.
    ltac_ns = []
    if _D.flag("NORMALIZE_LTAC"):
        for t in (ltac_names or []):
            m = re.match(r"\s*(?:Ltac|Ltac2)\s+([A-Za-z_][\w']*)", t if isinstance(t, str) else "")
            if not m:
                continue
            n = m.group(1)
            if (n not in names and n not in ctors and n not in prem_names
                    and n not in _PROTECTED and n not in _HEADERS and len(n) > 1
                    and not is_stdlib_name(n)):
                ltac_ns.append(n)
        ltac_ns = list(dict.fromkeys(ltac_ns))
    global LAST_THM_DECL
    LAST_THM_DECL = None
    thm = None
    if _D.flag("NORMALIZE_THEOREM"):
        t = theorem_name(proof_script or "")
        if t and t not in names and t not in ctors:
            # ★★ **동명 선언이 프롬프트에 둘 이상이면 매핑하지 않는다.**
            #   `apply_mapping` 은 텍스트 치환이라 같은 이름을 전부 바꾼다. [PROOFS] 에
            #   같은 이름의 **다른** lemma 가 실려 있으면(모듈이 달라 흔하다) 셋 다
            #   `G0` 이 되어 모델이 구분할 수 없다.
            #   실측: `Lemma G0 p q : to_nat p = to_nat q -> p = q.` 와
            #        `Lemma G0 (n m : nat) : n<>0 -> … -> n = m.` 이 같은 이름이 됐다.
            #   `premise_names` 에는 이 방어가 있었는데(중복 이름은 원래대로 둔다)
            #   정리 이름 경로에만 빠져 있었다.
            _ndecl = len(re.findall(
                r"(?:Lemma|Theorem|Corollary|Remark|Fact|Proposition|Definition|"
                r"Instance|Axiom)\s+" + re.escape(t) + r"(?![\w'])", avoid_text or ""))
            if _ndecl > 1:
                LAST_THM_DECL = t          # 동명 다수 — 선언부 한 곳만 G# 로
            elif t in prem_names:
                LAST_THM_DECL = t          # 충돌 — 선언부만 따로 처리
            else:
                thm = t
    # ★ 주입 정의(T#/f#/C#)도 stdlib 이면 바꾸지 않는다 — lemma 와 같은 이유
    names = [x for x in dict.fromkeys(names) if not is_stdlib_name(x)]
    ctors = [c for c in dict.fromkeys(ctors)
             if c not in names and not is_stdlib_name(c)]
    prem_names = [p for p in dict.fromkeys(prem_names) if p not in names and p not in ctors]
    if not names and not ctors and not prem_names and not thm and not ltac_ns:
        return {}
    # ★ 충돌 검사는 **T\d+/f\d+/C\d+ 형태만** 훑으면 된다.
    #   프롬프트 전체(~8KB)를 일반 식별자 정규식으로 훑으면 예제마다 비용이 크다.
    # ★ 이름 할당은 `name_alloc.NameAllocator` 한 곳으로 통합했다 (assert 와 공통).
    #   여기서는 **가벼운 모드** — 프롬프트가 8KB 라 매 예제마다 일반 식별자 정규식으로
    #   훑으면 비용이 크다. 정해진 형태(`[TfCLG]\d+`)만 본다.
    alloc = NameAllocator.from_pattern(
        avoid_text or "", r"\b[TfCLGK]\d+\b",
        extra=(set(names) | set(ctors) | set(prem_names) | set(ltac_ns)
               | ({thm} if thm else set())))

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
    # ★ 파일 내 Ltac 은 **K** 접두사 — tactic 자리에 오는 것이라 lemma(L) 와 구분한다.
    n_k = 0
    for ln in ltac_ns:
        mapping[ln], n_k = fresh("K", n_k)
    # 증명 중인 정리는 **G**(goal) — 하나뿐이라 번호는 0 에서 시작
    if thm:
        mapping[thm], _ = fresh("G", 0)
    return mapping


def _sub_code(seg: str, mapping: dict) -> str:
    """코드 구간 한 조각을 치환한다. 모듈 접두사는 건너뛴다."""
    keep = {m.start() for m in _MODPFX.finditer(seg)}
    return _IDENT.sub(
        lambda m: m.group(0) if m.start() in keep
        else mapping.get(m.group(0), m.group(0)), seg)


# ══ 도입되는 이름 vs 참조되는 이름 ═══════════════════════════════════════
#
#   tactic 안의 이름에는 두 종류가 있다.
#
#       참조   `apply add_comm`      — 프롬프트에서 **읽어야** 하는 이름
#       도입   `destruct X as [f1 …]` — 그 자리에서 **새로 만드는** 이름
#              `intros a b c`         — 마찬가지
#
#   검사기가 이걸 구분 못 하면 "정답이 프롬프트에 없는 이름을 쓴다" 고 **오탐**한다.
#   실측: `destruct IN as [f1 [IN1 [a1 [b1 LE1]]]].` 의 `f1` 이 그렇게 걸렸다.
#   (`[TfCLG]\d+` 정규식은 정규화 이름과 진짜 식별자를 구분 못 한다 — 네 번 당했다.)
_INTRO_AS = re.compile(r"\bas\s*\[[^\]]*\]|\bas\s+[A-Za-z_][\w']*")
_INTRO_TAC = re.compile(
    r"\b(?:intros?|intro|eintros?|move\s*=>|rename\s+\S+\s+into)\s+[^.;]*")
_INTRO_PAT = re.compile(r"\[[^\[\]]*\]")


# ★ SSReflect·표준 tactic 중 **이름을 만드는** 형태.
#   `have NAME: TYPE by TAC` · `set NAME := …` · `pose NAME := …` ·
#   `remember X as NAME` · `assert (…) as NAME` · `suff NAME: …` · `wlog NAME: …`
#   실측 오탐: `have srdf: substrate r = f4 f by …` 의 srdf,
#   `have Tbt: f0 C1 T0 by fprops.` 의 Tbt, `have bgp: …` 의 bgp 를
#   "프롬프트에 없는 외부 이름" 으로 신고했다 — tactic 자신의 **산출물**인데.
_INTRO_HAVE = re.compile(
    r"(?:^|[;\[\]|(){}\s])(?:have|suff|suffices|wlog|gen\s+have)\s+"
    r"(?:\[[^\]]*\]\s*)?([A-Za-z_][\w']*)\s*[:(]")
# ★ SSReflect **intro 패턴** — `move: X => [a b c]` · `case: X => [|n IH]` 의
#   대괄호 안 이름은 전부 **새로 도입되는** 것이다.
#   실측 오탐: `move: (cg _ ya) => [z zf lzg]` 의 lzg 를 외부 참조로 셌다.
_INTRO_SSR_PAT = re.compile(r"=>\s*((?:[\[\]|/\s]|[A-Za-z_][\w']*)+)")
# ★ `assert (H := e)` · `have (H := e)` 형태의 이름
#   실측 오탐: `assert (H3':= H3).` 의 H3'
_INTRO_ASSIGN = re.compile(r"[(\s]([A-Za-z_][\w']*)\s*:=")

# ★ `destruct n as [| n'] eqn:E.` 의 **`eqn`** — 이건 이름이 아니라 **절 키워드**다.
#   실측: 이걸 "프롬프트에 없는 외부 참조" 로 신고했다(덤프 [13]).
#   `eqn:E` 는 E 를 도입하고 `eqn` 자체는 문법이다.
_INTRO_EQN = re.compile(r"\beqn\s*:\s*([A-Za-z_][\w']*)")
# ★ SSReflect **중첩** intro 패턴 — `have [sf [ff _] f0 fs1 fs2] := (L5 h a pN).`
#   기존 `_INTRO_HAVE` 의 `\[[^\]]*\]` 는 첫 `]` 에서 끊겨 중첩을 못 읽는다.
#   그래서 fs1·fs2 가 "환각" 으로 신고됐다(덤프 [15]).
#   → 괄호 균형을 직접 세어 그 안의 이름을 전부 도입으로 본다.
_HAVE_HEAD = re.compile(
    r"(?:^|[;\s|(){}])(?:have|suff|suffices|wlog|case|elim|destruct|move)\s*[:]?\s*(?=\[)"
    r"|=>\s*(?=[\[])"
    # ★ `as` 뒤의 묶음도 **도입 패턴**이다. `_INTRO_AS` 의 `\[[^\]]*\]` 는 첫 `]` 에서
    #   끊겨 **중첩을 못 읽는다** — 실측: `destruct H as [q [Hqq [r [Hrq [[Hq Hr]
    #   [[Hnnq Hnnr] Heq]]]]]].` 의 Hnnr 이 환각으로 신고됐다.
    #   괄호형 `as (x, Hor)` 도 마찬가지다(`case (…) as (x,Hor).`).
    r"|\bas\s*(?=[\[(])")


def _bracket_names(tac: str) -> set:
    """`[...]` 균형 그룹 안의 식별자 — 단 `/view` 는 **외부 참조**라 뺀다."""
    out = set()
    for m in _HAVE_HEAD.finditer(tac or ""):
        # 여는 괄호를 찾는다 — `[` 든 `(` 든 (`as (x, Hor)` 형태 때문에).
        i = -1
        for k in range(max(0, m.end() - 1), min(len(tac), m.end() + 2)):
            if tac[k] in "[(":
                i = k
                break
        if i < 0:
            continue
        op = tac[i]
        cl = "]" if op == "[" else ")"
        d, j = 0, i
        while j < len(tac):
            if tac[j] == op:
                d += 1
            elif tac[j] == cl:
                d -= 1
                if d == 0:
                    break
            j += 1
        if d != 0:
            continue
        grp = re.sub(r"/[A-Za-z_][\w']*", " ", tac[i:j + 1])   # view 제거
        grp = re.sub(r"\busing\b.*", " ", grp)                  # `as [..] using L` 의 L 은 참조
        out |= set(re.findall(r"[A-Za-z_][\w']*", grp))
    return out


_INTRO_SET = re.compile(
    r"(?:^|[;\s])(?:set|pose|epose|remember)\s+"
    r"(?:([A-Za-z_][\w']*)\s*:?=|.*?\bas\s+([A-Za-z_][\w']*))")


# ★ `assert (Erw : pb + nd = ...)` · `assert (spliteps : (eps/3 > 0)%R) by lra.`
#   → **`(이름 : 타입)` 의 이름은 도입**이다. 지금은 `(H := e)` 만 봤다.
# ★ `assert (forall Γ vsubst vsubst' (vr : VR Γ), ...)`
#   → forall/fun **바인더**도 도입이다. 실측에서 vsubst'·veqsubst·vr' 이
#     "프롬프트에 없는 이름" 으로 신고됐다.
#   단 `(vr : VR Γ)` 의 **`VR`·`Γ` 는 외부 참조**다 — `:` 앞만 도입으로 센다.
# ★ `auto with arith` 의 **arith 는 힌트 DB 이름**이지 참조가 아니다.
#   실측: gold 환각 36건 중 5건이 이것이었다(arith·geo·real·qarith·distributeMod).
#   `auto using foo` 의 foo 는 **진짜 lemma** 이므로 `with` 만 대상으로 한다.
_HINT_DB = re.compile(
    r"\b(?:auto|eauto|autounfold|autorewrite|autoapply|trivial|firstorder|intuition|"
    r"congruence|typeclasses\s+eauto|debug\s+auto|info_auto|new\s+auto)\b"
    r"[^.;]*?\bwith\b([^.;]*)")
_BINDER_HEAD = re.compile(r"\b(?:forall|fun)\s+([^,]*?)(?:,|=>)")
_ASSERT_HEAD = re.compile(
    r"\b(?:assert|enough|refine|have|suff|suffices|pose\s+proof|set|remember)\s*\(")


def _names_before_colon(seg: str) -> set:
    """`a b c : T` 에서 `a b c` 만. `:` 가 없으면 전부(바인더 나열)."""
    if ":" in seg:
        seg = seg.split(":", 1)[0]
    return set(re.findall(r"[A-Za-z_][\w']*", seg))


def _binder_names(tac: str) -> set:
    """forall/fun 바인더 + `assert (이름 : ...)` 의 이름."""
    out: set = set()
    t = tac or ""
    for m in _BINDER_HEAD.finditer(t):
        region = m.group(1)
        # 괄호 묶음은 `:` 앞만, 괄호 밖 홑이름은 전부 바인더
        for grp in re.findall(r"\(([^()]*)\)", region):
            out |= _names_before_colon(grp)
        bare = re.sub(r"\([^()]*\)", " ", region)
        out |= set(re.findall(r"[A-Za-z_][\w']*", bare))
    for m in _ASSERT_HEAD.finditer(t):
        i = m.end() - 1
        d, j = 0, i
        while j < len(t):
            if t[j] == "(":
                d += 1
            elif t[j] == ")":
                d -= 1
                if d == 0:
                    break
            j += 1
        inner = t[i + 1:j]
        # `이름 : ...` 형태일 때만 (`assert (forall ...)` 은 위에서 처리)
        m2 = re.match(r"\s*([A-Za-z_][\w']*)\s*:(?!=)", inner)
        if m2:
            out.add(m2.group(1))
    out.discard("forall")
    out.discard("fun")
    return out


def introduced_names(tac: str) -> set:
    """이 tactic 이 **새로 만드는** 이름들. 프롬프트에 없어도 정상이다."""
    out: set = set()
    for m in _INTRO_AS.finditer(tac or ""):
        out |= set(re.findall(r"[A-Za-z_][\w']*", m.group(0)))
    for m in _INTRO_TAC.finditer(tac or ""):
        # ★ `/name` 은 SSReflect **view**(외부 lemma 적용)라 도입 이름이 아니다.
        #   `move=> a b /andP[c d]` 에서 andP 는 외부 참조다 — 도입으로 세면 환각을 놓친다.
        out |= set(re.findall(r"[A-Za-z_][\w']*",
                              re.sub(r"/\s*[A-Za-z_][\w']*", " ", m.group(0))))
    for m in _INTRO_HAVE.finditer(tac or ""):        # ★ SSReflect have/suff/wlog
        out.add(m.group(1))
    for m in _INTRO_SET.finditer(tac or ""):         # ★ set/pose/remember
        for g in m.groups():
            if g:
                out.add(g)
    for m in _INTRO_SSR_PAT.finditer(tac or ""):     # ★ SSReflect `=> [a b c]`
        # ★ 단 `/name` 은 **view**(외부 lemma 적용)이지 도입 이름이 아니다.
        #   `move=> a b /andP[c d]` 에서 a·b·c·d 는 도입, andP 는 **외부 참조**다.
        #   그걸 도입으로 세면 진짜 환각을 놓친다.
        _seg = re.sub(r"/\s*[A-Za-z_][\w']*", " ", m.group(1))
        out |= set(re.findall(r"[A-Za-z_][\w']*", _seg))
    for m in _INTRO_ASSIGN.finditer(tac or ""):      # ★ `(H := e)`
        out.add(m.group(1))
    for m in _INTRO_EQN.finditer(tac or ""):         # ★ `eqn:E`
        out.add(m.group(1))
        out.add("eqn")
    out |= _bracket_names(tac or "")                 # ★ 중첩 `[a [b _] c]`
    out |= _binder_names(tac or "")                  # ★ forall 바인더 · assert (H : T)
    for m in _HINT_DB.finditer(tac or ""):           # ★ `auto with arith` 의 DB 이름
        out |= set(re.findall(r"[A-Za-z_][\w']*", m.group(1)))
    out -= {"as", "intros", "intro", "eintros", "eintro", "move", "rename", "into",
            "have", "suff", "suffices", "wlog", "set", "pose", "remember", "by"}
    return out


def apply_mapping(text: str, mapping: dict) -> str:
    """단어 경계 기준 일괄 치환. 부분 문자열 오염 방지(`val` 이 `value` 를 건드리지 않게).

    ★ 모듈 접두사(`M.x` 의 `M`)와 문자열·주석 안은 건너뛴다 — 위 `_IDENT` 주석 참고.
    """
    if not text or not mapping:
        return text
    out, pos = [], 0
    for m in _SKIP.finditer(text):
        out.append(_sub_code(text[pos:m.start()], mapping))
        out.append(m.group(0))                 # 문자열·주석은 원문 그대로
        pos = m.end()
    out.append(_sub_code(text[pos:], mapping))
    return "".join(out)


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
    rate = _D.fnum("NORMALIZE_RATE")
    if rate <= 0:
        return False
    if rate >= 1:
        return True
    h = int(hashlib.md5((key or "").encode()).hexdigest()[:8], 16)
    return (h % 1000) < rate * 1000
