# ❌ opener-sub(wo compound) 실패 예시

작성 2026-08-01. opener-sub(wo compound)가 못 닫은(dead) 정리들.
롤아웃: `data/grpo_rollouts/combo_subgoal_opener.jsonl`. executor=subgoal 모델.

## 롤아웃 성공/실패율 (train 100, greedy 단일궤도)
| | 개수 | 비율 |
|---|---|---|
| **성공(≥1)** | 30/94 | **32%** |
| &nbsp;└ all-solved | 5 | 5% |
| &nbsp;└ mixed | 25 | 27% |
| **실패(dead)** | 64/94 | **68%** |
| attempt당 | | 17.0% |

## 읽는 법
- `✓ VALID` 적용성공 / `❌ INVALID` 거부(상태유지→재시도) / `✅ COMPLETE` 완결 / `↻재시도` 앞 실패로 같은자리
- `[opener]`/`[rango]` 누가 낸 수인가

---
### `succ_pred` · plain: dead
**GOLD 전문:**
```coq
Proof.
intros x Fx.
destruct (Rle_or_lt 0 x) as [[Hx|Hx]|Hx].
now apply succ_pred_pos.
rewrite <- Hx.
rewrite pred_0, succ_opp, pred_ulp_0.
apply Ropp_0.
unfold pred.
rewrite succ_opp, pred_succ_pos.
apply Ropp_involutive.
now apply generic_format_opp.
now apply Ropp_0_gt_lt_contravar.
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros x Fx.                                          | ✓  VALID
[rango ] apply Rle_antisym.                                    | ✓  VALID
[rango ] replace (pred x) with ((-1)^(ZnearestA (pred (x))))%… | ❌ INVALID(거부, 상태유지)
[rango ] -                                                     | ✓  VALID  ↻재시도
[rango ] apply succ_le_lt with (1 := Fx).                      | ❌ INVALID(거부, 상태유지)
[rango ] rewrite pred_eq_pos.                                  | ✓  VALID  ↻재시도
[rango ] rewrite succ_eq_pos by now apply pred_pos_ge_0.       | ❌ INVALID(거부, 상태유지)
[rango ] 2: rewrite <- Rplus_0_r.                              | ✓  VALID  ↻재시도
[rango ] 2: left.                                              | ✓  VALID
[rango ] rewrite succ_eq_pos.                                  | ✓  VALID
[rango ] 2: rewrite <- Rplus_0_r.                              | ✓  VALID
[rango ] 2: left.                                              | ✓  VALID
[rango ] 2: now apply pred_pos_ge_0.                           | ❌ INVALID(거부, 상태유지)
[rango ] now apply pred_pos_ge_0.                              | ❌ INVALID(거부, 상태유지)  ↻재시도
```

---
### `make_predecessors_correct_2` · plain: dead
**GOLD 전문:**
```coq
Proof.
intros.
exploit make_predecessors_correct_1; eauto.
unfold successors_list.
destruct (make_predecessors!s); simpl; intros.
exists l; auto.
contradiction.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] intros.                                               | ✓  VALID
[opener] unfold successors_list.                               | ✓  VALID
[opener] destruct (make_predecessors!s); simpl; intros.        | ✓  VALID
[rango ] eauto.                                                | ✓  VALID
[rango ] eauto.                                                | ✓  VALID
[rango ] eauto.                                                | ✓  VALID
[rango ] exists l; auto.                                       | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
```

---
### `locmap_set_lessdef` · plain: dead
**GOLD 전문:**
```coq
Proof.
intros; red; intros l'.
unfold Locmap.set.
destruct (Loc.eq l l').
-
destruct l; auto using Val.load_result_lessdef.
-
destruct (Loc.diff_dec l l'); auto.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] intros; red; intros.                                  | ✓  VALID
[opener] inv H.                                                | ❌ INVALID(거부, 상태유지)
[rango ] destruct (Val.compare v1 v2) as [EQ | [LT | GT]].     | ❌ INVALID(거부, 상태유지)  ↻재시도
[rango ] induction H0.                                         | ✓  VALID  ↻재시도
[rango ] apply LocmapFacts.lessdef_set, H.                     | ❌ INVALID(거부, 상태유지)
[rango ] +                                                     | ✓  VALID  ↻재시도
[rango ] apply Locmap.lessdef_set.                             | ❌ INVALID(거부, 상태유지)
[rango ] unfold Val.lessdef.                                   | ❌ INVALID(거부, 상태유지)  ↻재시도
```

---
### `dests_disjoint_cons_right` · plain: dead
**GOLD 전문:**
```coq
Proof.
intros.
rewrite dests_disjoint_sym.
rewrite dests_disjoint_cons_left.
rewrite dests_disjoint_sym.
tauto.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] induction m1; simpl.                                  | ✓  VALID
[rango ] split; intros.                                        | ✓  VALID
[rango ] elim H; intros; auto.                                 | ❌ INVALID(거부, 상태유지)
[rango ] unfold dests_disjoint in H.                           | ✓  VALID  ↻재시도
[rango ] split.                                                | ✓  VALID
[rango ] red; intros.                                          | ✓  VALID
[rango ] rewrite map_nil in H.                                 | ❌ INVALID(거부, 상태유지)
[rango ] unfold list_disjoint in *.                            | ✓  VALID  ↻재시도
[rango ] intros.                                               | ✓  VALID
[rango ] inversion H0.                                         | ✓  VALID
[rango ] tauto.                                                | ✓  VALID
[rango ] firstorder.                                           | ✓  VALID
[rango ] destruct H.                                           | ❌ INVALID(거부, 상태유지)
[rango ] intros.                                               | ✓  VALID  ↻재시도
[rango ] rewrite dests_disjoint_cons_left.                     | ❌ INVALID(거부, 상태유지)
[rango ] unfold list_disjoint.                                 | ✓  VALID  ↻재시도
[rango ] unfold dests_disjoint.                                | ✓  VALID
[rango ] simpl.                                                | ✓  VALID
[rango ] unfold list_disjoint, list_disjoint.                  | ✓  VALID
[rango ] intros.                                               | ✓  VALID
[rango ] destruct a.                                           | ✓  VALID
[rango ] simpl.                                                | ✓  VALID
[rango ] tauto.                                                | ❌ INVALID(거부, 상태유지)
```

---
### `ptd_cost_build_from_ptl` · plain: dead
**GOLD 전문:**
```coq
Proof.
destruct ptlz=>//.
apply eq_add_S.
rewrite -ptd_cost_build_from_pt /=.
ring.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] destruct ptlz=>//.                                    | ✓  VALID
[rango ] rewrite /ptdlz_cost/ptd_cost /=.                      | ❌ INVALID(거부, 상태유지)
[rango ] -                                                     | ✓  VALID  ↻재시도
[rango ] simpl.                                                | ✓  VALID
[rango ] exact (ptd_cost_build_from_pt _ _ ptol ptolz).        | ❌ INVALID(거부, 상태유지)
[rango ] by rewrite -ptd_cost_build_from_pt .                  | ❌ INVALID(거부, 상태유지)  ↻재시도
```

---
### `pres_sem_shift` · plain: dead
**GOLD 전문:**
```coq
Proof.
intros.
unfold shift_op_type, sem_shift in *.
DestructCases; auto with ty.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] intros.                                               | ✓  VALID
[opener] unfold shift_op_type; intros; try contradiction.      | ✓  VALID
[rango ] rewrite <- H0 in H.                                   | ❌ INVALID(거부, 상태유지)
[rango ] rewrite H0 in H.                                      | ❌ INVALID(거부, 상태유지)  ↻재시도
```

---
### `eval_builtin_args_inject` · plain: dead
**GOLD 전문:**
```coq
Proof.
induction 1; intros.
-
exists (@nil val); split; constructor.
-
simpl in H5.
exploit eval_builtin_arg_inject; eauto using in_or_app.
intros (v1' & A & B).
destruct IHlist_forall2 as (vl' & C & D); eauto using in_or_app.
exists (v1' :: vl'); split; constructor; auto.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] intros.                                               | ✓  VALID
[opener] inv H.                                                | ✓  VALID
[rango ] -                                                     | ✓  VALID
[rango ] simpl.                                                | ✓  VALID
[rango ] apply eval_builtin_arg_list_inject; auto with barg.   | ❌ INVALID(거부, 상태유지)
[rango ] destruct sp; simpl in *.                              | ✓  VALID  ↻재시도
[rango ] 1,2 : intros.                                         | ✓  VALID
[rango ] +                                                     | ✓  VALID
[rango ] eauto.                                                | ✓  VALID
[rango ] found_proof_irrelevance.                              | ❌ INVALID(거부, 상태유지)
[rango ] exists nil; split; auto with barg.                    | ✓  VALID  ↻재시도
[rango ] constructor.                                          | ✓  VALID
[rango ] +                                                     | ✓  VALID
[rango ] exists nil; split; auto with barg.                    | ✓  VALID
[rango ] constructor.                                          | ✓  VALID
[rango ] +                                                     | ✓  VALID
[rango ] exists nil; split; auto with barg.                    | ✓  VALID
[rango ] constructor.                                          | ✓  VALID
[rango ] +                                                     | ❌ INVALID(거부, 상태유지)
[rango ] -                                                     | ✓  VALID  ↻재시도
[rango ] assert (Ptrofs.valid ge).                             | ❌ INVALID(거부, 상태유지)
[rango ] rewrite (eval_builtin_arg_determ _ _ _ _ H5) in *.    | ❌ INVALID(거부, 상태유지)  ↻재시도
```

---
### `traceinf_sim_refl` · plain: dead
**GOLD 전문:**
```coq
Proof.
cofix COINDHYP; intros.
destruct T.
constructor.
apply COINDHYP.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] destruct T; simpl.                                    | ✓  VALID
[rango ] constructor.                                          | ✓  VALID
[rango ] constructor.                                          | ❌ INVALID(거부, 상태유지)
[rango ] auto.                                                 | ✓  VALID  ↻재시도
[rango ] constructor.                                          | ❌ INVALID(거부, 상태유지)
[rango ] elim e.                                               | ✓  VALID  ↻재시도
[rango ] subst.                                                | ✓  VALID
[rango ] constructor.                                          | ❌ INVALID(거부, 상태유지)
```

---
### `ZOmod_eq` · plain: dead
**GOLD 전문:**
```coq
Proof.
intros a b.
rewrite (Z.quot_rem' a b) at 2.
ring.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] intros.                                               | ✓  VALID
[opener] destruct b; simpl.                                    | ✓  VALID
[rango ] apply Z.mod_small.                                    | ❌ INVALID(거부, 상태유지)
[rango ] ring.                                                 | ❌ INVALID(거부, 상태유지)  ↻재시도
```

---
### `type_code_complete` · plain: dead
**GOLD 전문:**
```coq
Proof.
intros te e0 WTC SAT0.
set (P := fun c res =>
        (forall pc i, c!pc = Some i -> wt_instr f te i) ->
        exists e', res = OK e' /\ S.satisf te e').
assert (P f.(fn_code) (type_code e0)).
{
unfold type_code.
apply PTree_Properties.fold_rec; unfold P; intros.
-
apply H0.
intros.
apply H1 with pc.
rewrite <- H; auto.
-
exists e0; auto.
-
destruct H1 as [e [A B]].
intros.
apply H2 with pc.
rewrite PTree.gso; auto.
congruence.
subst a.
destruct (type_instr_complete te e v) as [e' [C D]].
auto.
apply H2 with k.
apply PTree.gss.
exists e'; split; auto.
rewrite C; auto.
}
apply H; auto.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] intros.                                               | ✓  VALID
[opener] inv H.                                                | ❌ INVALID(거부, 상태유지)
[rango ] pose (R := fun (c opte (pc':positive)) => match pc' … | ❌ INVALID(거부, 상태유지)  ↻재시도
[rango ] destruct (fn_code f) as [s| ].                        | ✓  VALID  ↻재시도
[rango ] eauto; intros.                                        | ✓  VALID
[rango ] exists e.                                             | ✓  VALID
[rango ] constructor; auto.                                    | ✓  VALID
[rango ] unfold type_code; apply PTree.gempty.                 | ❌ INVALID(거부, 상태유지)
[rango ] apply PTree.type_code_sound; auto.                    | ❌ INVALID(거부, 상태유지)  ↻재시도
```

---
### `assign_variables_incr` · plain: dead
**GOLD 전문:**
```coq
Proof.
induction vars; intros until sz'.
simpl; intros.
inv H.
lia.
Opaque assign_variable.
destruct a as [id s].
simpl.
intros.
destruct (assign_variable (cenv, sz) (id, s)) as [cenv1 sz1] eqn:?.
apply Z.le_trans with sz1.
eapply assign_variable_incr; eauto.
eauto.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] induction vars; intros until sz'.                     | ✓  VALID
[rango ] destruct 1.                                           | ✓  VALID
[rango ] apply Z.le_trans with sz; auto.                       | ✓  VALID
[rango ] apply Z.le_refl.                                      | ✓  VALID
[rango ] simpl in TRANSL.                                      | ✓  VALID
[rango ] destruct (Z.eq_dec sz sz').                           | ✓  VALID
[rango ] subst.                                                | ✓  VALID
[rango ] apply Z.le_refl.                                      | ✓  VALID
[rango ] apply Z.neq_le_incl; auto.                            | ❌ INVALID(거부, 상태유지)
```

---
### `Zdigit_ge_Zpower_pos` · plain: dead
**GOLD 전문:**
```coq
Proof.
intros e n Hn k Hk.
unfold Zdigit.
rewrite Z.quot_small.
apply Zrem_0_l.
split.
apply Hn.
apply Z.lt_le_trans with (1 := proj2 Hn).
replace k with (e + (k - e))%Z by ring.
rewrite Zpower_plus.
rewrite <- (Zmult_1_r (beta ^ e)) at 1.
apply Zmult_le_compat_l.
apply (Zlt_le_succ 0).
apply Zpower_gt_0.
now apply Zle_minus_le_0.
apply Zlt_le_weak.
now apply Z.le_lt_trans with n.
generalize (Z.le_lt_trans _ _ _ (proj1 Hn) (proj2 Hn)).
clear.
now destruct e as [|e|e].
now apply Zle_minus_le_0.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] intros.                                               | ✓  VALID
[opener] destruct e; simpl.                                    | ✓  VALID
[rango ] now case (Zdigit n k).                                | ❌ INVALID(거부, 상태유지)
[rango ] case H; intros.                                       | ✓  VALID  ↻재시도
[rango ] easy.                                                 | ❌ INVALID(거부, 상태유지)
[rango ] apply Z.le_antisymm.                                  | ✓  VALID  ↻재시도
[rango ] eapply Zdigit_le_0; eauto.                            | ❌ INVALID(거부, 상태유지)
[rango ] rewrite (Zdigit_lt _ _ (Zlt_0_1 n)) at 1.             | ❌ INVALID(거부, 상태유지)  ↻재시도
```

---
### `return_address_exists` · plain: dead
**GOLD 전문:**
```coq
Proof.
intros.
destruct (transf_function f) as [tf|] eqn:TF.
+
exploit transf_function_inv; eauto.
intros (tc1 & ep1 & TR1 & TL1).
exploit transl_code_tail; eauto.
intros (tc2 & ep2 & TR2 & TL2).
Opaque transl_instr.
monadInv TR2.
assert (TL3: is_tail x (fn_code tf)).
{
apply is_tail_trans with tc1; auto.
apply is_tail_trans with tc2; auto.
eapply transl_instr_tail; eauto.
}
exploit is_tail_code_tail.
eexact TL3.
intros [ofs CT].
exists (Ptrofs.repr ofs).
red; intros.
rewrite Ptrofs.unsigned_repr.
congruence.
exploit code_tail_bounds_1; eauto.
apply transf_function_len in TF.
lia.
+
exists Ptrofs.zero; red; intros.
congruence.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] intros.                                               | ✓  VALID
[opener] destruct (is_tail_step (Mcall sg ros :: c) (Mach.fn_… | ❌ INVALID(거부, 상태유지)
[rango ] destruct (prog_defs f) as [s t pf].                   | ❌ INVALID(거부, 상태유지)  ↻재시도
[rango ] set (c1 := Mach.fn_code f); set (c2 := c); set (c' :… | ✓  VALID  ↻재시도
[rango ] assert (BTF: is_tail c1 c2).                          | ✓  VALID
[rango ] apply transl_instr_tail; auto.                        | ❌ INVALID(거부, 상태유지)
[rango ] {                                                     | ✓  VALID  ↻재시도
[rango ] eapply is_tail_trans with (2 := H).                   | ❌ INVALID(거부, 상태유지)
[rango ] generalize (H c c c1 c2).                             | ❌ INVALID(거부, 상태유지)  ↻재시도
```

---
### `Rnd_N0_pt_monotone` · plain: dead
**GOLD 전문:**
```coq
Proof.
intros F HF x y f g Hxf Hyg Hxy.
apply (Rnd_NG_pt_monotone F _ (Rnd_N0_pt_unique_prop F HF) x y).
now apply -> Rnd_N0_NG_pt.
now apply -> Rnd_N0_NG_pt.
exact Hxy.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] intros.                                               | ✓  VALID
[opener] unfold round_pred_monotone; intros x y Hxy.           | ✓  VALID
[rango ] now intros g Hg Hy.                                   | ❌ INVALID(거부, 상태유지)
[rango ] intros g H0 H1.                                       | ✓  VALID  ↻재시도
[rango ] unfold Rnd_N0_pt in H0.                               | ✓  VALID
[rango ] elim H0; clear H0; intros H0 H1.                      | ❌ INVALID(거부, 상태유지)
[rango ] intros H2.                                            | ✓  VALID  ↻재시도
[rango ] elim H0.                                              | ✓  VALID
[rango ] intros.                                               | ✓  VALID
[rango ] elim H1.                                              | ✓  VALID
[rango ] intros.                                               | ✓  VALID
[rango ] halign H4 with y.                                     | ❌ INVALID(거부, 상태유지)
[rango ] assert (H7 : x = y).                                  | ✓  VALID  ↻재시도
[rango ] apply Rabs_inj_above; assumption.                     | ❌ INVALID(거부, 상태유지)
[rango ] apply Rnd_N_pt_monotone; assumption.                  | ❌ INVALID(거부, 상태유지)  ↻재시도
```

---
### `plub_comm` · plain: dead
**GOLD 전문:**
```coq
Proof.
intros; unfold plub; destruct p; destruct q; auto.
destruct (ident_eq id id0).
subst id0.
rewrite dec_eq_true.
destruct (Ptrofs.eq_dec ofs ofs0).
subst ofs0.
rewrite dec_eq_true.
auto.
rewrite dec_eq_false by auto.
auto.
rewrite dec_eq_false by auto.
auto.
destruct (ident_eq id id0).
subst id0.
rewrite dec_eq_true; auto.
rewrite dec_eq_false; auto.
destruct (ident_eq id id0).
subst id0.
rewrite dec_eq_true; auto.
rewrite dec_eq_false; auto.
destruct (ident_eq id id0).
subst id0.
rewrite dec_eq_true; auto.
rewrite dec_eq_false; auto.
destruct (Ptrofs.eq_dec ofs ofs0).
subst ofs0.
rewrite dec_eq_true; auto.
rewrite dec_eq_false; auto.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] intros; unfold plub.                                  | ✓  VALID
[opener] destruct p; destruct q; auto.                         | ✓  VALID
[rango ] all: destruct ident_eq; subst; simpl; auto.           | ❌ INVALID(거부, 상태유지)
[rango ] -                                                     | ✓  VALID  ↻재시도
[rango ] destruct (ident_eq id0 id).                           | ✓  VALID
[rango ] *                                                     | ✓  VALID
[rango ] destruct (ident_eq id id0); auto using (zdec_no_dec_… | ✓  VALID
[rango ] +                                                     | ✓  VALID
[rango ] destruct (Ptrofs.eq_dec ofs ofs0); try congruence.    | ✓  VALID
[rango ] destruct (Ptrofs.eq_dec ofs0 ofs); try congruence.    | ✓  VALID
[rango ] destruct (Ptrofs.eq_dec ofs0 ofs); auto using (zdec_… | ✓  VALID
[rango ] congruence.                                           | ✓  VALID
[rango ] rewrite e0.                                           | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] +                                                     | ✓  VALID
[rango ] destruct (Ptrofs.eq_dec ofs0 ofs); congruence.        | ✓  VALID
[rango ] -                                                     | ❌ INVALID(거부, 상태유지)
```

---
### `Rabs_le_inv` · plain: dead
**GOLD 전문:**
```coq
Proof.
intros x y Hxy.
split.
apply Rle_trans with (- Rabs x)%R.
now apply Ropp_le_contravar.
apply Ropp_le_cancel.
rewrite Ropp_involutive, <- Rabs_Ropp.
apply RRle_abs.
apply Rle_trans with (2 := Hxy).
apply RRle_abs.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] destruct H as (H1,H2).                                | ❌ INVALID(거부, 상태유지)
[rango ] Proof.                                                | ✓  VALID  ↻재시도
[rango ] intros x y [H|H].                                     | ✓  VALID
[rango ] split.                                                | ✓  VALID
[rango ] -                                                     | ✓  VALID
[rango ] now apply Ropp_le_contravar.                          | ❌ INVALID(거부, 상태유지)
[rango ] apply Ropp_le_contravar.                              | ❌ INVALID(거부, 상태유지)  ↻재시도
```

---
### `m_eq_0` · plain: dead
**GOLD 전문:**
```coq
Proof with auto with typeclass_instances.
intros Y.
specialize (Zeven_ex (radix_val beta)); rewrite Even_beta.
intros (b, Hb); rewrite Zplus_0_r in Hb.
exists (Fmult (Float beta b (-1)) u)%R.
split.
rewrite F2R_mult; unfold m; rewrite <- Y, Rplus_0_l.
rewrite Rmult_comm.
unfold Rdiv; apply f_equal.
unfold F2R; simpl; unfold Z.pow_pos; simpl.
rewrite Zmult_1_r, Hb, mult_IZR.
simpl; field.
apply Rgt_not_eq, Rmult_lt_reg_l with (1 := Rlt_0_2).
rewrite Rmult_0_r, <- (mult_IZR 2), <-Hb.
apply radix_pos.
apply trans_eq with (-1+Fexp u)%Z.
unfold Fmult.
destruct u; reflexivity.
rewrite Zplus_comm, Cu; unfold Zminus; now apply f_equal2.
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof with auto.                                      | ✓  VALID
[rango ] intros Heq.                                           | ✓  VALID
[rango ] assert (m = m%R) by (reflexivity; field); clear xPos. | ✓  VALID
[rango ] eapply canonical_generic_format; try eassumption.     | ❌ INVALID(거부, 상태유지)
[rango ] specialize (u'_eq (Rlt_0_2 := Rlt_0_2) m); intros f … | ❌ INVALID(거부, 상태유지)  ↻재시도
```

---
### `shlimm_sound` · plain: dead
**GOLD 전문:**
```coq
Proof.
unfold shlimm; intros.
unfold Val.shl.
destruct (Int.ltu n Int.iwordsize).
destruct x; simpl in *.
-
auto.
-
InvAgree.
apply iagree_shl; auto.
-
InvAgree.
apply Val.lessdef_same.
f_equal.
apply iagree_mone.
apply iagree_shl; auto.
-
destruct v; auto with na.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] intros.                                               | ✓  VALID
[opener] unfold shlimm; rewrite Int.limm_shl.                  | ❌ INVALID(거부, 상태유지)
[rango ] destruct x; simpl in *.                               | ✓  VALID  ↻재시도
[rango ] -                                                     | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] -                                                     | ✓  VALID
[rango ] InvAgree.                                             | ✓  VALID
[rango ] unfold Val.shl; fold Val.shl.                         | ✓  VALID
[rango ] destruct (zlt n Int.iwordsize) eqn:LTSW; auto.        | ❌ INVALID(거부, 상태유지)
[rango ] assert (T :=  Int.ltu n Int.iwordsize).               | ✓  VALID  ↻재시도
[rango ] destruct (Int.ltu n Int.iwordsize); auto.             | ✓  VALID
[rango ] apply iagree_shl; auto with ints.                     | ✓  VALID
[rango ] -                                                     | ✓  VALID
[rango ] unfold Val.shl; fold Val.shl.                         | ✓  VALID
[rango ] destruct v; destruct w; [unfold Val.lessdef | unfold… | ❌ INVALID(거부, 상태유지)
[rango ] destruct v; destruct w; simpl in *.                   | ✓  VALID  ↻재시도
[rango ] +                                                     | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] +                                                     | ✓  VALID
[rango ] intro.                                                | ❌ INVALID(거부, 상태유지)
[rango ] unfold Int.shl.                                       | ✓  VALID  ↻재시도
[rango ] red.                                                  | ❌ INVALID(거부, 상태유지)
[rango ] fold Int.shl.                                         | ✓  VALID  ↻재시도
[rango ] case (Int.ltu n Int.iwordsize); auto.                 | ✓  VALID
... (총 26스텝)
```

---
### `store_argument_load_result` · plain: dead
**GOLD 전문:**
```coq
Proof.
unfold store_argument; intros; destruct chunk;
  auto using Val.load_result_lessdef; InvAgree; simpl.
-
apply sign_ext_sound with (v := Vint i) (w := Vint i0) (x := All) (n := 8).
auto.
compute; auto.
-
apply zero_ext_sound with (v := Vint i) (w := Vint i0) (x := All) (n := 8).
auto.
lia.
-
apply sign_ext_sound with (v := Vint i) (w := Vint i0) (x := All) (n := 16).
auto.
compute; auto.
-
apply zero_ext_sound with (v := Vint i) (w := Vint i0) (x := All) (n := 16).
auto.
lia.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] intros.                                               | ✓  VALID
[opener] unfold store_argument.                                | ✓  VALID
[opener] destruct v; destruct w; auto.                         | ✓  VALID
[rango ] -                                                     | ✓  VALID
[rango ] simpl.                                                | ✓  VALID
[rango ] simpl in *.                                           | ✓  VALID
[rango ] unfold Val.lessdef; eauto.                            | ❌ INVALID(거부, 상태유지)
[rango ] destruct chunk; auto; injection.                      | ✓  VALID  ↻재시도
[rango ] -                                                     | ✓  VALID
[rango ] simpl.                                                | ✓  VALID
[rango ] simpl in *.                                           | ✓  VALID
[rango ] specialize (lessdef_agr Vundef Vlong Int64.eqb).      | ❌ INVALID(거부, 상태유지)
[rango ] destruct chunk; auto.                                 | ✓  VALID  ↻재시도
[rango ] Qed.                                                  | ❌ INVALID(거부, 상태유지)
[rango ] -                                                     | ✓  VALID  ↻재시도
[rango ] simpl in *.                                           | ✓  VALID
[rango ] destruct (proj_value (Vfloat f)) eqn:PV; auto.        | ❌ INVALID(거부, 상태유지)
[rango ] destruct chunk; auto; injection.                      | ✓  VALID  ↻재시도
[rango ] -                                                     | ✓  VALID
[rango ] simpl.                                                | ✓  VALID
[rango ] simpl in *.                                           | ✓  VALID
[rango ] destruct chunk; auto.                                 | ✓  VALID
[rango ] Qed.                                                  | ❌ INVALID(거부, 상태유지)
[rango ] -                                                     | ✓  VALID  ↻재시도
... (총 29스텝)
```

---
### `external_call_spec` · plain: dead
**GOLD 전문:**
```coq
Proof.
intros.
unfold external_call, ef_sig; destruct ef.
apply external_functions_properties.
apply builtin_or_external_sem_ok.
apply builtin_or_external_sem_ok.
apply volatile_load_ok.
apply volatile_store_ok.
apply extcall_malloc_ok.
apply extcall_free_ok.
apply extcall_memcpy_ok.
apply extcall_annot_ok.
apply extcall_annot_val_ok.
apply inline_assembly_properties.
apply extcall_debug_ok.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] intros.                                               | ✓  VALID
[opener] unfold external_call.                                 | ✓  VALID
[opener] destruct (proj_bytesize (ef_sig ef)).                 | ❌ INVALID(거부, 상태유지)
[rango ] destruct ef; eauto using extcall_external_sem.        | ❌ INVALID(거부, 상태유지)  ↻재시도
[rango ] destruct ef; [apply builtin_or_external_sem_ok|].     | ❌ INVALID(거부, 상태유지)  ↻재시도
```
