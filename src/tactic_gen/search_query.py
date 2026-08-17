"""goal 을 **Coq SearchPattern 질의**로 바꾼다.

## 왜

TF-IDF 검색은 gold lemma 의 34.2% 를 풀 안에 두고도 못 뽑고, 32.4% 는 풀에 아예 없다
(scripts/diagnose_premise_miss.py). 후보를 100→1000 으로 늘려도 +5.9pp 뿐이라 수량으로는
해결되지 않는다. 반면 Coq 은 **그 시점에 실제로 로드된 모든 것**을 알고, `SearchPattern` 으로
goal 모양에 맞는 lemma 를 직접 찾아준다.

실측: TF-IDF 가 1000 위 안에도 못 넣던 `Zlt_le_succ` 를
`SearchPattern (Z.succ _ <= _)` 이 **38ms 에 3건 중 2위**로 반환했다.

## 핵심 설계 — 추상화 사다리

패턴이 너무 구체적이면 0건, 너무 일반적이면 수백 건이 나온다. 그래서 goal 결론 트리를
**여러 추상화 수준**으로 만들어 좁은 것부터 시도하고, 결과가 모자라면 넓힌다.

    goal: Z.succ 0 <= a
      L0  Z.succ 0 <= a          (원본 — 보통 0건, 변수가 그대로라 안 맞는다)
      L1  Z.succ _ <= _          (잎을 _ 로)            ← 실측에서 3건, gold 포함
      L2  Z.succ _ <= _          (깊이 2 까지 유지)
      L3  _ <= _                 (head 만)              ← 192건, 노이즈

rewrite 용으로는 goal 의 **부분항**을 등식 한 변으로 두는 질의도 만든다:
`SearchPattern (부분항모양 = _)`.

## 왜 파서를 재사용하나

`applicable.py` 가 이미 Coq 항을 트리로 파싱하고 notation 우선순위를 안다. 그 트리를 다시
문자열로 찍되 원하는 깊이 아래를 `_` 로 바꾸면 그대로 질의가 된다. 파싱과 질의가 같은
구조 이해를 공유하므로 어긋나지 않는다.
"""
from __future__ import annotations

import re

from tactic_gen.applicable import (_INFIX, goal_conclusion, parse, subterms)

# 질의에 쓰면 안 되는 head — 너무 흔해 수백 건이 나오거나 문법이 깨진다.
_TOO_COMMON = {"eq", "and", "or", "not", "iff", "True", "False"}


def local_names(state: str) -> set[str]:
    """proof state 의 가설 블록에 선언된 **지역 이름**.

    ★ 이걸 안 지우면 질의가 통째로 헛돈다. `SearchPattern (Z.succ 0 <= a)` 의 `a` 는
      이 증명 안에서만 사는 변수라 어떤 lemma 에도 없다 → 항상 0건. 지역 이름은 전부
      `_` 로 바꿔야 "모양"만 남는다.

    형식: `a: Z` / `f, f0: float` / `H: 0 < a` 가 빈 줄 전까지 이어진다.
    """
    s = (state or "").split("[GOAL]")[0]
    if "=====" in s:
        s = s.split("=====")[0]
    else:
        parts = re.split(r"\n\s*\n", s)
        s = parts[0] if len(parts) > 1 else ""
    out: set[str] = set()
    for ln in s.split("\n"):
        m = re.match(r"^\s*([A-Za-z_][\w']*(?:\s*,\s*[A-Za-z_][\w']*)*)\s*:", ln)
        if m:
            out |= {x.strip() for x in m.group(1).split(",")}
    return out


def _fmt(t, depth: int, loc: set[str], cur: int = 0) -> str:
    """트리를 Coq 항 문자열로. cur >= depth 인 가지와 **지역 이름**을 `_` 로 접는다."""
    if t is None:
        return "_"
    if cur >= depth:
        return "_"
    k = t[0]
    if k == "id":
        return "_" if t[1].split(".")[-1] in loc else t[1]
    if k == "opq":
        return "_"                                   # 못 읽은 덩어리는 와일드카드
    if k == "app":
        return f"({_fmt(t[1], depth, loc, cur)} {_fmt(t[2], depth, loc, cur + 1)})"
    if k == "op":
        return (f"({_fmt(t[2], depth, loc, cur + 1)} {t[1]} "
                f"{_fmt(t[3], depth, loc, cur + 1)})")
    return "_"


def _strip_outer(s: str) -> str:
    """최상위 괄호 한 겹 제거 — `SearchPattern ((a <= b)).` 도 되지만 읽기 나쁘다."""
    if s.startswith("(") and s.endswith(")"):
        d = 0
        for i, c in enumerate(s):
            if c == "(":
                d += 1
            elif c == ")":
                d -= 1
                if d == 0:
                    return s[1:-1] if i == len(s) - 1 else s
    return s


def _informative(pat: str) -> bool:
    """`_`, `(_ _)`, `_ = _` 처럼 정보가 없는 패턴은 버린다(수백 건이 나온다).

    ★ 연산자만 남은 `_ * _ = _ * _` 는 **유효하다** — 실측에서 13건을 정확히 반환했다.
      이름만 정보로 치면 이런 순수 대수 패턴을 통째로 버리게 된다.
    """
    core = pat.replace("(", " ").replace(")", " ")
    toks = [x for x in core.split() if x and x != "_"]
    if not toks:
        return False
    named = [x for x in toks if x not in _INFIX]
    ops = [x for x in toks if x in _INFIX]
    if named:
        return not (len(named) == 1 and named[0] in _TOO_COMMON and len(ops) == 0)
    return len(ops) >= 2                            # `_ = _` (1개) 는 버리고 `_*_=_*_` 는 남긴다


def goal_patterns(goal_state: str, max_q: int = 4) -> list[str]:
    """goal 결론에서 **좁은 것부터** SearchPattern 인자 목록을 만든다.

    apply 대상(결론 전체 모양)을 겨냥한다. 반환은 중복 제거된 순서 있는 리스트.
    """
    g = parse(goal_conclusion(goal_state))
    if g is None:
        return []
    loc = local_names(goal_state)
    out: list[str] = []
    for d in (3, 2, 4, 1):                          # 2~3 이 실측에서 가장 잘 맞았다
        p = _strip_outer(_fmt(g, d, loc))
        if p not in out and _informative(p):
            out.append(p)
    return out[:max_q]


def _size(t):
    if t is None or t[0] in ("id", "opq"):
        return 1
    return 1 + (_size(t[1]) + _size(t[2]) if t[0] == "app" else _size(t[2]) + _size(t[3]))


def rewrite_patterns(goal_state: str, max_q: int = 4) -> list[str]:
    """rewrite 대상: goal 의 **부분항**이 등식 한 변에 오는 lemma 를 찾는다.

    `SearchPattern (f _ _ = _)` 꼴. 부분항이 클수록 좁으므로 큰 것부터 쓴다.
    ★ 이미 등식/논리연산인 부분항에 `= _` 를 또 붙이면 `(a = b) = _` 가 되어 헛돈다.
      순수 항(등식이 아닌 것)만 왼변 후보로 쓴다.
    """
    g = parse(goal_conclusion(goal_state))
    if g is None:
        return []
    loc = local_names(goal_state)
    LOGIC = {"=", "<->", "->", "/\\", "\\/", "<", "<=", ">", ">=", "<>"}
    subs = [s for s in subterms(g)
            if s[0] == "app" or (s[0] == "op" and s[1] not in LOGIC)]
    subs.sort(key=_size, reverse=True)
    out: list[str] = []
    for s in subs:
        for d in (2, 3):
            p = _strip_outer(_fmt(s, d, loc))
            if not _informative(p):
                continue
            q = f"{p} = _"
            if q not in out:
                out.append(q)
            if len(out) >= max_q:
                return out
    return out


def queries(goal_state: str, n_apply: int = 3, n_rw: int = 3) -> list[str]:
    """실행할 SearchPattern 문장 전체. 좁은 질의부터 나온다."""
    qs = []
    for p in goal_patterns(goal_state, n_apply):
        qs.append(f"SearchPattern ({p}).")
    for p in rewrite_patterns(goal_state, n_rw):
        qs.append(f"SearchPattern ({p}).")
    seen: set[str] = set()
    out = []
    for q in qs:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out
