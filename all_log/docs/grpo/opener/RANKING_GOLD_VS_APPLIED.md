# rango 후보 랭킹 — 정답 tactic vs 실제 적용 (score 포함, 16정리)

작성 2026-08-01. `RECORD_TOPK=5`로 롤아웃 각 step의 rango top5+score(log-prob) 기록. executor=subgoal 모델.
측정: `topk_probe2.jsonl` (roll20 중 16정리). **정답 tactic이 rango 랭킹 몇 위? 실제 적용한 건?**

## 전체 통계 (932 step, rango_topk 기록된 것)
- gold tactic이 top5에 **있음 323 (35%)** / 없음 609 (65%)

| gold 최고순위 | step 수 | 비율 |
|---|---|---|
| 1위 | 212 | 23% |
| 2위 | 64 | 7% |
| 3위 | 21 | 2% |
| 4위 | 13 | 1% |
| 5위 | 13 | 1% |
| (top5 밖) | 609 | 65% |

**적용 결과 분류:**
- 모델이 **gold tactic을 실제 적용**: 227 (24%)
- gold가 top5에 있는데 **다른 걸 적용**: 97 (10%)
- gold가 top5에 없어 **다른 걸 적용**: 608 (65%)

→ **두 실패 분리**:
  - **selection 실패 65%**: 정답을 top5에도 못 뽑음
  - **composition/off-path 35%**: 뽑았어도(심지어 1위) 앞 스텝 어긋나 다른 걸 적용하거나 정답 적용해도 INVALID

## 기호: `score`=log-prob(0에 가까울수록 선호) / `★`적용 / `☆`gold도 쓰는 tactic

---
## `assign_variables_incr`
**GOLD:** Proof. / induction vars; intros until sz'. / simpl; intros. / inv H. / lia. / Opaque assign_variable. / destruct a as [id s]. / simpl. / intros. / destruct (assign_variable (cenv, sz) (id, s)) as [cenv1 sz1] eqn:?. / apply Z.le_trans with sz1. / eapply assign_variable_incr; eauto. / eauto.

**step별 rango top5:**
```text
[step0] 적용: Proof  →VALID
   1. score=  -0.00  Proof. ★적용 ☆gold
   2. score=  -0.01  Proof. ★적용 ☆gold
   3. score=  -0.00  Proof. ★적용 ☆gold
   4. score=  -0.00  Proof. ★적용 ☆gold
   5. score=  -0.01  Proof. ★적용 ☆gold
[step1] 적용: unfold assign_variables, assign_variable  →VALID
   1. score= -10.08  unfold assign_variables, assign_variab ★적용
   2. score=  -0.66  induction vars; simpl; intros.
   3. score=  -4.27  induction vars; simpl; intros; inv H.
   4. score= -17.41  intros. ☆gold
   5. score= -27.82  intros. ☆gold
[step2] 적용: intros  →VALID
   1. score= -16.15  intros. ★적용 ☆gold
   2. score=  -1.76  intros. ★적용 ☆gold
   3. score= -11.39  intros. ★적용 ☆gold
   4. score=  -1.62  induction vars; simpl; intros.
   5. score=  -1.61  induction vars; simpl; intros.
[step3] 적용: congruence  →INVALID
   1. score= -75.88  congruence. ★적용
   2. score= -60.12  inv H. ☆gold
   3. score= -67.23  apply fold_left_in_r in H.
   4. score=  -3.26  generalize (align_le sz (block_alignme
   5. score= -40.36  rewrite <- Z.add_diag_r in H.
[step4] 적용: inv H  →VALID
   1. score= -75.88  congruence.
   2. score= -60.12  inv H. ★적용 ☆gold
   3. score= -67.23  apply fold_left_in_r in H.
   4. score=  -3.26  generalize (align_le sz (block_alignme
   5. score= -40.36  rewrite <- Z.add_diag_r in H.
[step5] 적용: clear TRANSL  →VALID
   1. score= -85.39  clear TRANSL. ★적용
   2. score= -77.03  unfold fold_left in H1.
   3. score= -21.98  generalize (align_le sz (block_alignme
   4. score= -30.75  generalize (align_lt sz (block_alignme
   5. score=  -5.35  generalize (align_le sz (block_alignme
[step6] 적용: genv indirs  →INVALID
   1. score= -96.12  genv indirs. ★적용
   2. score= -95.66  apply equal_plus with 0.
   3. score= -39.10  pose proof align_le (cenv, sz) (sz' ||
   4. score= -36.98  unfold fold_left; induction vars; simp
   5. score= -12.92  generalize (align_le sz (block_alignme
[step7] 적용: induction vars; simpl in *; inv H1; auto  →VALID
   1. score= -96.12  genv indirs.
   2. score= -95.66  apply equal_plus with 0.
   3. score= -39.10  pose proof align_le (cenv, sz) (sz' ||
   4. score= -36.98  unfold fold_left; induction vars; simp
   5. score= -12.92  generalize (align_le sz (block_alignme
[step8] 적용: destruct a as (id, sz1); simpl in *  →VALID
   1. score= -10.45  destruct a as (id, sz1); simpl in *. ★적용
   2. score=  -9.61  elim a; simpl; auto with zarith.
   3. score=  -7.58  destruct a as (id, sz1).
   4. score= -10.42  inversion_clear H0.
   5. score=  -7.72  constructor.
```

---
## `ptd_cost_build_from_ptl`
**GOLD:** Proof. / destruct ptlz=>//. / apply eq_add_S. / rewrite -ptd_cost_build_from_pt /=. / ring.

**step별 rango top5:**
```text
[step0] 적용: Proof  →VALID
   1. score=  -0.00  Proof. ★적용 ☆gold
   2. score=  -0.00  Proof. ★적용 ☆gold
   3. score=  -0.00  Proof. ★적용 ☆gold
   4. score=  -0.00  Proof. ★적용 ☆gold
   5. score=  -0.00  Proof. ★적용 ☆gold
[step1] 적용: destruct ptlz=>/=  →VALID
   1. score= -16.37  destruct ptlz=>/=. ★적용
   2. score=  -3.80  destruct ptlz as [|???? pt]; [contradi
   3. score=  -0.55  destruct ptlz as [|???? pt]=>//=.
   4. score=  -0.66  destruct ptlz as [|???? pt]=>//=.
   5. score=  -0.45  destruct ptlz as [|???? pt]=>//=.
[step2] 적용: -  →VALID
   1. score=  -0.29  - ★적용
   2. score=  -5.37  - ★적용
   3. score=  -0.42  - ★적용
   4. score=  -1.81  reflexivity.
   5. score=  -1.40  reflexivity.
[step3] 적용: reflexivity  →VALID
   1. score=  -0.16  reflexivity. ★적용
   2. score=  -0.14  reflexivity. ★적용
   3. score=  -0.13  reflexivity. ★적용
   4. score=  -0.13  reflexivity. ★적용
   5. score=  -0.17  reflexivity. ★적용
[step4] 적용: -  →VALID
   1. score=  -0.02  - ★적용
   2. score=  -0.03  - ★적용
   3. score=  -0.03  - ★적용
   4. score=  -0.04  - ★적용
   5. score=  -0.02  - ★적용
[step5] 적용: apply ptd_cost_build_from_pt  →INVALID
   1. score=  -0.77  apply ptd_cost_build_from_pt. ★적용
   2. score=  -9.68  apply eq_add_S. ☆gold
   3. score=  -9.91  rewrite !ptd_cost_build_from_pt.
   4. score=  -0.83  apply ptd_cost_build_from_pt. ★적용
   5. score=  -4.45  apply ptd_cost_build_from_pt /=.
[step6] 적용: apply ptd_cost_build_from_pt; try rassum  →INVALID
   1. score=  -0.77  apply ptd_cost_build_from_pt.
   2. score=  -9.68  apply eq_add_S. ☆gold
   3. score=  -9.91  rewrite !ptd_cost_build_from_pt.
   4. score=  -0.83  apply ptd_cost_build_from_pt.
   5. score=  -4.45  apply ptd_cost_build_from_pt /=.
```

---
## `locmap_set_lessdef`
**GOLD:** Proof. / intros; red; intros l'. / unfold Locmap.set. / destruct (Loc.eq l l'). / - / destruct l; auto using Val.load_result_lessdef. / - / destruct (Loc.diff_dec l l'); auto.

**step별 rango top5:**
```text
[step0] 적용: Proof  →VALID
   1. score=  -0.09  Proof. ★적용 ☆gold
   2. score=  -0.09  Proof. ★적용 ☆gold
   3. score=  -0.06  Proof. ★적용 ☆gold
   4. score=  -0.09  Proof. ★적용 ☆gold
   5. score=  -0.09  Proof. ★적용 ☆gold
[step1] 적용: intros  →VALID
   1. score= -11.94  intros. ★적용
   2. score= -12.25  intros *.
   3. score=  -5.78  intros. ★적용
   4. score= -12.60  induction ls1; simpl; intuition auto w
   5. score= -24.60  intros. ★적용
[step2] 적용: unfold Locmap.set  →VALID
   1. score= -16.29  unfold Locmap.set. ★적용 ☆gold
   2. score= -41.32  intro.
   3. score= -10.94  unfold locmap_lessdef in *; simpl in *
   4. score= -16.35  destruct ls1; auto.
   5. score= -31.85  eapply locmap_lessdef_ext; congruence.
[step3] 적용: intro  →VALID
   1. score=  -7.98  intro. ★적용
   2. score= -12.89  intros i j Hi Hj.
   3. score= -21.33  intros.
   4. score=  -6.02  intro. ★적용
   5. score= -13.84  rewrite H0.
[step4] 적용: destruct l; destruct l0; auto  →VALID
   1. score= -49.70  destruct l; destruct l0; auto. ★적용
   2. score= -20.89  destruct Loc.eq_dec as [?|]; [contradi
   3. score=  -3.96  destruct (Loc.eq l l0); auto.
   4. score= -43.13  destruct (Loc.eq_dec l l0).
   5. score= -14.02  destruct (Loc.eq l l0); auto.
[step5] 적용: -  →VALID
   1. score= -34.67  - ★적용 ☆gold
   2. score= -14.69  - ★적용 ☆gold
   3. score=  -2.05  destruct (Loc.eq (R r) (R r0)); auto.
   4. score= -16.73  - ★적용 ☆gold
   5. score= -21.98  - ★적용 ☆gold
[step6] 적용: destruct (Loc.eq (R r) (R r0))  →VALID
   1. score= -44.98  destruct (Loc.eq (R r) (R r0)). ★적용
   2. score=  -8.75  destruct (Loc.eq (R r) (R r0)); destru
   3. score= -32.52  rewrite !dec_eq_true; auto.
   4. score= -45.72  rewrite dec_eq_true.
   5. score= -52.64  destruct (Val.eq_dec v1 v2); subst.
[step7] 적용: exact H0  →VALID
   1. score=  -2.75  exact H0. ★적용
   2. score=  -3.49  auto.
   3. score=  -0.66  auto.
   4. score=  -9.79  auto.
   5. score= -12.39  +
[step8] 적용: destruct (Loc.diff_dec (R r) (R r0)); au  →VALID
   1. score=  -2.13  destruct (Loc.diff_dec (R r) (R r0));  ★적용
   2. score= -44.89  contradiction.
   3. score=  -2.53  destruct (Loc.diff_dec (R r) (R r0));  ★적용
   4. score= -41.58  contradiction.
   5. score= -47.86  elim n; auto.
```

---
## `dests_disjoint_cons_right`
**GOLD:** Proof. / intros. / rewrite dests_disjoint_sym. / rewrite dests_disjoint_cons_left. / rewrite dests_disjoint_sym. / tauto.

**step별 rango top5:**
```text
[step0] 적용: Proof  →VALID
   1. score=  -0.00  Proof. ★적용 ☆gold
   2. score=  -0.00  Proof. ★적용 ☆gold
   3. score=  -0.00  Proof. ★적용 ☆gold
   4. score=  -0.00  Proof. ★적용 ☆gold
   5. score=  -0.00  Proof. ★적용 ☆gold
[step1] 적용: unfold dests_disjoint, list_disjoint  →VALID
   1. score=  -0.45  unfold dests_disjoint, list_disjoint. ★적용
   2. score= -36.00  intros. ☆gold
   3. score= -26.05  intros. ☆gold
   4. score=  -0.46  unfold dests_disjoint, list_disjoint. ★적용
   5. score=  -9.49  destruct m1; intros.
[step2] 적용: intros  →VALID
   1. score= -22.88  intros. ★적용 ☆gold
   2. score= -15.96  intros. ★적용 ☆gold
   3. score=  -0.17  simpl; intros; split; intros.
   4. score=  -0.43  simpl; intros; split; intros.
   5. score=  -0.33  simpl; intros; split; intros.
[step3] 적용: split; simpl; intro  →VALID
   1. score= -10.52  split; simpl; intro. ★적용
   2. score=  -1.02  split; intros.
   3. score=  -7.50  split; intro.
   4. score=  -0.93  split; intros.
   5. score=  -0.80  split; intros.
[step4] 적용: split  →VALID
   1. score=  -0.89  split. ★적용
   2. score=  -0.85  split. ★적용
   3. score=  -7.37  split. ★적용
   4. score=  -2.91  split; intros.
   5. score=  -4.39  firstorder.
[step5] 적용: firstorder  →VALID
   1. score=  -4.18  firstorder. ★적용
   2. score=  -0.14  auto.
   3. score=  -4.16  firstorder. ★적용
   4. score=  -0.13  auto.
   5. score=  -0.18  auto.
[step6] 적용: red; intro; subst  →VALID
   1. score=  -2.15  red; intro; subst. ★적용
   2. score=  -9.54  red; intro.
   3. score=  -3.37  red; intro.
   4. score= -12.36  intro.
   5. score= -28.53  apply H.
[step7] 적용: elim (H d d); auto  →VALID
   1. score=  -3.12  elim (H d d); auto. ★적용
   2. score=  -5.40  apply (H d); auto.
   3. score=  -2.55  apply H with d; auto.
   4. score=  -6.20  apply H0.
   5. score= -29.05  apply H with d.
[step8] 적용: intros  →VALID
   1. score=  -1.94  intros. ★적용 ☆gold
   2. score=  -0.74  intros. ★적용 ☆gold
   3. score=  -0.60  intros. ★적용 ☆gold
   4. score=  -0.41  intros. ★적용 ☆gold
   5. score=  -0.57  intros. ★적용 ☆gold
```

---
## `make_predecessors_correct_2`
**GOLD:** Proof. / intros. / exploit make_predecessors_correct_1; eauto. / unfold successors_list. / destruct (make_predecessors!s); simpl; intros. / exists l; auto. / contradiction.

**step별 rango top5:**
```text
[step0] 적용: Proof  →VALID
   1. score=  -0.00  Proof. ★적용 ☆gold
   2. score=  -0.01  Proof. ★적용 ☆gold
   3. score=  -0.01  Proof. ★적용 ☆gold
   4. score=  -0.00  Proof. ★적용 ☆gold
   5. score=  -0.01  Proof. ★적용 ☆gold
[step1] 적용: induction n  →VALID
   1. score=  -5.15  induction n. ★적용
   2. score=  -1.87  intros. ☆gold
   3. score=  -0.35  intros until s.
   4. score=  -4.19  unfold make_predecessors.
   5. score=  -0.47  intros until s.
[step2] 적용: -  →VALID
   1. score=  -0.24  - ★적용
   2. score=  -0.21  - ★적용
   3. score=  -0.31  - ★적용
   4. score=  -0.18  - ★적용
   5. score=  -0.27  - ★적용
[step3] 적용: intros until s  →VALID
   1. score= -17.52  intros until s. ★적용
   2. score= -28.05  intros a s P_H_instr.
   3. score=  -9.30  simpl.
   4. score=  -8.41  intros; eexists; split; eauto.
   5. score= -12.61  intros until s. ★적용
[step4] 적용: set (P := fun m p => m!n = Some instr ->  →INVALID
   1. score= -10.05  set (P := fun m p => m!n = Some instr  ★적용
   2. score=-101.98  rewrite L.n1_eq.
   3. score=-115.46  simpl.
   4. score= -10.65  set (P := fun m p => m!n = Some instr 
   5. score= -92.79  intros. ☆gold
[step5] 적용: intros  →VALID
   1. score= -10.05  set (P := fun m p => m!n = Some instr 
   2. score=-101.98  rewrite L.n1_eq.
   3. score=-115.46  simpl.
   4. score= -10.65  set (P := fun m p => m!n = Some instr 
   5. score= -92.79  intros. ★적용 ☆gold
[step6] 적용: rewrite PTree.gsspec in H  →INVALID
   1. score=  -4.38  rewrite PTree.gsspec in H. ★적용
   2. score=  -5.74  specialize (IHn instr s H H0).
   3. score= -13.54  destruct (PEQL (n~1) s).
   4. score= -42.79  eauto.
   5. score= -24.66  inv H.
[step7] 적용: eauto  →VALID
   1. score=  -4.38  rewrite PTree.gsspec in H.
   2. score=  -5.74  specialize (IHn instr s H H0).
   3. score= -13.54  destruct (PEQL (n~1) s).
   4. score= -42.79  eauto. ★적용
   5. score= -24.66  inv H.
[step8] 적용: destruct (IHn instr s) as [l [P Q]]; aut  →VALID
   1. score= -40.37  destruct (IHn instr s) as [l [P Q]]; a ★적용
   2. score= -88.93  inv H.
   3. score= -46.03  exploit make_predecessors_greater; [ea
   4. score= -62.22  destruct H with s.
   5. score= -47.59  destruct (peq n s).
```

---
## `lessdef_list_trans`
**GOLD:** Proof. / induction 1; intros vl3 LD; inv LD; constructor; eauto using lessdef_trans.

**step별 rango top5:**
```text
[step0] 적용: Proof  →VALID
   1. score=  -0.00  Proof. ★적용 ☆gold
   2. score=  -0.00  Proof. ★적용 ☆gold
   3. score=  -0.00  Proof. ★적용 ☆gold
   4. score=  -0.00  Proof. ★적용 ☆gold
   5. score=  -0.00  Proof. ★적용 ☆gold
[step1] 적용: intros vl1 vl2 H1  →VALID
   1. score= -48.71  intros vl1 vl2 H1. ★적용
   2. score= -26.64  intros vl1 vl2 vl2' vl1' vl2'' Hlessde
   3. score= -74.96  induction 1; intros.
   4. score= -25.94  induction 1; intros; destruct vl2; try
   5. score= -61.75  induction 1; simpl.
[step2] 적용: induction 1; auto; simpl in *  →VALID
   1. score= -11.15  induction 1; auto; simpl in *. ★적용
   2. score=  -7.25  induction H1; intros.
   3. score=  -2.17  induction H1; intros.
   4. score= -14.78  induction H1; simpl; eauto with lessde
   5. score=  -4.07  induction 1; intros.
[step3] 적용: inv H1  →VALID
   1. score=  -2.60  inv H1. ★적용
   2. score= -30.30  constructor.
   3. score=  -3.21  eapply lessdef_trans; eauto.
   4. score=  -9.56  destruct H0; auto.
   5. score= -20.49  inv H1. ★적용
[step4] 적용: constructor; auto  →VALID
   1. score= -11.81  constructor; auto. ★적용
   2. score=  -8.48  inversion H5; subst.
   3. score= -20.99  constructor.
   4. score= -11.76  constructor 2.
   5. score=  -4.99  apply lessdef_trans with v1; auto.
[step5] 적용: rewrite lessdef_same; auto  →INVALID
   1. score= -11.80  rewrite lessdef_same; auto. ★적용
   2. score=  -7.55  constructor; auto.
   3. score=  -3.60  apply lessdef_trans with v1; auto.
   4. score=  -2.98  inv H5.
   5. score=  -1.19  eapply lessdef_trans; eauto.
[step6] 적용: eapply lessdef_trans; eauto  →VALID
   1. score= -11.80  rewrite lessdef_same; auto.
   2. score=  -7.55  constructor; auto.
   3. score=  -3.60  apply lessdef_trans with v1; auto.
   4. score=  -2.98  inv H5.
   5. score=  -1.19  eapply lessdef_trans; eauto. ★적용
[step7] 적용: eauto  →VALID
   1. score=  -8.97  eauto. ★적용
   2. score=  -2.50  auto.
   3. score=  -6.85  apply IHlessdef_list; eauto.
   4. score=  -2.55  auto.
   5. score= -28.02  auto.
[step8] 적용: destruct H5  →VALID
   1. score=  -7.99  destruct H5. ★적용
   2. score=  -1.13  eauto.
   3. score=  -4.74  eapply lessdef_list_inv; eauto.
   4. score=  -4.02  apply IHlessdef_list; auto.
   5. score=  -8.99  constructor; auto.
```

---
## 종합
- 정답 tactic top5 포함률 **35%** — 나머지 65%는 아예 못 뽑음(selection).
- 있어도 모델은 **자기 1위(gold 아닌 것)를 적용**하거나 앞 스텝 어긋나 실패(composition).
- score를 보면 모델이 gold보다 **다른 후보에 더 높은 log-prob**을 준 경우가 많음 = 선호 자체가 gold와 다름.
- = recall(88.5%)이 아니라 **selection + composition = 1.3B capacity**.

관련: [[RECALL_VS_USE_EXAMPLES]] · [[WHY_COMPOUND_WONT_FIX_CLOSING]]