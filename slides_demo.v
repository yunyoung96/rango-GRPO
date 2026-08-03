(** Coq examples used in presentation/slides.md.

    Run this file one command at a time in CoqIDE or VS Code with VSCoq
    to demonstrate how the proof state changes.
*)

(** 1. Introduce a variable, simplify, and close the equality. *)
Theorem zero_plus_n : forall n : nat, 0 + n = n.
Proof.
  intros n.
  simpl.
  reflexivity.
Qed.

(** Prove a lemma, then reuse it as a premise. *)
Lemma zero_plus : forall n : nat, 0 + n = n.
Proof.
  intros n.
  simpl.
  reflexivity.
Qed.

Theorem zero_plus_twice : forall n : nat, 0 + (0 + n) = n.
Proof.
  intros n.
  rewrite zero_plus.
  simpl.
  reflexivity.
Qed.

(** 2. Split a Boolean into its two possible cases. *)
Theorem bool_cases : forall b : bool, b = true \/ b = false.
Proof.
  intros b.
  destruct b.
  - left.
    reflexivity.
  - right.
    reflexivity.
Qed.
