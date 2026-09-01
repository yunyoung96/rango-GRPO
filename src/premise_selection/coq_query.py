"""★ goal 을 `SearchPattern`/`SearchRewrite` 질의로 바꾼다 — **구체→추상 사다리**.

## 왜 사다리인가

`SearchPattern` 은 **단일화가 아니라 매칭**이다 — lemma 결론이 **패턴의 인스턴스**여야
한다. 그래서 goal 보다 **더 일반적인** lemma 는 구체 패턴으로 절대 안 나온다:

    goal   Pos.succ a <> Pos.succ b
    (Pos.succ ?a <> Pos.succ ?b)  →   0건
    (?x <> ?y)                    →  77건 · not_eq_sym ★ · Plt_ne ★

`not_eq_sym`·`Rle_trans`·`eq_sym`·`f_equal`·`proj1` 같은 **구조적 lemma** 가 통째로
이 부류다. 그래서 구체→추상 여러 단을 쏘고 합집합을 쓴다.

## `_` 가 아니라 `?x` 를 쓴다

`_` 는 서로 **독립**이라 패턴이 헐거워진다. `?x` 는 같은 이름이 같은 항이어야 한다는
**일관성**을 건다 — 바깥에서 치환트리로 만들던 것이 문법에 이미 있다.

    (Z.add _ _ = Z.add _ _)       → 20건 이상 (사실상 전부)
    (Z.add ?x ?y = Z.add ?y ?x)   → Z.add_comm 하나

## 사다리 (합집합으로 쓴다)

    L1  지역변수 → ?이름                 구체 lemma
    L2  + 피연산자의 **인자**를 ?z 로      한 단계 일반
    L3  + 피연산자를 통째로 ?z 로          관계만 남음 → 구조적 lemma
"""
from __future__ import annotations

import re
from typing import Optional

# 출력형 goal 에서 최상위로 나타나는 중위 연산 (긴 것부터 — `<->` 가 `<` 보다 먼저)
INFIX = ["<->", "->", "<=", ">=", "<>", "=", "<", ">", "/\\", "\\/"]
_ID = re.compile(r"[A-Za-z_][\w']*")
_QID = re.compile(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*")
_OPCH = set("<>=|!~/\\+-*:")
# 프로젝트 고유 중위 notation (`|=` · `**` · `⊑` …) — 괄호 깊이 0 의 기호 뭉치
_UNKOP = re.compile(r"(?<=\s)[|&^~!<>=+*/\\@#$%-]{1,3}(?=\s)")
_SAFE = re.compile(r"^[\w\s().,'?@!|+*/\\<>=~:%\[\]{}-]*$")


def _split_top(s: str, op: str) -> Optional[tuple]:
    """괄호 깊이 0 에서 `op` 로 한 번 쪼갠다. 없으면 None."""
    d, i = 0, 0
    while i < len(s):
        c = s[i]
        if c in "([{":
            d += 1
        elif c in ")]}":
            d -= 1
        elif d == 0 and s.startswith(op, i):
            # ★ 더 긴 연산의 **일부**를 잡으면 안 된다. `m |= X` 의 `=`, `a <= b` 의 `<`,
            #   `A <-> B` 의 `<` … 앞뒤에 연산 글자가 붙어 있으면 건너뛴다.
            #   (실측: `|=` 때문에 `?m ?a0 = (range ?b0 … ?b21)` 같은 쓰레기 패턴이 나왔다.)
            if s[i - 1:i] in _OPCH or s[i + len(op):i + len(op) + 1] in _OPCH:
                i += 1
                continue
            return s[:i].strip(), s[i + len(op):].strip()
        i += 1
    return None


#: 적용(application)이 **아닌** 것을 여는 머리말. 이걸 공백으로 쪼개면
#: `match ?a0 ?a1 … ?a14` 같은 **파스 오류** 패턴이 나오고, 질의 하나가 깨지면
#: 그 뒤 질의가 전부 죽는다(실측으로 19~51개를 잃었다).
_NOTAPP = re.compile(r"^\s*(?:match|if|let|fun|forall|exists|fix|cofix)\b")


def _args_of(t: str) -> Optional[list]:
    """`f a (g b) c` → ['f', 'a', '(g b)', 'c']. 적용이 아니면 None."""
    if _NOTAPP.match(t or ""):
        return None
    out, buf, d = [], "", 0
    for c in t.strip():
        if c in "([{":
            d += 1
        elif c in ")]}":
            d -= 1
        if c.isspace() and d == 0:
            if buf:
                out.append(buf); buf = ""
        else:
            buf += c
    if buf:
        out.append(buf)
    return out if len(out) > 1 else None


def abstract_locals(term: str, locals_: set) -> str:
    """지역 이름 → `?이름`. **같은 이름은 같은 `?`** 라 일관성이 유지된다."""
    def rep(m):
        w = m.group(0)
        # ★ goal 에 이미 evar(`?nvl`)가 있으면 `??nvl` 이 되어 패턴이 깨진다
        if m.start() > 0 and term[m.start() - 1] == "?":
            return w
        return "?" + w.replace("'", "_") if w in locals_ else w
    return _ID.sub(rep, term)


_SCOPE = re.compile(r"%[A-Za-z_][\w']*\s*$")


def scope_of(t: str) -> str:
    """`(0 <= m)%R` → `R`. 없으면 빈 문자열.

    ★ 스코프를 떼면 **뜻이 바뀐다.** `(0 <= ?x)%R` 의 `0` 은 `IZR Z0` 인데
      `%R` 을 떼면 **nat 의 0** 으로 해석돼 Rle 계열을 하나도 못 찾는다
      (실측: bpow_ge_0·Rmult_le_compat_r·le_F2R 등 Flocq/Reals 계열이 통째로 누락).
    """
    m = _SCOPE.search(t.strip())
    return m.group(0).lstrip("%").strip() if m else ""


def strip_outer(t: str) -> str:
    """바깥 괄호와 `%Z`·`%R` 스코프 표기를 벗긴다.

    ★ 출력형 goal 은 `(0 <= m)%Z` 처럼 **통째로 괄호+스코프**인 경우가 많다.
      그대로 두면 최상위 중위 연산이 괄호 깊이 1 에 있어 안 잡히고,
      사다리 2·3단이 아예 안 만들어진다(실측: `후보 0` 의 주범).
    """
    t = t.strip()
    for _ in range(6):
        t2 = _SCOPE.sub("", t).strip()
        if t2.startswith("(") and t2.endswith(")"):
            d = 0
            ok = True
            for i, c in enumerate(t2):
                if c == "(":
                    d += 1
                elif c == ")":
                    d -= 1
                    if d == 0 and i != len(t2) - 1:
                        ok = False
                        break
            if ok:
                t2 = t2[1:-1].strip()
        if t2 == t:
            return t
        t = t2
    return t


def ladder(goal: str, locals_: set, max_levels: int = 3) -> list:
    """구체→추상 패턴 사다리. 중복은 뺀다."""
    out, seen = [], set()

    def add(p):
        p = " ".join(p.split())
        if not (p and _SAFE.match(p) and len(p) < 600):
            return
        if sc:                       # ★ 스코프를 되붙인다 — 안 붙이면 뜻이 바뀐다
            p = f"({p})%{sc}"
        if p not in seen:
            seen.add(p); out.append(p)

    sc = scope_of(goal)
    goal = strip_outer(goal)
    # ★ 안전망 — goal 안쪽 바인더는 **절대** 추상화하지 않는다.
    #   `forall ?x, …` / `fun ?x => …` 는 문법 오류이고, 한 번 나면 뒤 질의가 다 죽는다.
    locals_ = set(locals_) - goal_binders(goal)
    l1 = abstract_locals(goal, locals_)
    add(l1)
    if max_levels < 2:
        return out

    # ★ 앞에 `forall`/`exists` 가 붙어 있으면 그 전체가 한정 명제다 — 중위로 쪼개면
    #   `(forall ?a0 …) = (…)` 같은 쓰레기가 나온다. 그 경우 2·3단은 만들지 않는다.
    if re.match(r"^\s*(?:forall|exists|fun|let)\b", l1):
        return out
    # 최상위 중위 연산을 찾아 좌·우변을 얻는다
    for op in INFIX:
        sp = _split_top(l1, op)
        if not sp:
            continue
        lhs, rhs = sp
        # L2 — 각 변의 **인자**만 ?z 로 (머리는 남긴다)
        def blur_args(t, tag):
            a = _args_of(t)
            if not a:
                return t
            return "(" + a[0] + " " + " ".join(f"?{tag}{i}" for i in range(len(a) - 1)) + ")"
        add(f"{blur_args(lhs,'a')} {op} {blur_args(rhs,'b')}")
        # L3 — 변을 통째로 ?z 로 (관계만 남는다)
        if max_levels >= 3:
            add(f"?zl {op} ?zr")
        break
    else:
        # ★ 등록된 중위가 없다 — 프로젝트 고유 notation 일 수 있다(`m |= P`, `a ** b`).
        #   기호 뭉치를 **동적으로** 찾아 그것을 관계로 삼는다.
        m = _UNKOP.search(l1)
        if m:
            op = m.group(0)
            lhs, rhs = l1[:m.start()].strip(), l1[m.end():].strip()
            def blur(t, tag):
                a = _args_of(t)
                return ("(" + a[0] + " " + " ".join(f"?{tag}{i}" for i in range(len(a) - 1)) + ")") if a else t
            add(f"{blur(lhs,'a')} {op} {blur(rhs,'b')}")
            if max_levels >= 3:
                add(f"?zl {op} ?zr")
        else:
            a = _args_of(l1)
            if a:
                add("(" + a[0] + " " + " ".join(f"?c{i}" for i in range(len(a) - 1)) + ")")
    return out[:max_levels + 1]


#: 적용의 **끝**을 알리는 낱말. 여기서 런이 끊긴다.
_APPKW = {"with", "end", "then", "else", "in", "return", "as", "at", "is",
          "fun", "forall", "exists", "let", "match", "if", "fix", "cofix"}
_IDENT = re.compile(r"[A-Za-z_?][\w'.]*")


def _chunks(t: str):
    """문자열을 깊이 0 기준으로 낱덩이로 쪼갠다 — 이름 · 괄호덩이 · 그 밖(연산자)."""
    i, n = 0, len(t)
    while i < n:
        c = t[i]
        if c.isspace():
            i += 1; continue
        if c in "([{":
            d, a = 0, i
            while i < n:
                if t[i] in "([{": d += 1
                elif t[i] in ")]}":
                    d -= 1
                    if d == 0: i += 1; break
                i += 1
            yield ("grp", t[a:i]); continue
        m = _IDENT.match(t, i)
        if m:
            yield ("kw" if m.group(0) in _APPKW else "id", m.group(0)); i = m.end(); continue
        yield ("op", c); i += 1


def app_subterms(t: str, maxn: int = 12) -> list:
    """★★ **괄호 없는 적용 부분항**까지 훑는다.

    `rewrite` 는 부분항을 치환한다. 그런데 예전 판은 괄호 친 것만 모아서
    `match PTree.get i (PTree.set j x (snd m)) with …` 의 **진짜 redex** 인
    `PTree.get i (PTree.set j x (snd m))` 을 통째로 놓쳤다 — 괄호가 없어서다.
    gold 가 `PTree.gso : get i (set j x m) = get i m` 인데 그 좌변을 질의로
    만들지 않았다는 뜻이다.

    깊이 0 에서 `이름`·`괄호덩이` 가 이어지는 **최대 런**을 적용으로 보고,
    괄호덩이 안쪽으로 재귀한다. 낱말(`with`/`end`/…)과 연산자에서 런이 끊긴다.
    """
    out = []

    def walk(s, depth=0):
        if depth > 6 or not s:
            return
        run = []

        def flush():
            if len(run) >= 2:
                e = " ".join(run)
                if 6 < len(e) < 300:
                    out.append(e)
            run.clear()

        for kind, tok in _chunks(s):
            if kind in ("id", "grp"):
                run.append(tok)
                if kind == "grp":
                    walk(tok[1:-1], depth + 1)
            else:
                flush()
        flush()

    walk(strip_outer(t))
    # 긴 것 우선 — 큰 redex 가 더 특징적이다. 중복은 뺀다.
    return sorted(dict.fromkeys(out), key=len, reverse=True)[:maxn]


def rewrite_targets(goal: str, locals_: set, maxn: int = 4) -> list:
    """`SearchRewrite` 질의 대상 — goal 의 큰 부분항부터, 각각 사다리 1~2단."""
    subs, st = [], []
    for i, ch in enumerate(goal):
        if ch == "(":
            st.append(i)
        elif ch == ")" and st:
            a = st.pop()
            f = goal[a:i + 1]
            if 6 < len(f) < 200:
                subs.append(f)
    # ★ 긴 것만 고르면 안 된다 — `rewrite F2R_0` 의 대상 `F2R (Float beta 0 e)` 는
    #   작은 부분항이다. 길이 스펙트럼에 고루 걸치도록 큰 것/작은 것을 섞는다.
    # ★ 괄호 없는 적용도 넣는다 — 예전 판이 통째로 놓치던 자리다.
    subs += app_subterms(goal)
    subs = sorted(set(subs), key=len, reverse=True)
    pick = []
    if subs:
        half = max(1, maxn // 2)
        pick = subs[:half] + subs[-(maxn - half):]
    out, seen = [], set()
    for t in dict.fromkeys(pick):
        for p in ladder(t, locals_, max_levels=2):
            if p not in seen:
                seen.add(p); out.append(p)
    return out[:maxn * 2]


# ── 지역 이름 추출 ───────────────────────────────────────────────────────────
_DECL_LINE = re.compile(r"^\s*([A-Za-z_][\w']*(?:\s*,\s*[A-Za-z_][\w']*)*)\s*:=?\s")


def local_names(goal) -> set:
    """goal 의 **지역 이름**(가설·변수). 이것만 `?x` 로 추상화한다.

    ★ 가설 한 줄이 **여러 줄로 접힌다.** 연속행에는 `:` 가 없거나 타입 본문 안의
      `:` 가 걸리므로, 순진하게 `h.split(":")[0]` 을 쓰면 **본문의 전역 이름까지**
      지역으로 잡는다. 실측으로 걸렸다 —

          'H: m'                                   → H          (정상)
          '|= range sp 0 (fe_stack_data fe) **'    → range, sp, fe_stack_data …  ★오인
          '   range sp (…) (fe_size fe) ** P'      → range, fe_size …            ★오인

      그러면 패턴이 `?m |= ?range ?sp …` 가 되어 6,667건을 긁고 gold 는 못 잡는다.
      **선언 형태(`이름[, 이름…] : 타입`)로 시작하는 줄만** 본다.
    """
    out: set = set()
    for h in (getattr(goal, "hyps", None) or []):
        m = _DECL_LINE.match(h)
        if not m:
            continue                      # 연속행 — 건너뛴다
        out |= set(re.findall(r"[A-Za-z_][\w']*", m.group(1)))
    # ★★ goal **안쪽** 바인더(`exists (changed : bool) …` 의 changed)는 **빼야 한다.**
    #   이것들은 goal 안에서 묶여 있으므로 lemma 가 채울 자리가 아니다 — **경직**이다.
    #   `?x` 로 바꾸면 `forall ?x, …` · `fun ?x => …` 가 되어 **문법 오류**가 나고,
    #   Coq 은 그 시점에 파일 처리를 중단해 **뒤 질의가 전부 죽는다**
    #   (실측: 후보 0 인 23건 **전부**가 이것이었고, 첫 질의에서 죽어 19~51개를 잃었다).
    #   대신 `Search` 인자에서는 빼야 하므로 그건 `goal_binders()` 를 따로 쓴다.
    out -= goal_binders(getattr(goal, "goal", "") or "")
    return out


def hyp_queries(goal, locals_: set, maxn: int = 4) -> list:
    """`apply L in H` / `rewrite L in H` — **전방추론** 용 질의.

    ★ 전방추론은 lemma 의 **전제**가 가설 `H` 와 맞고 결론이 `H` 를 대체한다.
      결론이 goal 과 맞을 이유가 **전혀 없다** — `SearchPattern <goal>` 로는
      원리적으로 못 찾는다(실측: 놓친 것의 16%).
      대신 **각 가설의 타입**을 패턴으로 쏜다. `SearchPattern (H_타입 -> ?z)` 가
      정확한 형태지만, `SearchPattern` 이 화살표 접미사를 보므로
      `H_타입 -> ?z` 를 그대로 쓰면 된다(§규칙 ③).
    """
    out, seen = [], set()
    for h in (getattr(goal, "hyps", None) or []):
        m = _DECL_LINE.match(h)
        if not m:
            continue
        ty = h[m.end():].strip()
        if not ty or len(ty) > 200:
            continue
        for p in ladder(ty, locals_, max_levels=2):
            q = f"{p} -> ?zfwd"
            if q not in seen and _SAFE.match(q):
                seen.add(q); out.append(q)
        if len(out) >= maxn * 2:
            break
    return out[:maxn * 2]


# ── 기호 결합 질의 ───────────────────────────────────────────────────────────
_KW = {"forall", "exists", "fun", "let", "in", "match", "with", "end", "if", "then",
       "else", "Prop", "Type", "Set", "True", "False", "return", "as", "of", "at", "by",
       "do", "ret", "check", "assertion"}
_CHECK_GLOBALS = True   # Search 인자를 선언된 이름으로 제한 (오류 질의 차단)


def rigid_syms(term: str, locals_: set, maxn: int = 6) -> list:
    """`Search` 인자로 쓸 **전역 이름**. 등장 순서를 유지한다.

    지역 이름과 **goal 안쪽 바인더**를 뺀다 — 바인더는 추상화 대상은 아니지만
    전역도 아니라서 `Search <바인더>` 는 오류가 난다.
    """
    locals_ = set(locals_) | goal_binders(term)
    out = []
    for m in _QID.finditer(term):
        w = m.group(0)
        if m.start() > 0 and term[m.start() - 1] == "?":
            continue
        if w in locals_ or w in _KW or len(w) <= 1:
            continue
        # ★ 실제로 선언된 이름만 쏜다 — 아니면 `Search` 가 오류를 내고
        #   Coq 이 파일 처리를 중단해 **뒤 질의가 전부 죽는다**.
        if _CHECK_GLOBALS:
            kg = known_globals()
            if kg and (w not in kg and w.split(".")[-1] not in kg):
                continue
        if w not in out:
            out.append(w)
    return out[:maxn]


_NOTA = re.compile(r"(?<=\s)([|&^~!<>=+*/\\@#$%-]{1,3})(?=\s)")


def symbol_queries(goal: str, locals_: set, maxn: int = 6, with_hyps=None) -> list:
    """`Search <기호…>` — **기호 결합**으로 좁힌다.

    ★ 관계를 `(?a = ?b)` 로 **못 박으면 안 된다.** 프로젝트가 자기 동치관계를 쓰면
      결론이 등식이 아니다 — 실측:

          sep_swap23 : massert_eqv (sepconj P (sepconj Q (sepconj R S))) (…)

      `rewrite sep_swap23` 은 setoid 재작성이라 되는데, `Search … (?a = ?b)` 로는
      **원리적으로** 못 찾는다(놓친 것의 41% 를 차지하던 ⑤ 의 정체).
      → 관계 무제약 질의를 **먼저** 쓰고, 등식 제약은 좁히는 용도로만 덧붙인다.

    ★ **notation 이 진짜 이름을 가린다.** 출력형 goal 은 `P ** Q` 라고 찍지만
      실제 상수는 `sepconj` 다. `Search "**"` 로 notation 문자열을 직접 물으면 잡힌다.
    """
    goal = strip_outer(goal)
    syms = rigid_syms(goal, locals_, maxn)
    notas = [m.group(1) for m in _NOTA.finditer(" " + goal + " ")]
    notas = [n for n in dict.fromkeys(notas) if n not in ("=", "->", ":")][:2]
    out, seen = [], set()

    def add(q):
        if q not in seen and len(q) < 300:
            seen.add(q); out.append(q)

    # ① 기호 결합 — 좁은 것부터 (관계 무제약)
    for k in (3, 2, 1):
        if len(syms) >= k:
            add("Search " + " ".join(syms[:k]) + ".")
    # ② 등식으로 좁힌 것 (rewrite 에 유용)
    for k in (3, 2):
        if len(syms) >= k:
            add("Search " + " ".join(syms[:k]) + " (?a = ?b).")
    return out


def notation_queries(goal: str, locals_: set, maxn: int = 2) -> list:
    """`Search "**"` — notation 문자열로 직접 묻는다. **위험 질의**다.

    ★ 없는 notation 이면 `Unable to interpret "…" as a reference` 오류가 나고
      Coq 이 파일 처리를 중단해 **뒤 질의가 전부 죽는다**
      (실측: 질의 중간 사망 84건 중 **29건**이 이것).
      그래서 다른 질의와 섞지 않고 **전체 목록의 맨 뒤**에 따로 붙인다 —
      죽어도 잃는 것이 없게.
    """
    goal = strip_outer(goal)
    notas = [m.group(1) for m in _NOTA.finditer(" " + goal + " ")]
    out, seen = [], set()
    for n in dict.fromkeys(notas):
        if n in ("=", "->", ":", "-", "+", "*", "/") or len(n) < 2:
            continue
        q = f'Search "{n}".'
        if q not in seen:
            seen.add(q); out.append(q)
        if len(out) >= maxn:
            break
    return out


def hyp_rewrite_queries(goal, locals_: set, maxn: int = 3) -> list:
    """`rewrite L in H` — **가설 안**을 재작성한다. 가설의 기호로 질의한다.

    ★ 전방추론이라 lemma 결론이 goal 과 맞을 이유가 없다. 그리고 `rewrite … in H` 는
      `apply … in H` 와도 다르다 — lemma 의 **좌변이 H 의 부분항**과 맞아야지
      lemma 의 전제가 H 인 것이 아니다. 그래서 `<H타입> -> ?z` 형태도 틀렸다
      (실측: `rewrite … in H` 복원율 25.0% 로 최악이었다).
      → **가설 타입의 기호**로 `Search` 한다.
    """
    out, seen = [], set()
    for h in (getattr(goal, "hyps", None) or []):
        m = _DECL_LINE.match(h)
        if not m:
            continue
        ty = h[m.end():].strip()
        if not ty or len(ty) > 240:
            continue
        for q in symbol_queries(ty, locals_, maxn=4):
            if q not in seen:
                seen.add(q); out.append(q)
        if len(out) >= maxn * 3:
            break
    return out[:maxn * 3]


def elab_subterms(elab_goal_concl: str, maxn: int = 8) -> list:
    """**elaborate 된** goal 결론에서 부분항을 뽑는다 — `SearchRewrite` 대상용.

    ★ 출력형 goal 에서 뽑으면 세 가지를 놓친다(실측):
        · 괄호 안 친 최상위 적용 (`Int.and x y`)
        · notation 이 가린 구조 (`P ** Q` 는 괄호가 없다 — 실은 `sepconj P Q`)
        · `if … then … else` 안쪽 (rewrite ZMap.gi 가 후보 0 이던 원인)
      elaborate 형은 **완전히 괄호가 쳐진 적용**이라 이 셋이 다 풀린다.

    적용 노드마다 `(f a b …)` 를 만들고, 인자를 `?z` 로 바꾼 **1단 추상**도 같이 낸다
    (redex 는 대개 인자가 구체적이지 않다).
    """
    from premise_selection.fingerprint import parse as _parse
    n = _parse(elab_goal_concl)
    if n is None:
        return []
    nodes: list = []

    def walk(t, d=0):
        if t is None or d > 8:
            return
        if t[0] == "app":
            nodes.append(t)
            walk(t[1], d + 1)
            for a in t[2]:
                walk(a, d + 1)
    walk(n)

    def emit(t):
        if t[0] == "atom":
            return t[1]
        return "(" + emit(t[1]) + " " + " ".join(emit(a) for a in t[2]) + ")"

    out, seen = [], set()
    # 큰 것부터 — redex 는 보통 중간 크기라 양쪽을 고루 담는다
    nodes.sort(key=lambda t: -len(emit(t)))
    for t in nodes:
        s1 = emit(t)
        if not (6 < len(s1) < 240):
            continue
        for cand in (s1,
                     "(" + emit(t[1]) + " " + " ".join(f"?z{i}" for i in range(len(t[2]))) + ")"):
            if cand not in seen and _SAFE.match(cand):
                seen.add(cand); out.append(cand)
        if len(out) >= maxn:
            break
    return out[:maxn]


# ── 최대 재현율 모드 ─────────────────────────────────────────────────────────
#
#   목표가 "**전체 참조 가능 집합 → 필터 → gold 포함률 100%**" 로 좁혀지면
#   후보 수는 부차적이다. 좁히는 질의만으로는 못 닿는 것들이 있고, 그때는
#   **기호 하나씩** 넓게 쏴야 한다.
#
#   실측으로 남던 것들:
#     · `rewrite sep_swap23`   결론이 `massert_eqv` — 기호 결합이 안 좁혀짐
#     · `rewrite … in H`       가설 안을 재작성 — goal 기호로는 안 닿음
#     · `rewrite <- (L …)`     역방향 + 항 적용
#     · `apply L with (1:=H)`  전제 자리 지정

def wide_queries(goal: str, locals_: set, hyps=None, maxsym: int = 10) -> list:
    """**넓게** 쏘는 질의 — 기호 하나씩, 관계 무제약.

    goal 기호 각각 + 가설 기호 각각. 후보는 많아지지만 **닿는다**.
    """
    out, seen = [], set()

    def add(q):
        if q not in seen:
            seen.add(q); out.append(q)

    for s in rigid_syms(strip_outer(goal), locals_, maxsym):
        add(f"Search {s}.")
    for h in (hyps or []):
        m = _DECL_LINE.match(h)
        ty = h[m.end():].strip() if m else ""
        if not ty or len(ty) > 240:
            continue
        for s in rigid_syms(strip_outer(ty), locals_, 4):
            add(f"Search {s}.")
    return out


# ── goal **안쪽** 바인더 · 전역 이름 검증 ─────────────────────────────────────
_GBIND = [
    re.compile(r"\bforall\s+([^,]{1,200}),"),
    re.compile(r"\bexists\s*!?\s*([^,]{1,200}),"),
    re.compile(r"\bfun\s+([^=]{1,200})=>"),
    re.compile(r"\blet\s+([A-Za-z_][\w']*)"),
    re.compile(r"\bdo\s+([A-Za-z_][\w']*)\s*<-"),
    re.compile(r"\bmatch\s+.*?\bwith\b"),          # match 분기 변수는 아래 `|` 로
]
_MATCHARM = re.compile(r"\|\s*[A-Za-z_][\w'.]*\s+([^=>|]{1,80})=>")


def goal_binders(term: str) -> set:
    """goal **안쪽**에서 묶인 이름 — `exists (changed : bool) (e' : typenv), …` 의 changed·e'.

    ★ 가설 목록(`hyps`)에만 있는 게 아니다. 이것들을 전역 상수로 착각하고
      `Search changed.` 를 쏘면 **문법 오류**가 나고, Coq 은 그 시점에 파일 처리를
      중단하므로 **뒤 질의가 전부 죽는다**(실측: `후보 0` 의 주범, 남은 실패의 56%).
    """
    out: set = set()
    for rx in _GBIND[:5]:
        for m in rx.finditer(term):
            seg = m.group(1)
            seg = re.sub(r":\s*[^)]*", "", seg)      # `(x : T)` 의 타입 제거
            out |= set(re.findall(r"[A-Za-z_][\w']*", seg))
    for m in _MATCHARM.finditer(term):
        out |= set(re.findall(r"[A-Za-z_][\w']*", m.group(1)))
    out.discard("")
    return out


_GLOBALS: Optional[set] = None
GLOBALS_DB = "raw-data/coqstoq-test/coqstoq-test-sentences.db"
GLOBALS_ELAB = "data/elab_compcert.jsonl"


def known_globals() -> set:
    """실제로 선언된 이름들. `Search` 인자를 여기에 대조해 **오류 질의를 막는다**."""
    global _GLOBALS
    if _GLOBALS is not None:
        return _GLOBALS
    g: set = set()
    try:
        import json as _json
        if os.path.exists(GLOBALS_ELAB):
            for ln in open(GLOBALS_ELAB):
                ln = ln.strip()
                if ln:
                    n = _json.loads(ln)["name"]
                    g.add(n); g.add(n.split(".")[-1])
    except Exception:
        pass
    try:
        import sqlite3 as _sq
        c = _sq.connect(GLOBALS_DB); c.execute("PRAGMA query_only=1")
        rx = re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?"
                        r"(?:Lemma|Theorem|Definition|Corollary|Fixpoint|Inductive|Remark|"
                        r"Proposition|Instance|Record|Axiom|Parameter|Fact|Property|Variable|"
                        r"Class|CoFixpoint|Notation)\s+([A-Za-z_][\w']*)")
        for (t,) in c.execute("SELECT text FROM sentence"):
            m = rx.match(t or "")
            if m:
                g.add(m.group(1))
    except Exception:
        pass
    _GLOBALS = g
    return g
