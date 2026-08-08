"""Coq 에러 메시지 기반 자가 교정 — 검증기가 알려준 정답으로 후보를 고쳐 즉시 재시도.

## 왜 이 방식인가 (실측 근거 2개)

**① 후보를 '제거'하는 개입은 무효다.**
환각 이름 필터(나쁜 후보 제거)를 rand200 에 붙인 결과:

    필터 ON  초당탐색 0.110 · 같은 정리 91개 40성공(44.0%)
    필터 OFF 초당탐색 0.118 · 같은 정리 91개 41성공(45.1%)   → 0.93배, 차이 -1 (p=1.000)

오프라인에서 INVALID 의 23.4% 를 걸러냈는데 **탐색량이 늘지 않았다**. INVALID 는 Coq 이
파싱·이름해석에서 빠르게 거절하므로 지워도 예산이 안 생긴다. 시간을 쓰는 건 VALID tactic 이다.
→ 유효한 개입은 **올바른 후보를 만들어 넣는 것**뿐이다.

**② Coq 이 정답을 알려준다.**
rand200 의 destruct 패턴 오류 238건에서 에러 메시지가 기대 분기 수를 명시한다:

    destruct chunk as [[c1 c2] [c3 c4] [c5 c6]].  → Expects a disjunctive pattern with 10 branches.
    destruct x as [[s m] e].                      → Expects a disjunctive pattern with 3 branches.
    destruct rs3 as [n|n1 t1].                    → Expects a disjunctive pattern with 6 branches.

분기 수 N 을 알면 `as [ | | ... ]`(빈 분기 N개)로 고칠 수 있다. 빈 분기는 Coq 이 인자를
자동 명명하므로 **per-branch arity 를 몰라도 항상 문법적으로 맞는다.**
타입 인덱스가 필요 없다 — 인덱스에 없는 타입(파싱 실패 57%)도 고쳐진다.

(아이디어 목록 19 '에러 메시지 repair loop' — 목록이 "가장 싼 baseline, ablation 필수"로 지목)
"""
from __future__ import annotations

import os
import re

# Coq 이 기대 분기 수를 알려주는 형태
_BRANCHES = re.compile(r"Expects a disjunctive pattern with (\d+) branches")
# `destruct x as [...]` / `induction x as [...]` — 패턴 부분을 통째로 교체한다.
#   중첩 대괄호(`as [[c1 c2] [c3 c4]]`)가 있으므로 깊이를 세어 닫는 위치를 찾는다.
_HEAD = re.compile(r"^(\s*)(destruct|induction|case)\s+(.+?)\s+as\s*\[")


def _close_bracket(s: str, open_at: int) -> int:
    """open_at 의 '[' 에 대응하는 ']' 위치. 못 찾으면 -1."""
    depth = 0
    for i in range(open_at, len(s)):
        if s[i] == "[":
            depth += 1
        elif s[i] == "]":
            depth -= 1
            if depth == 0:
                return i
    return -1


def repair(tactic: str, error: str) -> list:
    """에러 메시지를 보고 고친 후보들. 못 고치면 빈 리스트.

    현재 대응: **분기 수 불일치**(Expects a disjunctive pattern with N branches).
    """
    if os.environ.get("ERROR_REPAIR", "0") != "1":
        return []
    m = _BRANCHES.search(error or "")
    if not m:
        return []
    n = int(m.group(1))
    if n <= 0 or n > 64:
        return []
    h = _HEAD.match(tactic or "")
    if not h:
        return []
    open_at = tactic.index("[", h.end() - 1)
    close_at = _close_bracket(tactic, open_at)
    if close_at < 0:
        return []
    # 빈 분기 N개 — Coq 이 각 생성자의 인자를 자동 명명한다(arity 를 몰라도 맞음)
    fixed_pat = "[" + "|" * (n - 1) + "]"
    out = tactic[:open_at] + fixed_pat + tactic[close_at + 1:]
    return [out] if out.strip() != (tactic or "").strip() else []
