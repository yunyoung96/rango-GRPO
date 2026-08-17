"""**goal 모양을 보고 premise 가 실제로 적용 가능한지** 판정한다.

## 왜 필요한가

기존 재랭킹(`tactic_data.rerank_premises`)은 goal 과 premise 결론의 **head·연산자 중첩 개수**를
센다. 이건 "닮았나"이지 "**되나**"가 아니다. 예를 들어

    goal    : a + b * c = b * c + a
    premise : forall n m, n * m = m * n        (Nat.mul_comm)

는 `+`,`*`,`=` 가 겹쳐 점수가 높지만 `rewrite Nat.mul_comm` 은 되고
`apply Nat.mul_comm` 은 **안 된다**. 반대로 이름이 하나도 안 겹쳐도 되는 경우가 있다.

여기서는 premise 를 `forall (x…), H₁ → … → C` 로 파싱해 바인더 변수를 **메타변수**로 두고,
C 를 goal 결론과 **일차 단일화(one-way matching)** 한다. 즉 Coq 이 하는 일의 축소판이다.

    apply    : C 가 goal 결론 **전체**와 매칭되나
    rewrite  : C 가 `L = R`(또는 `L <-> R`)일 때 L 이 goal 의 **어떤 부분항**과 매칭되나
    rewrite <-: 같은 것을 R 로

## 왜 토큰 매칭이 아니라 파서인가

`n + m` 의 `n` 은 goal 의 `a * b` 에 매칭되어야 하는데 `a * b` 에는 괄호가 없다.
연산자 우선순위를 모르면 어디까지가 한 항인지 알 수 없으므로 Pratt 파서를 둔다.

## 설계 원칙 — **보수적**

파싱이 실패하거나 구조를 모르면 `True`(적용 가능할 수도)를 돌려준다. 이 판정은 gold lemma 를
떨어뜨리면 안 되는 곳에 쓰이므로 위양성은 싸지만 위음성은 치명적이다.

**실측으로 잡은 함정** (scripts/measure_applicable.py 로 재현율을 재면서 하나씩 드러났다):

  · `<->` 를 문자열 `->` 로 자르면 `A <-> B` 가 가설 `A <` + 결론 `B` 가 된다 → 토큰 단위로 자른다
  · `(s, d) :: m2` 에서 `,`·`::` 를 모르면 괄호 안 첫 원소만 남고 나머지를 버린다 → 연산자로 추가
  · `apply f with x` 계열은 **화살표 중간**의 `forall` 에 변수가 묶인다 → 청크마다 벗긴다
  · `Lemma f {A} (x : T) : …` 의 선언부 바인더도 메타변수다 → `:` 앞을 읽는다
  · 상호재귀 `Lemma A … with B …` 는 `with` 앞에서 끊어야 한다
"""
from __future__ import annotations

import functools
import re
from typing import Optional

# ── 토큰화 ──────────────────────────────────────────────────────────────────
#   qualified 이름(Int.max_signed)은 한 토큰. 여러 글자 기호는 **긴 것부터** 잡아야
#   '<->' 가 '<' + '->' 로, '::' 가 ':' + ':' 로 쪼개지지 않는다.
_TOK = re.compile(
    r"""[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*        # 식별자 (qualified 포함)
      | \d+                                           # 숫자
      | <->|<-|->                                     # 화살표 (긴 것 먼저!)
      | /\\|\\/                                       # 논리곱·논리합
      | <=\?|>=\?|=\?|<\?|>\?|\?=                     # bool 비교
      | <=|>=|<>|=|<|>                                # 비교
      | \+\+|\+|-|\*|/|\^                             # 산술
      | &&|\|\|                                       # bool 연산 (Prop 의 /\ \/ 와 레벨이 다르다)
      | ::|:|~|@|!|\||,|;|\.                          # 기타 (:: 먼저!)
      | \(|\)|\[|\]|\{|\}""",
    re.X,
)

# `0%R`, `(x < 0)%R` 의 scope 주석. 표기 범위일 뿐 항의 구조가 아니므로 지운다.
#   (안 지우면 '%' 가 중위연산으로 붙어 `0 % R` 이 되어 매칭이 전부 깨진다.)
_SCOPE = re.compile(r"%[A-Za-z_]\w*")

_KW = {"forall", "exists", "fun", "match", "with", "end", "let", "in", "if", "then",
       "else", "return", "fix", "cofix", "as", "struct", "Type", "Prop", "Set"}

# 중위 연산자 우선순위 = **Coq notation 레벨**(클수록 약하게 묶인다). 숫자를 그대로 쓴다.
#   ★ 함정: `||`(orb)·`&&`(andb) 는 bool 연산이라 레벨 50/40 으로 `=`(70) 보다 **강하게** 묶인다.
#     Prop 의 `\/`(85)·`/\`(80) 와 헷갈려 85 를 주면 `a = b || c` 가 `(a = b) || c` 로 파싱돼
#     매칭이 통째로 깨진다 (실측으로 잡음).
_INFIX: dict[str, tuple[int, bool]] = {
    ",": (200, True),                                  # pair — 괄호 안에서만 의미
    "->": (99, True), "<->": (95, True),
    "\\/": (85, True),
    "/\\": (80, True),
    "=": (70, False), "<>": (70, False), "<=": (70, False), "<": (70, False),
    ">=": (70, False), ">": (70, False),
    "=?": (70, False), "<?": (70, False), "<=?": (70, False),
    ">?": (70, False), ">=?": (70, False), "?=": (70, False),
    "::": (60, True), "++": (60, True),
    "||": (50, True), "+": (50, False), "-": (50, False),
    "&&": (40, True), "*": (40, False), "/": (40, False),
    "^": (30, True),
}
_CLOSE = {")", "]", "}"}
_STOP = _CLOSE | {";", ".", ":"}


def tokenize(s: str) -> list[str]:
    return _TOK.findall(_SCOPE.sub("", s or ""))


class _P:
    """Pratt 파서. 항 트리: ('id',name) · ('app',f,arg) · ('op',sym,l,r) · ('opq',txt)"""

    def __init__(self, toks: list[str]):
        self.t = toks
        self.i = 0

    def peek(self) -> Optional[str]:
        return self.t[self.i] if self.i < len(self.t) else None

    def next(self) -> Optional[str]:
        v = self.peek()
        self.i += 1
        return v

    def _skip_balanced(self, start: int) -> str:
        """여는 괄호 자리(start)부터 짝이 맞는 닫는 괄호까지 통째로 삼켜 원문을 돌려준다.

        ★ 괄호 안을 파싱하다 실패했을 때 **소비한 만큼만** 버리면 `(s, d) :: m2` 가 `s` 로
          뭉개진다. 반드시 균형 지점까지 건너뛴 뒤 불투명 항으로 만들어야 한다.
        """
        d, j = 0, start
        while j < len(self.t):
            c = self.t[j]
            if c in "([{":
                d += 1
            elif c in _CLOSE:
                d -= 1
                if d == 0:
                    j += 1
                    break
            j += 1
        txt = " ".join(self.t[start:j])
        self.i = j
        return txt

    def atom(self):
        start = self.i
        v = self.next()
        if v is None:
            raise ValueError("eof")
        if v == "(":
            try:
                e = self.expr(1000)
            except Exception:
                return ("opq", self._skip_balanced(start))
            if self.peek() == ")":
                self.next()
                return e
            return ("opq", self._skip_balanced(start))     # 못 읽은 구조 → 통째로 불투명
        if v in ("[", "{"):
            return ("opq", self._skip_balanced(start))
        if v == "~":
            return ("app", ("id", "not"), self.expr(75))
        if v in ("forall", "exists", "fun", "match", "let", "if", "fix", "cofix"):
            rest = self.t[start:]
            self.i = len(self.t)
            return ("opq", " ".join(rest))
        if v == "@":
            return self.atom()
        if v in _INFIX or v in _STOP or v in ("->", "<-"):
            raise ValueError(f"unexpected {v}")
        return ("id", v)

    def app(self):
        e = self.atom()
        while True:
            p = self.peek()
            if p is None or p in _INFIX or p in _STOP or p in ("<-", "->") or p in _KW:
                return e
            e = ("app", e, self.atom())

    def expr(self, maxp: int = 1000):
        left = self.app()
        while True:
            p = self.peek()
            if p is None or p not in _INFIX:
                return left
            prec, right = _INFIX[p]
            if prec > maxp:
                return left
            self.next()
            rhs = self.expr(prec if right else prec - 1)
            left = ("op", p, left, rhs)


def parse_toks(toks: list[str]):
    t = list(toks)
    while t and t[-1] in (".", ";", ","):
        t.pop()
    if not t:
        return None
    try:
        return _P(t).expr()
    except Exception:
        return None


def parse(text: str):
    """Coq 항 문자열 → 트리. 실패하면 None."""
    return parse_toks(tokenize(text))


# ── notation ↔ 함수 이름 정규화 ──────────────────────────────────────────────
#   goal 은 `beta ^ e` 로 보이는데 lemma 는 `Zpower n k` 로 쓴다. 같은 것이므로 한쪽으로
#   모아야 매칭된다. 모듈 접두사(Z./Nat./N.)도 떼어 `Z.add`·`plus`·`+` 를 하나로 본다.
#
#   ★ 타입을 무시하므로 nat 의 `+` 와 Z 의 `+` 를 같게 본다 = 위양성이 는다.
#     이 판정은 **재현율이 생명**이므로 의도한 트레이드오프다.
_OP2FN = {
    "+": "add", "-": "sub", "*": "mul", "/": "div", "^": "pow",
    "++": "app", "::": "cons", "||": "orb", "&&": "andb",
    "/\\": "and", "\\/": "or", "<->": "iff", "->": "impl", ",": "pair",
    "=": "eq", "<": "lt", "<=": "le", "<>": "neq",
    "=?": "eqb", "<?": "ltb", "<=?": "leb", "?=": "compare",
}
_SWAP = {">": "lt", ">=": "le", ">?": "ltb", ">=?": "leb"}      # a > b ≡ lt b a
_FN_ALIAS = {
    "plus": "add", "minus": "sub", "mult": "mul",
    "Zplus": "add", "Zminus": "sub", "Zmult": "mul", "Zpower": "pow", "Zdiv": "div",
    "Nplus": "add", "Nmult": "mul",
    "Zle": "le", "Zlt": "lt", "Zge": "ge", "Zgt": "gt",
    "andb": "andb", "orb": "orb", "negb": "negb",
}


def canon(t):
    """항 트리를 정규형으로: 중위 연산 → 함수적용, 모듈접두사 제거, a>b → lt b a."""
    if t is None:
        return None
    if t[0] == "id":
        s = t[1].split(".")[-1]
        return ("id", _FN_ALIAS.get(s, s))
    if t[0] == "opq":
        return t
    if t[0] == "app":
        return ("app", canon(t[1]), canon(t[2]))
    if t[0] == "op":
        s = t[1]
        l_, r_ = canon(t[2]), canon(t[3])
        if s in _SWAP:
            return ("app", ("app", ("id", _SWAP[s]), r_), l_)
        fn = _OP2FN.get(s)
        if fn is None:
            return ("op", s, l_, r_)
        return ("app", ("app", ("id", fn), l_), r_)
    return t


def as_eq(t):
    """정규형에서 `eq L R` / `iff L R` 를 (L, R) 로. 아니면 None."""
    if t is not None and t[0] == "app" and t[1][0] == "app" \
            and t[1][1][0] == "id" and t[1][1][1] in ("eq", "iff"):
        return t[1][2], t[2]
    return None


def as_impl(t):
    """정규형에서 `impl A B` 를 (A, B) 로. 아니면 None."""
    if t is not None and t[0] == "app" and t[1][0] == "app" \
            and t[1][1][0] == "id" and t[1][1][1] == "impl":
        return t[1][2], t[2]
    return None


# ── premise 분해 ────────────────────────────────────────────────────────────
_DECL = re.compile(
    r"^\s*(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint|Instance|Axiom|"
    r"Proposition|Example|Let|Program\s+Definition|Program\s+Fixpoint)\s+"
    r"([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)", re.S)


def _split_top_tok(toks: list[str], sym: str) -> list[list[str]]:
    """최상위(괄호 밖)에서 토큰 sym 으로 자른다. 문자열 자르기와 달리 `<->` 를 안 건드린다."""
    out: list[list[str]] = []
    buf: list[str] = []
    d = 0
    for t in toks:
        if t in "([{":
            d += 1
        elif t in _CLOSE:
            d -= 1
        if d == 0 and t == sym:
            out.append(buf)
            buf = []
            continue
        buf.append(t)
    out.append(buf)
    return out


def _binder_vars_tok(toks: list[str]) -> set[str]:
    """`( n m : nat ) ( H : P n )` / `n m : nat` / `n m` → {n, m, H}

    괄호 그룹은 그룹별로 `:` 앞을, 괄호 밖은 전체에서 첫 `:` 앞을 변수로 본다.
    """
    vs: set[str] = set()
    i = 0
    plain: list[str] = []
    while i < len(toks):
        t = toks[i]
        if t in "([{":
            d, j = 0, i
            while j < len(toks):
                if toks[j] in "([{":
                    d += 1
                elif toks[j] in _CLOSE:
                    d -= 1
                    if d == 0:
                        break
                j += 1
            grp = toks[i + 1:j]
            lhs = _split_top_tok(grp, ":")[0]
            vs |= {x for x in lhs if re.match(r"^[A-Za-z_][\w']*$", x)}
            i = j + 1
            continue
        plain.append(t)
        i += 1
    lhs = _split_top_tok(plain, ":")[0]
    vs |= {x for x in lhs if re.match(r"^[A-Za-z_][\w']*$", x)}
    return vs - _KW


def _strip_foralls(toks: list[str]) -> tuple[set[str], list[str]]:
    """앞쪽에 붙은 forall 들을 벗겨 (변수, 남은 토큰). 중첩도 처리."""
    vs: set[str] = set()
    t = list(toks)
    while t and t[0] in ("forall", "∀"):
        d, cut = 0, -1
        for i in range(1, len(t)):
            if t[i] in "([{":
                d += 1
            elif t[i] in _CLOSE:
                d -= 1
            elif t[i] == "," and d == 0:
                cut = i
                break
        if cut < 0:
            return vs, t
        vs |= _binder_vars_tok(t[1:cut])
        t = t[cut + 1:]
    return vs, t


def decompose(ptext: str) -> Optional[tuple[set[str], list[list[str]], list[str]]]:
    """premise 텍스트 → (메타변수, 가설 토큰들, 결론 토큰). 파싱 불가면 None."""
    t = re.sub(r"\(\*.*?\*\)", " ", (ptext or ""), flags=re.S).strip()
    toks = tokenize(t)
    if not toks:
        return None

    mvars: set[str] = set()
    m = _DECL.match(t)
    if m:
        # 선언 키워드 + 이름을 건너뛴다 (Program Definition 은 토큰 2개)
        skip = 2 if t.lstrip().startswith("Program") else 1
        toks = toks[skip:]
        if toks and re.match(r"^[A-Za-z_][\w']*$", toks[0]):
            toks = toks[1:]
        # ★ 상호재귀 `... with g ...` 는 여기서 끊는다 (안 끊으면 결론이 뒤 정의까지 삼킨다)
        w = next((i for i, x in enumerate(toks) if x == "with"), -1)
        head = _split_top_tok(toks, ":")
        if len(head) >= 2:
            mvars |= _binder_vars_tok(head[0])        # 선언부 바인더도 메타변수
            toks = [x for ch in head[1:] for x in (ch + [":"])][:-1]
        if w >= 0:
            w2 = next((i for i, x in enumerate(toks) if x == "with"), -1)
            if w2 >= 0:
                toks = toks[:w2]
    while toks and toks[-1] == ".":
        toks.pop()

    v0, toks = _strip_foralls(toks)
    mvars |= v0
    chain = _split_top_tok(toks, "->")
    # ★ 화살표 중간의 forall 도 메타변수를 묶는다: `A -> forall l, B l -> C l`
    hyps: list[list[str]] = []
    for ch in chain[:-1]:
        v, rest = _strip_foralls(ch)
        mvars |= v
        hyps.append(rest)
    v, concl = _strip_foralls(chain[-1])
    mvars |= v
    if not concl:
        return None
    return mvars, hyps, concl


# ── 일차 매칭 (패턴의 메타변수만 대입, goal 쪽은 고정) ──────────────────────
def match(pat, tgt, mv: set[str], sub: dict) -> bool:
    if pat is None or tgt is None:
        return False
    if pat[0] == "id" and pat[1] in mv:
        prev = sub.get(pat[1])
        if prev is None:
            sub[pat[1]] = tgt
            return True
        return prev == tgt
    if pat[0] == "opq" or (tgt is not None and tgt[0] == "opq"):
        return True                                  # 판정 유보 → 보수적으로 통과
    if pat[0] != tgt[0]:
        return False
    if pat[0] == "id":
        return pat[1].split(".")[-1] == tgt[1].split(".")[-1]
    if pat[0] == "app":
        return match(pat[1], tgt[1], mv, sub) and match(pat[2], tgt[2], mv, sub)
    if pat[0] == "op":
        return (pat[1] == tgt[1]
                and match(pat[2], tgt[2], mv, sub)
                and match(pat[3], tgt[3], mv, sub))
    return False


def subterms(t):
    if t is None:
        return
    yield t
    if t[0] == "app":
        yield from subterms(t[1])
        yield from subterms(t[2])
    elif t[0] == "op":
        yield from subterms(t[2])
        yield from subterms(t[3])


def _matches_any_sub(pat, goal, mv) -> bool:
    return any(match(pat, s, mv, {}) for s in subterms(goal))


def goal_conclusion(state: str) -> str:
    """proof state 에서 **현재 goal** 의 결론부만.

    ★ 함정 둘 (실측으로 드러남):
      ① state 에는 남은 goal 이 `[GOAL]` 로 이어 붙어 여러 개 들어 있다. tactic 이 작용하는
         것은 **첫 번째**인데, 뒤에서부터 자르면 엉뚱한 goal 을 본다 → 재현율이 무너진다.
      ② 가설블록과 결론은 빈 줄로 나뉘므로, 첫 goal **안에서** 마지막 블록이 결론이다.
    """
    s = (state or "").split("[GOAL]")[0]          # ① 현재(첫) goal 만
    if "=====" in s:
        return s.split("=====")[-1].lstrip("= \t").strip()
    parts = re.split(r"\n\s*\n", s)
    return (parts[-1] if len(parts) > 1 else s).strip()


def applicability(goal_state: str, premise: str) -> dict:
    """{'apply':bool, 'rw':bool, 'rw_rev':bool, 'parsed':bool}

    parsed=False 면 판정 불가 → 호출부는 **적용 가능으로 간주**해야 한다(보수성).
    """
    unk = {"apply": True, "rw": True, "rw_rev": True, "parsed": False}
    d = decompose(premise)
    if d is None:
        return unk
    mv, _hyps, concl_t = d
    g = parse(goal_conclusion(goal_state))
    c = parse_toks(concl_t)
    if g is None or c is None:
        return unk
    g, c = canon(g), canon(c)                    # notation 을 함수형으로 모아 비교 가능하게

    out = {"apply": False, "rw": False, "rw_rev": False, "parsed": True}
    # ★ goal 이 `forall x, P` / `A -> B` 면 intros 후의 몸통에도 apply 가 성립한다.
    #   Coq 의 apply 가 goal 을 자동으로 벗기지는 않지만 실무에서 intros 와 짝지어 쓰이므로,
    #   재현율을 지키기 위해 몸통까지 후보로 본다(보수적).
    gts = [g]
    gg = g
    for _ in range(6):
        im = as_impl(gg)
        if not im:
            break
        gg = im[1]
        gts.append(gg)
    out["apply"] = any(match(c, x, mv, {}) for x in gts)

    eq = as_eq(c)
    if eq:
        lhs, rhs = eq
        if not (lhs[0] == "id" and lhs[1] in mv):        # `?x = e` 는 무엇에나 맞아 무의미
            out["rw"] = _matches_any_sub(lhs, g, mv)
        if not (rhs[0] == "id" and rhs[1] in mv):
            out["rw_rev"] = _matches_any_sub(rhs, g, mv)
    return out


def usable(goal_state: str, premise: str) -> bool:
    """apply · rewrite · rewrite<- 중 하나라도 되면 True (판정 불가는 True)."""
    a = applicability(goal_state, premise)
    return (not a["parsed"]) or a["apply"] or a["rw"] or a["rw_rev"]


# ── 배치 API (학습 경로용) ──────────────────────────────────────────────────
#   premise 하나하나에 applicability() 를 부르면 **goal 을 premise 수만큼 재파싱**한다
#   (예제당 50~100 회). goal 은 한 번만 파싱하고, premise 분해는 텍스트가 반복되므로
#   캐시한다 — 학습 처리량에 직접 영향을 준다.
@functools.lru_cache(maxsize=200_000)
def _prem_parts(ptext: str):
    """premise → (메타변수, 정규화된 결론트리). 결과는 goal 과 무관하므로 캐시가 유효하다."""
    d = decompose(ptext)
    if d is None:
        return None
    c = parse_toks(d[2])
    if c is None:
        return None
    return frozenset(d[0]), canon(c)


def usable_flags(goal_state: str, premises: list[str]) -> list[bool]:
    """premise 목록 각각이 현재 goal 에 적용 가능한지. 판정 불가는 True(보수적)."""
    g = parse(goal_conclusion(goal_state))
    if g is None:
        return [True] * len(premises)
    g = canon(g)
    gts = [g]
    gg = g
    for _ in range(6):
        im = as_impl(gg)
        if not im:
            break
        gg = im[1]
        gts.append(gg)
    subs = list(subterms(g))

    out = []
    for t in premises:
        parts = _prem_parts(t)
        if parts is None:
            out.append(True)
            continue
        mv, c = parts
        if any(match(c, x, mv, {}) for x in gts):
            out.append(True)
            continue
        eq = as_eq(c)
        ok = False
        if eq:
            for side in eq:
                if side[0] == "id" and side[1] in mv:
                    continue
                if any(match(side, s, mv, {}) for s in subs):
                    ok = True
                    break
        out.append(ok)
    return out
