"""★ 지문색인 (Schulz, IJCAR 2012) — 항을 **고정 위치 몇 곳**의 자질 벡터로 요약한다.

## 왜 이것인가

판별트리·치환트리·경로색인과 성능이 대등한데(E 전체 6,000.2s vs NPDT 6,082.2s)
**유지비가 싸다**. 후보 집합이 스텝마다 바뀌는 우리 상황에 맞다.
그리고 **건전(sound)** 하다 — 지문 불일치는 비유니피케이션의 **필요조건**이라
통과한 것만 진짜로 검사하면 되고, **참인 매칭을 절대 안 버린다**.

## 자질 알파벳

    f   그 위치의 실제 최상위 함수기호
    A   그 위치가 **변수**
    B   그 위치가 **변수 아래**  (인스턴스화로 생길 수 있다)
    N   그 위치는 **어떤 인스턴스에서도 존재 불가**

## 위치

`FP6M` = ε, 1, 2, 3, 1.1, 1.2 (논문이 실측으로 고른 여섯 곳).
`ε` 는 머리, `1` 은 첫 인자, `1.1` 은 첫 인자의 첫 인자.

## 호환표

  유니피케이션(`apply`: 양쪽에 변수) 과 매칭(`rewrite`: 한쪽만 변수) 이 다르다.
  **매칭이 더 엄격**하다 — 예: `f1` 대 `A` 는 유니피케이션 Y, 매칭(s→t) N.

★ 전제: **양쪽 항이 elaborate 되어 있어야** 한다. 출력 형태끼리 비교하면
  notation·암묵인자 때문에 같은 항이 다른 지문을 낸다.
"""
from __future__ import annotations

import re
from typing import Optional

FP6M = ["", "1", "2", "3", "1.1", "1.2"]

_TOK = re.compile(r"\(|\)|@?[A-Za-z_][\w'.]*|[0-9]+|->|=>|,|:|[^\s()]+")

def tokenize(s: str) -> list[str]:
    return _TOK.findall(s or "")


def parse(s: str):
    """elaborate 된 Coq 항 → 트리.  ('app', 머리, [인자]) 또는 ('atom', 이름).

    elaborate 형태는 적용이 **병치**(`@eq T a b`)라 괄호만 보면 된다.
    실패하면 None — 호출부가 **통과**시켜야 한다(건전성).
    """
    toks = tokenize(s)
    pos = [0]

    def atom():
        if pos[0] >= len(toks):
            return None
        t = toks[pos[0]]
        if t == "(":
            pos[0] += 1
            n = app()
            if pos[0] < len(toks) and toks[pos[0]] == ")":
                pos[0] += 1
            return n
        if t == ")":
            return None
        pos[0] += 1
        return ("atom", t.lstrip("@"))

    def app():
        h = atom()
        if h is None:
            return None
        args = []
        while pos[0] < len(toks) and toks[pos[0]] != ")":
            a = atom()
            if a is None:
                break
            args.append(a)
        return ("app", h, args) if args else h

    try:
        return app()
    except Exception:
        return None


def _at(node, path: str):
    """위치 `path`("" · "1" · "1.2")의 부분항. 없으면 None."""
    if node is None:
        return None
    if path == "":
        return node
    for p in path.split("."):
        if node is None or node[0] != "app":
            return None
        i = int(p) - 1
        args = node[2]
        if i >= len(args):
            return None
        node = args[i]
    return node


def feature(node, path: str, variables: set) -> str:
    """그 위치의 자질 — `f<이름>` · `A` · `B` · `N`."""
    if node is None:
        return "N"
    # 경로를 따라가며 **도중에 변수를 만나면** 그 아래는 전부 B
    cur = node
    if path:
        for p in path.split("."):
            if cur is None:
                return "N"
            if cur[0] == "atom":
                return "B" if cur[1] in variables else "N"
            h = cur[1]
            if h[0] == "atom" and h[1] in variables:
                return "B"
            i = int(p) - 1
            if i >= len(cur[2]):
                return "N"
            cur = cur[2][i]
    if cur is None:
        return "N"
    if cur[0] == "atom":
        return "A" if cur[1] in variables else "f" + cur[1]
    h = cur[1]
    if h[0] == "atom":
        return "A" if h[1] in variables else "f" + h[1]
    return "N"


def fingerprint(term_str: str, variables: set, positions=FP6M) -> Optional[list]:
    n = parse(term_str)
    if n is None:
        return None
    return [feature(n, p, variables) for p in positions]


def _compat_uni(a: str, b: str) -> bool:
    """유니피케이션 호환 — `apply` 쪽."""
    if a == "N" or b == "N":
        # N 은 B 하고만 맞는다(그 위치가 변수 아래라 없을 수도 있다)
        return (a == "N" and b in ("N", "B")) or (b == "N" and a in ("N", "B"))
    if a in ("A", "B") or b in ("A", "B"):
        return True                       # 변수 쪽은 무엇과도
    return a == b                         # 둘 다 경직 기호 → 같아야 한다


def _compat_match(a: str, b: str) -> bool:
    """매칭 호환 (a=규칙 좌변, b=대상항) — `rewrite` 쪽. 유니피케이션보다 엄격.

    규칙 쪽 변수(A)는 무엇이든 받지만, **대상 쪽 변수는 규칙의 경직 기호를 못 받는다**
    (대상은 인스턴스화되지 않는다).
    """
    if a == "N" or b == "N":
        return (a == "N" and b in ("N", "B")) or (b == "N" and a in ("N", "B"))
    if a in ("A", "B"):
        return True
    if b in ("A", "B"):
        return b == "B"                   # 대상이 변수 자체면 규칙의 기호를 못 받는다
    return a == b


def compatible(fa, fb, mode: str = "uni") -> bool:
    """지문 두 개가 호환되나. 하나라도 없으면 **통과**(건전성)."""
    if fa is None or fb is None:
        return True
    f = _compat_uni if mode == "uni" else _compat_match
    return all(f(x, y) for x, y in zip(fa, fb))


# ── 바인더 벗기기 (peel) ─────────────────────────────────────────────────────
def peel(ty: str):
    """`forall (x : T) …, C` → (결론 C, 바인더 이름 집합).

    ★ 쉼표를 **괄호 깊이 0** 에서 찾아야 한다. 안 그러면
      `forall (rs' : forall _ : Asm.preg, Values.val) (…), C` 에서
      바인더 **안쪽** 쉼표를 잡아 결론이 `Values.val) (_ : …` 같은 쓰레기가 된다.
      (실측: 함수 타입 바인더를 가진 lemma 가 전부 이렇게 깨졌다.)
    """
    binders: set = set()
    c = (ty or "").strip()
    for _ in range(80):
        if not c.startswith("forall"):
            break
        d, i = 0, 6
        while i < len(c):
            ch = c[i]
            if ch in "([{":
                d += 1
            elif ch in ")]}":
                d -= 1
            elif ch == "," and d == 0:
                break
            i += 1
        if i >= len(c):
            break
        head = c[6:i]
        # `(x y : T)` 의 콜론 **앞** 이름만 바인더다
        for m in re.finditer(r"[\(\[\{]([^:]*?):", head):
            binders |= set(re.findall(r"[A-Za-z_][\w']*", m.group(1)))
        # 괄호 없는 `forall x y,` 형태
        bare = re.sub(r"[\(\[\{].*?[\)\]\}]", " ", head, flags=re.S)
        bare = bare.split(":")[0]
        binders |= set(re.findall(r"[A-Za-z_][\w']*", bare))
        c = c[i + 1:].strip()
    binders.discard("forall")
    binders.discard("_")
    return c, binders


# ── 판별트리 (discrimination tree) ───────────────────────────────────────────
#
#   지문색인은 **고정 위치 몇 곳**만 본다. 판별트리는 항을 전위순회한 **문자열 전체**를
#   색인한다 — 변수는 `*` 하나로 접히고, `*` 는 **부분항 통째로** 매칭한다.
#   위치를 고르지 않으므로 지문색인보다 **엄격히 더 강하다**.
#
#   우리는 후보를 어차피 전수 스캔하므로 트리 자료구조 자체는 필요 없다.
#   필요한 것은 **retrieval 판정** — 그것만 구현한다(트리를 만들면 같은 답이 더 빨리 나올 뿐).

def flatten(node, variables: set, out: list, depth: int = 0, maxd: int = 12):
    """전위순회 문자열. 변수는 `*`(그 자리 부분항 전체를 접는다)."""
    if node is None or depth > maxd:
        out.append("*"); return
    if node[0] == "atom":
        out.append("*" if node[1] in variables else node[1]); return
    h = node[1]
    if h[0] == "atom" and h[1] in variables:
        out.append("*"); return          # 머리가 변수면 적용 전체를 접는다
    out.append(h[1] if h[0] == "atom" else "?")
    out.append(f"/{len(node[2])}")       # arity — `f a` 와 `f a b` 를 가른다
    for a in node[2]:
        flatten(a, variables, out, depth + 1, maxd)


def dt_key(term_str: str, variables: set, maxd: int = 12):
    n = parse(term_str)
    if n is None:
        return None
    out: list = []
    flatten(n, variables, out, 0, maxd)
    return out


def _dt_walk(a: list, i: int, b: list, j: int, mode: str):
    """두 전위순회 문자열이 매칭되나. `*` 는 상대 쪽 **부분항 하나**를 통째로 건너뛴다."""
    if i >= len(a) and j >= len(b):
        return True
    if i >= len(a) or j >= len(b):
        return False
    x, y = a[i], b[j]
    if x == "*":
        k = _skip(b, j)
        return k is not None and _dt_walk(a, i + 1, b, k, mode)
    if y == "*":
        if mode == "match":
            return False                 # 대상 쪽 변수는 규칙의 경직 기호를 못 받는다
        k = _skip(a, i)
        return k is not None and _dt_walk(a, k, b, j + 1, mode)
    if x != y:
        return False
    return _dt_walk(a, i + 1, b, j + 1, mode)


def _skip(s: list, i: int):
    """`s[i]` 에서 시작하는 **부분항 하나**를 건너뛴 다음 위치."""
    if i >= len(s):
        return None
    if s[i] == "*":
        return i + 1
    i += 1
    if i < len(s) and s[i].startswith("/"):
        n = int(s[i][1:]); i += 1
        for _ in range(n):
            i = _skip(s, i)
            if i is None:
                return None
    return i


def dt_compatible(ka, kb, mode: str = "uni") -> bool:
    """판별트리 retrieval 판정. 하나라도 없으면 통과(건전성)."""
    if ka is None or kb is None:
        return True
    return _dt_walk(ka, 0, kb, 0, mode)


# ── 치환트리 (substitution tree) 상당 — 변수 **일관성**을 지킨다 ──────────────
#
#   판별트리는 변수를 `*` 로 접으므로 **같은 변수가 여러 번 나오면 일관돼야 한다**는
#   제약을 잃는다 — `f X X` 가 `f a b` 와도 매칭된다(위양성).
#   치환트리는 간선이 **치환**이라 그 일관성을 유지하고, 같은 질의에 대해
#   **더 촘촘한 상위집합**을 돌려준다.
#
#   우리는 전수 스캔이므로 트리 자체는 필요 없다. 필요한 것은 그 retrieval 관계 —
#   즉 **치환을 들고 하는 일차 매칭**이다. 그것만 구현한다.

def st_match(pat, term, variables: set, subst: Optional[dict] = None, depth: int = 0):
    """`pat` 을 `term` 에 일차 매칭. 되면 치환 dict, 안 되면 None.

    `pat` 쪽 변수만 채워진다(`term` 은 경직 — goal 이라 인스턴스화되지 않는다).
    같은 변수는 **같은 항**에만 대응해야 한다 — 이것이 판별트리와의 차이다.
    """
    if subst is None:
        subst = {}
    if pat is None or term is None or depth > 14:
        return subst                      # 판정 불가 → 통과(건전성)
    if pat[0] == "atom" and pat[1] in variables:
        prev = subst.get(pat[1])
        if prev is None:
            subst[pat[1]] = term
            return subst
        return subst if prev == term else None
    if pat[0] == "atom":
        return subst if (term[0] == "atom" and term[1] == pat[1]) else None
    # pat 이 적용
    ph = pat[1]
    if ph[0] == "atom" and ph[1] in variables:
        return subst                      # 머리가 변수 → 무엇과도 (고차 — 통과)
    if term[0] != "app":
        return None
    if len(pat[2]) != len(term[2]):
        return None
    s = st_match(ph, term[1], variables, subst, depth + 1)
    if s is None:
        return None
    for a, b in zip(pat[2], term[2]):
        s = st_match(a, b, variables, s, depth + 1)
        if s is None:
            return None
    return s


def st_compatible(pat_str: str, term_str: str, variables: set) -> bool:
    """치환트리 retrieval 판정. 파싱 실패는 통과."""
    p, t = parse(pat_str), parse(term_str)
    if p is None or t is None:
        return True
    return st_match(p, t, variables) is not None
