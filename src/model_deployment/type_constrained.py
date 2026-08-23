"""타입 제약 후보 생성 — 모델이 못 만드는 **올바른 destruct/induction 패턴**을 시스템이 만들어 넣는다.

## 왜 '제거'가 아니라 '추가'인가 (실측)

환각 이름 필터(나쁜 후보 **제거**)를 붙여 rand200 을 돌린 결과:

    필터 ON  초당탐색 0.110   같은 정리 91개 40 성공 (44.0%)
    필터 OFF 초당탐색 0.118   같은 정리 91개 41 성공 (45.1%)
    → 탐색속도 비 0.93배, 성공률 차이 -1 (McNemar p=1.000)

오프라인에서 INVALID 의 23.4% 를 걸러냈는데도 **탐색량이 전혀 늘지 않았다.**
이유: INVALID 는 Coq 이 파싱·이름해석 단계에서 **빠르게** 거절한다. 시간을 쓰는 건
실제로 실행되는 VALID tactic 이다. 따라서 나쁜 후보를 지워도 예산이 안 생긴다.

→ **후보를 지우는 개입은 원리적으로 무효.** 모델이 만들지 못하는 **올바른 후보를 추가**해야 한다.

## 무엇을 추가하나

`destruct v` / `induction v` 에서 v 의 타입 정의를 조회해 **정확한 분기 패턴**을 만든다:

    val := | Vundef | Vint: int->val | Vlong: int64->val | Vfloat: float->val
           | Vsingle: float32->val | Vptr: block->ptrofs->val
    →  destruct v as [| x0 | x1 | x2 | x3 | x4 x5]
       (생성자 6개, 각 인자수 0/1/1/1/1/2 → 바인더 개수가 정확히 일치)

이건 모델이 반복해서 틀리는 부분이다(`Expects a disjunctive pattern with N branches` 238건).
arity 는 **시스템이 결정하므로 틀릴 수 없다**(아이디어 목록 18 TyFlow 의 최소판).

원 후보는 그대로 두고 **변형을 덧붙이기만** 한다 — 탐색 폭이 줄지 않는다.
"""
from __future__ import annotations
import rango_defaults as _D   # ★ 프로덕션 기본값 단일 출처

import json
import os
import re
from typing import Optional

_IDENT = re.compile(r"[A-Za-z_][\w']*")
# `destruct v.` (패턴 없음) — 이미 유효한 Coq 이므로 이득은 작다(명시적 이름 부여 정도).
_TARGET = re.compile(r"^(\s*)(destruct|induction)\s+([A-Za-z_][\w']*)\s*\.\s*$")
# ★ 진짜 표적: 모델이 **틀린 분기 수**의 패턴을 쓴 경우.
#   `Expects a disjunctive pattern with N branches` 가 rand200 에서 238건.
#   기존 패턴의 분기 수가 실제 생성자 수와 다르면 **정확한 패턴으로 고친 변형**을 추가한다.
_TARGET_AS = re.compile(r"^(\s*)(destruct|induction)\s+([A-Za-z_][\w']*)\s+as\s*\[([^\]]*)\]\s*(.*)$")
_TYPE_HEAD = re.compile(r"\b(Inductive|CoInductive|Variant)\b")

_IDX: Optional[dict] = None


def _index() -> dict:
    global _IDX
    if _IDX is None:
        path = _D.get("FUNC_DEFS_PATH")
        try:
            with open(path) as f:
                _IDX = json.load(f)
        except OSError:
            _IDX = {}
    return _IDX


def hyp_type(goal: str, var: str) -> Optional[str]:
    """가설 블록에서 `var : T` 의 T head."""
    hyp = (goal or "").split("\n\n", 1)[0]
    for ln in hyp.split("\n"):
        m = re.match(r"^\s*([\w', ]+?)\s*:\s*(.+)$", ln)
        if not m:
            continue
        names = [x for x in re.split(r"[,\s]+", m.group(1).strip()) if x]
        if var in names:
            t = m.group(2).strip().split()
            return t[0].split(".")[-1] if t else None
    return None


def ctor_arities(defn: str) -> Optional[list]:
    """정의문 → 생성자별 인자 개수 리스트. Inductive 계열이 아니거나 잘렸으면 None.

    `| Vint: int -> val` → 화살표 개수 = 1.  `| Vundef: val` → 0.
    `| cons (x:A) (l:list A)` (괄호형) → 괄호 그룹 수.
    """
    if ":=" not in defn or "..." in defn:
        return None
    head, body = defn.split(":=", 1)
    if not _TYPE_HEAD.search(head):
        return None
    out = []
    for part in body.split("|"):
        part = part.strip().rstrip(".").strip()
        if not part:
            continue
        m = re.match(r"[A-Za-z_][\w']*", part)
        if not m:
            return None                    # 예상 못한 형태 → 안전하게 포기
        rest = part[m.end():].strip()
        if rest.startswith(":"):
            # `: A -> B -> T` 형태. 최상위 '->' 개수 = 인자 수
            sig = rest[1:]
            depth = 0
            n = 0
            i = 0
            while i < len(sig) - 1:
                c = sig[i]
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                elif depth == 0 and sig[i:i + 2] == "->":
                    n += 1
                    i += 1
                i += 1
            out.append(n)
        else:
            out.append(len(re.findall(r"\([^()]*\)", rest)))   # 괄호형 인자
    return out or None


def canonical_pattern(arities: list, used: set) -> str:
    """생성자별 인자수 → `as [| x0 | x1 x2 | ...]`. used 와 겹치지 않는 신선한 이름 사용."""
    k = 0
    groups = []
    for a in arities:
        names = []
        for _ in range(a):
            while f"x{k}" in used:
                k += 1
            names.append(f"x{k}")
            used.add(f"x{k}")
            k += 1
        groups.append(" ".join(names))
    return "[" + "|".join(groups) + "]"


def _arities_for(goal: str, var: str):
    """goal 의 변수 var 타입 → 생성자 인자수 리스트(못 구하면 None)."""
    tname = hyp_type(goal, var)
    if not tname:
        return None
    slot = _index().get(tname)
    if not slot:
        return None
    defn = slot if isinstance(slot, str) else next(iter(slot.values()), None)
    if not defn:
        return None
    ar = ctor_arities(defn)
    return ar if (ar and len(ar) >= 2) else None


def extra_candidates(tactic: str, goal: str) -> list:
    """이 후보에서 파생할 **올바른 패턴** 변형들. 없으면 빈 리스트."""
    if os.environ.get("TYPE_CONSTRAINED", "0") != "1":
        return []
    # ① 이미 as 패턴이 있는데 **분기 수가 틀린** 경우 → 고친 변형 추가 (주 표적)
    ma = _TARGET_AS.match(tactic or "")
    if ma:
        indent, tac, var, pat, tail = ma.groups()
        ar = _arities_for(goal, var)
        if not ar:
            return []
        have = len(pat.split("|"))
        if have == len(ar):
            return []                       # 분기 수가 이미 맞음 → 손대지 않음
        used = set(_IDENT.findall(goal or "")) | set(_IDENT.findall(pat))
        fixed = canonical_pattern(ar, used)
        tail = (tail or "").strip()
        if not tail:
            tail = "."                       # `as [...]` 뒤에 아무것도 없으면 마침표
        return [f"{indent}{tac} {var} as {fixed}{tail}"]   # ★ 공백 없이 이어붙임(`] .` 는 문법오류)
    # ② 패턴이 아예 없는 경우 → 명시적 패턴 변형 추가(부수적)
    m = _TARGET.match(tactic or "")
    if not m:
        return []
    indent, tac, var = m.group(1), m.group(2), m.group(3)
    ar = _arities_for(goal, var)
    if not ar:
        return []
    used = set(_IDENT.findall(goal or ""))
    pat = canonical_pattern(ar, used)
    return [f"{indent}{tac} {var} as {pat}."]


def augment_result(result, goal: str):
    """ModelResult 에 타입 기반 정확 패턴 후보를 **덧붙인다**(기존 후보는 유지)."""
    if os.environ.get("TYPE_CONSTRAINED", "0") != "1":
        return result, 0
    tactics = getattr(result, "next_tactic_list", None)
    if not tactics:
        return result, 0
    added = []
    seen = set(tactics)
    for t in list(tactics):
        for e in extra_candidates(t, goal):
            if e not in seen:
                seen.add(e)
                added.append(e)
    if not added:
        return result, 0
    n = len(tactics)
    result.next_tactic_list = tactics + added
    for attr, fill in (("score_list", None), ("num_tokens_list", None), ("costs", 0.0)):
        v = getattr(result, attr, None)
        if isinstance(v, list) and len(v) == n:
            # 추가 후보의 점수는 원본 최고점과 동일하게 둔다(탐색이 먼저 시도하도록)
            best = max(v) if (v and fill is None) else fill
            setattr(result, attr, v + [best] * len(added))
    return result, len(added)
