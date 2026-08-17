"""gold tactic 에서 **참조된 전역 lemma 이름**을 뽑는다 — 측정 스크립트 공용.

## 왜 어렵나

lemma 를 참조하는 문법이 `apply X` 하나가 아니다. TRAIN 4,000 예제의 tactic head 분포를
세어 보면 `apply`(515)·`rewrite`(332) 외에도 `destruct`(194)·`unfold`(123)·`move`(84)·
`induction`(70)·`exact`(64)·`have`(62)·`eapply`(53)·`elim`(48)·`auto`(169) 가 줄줄이 나온다.
넷만 보면 참조의 절반 이상을 놓친다.

또 같은 tactic 안에서도 인자 문법이 갈린다.

    apply X.                    apply (X a b).           apply X with (n := 3).
    rewrite <- X, Y at 2.       rewrite !X in H.         erewrite X by auto.
    exact (X _ _).              elim X using Y.          induction l using X.
    destruct (X a) as [p q].    specialize (X a).        pose proof X as H.
    auto using X, Y.            eauto 5 using X with db.
    apply: X.                   exact: X.                rewrite -X.        (SSReflect)
    move/X.                     case/X.                  have := X a.

## 무엇을 빼야 하나

  · tactic 키워드 (`try`, `by`, `now`, `repeat`, `auto` …)
  · **지역 가설·변수** (`H`, `H0`, `IHl`, `Heq`, 그리고 goal 가설블록에 선언된 이름)
  · 명명 인자의 **왼쪽** (`with (n := 3)` 의 `n` 은 lemma 의 바인더 이름)
  · `as [x y]` 의 패턴 이름, `in H` 의 대상, `with db` 의 hint DB 이름
  · 숫자, 한 글자 소문자

## 쓰는 법

    gold_lemmas(tactic, local_names)  → 참조된 이름 리스트 (등장 순서, 중복 제거)
    gold_lemma(tactic, local_names)   → 그중 첫 번째 (없으면 None)

`local_names` 는 `tactic_gen.search_query.local_names(proof_state)` 로 얻는다. 넘기지 않으면
정규식 패턴만으로 지역 이름을 걸러내므로 정확도가 떨어진다.
"""
from __future__ import annotations

import re

# ── tactic 키워드 (이름으로 오인하면 안 되는 것) ─────────────────────────────
_TACKW = {
    # 흔한 tactic
    "rewrite", "apply", "eapply", "erewrite", "setoid_rewrite", "rewrite_strat",
    "autorewrite", "exact", "eexact", "refine", "eapply_clear", "simple",
    "auto", "eauto", "firstorder", "trivial", "tauto", "intuition", "congruence",
    "discriminate", "lia", "nia", "lra", "nra", "omega", "ring", "ring_simplify",
    "field", "field_simplify", "psatz", "btauto", "reflexivity", "symmetry",
    "transitivity", "etransitivity", "f_equal", "assumption", "exfalso",
    "intros", "intro", "destruct", "induction", "elim", "case", "inversion",
    "injection", "subst", "clear", "clearbody", "revert", "generalize", "specialize",
    "pose", "proof", "set", "remember", "assert", "cut", "enough", "refine",
    "split", "left", "right", "exists", "eexists", "esplit", "constructor",
    "econstructor", "simpl", "cbn", "cbv", "lazy", "hnf", "red", "unfold", "fold",
    "change", "replace", "rename", "move", "have", "suff", "suffices", "wlog",
    "without", "loss", "by", "now", "try", "repeat", "first", "solve", "progress",
    "idtac", "fail", "instantiate", "abstract", "shelve", "unshelve", "admit",
    "give_up", "time", "do", "once", "exactly_once", "only", "all", "par",
    "swap", "cycle", "revgoals", "guard", "let", "in", "with", "as", "using",
    "at", "into", "eqn", "type", "of", "after", "before", "until", "return",
    "end", "match", "goal", "context", "constr", "ltac", "fun", "forall",
    "discrR", "vm_compute", "native_compute", "compute", "decide", "equality",
    "dependent", "rewrite_all", "easy", "done", "rew", "over", "under",
}

# 지역 가설·변수로 굳어진 관용 이름들. goal 가설블록을 넘겨받으면 그쪽이 더 정확하다.
_LOCALPAT = re.compile(
    r"^(?:H\d*|H'+\d*|IH\w*|Heq\w*|Hyp\w*|Hle\w*|Hlt\w*|Hn\w*|eq\d+|E\d*|"
    r"[a-z]\d*|[a-z]'\d*)$")

_IDRE = re.compile(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*")

# ── 참조 위치를 아는 tactic ──────────────────────────────────────────────────
#   값: 인자 전체에서 이름을 훑는다(True) / `using`·`/`·`:=` 뒤만 본다(False)
_TERM_HEADS = {
    "apply", "eapply", "exact", "eexact", "refine", "rewrite", "erewrite",
    "setoid_rewrite", "rewrite_strat", "elim", "case", "destruct", "induction",
    "specialize", "generalize", "absurd", "contradict", "symmetry", "transitivity",
    "etransitivity", "replace", "unfold", "fold", "inversion", "injection",
    "constructor", "econstructor", "revert", "move", "have", "suff", "suffices",
}
# `using X` / `with db` 를 갖는 것들 — using 뒤만 lemma 다
_USING_HEADS = {"auto", "eauto", "firstorder", "intuition", "induction", "elim",
                "destruct", "case", "trivial", "eassumption"}

# tactic 을 감싸는 결합자 — 벗겨내고 안쪽을 다시 본다
_WRAPPERS = re.compile(
    r"^\s*(?:try|repeat|now|by|first|solve|progress|once|do\s+\d+|time|abstract|"
    r"all|par|only\s+[\d,\-]+)\s*[:\s]\s*")

_SPLIT = re.compile(r"[;|]|\[|\]|\{|\}")


def _pieces(tac: str) -> list[str]:
    """tactic 을 조각으로. `;` `|` 분기와 대괄호 분기를 모두 벗긴다."""
    out = []
    for raw in _SPLIT.split(tac or ""):
        s = raw.strip().lstrip("-+*> ").strip()
        while s:
            m = _WRAPPERS.match(s)
            if not m:
                break
            s = s[m.end():].strip()
        if s:
            out.append(s)
    return out


def _strip_modifiers(rest: str) -> str:
    """인자부에서 lemma 가 아닌 조각을 제거한다.

    · ` in H`  대상 가설            · ` as [x y]` 패턴 이름
    · ` at 2`  위치                 · ` with db`(auto 계열의 hint DB)
    · `(n := 3)` 의 왼쪽            · `<- -> ! ? -` 방향·반복 수식어
    """
    s = rest
    s = re.split(r"\bin\b", s)[0]                       # in H
    s = re.split(r"\bas\b", s)[0]                       # as [x y]
    s = re.sub(r"\bat\s+[\d\s,]+", " ", s)              # at 2
    s = re.sub(r"\beqn\s*:\s*\w+", " ", s)              # destruct … eqn:E
    # `with (n := 3)` 의 n, `(x:=t)` 의 x 를 지운다 (lemma 의 바인더 이름)
    s = re.sub(r"([A-Za-z_][\w']*)\s*:=", " := ", s)
    s = s.replace("<-", " ").replace("->", " ")
    s = re.sub(r"[!?]", " ", s)
    s = re.sub(r"(?<![\w')])-(?=[A-Za-z_(])", " ", s)   # SSReflect `rewrite -X`
    return s


def _names_in(s: str, loc: set[str]) -> list[str]:
    out = []
    for x in _IDRE.findall(s or ""):
        b = x.split(".")[-1]
        if b in _TACKW or b.isdigit():
            continue
        if set(b) <= {"_"}:            # `_` 는 Coq 와일드카드지 이름이 아니다
            continue
        if b in loc or _LOCALPAT.match(b):
            continue
        if len(b) < 3 and b.islower():
            continue
        if b not in out:
            out.append(b)
    return out


def gold_lemmas(tac: str, loc: set[str] | None = None) -> list[str]:
    """tactic 이 참조하는 전역 lemma 이름 전부 (등장 순서, 중복 제거)."""
    loc = loc or set()
    out: list[str] = []
    for piece in _pieces(tac):
        toks = piece.split()
        if not toks:
            continue
        raw_head = toks[0].strip(".:")
        head = raw_head.lower()
        # SSReflect view: `move/X`, `case/X`, `apply/X`
        mview = re.match(r"^(move|case|apply|exact|elim|rewrite)\s*/\s*(.+)$", piece)
        if mview:
            out += [n for n in _names_in(_strip_modifiers(mview.group(2)), loc)
                    if n not in out]
            continue
        # `have := X a` / `have H : T := X` — := 뒤가 항
        if head in ("have", "pose", "set", "assert", "suff", "suffices"):
            if ":=" in piece:
                out += [n for n in _names_in(
                    _strip_modifiers(piece.split(":=", 1)[1]), loc) if n not in out]
            elif head == "pose" and len(toks) > 1 and toks[1] == "proof":
                out += [n for n in _names_in(
                    _strip_modifiers(" ".join(toks[2:])), loc) if n not in out]
            continue
        rest = piece[len(raw_head):]
        if head in _USING_HEADS and re.search(r"\busing\b", rest):
            seg = re.split(r"\busing\b", rest, 1)[1]
            seg = re.split(r"\bwith\b", seg)[0]          # with db 는 hint DB
            out += [n for n in _names_in(_strip_modifiers(seg), loc) if n not in out]
            if head not in _TERM_HEADS:
                continue
            rest = re.split(r"\busing\b", rest, 1)[0]
        elif head in _USING_HEADS and head not in _TERM_HEADS:
            continue                                     # `auto with db` 등 — lemma 없음
        if head in _TERM_HEADS:
            if head in ("auto", "eauto", "trivial"):
                continue
            out += [n for n in _names_in(_strip_modifiers(rest), loc) if n not in out]
    return out


def gold_lemma(tac: str, loc: set[str] | None = None):
    """참조된 첫 lemma 이름. 없으면 None."""
    xs = gold_lemmas(tac, loc)
    return xs[0] if xs else None
