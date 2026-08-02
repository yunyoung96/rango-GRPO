# ✅ opener-sub(wo compound) 성공 예시

작성 2026-08-01. opener-sub(wo compound)가 닫은 정리들.
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
### `is_nan_SF2FF` · plain: solved
**GOLD 전문:**
```coq
Proof.
now intros [s|s| |s m e].
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] now intros [s|s|s|s m e].                             | ❌ INVALID(거부, 상태유지)
[rango ] now intros [s|s| |s m e].                             | ✅ COMPLETE(Qed 완결)  ↻재시도
```

---
### `F2R_bpow` · plain: solved
**GOLD 전문:**
```coq
Proof.
intros e.
unfold F2R.
simpl.
apply Rmult_1_l.
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros e.                                             | ✓  VALID
[rango ] unfold F2R.                                           | ✓  VALID
[rango ] simpl.                                                | ✓  VALID
[rango ] rewrite <- Rmult_1_l.                                 | ✓  VALID
[rango ] reflexivity.                                          | ✅ COMPLETE(Qed 완결)
```

---
### `Bopp_involutive` · plain: mixed
**GOLD 전문:**
```coq
Proof.
now intros [sx|sx| |sx mx ex Hx] ; simpl ; try rewrite Bool.negb_involutive.
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] easy.                                                 | ❌ INVALID(거부, 상태유지)
[rango ] intros [y|y| |y my] ; try easy ; simpl.               | ✓  VALID  ↻재시도
[rango ] -                                                     | ✓  VALID
[rango ] now destruct (notboolnegb y).                         | ❌ INVALID(거부, 상태유지)
[rango ] now destruct y.                                       | ✓  VALID  ↻재시도
[rango ] -                                                     | ✓  VALID
[rango ] destruct y.                                           | ✓  VALID
[rango ] +                                                     | ✓  VALID
[rango ] easy.                                                 | ✓  VALID
[rango ] +                                                     | ✓  VALID
[rango ] easy.                                                 | ✓  VALID
[rango ] -                                                     | ✓  VALID
[rango ] destruct y.                                           | ✓  VALID
[rango ] +                                                     | ✓  VALID
[rango ] easy.                                                 | ✓  VALID
[rango ] +                                                     | ✓  VALID
[rango ] easy.                                                 | ✅ COMPLETE(Qed 완결)
```

---
### `lessdef_list_trans` · plain: mixed
**GOLD 전문:**
```coq
Proof.
induction 1; intros vl3 LD; inv LD; constructor; eauto using lessdef_trans.
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] induction 1; intros.                                  | ✓  VALID
[rango ] auto.                                                 | ✓  VALID
[rango ] inv H1; auto.                                         | ✓  VALID
[rango ] constructor; auto.                                    | ✓  VALID
[rango ] eauto.                                                | ✓  VALID
[rango ] eauto.                                                | ✓  VALID
[rango ] eauto.                                                | ✓  VALID
[rango ] eauto.                                                | ✓  VALID
[rango ] eauto.                                                | ✓  VALID
[rango ] eauto.                                                | ✓  VALID
[rango ] eauto.                                                | ✓  VALID
[rango ] eauto.                                                | ✓  VALID
[rango ] eauto.                                                | ✓  VALID
[rango ] eauto.                                                | ✓  VALID
[rango ] eapply lessdef_trans; eauto.                          | ✅ COMPLETE(Qed 완결)
```

---
### `sub_zero_r` · plain: mixed
**GOLD 전문:**
```coq
Proof.
destruct x; simpl; auto.
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] destruct x; simpl; auto.                              | ✅ COMPLETE(Qed 완결)
```

---
### `typeconv_integer_promotion` · plain: mixed
**GOLD 전문:**
```coq
Proof.
destruct i; reflexivity.
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] destruct i; simpl; auto.                              | ✅ COMPLETE(Qed 완결)
```

---
### `Plt_succ` · plain: mixed
**GOLD 전문:**
```coq
Proof.
unfold Plt; intros.
apply Pos.lt_succ_r.
apply Pos.le_refl.
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] unfold Plt; intro.                                    | ✓  VALID
[rango ] red; red; intro.                                      | ❌ INVALID(거부, 상태유지)
[rango ] apply Pos.lt_succ_diag_r; auto.                       | ✅ COMPLETE(Qed 완결)  ↻재시도
```

---
### `list_disjoint_notin` · plain: mixed
**GOLD 전문:**
```coq
Proof.
unfold list_disjoint; intros; red; intros.
apply H with a a; auto.
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] unfold list_disjoint; simpl; intros.                  | ✓  VALID
[rango ] intro.                                                | ✓  VALID
[rango ] apply H; auto.                                        | ❌ INVALID(거부, 상태유지)
[rango ] eapply H; eauto.                                      | ✅ COMPLETE(Qed 완결)  ↻재시도
```

---
### `eqb_false` · plain: mixed
**GOLD 전문:**
```coq
Proof.
now intros [|] [|].
Qed.
```
**opener-sub(wo compound):**
```text
[opener] destruct x; destruct y; auto.                         | ✅ COMPLETE(Qed 완결)
```

---
### `cmpf_ge` · plain: mixed
**GOLD 전문:**
```coq
Proof.
destruct v1; destruct v2; auto.
unfold cmpf, cmpf_bool.
rewrite Float.cmp_ge_gt_eq.
destruct (Float.cmp Cgt f f0); destruct (Float.cmp Ceq f f0); auto.
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] destruct v1; destruct v2; auto.                       | ✓  VALID
[rango ] unfold cmpf, cmpf_bool.                               | ✓  VALID
[rango ] rewrite Float.cmp_ge_gt_eq.                           | ✓  VALID
[rango ] destruct (Float.cmp Cgt f f0); destruct (Float.cmp C… | ✅ COMPLETE(Qed 완결)
```

---
### `Zle_bool_true` · plain: mixed
**GOLD 전문:**
```coq
Proof.
intros x y.
apply (proj1 (Zle_is_le_bool x y)).
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros x y Hle.                                       | ✓  VALID
[rango ] generalize (proj1 (Zle_is_le_bool _ _) Hle).          | ✓  VALID
[rango ] case (Zle_eq_dec _ _); intros; easy.                  | ❌ INVALID(거부, 상태유지)
[rango ] easy.                                                 | ✅ COMPLETE(Qed 완결)  ↻재시도
```

---
### `Rnd_N_pt_0` · plain: mixed
**GOLD 전문:**
```coq
Proof.
intros F HF.
split.
exact HF.
intros g _.
rewrite 2!Rminus_0_r, Rabs_R0.
apply Rabs_pos.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] intros.                                               | ✓  VALID
[opener] destruct H.                                           | ❌ INVALID(거부, 상태유지)
[rango ] now apply Rnd_N_pt_refl.                              | ✅ COMPLETE(Qed 완결)  ↻재시도
```

---
### `Rinv_lt` · plain: mixed
**GOLD 전문:**
```coq
Proof.
intros x y Hx Hxy.
apply Rinv_lt_contravar.
apply Rmult_lt_0_compat.
exact Hx.
now apply Rlt_trans with x.
exact Hxy.
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros x y Hx Hyp.                                    | ✓  VALID
[rango ] apply Rinv_lt_contravar.                              | ✓  VALID
[rango ] apply Rmult_lt_0_compat ;   try (lra || now apply Rl… | ✓  VALID
[rango ] assumption.                                           | ✅ COMPLETE(Qed 완결)
```

---
### `splitlong_ptr32` · plain: mixed
**GOLD 전문:**
```coq
Proof.
unfold splitlong, ptr64; congruence.
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros E1.                                            | ✓  VALID
[rango ] unfold splitlong in E1.                               | ✓  VALID
[rango ] rewrite negb_true in E1.                              | ❌ INVALID(거부, 상태유지)
[rango ] unfold ptr64.                                         | ✓  VALID  ↻재시도
[rango ] reflexivity.                                          | ✅ COMPLETE(Qed 완결)
```

---
### `notbool_bool_val` · plain: mixed
**GOLD 전문:**
```coq
Proof.
intros.
unfold sem_notbool.
destruct (bool_val v t m) as [[] | ]; reflexivity.
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros.                                               | ✓  VALID
[rango ] unfold bool_val; case_j v; case_v (Val.of_bool 1); c… | ❌ INVALID(거부, 상태유지)
[rango ] unfold sem_notbool.                                   | ✓  VALID  ↻재시도
[rango ] destruct (bool_val v t m); auto.                      | ✅ COMPLETE(Qed 완결)
```

---
### `ge_lub_right` · plain: mixed
**GOLD 전문:**
```coq
Proof.
unfold lub, ge, EqSet.Subset; intros.
destruct x; destruct y; auto.
intros; apply EqSet.union_3; auto.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] unfold lub, ge, EqSet.Subset; intros.                 | ✓  VALID
[opener] destruct x; destruct y; auto.                         | ✓  VALID
[rango ] intros; apply EqSet.union_3; auto.                    | ✅ COMPLETE(Qed 완결)
```

---
### `gmap` · plain: solved
**GOLD 전문:**
```coq
Proof.
intros.
unfold map, get.
apply PMap.gmap.
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros.                                               | ✓  VALID
[rango ] destruct m.                                           | ❌ INVALID(거부, 상태유지)
[rango ] unfold map, get.                                      | ✓  VALID  ↻재시도
[rango ] reflexivity.                                          | ✅ COMPLETE(Qed 완결)
```

---
### `Zle_bool_spec` · plain: mixed
**GOLD 전문:**
```coq
Proof.
intros x y.
generalize (Zle_is_le_bool x y).
case Zle_bool ; intros (H1, H2) ; constructor.
now apply H2.
destruct (Zle_or_lt x y) as [H|H].
now specialize (H1 H).
exact H.
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros x y.                                           | ✓  VALID
[rango ] unfold Zle_bool.                                      | ✓  VALID
[rango ] generalize (Zle_bool_prop_spec x y).                  | ❌ INVALID(거부, 상태유지)
[rango ] case Z.compare_spec; intros Heq.                      | ✓  VALID  ↻재시도
[rango ] -                                                     | ✓  VALID
[rango ] now apply Zle_bool_iff.                               | ❌ INVALID(거부, 상태유지)
[rango ] rewrite <- Heq.                                       | ✓  VALID  ↻재시도
[rango ] constructor.                                          | ✓  VALID
[rango ] apply Z.le_refl.                                      | ✓  VALID
[rango ] -                                                     | ✓  VALID
[rango ] constructor.                                          | ✓  VALID
[rango ] now apply Z.lt_le.                                    | ❌ INVALID(거부, 상태유지)
[rango ] now apply Z.lt_le_incl.                               | ✓  VALID  ↻재시도
[rango ] -                                                     | ✓  VALID
[rango ] constructor.                                          | ✓  VALID
[rango ] now apply Heq.                                        | ✅ COMPLETE(Qed 완결)
```

---
### `regs_inject` · plain: mixed
**GOLD 전문:**
```coq
Proof.
induction l; simpl.
constructor.
constructor; auto.
Qed.
```
**opener-sub(wo compound):**
```text
[opener] induction l; simpl.                                   | ✓  VALID
[rango ] +                                                     | ✓  VALID
[rango ] now constructor.                                      | ✓  VALID
[rango ] +                                                     | ✓  VALID
[rango ] econstructor; eauto.                                  | ✅ COMPLETE(Qed 완결)
```

---
### `dests_disjoint_append_right` · plain: mixed
**GOLD 전문:**
```coq
Proof.
intros.
rewrite dests_disjoint_sym.
rewrite dests_disjoint_append_left.
intuition; rewrite dests_disjoint_sym; assumption.
Qed.
```
**opener-sub(wo compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros.                                               | ✓  VALID
[rango ] rewrite (dests_disjoint_app_inv m1 m2).               | ❌ INVALID(거부, 상태유지)
[rango ] rewrite dests_disjoint_sym.                           | ✓  VALID  ↻재시도
[rango ] rewrite dests_disjoint_append_left.                   | ✓  VALID
[rango ] unfold dests_disjoint; intros.                        | ✓  VALID
[rango ] simpl; firstorder.                                    | ✅ COMPLETE(Qed 완결)
```
