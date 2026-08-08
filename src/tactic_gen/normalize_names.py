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


def build_mapping(injected: dict, seed_key: str, avoid_text: str = "") -> dict:
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
    if not injected:
        return {}
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
    names = list(dict.fromkeys(names))
    ctors = [c for c in dict.fromkeys(ctors) if c not in names]
    if not names and not ctors:
        return {}
    taken = set(_IDENT.findall(avoid_text or "")) | set(names) | set(ctors)

    def fresh(prefix, k):
        """taken 과 겹치지 않는 첫 이름과 다음 인덱스."""
        while f"{prefix}{k}" in taken:
            k += 1
        taken.add(f"{prefix}{k}")
        return f"{prefix}{k}", k + 1

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
    return mapping


def apply_mapping(text: str, mapping: dict) -> str:
    """단어 경계 기준 일괄 치환. 부분 문자열 오염 방지(`val` 이 `value` 를 건드리지 않게)."""
    if not text or not mapping:
        return text
    return _IDENT.sub(lambda m: mapping.get(m.group(0), m.group(0)), text)


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
