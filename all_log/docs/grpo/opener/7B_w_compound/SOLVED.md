# ✅ opener-tac(w compound) 성공 예시

작성 2026-08-01. opener-tac(w compound)가 닫은 정리들.
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
### `is_nan_SF2FF` · plain: solved
**GOLD 전문:**
```coq
Proof.
now intros [s|s| |s m e].
Qed.
```
**opener-tac(w compound):**
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
**opener-tac(w compound):**
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
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] easy.                                                 | ❌ INVALID(거부, 상태유지)
[rango ] intros [sx|sx| |sx mx ex Hx].                         | ✓  VALID  ↻재시도
[rango ] (* *) now destruct sx.                                | ✓  VALID
[rango ] (* *) now destruct sx.                                | ✓  VALID
[rango ] (* *) easy.                                           | ✓  VALID
[rango ] (* *) now destruct sx.                                | ✅ COMPLETE(Qed 완결)
```

---
### `lessdef_list_trans` · plain: mixed
**GOLD 전문:**
```coq
Proof.
induction 1; intros vl3 LD; inv LD; constructor; eauto using lessdef_trans.
Qed.
```
**opener-tac(w compound):**
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
**opener-tac(w compound):**
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
**opener-tac(w compound):**
```text
[opener] destruct i; reflexivity.                              | ✅ COMPLETE(Qed 완결)
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
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] destruct v1; destruct v2; auto.                       | ✓  VALID
[rango ] unfold cmpf, cmpf_bool.                               | ✓  VALID
[rango ] rewrite Float.cmp_ge_gt_eq.                           | ✓  VALID
[rango ] destruct (Float.cmp Cgt f f0); destruct (Float.cmp C… | ✅ COMPLETE(Qed 완결)
```

---
### `tr_funbody_inv` · plain: mixed
**GOLD 전문:**
```coq
Proof.
intros.
inv H.
eauto.
Qed.
```
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros.                                               | ✓  VALID
[opener] inv H.                                                | ✓  VALID
[rango ] specialize (H2 pc i).                                 | ✓  VALID
[opener] inv H0.                                               | ✓  VALID
[rango ] eauto.                                                | ✅ COMPLETE(Qed 완결)
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
**opener-tac(w compound):**
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
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] unfold list_disjoint; simpl; intros.                  | ✓  VALID
[rango ] intro.                                                | ✓  VALID
[rango ] apply H; auto.                                        | ❌ INVALID(거부, 상태유지)
[rango ] eapply H; eauto.                                      | ✅ COMPLETE(Qed 완결)  ↻재시도
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
**opener-tac(w compound):**
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
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros F Hf.                                          | ✓  VALID
[rango ] destruct (Rnd_N_pt_DN_or_UP F 0 Hf) as [Hd|Hu] ; con… | ❌ INVALID(거부, 상태유지)
[rango ] now apply Rnd_N_pt_refl with (1 := Hf).               | ✅ COMPLETE(Qed 완결)  ↻재시도
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
**opener-tac(w compound):**
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
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros E1.                                            | ✓  VALID
[rango ] unfold splitlong in E1.                               | ✓  VALID
[rango ] rewrite negb_true_iff in E1.                          | ❌ INVALID(거부, 상태유지)
[rango ] unfold ptr64.                                         | ✓  VALID  ↻재시도
[rango ] auto.                                                 | ✅ COMPLETE(Qed 완결)
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
**opener-tac(w compound):**
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
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] destruct x; destruct y; simpl; auto.                  | ✓  VALID
[rango ] red.                                                  | ✓  VALID
[rango ] apply EqSet.union_3; auto.                            | ✅ COMPLETE(Qed 완결)
```

---
### `init_regs_lessdef` · plain: mixed
**GOLD 전문:**
```coq
Proof.
induction rl; simpl; intros.
red; intros.
rewrite Regmap.gi.
auto.
inv H.
red; intros.
rewrite Regmap.gi.
auto.
apply set_reg_lessdef; auto.
Qed.
```
**opener-tac(w compound):**
```text
[opener] induction rl; simpl; intros.                          | ✓  VALID
[rango ] -                                                     | ✓  VALID
[rango ] red.                                                  | ✓  VALID
[rango ] match goal with |- (forall _ , val) => replace (fora… | ❌ INVALID(거부, 상태유지)
[rango ] intros.                                               | ✓  VALID  ↻재시도
[rango ] constructor.                                          | ✓  VALID
[rango ] -                                                     | ✓  VALID
[rango ] destruct vl1 as [ | v1 vs].                           | ✓  VALID
[opener] inv H.                                                | ✓  VALID
[rango ] constructor.                                          | ✓  VALID
[opener] inv H.                                                | ✓  VALID
[rango ] apply set_reg_lessdef.                                | ✓  VALID
[rango ] assumption.                                           | ✓  VALID
[rango ] apply IHrl; auto.                                     | ✅ COMPLETE(Qed 완결)
```

---
### `gmap` · plain: mixed
**GOLD 전문:**
```coq
Proof.
intros.
unfold map, get.
apply PMap.gmap.
Qed.
```
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros.                                               | ✓  VALID
[rango ] destruct m.                                           | ❌ INVALID(거부, 상태유지)
[rango ] unfold map, get.                                      | ✓  VALID  ↻재시도
[rango ] reflexivity.                                          | ✅ COMPLETE(Qed 완결)
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
**opener-tac(w compound):**
```text
[opener] induction l; simpl.                                   | ✓  VALID
[rango ] split.                                                | ❌ INVALID(거부, 상태유지)
[rango ] auto.                                                 | ✓  VALID  ↻재시도
[rango ] apply Val.inject_list_inj.                            | ❌ INVALID(거부, 상태유지)
[rango ] eauto.                                                | ✅ COMPLETE(Qed 완결)  ↻재시도
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
**opener-tac(w compound):**
```text
[rango ] Proof.                                                | ✓  VALID
[rango ] intros.                                               | ✓  VALID
[rango ] rewrite dests_disjoint_sym.                           | ✓  VALID
[rango ] rewrite dests_disjoint_append_left.                   | ✓  VALID
[rango ] rewrite (dests_disjoint_sym m1 m2).                   | ✓  VALID
[rango ] tauto.                                                | ❌ INVALID(거부, 상태유지)
[rango ] rewrite (dests_disjoint_sym m2 m1).                   | ✓  VALID  ↻재시도
[rango ] tauto.                                                | ❌ INVALID(거부, 상태유지)
[rango ] firstorder.                                           | ✅ COMPLETE(Qed 완결)  ↻재시도
```
