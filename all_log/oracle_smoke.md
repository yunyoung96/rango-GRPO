# Oracle-prefix teacher-forcing ablation — `rango`

> 각 target×prefix에서 oracle prefix(gold) 상태 → retrieval+생성 → gold와 비교.

> exact-match(정규화 문자열)은 **하한**(다른 유효 tactic 미인정). nbest=8


---
# Summary

- 총 (target,prefix) 스텝: **4**
- **top-1 exact-match**: 0/4 = **0.0%**
- **top-8 exact-match**: 2/4 = **50.0%**

## prefix 위치별 top-1 (0..9, 10=10+)

| pos | top1 | n | rate |
|---|---|---|---|
| 1 | 0 | 3 | 0.0% |
| 2 | 0 | 1 | 0.0% |

## buchberger-theories-Bar.v · proof#0 — `Definition iwpath_sup_refl (x : A) (a : forall c : B x, IW I A B i j (j x c)) : iwpath_sup (x; (a, a)) (apD10 1) = idpath.`  (3 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (A : Type) (P : Pred A) (xs bs : list A),
ExistsL A P bs -> ExistsL A P (xs ++ bs)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A P xs; elim xs; simpl in |- *; auto`
- **생성 top5**: `intros`(-0.93) · `intros`(-2.69) · `intros`(-2.93) · `reflexivity`(-3.18) · `reflexivity`(-3.64)

## buchberger-theories-Bar.v · proof#1 — `Definition IWPath_ind_refl : forall l a, P (l ; (a, a)) idpath.`  (4 steps)


### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (A : Type) (P : Pred A) (xs bs cs : list A),
ExistsL A P (xs ++ bs) -> ExistsL A P (xs ++ cs ++ bs)`
- **retrieval 증명 top1**: `Definition iwpath_sup_refl (x : A) (a : forall c : B x, IW I A B i j (j x c)) : iwpath_sup`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A P xs; elim xs; simpl in |- *; auto`
- **생성 top5**: `intros`(-2.30) · `intros`(-2.66) · `intros A P l a`(-3.35) · `intros A P xs bs cs`(-3.83) · `intros A P xs bs cs`(-4.57)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a : A) (l : list A),
(forall bs cs : list A, ExistsL A P (l ++ bs) -> ExistsL A P (l ++ cs ++ bs)) ->
forall bs cs : list A,
ExistsL A P (a :: l ++ bs) -> ExistsL A P (a :: l ++ cs ++ bs)`
- **retrieval 증명 top1**: `Definition iwpath_sup_refl (x : A) (a : forall c : B x, IW I A B i j (j x c)) : iwpath_sup`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros a l H' bs cs H'0; inversion H'0; auto`
- **생성 top5**: `-`(-4.67) · `intros a l IHl bs cs H`(-6.12) · `intros a l Hrec bs cs H`(-6.21) · `intros a l Hrec l1 l2 H`(-6.32) · `intros a l IHl bs cs Ex`(-6.53)

## buchberger-theories-Bar.v · proof#2 — `Definition IWPath_ind_beta_iwpath_sup (x : A') (h : forall y : B' x, IWPath (j' x y)) : IWPath_ind _ (iwpath_sup x h) = S x h (fun c => IWPath_ind _ (`  (3 steps)


### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (A : Type) (R : Rel A) (xs bs : list A),
GoodR A R bs -> GoodR A R (xs ++ bs)`
- **retrieval 증명 top2**: `Definition iwpath_sup_refl (x : A) (a : forall c : B x, IW I A B i j (j x c)) : iwpath_sup` ; `Definition IWPath_ind_refl : forall l a, P (l ; (a, a)) idpath. Proof. intros A P xs; elim`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A R xs; elim xs; simpl in |- *; auto`
- **생성 top5**: `intros`(-2.95) · `intros A R xs; elim xs; simpl in |- *; auto`(-3.31) · `intros; reflexivity`(-3.84) · `intros A R xs bs; elim xs; simpl in |- *; auto`(-3.88) · `intros A R xs`(-4.26)
