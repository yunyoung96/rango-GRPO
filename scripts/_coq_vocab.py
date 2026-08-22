"""Coq **기본 어휘** — 프롬프트 검사기가 "프로젝트 고유 이름" 으로 오인하면 안 되는 것들.

## 왜 필요한가

검사기들은 "정답이 쓰는 이름이 프롬프트에 있는가" 를 본다. 그런데 정답에는
`True` · `BoolSpec` · `Nat` · `list` 처럼 **Coq 이 기본으로 아는 이름**이 섞인다.
그걸 프로젝트 이름으로 세면 "프롬프트에 없다 → 환각" 이라고 신고하고 학습을 막는다.
실측 오탐: `idx=1984542 True` · `BoolSpec`.

이 계열의 오탐은 이번이 일곱 번째다. 어휘 판정을 **한 곳에** 모아 둔다.
(엄밀한 목록이 아니라 **오탐을 막을 만큼**의 목록이다. 빠진 것이 있으면 여기 더한다.)
"""

# 논리·타입
CORE_TYPES = """
Prop Set Type SProp True False and or not iff eq ex all
nat bool unit list option prod sum sig sigT sigT2 sig2 comparison
positive N Z Q R Rdefinitions ascii string byte
Empty_set Inhabited Acc
""".split()

# 생성자·기본 함수
CORE_TERMS = """
O S tt I conj or_introl or_intror ex_intro eq_refl eq_ind eq_rect eq_sym eq_trans
nil cons Some None pair fst snd left right inl inr exist existT
xI xO xH Npos N0 Zpos Zneg Z0
true false negb andb orb xorb implb
length app rev map filter fold_left fold_right nth hd tl In
plus minus mult div modulo pred succ max min pow
le lt ge gt leb ltb eqb compare
id const flip comp proj1 proj2 projT1 projT2
""".split()

# 표준 술어·구조 (자주 정답에 그대로 나온다)
CORE_PREDS = """
BoolSpec CompareSpec CompSpec Decidable Equivalence Reflexive Symmetric Transitive
Proper respectful relation subrelation PreOrder PartialOrder StrictOrder
Permutation Forall Exists NoDup Sorted HdRel LocallySorted
well_founded Fix Acc_inv
""".split()

# 모듈 접두사로 자주 오는 것
CORE_MODULES = """
Nat PeanoNat List Bool Arith Lia Zarith ZArith Znat Nnat Pnat Ascii String
Coq Datatypes Logic Init Specif Basics Wf Relations Morphisms Setoid
Pos Zpos Z N Q R Rdefinitions Raxioms RIneq Rfunctions
""".split()

# ★ SSReflect · Ltac **문법 키워드** — 이름이 아니다.
#   실측 오탐: `have ox := (L19 oix).` 의 `have` 를 "프롬프트에 없는 이름" 으로 신고했다.
SSR_LTAC = """
have suff suffices wlog without loss move case elim apply exact congr
rewrite under over set pose put fold unfold by done first last
do rep repeat try solve abstract now let2 exists2 esplit eexists
gen depelim dependent generalizing using with into as in at
lazymatch multimatch match context goal hyp ltac idtac fail assert
change replace symmetry transitivity reflexivity etransitivity
""".split()

COQ_VOCAB = frozenset(CORE_TYPES + CORE_TERMS + CORE_PREDS + CORE_MODULES + SSR_LTAC)


def is_core(name: str) -> bool:
    """`name` (모듈 접두사 포함 가능) 이 Coq 기본 어휘인가."""
    if not name:
        return False
    if name in COQ_VOCAB:
        return True
    # `Nat.iter` · `List.map` — 접두사와 꼬리 중 하나라도 기본이면 기본으로 본다
    parts = name.split(".")
    return parts[0] in COQ_VOCAB or parts[-1] in COQ_VOCAB


if __name__ == "__main__":
    import sys
    for a in sys.argv[1:] or ["True", "BoolSpec", "subst_arr", "Nat.iter", "my_lemma"]:
        print(f"   {a:20s} {'기본 어휘' if is_core(a) else '프로젝트 이름'}")
