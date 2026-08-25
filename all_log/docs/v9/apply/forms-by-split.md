# `apply` · `rewrite` 형태별 — split 비교와 실패 실측

> 학습이 무엇을 가르치고, CompCert 가 무엇을 요구하고, 모델이 어디서 틀리는가.
> 예시는 전부 **실제 소스에서 뽑은 것**이고 실패 예시는 rand200 로그에서 뽑았다.

데이터: TRAIN 120프로젝트 428,085스텝 · CompCert 113,078스텝 ·
rand200 로그 122정리(ckpt-12000/25000 합산)

---

## 0. 한 장 요약

| 형태 | TRAIN | CompCert | 비 | 모델 사용 | **모델 실패율** |
|---|---|---|---|---|---|
| `apply L.` | 10.8% | 13.3% | 1.2× | 1,141 | 15.8% |
| `eapply L.` | — | — | — | 1,759 | 4.1% |
| `apply L with (x := e).` | 1.0% | 1.9% | **1.9×** | 71 | 22.5% |
| `apply L in H.` | 1.2% | 0.3% | **0.2×** | 173 | **48.0%** |
| `apply (L a b).` | 3.3% | 0.4% | **0.1×** | 50 | 18.0% |
| `rewrite L.` | 6.5% | 8.0% | 1.2× | 1,757 | **44.8%** |
| `rewrite <- L.` | 1.0% | 1.3% | 1.3× | 584 | **43.5%** |
| `rewrite (L a b).` | 1.9% | 0.8% | **0.4×** | 100 | **44.0%** |
| `rewrite L by tac.` | 0.1% | 1.4% | **14.0×** | 32 | **84.4%** |
| `rewrite L in H.` | 0.7% | 0.7% | 1.0× | 175 | **61.7%** |
| `rewrite L at n.` | 0.0% | 0.0% | — | 2 | **50.0%** |
| `erewrite L.` | — | — | — | — | — |

* **비** = CompCert ÷ TRAIN. 1보다 크면 **CompCert 가 더 많이 요구하는데 학습이 덜 가르친 것**.
* **모델 실패율** = rand200 에서 그 형태로 생성한 tactic 중 Coq 이 INVALID 로 거부한 비율.

**읽을 것 셋**

1. **학습이 8.3배 과잉으로 가르치는 형태가 있다** — `apply (L a b)` 항 부분적용
   (TRAIN 3.3% vs CompCert 0.4%). CompCert 는 인자를 줄 때 `with (x := e)` 를 쓴다.
2. **CompCert 가 14배 더 쓰는데 학습에 거의 없는 형태가 있다** — `rewrite L by tac`
   (TRAIN 0.1% vs CompCert 1.4%). 그리고 모델의 실패율이 **84.4%** 로 최악이다.
3. **`rewrite` 계열이 통째로 나쁘다** — 맨 형태 44.8% · `<-` 43.5% · `in H` 61.7%.
   `apply` 계열(4~22%)의 두세 배다.

---

## `apply L.`

L 의 결론을 goal 과 **고차 단일화**한다. 인자는 전부 Coq 이 정한다. 못 정하면 즉사.

TRAIN **10.8%**　CompCert **13.3%**　모델 사용 **1,141회**　모델 실패율 **15.8%**

**TRAIN 실제 예**

```coq
  apply eqP.        // wytseoortwijn-VMCAI20-SharedMemAbstr/coq/HahnBase.v
  apply IHsub_r; try assumption.        // julbinb-ftfjp-2019/Mechanization/MiniJl/RedSubProps.v
  apply SR_UnionR1; apply IHHsub1; assumption.        // julbinb-ftfjp-2019/Mechanization/MiniJl/RedSubProps.v
  apply SR_UnionR2; apply IHHsub1; assumption.        // julbinb-ftfjp-2019/Mechanization/MiniJl/RedSubProps.v
  apply IHHsub1; try assumption.        // julbinb-ftfjp-2019/Mechanization/MiniJl/RedSubProps.v
```

**CompCert 실제 예**

```coq
  apply Int.eq_dec.        // compcert/backend/NeedDomain.v
  apply vagree_same.        // compcert/backend/NeedDomain.v
  apply orb_true_r; auto.        // compcert/backend/NeedDomain.v
  apply iagree_not; auto.        // compcert/backend/NeedDomain.v
  apply iagree_not'.        // compcert/backend/NeedDomain.v
```

**모델이 틀린 예 (rand200)**

```
  apply Z.le_le.
      → The reference Z.le_le was not found in the current environment.
  apply Z.le_ge_lt.
      → The reference Z.le_ge_lt was not found …
```

---

## `eapply L.`

못 정한 인자를 **evar(`?x`)로 미룬다.** 실패를 뒤로 넘기므로 가장 안전하다.

모델 사용 **1,759회**　모델 실패율 **4.1%**

**TRAIN 실제 예**

```coq
  eapply IHh1_2; [ now eauto| | now eauto].        // codyroux-hoare-toy/lang.v
  eapply IHh1_1; eauto; congruence.        // codyroux-hoare-toy/lang.v
  eapply starES.        // coq-community-autosubst/examples/ssr/pred_CC_omega.v
  eapply pstep_beta; eauto.        // coq-community-autosubst/examples/ssr/pred_CC_omega.v
  eapply sub_sort.        // coq-community-autosubst/examples/ssr/pred_CC_omega.v
```

**CompCert 실제 예**

```coq
  eapply eqmod_trans.        // compcert/backend/NeedDomain.v
  eapply same_bits_eqmod; eauto.        // compcert/backend/NeedDomain.v
  eapply nge_trans; eauto.        // compcert/backend/NeedDomain.v
  eapply bc_stack; eauto.        // compcert/backend/NeedDomain.v
  eapply STK; eauto.        // compcert/backend/NeedDomain.v
```

**모델이 틀린 예 (rand200)**

```
  eapply alloc_global_unchanged.
      → The variable alloc_global_unchanged was not found …
```

---

## `apply L with (x := e).`

**이름으로** 인자를 못박는다. lemma 의 arity·순서를 몰라도 되는 것이 핵심.

TRAIN **1.0%**　CompCert **1.9%**　모델 사용 **71회**　모델 실패율 **22.5%**

**TRAIN 실제 예**

```coq
  apply sub_r_nf__transitive with (MkNF(t')); try (apply mk_nf__in_nf).        // julbinb-ftfjp-2019/Mechanization/MiniJl/RedSubProps.v
  apply sub_r_nf__transitive with (MkNF( TPair t1' t2'));
  assumption || apply mk_nf__in_nf.        // julbinb-ftfjp-2019/Mechanization/MiniJl/RedSubProps.v
  apply multi_step with (APlus (ANum 3) (ANum 12)).        // norangLemon-plHW/02/Types.v
  apply multi_step with (ANum 15).        // norangLemon-plHW/02/Types.v
```

**CompCert 실제 예**

```coq
  apply eqmod_trans with ((i - Int.unsigned amount) + Int.unsigned amount).        // compcert/backend/NeedDomain.v
  apply eval_condition_inj with (f := inject_id) (m1 := m1) (vl1 := args1); auto.        // compcert/backend/NeedDomain.v
  apply nge_agree with (NE.get r ne); auto.        // compcert/backend/NeedDomain.v
  eapply exec_Lload with (a := a).        // compcert/backend/Debugvarproof.v
  eapply exec_Lstore with (a := a).        // compcert/backend/Debugvarproof.v
```

**모델이 틀린 예 (rand200)**

```
  apply bpow_le with (bpow e2).
      → Not the right number of missing arguments (expected 0).
  apply Z.lt_le with (1 := H).
      → The reference Z.lt_le was not found …
```

---

## `apply L in H.`

**전방향** — goal 이 아니라 가설 `H` 를 L 로 변형한다. 방향이 반대다.

TRAIN **1.2%**　CompCert **0.3%**　모델 사용 **173회**　모델 실패율 **48.0%**

**TRAIN 실제 예**

```coq
  apply lambdaA_t in H.        // Kilgrobil-weak_distributive_laws/powerset_github.v
  apply cr_star_normal in h => //.        // coq-community-autosubst/examples/ssr/pred_CC_omega.v
  apply red_prod_inv in h.        // coq-community-autosubst/examples/ssr/pred_CC_omega.v
  apply (f_equal g) in E; trivial.        // DmxLarchey-Introduction-to-Coq/lab2.v
  apply Hg, Hf in E; trivial.        // DmxLarchey-Introduction-to-Coq/lab2.v
```

**CompCert 실제 예**

```coq
  apply filter_In in H1.        // compcert/backend/Debugvarproof.v
  apply Pos.compare_gt_iff in L.        // compcert/backend/Debugvarproof.v
  apply Pos.compare_lt_iff in L.        // compcert/backend/Debugvarproof.v
  apply join_2 in H3; auto.        // compcert/backend/Debugvarproof.v
  apply is_sgn_sign_ext in H1; auto.        // compcert/backend/ValueDomain.v
```

**모델이 틀린 예 (rand200)**

```
  apply lt_bpow in H.
      → Unable to apply lemma of type …
  apply H_asrt0 in H.
      → Unable to apply lemma of type …
```

---

## `apply (L a b).`

**위치로** 인자를 채운 항을 만들어 적용한다. arity 와 순서를 알아야 한다.

TRAIN **3.3%**　CompCert **0.4%**　모델 사용 **50회**　모델 실패율 **18.0%**

**TRAIN 실제 예**

```coq
  apply (im_nonempty (im g) (lambda A t)).        // Kilgrobil-weak_distributive_laws/powerset_github.v
  eapply (conv_subst _ conv).        // coq-community-autosubst/examples/ssr/pred_CC_omega.v
  eapply (ty_ctx_conv tp2).        // coq-community-autosubst/examples/ssr/pred_CC_omega.v
  apply (H1 _ Ha).        // DmxLarchey-Introduction-to-Coq/lab2.v
  apply (H _ Hx).        // DmxLarchey-Introduction-to-Coq/lab2.v
```

**CompCert 실제 예**

```coq
  apply (andimm_redundant_sound (Vint (Int.not i)) (Vint (Int.not i0)) (I m) (Int.not n)).        // compcert/backend/NeedDomain.v
  eapply (Genv.init_mem_transf_partial TRANSF); eauto.        // compcert/backend/Debugvarproof.v
  eapply (REC (sz - 1)).        // compcert/backend/ValueDomain.v
  apply (Genv.init_mem_match TRANSL); auto.        // compcert/backend/Constpropproof.v
  apply (combine_comparison_cmp_sound valu c v v0 res res'); auto.        // compcert/arm/CombineOpproof.v
```

**모델이 틀린 예 (rand200)**

```
  apply (typesize_pos Int).
      → The variable Int was not found in the current environment.
  apply (Rmult_lt_compat_left H3).
      → The variable Rmult_lt_compat_left was not found …
```

---

## `rewrite L.`

등식 `L : a = b` 로 goal 의 `a` 를 `b` 로 바꾼다. 어느 인스턴스인지는 Coq 이 고른다.

TRAIN **6.5%**　CompCert **8.0%**　모델 사용 **1,757회**　모델 실패율 **44.8%**

**TRAIN 실제 예**

```coq
  rewrite unite_pairs_union_t.        // julbinb-ftfjp-2019/Mechanization/MiniJl/RedSubProps.v
  rewrite unite_pairs_union_t.        // julbinb-ftfjp-2019/Mechanization/MiniJl/RedSubProps.v
  rewrite unite_pairs_union_t.        // julbinb-ftfjp-2019/Mechanization/MiniJl/RedSubProps.v
  rewrite unite_pairs_union_t.        // julbinb-ftfjp-2019/Mechanization/MiniJl/RedSubProps.v
  rewrite Heq.        // elfi-sf/orig_files/SfLib.v
```

**CompCert 실제 예**

```coq
  rewrite H0; auto.        // compcert/backend/NeedDomain.v
  rewrite H0.        // compcert/backend/NeedDomain.v
  rewrite H1.        // compcert/backend/NeedDomain.v
  rewrite iagree_and_eq.        // compcert/backend/NeedDomain.v
  rewrite Int.bits_shru by lia.        // compcert/backend/NeedDomain.v
```

**모델이 틀린 예 (rand200)**

```
  rewrite Int64.eq_sym.
      → Found no subterm matching "Int64.eq ?M ?M" in the current goal.
  rewrite STORE.
      → Found no subterm matching "store chunk m1 b ofs v" …
```

---

## `rewrite <- L.`

반대 방향. `b` 를 `a` 로.

TRAIN **1.0%**　CompCert **1.3%**　모델 사용 **584회**　모델 실패율 **43.5%**

**TRAIN 실제 예**

```coq
  rewrite <- H.        // elfi-sf/orig_files/SfLib.v
  rewrite <- H.        // Kilgrobil-weak_distributive_laws/powerset_github.v
  rewrite <- H2 in H0.        // Kilgrobil-weak_distributive_laws/powerset_github.v
  rewrite <- H1, H3.        // Kilgrobil-weak_distributive_laws/powerset_github.v
  rewrite <- H, <- H0.        // Kilgrobil-weak_distributive_laws/powerset_github.v
```

**CompCert 실제 예**

```coq
  rewrite <- H in H2.        // compcert/backend/NeedDomain.v
  rewrite <- H.        // compcert/backend/NeedDomain.v
  rewrite <- H.        // compcert/backend/NeedDomain.v
  rewrite <- H1.        // compcert/backend/NeedDomain.v
  rewrite <- F2R_change_exp.        // compcert/flocq/Calc/Operations.v
```

**모델이 틀린 예 (rand200)**

```
  rewrite <- encode_val_shape.
      → Cannot find an homogeneous relation to rewrite.
  rewrite <- store_mem_contents.
      → store_mem_contents depends on the variable STORE which is not de…
```

---

## `rewrite (L a b).`

L 을 **부분적용**해 어느 인스턴스인지 못박는다. `Found no subterm` 의 해법.

TRAIN **1.9%**　CompCert **0.8%**　모델 사용 **100회**　모델 실패율 **44.0%**

**TRAIN 실제 예**

```coq
  rewrite (mk_nf_nf__equal _ Hnf1).        // julbinb-ftfjp-2019/Mechanization/MiniJl/RedSubProps.v
  rewrite (mk_nf_nf__equal _ Hnf2).        // julbinb-ftfjp-2019/Mechanization/MiniJl/RedSubProps.v
  rewrite <- (mk_nf_nf__equal _ Hnfa).        // julbinb-ftfjp-2019/Mechanization/MiniJl/RedSubProps.v
  rewrite (subst_ee_intro x); auto using subst_ee_expr.        // esope-fzip_coq/metatheory/Fsub_LetSum_Infrastructure.v
  erewrite <- (H (fst (split x)) (snd (split x))).        // wricciot-nullSQL/SemFacts.v
```

**CompCert 실제 예**

```coq
  rewrite (Int.and_commut n).        // compcert/backend/NeedDomain.v
  rewrite <- (Int.not_involutive x).        // compcert/backend/NeedDomain.v
  rewrite <- (Int.not_involutive y).        // compcert/backend/NeedDomain.v
  rewrite (parent_locset_match _ _ STACKS).        // compcert/backend/Debugvarproof.v
  rewrite (match_program_main TRANSF), symbols_preserved.        // compcert/backend/Debugvarproof.v
```

**모델이 틀린 예 (rand200)**

```
  rewrite <- (IZR_Zpower radix2).
      → Found no subterm matching "bpow radix2 ?M" …
```

---

## `rewrite L by tac.`

L 의 **전제(부수 goal)** 를 그 자리에서 닫는다. 조건부 등식에 필수.

TRAIN **0.1%**　CompCert **1.4%**　모델 사용 **32회**　모델 실패율 **84.4%**

**TRAIN 실제 예**

```coq
  rewrite IHn2 by lia.        // wilcoxjay-mechanized-metatheory2/util.v
  erewrite IHm by eassumption.        // wilcoxjay-mechanized-metatheory2/map.v
  erewrite gs_aux by eassumption.        // wilcoxjay-mechanized-metatheory2/map.v
  rewrite key_eq_dec_no by auto using lt_neq.        // wilcoxjay-mechanized-metatheory2/map.v
  rewrite key_eq_dec_yes in E by reflexivity.        // wilcoxjay-mechanized-metatheory2/map.v
```

**CompCert 실제 예**

```coq
  rewrite ! H by auto.        // compcert/backend/NeedDomain.v
  rewrite zlt_true by lia.        // compcert/backend/NeedDomain.v
  rewrite zlt_false by lia.        // compcert/backend/NeedDomain.v
  rewrite Int.bits_shru in H2 by auto.        // compcert/backend/NeedDomain.v
  rewrite ! Int.bits_shr by auto.        // compcert/backend/NeedDomain.v
```

**모델이 틀린 예 (rand200)**

```
  rewrite pop_preserves_invariant by eauto.
      → Syntax error: [ltac_use_default] expected after [tactic]
  rewrite INJ by auto.
      → Found no subterm matching "F ?M" in the current goal.
```

---

## `rewrite L in H.`

goal 이 아니라 가설 안에서 재작성.

TRAIN **0.7%**　CompCert **0.7%**　모델 사용 **175회**　모델 실패율 **61.7%**

**TRAIN 실제 예**

```coq
  rewrite H4 in H5.        // Kilgrobil-weak_distributive_laws/powerset_github.v
  rewrite H in H1.        // Kilgrobil-weak_distributive_laws/powerset_github.v
  rewrite H2,H in H3.        // Kilgrobil-weak_distributive_laws/powerset_github.v
  rewrite subset_in_union in H3 ; try assumption.        // Kilgrobil-weak_distributive_laws/powerset_github.v
  rewrite H in H1.        // Kilgrobil-weak_distributive_laws/powerset_github.v
```

**CompCert 실제 예**

```coq
  rewrite iagree_and_eq in H.        // compcert/backend/NeedDomain.v
  rewrite ! Int.and_mone in H.        // compcert/backend/NeedDomain.v
  rewrite iagree_and_eq in *.        // compcert/backend/NeedDomain.v
  rewrite iagree_and_eq in H.        // compcert/backend/NeedDomain.v
  rewrite iagree_and_eq in H.        // compcert/backend/NeedDomain.v
```

**모델이 틀린 예 (rand200)**

```
  rewrite <-size_chunk_conv in STORE.
      → Found no subterm matching "Z.of_nat (size_chunk_nat ?M)" …
```

---

## `rewrite L at n.`

**몇 번째 등장**인지 지정. 인스턴스가 여럿일 때.

TRAIN **0.0%**　CompCert **0.0%**　모델 사용 **2회**　모델 실패율 **50.0%**

**TRAIN 실제 예**

```coq
  rewrite HH at 3; apply (joinl_hom1 n); auto.        // olivierverdier-GeometricAlgebra/Grassmann.v
  rewrite H2 at 2; rewrite first_deg0; auto.        // olivierverdier-GeometricAlgebra/Grassmann.v
  rewrite <- wplus_unit at 1.        // mit-plv-bbv/src/bbv/Word.v
  rewrite <-Hw; rewrite <-Hw in H at 2; clear Hw.        // mit-plv-bbv/src/bbv/Word.v
  rewrite <- Nat.mul_1_r at 1.        // mit-plv-bbv/src/bbv/Word.v
```

**CompCert 실제 예**

```coq
  rewrite <- (Rabs_right (bpow e)) at 3.        // compcert/flocq/Calc/Round.v
  rewrite Fx at 1.        // compcert/flocq/Calc/Round.v
  rewrite (Zdecomp x) at 1.        // compcert/lib/Zbits.v
  rewrite H0 at 1.        // compcert/lib/Zbits.v
  rewrite H0 at 3.        // compcert/lib/Zbits.v
```

**모델이 틀린 예 (rand200)**

```
  rewrite size_chunk_Mptr at 3.
      → Invalid occurrence number: 3.
```

---

## `erewrite L.`

`eapply` 의 rewrite 판 — 못 정한 변수를 evar 로 남긴다.



**TRAIN 실제 예**

```coq
  erewrite IHe1; erewrite IHe2; now auto.        // codyroux-hoare-toy/lang.v
  erewrite eval_ext; now auto.        // codyroux-hoare-toy/lang.v
  erewrite get_wf_aux_lt_None in H by eauto.        // wilcoxjay-mechanized-metatheory2/map.v
  erewrite get_wf_aux_lt_None in H by eauto.        // wilcoxjay-mechanized-metatheory2/map.v
  erewrite get_wf_aux_lt_None in H by eauto.        // wilcoxjay-mechanized-metatheory2/map.v
```

**CompCert 실제 예**

```coq
  erewrite bbeq_sound; eauto.        // compcert/backend/ValueDomain.v
  erewrite bc_below_invalid; eauto.        // compcert/backend/ValueDomain.v
  erewrite weak_valid_ptr_inj by eauto.        // compcert/common/Values.v
  erewrite weak_valid_ptr_inj by eauto.        // compcert/common/Values.v
  erewrite weak_valid_ptr_inj by eauto.        // compcert/common/Values.v
```

---

