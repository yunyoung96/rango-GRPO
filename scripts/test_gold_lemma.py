#!/usr/bin/env python3
"""gold_lemma 추출 검증 — **다양한 apply/rewrite 문법을 다 커버하는가**.

측정 전체가 이 추출기에 의존한다. 놓치면 "lemma 를 안 쓰는 tactic" 으로 잘못 세고,
과하게 잡으면 "데이터셋 밖" 이 부풀어 오른다. 실제 TRAIN 에 나오는 문법을 케이스로 박아둔다.
"""
import sys

sys.path.insert(0, "src")
from tactic_gen.gold_lemma import gold_lemmas  # noqa: E402

LOC = {"H", "H0", "H1", "HDisjCalls", "IHl", "Heqx2", "l", "n", "m", "a", "b", "x", "y",
       "sz1", "tc1", "s", "d", "epos", "HSemAction", "Hy'", "L10", "H3"}

CASES = [
    # ── 기본 ──
    ("apply Zlt_le_succ.", ["Zlt_le_succ"]),
    ("eapply ratAdd_eqRat_compat.", ["ratAdd_eqRat_compat"]),
    ("rewrite Nat.add_comm.", ["add_comm"]),
    ("erewrite foo_bar.", ["foo_bar"]),
    # ── 인자·방향·수식어 ──
    ("apply (Zlt_le_succ 0 a), epos.", ["Zlt_le_succ"]),
    ("apply Z.le_trans with sz1.", ["le_trans"]),
    ("apply plus_le_compat with (n := 3).", ["plus_le_compat"]),
    ("rewrite <- plus_n_O.", ["plus_n_O"]),
    ("rewrite -> ExpandAnd.", ["ExpandAnd"]),
    ("rewrite mul_comm at 2.", ["mul_comm"]),
    ("rewrite !app_length.", ["app_length"]),
    ("rewrite ?rev_length.", ["rev_length"]),
    ("rewrite divides_rem_rem, mul_comm.", ["divides_rem_rem", "mul_comm"]),
    # ── in / as 는 대상이므로 이름이 아니다 ──
    ("apply M.F.P.F.not_find_in_iff in HDisjCalls.", ["not_find_in_iff"]),
    ("rewrite eqb_leibniz in Heqx2.", ["eqb_leibniz"]),
    ("rewrite L10 in H3.", []),                         # 둘 다 지역
    ("destruct (lt_dec n m) as [p q].", ["lt_dec"]),
    # ── 다른 tactic 들 ──
    ("exact rev_involutive.", ["rev_involutive"]),
    ("exact (app_length l1 l2).", ["app_length"]),
    ("elim le_lt_dec.", ["le_lt_dec"]),
    ("induction l using rev_ind.", ["rev_ind"]),
    ("elim n using nat_ind.", ["nat_ind"]),
    ("specialize (le_trans a b).", ["le_trans"]),
    ("pose proof Nat.le_max_l as Hm.", ["le_max_l"]),
    ("unfold not_find_in_iff.", ["not_find_in_iff"]),
    ("inversion wf_step.", ["wf_step"]),
    ("refine (ex_intro _ _ _).", ["ex_intro"]),
    # ── auto/eauto: using 뒤만 ──
    ("auto using rev_length.", ["rev_length"]),
    ("eauto 5 using app_length with arith.", ["app_length"]),
    ("auto with arith.", []),                           # hint DB 는 lemma 아님
    ("auto.", []),
    # ── 결합자 벗기기 ──
    ("try rewrite mul_comm.", ["mul_comm"]),
    ("now apply le_refl.", ["le_refl"]),
    ("repeat rewrite app_nil_r.", ["app_nil_r"]),
    ("apply CompIdLeft ; auto.", ["CompIdLeft"]),
    ("rewrite IHl ; try rewrite app_length ; inversion H.", ["app_length"]),
    ("apply in_app_or in H ; destruct H as [ H | H ] ; [ apply Hy' | contradiction ].",
     ["in_app_or"]),
    # ── SSReflect ──
    ("apply: leEq_reflexive.", ["leEq_reflexive"]),
    ("exact: rev_length.", ["rev_length"]),
    ("rewrite -ptd_cost_build_from_pt.", ["ptd_cost_build_from_pt"]),
    ("move/eqP.", ["eqP"]),
    ("case/andP.", ["andP"]),
    ("have := app_length l.", ["app_length"]),
    ("have H2 : P := my_lemma.", ["my_lemma"]),
    ("by apply subset_trans.", ["subset_trans"]),
    # ── 지역 가설만 쓰는 경우 → 없음 ──
    ("apply H.", []),
    ("rewrite H0.", []),
    ("rewrite IHm in b.", []),
    ("apply tr.", []),
    ("rewrite -> eq1.", []),
    ("intros a b.", []),
    ("simpl.", []),
    ("destruct l.", []),
    ("induction l.", []),
]

fail = []
for tac, want in CASES:
    got = gold_lemmas(tac, LOC)
    if got != want:
        fail.append(f"  ✗ {tac:66s}\n      got={got}  want={want}")

print(f"■ gold_lemma 문법 커버리지 — {len(CASES)}건")
if fail:
    print(f"\n실패 {len(fail)}건:")
    print("\n".join(fail))
    sys.exit(1)
print("전부 통과")
