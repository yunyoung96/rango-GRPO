"""합성 에러 — ERROR_COND 학습이 실제로 발동하도록 (state, 실패시도, Coq에러) 를 만들어낸다.

## 왜 합성인가

ERROR_COND=1 로 프롬프트에 [ATTEMPT]/[ERROR] 섹션을 만들었지만, **학습 데이터에 에러 필드를
채우는 곳이 없다**(LmDataset 은 코퍼스에서 state/gold 만 만든다). 그대로 두면 그 기능은
60,000 step 동안 한 번도 발동하지 않는다.

진짜 롤아웃으로 모으려면 정리마다 모델 샘플링 + Coq 검증이 필요해 GPU·시간이 많이 든다.
대신 **실제로 가장 흔한 두 에러를 그대로 합성**한다 — 문구는 Coq 이 내는 것과 동일하다.

## 무엇을 합성하나 (rand200 실측 분포에 맞춤)

INVALID 7,981건의 실제 구성:
    이름 못 찾음                3,613 (45.3%)  ← 그중 78%가 지어낸 이름
    destruct 패턴 분기수 오류      238 ( 3.0%)

① **분기 수 오류** — gold 가 `destruct x as [...]` 이고 x 의 타입 생성자 수 N 을 알 때,
   틀린 분기 수로 시도했다 치고 Coq 문구를 그대로 만든다:
       [ATTEMPT] destruct x as [| a | b].
       [ERROR]   Expects a disjunctive pattern with 6 branches.
   → 에러의 숫자만 읽으면 정답 패턴을 알 수 있다. '에러를 읽는 습관'을 직접 가르친다.

② **이름 없음** — gold 가 `apply foo` / `unfold foo` 일 때, 그럴듯하지만 없는 이름으로
   시도했다 치고:
       [ATTEMPT] apply foo_bar_lemma.
       [ERROR]   The variable foo_bar_lemma was not found in the current environment.
   → 실제 실패의 45%가 이 형태다(환각 이름).

## 한계 (명시)

합성이므로 **모델이 실제로 낼 법한 실패 분포와는 다르다**. 진짜 on-policy 롤아웃이 더 낫다.
다만 (a) 에러 문구가 실제와 동일하고 (b) 정답이 에러로부터 유도 가능하다는 두 성질은 지켜져,
'에러를 읽어 고친다'는 능력 자체는 학습된다. on-policy 는 다음 라운드 과제.
"""
from __future__ import annotations

import hashlib
import os
import re
from typing import Optional

_AS = re.compile(r"\b(destruct|induction|case)\s+([A-Za-z_][\w']*)\s+as\s*\[([^\]]*)\]")
_APPLY = re.compile(r"\b(apply|eapply|unfold|rewrite)\s+([A-Za-z_][\w']*)")
_SUFFIX = ("_lemma", "_eq", "_spec", "_aux", "_comm", "_assoc", "_inv", "_le")


def _rate() -> float:
    return float(os.environ.get("SYNTH_ERROR_RATE", "0.3"))


def _pick(key: str) -> bool:
    """이 예제에 합성 에러를 붙일지 — 결정적(같은 예제는 항상 같은 결정)."""
    r = _rate()
    if r <= 0:
        return False
    if r >= 1:
        return True
    h = int(hashlib.md5(("se:" + (key or "")).encode()).hexdigest()[:8], 16)
    return (h % 1000) < r * 1000


def make(target: str, goal: str, injected: dict, key: str):
    """(attempted_tactic, coq_error) 또는 (None, None).

    injected: 프롬프트에 실제로 들어간 {이름: 정의문} — 여기 있는 타입만 분기수를 안다.
    """
    if os.environ.get("ERROR_COND", "0") != "1" or not _pick(key):
        return None, None
    h = int(hashlib.md5((key or "").encode()).hexdigest()[:8], 16)

    # ① 분기 수 오류 — gold 가 as 패턴을 쓰고, 대상 타입의 생성자 수를 알 때
    m = _AS.search(target or "")
    if m:
        tac, var, pat = m.group(1), m.group(2), m.group(3)
        n_true = len([p for p in pat.split("|")])
        if 2 <= n_true <= 32:
            wrong = 2 if n_true != 2 else 3          # 실제와 다른 분기 수로 시도했다 치고
            att = f"{tac} {var} as [{'|' * (wrong - 1)}]."
            err = f"Expects a disjunctive pattern with {n_true} branches."
            return att, err

    # ② 이름 없음 — gold 가 apply/unfold 계열일 때, 그럴듯하지만 없는 이름
    m2 = _APPLY.search(target or "")
    if m2:
        tac, name = m2.group(1), m2.group(2)
        fake = name + _SUFFIX[h % len(_SUFFIX)]
        if fake not in (goal or "") and fake not in injected:
            att = f"{tac} {fake}."
            kind = "reference" if tac in ("unfold",) else "variable"
            err = f"The {kind} {fake} was not found in the current environment."
            return att, err
    return None, None
