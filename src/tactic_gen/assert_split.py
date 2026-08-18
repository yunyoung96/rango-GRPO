"""검색 실패한 gold tactic 을 **assert 2단계**로 바꾼다.

## 왜

gold lemma 가 검색 결과에 없으면, 익명화된 프롬프트에서 모델은 **읽을 수 없는 이름**을
지어내야 한다 — 원리적으로 불가능하다. 이름 대신 **명제**를 세우면 프롬프트에서 읽을 수
있는 것만으로 증명이 이어진다.

    원래 :  t1; apply L; t3.

    변환 :  assert (L 의 statement) as H.
            - exact L.            ← 이 goal 이 곧 L 의 statement → 검색이 L 을 1~5위로 찾는다
            - t1; apply H; t3.    ← 원래 구조 그대로, L→H 치환만

## 왜 assert 를 맨 앞에 두나

`t1; apply L; t3` 처럼 lemma 가 복합 tactic **중간**에 있어도(실측 16.0%),
L 은 전역 lemma 라 그 statement 가 **컨텍스트와 무관하게 성립**한다. 따라서 assert 를
맨 앞으로 빼고 원래 tactic 을 통째로 둘째 bullet 에 넣으면 `;` 구조가 보존된다.

## 언제 쓰나

**검색이 성공했으면 쓰지 않는다.** assert 는 증명을 길게 만들고 "명제 생성" 이라는 어려운
과제를 더한다. gold premise 가 top-K 안에 있으면 원래 gold tactic 이 1순위다.
"""
from __future__ import annotations

import re

_DECL = re.compile(
    r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|Instance|Axiom|"
    r"Proposition|Example|Let|Program\s+\w+)\s+"
    r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)\s*", re.S)

# ★ bullet 은 쓰지 않는다 — 중괄호만 쓴다.
#
#   Coq 은 **현재 열려 있는** bullet 안에서 같은 bullet 을 다시 쓰면 거부한다:
#       [Focus] Wrong bullet -: Current bullet - is not finished.
#   그런데 proof_script 를 봐도 **어떤 bullet 이 아직 안 닫혔는지 알 수 없다**
#   (과거에 쓰인 `-` 가 이미 닫혔는지 열려 있는지 구분이 불가능하다).
#   반면 `{ }` 는 bullet 깊이와 무관하게 항상 안전하다 — 중첩 `- +` 안에서도 오류 0건(실측).
_BULLETS = ["-", "+", "*", "--", "++", "**"]


def has_implicit(premise_text: str) -> bool:
    """선언부에 암묵인자 `{A}` 가 있나. 있으면 `exact @L` 로 받아야 한다."""
    t = re.sub(r"\(\*.*?\*\)", " ", premise_text or "", flags=re.S).strip()
    m = _DECL.match(t)
    if not m:
        return False
    rest = t[m.end():]
    depth = 0
    for i, c in enumerate(rest):
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif depth == 0 and c == "{":
            return True
        elif depth == 0 and c == ":" and not rest.startswith(":=", i):
            return False
    return False


def statement_of(premise_text: str) -> str | None:
    """premise 선언에서 **타입(statement)** 만 뽑는다.

    `Lemma foo : forall n, P n.`            → `forall n, P n`
    `Lemma foo (n : nat) : P n.`            → `forall (n : nat), P n`   (인자를 forall 로)
    본문(`:= ...`)이 있는 정의는 대상이 아니다(None).
    """
    t = re.sub(r"\(\*.*?\*\)", " ", premise_text or "", flags=re.S).strip()
    m = _DECL.match(t)
    if not m:
        return None
    rest = t[m.end():]
    # `:= 본문` 이 있으면 정의라 assert 대상이 아니다
    depth = 0
    binder_end = -1
    colon = -1
    i = 0
    while i < len(rest):
        c = rest[i]
        if c in "({[":
            depth += 1
        elif c in ")}]":
            depth -= 1
        elif depth == 0 and rest.startswith(":=", i):
            return None
        elif depth == 0 and c == ":" and not rest.startswith(":=", i):
            colon = i
            break
        i += 1
    if colon < 0:
        return None
    binders = rest[:colon].strip()
    body = rest[colon + 1:].strip().rstrip(".").strip()
    if not body:
        return None
    # ★ `Definition foo : nat := 3.` 처럼 본문이 있으면 정의라 assert 대상이 아니다.
    #   `:` 를 먼저 만나므로 위 루프에서 못 걸러진다 → body 에서 다시 본다.
    if re.search(r"(?<![:<>=]):=(?!=)", body):
        return None
    if binders:
        # `(n : nat) (m : nat)` → `forall (n : nat) (m : nat),`
        # ★ 암묵인자 `{A}` 는 `forall {A}` 가 **Coq 문법 오류**다 → 괄호를 벗겨 `A` 로.
        #   타입은 Coq 이 추론한다(`forall A (l : list A), …` 는 유효).
        binders = re.sub(r"\{([^{}]*)\}", r"\1", binders)
        return f"forall {binders}, {body}"
    return body


def _rename(tac: str, old: str, new: str) -> str:
    """tactic 안의 lemma 이름을 바꾼다. 한정이름(`Z.le_trans`)도 통째로."""
    pat = re.compile(r"(?<![\w'.])((?:[A-Za-z_][\w']*\.)*)" + re.escape(old) + r"(?![\w'])")
    return pat.sub(new, tac)


def pick_bullet(proof_script: str) -> str:
    """이미 쓰인 bullet 과 겹치지 않는 것을 고른다.

    ⚠ **신뢰할 수 없다** — 현재 열려 있는 bullet 을 알 방법이 없기 때문이다.
      과거에 `-` 가 쓰였어도 이미 닫혔을 수 있고, 안 보여도 열려 있을 수 있다.
      `transform` 은 기본적으로 중괄호를 쓴다. 이 함수는 호환용으로만 남긴다.
    """
    used = set(re.findall(r"^\s*([-+*]{1,3})\s", proof_script or "", re.M))
    for b in _BULLETS:
        if b not in used:
            return b
    return "{"                      # 전부 쓰였으면 중괄호로 (항상 안전)


def transform(gold_tactic: str, lemmas, proof_script: str = "",
              state: str = "", use_bullet: bool = False) -> str | None:
    """(use_bullet 은 **쓰지 말 것** — 아래 경고 참조. 호환용으로만 남긴다.)"""
    """gold tactic → assert 형태. `lemmas` 는 [(이름, premise 텍스트), …].

    **여러 개도 지원한다** (`t1; apply L1; apply L2; tn` 같은 경우). 그때는 중괄호가
    안전하다 — bullet 은 중첩 규칙이 까다로워 개수가 늘면 깨지기 쉽지만, `{ }` 는
    나란히 놓으면 되고 이미 쓰인 bullet 과 충돌하지도 않는다.

        assert (S1) as H0. { exact L1. }
        assert (S2) as H1. { exact L2. }
        t1; apply H0; apply H1; tn.

    변환 불가(정의라 statement 가 없다 / 치환이 안 된다)면 None.
    """
    if isinstance(lemmas, str):
        lemmas = [(lemmas, proof_script)]        # 옛 호출 형태 방어
    used = _taken_names(state, proof_script)
    lines, inner = [], gold_tactic.strip()
    n_ok = 0
    for nm, ptext in lemmas:
        stmt = statement_of(ptext)
        if not stmt:
            continue
        h = _fresh(used)
        used.add(h)
        base = nm.split(".")[-1]
        new_inner = _rename(inner, base, h)
        if new_inner == inner:
            continue                              # 이 lemma 는 tactic 에 안 나온다
        inner = new_inner
        # ★ `{A}` 를 `A` 로 바꿔 명시했으므로 lemma 도 **@** 로 받아야 타입이 맞는다.
        #   안 그러면 "has type forall l1 l2 : list ?A" 로 불일치한다(실측).
        ref = ("@" + nm) if has_implicit(ptext) else nm
        lines.append((stmt, h, ref))
        n_ok += 1
    if not n_ok:
        return None
    if use_bullet and n_ok == 1:
        # ⚠ **깨진다. 쓰지 말 것.** 바깥 bullet 이 아직 **열려 있으면** Coq 이 거부한다:
        #     split.
        #     - assert (…) as H.
        #     - exact L.        ← [Focus] Wrong bullet -: Current bullet - is not finished.
        #   pick_bullet 으로는 못 막는다 — proof_script 의 `-` 가 이미 닫혔는지 아직
        #   열려 있는지 구분할 방법이 없기 때문이다(실증: scripts/verify_assert_split.py ⑩).
        b = pick_bullet(proof_script)
        if b != "{":
            stmt, h, nm = lines[0]
            return (f"assert ({stmt}) as {h}.\n{b} exact {nm}.\n{b} {inner}")
    out = [f"assert ({stmt}) as {h}. {{ exact {nm}. }}" for stmt, h, nm in lines]
    out.append(inner)
    return "\n".join(out)


def _taken_names(state: str, proof_script: str) -> set:
    """goal 가설블록 + 지금까지의 증명에 등장한 이름 전부.

    ★ 가설블록만 보면 부족하다 — 증명 앞부분에서 `intros H0 H1` 처럼 이름을 만들었으면
      그것도 피해야 한다. 정규화(v8)는 **지역 가설을 건드리지 않으므로** 여기서 고른
      이름이 프롬프트에 그대로 나타난다.
    """
    body = (state or "").split("[GOAL]")[0]
    out = set()
    for n in re.findall(r"^\s*([A-Za-z_][\w']*(?:\s*,\s*[A-Za-z_][\w']*)*)\s*:",
                        body, re.M):
        out |= {x.strip() for x in n.split(",")}
    out |= set(re.findall(r"[A-Za-z_][\w']*", proof_script or ""))
    return out


def _fresh(used: set, want: str = "Hasrt") -> str:
    if want not in used:
        return want
    i = 0
    while f"{want}{i}" in used:
        i += 1
    return f"{want}{i}"


def fresh_hyp(state: str, want: str = "Hasrt") -> str:
    """goal 가설블록과 겹치지 않는 이름."""
    body = (state or "").split("[GOAL]")[0]
    names = set(re.findall(r"^\s*([A-Za-z_][\w']*(?:\s*,\s*[A-Za-z_][\w']*)*)\s*:",
                           body, re.M))
    flat = set()
    for n in names:
        flat |= {x.strip() for x in n.split(",")}
    if want not in flat:
        return want
    for i in range(100):
        if f"{want}{i}" not in flat:
            return f"{want}{i}"
    return want + "_x"


# ── lemma **적용 항** 추출 ────────────────────────────────────────────────────
#   `have := L a b.` 같은 형태는 `L` 만 assert 하면 인자 개수가 어긋난다.
#   `assert (forall R p q, …) as H.` 로 만들면 H 는 인자가 전부 명시적인데
#   원래 `L a b` 는 암묵인자가 채워진 상태라 `H a b` 가 다른 것을 가리킨다(실측 실패).
#
#   → **`L` 과 그 인자들을 통째로** assert 한다: `Check (L a b).` 로 타입을 얻고
#     `assert (그 타입) as H. { exact (L a b). }` + `have := H.` 로 바꾼다.
#     인자가 이미 적용된 형태라 개수 문제가 원천적으로 없다.

# 인자 목록이 끝나는 지점 — tactic 구분자·수식어
_ARG_STOP = re.compile(
    r"^\s*(?:;|\.|\||\]|\}|\bin\b|\bwith\b|\bas\b|\bby\b|\bat\b|\busing\b|\beqn\b)")


def extract_application(tac: str, lemma: str):
    """tactic 에서 `lemma` 가 쓰인 **항 전체**(lemma + 인자들)를 뽑는다.

    반환 (항 문자열, 시작, 끝) 또는 None.
    `apply L.` → `L` · `have := L a b.` → `L a b` · `rewrite (L x) in H` → `(L x)`
    """
    base = lemma.split(".")[-1]
    m = re.search(r"(?<![\w'.])((?:[A-Za-z_][\w']*\.)*)" + re.escape(base) + r"(?![\w'])",
                  tac)
    if not m:
        return None
    start, i = m.start(), m.end()
    n = len(tac)
    while i < n:
        if _ARG_STOP.match(tac[i:]):
            break
        c = tac[i]
        if c in "([{":                       # 괄호는 균형까지 통째로
            d, j = 0, i
            while j < n:
                if tac[j] in "([{":
                    d += 1
                elif tac[j] in ")]}":
                    d -= 1
                    if d == 0:
                        j += 1
                        break
                j += 1
            i = j
            continue
        if c.isspace():
            i += 1
            continue
        if c in ")]}":                       # 우리 것이 아닌 닫는 괄호
            break
        # 식별자·숫자·와일드카드만 인자로 인정 (연산자가 오면 항이 아니다)
        mm = re.match(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*|\d+|_", tac[i:])
        if not mm:
            break
        i += mm.end()
    return tac[start:i].rstrip(), start, i


def transform_with_types(gold_tactic: str, applications, state: str = "",
                         proof_script: str = ""):
    """`applications` = [(항 문자열, 그 항의 타입)] 로 assert 를 만든다.

    타입은 호출부가 `Check (항).` 으로 **Coq 에게 물어서** 넘긴다 — Section 변수·암묵인자·
    인스턴스화가 전부 정리된 형태라 원문 statement 보다 정확하다.
    """
    used = _taken_names(state, proof_script)
    inner = gold_tactic.strip()
    lines = []
    # ★ 긴 항부터 치환해야 부분 치환이 안 생긴다 (`L a b` 를 먼저, 그 다음 `L`)
    for term, ty in sorted([a for a in applications if a[1]],
                           key=lambda a: -len(a[0])):
        # ★ 타입에 evar(`?h`)가 있으면 assert 못 한다 — Coq 이 미결정 항을 그대로
        #   출력한 것이고, 그대로 쓰면 `Syntax error … after [term level 200]` 이 난다.
        if re.search(r"\?[A-Za-z_]", ty):
            return None
        # ★ `rewrite <-?L` / `rewrite ?L` 은 **여러 번** 재작성한다. 한 번만 치환하면
        #   `Found no subterm matching` 이 난다 → 변환하지 않는다(실측).
        if re.search(r"[?!]\s*" + re.escape(term.split()[0]), gold_tactic):
            return None
        if term not in inner:
            continue
        h = _fresh(used)
        used.add(h)
        # ★ **모든** 등장을 바꾼다. 한 번만 바꾸면 나머지가 원래 이름으로 남아
        #   `Found no subterm matching` 이 난다(실측).
        inner = inner.replace(term, h)
        lines.append((ty, h, term))
    if not lines:
        return None
    # ★ 치환 후에도 원래 이름이 남아 있으면(다른 형태로 쓰인 것) 변환을 포기한다 —
    #   섞여 있으면 `The variable Hasrt was not found` 같은 어긋남이 생긴다.
    for _ty, _h, term in lines:
        head = re.match(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*", term)
        if head and re.search(r"(?<![\w'.])" + re.escape(head.group(0).split(".")[-1])
                              + r"(?![\w'])", inner):
            return None
    out = [f"assert ({ty}) as {h}. {{ exact ({term}). }}" for ty, h, term in lines]
    out.append(inner)
    return "\n".join(out)
