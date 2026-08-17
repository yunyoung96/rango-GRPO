"""gold tactic 에서 전역 lemma 이름을 뽑는다 — 측정 스크립트 공용."""
import re

# ── gold lemma 이름 추출 (정확도가 측정 전체를 좌우한다) ──────────────────────
#   함정: `rewrite IHm in b` 의 b, `rewrite X ; try rewrite Y` 의 try 처럼 lemma 가 아닌
#   토큰이 잡히면 "풀에 없음"으로 잘못 집계된다. 그래서
#     ① `;` 앞의 **첫 tactic** 만 본다   ② ` in ` 뒤(대상 가설)는 버린다
#     ③ tactic 키워드·지역가설·짧은 소문자 이름을 제외한다
_TACKW = {
    "rewrite", "apply", "eapply", "erewrite", "in", "with", "by", "at", "using",
    "auto", "eauto", "lia", "omega", "now", "intros", "intro", "destruct", "simpl",
    "unfold", "induction", "exact", "constructor", "reflexivity", "congruence",
    "discriminate", "try", "repeat", "assumption", "inversion", "subst", "split",
    "left", "right", "exists", "case", "elim", "generalize", "clear", "revert",
    "specialize", "pose", "set", "remember", "assert", "cut", "trivial", "ring",
    "field", "auto_with", "firstorder", "tauto", "intuition", "symmetry", "transitivity",
    "etransitivity", "f_equal", "change", "replace", "cbn", "cbv", "lazy", "hnf",
    "red", "fold", "injection", "discrR", "nia", "psatz", "idtac", "fail", "solve",
    "first", "progress", "instantiate", "refine", "econstructor", "eexists", "esplit",
}
_LOCALPAT = re.compile(r"^(?:H\d*|H'+|IH\w*|Heq\w*|Hyp\w*|eq\d+|E\d*|e\d*|n\d*|m\d*|"
                       r"l\d*|x\d*|y\d*|z\d*|v\d*|a\d*|b\d*|c\d*|d\d*|p\d*|"
                       r"q\d*|s\d*|t\d*|w\d*|i\d*|j\d*|k\d*|f\d*|g\d*|h\d*)$")
_IDRE = re.compile(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*")


def gold_lemma(tac: str):
    """tactic 에서 실제로 쓰인 **전역 lemma 이름**(마지막 성분). 없으면 None."""
    t = (tac or "").strip()
    t = re.split(r"\s*;\s*", t)[0]                 # ① 첫 tactic 만
    head = t.split()[0].lower().strip(";.") if t.split() else ""
    if head not in ("rewrite", "apply", "eapply", "erewrite"):
        return None
    rest = t[len(head):]
    rest = re.split(r"\bin\b", rest)[0]            # ② 대상 가설 제거
    rest = rest.lstrip(" <->").lstrip()             # rewrite <- / -> 방향 표시 제거
    for x in _IDRE.findall(rest):
        base = x.split(".")[-1]
        if base in _TACKW or base.isdigit():
            continue
        if _LOCALPAT.match(base):
            continue
        if len(base) < 3 and base.islower():        # ③ 짧은 소문자 = 지역 변수
            continue
        return base
    return None
