# ❌ opener-tac(w compound) 실패 예시

작성 2026-08-01. opener-tac(w compound)가 못 닫은(dead) 정리들.
롤아웃: `data/grpo_rollouts/opener_tac_pipe.jsonl`. executor=subgoal 모델.

## 롤아웃 성공/실패율 (train 100, greedy 단일궤도)
| | 개수 | 비율 |
|---|---|---|
| **성공(≥1)** | 31/97 | **32%** |
| &nbsp;└ all-solved | 4 | 4% |
| &nbsp;└ mixed | 27 | 28% |
| **실패(dead)** | 66/97 | **68%** |
| attempt당 | | 16.8% |

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
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros x Hx.                                          | ✓  VALID
[opener] destruct (Rle_or_lt 0 x) as [[Hx|Hx]|Hx].             | ❌ INVALID(거부, 상태유지)
[rango ] unfold succ; apply Rlt_antisym.                       | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros n instr s.                                     | ✓  VALID
[rango ] set (l:=make_predecessors ! s).                       | ✓  VALID
[rango ] intros.                                               | ✓  VALID
[rango ] exists (successors instr).                            | ✓  VALID
[rango ] split.                                                | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] apply H0.                                             | ❌ INVALID(거부, 상태유지)
[rango ] destruct l as [|l].                                   | ✓  VALID  ↻재시도
[rango ] reflexivity.                                          | ❌ INVALID(거부, 상태유지)
[rango ] exists s; trivial.                                    | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[opener] destruct ls1 as [[] | l1 ls1]; destruct ls2 as [[] |… | ❌ INVALID(거부, 상태유지)
[rango ] Proof.                                                | ✓  VALID  ↻재시도
[opener] destruct ls1 as [[] | l1 ls1]; destruct ls2 as [[] |… | ❌ INVALID(거부, 상태유지)
[rango ] induction ls1; simpl; intros; auto; constructor.      | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[opener] induction 1; intros.                                  | ✓  VALID
[rango ] -                                                     | ✓  VALID
[rango ] exists []; auto.                                      | ❌ INVALID(거부, 상태유지)
[rango ] eexists; split; auto.                                 | ✓  VALID  ↻재시도
[rango ] constructor.                                          | ✓  VALID
[opener] inv H5.                                               | ❌ INVALID(거부, 상태유지)
[rango ] -                                                     | ✓  VALID  ↻재시도
[opener] inv H5.                                               | ❌ INVALID(거부, 상태유지)
[rango ] exploit IHlist_forall2; auto; econstructor; eauto wi… | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[opener] destruct shift_op_type as [[] | $].                   | ❌ INVALID(거부, 상태유지)
[rango ] Proof.                                                | ✓  VALID  ↻재시도
[opener] destruct shift_op_type as [[] | $].                   | ❌ INVALID(거부, 상태유지)
[rango ] induction m using well_founded_induction; intros.     | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[opener] destruct m1; simpl; intros; split; intros.            | ✓  VALID
[rango ] simpl in *.                                           | ✓  VALID
[rango ] split.                                                | ✓  VALID
[rango ] apply dests_disjoint_sym.                             | ✓  VALID
[rango ] intros h.                                             | ✓  VALID
[rango ] simpl; intros.                                        | ✓  VALID
[rango ] contradiction.                                        | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] apply dests_disjoint_cons_left.                       | ❌ INVALID(거부, 상태유지)
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
**opener-tac(w compound):**
```text
[opener] destruct ptlz=>//.                                    | ✓  VALID
[rango ] match goal with [ |- (?l <> _ -> ?r)%l] => generaliz… | ❌ INVALID(거부, 상태유지)
[rango ] destruct ptl.                                         | ✓  VALID  ↻재시도
[rango ] -                                                     | ✓  VALID
[rango ] reflexivity.                                          | ❌ INVALID(거부, 상태유지)
[rango ] simpl.                                                | ✓  VALID  ↻재시도
[rango ] rewrite -ptd_cost_build_from_pt /=.                   | ❌ INVALID(거부, 상태유지)
[rango ] rewrite -ptd_cost_build_from_pt -=.                   | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] induction T using traceinf_ind; simpl; constructor; … | ❌ INVALID(거부, 상태유지)
[rango ] unfold traceinf.                                      | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[opener] induction vars; intros until sz'.                     | ✓  VALID
[opener] inv H.                                                | ❌ INVALID(거부, 상태유지)
[rango ] intros.                                               | ✓  VALID  ↻재시도
[opener] inv H.                                                | ✓  VALID
[rango ] lia.                                                  | ✓  VALID
[opener] inv H.                                                | ❌ INVALID(거부, 상태유지)
[rango ] simpl.                                                | ✓  VALID  ↻재시도
[opener] inv H.                                                | ❌ INVALID(거부, 상태유지)
[rango ] remember (fun a => a) as tp.                          | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros.                                               | ✓  VALID
[opener] destruct H0.                                          | ✓  VALID
[rango ] exists (mk_SType e).                                  | ❌ INVALID(거부, 상태유지)
[rango ] rename e into TABIG; rename H0 into TCODE.            | ✓  VALID  ↻재시도
[opener] destruct TABIG; simpl in *; try discriminate.         | ✓  VALID
[rango ] exists (fun pc ty => match S.te_typ te ! pc with    … | ❌ INVALID(거부, 상태유지)
[rango ] destruct (solution_deterministic _ (fun pc => fn_par… | ❌ INVALID(거부, 상태유지)  ↻재시도
```

---
### `eqb_false` · plain: dead
**GOLD 전문:**
```coq
Proof.
now intros [|] [|].
Qed.
```
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros x y H.                                         | ✓  VALID
[opener] destruct H.                                           | ✓  VALID
[opener] destruct x; destruct y; simpl.                        | ✓  VALID
[rango ] now destruct (H _).                                   | ❌ INVALID(거부, 상태유지)
[rango ] discriminate.                                         | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros a b.                                           | ✓  VALID
[rango ] destruct (Zdec_eq a b) as [?|?].                      | ❌ INVALID(거부, 상태유지)
[rango ] destruct (Z.rem_spec a b) as [H|[H|H]].               | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros e n Hk.                                        | ✓  VALID
[rango ] induction (Z.abs_nat e) ; intros k.                   | ✓  VALID
[rango ] destruct Hk.                                          | ✓  VALID
[rango ] intros Hk.                                            | ✓  VALID
[rango ] change (Zdigit 0 k) with 0%Z.                         | ✓  VALID
[rango ] apply Z0.case_eq.                                     | ❌ INVALID(거부, 상태유지)
[rango ] unfold Zdigit.                                        | ✓  VALID  ↻재시도
[rango ] rewrite Zrem0, Zmult_0_r.                             | ❌ INVALID(거부, 상태유지)
[rango ] apply Zdiv_rem_zero_pow_e ;[|apply radix_nonzero].    | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros.                                               | ✓  VALID
[opener] destruct (transf_function f) as [tf|] eqn:TF.         | ✓  VALID
[rango ] -                                                     | ✓  VALID
[rango ] apply is_tail_trans with (Mcall sg c).                | ❌ INVALID(거부, 상태유지)
[rango ] exists (Mach.fn_code tf).                             | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[opener] induction 1; inv plub_eq.                             | ❌ INVALID(거부, 상태유지)
[rango ] Proof.                                                | ✓  VALID  ↻재시도
[opener] induction 1; inv plub_eq.                             | ❌ INVALID(거부, 상태유지)
[rango ] intros; unfold plub, plt; rewrite !(Pos.compare_eq p… | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros F F0 x y f g (Hx1, _) (Hy1, _) Hxy.            | ✓  VALID
[rango ] destruct (Rnd_N_pt_le_0 F H0 x f Hx1 (x, (Hx1, Hxy))… | ❌ INVALID(거부, 상태유지)
[rango ] intros Hf.                                            | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros x y H.                                         | ✓  VALID
[rango ] assert (H1 : Rabs x <= y)%R).                         | ❌ INVALID(거부, 상태유지)
[rango ] split.                                                | ✓  VALID  ↻재시도
[rango ] pose proof (Rle_trans _ _ _ H).                       | ❌ INVALID(거부, 상태유지)
[rango ] apply Rplus_le_compat_l with (Ropp y).                | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[rango ] Proof with auto.                                      | ✓  VALID
[rango ] intros Heq.                                           | ✓  VALID
[rango ] assert (m = m%R) by (reflexivity; field); clear xPos. | ✓  VALID
[rango ] eapply canonical_generic_format; try eassumption.     | ❌ INVALID(거부, 상태유지)
[rango ] specialize (u'_eq (Rlt_0_2 := Rlt_0_2) m); intros f … | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[opener] destruct (external_function_sig ef) as [sg|] eqn:SIG. | ❌ INVALID(거부, 상태유지)
[rango ] Proof.                                                | ✓  VALID  ↻재시도
[opener] destruct (external_function_sig ef) as [sg|] eqn:SIG. | ❌ INVALID(거부, 상태유지)
[rango ] induction ef using well_typed_extcall_ind; unfold de… | ❌ INVALID(거부, 상태유지)  ↻재시도
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
**opener-tac(w compound):**
```text
[opener] destruct chunk; simpl; eauto using Val.lessdef_trans. | ✓  VALID
[rango ] -                                                     | ✓  VALID
[rango ] intros.                                               | ✓  VALID
[opener] destruct H as [[] | ]; discriminate || eauto.         | ❌ INVALID(거부, 상태유지)
[rango ] destruct v; destruct w; simpl in *; auto with arith.  | ✓  VALID  ↻재시도
[rango ] contradiction.                                        | ✓  VALID
[rango ] auto with arith.                                      | ✓  VALID
[rango ] apply Val.lessdef_same.                               | ✓  VALID
[rango ] erewrite <- Int.sign_ext_sgn_idem; auto.              | ❌ INVALID(거부, 상태유지)
[rango ] apply sign_ext_same_8; auto.                          | ❌ INVALID(거부, 상태유지)  ↻재시도
```
