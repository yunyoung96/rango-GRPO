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

import os
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
              state: str = "", use_bullet: bool = False,
              suffix: str = "", premises=None) -> str | None:
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
    used = _taken_names(state, proof_script, suffix, premises)
    base = _fresh_base(used)
    lines, inner = [], gold_tactic.strip()
    n_ok = 0
    for nm, ptext in lemmas:
        stmt = statement_of(ptext)
        if not stmt:
            WHY.append("statement 추출 실패(정의/본문있음)")
            continue
        # ★ 이 경로(이름 기반 폴백)도 위험 감지를 거쳐야 한다. 안 거치면 mathcomp
        #   notation 이 그대로 들어가 깨진다 — 실측에서 폴백 77건이 감지를 우회했다.
        if risky_type(stmt):
            if _no("위험 타입: " + _ty_kind(stmt)) is None:
                continue
        if risky_tactic(gold_tactic):
            if _no("위험 tactic: " + _tac_kind(gold_tactic)) is None:
                continue
        h = _fresh(used, base)
        used.add(h)
        base = nm.split(".")[-1]
        new_inner = _rename(inner, base, h)
        if new_inner == inner:
            WHY.append("lemma 이름이 tactic 에 없음")
            continue                              # 이 lemma 는 tactic 에 안 나온다
        inner = new_inner
        # ★ `{A}` 를 `A` 로 바꿔 명시했으므로 lemma 도 **@** 로 받아야 타입이 맞는다.
        #   안 그러면 "has type forall l1 l2 : list ?A" 로 불일치한다(실측).
        ref = ("@" + nm) if has_implicit(ptext) else nm
        lines.append((stmt, h, ref))
        n_ok += 1
    if not n_ok:
        return None                               # 이유는 위에서 이미 기록
    # ★ 최종 방어선 — 고른 이름이 정말 어디에도 없는지 **다시** 확인한다.
    #   _taken_names 가 한 글자라도 놓치면 뒤 증명의 assumption/auto 가 엉뚱한 가설을
    #   집어 조용히 다른 증명이 된다. 조용한 오염보다 포기가 낫다.
    for _ty, _h, _tm in lines:
        if not name_is_free(_h, state, proof_script, suffix, premises):
            WHY.append("이름 충돌 회피 실패(방어선)")
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


def _taken_names(state: str, proof_script: str, suffix: str = "",
                 premises=None) -> set:
    """겹치면 안 되는 이름 — **텍스트에 보이는 식별자 전부**.

    ★ 예전엔 goal 가설블록의 `이름 :` 패턴만 봤다. 그러면 이런 것들을 놓친다:
        · goal 본문의 바인더      `forall H_asrt0, …`
        · 가설 **타입** 안의 이름  `H : P H_asrt0`
        · premise(전역 lemma) 이름
      놓치면 Coq 이 `H_asrt0 is already used` 로 거절하거나, 더 나쁘게는 뒤 증명의
      `assumption`·`auto` 가 **엉뚱한 가설**을 집어 조용히 다른 증명이 된다.

    → 과하게 잡는 쪽이 안전하다. 이름 후보는 `H_asrt<n>` 로 무한하니 손해가 없다.
      `Foo.bar` 는 정규식이 `.` 를 포함하지 않으므로 `Foo` 와 `bar` 로 각각 잡힌다.
    """
    out = set()
    for txt in (state, proof_script, suffix, *(premises or ())):
        out |= set(re.findall(r"[A-Za-z_][\w']*", txt or ""))
    return out


def name_is_free(name: str, state: str = "", proof_script: str = "",
                 suffix: str = "", premises=None) -> bool:
    """`name` 이 어디에도 **단어 단위로** 나타나지 않는가 — 최종 방어선."""
    pat = re.compile(r"(?<![\w'])" + re.escape(name) + r"(?![\w'])")
    return not any(pat.search(t or "")
                   for t in (state, proof_script, suffix, *(premises or ())))


# ★ 사람이 쓸 가능성이 거의 없는 접두사를 쓴다. `H`·`H0` 같은 흔한 이름은 충돌 위험이 크고,
#   충돌하면 뒤 증명의 `assumption`·`auto` 가 엉뚱한 가설을 집는다.
# ── 포기 이유 기록 / 필터 계측 모드 ───────────────────────────────────────
#   ★ 위험 필터는 "깨질 것 같다"는 추측으로 넣은 것이고, 그중 risky_tactic 은
#     이미 실측으로 틀린 것이 확인됐다(`//` `=>` `by` `-` 는 assert 와 잘 돈다).
#     추측을 또 추측으로 고치지 않도록, **필터를 끄고 전부 시도하는 모드**를 둔다.
#     ASSERT_RISK=0 이면 필터가 걸렸을 자리를 WHY 에 `~이유` 로 기록만 하고 진행한다.
#     그러면 한 번 돌려서 필터별 정확도(걸러낸 것이 실제로 깨지는 비율)를 잴 수 있다.
WHY: list[str] = []
RISK_ON = os.environ.get("ASSERT_RISK", "1") == "1"


def _no(reason: str):
    """변환 포기 — 이유를 남기고 None. 필터가 꺼져 있으면 기록만 하고 진행(False)."""
    if RISK_ON:
        WHY.append(reason)
        return None
    WHY.append("~" + reason)          # `~` = 걸렸을 테지만 통과시킨 것
    return False                       # 호출부에서 "포기 아님" 으로 읽는다


_WANT = "H_asrt"


def _fresh_base(used: set, want: str = _WANT) -> str:
    """Coq 의 **자동 개명**까지 피하는 기저 이름을 고른다.

    ★ 텍스트 대조만으로는 부족하다(실측). Coq 은 `intros` 때 이름이 이미 쓰이고 있으면
      숫자를 붙여 개명한다 — 전역에 `H_asrt0` 이 있으면 `forall H_asrt0, …` 를 intro 할 때
      **`H_asrt1` 이 생긴다**. 이 이름은 프롬프트 어디에도 안 나오므로 못 잡는다.
      실제로 `H_asrt1 is already used` 로 깨졌다.

    → 기저 이름이 텍스트의 **어떤 식별자의 접두사도 되지 않게** 고른다. 그러면 Coq 이
      개명해도 그 이름은 원래 식별자의 가족(`H_asrt0`→`H_asrt1`) 안에 머물고,
      우리 가족(`H_asrta0`, `H_asrta1`, …)과 절대 만나지 않는다.
    """
    for suf in ("", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l"):
        base = want + suf
        if not any(u.startswith(base) for u in used):
            return base
    return want + "_zz"


def _fresh(used: set, want: str = _WANT) -> str:
    """**항상 인덱스를 붙인다**: H_asrt0, H_asrt1, …

    ★ 맨 이름(`H_asrt`)을 첫 번째로 쓰면 위험하다. 한 증명에서 gold premise 가 여러 스텝에서
      빠지면 assert 가 여러 개 생기는데, 학습 데이터는 스텝별로 **독립 생성**되므로 각각
      맨 이름을 골라 충돌한다(프롬프트의 proof_script 는 원본 tactic 이라 앞 스텝의 assert 를
      못 본다). 항상 인덱스를 붙이면 규칙이 하나로 통일되고, 이미 쓰인 번호는 건너뛴다.
    """
    i = 0
    while f"{want}{i}" in used:
        i += 1
    return f"{want}{i}"


def fresh_hyp(state: str, want: str = _WANT) -> str:
    """goal 가설블록과 겹치지 않는 이름. **_fresh 와 같이 항상 인덱스를 붙인다.**"""
    body = (state or "").split("[GOAL]")[0]
    names = set(re.findall(r"^\s*([A-Za-z_][\w']*(?:\s*,\s*[A-Za-z_][\w']*)*)\s*:",
                           body, re.M))
    flat = set()
    for n in names:
        flat |= {x.strip() for x in n.split(",")}
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
                         proof_script: str = "", skip_risk: bool = False,
                         suffix: str = "", premises=None):
    """`applications` = [(항 문자열, 그 항의 타입)] 로 assert 를 만든다.

    타입은 호출부가 `Check (항).` 으로 **Coq 에게 물어서** 넘긴다 — Section 변수·암묵인자·
    인스턴스화가 전부 정리된 형태라 원문 statement 보다 정확하다.
    """
    used = _taken_names(state, proof_script, suffix, premises)
    base = _fresh_base(used)
    inner = gold_tactic.strip()
    lines = []
    # ★ 긴 항부터 치환해야 부분 치환이 안 생긴다 (`L a b` 를 먼저, 그 다음 `L`)
    for term, ty in sorted([a for a in applications if a[1]],
                           key=lambda a: -len(a[0])):
        # ★ 타입에 evar(`?h`)가 있으면 assert 못 한다 — Coq 이 미결정 항을 그대로
        #   출력한 것이고, 그대로 쓰면 `Syntax error … after [term level 200]` 이 난다.
        if re.search(r"\?[A-Za-z_]", ty):
            if (r := _no("타입에 evar(?x) 남음")) is None:
                return r
        # ★ `rewrite <-?L` / `rewrite ?L` 은 **여러 번** 재작성한다. 한 번만 치환하면
        #   `Found no subterm matching` 이 난다 → 변환하지 않는다(실측).
        if re.search(r"[?!]\s*" + re.escape(term.split()[0]), gold_tactic):
            if (r := _no("rewrite ?L / !L (반복 재작성)")) is None:
                return r
        # skip_risk: `Set Printing All` 로 얻은 타입은 notation 이 이미 다 펴져 있어
        #   notation 위험 검사가 무의미하다(`@eq` 같은 형태가 오탐된다).
        if not skip_risk and risky_type(ty):
            if (r := _no("위험 타입: " + _ty_kind(ty))) is None:
                return r
        if not skip_risk and risky_tactic(gold_tactic):
            if (r := _no("위험 tactic: " + _tac_kind(gold_tactic))) is None:
                return r
        if term not in inner:
            continue
        h = _fresh(used, base)
        used.add(h)
        # ★ **모든** 등장을 바꾼다. 한 번만 바꾸면 나머지가 원래 이름으로 남아
        #   `Found no subterm matching` 이 난다(실측).
        inner = inner.replace(term, h)
        lines.append((ty, h, term))
    if not lines:
        return _no("적용 항이 tactic 문자열에 없음")
    # ★ 치환 후에도 원래 이름이 남아 있으면(다른 형태로 쓰인 것) 변환을 포기한다 —
    #   섞여 있으면 `The variable Hasrt was not found` 같은 어긋남이 생긴다.
    for _ty, _h, term in lines:
        head = re.match(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*", term)
        if head and re.search(r"(?<![\w'.])" + re.escape(head.group(0).split(".")[-1])
                              + r"(?![\w'])", inner):
            return _no("치환 후 원래 lemma 이름 잔존")
    # ★ 최종 방어선 — 고른 이름이 정말 어디에도 없는지 **다시** 확인한다.
    #   _taken_names 가 한 글자라도 놓치면 뒤 증명의 assumption/auto 가 엉뚱한 가설을
    #   집어 조용히 다른 증명이 된다. 조용한 오염보다 포기가 낫다.
    for _ty, _h, _tm in lines:
        if not name_is_free(_h, state, proof_script, suffix, premises):
            WHY.append("이름 충돌 회피 실패(방어선)")
            return None
    out = [f"assert ({ty}) as {h}. {{ exact ({term}). }}" for ty, h, term in lines]
    out.append(inner)
    return "\n".join(out)


# ── 위험 패턴 감지 — "확실할 때만 변환" ─────────────────────────────────────
#   목표는 변환 성공률을 **1 에 가깝게** 만드는 것이다. 적용률이 좀 떨어져도,
#   변환했는데 깨지는 것보다 낫다(깨지면 그 학습 예제가 통째로 못 쓰게 된다).
#   아래 패턴들은 실제 실패에서 반복해 나온 것들이다.

# 실제 실패에서 반복해 나온 패턴들. 대부분 **mathcomp/SSReflect 커스텀 notation** 이다:
#   `Check` 는 `{fpmodR}` · `'Mor(M, N)` · `{pred T}` · `'M_(1 + m)` 같은 표기로 출력하는데,
#   그것을 `assert` 에 다시 넣으면 그 notation 의 scope 가 안 열려 파싱이 깨진다
#   (`Unknown interpretation for notation "{ _ }"` · `Syntax error: [term level 200] …`).
#   Set Printing All 로 notation 을 펼 수도 있지만 항이 거대해져 실용성이 없다.
_RISKY_TY = re.compile(
    r"\?[A-Za-z_]"                        # evar 가 남아 있다
    r"|\{[^{}:|]*\}"                       # `{fpmodR}` `{pred T}` — 바인더가 아닌 중괄호 표기
    r"|'[A-Za-z_]"                        # `'Mor(M,N)` `'M_(1+m)` — 프라임 notation
    r"|#\|"                               # `#|T|` 카디널리티
    r"|=i|\\in\b|\\subset\b"             # SSReflect 집합 표기
    # ★ `\w+Type` 로 잡으면 `ExprType` `StateClass` 같은 **평범한 사용자 타입**까지
    #   걸린다(실측). mathcomp canonical structure 이름만 명시한다.
    r"|\b(?:eq|choice|count|fin|order|porder|lattice|distrLattice|bLattice|"
    r"tbLattice|zmod|ring|comRing|unitRing|comUnitRing|idomain|field|closedField|"
    r"numDomain|numField|realDomain|realField|rcf|lmod|lalg|alg|unitAlg|falg|"
    r"vect|finGroup|baseFinGroup|finRing|finField|finAlg|semiRing|nmod|"
    r"pointed|filter|topological|uniform|pseudoMetric|complete|normed)Type\b"
    r"|\bProper\b|\bSetoid\b|\bMorphism\b|\bEquivalence\b|\baxioms_\b"
    r"|\[set\b|\[pred\b|\[rel\b|\[seq\b"    # `[set z in p]` — SSReflect 내포 표기
)

# SSReflect 결합자는 goal 개수·순서를 바꾸므로 assert 를 끼우면 어긋나기 쉽다.
_RISKY_TAC = re.compile(r"//|=>|\bexact:|\bapply:|\bcase:|\belim:|\bmove:|\brewrite\s+-")


_TY_KIND = [
    (r"\?[A-Za-z_]", "evar"),
    (r"\b(?:eq|choice|count|fin|order|porder|lattice|zmod|ring|comRing|unitRing|"
     r"comUnitRing|idomain|field|closedField|numDomain|numField|realDomain|"
     r"realField|lmod|lalg|alg|vect|finGroup|baseFinGroup|semiRing|nmod)Type\b",
     "canonical structure(eqType 등)"),
    (r"\{[^{}:|]*\}", "중괄호 notation({pred T} 등)"),
    (r"'[A-Za-z_]", "프라임 notation('M_(n))"),
    (r"#\|", "카디널리티(#|T|)"),
    (r"=i|\\in\b|\\subset\b", "SSReflect 집합표기"),
    (r"\[set\b|\[pred\b|\[rel\b|\[seq\b", "SSReflect 내포표기"),
    (r"\bProper\b|\bSetoid\b|\bMorphism\b|\bEquivalence\b|\baxioms_\b", "typeclass/Proper"),
]
_TAC_KIND = [(r"//", "//"), (r"=>", "=>"), (r"\bexact:", "exact:"), (r"\bapply:", "apply:"),
             (r"\bcase:", "case:"), (r"\belim:", "elim:"), (r"\bmove:", "move:"),
             (r"\brewrite\s+-", "rewrite -")]


def _ty_kind(ty: str) -> str:
    for pat, nm in _TY_KIND:
        if re.search(pat, ty or ""):
            return nm
    return "타입 600자 초과" if len(ty or "") > 600 else "기타"


def _tac_kind(tac: str) -> str:
    hit = [nm for pat, nm in _TAC_KIND if re.search(pat, tac or "")]
    return " ".join(hit) if hit else "기타"


def risky_type(ty: str) -> bool:
    """assert 명제로 쓰기 위험한 타입인가."""
    return bool(_RISKY_TY.search(ty or "")) or len(ty or "") > 600


def risky_tactic(tac: str) -> bool:
    """assert 를 끼우면 구조가 어긋나기 쉬운 tactic 인가."""
    return bool(_RISKY_TAC.search(tac or ""))
