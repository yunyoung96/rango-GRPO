# recall ≠ use — premise에 정답 lemma가 있는데도 못 쓰는 예시 (전체 궤적)

작성 2026-08-01. "rango가 premise 50개(recall 88.5%)를 받고도 왜 못 쓰나(=capacity)"의 구체 근거.
각 예시: **GOLD 전문** / gold이 쓴 lemma가 **입력 premise에 실제로 있었음(★)** / 모델의 **전체 롤아웃 궤적**(Proof부터, opener/rango 구분).
전부 dead(실패) 정리이고, gold의 apply/rewrite lemma가 입력 premise 50개 안에 있었음에도 모델이 못 씀.

## 기호
- `✓`VALID `❌`INVALID(거부→재시도) `✅`COMPLETE / `[OPENER]`opener가 연 수 `[rango ]`executor / `(r1)`재시도

---
## 1. `succ_pred`
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
**gold lemma 중 입력 premise(50)에 있던 것: `['pred_0', 'succ_opp']`**
```
★ Theorem succ_opp : forall x, succ (-x) = (- pred x)%R.
★ Theorem pred_0 : pred 0 = Ropp (ulp 0).
```
**모델 궤적 (opener발동, 15스텝):**
```text
 0 [rango ] ✓ Proof.
 1 [rango ] ✓ intros x Fx.
 2 [OPENER] ✓ destruct (Rle_or_lt 0 x).
 3 [rango ] ✓ apply Rle_antisym.
 4 [rango ] ❌ rewrite valid_exp; trivial.
 5 [rango ] ✓ - (r1)
 6 [rango ] ❌ rewrite Rle_bool_false in H.
 7 [rango ] ✓ apply Rnot_lt_le. (r1)
 8 [rango ] ✓ intros H0.
 9 [rango ] ✓ apply succ_le_lt with (1 := Fx) in H0.
10 [rango ] ✓ revert H0.
11 [rango ] ✓ apply Rlt_not_le.
12 [rango ] ✓ rewrite <- Rplus_0_r.
13 [rango ] ❌ apply Rlt_le_trans with (1 := H).
14 [rango ] ❌ apply Rplus_lt_le_compat. (r1)
```

---
## 2. `m_eq_0`
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
**gold lemma 중 입력 premise(50)에 있던 것: `['F2R_mult']`**
```
★ Theorem F2R_mult : forall f1 f2 : float beta, F2R (Fmult f1 f2) = (F2R f1 * F2R f2
```
**모델 궤적 (opener없음, 9스텝):**
```text
 0 [rango ] ✓ Proof with auto with typeclass_instances.
 1 [rango ] ✓ intros Y.
 2 [rango ] ✓ symmetry in Y.
 3 [rango ] ❌ destruct (m_eq xPos) as (f,'Hf).
 4 [rango ] ✓ destruct u'_eq as (u', (Hu'1,Hu'2)); trivial. (r1)
 5 [rango ] ❌ rewrite Y; constructor.
 6 [rango ] ✓ rewrite Y; clear Y. (r1)
 7 [rango ] ❌ rewrite <- Rlt_irrefl; trivial with real.
 8 [rango ] ❌ reflexivity. (r1)
```

---
## 3. `store_argument_load_result`
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
**gold lemma 중 입력 premise(50)에 있던 것: `['sign_ext_sound', 'zero_ext_sound']`**
```
★ Lemma sign_ext_sound: forall v w x n, vagree v w (sign_ext n x) -> 0 < n -> vagree
★ Lemma zero_ext_sound: forall v w x n, vagree v w (zero_ext n x) -> 0 <= n -> vagre
```
**모델 궤적 (opener없음, 28스텝):**
```text
 0 [rango ] ✓ Proof.
 1 [rango ] ✓ intros.
 2 [rango ] ❌ assert ((Val.load_result chunk w) = Some (Val.bitwise w)).
 3 [rango ] ✓ unfold store_argument in H. (r1)
 4 [rango ] ❌ destruct (Val.decode_val chunk v).
 5 [rango ] ✓ destruct chunk; simpl in *. (r1)
 6 [rango ] ✓ -
 7 [rango ] ✓ destruct v; destruct w; auto with arith.
 8 [rango ] ✓ auto.
 9 [rango ] ✓ contradiction.
10 [rango ] ❌ Transparent vals.
11 [rango ] ✓ apply Val.lessdef_same. (r1)
12 [rango ] ❌ apply eqmod_eq.
13 [rango ] ✓ f_equal. (r1)
14 [rango ] ✓ 2: auto.
15 [rango ] ❌ all: extensionality.
16 [rango ] ✓ auto. (r1)
17 [rango ] ❌ auto using zlt_le, Z.le_iff.
18 [rango ] ✓ auto. (r1)
19 [rango ] ❌ apply Val.agree_sub; auto.
20 [rango ] ✓ auto with arith. (r1)
21 [rango ] ✓ simpl.
... (총 28스텝)
```

---
## 4. `Zscale_scale`
**GOLD 전문:**
```coq
Proof.
intros n k k' Hk.
unfold Zscale at 2.
rewrite Zle_bool_true with (1 := Hk).
now apply Zscale_mul_pow.
Qed.
```
**gold lemma 중 입력 premise(50)에 있던 것: `['Zle_bool_true']`**
```
★ Theorem Zle_bool_true : forall x y : Z, (x <= y)%Z -> Zle_bool x y = true.
```
**모델 궤적 (opener없음, 15스텝):**
```text
 0 [rango ] ✓ Proof.
 1 [rango ] ✓ intros n k k' Hk.
 2 [rango ] ✓ unfold Zscale.
 3 [rango ] ❌ case Zle_bool, Zle_bool_spec ; intros Hk' Hk''.
 4 [rango ] ✓ case Zle_bool_spec ; intros Hk''. (r1)
 5 [rango ] ✓ case Zle_bool.
 6 [rango ] ✓ replace 0%Z with (0 + 0)%Z by ring.
 7 [rango ] ❌ apply Zplus_le_0_compat.
 8 [rango ] ✓ rewrite Zplus_0_l. (r1)
 9 [rango ] ✓ replace (k + k' + 0)%Z with (k + k')%Z by ring.
10 [rango ] ✓ case Zle_bool_spec ; intros Hk'''.
11 [rango ] ✓ rewrite Zpower_plus; try lia.
12 [rango ] ✓ rewrite <- Zmult_assoc.
13 [rango ] ❌ apply refl_equal.
14 [rango ] ❌ rewrite <- Zmult_assoc, Z_quot_mult. (r1)
```

---
## 5. `transl_expr_Eop_correct`
**GOLD 전문:**
```coq
Proof.
intros; red; intros.
inv TE.
(* normal case *)
  exploit H0; eauto.
intros [rs1 [tm1 [EX1 [ME1 [RR1 [RO1 EXT1]]]]]].
edestruct eval_operation_lessdef as [v' []]; eauto.
exists (rs1#rd <- v'); exists tm1.
(* Exec *)
  split.
eapply star_right.
eexact EX1.
eapply exec_Iop; eauto.
rewrite (@eval_operation_preserved CminorSel.fundef _ _ _ ge tge).
eauto.
exact symbols_preserved.
traceEq.
(* Match-env *)
  split.
eauto with rtlg.
(* Result reg *)
  split.
rewrite Regmap.gss.
auto.
(* Other regs *)
  split.
intros.
rewrite Regmap.gso.
auto.
intuition congruence.
(* Mem *)
  auto.
Qed.
```
**gold lemma 중 입력 premise(50)에 있던 것: `['exec_Iop']`**
```
★ Lemma exec_Iop': forall s f sp pc rs m op args res pc' rs' v, (fn_code f)!pc = Som
```
**모델 궤적 (opener발동, 22스텝):**
```text
 0 [OPENER] ❌ destruct op; simpl; intros until v; Inv EO.
 1 [rango ] ✓ Proof. (r1)
 2 [OPENER] ❌ destruct op; simpl; intros until v; Inv EO.
 3 [rango ] ✓ intros. (r1)
 4 [OPENER] ✓ inv H1.
 5 [OPENER] ✓ inv H3.
 6 [OPENER] ✓ inv H.
 7 [rango ] ✓ inv H2.
 8 [rango ] ✓ -
 9 [rango ] ❌ inv H0.
10 [rango ] ✓ unfold transl_exprlist_prop in *. (r1)
11 [rango ] ✓ red; intros.
12 [OPENER] ✓ inv TE.
13 [rango ] ✓ exploit tr_move_correct; eauto.
14 [rango ] ❌ apply transl_expr_Evar_correct; auto.
15 [rango ] ✓ constructor. (r1)
16 [rango ] ✓ intros [rs' [A [B C]]].
17 [rango ] ✓ exploit transl_expr_Evar_correct.
18 [rango ] ❌ exists rs'; eauto.
19 [rango ] ✓ eauto. (r1)
20 [rango ] ❌ exists rs.
21 [rango ] ❌ intros id v'. (r1)
```

---
## 6. `compat_left2_sound`
**GOLD 전문:**
```coq
Proof.
unfold compat_left2; intros.
rewrite EqSet.for_all_between_iff in H.
apply select_reg_charact in H1.
destruct H1.
exploit H; eauto.
intros.
destruct (ekind q); try discriminate.
InvBooleans.
auto.
InvBooleans.
auto.
intros.
subst x2.
auto.
exact (select_reg_l_monotone r).
exact (select_reg_h_monotone r).
Qed.
```
**gold lemma 중 입력 premise(50)에 있던 것: `['select_reg_charact']`**
```
★ Remark select_reg_charact: forall r q, select_reg_l r q = true /\ select_reg_h r q
```
**모델 궤적 (opener없음, 23스텝):**
```text
 0 [rango ] ✓ Proof.
 1 [rango ] ✓ unfold compat_left2; intros r l1 l2 e q.
 2 [rango ] ✓ rewrite EqSet.for_all_between_iff.
 3 [rango ] ✓ intros H1 H2 H3.
 4 [rango ] ✓ exploit H1; try eauto; try contradiction.
 5 [rango ] ✓ apply select_reg_charact.
 6 [rango ] ✓ auto.
 7 [rango ] ❌ setoid_rewrite H3; reflexivity.
 8 [rango ] ✓ unfold select_reg_h. (r1)
 9 [rango ] ✓ apply Pos.leb_le.
10 [rango ] ✓ apply Pos.leb_le.
11 [rango ] ✓ rewrite H3; apply Pos.leb_refl.
12 [rango ] ❌ intros; destruct (ekind q); try discriminate; (eauto || (rig
13 [rango ] ✓ assert (ekind q = Full). (r1)
14 [rango ] ✓ exploit H1; eauto.
15 [rango ] ✓ assert (ekind q = Full).
16 [rango ] ✓ exploit H1; eauto.
17 [rango ] ✓ assert (ekind q = Full).
18 [rango ] ✓ exploit H1; eauto.
19 [rango ] ✓ rewrite <- H3.
20 [rango ] ✓ apply Pos.leb_refl.
21 [rango ] ❌ apply PeanoNat.Nat.eqb_eq in H2.
... (총 23스텝)
```

---
## 7. `agree_set_other`
**GOLD 전문:**
```coq
Proof.
intros.
apply agree_exten with rs.
auto.
intros.
apply Pregmap.gso.
congruence.
Qed.
```
**gold lemma 중 입력 premise(50)에 있던 것: `['agree_exten']`**
```
★ Lemma agree_exten: forall ms sp rs rs', agree ms sp rs -> (forall r, data_preg r =
```
**모델 궤적 (opener없음, 21스텝):**
```text
 0 [rango ] ✓ Proof.
 1 [rango ] ✓ intros.
 2 [rango ] ❌ rewrite <- Pregmap.gsso; auto.
 3 [rango ] ✓ destruct H. (r1)
 4 [rango ] ✓ split; auto.
 5 [rango ] ✓ unfold Regmap.set.
 6 [rango ] ❌ congruence.
 7 [rango ] ✓ simpl. (r1)
 8 [rango ] ✓ unfold Regmap.set in agree_mregs0.
 9 [rango ] ❌ rewrite RegEq.eqb_neq in agree_mregs0.
10 [rango ] ✓ auto. (r1)
11 [rango ] ✓ unfold Regmap.set.
12 [rango ] ✓ simpl.
13 [rango ] ❌ destruct (Val.eq_dec r Vundef).
14 [rango ] ✓ unfold Regmap.set in agree_mregs0. (r1)
15 [rango ] ✓ auto.
16 [rango ] ❌ congruence.
17 [rango ] ✓ rewrite <- agree_sp0. (r1)
18 [rango ] ✓ auto.
19 [rango ] ❌ elim type_uninst; inversion H0; auto.
20 [rango ] ❌ rewrite <- agree_sp0. (r1)
```

---
## 8. `pred_le_inv`
**GOLD 전문:**
```coq
Proof.
intros x y Fx Fy Hxy.
rewrite <- (succ_pred x), <- (succ_pred y); try assumption.
apply succ_le; trivial; now apply generic_format_pred.
Qed.
```
**gold lemma 중 입력 premise(50)에 있던 것: `['succ_le']`**
```
★ Theorem succ_le_lt: forall x y, F x -> F y -> (x < y)%R -> (succ x <= y)%R.
★ Theorem succ_le : forall x y, F x -> F y -> (x <= y)%R -> (succ x <= succ y)%R.
★ Lemma succ_le_lt_aux: forall x y, F x -> F y -> (0 <= x)%R -> (x < y)%R -> (succ x
```
**모델 궤적 (opener없음, 9스텝):**
```text
 0 [rango ] ✓ Proof.
 1 [rango ] ✓ intros x y Hx Hy H.
 2 [rango ] ✓ apply Rle_trans with (pred y); trivial.
 3 [rango ] ❌ rewrite ulp_pred, pred_le_id, (Rplus_assoc 0 x); trivial.
 4 [rango ] ✓ apply Rle_trans with (pred x); trivial. (r1)
 5 [rango ] ✓ apply Rle_trans with (x); trivial.
 6 [rango ] ✓ apply Rle_refl.
 7 [rango ] ❌ rewrite Rulpred with (x := x); trivial.
 8 [rango ] ❌ now apply Rle_pred. (r1)
```

---
## 9. `tr_function_linkorder`
**GOLD 전문:**
```coq
Proof.
intros.
inv H0.
econstructor; eauto.
eapply fenv_compat_linkorder; eauto.
Qed.
```
**gold lemma 중 입력 premise(50)에 있던 것: `['fenv_compat_linkorder']`**
```
★ Lemma fenv_compat_linkorder: forall cunit prog fenv, linkorder cunit prog -> fenv_
```
**모델 궤적 (opener없음, 14스텝):**
```text
 0 [rango ] ✓ Proof.
 1 [rango ] ❌ red; intros; red.
 2 [rango ] ✓ induction 1. (r1)
 3 [rango ] ✓ destruct H0.
 4 [rango ] ✓ intros.
 5 [rango ] ✓ inversion H2 as [f0 f1 f2 f3 fd1 fd2 fd3 fd4 fd E].
 6 [rango ] ❌ apply tr_function_sig_compat in E.
 7 [rango ] ✓ subst f0 f2 f3. (r1)
 8 [rango ] ✓ simpl in *.
 9 [rango ] ❌ inversion H3 as [p _].
10 [rango ] ✓ assert (linkorder cunit prog). (r1)
11 [rango ] ✓ {
12 [rango ] ❌ apply linkorder_weaken; red; intros; discriminate.
13 [rango ] ❌ unfold linkorder; red; intros. (r1)
```

---
## 10. `is_power2_correct`
**GOLD 전문:**
```coq
Proof.
intros.
apply is_power2_inv in H.
destruct H as [P Q].
apply Z_is_power2_sound in P.
tauto.
Qed.
```
**gold lemma 중 입력 premise(50)에 있던 것: `['is_power2_inv', 'Z_is_power2_sound']`**
```
★ Remark is_power2_inv: forall n logn, is_power2 n = Some logn -> Z_is_power2 (unsig
★ Lemma Z_is_power2_sound: forall x i, Z_is_power2 x = Some i -> x = two_p i /\ i = 
```
**모델 궤적 (opener없음, 15스텝):**
```text
 0 [rango ] ✓ Proof.
 1 [rango ] ✓ intros.
 2 [rango ] ❌ extensa x.
 3 [rango ] ✓ specialize (is_power2_inv n logn); auto. (r1)
 4 [rango ] ✓ intro P.
 5 [rango ] ❌ assert (unsigned n < zwordsize) by auto.
 6 [rango ] ✓ pose proof (P H). (r1)
 7 [rango ] ❌ apply H0 in H0.
 8 [rango ] ✓ destruct H0. (r1)
 9 [rango ] ✓ unfold two_p.
10 [rango ] ✓ destruct (unsigned logn); auto.
11 [rango ] ✓ -
12 [rango ] ✓ exfalso.
13 [rango ] ❌ assert (0 = Z_is_power2 (unsigned n) \/ 0 > Z_is_power2 (uns
14 [rango ] ❌ apply is_power2_nonneg in H1. (r1)
```

---
## 11. `ptd_cost_build_from_ptl`
**GOLD 전문:**
```coq
Proof.
destruct ptlz=>//.
apply eq_add_S.
rewrite -ptd_cost_build_from_pt /=.
ring.
Qed.
```
**gold lemma 중 입력 premise(50)에 있던 것: `['ptd_cost_build_from_pt']`**
```
★ Lemma ptd_cost_build_from_pt {symb word} (pt : parse_tree symb word) (ptz : pt_zip
```
**모델 궤적 (opener발동, 13스텝):**
```text
 0 [OPENER] ✓ destruct ptlz=>//.
 1 [rango ] ✓ destruct p.
 2 [rango ] ✓ -
 3 [rango ] ✓ simpl.
 4 [rango ] ✓ reflexivity.
 5 [rango ] ✓ -
 6 [rango ] ❌ pose (build_pt_dot_from_ptl ptl ptlz).
 7 [rango ] ✓ unfold pt_size. (r1)
 8 [rango ] ✓ unfold ptd_cost.
 9 [rango ] ❌ destruct p.
10 [rango ] ✓ unfold ptl_size. (r1)
11 [rango ] ❌ unfold ptl_cost.
12 [rango ] ❌ destruct (build_pt_dot_from_ptl ptl (Non_terminal_pt prod p) (r1)
```

---
## 12. `eval_shll`
**GOLD 전문:**
```coq
Proof.
unfold shll; red; intros.
destruct (is_intconst b) as [n|] eqn:IC.
-
(* Immediate *)
  exploit is_intconst_sound; eauto.
intros EQ; subst y; clear H0.
eapply eval_shllimm; eauto.
-
(* General case *)
  econstructor; split.
eapply eval_helper_2; eauto.
DeclHelper.
reflexivity.
reflexivity.
auto.
Qed.
```
**gold lemma 중 입력 premise(50)에 있던 것: `['eval_shllimm']`**
```
★ Lemma eval_shllimm: forall n, unary_constructor_sound (fun e => shllimm e n) (fun 
```
**모델 궤적 (opener없음, 10스텝):**
```text
 0 [rango ] ✓ Proof.
 1 [rango ] ✓ red; intros.
 2 [rango ] ✓ exploit eval_shllimm.
 3 [rango ] ✓ eexact H.
 4 [rango ] ✓ intros [v1 [B1 C1]].
 5 [rango ] ✓ exploit eval_shllimm.
 6 [rango ] ✓ eexact B1.
 7 [rango ] ✓ intros [v2 [B2 C2]].
 8 [rango ] ❌ exploit eval_shlia.
 9 [rango ] ❌ exploit eval_shll. (r1)
```

---
## 종합
위 12개 모두: **gold이 쓰는 lemma가 입력 premise 50개에 실제로 있었는데(★)** 모델이 못 씀.
- **selection**: 50개 중 정답 1위 지목 실패 — 이름 비슷한 것·가설·automation을 대신 고름
- **composition**: 정답 lemma를 알아도 앞 스텝·순서·인자를 못 맞춰 state 불일치 → INVALID
- = retrieval(recall 88.5%) 문제가 아니라 **use(선택+조합) = 1.3B capacity**.
- opener가 잘 열어줘도(예: destruct 인자 일치) 닫기(어느 lemma로 어떻게)가 gold와 갈라져 실패.
- **비유**: 공식집(premise 50) 펴놓고 봐도 ①어느 공식인지 못 고르고 ②언제·어떻게 쓸지 모르면 못 푼다.

관련: [[WHY_COMPOUND_WONT_FIX_CLOSING]] · [[CLOSING_FAILURE_ANALYSIS]]