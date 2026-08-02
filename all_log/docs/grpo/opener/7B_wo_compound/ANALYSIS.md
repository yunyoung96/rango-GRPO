# opener+rango vs plain SFT→GRPO vs GOLD — 종합 분석

작성 2026-07-31. 롤아웃 100 train theorem, executor=subgoal-학습모델 `rango-grpo-subgoal-bs2`.

- **opener+rango**: opener-once(생성형 opener-7b-sub)가 첫 분해를 열고 → rango(1.3B executor)가 이어감. hedge라 홀수 seed는 순수 rango.
- **plain SFT→GRPO**: 같은 executor를 opener 없이 (재활용: rango-grpo-subgoal-bs2-s0).
- **GOLD**: 사람 증명.

## 0. 기호 범례 (읽는 법)
| 기호 | 뜻 |
|---|---|
| `✓` | **VALID** — tactic 적용 성공, 다음 상태로 전진 |
| `❌` | **INVALID** — 적용 실패(coq-lsp 거부). **상태 안 바뀜 → 버려지고 재시도** |
| `✅` | **COMPLETE** — 증명 완결(Qed) |
| `[opener]`/`[rango]` | 그 수를 opener가 냈나 rango가 냈나 |

## 1. 롤아웃 형식 — '실패(❌) 다음 성공(✅)'이 나오는 원리
각 proof **상태**에서 모델이 tactic 하나를 뽑아 coq-lsp로 검증한다:
- **VALID** → 새 상태로 전진
- **INVALID** → 그 tactic은 **거부되어 상태를 안 바꿈**. 같은 자리에서 **재시도(retry+1)**로 다른 tactic을 다시 뽑음 (max_retries까지)
- **COMPLETE** → Qed

그래서 `❌` 바로 뒤 `✅`가 나올 수 있다 — **실패한 수는 무시되고 같은 위치에서 다시 뽑은 것**. 실제 예 (retry·상태 추적):
```
retry=0  ✓  unfold Plt; intro.            상태→ x: positive, (x < Pos.succ x)
retry=0  ❌ red; red; intro.              [같은 상태] 실패 → 버림
retry=1  ✅ apply Pos.lt_succ_diag_r;auto. [같은 상태] 재시도 성공 → 완결
```
`❌`와 `✅`의 **state_key가 완전히 동일**(`x: positive, (x < Pos.succ x)`) — INVALID는 상태를 안 바꾸므로 ✅는 ❌ 다음이 아니라 **마지막 VALID 상태**(`unfold Plt; intro.` 뒤)에 적용된다.

**MD 읽을 때 주의**: 중간의 `❌`는 버려진 재시도들. 궤적이 `✅`로 끝나면 = 결국 성공(중간 ❌ 무관). ✅ 없이 ❌만 = 재시도 다 써도 못 뚫은 dead.

## 2. 성공률 요약 (롤아웃, greedy 단일궤도)
| 방법 | 정리 ≥1성공 | mixed | attempt 성공률 |
|---|---|---|---|
| **opener+rango (subgoal모델)** | 32% (30/94) | 25 | 17.0% |
| **plain SFT→GRPO** | 34% (99/292) | 78 | 18.9% |
| (참고) gold-SFT + opener-once | 33% | 29% | 17.4% |
| (참고) opener-**every** (매 분기) | 19% | 8% | 12.6% |

→ **opener+rango(32%) ≈ plain(34%) = parity.** opener/subgoal/조합 다 ~32-34%. opener-every는 오히려 악화(19%, 과분해).

## 3. opener/rango 역할 분담 (성공 케이스는 누가 닫았나)
성공한 attempt 중:
- **순수 rango 72개 (56%)** — hedge 홀수 seed라 opener 안 씀, rango 혼자 품
- opener 발동 56개 중: **opener 한방 완결 24** (예: `destruct x; simpl; auto.`가 통째로 닫음) / **opener 열고→rango 이어 닫음 32**

즉 성공의 절반 이상이 opener 없이 rango 혼자, 나머지도 opener가 automation까지 한방에 닫거나 rango가 마무리. **opener가 '열고 rango가 어렵게 닫는' 협업 성공은 소수.** 예 (opener→rango 협업 성공):
```
[opener] ✓ intros.
[opener] ✓ unfold F2R.
[opener] ❌ destruct e; reflexivity.     ← opener 3번째 수 실패(버려짐)
[rango ] ✓ simpl.                        ← rango가 마지막 VALID 상태서 이어감
[rango ] ✅ ring.                         ← rango가 닫음
```

## 4. 왜 opener를 넣어도 성능이 안 오르나 — 두 벽 (열기 vs 닫기)
- **opener는 잘 연다**: opener 여는 수 VALID 75% (첫 수는 90% VALID). gold opening과 정확 일치 52%(인자까지)/73%(분해종류).
- **그런데 열기는 롤아웃의 binding 병목이 아니다**: dead의 실패 위치 = **opening(step≤1) 25% vs closing(step≥2) 75%**. 대부분 잘 연 다음 닫기에서 깨짐.
- **plain SFT도 이미 잘 연다**: compound-destruct 정리서 plain이 gold와 같은 분해 치는 비율은 낮지만(26%), opener로 옳게 열어줘도 닫기 실패는 그대로 → opener/plain parity.
- **결론**: opening과 closing은 **직렬 벽**. opener가 opening을 고쳐도 closing이 여전히 막아서 성능 0 개선.

## 5. closing이 실패하는 이유 (INVALID 1455개 분석)
| 원인 | 비율 |
|---|---|
| **잘못된 lemma apply/rewrite** (`apply f_equal`, `rewrite PTree.gsspec`...) | 45% |
| 기타 | 31% |
| 닫는 대신 또 분해 | 18% |
| automation(auto/lia) 실패 | 7% |

모델이 subgoal을 닫으려고 lemma를 적용하는데 **이 정리에 맞는 lemma·전략을 몰라서** 안 맞는 걸 골라 INVALID. gold의 핵심 보조정리(`exploit make_predecessors_correct_1`, `rewrite dests_disjoint_sym`)를 안 씀 → valid하지만 off-path → 닫기 실패. = **1.3B의 도메인 lemma 지식·증명 경로 부족(capacity 벽)**.

---
## 6. ✅ 맞춘 예시 (12개) — GOLD vs opener+rango vs plain SFT
(대개 gold 경로가 짧고 automation으로 닫히는 것.)

### `is_nan_SF2FF` — opener+rango: **성공** · plain SFT: **solved**
**GOLD 전문:**
```coq
Proof.
now intros [s|s| |s m e].
Qed.
```
**opener+rango:**
```
[rango ] ✓ Proof.
[rango ] ❌ now intros [s|s|s|s m e].
[rango ] ✅ now intros [s|s| |s m e].
```
**plain SFT→GRPO:**
```
✓ Proof.
✅ now intros [s|s| |s m e].
```

### `F2R_bpow` — opener+rango: **성공** · plain SFT: **solved**
**GOLD 전문:**
```coq
Proof.
intros e.
unfold F2R.
simpl.
apply Rmult_1_l.
Qed.
```
**opener+rango:**
```
[rango ] ✓ Proof.
[rango ] ✓ intros e.
[rango ] ✓ unfold F2R.
[rango ] ✓ simpl.
[rango ] ✓ rewrite <- Rmult_1_l.
[rango ] ✅ reflexivity.
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ intros e.
✓ unfold F2R.
✓ simpl.
✓ rewrite <- Rmult_1_l.
✅ reflexivity.
```

### `Bopp_involutive` — opener+rango: **성공** · plain SFT: **mixed**
**GOLD 전문:**
```coq
Proof.
now intros [sx|sx| |sx mx ex Hx] ; simpl ; try rewrite Bool.negb_involutive.
Qed.
```
**opener+rango:**
```
[rango ] ✓ Proof.
[rango ] ❌ easy.
[rango ] ✓ intros [y|y| |y my] ; try easy ; simpl.
[rango ] ✓ -
[rango ] ❌ now destruct (notboolnegb y).
[rango ] ✓ now destruct y.
[rango ] ✓ -
[rango ] ✓ destruct y.
[rango ] ✓ +
[rango ] ✓ easy.
[rango ] ✓ +
[rango ] ✓ easy.
[rango ] ✓ -
[rango ] ✓ destruct y.
[rango ] ✓ +
[rango ] ✓ easy.
[rango ] ✓ +
[rango ] ✅ easy.
```
**plain SFT→GRPO:**
```
✓ Proof.
❌ easy.
✓ intros [sx|sx| |sx mx ex Hx].
✓ (* *)
now destruct sx.
✓ (* *)
now destruct sx.
✓ (* *)
easy.
✅ (* *)
now destruct sx.
```

### `lessdef_list_trans` — opener+rango: **성공** · plain SFT: **mixed**
**GOLD 전문:**
```coq
Proof.
induction 1; intros vl3 LD; inv LD; constructor; eauto using lessdef_trans.
Qed.
```
**opener+rango:**
```
[rango ] ✓ Proof.
[rango ] ✓ induction 1; intros.
[rango ] ✓ auto.
[rango ] ✓ inv H1; auto.
[rango ] ✓ constructor; auto.
[rango ] ✓ eauto.
[rango ] ✓ eauto.
[rango ] ✓ eauto.
[rango ] ✓ eauto.
[rango ] ✓ eauto.
[rango ] ✓ eauto.
[rango ] ✓ eauto.
[rango ] ✓ eauto.
[rango ] ✓ eauto.
[rango ] ✓ eauto.
[rango ] ✅ eapply lessdef_trans; eauto.
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ induction 1; intros.
✓ auto.
✓ inv H1; auto.
✓ constructor; auto.
✓ eauto.
✓ eauto.
✓ eauto.
✓ eauto.
✓ eauto.
✓ eauto.
✓ eauto.
✓ eauto.
✓ eauto.
✓ eauto.
✅ eapply lessdef_trans; eauto.
```

### `sub_zero_r` — opener+rango: **성공** · plain SFT: **mixed**
**GOLD 전문:**
```coq
Proof.
destruct x; simpl; auto.
Qed.
```
**opener+rango:**
```
[rango ] ✓ Proof.
[rango ] ✅ destruct x; simpl; auto.
```
**plain SFT→GRPO:**
```
✓ Proof.
✅ destruct x; simpl; auto.
```

### `typeconv_integer_promotion` — opener+rango: **성공** · plain SFT: **mixed**
**GOLD 전문:**
```coq
Proof.
destruct i; reflexivity.
Qed.
```
**opener+rango:**
```
[rango ] ✓ Proof.
[rango ] ✅ destruct i; simpl; auto.
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ destruct i; simpl.
✓ auto.
✓ auto.
✓ auto.
✓ auto.
✓ auto.
✓ auto.
✓ auto.
✓ auto.
✓ auto.
✓ auto.
✓ auto.
✅ auto.
```

### `Plt_succ` — opener+rango: **성공** · plain SFT: **mixed**
**GOLD 전문:**
```coq
Proof.
unfold Plt; intros.
apply Pos.lt_succ_r.
apply Pos.le_refl.
Qed.
```
**opener+rango:**
```
[rango ] ✓ Proof.
[rango ] ✓ unfold Plt; intro.
[rango ] ❌ red; red; intro.
[rango ] ✅ apply Pos.lt_succ_diag_r; auto.
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ unfold Plt; intro.
❌ red; red; intro.
✅ apply Pos.lt_succ_diag_r; auto.
```

### `list_disjoint_notin` — opener+rango: **성공** · plain SFT: **solved**
**GOLD 전문:**
```coq
Proof.
unfold list_disjoint; intros; red; intros.
apply H with a a; auto.
Qed.
```
**opener+rango:**
```
[rango ] ✓ Proof.
[rango ] ✓ unfold list_disjoint; simpl; intros.
[rango ] ✓ intro.
[rango ] ❌ apply H; auto.
[rango ] ✅ eapply H; eauto.
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ unfold list_disjoint; simpl; intros.
✓ intro.
❌ apply H; auto.
✅ eapply H; eauto.
```

### `eqb_false` — opener+rango: **성공** · plain SFT: **mixed**
**GOLD 전문:**
```coq
Proof.
now intros [|] [|].
Qed.
```
**opener+rango:**
```
[opener] ✅ destruct x; destruct y; auto.
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ intros x y H.
✓ rewrite H.
❌ apply Bool.negb_nonneg.
❌ apply eqb_neg.
✓ unfold Bool.eqb.
✅ now destruct y.
```

### `cmpf_ge` — opener+rango: **성공** · plain SFT: **solved**
**GOLD 전문:**
```coq
Proof.
destruct v1; destruct v2; auto.
unfold cmpf, cmpf_bool.
rewrite Float.cmp_ge_gt_eq.
destruct (Float.cmp Cgt f f0); destruct (Float.cmp Ceq f f0); auto.
Qed.
```
**opener+rango:**
```
[rango ] ✓ Proof.
[rango ] ✓ destruct v1; destruct v2; auto.
[rango ] ✓ unfold cmpf, cmpf_bool.
[rango ] ✓ rewrite Float.cmp_ge_gt_eq.
[rango ] ✅ destruct (Float.cmp Cgt f f0); destruct (Float.cmp Ceq f f0); 
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ destruct v1; destruct v2; auto.
✓ unfold cmpf, cmpf_bool.
✓ rewrite Float.cmp_ge_gt_eq.
✅ destruct (Float.cmp Cgt f f0); destruct (Float.cmp Ceq f f0); 
```

### `Zle_bool_true` — opener+rango: **성공** · plain SFT: **mixed**
**GOLD 전문:**
```coq
Proof.
intros x y.
apply (proj1 (Zle_is_le_bool x y)).
Qed.
```
**opener+rango:**
```
[rango ] ✓ Proof.
[rango ] ✓ intros x y Hle.
[rango ] ✓ generalize (proj1 (Zle_is_le_bool _ _) Hle).
[rango ] ❌ case (Zle_eq_dec _ _); intros; easy.
[rango ] ✅ easy.
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ intros x y Hle.
✓ generalize (proj1 (Zle_is_le_bool _ _) Hle).
❌ case (Zle_eq_dec _ _); intros; easy.
✅ easy.
```

### `Rnd_N_pt_0` — opener+rango: **성공** · plain SFT: **mixed**
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
**opener+rango:**
```
[opener] ✓ intros.
[opener] ❌ destruct H.
[rango ] ✅ now apply Rnd_N_pt_refl.
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ intros F Hf.
❌ destruct (Rnd_N_pt_DN_or_UP F 0 Hf) as [Hd|Hu] ; constructor.
✅ now apply Rnd_N_pt_refl with (1 := Hf).
```

---
## 7. ❌ 틀린 예시 (12개) — GOLD vs opener+rango vs plain SFT
(gold의 핵심 lemma/전략을 rango가 몰라 off-path.)

### `succ_pred` — opener+rango: **실패** · plain SFT: **dead**
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
**opener+rango:**
```
[rango ] ✓ Proof.
[rango ] ✓ intros x Fx.
[rango ] ✓ apply Rle_antisym.
[rango ] ❌ replace (pred x) with ((-1)^(ZnearestA (pred (x))))%Z.
[rango ] ✓ -
[rango ] ❌ apply succ_le_lt with (1 := Fx).
[rango ] ✓ rewrite pred_eq_pos.
[rango ] ❌ rewrite succ_eq_pos by now apply pred_pos_ge_0.
[rango ] ✓ 2: rewrite <- Rplus_0_r.
[rango ] ✓ 2: left.
[rango ] ✓ rewrite succ_eq_pos.
[rango ] ✓ 2: rewrite <- Rplus_0_r.
[rango ] ✓ 2: left.
[rango ] ❌ 2: now apply pred_pos_ge_0.
[rango ] ❌ now apply pred_pos_ge_0.
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ intros x Fx.
✓ pattern (pred x)%R at 1.
❌ rewrite <- (fun_f_pred_eq fexp).
❌ rewrite <- succ_0, <- succ_opp, Ropp_opp ; easy.
❌ apply (le_antisym _ (pred_0 _)).
```

### `make_predecessors_correct_2` — opener+rango: **실패** · plain SFT: **dead**
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
**opener+rango:**
```
[opener] ✓ intros.
[opener] ✓ unfold successors_list.
[opener] ✓ destruct (make_predecessors!s); simpl; intros.
[rango ] ✓ eauto.
[rango ] ✓ eauto.
[rango ] ✓ eauto.
[rango ] ✓ exists l; auto.
[rango ] ✓ auto.
[rango ] ✓ auto.
[rango ] ✓ auto.
[rango ] ✓ auto.
[rango ] ✓ auto.
[rango ] ✓ auto.
[rango ] ✓ auto.
[rango ] ✓ auto.
[rango ] ✓ auto.
[rango ] ✓ auto.
[rango ] ✓ auto.
... (총 23스텝)
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ intros n instr s.
✓ set (l:=make_predecessors ! s).
✓ intros.
✓ exists (successors instr).
✓ split.
✓ auto.
❌ apply H0.
✓ destruct l as [|l].
❌ reflexivity.
❌ exists s; trivial.
✓ simpl.
✓ auto.
❌ apply f_equal with (f:= (fun m=>(s,m))).
❌ subst l.
❌ apply inj.
```

### `locmap_set_lessdef` — opener+rango: **실패** · plain SFT: **dead**
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
**opener+rango:**
```
[opener] ✓ intros; red; intros.
[opener] ❌ inv H.
[rango ] ❌ destruct (Val.compare v1 v2) as [EQ | [LT | GT]].
[rango ] ✓ induction H0.
[rango ] ❌ apply LocmapFacts.lessdef_set, H.
[rango ] ✓ +
[rango ] ❌ apply Locmap.lessdef_set.
[rango ] ❌ unfold Val.lessdef.
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ induction ls1; simpl; intros; auto.
✓ -
❌ econstructor.
✓ unfold locmap_lessdef in *.
✓ intros.
❌ apply Val.lessdef_conv with (f := Fundef.fundef).
❌ destruct (Val.compare l l0); simpl; auto with typing.
✓ replace l0 with l.
❌ auto with locmap_type.
❌ apply (H l).
✓ +
❌ unfold Val.lessdef; intros [[] ? ?].
❌ unfold locmap.
❌ destruct (H0 l).
```

### `dests_disjoint_cons_right` — opener+rango: **실패** · plain SFT: **dead**
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
**opener+rango:**
```
[opener] ✓ induction m1; simpl.
[rango ] ✓ split; intros.
[rango ] ❌ elim H; intros; auto.
[rango ] ✓ unfold dests_disjoint in H.
[rango ] ✓ split.
[rango ] ✓ red; intros.
[rango ] ❌ rewrite map_nil in H.
[rango ] ✓ unfold list_disjoint in *.
[rango ] ✓ intros.
[rango ] ✓ inversion H0.
[rango ] ✓ tauto.
[rango ] ✓ firstorder.
[rango ] ❌ destruct H.
[rango ] ✓ intros.
[rango ] ❌ rewrite dests_disjoint_cons_left.
[rango ] ✓ unfold list_disjoint.
[rango ] ✓ unfold dests_disjoint.
[rango ] ✓ simpl.
... (총 23스텝)
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ unfold dests_disjoint, list_disjoint.
✓ simpl; intros; split; intros.
✓ split.
✓ auto.
✓ firstorder.
❌ destruct H.
❌ intro; rewrite dests_decomp in H0; destruct H0.
```

### `ptd_cost_build_from_ptl` — opener+rango: **실패** · plain SFT: **dead**
**GOLD 전문:**
```coq
Proof.
destruct ptlz=>//.
apply eq_add_S.
rewrite -ptd_cost_build_from_pt /=.
ring.
Qed.
```
**opener+rango:**
```
[opener] ✓ destruct ptlz=>//.
[rango ] ❌ rewrite /ptdlz_cost/ptd_cost /=.
[rango ] ✓ -
[rango ] ✓ simpl.
[rango ] ❌ exact (ptd_cost_build_from_pt _ _ ptol ptolz).
[rango ] ❌ by rewrite -ptd_cost_build_from_pt .
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ destruct ptlz as [|???? pt]=>//=.
❌ apply ptd_cost_build_from_pt.
❌ by rewrite -ptd_cost_build_from_pt.
```

### `pres_sem_shift` — opener+rango: **실패** · plain SFT: **dead**
**GOLD 전문:**
```coq
Proof.
intros.
unfold shift_op_type, sem_shift in *.
DestructCases; auto with ty.
Qed.
```
**opener+rango:**
```
[opener] ✓ intros.
[opener] ✓ unfold shift_op_type; intros; try contradiction.
[rango ] ❌ rewrite <- H0 in H.
[rango ] ❌ rewrite H0 in H.
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ intros.
✓ unfold sem_shift in *.
✓ set (ty' := Cop.binarith_type (classify_binarith ty1 ty2)) in 
✓ destruct (classify_shift ty1 ty2); eauto using wt_val.
✓ -
✓ simpl in *.
❌ destruct v1; destruct v2; auto with typing.
✓ destruct v1; destruct v2; auto using wt_val.
✓ +
✓ congruence.
✓ +
✓ congruence.
✓ +
✓ congruence.
✓ +
✓ congruence.
```

### `eval_builtin_args_inject` — opener+rango: **실패** · plain SFT: **dead**
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
**opener+rango:**
```
[opener] ✓ intros.
[opener] ✓ inv H.
[rango ] ✓ -
[rango ] ✓ simpl.
[rango ] ❌ apply eval_builtin_arg_list_inject; auto with barg.
[rango ] ✓ destruct sp; simpl in *.
[rango ] ✓ 1,2 : intros.
[rango ] ✓ +
[rango ] ✓ eauto.
[rango ] ❌ found_proof_irrelevance.
[rango ] ✓ exists nil; split; auto with barg.
[rango ] ✓ constructor.
[rango ] ✓ +
[rango ] ✓ exists nil; split; auto with barg.
[rango ] ✓ constructor.
[rango ] ✓ +
[rango ] ✓ exists nil; split; auto with barg.
[rango ] ✓ constructor.
... (총 22스텝)
```
**plain SFT→GRPO:**
```
✓ Proof.
❌ induction 1; intros SP GL RS MI K L0; simpl in *.
❌ induction 1; intros SU GL RS MI H; simpl in H.
❌ induction 1; intros SP GL RS MI K DR; simpl in K DR.
```

### `traceinf_sim_refl` — opener+rango: **실패** · plain SFT: **dead**
**GOLD 전문:**
```coq
Proof.
cofix COINDHYP; intros.
destruct T.
constructor.
apply COINDHYP.
Qed.
```
**opener+rango:**
```
[opener] ✓ destruct T; simpl.
[rango ] ✓ constructor.
[rango ] ❌ constructor.
[rango ] ✓ auto.
[rango ] ❌ constructor.
[rango ] ✓ elim e.
[rango ] ✓ subst.
[rango ] ❌ constructor.
```
**plain SFT→GRPO:**
```
✓ Proof.
❌ induction T using traceinf_ind; simpl; constructor; eauto.
❌ unfold traceinf.
✓ destruct T; simpl.
✓ auto.
❌ unfold traceinf_sim; auto.
✓ constructor.
✓ auto.
❌ red; reflexivity.
✓ auto.
❌ constructor.
❌ constructor.
```

### `ZOmod_eq` — opener+rango: **실패** · plain SFT: **dead**
**GOLD 전문:**
```coq
Proof.
intros a b.
rewrite (Z.quot_rem' a b) at 2.
ring.
Qed.
```
**opener+rango:**
```
[opener] ✓ intros.
[opener] ✓ destruct b; simpl.
[rango ] ❌ apply Z.mod_small.
[rango ] ❌ ring.
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ intros a b.
❌ destruct (Zdec_eq a b) as [?|?].
❌ destruct (Z.rem_spec a b) as [H|[H|H]].
✓ unfold Z.rem.
✓ unfold Z.quotrem.
❌ fold (quot a b).
✓ destruct a.
✓ -
✓ reflexivity.
✓ -
✓ destruct b.
✓ +
✓ reflexivity.
✓ +
✓ destruct (N.pos p0) eqn:des ; try easy.
✓ unfold N.pos_div_eucl.
❌ fold pos_div_eucl.
... (총 21스텝)
```

### `type_code_complete` — opener+rango: **실패** · plain SFT: **dead**
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
**opener+rango:**
```
[opener] ✓ intros.
[opener] ❌ inv H.
[rango ] ❌ pose (R := fun (c opte (pc':positive)) => match pc' with Ok _ 
[rango ] ✓ destruct (fn_code f) as [s| ].
[rango ] ✓ eauto; intros.
[rango ] ✓ exists e.
[rango ] ✓ constructor; auto.
[rango ] ❌ unfold type_code; apply PTree.gempty.
[rango ] ❌ apply PTree.type_code_sound; auto.
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ intros te e TYCODE.
❌ revert te.
❌ revert te; induction 1 as [e e|te IH] using S.solve_ind; intro
```

### `assign_variables_incr` — opener+rango: **실패** · plain SFT: **dead**
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
**opener+rango:**
```
[opener] ✓ induction vars; intros until sz'.
[rango ] ✓ destruct 1.
[rango ] ✓ apply Z.le_trans with sz; auto.
[rango ] ✓ apply Z.le_refl.
[rango ] ✓ simpl in TRANSL.
[rango ] ✓ destruct (Z.eq_dec sz sz').
[rango ] ✓ subst.
[rango ] ✓ apply Z.le_refl.
[rango ] ❌ apply Z.neq_le_incl; auto.
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ induction vars; simpl; intros.
✓ inv H; auto.
✓ lia.
✓ eapply IHvars; auto.
❌ apply assign_variable_eq_right2.
❌ apply H.
✓ inv H; auto.
✓ eauto.
❌ rewrite H1.
✓ auto.
✓ auto.
✓ eauto.
✓ eauto.
✓ eauto.
✓ eauto.
✓ eauto.
✓ destruct a; auto.
... (총 19스텝)
```

### `Zdigit_ge_Zpower_pos` — opener+rango: **실패** · plain SFT: **dead**
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
**opener+rango:**
```
[opener] ✓ intros.
[opener] ✓ destruct e; simpl.
[rango ] ❌ now case (Zdigit n k).
[rango ] ✓ case H; intros.
[rango ] ❌ easy.
[rango ] ✓ apply Z.le_antisymm.
[rango ] ❌ eapply Zdigit_le_0; eauto.
[rango ] ❌ rewrite (Zdigit_lt _ _ (Zlt_0_1 n)) at 1.
```
**plain SFT→GRPO:**
```
✓ Proof.
✓ intros e n Hk.
✓ induction (Z.abs_nat e) ; intros k.
✓ destruct Hk.
✓ intros Hk.
✓ change (Zdigit 0 k) with 0.
❌ rewrite Z2Z.inj_lt.
✓ destruct Hk.
✓ destruct (Z.le_gt_cases e n) as [H1|H1].
✓ apply (Zle_gt_trans e k); auto with zarith.
❌ apply Zle_minus_le_0.
❌ now apply Zle_le_trans with (Zpower beta n).
❌ apply le_Z_trans with n.
```

---
## 8. 핵심 결론
- **opener+rango 32% ≈ plain 34% = parity.** opener·subgoal·조합 모두 천장 ~34%.
- opener는 90% 잘 열지만, **롤아웃 병목은 열기가 아니라 닫기**. 닫기는 이 정리에 어느 lemma를 어떤 순서로 쓰는지(도메인 지식·증명 경로)인데 1.3B가 모름.
- 열기(opener)·닫기(subgoal)를 각각/동시에 고쳐도 무효 = 직렬 벽 + capacity 한계.
- **진짜 레버 = 더 큰 executor(7B).** opener/subgoal 방향은 여기서 종료.