# Oracle-prefix teacher-forcing ablation — `rango`

> 각 target×prefix에서 oracle prefix(gold) 상태 → retrieval+생성 → gold와 비교.

> exact-match(정규화 문자열)은 **하한**(다른 유효 tactic 미인정). nbest=8


---
# Summary

- 총 (target,prefix) 스텝: **337**
- **top-1 exact-match**: 27/337 = **8.0%**
- **top-8 exact-match**: 78/337 = **23.1%**

## prefix 위치별 top-1 (0..9, 10=10+)

| pos | top1 | n | rate |
|---|---|---|---|
| 0 | 3 | 27 | 11.1% |
| 1 | 2 | 57 | 3.5% |
| 2 | 1 | 44 | 2.3% |
| 3 | 4 | 33 | 12.1% |
| 4 | 3 | 27 | 11.1% |
| 5 | 4 | 19 | 21.1% |
| 6 | 1 | 18 | 5.6% |
| 7 | 0 | 17 | 0.0% |
| 8 | 1 | 15 | 6.7% |
| 9 | 1 | 13 | 7.7% |
| 10 | 7 | 67 | 10.4% |

## buchberger-theories-Bar.v · proof#0 — `Definition iwpath_sup_refl (x : A) (a : forall c : B x, IW I A B i j (j x c)) : iwpath_sup (x; (a, a)) (apD10 1) = idpath.`  (3 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (A : Type) (P : Pred A) (xs bs : list A),
ExistsL A P bs -> ExistsL A P (xs ++ bs)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A P xs; elim xs; simpl in |- *; auto`
- **생성 top5**: `intros`(-0.69) · `intros`(-3.08) · `intros`(-3.35) · `reflexivity`(-3.45) · `induction xs`(-4.09)

## buchberger-theories-Bar.v · proof#1 — `Definition IWPath_ind_refl : forall l a, P (l ; (a, a)) idpath.`  (4 steps)


### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (A : Type) (P : Pred A) (xs bs cs : list A),
ExistsL A P (xs ++ bs) -> ExistsL A P (xs ++ cs ++ bs)`
- **retrieval 증명 top1**: `Definition iwpath_sup_refl (x : A) (a : forall c : B x, IW I A B i j (j x c)) : iwpath_sup`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A P xs; elim xs; simpl in |- *; auto`
- **생성 top5**: `intros`(-1.98) · `intros`(-2.78) · `intros A P l a`(-3.18) · `intros A P xs bs cs`(-3.56) · `intros A P xs`(-4.51)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a : A) (l : list A),
(forall bs cs : list A, ExistsL A P (l ++ bs) -> ExistsL A P (l ++ cs ++ bs)) ->
forall bs cs : list A,
ExistsL A P (a :: l ++ bs) -> ExistsL A P (a :: l ++ cs ++ bs)`
- **retrieval 증명 top1**: `Definition iwpath_sup_refl (x : A) (a : forall c : B x, IW I A B i j (j x c)) : iwpath_sup`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros a l H' bs cs H'0; inversion H'0; auto`
- **생성 top5**: `intros`(-4.60) · `-`(-4.68) · `intros a l Hrec bs cs H`(-5.04) · `intros a l Hrec bs cs`(-6.38) · `intros a l Hrec l bs cs H`(-6.56)

## buchberger-theories-Bar.v · proof#2 — `Definition IWPath_ind_beta_iwpath_sup (x : A') (h : forall y : B' x, IWPath (j' x y)) : IWPath_ind _ (iwpath_sup x h) = S x h (fun c => IWPath_ind _ (`  (3 steps)


### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (A : Type) (R : Rel A) (xs bs : list A),
GoodR A R bs -> GoodR A R (xs ++ bs)`
- **retrieval 증명 top2**: `Definition iwpath_sup_refl (x : A) (a : forall c : B x, IW I A B i j (j x c)) : iwpath_sup` ; `Definition IWPath_ind_refl : forall l a, P (l ; (a, a)) idpath. Proof. intros A P xs; elim`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A R xs; elim xs; simpl in |- *; auto`
- **생성 top5**: `intros`(-3.32) · `intros A R xs; elim xs; simpl in |- *; auto`(-3.33) · `intros A R xs`(-3.65) · `intros A R xs bs; elim xs; simpl in |- *; auto`(-3.95) · `intros A R xs bs`(-3.98)

## buchberger-theories-Bar.v · proof#3 — `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)) <~> a = b.`  (4 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (A : Type) (R : Rel A) (xs bs cs : list A),
GoodR A R (xs ++ bs) -> GoodR A R (xs ++ cs ++ bs)`
- **retrieval 증명 top2**: `Definition IWPath_ind_beta_iwpath_sup (x : A') (h : forall y : B' x, IWPath (j' x y)) : IW` ; `Definition IWPath_ind_refl : forall l a, P (l ; (a, a)) idpath. Proof. intros A P xs; elim`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A R xs bs cs; elim xs; simpl in |- *; auto`
- **생성 top5**: `intros`(-2.39) · `intros A R xs; elim xs; simpl in |- *; auto`(-3.57) · `intros A R xs`(-3.88) · `intros A R xs; elim xs; simpl in |- *`(-4.25) · `intros A R xs bs cs H`(-4.29)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a : A) (l : list A),
(GoodR A R (l ++ bs) -> GoodR A R (l ++ cs ++ bs)) ->
GoodR A R (a :: l ++ bs) -> GoodR A R (a :: l ++ cs ++ bs)`
- **retrieval 증명 top2**: `Definition IWPath_ind_refl : forall l a, P (l ; (a, a)) idpath. Proof. intros A P xs; elim` ; `Definition IWPath_ind_beta_iwpath_sup (x : A') (h : forall y : B' x, IWPath (j' x y)) : IW`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros a l H' H'0; inversion H'0; simpl in |- *; auto`
- **생성 top5**: `intros a l H' bs cs H'0; inversion H'0; auto`(-3.24) · `intros a l H' H'0; inversion H'0; auto`(-3.88) · `intros a l H' bs' cs' H'0; inversion H'0; auto`(-4.21) · `intros a l H' h; inversion h; auto`(-5.24) · `intros x l H' H'0; inversion H'0; auto`(-5.34)

## buchberger-theories-Bar.v · proof#4 — `Definition equiv_path_hfiber_index (l : I) (a b : IW I A B i j l) : iw_to_hfiber_index l a = iw_to_hfiber_index l b <~> hfiber i' (l; (a, b)).`  (3 steps)


### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (A B : Type) (P : Pred A) (S : Pred B) (f : A -> B),
(forall a : A, P a -> S (f a)) ->
forall l : list A, ExistsL A P l -> ExistsL B S (map f l)`
- **retrieval 증명 top2**: `Definition IWPath_ind_refl : forall l a, P (l ; (a, a)) idpath. Proof. intros A P xs; elim` ; `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A B P S f H' l H'0; elim H'0; simpl in |- *; auto`
- **생성 top5**: `intros A R xs bs cs; elim xs; simpl in |- *; auto`(-5.07) · `intros`(-5.09) · `intros A B P S f H' l H'0; elim H'0; simpl in |- *; auto`(-6.31) · `intros A B P S f H' l H'0`(-6.34) · `intros A B P S f H' l; elim l; simpl in |- *; auto`(-6.52)

## buchberger-theories-Bar.v · proof#5 — `Global Instance ishprop_iwtype `{Funext} (I : Type) (A : Type) (B : A -> Type) (i : A -> I) (j : forall x, B x -> I) {h : IsEmbedding i} : forall x, I`  (5 steps)


### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (A B : Type) (R : Rel A) (S : Rel B) (f : A -> B),
(forall a b : A, R a b -> S (f a) (f b)) ->
forall l : list A, GoodR A R l -> GoodR B S (map f l)`
- **retrieval 증명 top2**: `Definition equiv_path_hfiber_index (l : I) (a b : IW I A B i j l) : iw_to_hfiber_index l a` ; `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A B R S f H' l H'0; elim H'0; simpl in |- *; auto`
- **생성 top5**: `intros`(-3.46) · `intros A B R S f H' l H'0`(-4.14) · `intros A B`(-4.14) · `intros A B R S f H' l H'0; elim H'0; simpl in |- *; auto`(-4.36) · `intros`(-4.50)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a : A) (l0 : list A),
ExistsL A (fun x : A => R x a) l0 -> GoodR B S (f a :: map f l0)`
- **retrieval 증명 top2**: `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)` ; `Definition equiv_path_hfiber_index (l : I) (a b : IW I A B i j l) : iw_to_hfiber_index l a`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros a l0 H'1; apply FoundG; auto`
- **생성 top5**: `intros a l' H'1; elim H'1; simpl in |- *; auto`(-2.27) · `intros a l' H'1; inversion H'1; simpl in |- *; auto`(-2.59) · `intros a l' H'1; inversion H'1; auto`(-3.55) · `intros a l' H'1`(-3.62) · `intros a l0 H'1; elim H'1; simpl in |- *; auto`(-4.07)

### step 3 — ❌miss
- **goal(입력 상태)**: `ExistsL B (fun x : B => S x (f a)) (map f l0)`
- **retrieval 증명 top2**: `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)` ; `Definition IWPath_ind_beta_iwpath_sup (x : A') (h : forall y : B' x, IWPath (j' x y)) : IW`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `apply subPredExistsL with (P := fun x : A => R x a); auto`
- **생성 top5**: `induction l0`(-2.96) · `apply ExistsL_map; auto`(-3.11) · `elim H'1; simpl in |- *; auto`(-3.31) · `apply ExistsL_map`(-3.46) · `induction l0; simpl in |- *; auto`(-3.47)

## buchberger-theories-Bar.v · proof#6 — `Class IsGraph (A : Type) := { Hom : A -> A -> Type }.`  (11 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (A B : Type) (R : Rel A) (S : Rel B) (f : A -> B),
(forall a b : A, R a b -> S (f a) (f b)) ->
(forall b : B, {a : A | b = f a}) ->
forall l : list A, GRBar A R l -> GRBar B S (map f l)`
- **retrieval 증명 top2**: `Global Instance ishprop_iwtype `{Funext} (I : Type) (A : Type) (B : A -> Type) (i : A -> I` ; `Definition equiv_path_hfiber_index (l : I) (a b : IW I A B i j l) : iw_to_hfiber_index l a`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A B R S f H' H'0 l H'1; elim H'1; simpl in |- *; auto`
- **생성 top5**: `intros`(-3.29) · `intros A B R S f H' l H'0`(-3.98) · `intros A B R S f H' l H'0; elim H'0; simpl in |- *; auto`(-4.45) · `intros A B`(-4.88) · `intros`(-5.44)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall l0 : list A, GoodR A R l0 -> GRBar B S (map f l0) / forall l0 : list A,
(forall a : A, Bar A (GoodR A R) (a :: l0)) ->
(forall a : A, GRBar B S (f a :: map f l0)) -> GRBar B S (map f l0)`
- **retrieval 증명 top2**: `Global Instance ishprop_iwtype `{Funext} (I : Type) (A : Type) (B : A -> Type) (i : A -> I` ; `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros l0 H'2`
- **생성 top5**: `intros l0 H'2; elim H'2; simpl in |- *; auto`(-2.07) · `-`(-2.28) · `intros l' H'2; elim H'2; simpl in |- *; auto`(-2.81) · `intros l0 H'2; elim H'2; auto`(-4.02) · `+`(-4.28)

### step 3 — ❌miss
- **goal(입력 상태)**: `GRBar B S (map f l0) / forall l0 : list A,
(forall a : A, Bar A (GoodR A R) (a :: l0)) ->
(forall a : A, GRBar B S (f a :: map f l0)) -> GRBar B S (map f l0)`
- **retrieval 증명 top2**: `Global Instance ishprop_iwtype `{Funext} (I : Type) (A : Type) (B : A -> Type) (i : A -> I` ; `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `red in |- *; apply Base; auto`
- **생성 top5**: `elim H'2; simpl in |- *; auto`(-3.19) · `-`(-3.54) · `unfold GRBar in |- *`(-4.54) · `elim H'2; auto`(-4.66) · `induction l0`(-4.73)

### step 4 — ❌miss
- **goal(입력 상태)**: `GoodR B S (map f l0) / forall l0 : list A,
(forall a : A, Bar A (GoodR A R) (a :: l0)) ->
(forall a : A, GRBar B S (f a :: map f l0)) -> GRBar B S (map f l0)`
- **retrieval 증명 top2**: `Global Instance ishprop_iwtype `{Funext} (I : Type) (A : Type) (B : A -> Type) (i : A -> I` ; `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `unfold GRBar in |- *`
- **생성 top5**: `red in |- *`(-3.21) · `red in |- *; apply Map; auto`(-3.63) · `red in |- *; apply Base; auto`(-3.63) · `elim H'2; simpl in |- *; auto`(-4.10) · `red in |- *; apply Good; auto`(-4.20)

### step 5 — ❌miss
- **goal(입력 상태)**: `GoodR B S (map f l0) / forall l0 : list A,
(forall a : A, Bar A (GoodR A R) (a :: l0)) ->
(forall a : A, GRBar B S (f a :: map f l0)) -> GRBar B S (map f l0)`
- **retrieval 증명 top2**: `Global Instance ishprop_iwtype `{Funext} (I : Type) (A : Type) (B : A -> Type) (i : A -> I` ; `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `apply subRelGoodR with (R := R); auto`
- **생성 top5**: `red in |- *`(-2.60) · `elim H'2; simpl in |- *; auto`(-2.95) · `red in |- *; apply Base; auto`(-3.00) · `unfold GoodR in |- *`(-3.27) · `red in |- *; apply Map; auto`(-4.22)

### step 6 — ❌miss
- **goal(입력 상태)**: `forall l0 : list A,
(forall a : A, Bar A (GoodR A R) (a :: l0)) ->
(forall a : A, GRBar B S (f a :: map f l0)) -> GRBar B S (map f l0)`
- **retrieval 증명 top2**: `Global Instance ishprop_iwtype `{Funext} (I : Type) (A : Type) (B : A -> Type) (i : A -> I` ; `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros l0 H'2 H'3; red in |- *; apply Ind; auto`
- **생성 top5**: `intros l0 H'2 H'3`(-1.86) · `intros l0 H'2 H'3; elim H'3; simpl in |- *; auto`(-2.57) · `intros l0 H'3 H'4`(-3.25) · `intros l0 H'3 H'4; elim H'4; simpl in |- *; auto`(-3.61) · `intros l' H'2 H'3`(-3.75)

### step 7 — ❌miss
- **goal(입력 상태)**: `forall a : B, Bar B (GoodR B S) (a :: map f l0)`
- **retrieval 증명 top2**: `Global Instance ishprop_iwtype `{Funext} (I : Type) (A : Type) (B : A -> Type) (i : A -> I` ; `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros a; case (H'0 a); auto`
- **생성 top5**: `intros b; red in |- *`(-3.40) · `intros b; red in |- *; apply Base; auto`(-3.52) · `intro b; red in |- *`(-3.54) · `intros b H'4`(-3.78) · `intros b; red in |- *; apply Ind; auto`(-4.13)

### step 8 — ❌miss
- **goal(입력 상태)**: `forall x : A, a = f x -> Bar B (GoodR B S) (a :: map f l0)`
- **retrieval 증명 top2**: `Global Instance ishprop_iwtype `{Funext} (I : Type) (A : Type) (B : A -> Type) (i : A -> I` ; `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros x H'4; rewrite H'4; auto`
- **생성 top5**: `intros x H'4`(-3.69) · `intros a0 H'4; red in |- *`(-4.28) · `intros x H'4; red in |- *`(-4.34) · `intros a0 H'4; red in |- *; apply Ind; auto`(-4.70) · `intros x H'4; red in |- *; apply Base; auto`(-5.10)

### step 9 — ❌miss
- **goal(입력 상태)**: `Bar B (GoodR B S) (f x :: map f l0)`
- **retrieval 증명 top2**: `Global Instance ishprop_iwtype `{Funext} (I : Type) (A : Type) (B : A -> Type) (i : A -> I` ; `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `unfold GRBar in H'3; apply H'3; auto`
- **생성 top5**: `red in |- *; apply Base; auto`(-2.24) · `apply Base; auto`(-2.43) · `red in |- *`(-3.43) · `unfold GRBar in |- *`(-3.65) · `apply subRelGoodR with (R := S); auto`(-4.48)

## buchberger-theories-Bar.v · proof#7 — `Notation "a $-> b" := (Hom a b).`  (3 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (A : Type) (R : Rel A) (l : list A),
GRBar A R l -> forall a : A, GRBar A R (a :: l)`
- **retrieval 증명 top2**: `Class IsGraph (A : Type) := { Hom : A -> A -> Type }. Proof. intros A B R S f H' H'0 l H'1` ; `Global Instance ishprop_iwtype `{Funext} (I : Type) (A : Type) (B : A -> Type) (i : A -> I`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A R l H'; elim H'; auto`
- **생성 top5**: `intros A R xs a; elim xs; simpl in |- *; auto`(-3.13) · `intros A R xs a`(-3.16) · `intros`(-3.72) · `intros A R xs; elim xs; simpl in |- *; auto`(-4.06) · `intros A R l H' a`(-4.13)

## buchberger-theories-Buch.v · proof#0 — `Global Instance is1natural_comp {A B : Type} `{IsGraph A} `{Is1Cat B} {F G K : A -> B} `{!Is0Functor F} `{!Is0Functor G} `{!Is0Functor K} (gamma : G $`  (3 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall Q : list (poly A0 eqA ltM), stable Q Q`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `auto`
- **생성 top5**: `intros`(-1.85) · `intro Q`(-2.99) · `intros Q`(-3.33) · `intros`(-3.43) · `intros gamma alpha`(-4.06)

## buchberger-theories-Buch.v · proof#1 — `Global Instance is1natural_prewhisker {A B C : Type} {F G : B -> C} (K : A -> B) `{IsGraph A, Is01Cat B, Is1Cat C, !Is0Functor F, !Is0Functor G, !Is0F`  (3 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall Q y R : list (poly A0 eqA ltM), stable Q y -> stable y R -> stable Q R`
- **retrieval 증명 top1**: `Global Instance is1natural_comp {A B : Type} `{IsGraph A} `{Is1Cat B} {F G K : A -> B} `{!`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros Q y R H' H'0; inversion H'; inversion H'0; auto`
- **생성 top5**: `intros`(-1.74) · `auto`(-2.34) · `intros`(-3.26) · `intros Q y R`(-3.86) · `unfold stable`(-3.98)

## buchberger-theories-Buch.v · proof#2 — `Global Instance is1natural_postwhisker {A B C : Type} {F G : A -> B} (K : B -> C) `{IsGraph A, Is1Cat B, Is1Cat C, !Is0Functor F, !Is0Functor G, !Is0F`  (3 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall Q R : list (poly A0 eqA ltM), stable R Q -> stable Q R`
- **retrieval 증명 top2**: `Global Instance is1natural_prewhisker {A B C : Type} {F G : B -> C} (K : A -> B) `{IsGraph` ; `Global Instance is1natural_comp {A B : Type} `{IsGraph A} `{Is1Cat B} {F G K : A -> B} `{!`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros Q R H'; elim H'; auto`
- **생성 top5**: `intros Q y R H' H'0; inversion H'; inversion H'0; auto`(-1.15) · `intros Q y R H'; inversion H'; inversion H'0; auto`(-2.28) · `intros Q y R H'`(-3.41) · `intros Q y R H' H'0`(-3.53) · `intros`(-4.72)

## buchberger-theories-Buch.v · proof#3 — `Definition nattrans_comp {A B : Type} {F G K : A -> B} `{IsGraph A, Is1Cat B, !Is0Functor F, !Is0Functor G, !Is0Functor K} : NatTrans G K -> NatTrans `  (5 steps)


### step 0 — ❌miss
- **goal(입력 상태)**: `forall (a : poly A0 eqA ltM) (Q : list (poly A0 eqA ltM)),
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec a Q ->
stable Q (addEnd A A0 eqA n ltM a Q)`
- **retrieval 증명 top2**: `Global Instance is1natural_comp {A B : Type} `{IsGraph A} `{Is1Cat B} {F G K : A -> B} `{!` ; `Global Instance is1natural_postwhisker {A B C : Type} {F G : A -> B} (K : B -> C) `{IsGrap`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `Proof using os minusA invA divA cs A1`
- **생성 top5**: `Proof`(-0.17) · `Proof`(-2.41) · `Proof`(-5.93) · `Proof`(-5.94) · `intros gamma alpha beta`(-9.13)

### step 1 — ❌miss
- **goal(입력 상태)**: `forall (a : poly A0 eqA ltM) (Q : list (poly A0 eqA ltM)),
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec a Q ->
stable Q (addEnd A A0 eqA n ltM a Q)`
- **retrieval 증명 top2**: `Global Instance is1natural_comp {A B : Type} `{IsGraph A} `{Is1Cat B} {F G K : A -> B} `{!` ; `Global Instance is1natural_postwhisker {A B C : Type} {F G : A -> B} (K : B -> C) `{IsGrap`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros a Q H'0; apply stable0; auto`
- **생성 top5**: `intros gamma gamma' H'`(-6.91) · `intros gamma alpha H'; elim H'`(-7.37) · `intros gamma gamma' H'; elim H'; auto`(-7.78) · `intros gamma gamma' H'; elim H'`(-7.99) · `intros gamma gamma' H'; inversion H'`(-8.18)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall a0 : poly A0 eqA ltM,
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec a0 (addEnd A A0 eqA n ltM a Q) ->
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec a0 Q`
- **retrieval 증명 top2**: `Global Instance is1natural_comp {A B : Type} `{IsGraph A} `{Is1Cat B} {F G K : A -> B} `{!` ; `Global Instance is1natural_postwhisker {A B C : Type} {F G : A -> B} (K : B -> C) `{IsGrap`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros a0 H'1`
- **생성 top5**: `intros b H'1`(-3.56) · `intros b H'1; apply stable0; auto`(-4.14) · `intros b H'1; inversion H'1; auto`(-4.56) · `intros b H'1; inversion H'0; inversion H'1; auto`(-4.78) · `intros b H'1; inversion H'1`(-5.29)

### step 3 — ❌miss
- **goal(입력 상태)**: `Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec a0 Q`
- **retrieval 증명 top2**: `Global Instance is1natural_comp {A B : Type} `{IsGraph A} `{Is1Cat B} {F G K : A -> B} `{!` ; `Global Instance is1natural_postwhisker {A B C : Type} {F G : A -> B} (K : B -> C) `{IsGrap`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply Cb_trans with (b := a) (1 := cs); auto`
- **생성 top5**: `inversion H'0; inversion H'1; auto`(-3.95) · `inversion H'0`(-4.36) · `inversion H'0; inversion H'1`(-4.44) · `elim H'1; auto`(-4.72) · `inversion H'1; inversion H'0; auto`(-5.40)

## buchberger-theories-Buch.v · proof#4 — `Definition nattrans_prewhisker {A B C : Type} {F G : B -> C} `{IsGraph A, Is1Cat B, Is1Cat C, !Is0Functor F, !Is0Functor G} (alpha : NatTrans F G) (K `  (3 steps)


### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (A2 : Type) (p q : list A2) (a : A2),
A2 -> incl p q -> In a p -> In a q`
- **retrieval 증명 top2**: `Global Instance is1natural_comp {A B : Type} `{IsGraph A} `{Is1Cat B} {F G K : A -> B} `{!` ; `Definition nattrans_comp {A B : Type} {F G K : A -> B} `{IsGraph A, Is1Cat B, !Is0Functor `
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `auto`
- **생성 top5**: `intros`(-2.40) · `auto`(-2.85) · `intros; apply alpha; auto`(-5.16) · `intros; apply alpha`(-6.54) · `intros A2 p q a Q H' H'0`(-7.19)

## buchberger-theories-Buch.v · proof#5 — `Definition is1natural_homotopic {A B : Type} `{Is01Cat A} `{Is1Cat B} {F : A -> B} `{!Is0Functor F} {G : A -> B} `{!Is0Functor G} {alpha : F $=> G} (g`  (9 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (P : list (poly A0 eqA ltM)) (a b : poly A0 eqA ltM),
reds a b P -> reds b a P`
- **retrieval 증명 top2**: `Definition nattrans_comp {A B : Type} {F G K : A -> B} `{IsGraph A, Is1Cat B, !Is0Functor ` ; `Global Instance is1natural_comp {A B : Type} `{IsGraph A} `{Is1Cat B} {F G K : A -> B} `{!`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros P a b H'; elim H'; simpl in |- *; auto`
- **생성 top5**: `auto`(-2.86) · `intros p Q R H'`(-5.17) · `intros P Q R H'`(-5.17) · `intros Q R H'; elim H'; auto`(-5.24) · `intros P Q R H'; elim H'; auto`(-5.26)

### step 2 — 🔶topk
- **goal(입력 상태)**: `forall (P0 : list (poly A0 eqA ltM)) (a0 b0 : poly A0 eqA ltM),
red A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec
  (spolyp A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM ltM_dec`
- **retrieval 증명 top2**: `Definition nattrans_comp {A B : Type} {F G K : A -> B} `{IsGraph A, Is1Cat B, !Is0Functor ` ; `Global Instance is1natural_comp {A B : Type} `{IsGraph A} `{Is1Cat B} {F G K : A -> B} `{!`
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum`
- **gold**: `intros P0 a0 b0 H'0`
- **생성 top5**: `-`(-2.98) · `intros P0 a0 b0 H'0`(-3.91) · `intros P0 a0 b0 H'0; inversion H'0; auto`(-4.27) · `intros P0 a0 b0 H'0; elim H'0; simpl in |- *; auto`(-4.73) · `+`(-4.73)

### step 3 — ❌miss
- **goal(입력 상태)**: `reds b0 a0 P0 / forall (P0 : list (poly A0 eqA ltM)) (a0 b0 c : poly A0 eqA ltM),
In c P0 ->
reds a0 c P0 ->
reds c a0 P0 ->
reds c b0 P0 ->
reds b0 c P0 ->
divp A A0 eqA multA divA n ltM
  (ppcp A A0`
- **retrieval 증명 top2**: `Definition nattrans_comp {A B : Type} {F G K : A -> B} `{IsGraph A, Is1Cat B, !Is0Functor ` ; `Global Instance is1natural_comp {A B : Type} `{IsGraph A} `{Is1Cat B} {F G K : A -> B} `{!`
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G`
- **gold**: `apply reds0; auto`
- **생성 top5**: `inversion H'0; auto`(-2.84) · `elim H'0; simpl in |- *; auto`(-3.42) · `elim H'0; auto`(-3.78) · `unfold reds in |- *`(-4.27) · `inversion H'0`(-4.46)

### step 4 — ❌miss
- **goal(입력 상태)**: `red A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec
  (spolyp A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM ltM_dec
     os b0 a0) P0 / forall (P0 : list (poly A0 eqA ltM)) (a0 b0`
- **retrieval 증명 top2**: `Definition nattrans_comp {A B : Type} {F G K : A -> B} `{IsGraph A, Is1Cat B, !Is0Functor ` ; `Global Instance is1natural_comp {A B : Type} `{IsGraph A} `{Is1Cat B} {F G K : A -> B} `{!`
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G`
- **gold**: `apply red_com; auto`
- **생성 top5**: `-`(-3.68) · `apply reds0; auto`(-3.85) · `apply reds1; auto`(-3.86) · `red in |- *`(-4.18) · `inversion H'0; auto`(-4.45)

### step 5 — ✅top1
- **goal(입력 상태)**: `forall (P0 : list (poly A0 eqA ltM)) (a0 b0 c : poly A0 eqA ltM),
In c P0 ->
reds a0 c P0 ->
reds c a0 P0 ->
reds c b0 P0 ->
reds b0 c P0 ->
divp A A0 eqA multA divA n ltM
  (ppcp A A0 A1 eqA plusA in`
- **retrieval 증명 top2**: `Definition nattrans_comp {A B : Type} {F G K : A -> B} `{IsGraph A, Is1Cat B, !Is0Functor ` ; `Global Instance is1natural_comp {A B : Type} `{IsGraph A} `{Is1Cat B} {F G K : A -> B} `{!`
- **retrieval premise top3**: `Lemma cmp_of_comparison_swap: forall c x, cmp_of_comparison (swap_comp` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `intros P0 a0 b0 c H'0 H'1 H'2 H'3 H'4 H'5`
- **생성 top5**: `intros P0 a0 b0 c H'0 H'1 H'2 H'3 H'4 H'5`(-2.82) · `intros P0 a0 b0 c H'0 H'1 H'2 H'3`(-3.20) · `intros P0 a0 b0 c H'0 H'1 H'2 H'3 H'4`(-3.28) · `intros P0 a0 b0 c H'0 H'1 H'2 H'3 H'4 H'5 H'6`(-3.68) · `intros`(-3.77)

### step 6 — ❌miss
- **goal(입력 상태)**: `reds b0 a0 P0`
- **retrieval 증명 top2**: `Definition nattrans_comp {A B : Type} {F G K : A -> B} `{IsGraph A, Is1Cat B, !Is0Functor ` ; `Global Instance is1natural_comp {A B : Type} `{IsGraph A} `{Is1Cat B} {F G K : A -> B} `{!`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma InFinEnumC_weaken : forall x l, In x l -> InFinEnumC x l.`
- **gold**: `apply reds1 with (c := c); auto`
- **생성 top5**: `apply reds0; auto`(-1.99) · `apply red_com; auto`(-2.39) · `apply reds_com; auto`(-3.20) · `apply reds1; auto`(-3.24) · `apply reds_com with c; auto`(-4.71)

### step 7 — ❌miss
- **goal(입력 상태)**: `divp A A0 eqA multA divA n ltM
  (ppcp A A0 A1 eqA plusA invA minusA multA divA cs n ltM b0 a0) c`
- **retrieval 증명 top2**: `Definition nattrans_comp {A B : Type} {F G K : A -> B} `{IsGraph A, Is1Cat B, !Is0Functor ` ; `Global Instance is1natural_comp {A B : Type} `{IsGraph A} `{Is1Cat B} {F G K : A -> B} `{!`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma InFinEnumC_weaken : forall x l, In x l -> InFinEnumC x l.`
- **gold**: `apply divp_ppc; auto`
- **생성 top5**: `apply red_com; auto`(-3.80) · `apply div_com; auto`(-3.91) · `apply divp_com; auto`(-3.98) · `elim H'5; simpl in |- *; auto`(-4.29) · `elim H'5; auto`(-4.55)

## buchberger-theories-Buch.v · proof#6 — `Definition issig_NatEquiv {A B : Type} `{IsGraph A} `{HasEquivs B} (F G : A -> B) `{!Is0Functor F, !Is0Functor G} : _ <~> NatEquiv F G := ltac:(issig)`  (2 steps)


### step 0 — ❌miss
- **goal(입력 상태)**: `cpRes -> list (poly A0 eqA ltM)`
- **retrieval 증명 top2**: `Definition is1natural_homotopic {A B : Type} `{Is01Cat A} `{Is1Cat B} {F : A -> B} `{!Is0F` ; `Definition nattrans_comp {A B : Type} {F G K : A -> B} `{IsGraph A, Is1Cat B, !Is0Functor `
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros H'; case H'; auto`
- **생성 top5**: `Proof`(-0.07) · `Proof`(-4.24) · `Proof using os`(-5.07) · `Proof using os minusA invA divA cs A1`(-5.31) · `Proof with auto`(-6.47)

## buchberger-theories-Buch.v · proof#7 — `Lemma nattrans_natequiv {A B : Type} `{IsGraph A} `{HasEquivs B} {F G : A -> B} `{!Is0Functor F, !Is0Functor G} : NatEquiv F G -> NatTrans F G.`  (4 steps)


### step 0 — ❌miss
- **goal(입력 상태)**: `poly A0 eqA ltM -> cpRes -> cpRes`
- **retrieval 증명 top2**: `Definition issig_NatEquiv {A B : Type} `{IsGraph A} `{HasEquivs B} (F G : A -> B) `{!Is0Fu` ; `Definition is1natural_homotopic {A B : Type} `{Is01Cat A} `{Is1Cat B} {F : A -> B} `{!Is0F`
- **retrieval premise top3**: `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ ` ; `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum`
- **gold**: `intros i H'; case H'`
- **생성 top5**: `Proof`(-0.24) · `Proof using os minusA invA divA cs A1`(-2.79) · `Proof using os minusA invA divA cs`(-4.68) · `Proof using os`(-4.85) · `Proof using os minusA invA divA cs A0 A1`(-6.43)

### step 1 — ❌miss
- **goal(입력 상태)**: `list (poly A0 eqA ltM) -> cpRes / list (poly A0 eqA ltM) -> cpRes`
- **retrieval 증명 top2**: `Definition issig_NatEquiv {A B : Type} `{IsGraph A} `{HasEquivs B} (F G : A -> B) `{!Is0Fu` ; `Definition is1natural_homotopic {A B : Type} `{Is01Cat A} `{Is1Cat B} {F : A -> B} `{!Is0F`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros H'0; exact (Keep (i :: H'0))`
- **생성 top5**: `-`(-2.29) · `auto`(-3.86) · `intros l; case l`(-4.20) · `intros l; case l; auto`(-4.76) · `intro l; case l`(-5.38)

### step 2 — ❌miss
- **goal(입력 상태)**: `list (poly A0 eqA ltM) -> cpRes`
- **retrieval 증명 top2**: `Definition issig_NatEquiv {A B : Type} `{IsGraph A} `{HasEquivs B} (F G : A -> B) `{!Is0Fu` ; `Definition is1natural_homotopic {A B : Type} `{Is01Cat A} `{Is1Cat B} {F : A -> B} `{!Is0F`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros H'0; exact (DontKeep (i :: H'0))`
- **생성 top5**: `intros l; case l`(-2.52) · `intros l`(-3.80) · `intros H'0`(-4.23) · `intros L; case L`(-4.62) · `intros i0`(-4.70)

## buchberger-theories-BuchAux.v · proof#0 — `Global Instance is0gpd_core {A : Type} `{HasEquivs A} : Is0Gpd (core A).`  (4 steps)


### step 0 — ❌miss
- **goal(입력 상태)**: `poly A0 eqA ltM -> list (poly A0 eqA ltM) -> list (poly A0 eqA ltM)`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros a H'0; elim H'0`
- **생성 top5**: `Proof`(-0.05) · `Proof`(-3.66) · `Proof`(-6.32) · `Proof`(-6.42) · `Proof`(-6.52)

### step 1 — 🔶topk
- **goal(입력 상태)**: `list (poly A0 eqA ltM) / poly A0 eqA ltM ->
list (poly A0 eqA ltM) -> list (poly A0 eqA ltM) -> list (poly A0 eqA ltM)`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `exact (a :: nil)`
- **생성 top5**: `-`(-1.79) · `exact a`(-2.20) · `exact []`(-2.94) · `+`(-3.04) · `exact a`(-3.05)

### step 2 — ❌miss
- **goal(입력 상태)**: `poly A0 eqA ltM ->
list (poly A0 eqA ltM) -> list (poly A0 eqA ltM) -> list (poly A0 eqA ltM)`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros b L1 Rec; exact (b :: Rec)`
- **생성 top5**: `intros`(-2.80) · `auto`(-4.10) · `intros b H'1 H'2`(-4.33) · `intros b H'1 H'2; exact (b :: H'1)`(-4.57) · `intros a0 H'1 H'2`(-4.82)

## buchberger-theories-BuchAux.v · proof#1 — `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A).`  (6 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (a b : poly A0 eqA ltM) (aL : list (poly A0 eqA ltM)),
In a (addEnd b aL) -> a = b \/ In a aL`
- **retrieval 증명 top1**: `Global Instance is0gpd_core {A : Type} `{HasEquivs A} : Is0Gpd (core A). intros a H'0; eli`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros a b aL; elim aL; simpl in |- *; auto`
- **생성 top5**: `intros a H'0; elim H'0`(-2.76) · `intros a H'; elim H'`(-3.90) · `intros a H'0; elim H'0`(-5.08) · `intros a b H'0; elim H'0`(-5.26) · `intros a H'0 b H'1; elim H'0`(-5.83)

### step 2 — ❌miss
- **goal(입력 상태)**: `b = a \/ False -> a = b \/ False / forall (a0 : poly A0 eqA ltM) (l : list (poly A0 eqA ltM)),
(In a (addEnd b l) -> a = b \/ In a l) ->
a0 = a \/ In a (addEnd b l) -> a = b \/ a0 = a \/ In a l`
- **retrieval 증명 top1**: `Global Instance is0gpd_core {A : Type} `{HasEquivs A} : Is0Gpd (core A). intros a H'0; eli`
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `intros H'; case H'; [ intros H'0; rewrite <- H'0 | intros H'0; clear H' ]; auto`
- **생성 top5**: `intros []; auto`(-2.78) · `-`(-2.88) · `intros []; auto`(-4.31) · `intros [<- | []]; auto`(-4.95) · `intros H; elim H; auto`(-5.09)

### step 3 — ❌miss
- **goal(입력 상태)**: `forall (a0 : poly A0 eqA ltM) (l : list (poly A0 eqA ltM)),
(In a (addEnd b l) -> a = b \/ In a l) ->
a0 = a \/ In a (addEnd b l) -> a = b \/ a0 = a \/ In a l`
- **retrieval 증명 top1**: `Global Instance is0gpd_core {A : Type} `{HasEquivs A} : Is0Gpd (core A). intros a H'0; eli`
- **retrieval premise top3**: `Lemma InFinEnumC_weaken : forall x l, In x l -> InFinEnumC x l.` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `intros a0 l H' H'0; case H'0; [ intros H'1; rewrite <- H'1; clear H'0 | intros H'1; clear H'0 ]; auto`
- **생성 top5**: `intros c cL; case cL; simpl in |- *; auto`(-5.86) · `intros c L1 Rec; case Rec; auto`(-6.37) · `intros c l H' H'0; elim H'0; auto`(-6.98) · `intros c l H' H'0; case H'0; auto`(-7.10) · `intros c cL H' H'0; elim H'0; auto`(-7.11)

### step 4 — ❌miss
- **goal(입력 상태)**: `a = b \/ a0 = a \/ In a l`
- **retrieval 증명 top1**: `Global Instance is0gpd_core {A : Type} `{HasEquivs A} : Is0Gpd (core A). intros a H'0; eli`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma InFinEnumC_weaken : forall x l, In x l -> InFinEnumC x l.`
- **gold**: `case (H' H'1); auto`
- **생성 top5**: `apply H'; auto`(-2.82) · `case H'; auto`(-2.83) · `elim H'1; auto`(-2.86) · `right; left; auto`(-3.45) · `apply H'`(-3.45)

## buchberger-theories-BuchAux.v · proof#2 — `Global Instance hasequivs_core {A : Type} `{HasEquivs A} : HasEquivs (core A).`  (3 steps)


### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (a : poly A0 eqA ltM) (aL : list (poly A0 eqA ltM)),
In a (addEnd a aL)`
- **retrieval 증명 top2**: `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b` ; `Global Instance is0gpd_core {A : Type} `{HasEquivs A} : Is0Gpd (core A). intros a H'0; eli`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros a aL; elim aL; simpl in |- *; auto`
- **생성 top5**: `intros a H'; elim H'; simpl in |- *; auto`(-3.50) · `intros a H'0; elim H'0`(-3.55) · `intros a aL; elim aL; simpl in |- *; auto`(-4.14) · `intros a H'; elim H'`(-4.31) · `intros a aL`(-4.49)

## buchberger-theories-BuchAux.v · proof#3 — `Lemma cate_isinitial A `{HasEquivs A} (x y : A) : IsInitial x -> IsInitial y -> x $<~> y.`  (4 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (a b : poly A0 eqA ltM) (aL : list (poly A0 eqA ltM)),
In a aL -> In a (addEnd b aL)`
- **retrieval 증명 top2**: `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b` ; `Global Instance hasequivs_core {A : Type} `{HasEquivs A} : HasEquivs (core A). Proof. intr`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros a b aL; elim aL; simpl in |- *; auto`
- **생성 top5**: `intros`(-3.89) · `intros x y Hx Hy`(-4.21) · `intros x y Hx Hy`(-5.40) · `intros x y H H0`(-5.48) · `intros x y xL yL`(-5.95)

### step 2 — 🔶topk
- **goal(입력 상태)**: `forall (a0 : poly A0 eqA ltM) (l : list (poly A0 eqA ltM)),
(In a l -> In a (addEnd b l)) ->
a0 = a \/ In a l -> a0 = a \/ In a (addEnd b l)`
- **retrieval 증명 top2**: `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b` ; `Global Instance is0gpd_core {A : Type} `{HasEquivs A} : Is0Gpd (core A). intros a H'0; eli`
- **retrieval premise top3**: `Lemma InFinEnumC_weaken : forall x l, In x l -> InFinEnumC x l.` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `intros a0 l H' H'0; case H'0; auto`
- **생성 top5**: `intros a0 l H' H'0; case H'0; [ intros H'1; rewrite <- H'1; clear H'0 | intros H'1; clear H'0 ]; auto`(-4.53) · `intros a0 l H' H'0; case H'0; auto`(-4.76) · `intros a0 l H' H'0; case H'0; [ intros H'1; rewrite <- H'1; clear H'0 | intros H'1; clear H'0 ]; auto`(-5.02) · `intros a0 l H' H'0; elim H'0; auto`(-5.38) · `intros a0 l H' H'0; elim H'0`(-5.39)

## buchberger-theories-BuchAux.v · proof#4 — `Lemma cate_isterminal A `{HasEquivs A} (x y : A) : IsTerminal x -> IsTerminal y -> x $<~> y.`  (4 steps)


### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (a : poly A0 eqA ltM) (P : list (poly A0 eqA ltM)),
addEnd a P = P ++ a :: nil`
- **retrieval 증명 top2**: `Global Instance hasequivs_core {A : Type} `{HasEquivs A} : HasEquivs (core A). Proof. intr` ; `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros a P; elim P; simpl in |- *; auto`
- **생성 top5**: `intros a b aL; elim aL; simpl in |- *; auto`(-1.19) · `intros a L; elim L; simpl in |- *; auto`(-3.56) · `intros a P; elim a; simpl in |- *; auto`(-3.87) · `intros a b aL`(-4.04) · `intros a P; elim P; simpl in |- *; auto`(-4.27)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a0 : poly A0 eqA ltM) (l : list (poly A0 eqA ltM)),
addEnd a l = l ++ a :: nil -> a0 :: addEnd a l = a0 :: l ++ a :: nil`
- **retrieval 증명 top2**: `Lemma cate_isinitial A `{HasEquivs A} (x y : A) : IsInitial x -> IsInitial y -> x $<~> y. ` ; `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros a0 l H'; elim H'; auto`
- **생성 top5**: `intros a0 l H'0; case H'0; auto`(-2.52) · `intros a0 l H'; case H'; auto`(-2.63) · `intros a0 l H' H'0; case H'0; auto`(-3.59) · `intros a0 l H'; case H'`(-4.32) · `intros a0 l H'`(-4.38)

## buchberger-theories-BuchAux.v · proof#5 — `Lemma isinitial_cate A `{HasEquivs A} (x y : A) : x $<~> y -> IsInitial x -> IsInitial y.`  (4 steps)


### step 0 — ❌miss
- **goal(입력 상태)**: `poly A0 eqA ltM -> poly A0 eqA ltM -> poly A0 eqA ltM`
- **retrieval 증명 top2**: `Global Instance hasequivs_core {A : Type} `{HasEquivs A} : HasEquivs (core A). Proof. intr` ; `Global Instance is0gpd_core {A : Type} `{HasEquivs A} : Is0Gpd (core A). intros a H'0; eli`
- **retrieval premise top3**: `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ ` ; `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum`
- **gold**: `intros p q; case p; case q`
- **생성 top5**: `Proof`(-0.01) · `Proof`(-7.04) · `Proof`(-7.08) · `Proof with auto`(-8.61) · `intros H'; elim H'; auto`(-10.65)

### step 1 — ❌miss
- **goal(입력 상태)**: `forall x : list (Term A n),
canonical A0 eqA ltM x ->
forall x0 : list (Term A n), canonical A0 eqA ltM x0 -> poly A0 eqA ltM`
- **retrieval 증명 top2**: `Global Instance is0gpd_core {A : Type} `{HasEquivs A} : Is0Gpd (core A). intros a H'0; eli` ; `Global Instance hasequivs_core {A : Type} `{HasEquivs A} : HasEquivs (core A). Proof. intr`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros x Cpx x0 Cpx0; exists (spolyf A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec x x0 Cpx Cpx0); auto`
- **생성 top5**: `auto`(-3.37) · `simpl in |- *; auto`(-3.73) · `intros a P; elim P; simpl in |- *; auto`(-5.29) · `simpl in |- *`(-5.39) · `simpl in |- *; intros; auto`(-7.12)

### step 2 — ❌miss
- **goal(입력 상태)**: `canonical A0 eqA ltM
  (spolyf A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec x x0 Cpx
     Cpx0)`
- **retrieval 증명 top2**: `Global Instance is0gpd_core {A : Type} `{HasEquivs A} : Is0Gpd (core A). intros a H'0; eli` ; `Global Instance hasequivs_core {A : Type} `{HasEquivs A} : HasEquivs (core A). Proof. intr`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply spolyf_canonical with (1 := cs); auto`
- **생성 top5**: `unfold canonical in |- *`(-4.08) · `simpl in |- *`(-4.15) · `unfold canonical in |- *; simpl in |- *`(-4.43) · `simpl in |- *; auto`(-4.50) · `unfold canonical in |- *; simpl in |- *; auto`(-4.55)

## buchberger-theories-BuchAux.v · proof#6 — `Lemma isterminal_cate A `{HasEquivs A} (x y : A) : x $<~> y -> IsTerminal x -> IsTerminal y.`  (15 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (a b : poly A0 eqA ltM) (aL : list (poly A0 eqA ltM)),
red (spolyp a b) aL -> red (spolyp b a) aL`
- **retrieval 증명 top2**: `Lemma cate_isinitial A `{HasEquivs A} (x y : A) : IsInitial x -> IsInitial y -> x $<~> y. ` ; `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros a b; case a; case b; simpl in |- *`
- **생성 top5**: `intros p q; case p; case q`(-0.81) · `intros a b aL; elim aL; simpl in |- *; auto`(-2.52) · `intros p q; elim p; simpl in |- *; auto`(-3.51) · `intros p q; case p; case q; simpl in |- *; auto`(-3.57) · `intros p q; case p; case q; auto`(-4.46)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (x : list (Term A n)) (c : canonical A0 eqA ltM x)
  (x0 : list (Term A n)) (c0 : canonical A0 eqA ltM x0)
  (aL : list (poly A0 eqA ltM)),
red
  (exist (fun a0 : list (Term A n) => canonical A`
- **retrieval 증명 top2**: `Lemma isinitial_cate A `{HasEquivs A} (x y : A) : x $<~> y -> IsInitial x -> IsInitial y. ` ; `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b`
- **retrieval premise top3**: `Lemma cmp_of_comparison_swap: forall c x, cmp_of_comparison (swap_comp` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na`
- **gold**: `unfold red in |- *; simpl in |- *`
- **생성 top5**: `auto`(-2.72) · `intros x c x0 c0; case c; case c0; simpl in |- *`(-5.05) · `intros x c x0 c0 aL; elim aL; simpl in |- *; auto`(-5.09) · `intros x c x0 c0; case c; case c0`(-5.33) · `intros x c x0 c0 aL; case aL; auto`(-5.46)

### step 3 — ❌miss
- **goal(입력 상태)**: `forall (x : list (Term A n)) (c : canonical A0 eqA ltM x)
  (x0 : list (Term A n)) (c0 : canonical A0 eqA ltM x0)
  (aL : list (poly A0 eqA ltM)),
reducestar A A0 A1 eqA invA minusA multA divA eqA_dec`
- **retrieval 증명 top2**: `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b` ; `Lemma cate_isinitial A `{HasEquivs A} (x y : A) : IsInitial x -> IsInitial y -> x $<~> y. `
- **retrieval premise top3**: `Lemma cmp_of_comparison_swap: forall c x, cmp_of_comparison (swap_comp` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `intros x Cx x0 Cx0 aL H'1; inversion H'1`
- **생성 top5**: `auto`(-3.33) · `unfold redugestar in |- *; simpl in |- *`(-4.00) · `unfold redugestar in |- *`(-4.12) · `intros x c x0 c0 aL; elim aL; simpl in |- *; auto`(-5.33) · `intros x0 l H'; elim H'; auto`(-5.91)

### step 4 — ❌miss
- **goal(입력 상태)**: `reducestar A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec aL
  (spolyf A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec x0 x Cx0
     Cx) (pO A n)`
- **retrieval 증명 top2**: `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b` ; `Lemma cate_isinitial A `{HasEquivs A} (x y : A) : IsInitial x -> IsInitial y -> x $<~> y. `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na`
- **gold**: `cut (canonical A0 eqA ltM (spolyf A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec x x0 Cx Cx0)); [ intros Op1 | apply spolyf_canonical with (1 := cs) ]; auto`
- **생성 top5**: `unfold reducestar in |- *; simpl in |- *`(-2.00) · `unfold reducestar in |- *`(-2.55) · `unfold reducestar in |- *; simpl in |- *; auto`(-3.93) · `rewrite H1`(-4.42) · `unfold reduceplus in |- *; simpl in |- *`(-4.82)

### step 5 — ❌miss
- **goal(입력 상태)**: `reducestar A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec aL
  (spolyf A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec x0 x Cx0
     Cx) (pO A n)`
- **retrieval 증명 top2**: `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b` ; `Lemma cate_isinitial A `{HasEquivs A} (x y : A) : IsInitial x -> IsInitial y -> x $<~> y. `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na`
- **gold**: `cut (canonical A0 eqA ltM (spolyf A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec x0 x Cx0 Cx)); [ intros Op2 | apply spolyf_canonical with (1 := cs) ]; auto`
- **생성 top5**: `unfold reducestar in |- *; simpl in |- *`(-2.66) · `unfold reducestar in |- *`(-3.08) · `elim H0; auto`(-4.20) · `elim H0; simpl in |- *; auto`(-4.56) · `unfold reduceplus in |- *`(-4.80)

### step 6 — ❌miss
- **goal(입력 상태)**: `reducestar A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec aL
  (spolyf A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec x0 x Cx0
     Cx) (pO A n)`
- **retrieval 증명 top2**: `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b` ; `Lemma cate_isinitial A `{HasEquivs A} (x y : A) : IsInitial x -> IsInitial y -> x $<~> y. `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na`
- **gold**: `apply reducestar0; auto`
- **생성 top5**: `unfold reducestar in |- *; simpl in |- *`(-3.14) · `exact H'`(-3.39) · `unfold reducestar in |- *`(-3.42) · `auto`(-3.56) · `exact H'1`(-3.90)

### step 7 — ❌miss
- **goal(입력 상태)**: `reduceplus A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec aL
  (spolyf A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec x0 x Cx0
     Cx) (pO A n)`
- **retrieval 증명 top2**: `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b` ; `Lemma cate_isinitial A `{HasEquivs A} (x y : A) : IsInitial x -> IsInitial y -> x $<~> y. `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na`
- **gold**: `apply reduceplus_eqp_com with (1 := cs) (p := mults (A:=A) multA (n:=n) (invTerm (A:=A) invA (n:=n) (T1 A1 n)) (spolyf A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec x x0 Cx Cx0)) (q := mults (A:=A) multA (n:=n) (invTerm (A:=A) invA (n:=n) (T1 A1 n)) (pO A n)); auto`
- **생성 top5**: `apply reducestar1; auto`(-1.70) · `apply reducestar0; auto`(-2.92) · `auto`(-2.98) · `apply reducestar; auto`(-3.37) · `exact H`(-3.89)

### step 8 — ❌miss
- **goal(입력 상태)**: `reduceplus A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec aL
  (mults multA (n:=n) (invTerm invA (n:=n) (T1 A1 n))
     (spolyf A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec x x0 `
- **retrieval 증명 top2**: `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b` ; `Lemma cate_isinitial A `{HasEquivs A} (x y : A) : IsInitial x -> IsInitial y -> x $<~> y. `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na`
- **gold**: `apply reduceplus_mults with (1 := cs); auto`
- **생성 top5**: `apply reducestar0; auto`(-3.08) · `unfold reduceplus in |- *`(-4.41) · `unfold reduceplus in |- *; simpl in |- *`(-4.41) · `apply spolyf_canonical with (1 := cs); auto`(-4.70) · `apply reduceplus_eqp; auto`(-4.78)

### step 9 — ❌miss
- **goal(입력 상태)**: `eqP A eqA n
  (mults multA (n:=n) (invTerm invA (n:=n) (T1 A1 n))
     (spolyf A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec x x0 Cx
        Cx0))
  (spolyf A A0 A1 eqA invA minusA multA di`
- **retrieval 증명 top2**: `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b` ; `Lemma cate_isinitial A `{HasEquivs A} (x y : A) : IsInitial x -> IsInitial y -> x $<~> y. `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na`
- **gold**: `inversion H; auto`
- **생성 top5**: `unfold eqP in |- *`(-3.31) · `unfold eqP in |- *; simpl in |- *`(-3.46) · `apply eqP_refl`(-4.08) · `apply spolyf_eqp; auto`(-5.11) · `apply reduceplus_eqp_com with (1 := cs); auto`(-5.36)

### step 10 — ❌miss
- **goal(입력 상태)**: `eqP A eqA n
  (mults multA (n:=n) (invTerm invA (n:=n) (T1 A1 n))
     (spolyf A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec x x0 Cx
        Cx0))
  (spolyf A A0 A1 eqA invA minusA multA di`
- **retrieval 증명 top2**: `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b` ; `Lemma cate_isinitial A `{HasEquivs A} (x y : A) : IsInitial x -> IsInitial y -> x $<~> y. `
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na`
- **gold**: `apply (eqp_sym _ _ _ _ _ _ _ _ _ cs n); auto`
- **생성 top5**: `inversion H0; auto`(-1.04) · `apply reducestar0; auto`(-2.75) · `inversion Op1; auto`(-3.59) · `apply spolyf_canonical with (1 := cs); auto`(-3.88) · `inversion H; auto`(-4.09)

### step 11 — ❌miss
- **goal(입력 상태)**: `eqP A eqA n
  (spolyf A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec x0 x Cx0
     Cx)
  (mults multA (n:=n) (invTerm invA (n:=n) (T1 A1 n))
     (spolyf A A0 A1 eqA invA minusA multA divA e`
- **retrieval 증명 top2**: `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b` ; `Lemma cate_isinitial A `{HasEquivs A} (x y : A) : IsInitial x -> IsInitial y -> x $<~> y. `
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na`
- **gold**: `apply spolyf_com with (1 := cs); auto`
- **생성 top5**: `inversion H0; auto`(-1.88) · `apply (eqp_sym _ _ _ _ _ _ _ _ _ cs n); auto`(-3.19) · `inversion H; auto`(-3.88) · `inversion Op1; auto`(-3.90) · `apply spolyf_canonical with (1 := cs); auto`(-4.74)

### step 12 — 🔶topk
- **goal(입력 상태)**: `eqP A eqA n
  (mults multA (n:=n) (invTerm invA (n:=n) (T1 A1 n))
     (spolyf A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec x x0 Cx
        Cx0))
  (spolyf A A0 A1 eqA invA minusA multA di`
- **retrieval 증명 top2**: `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b` ; `Lemma cate_isinitial A `{HasEquivs A} (x y : A) : IsInitial x -> IsInitial y -> x $<~> y. `
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na`
- **gold**: `apply (eqp_sym _ _ _ _ _ _ _ _ _ cs n); auto`
- **생성 top5**: `inversion H0; auto`(-3.24) · `inversion Op1; auto`(-3.29) · `apply spolyf_com with (1 := cs); auto`(-3.54) · `apply (eqp_sym _ _ _ _ _ _ _ _ _ cs n); auto`(-3.77) · `apply eqp_refl`(-3.99)

### step 13 — ✅top1
- **goal(입력 상태)**: `eqP A eqA n
  (spolyf A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec x0 x Cx0
     Cx)
  (mults multA (n:=n) (invTerm invA (n:=n) (T1 A1 n))
     (spolyf A A0 A1 eqA invA minusA multA divA e`
- **retrieval 증명 top2**: `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b` ; `Lemma cate_isinitial A `{HasEquivs A} (x y : A) : IsInitial x -> IsInitial y -> x $<~> y. `
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na`
- **gold**: `apply spolyf_com with (1 := cs); auto`
- **생성 top5**: `apply spolyf_com with (1 := cs); auto`(-1.81) · `apply spolyf_mults with (1 := cs); auto`(-2.22) · `inversion H0; auto`(-3.35) · `apply spolyf_mult with (1 := cs); auto`(-3.63) · `inversion Op1; auto`(-4.10)

## buchberger-theories-BuchAux.v · proof#7 — `Class Cat_IsBiInv {A} `{Is1Cat A} {x y : A} (f : x $-> y) := { cat_equiv_inv : y $-> x; cat_eisretr : f $o cat_equiv_inv $== Id y; cat_equiv_inv' : y `  (6 steps)


### step 0 — ❌miss
- **goal(입력 상태)**: `forall (Q : list (poly A0 eqA ltM)) (p : list (Term A n)),
canonical A0 eqA ltM p ->
reduceplus A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec Q p
  (pO A n) ->
reducestar A A0 A1 eqA invA m`
- **retrieval 증명 top2**: `Lemma isinitial_cate A `{HasEquivs A} (x y : A) : x $<~> y -> IsInitial x -> IsInitial y. ` ; `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `Proof using plusA os cs`
- **생성 top5**: `Proof`(-0.24) · `Proof`(-3.58) · `intros Q p; case Q; case p`(-6.80) · `intros Q p H' H'0`(-7.23) · `intros Q p; case Q; simpl in |- *`(-7.30)

### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (Q : list (poly A0 eqA ltM)) (p : list (Term A n)),
canonical A0 eqA ltM p ->
reduceplus A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec Q p
  (pO A n) ->
reducestar A A0 A1 eqA invA m`
- **retrieval 증명 top2**: `Lemma isinitial_cate A `{HasEquivs A} (x y : A) : x $<~> y -> IsInitial x -> IsInitial y. ` ; `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros Q p H' H'0`
- **생성 top5**: `induction Q`(-4.04) · `intros Q; case Q`(-5.71) · `intros Q p H' H'0`(-5.84) · `intros Q p; case Q`(-6.12) · `intros Q; case Q; simpl in |- *`(-6.38)

### step 2 — ❌miss
- **goal(입력 상태)**: `reducestar A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec Q p
  (pO A n)`
- **retrieval 증명 top2**: `Lemma isinitial_cate A `{HasEquivs A} (x y : A) : x $<~> y -> IsInitial x -> IsInitial y. ` ; `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `elim reduce0_reducestar with (1 := cs) (eqA_dec := eqA_dec) (ltM_dec := ltM_dec) (Q := Q) (p := pO A n); auto`
- **생성 top5**: `elim H'0`(-3.02) · `elim H'0; auto`(-3.54) · `unfold canonical in H'`(-4.17) · `inversion H'0`(-4.21) · `elim H'0; simpl in |- *; auto`(-4.22)

### step 3 — ❌miss
- **goal(입력 상태)**: `forall x : list (Term A n),
reducestar A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec Q
  (pO A n) x ->
reducestar A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec Q p
  (pO A n)`
- **retrieval 증명 top2**: `Lemma isinitial_cate A `{HasEquivs A} (x y : A) : x $<~> y -> IsInitial x -> IsInitial y. ` ; `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros t E; apply reducestar0; auto`
- **생성 top5**: `intros Q0 H'1`(-3.13) · `intros Q' H'1`(-4.00) · `intros Q0 H'1; case H'1; auto`(-5.44) · `intros Q' H''; case H''; auto`(-5.63) · `intros Q0 H'1; elim H'1; auto`(-6.16)

### step 4 — ❌miss
- **goal(입력 상태)**: `irreducible A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec Q
  (pO A n)`
- **retrieval 증명 top2**: `Lemma isinitial_cate A `{HasEquivs A} (x y : A) : x $<~> y -> IsInitial x -> IsInitial y. ` ; `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A). Proof. intros a b`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply pO_irreducible; auto`
- **생성 top5**: `unfold irreducible in |- *`(-3.93) · `apply reducestar_irreducible with (1 := cs); auto`(-4.08) · `apply reducestar_irreducible; auto`(-4.18) · `apply reduceplus_irreducible with (1 := cs); auto`(-5.29) · `unfold irreducible in |- *; auto`(-5.40)

## buchberger-theories-BuchRed.v · proof#0 — `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y : A), IsConnected O (x = y)) : Lex O.`  (6 steps)


### step 0 — ❌miss
- **goal(입력 상태)**: `forall (L : list (poly A0 eqA ltM)) (p q : poly A0 eqA ltM),
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q (addEnd A A0 eqA n ltM p L) ->
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q (p :: L)`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `Proof using os minusA invA divA cs A1`
- **생성 top5**: `Proof`(-0.86) · `Proof`(-1.14) · `Proof`(-2.80) · `intros`(-3.45) · `intros`(-4.65)

### step 1 — ❌miss
- **goal(입력 상태)**: `forall (L : list (poly A0 eqA ltM)) (p q : poly A0 eqA ltM),
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q (addEnd A A0 eqA n ltM p L) ->
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q (p :: L)`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros L p q H; apply Cb_incl with (1 := cs) (P := addEnd A A0 eqA n ltM p L); auto`
- **생성 top5**: `intros`(-2.55) · `induction L`(-3.76) · `intros L p q`(-4.05) · `intros L`(-4.19) · `intros L p q H`(-4.52)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall a : poly A0 eqA ltM, In a (addEnd A A0 eqA n ltM p L) -> In a (p :: L)`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `elim L; simpl in |- *; auto`
- **생성 top5**: `intros x Hx`(-4.14) · `-`(-4.22) · `intros u Hu`(-4.47) · `intros a Ha`(-4.60) · `intros r Hr`(-4.69)

### step 3 — ❌miss
- **goal(입력 상태)**: `forall (a : poly A0 eqA ltM) (l : list (poly A0 eqA ltM)),
(forall a0 : poly A0 eqA ltM,
 In a0 (addEnd A A0 eqA n ltM p l) -> p = a0 \/ In a0 l) ->
forall a0 : poly A0 eqA ltM,
a = a0 \/ In a0 (addEn`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros a l H0 a0 H1; elim H1; clear H1; intros H1; auto`
- **생성 top5**: `intros`(-3.43) · `intros; elim H; auto`(-5.21) · `intros; elim H0; auto`(-5.30) · `intros; elim H; simpl in |- *; auto`(-6.57) · `intros; elim H; intros; auto`(-7.33)

### step 4 — ❌miss
- **goal(입력 상태)**: `p = a0 \/ a = a0 \/ In a0 l`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `case (H0 a0); auto`
- **생성 top5**: `elim H0 with a0; auto`(-2.42) · `elim (H0 a0); auto`(-2.64) · `apply H0 in H1`(-3.33) · `elim (H0 a0 H1); auto`(-3.67) · `apply H0; auto`(-3.75)

## buchberger-theories-BuchRed.v · proof#1 — `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsConnected O A) -> (IsConnected O B) -> (MapIn O f) -> IsEquiv f`  (6 steps)


### step 0 — ✅top1
- **goal(입력 상태)**: `forall (L : list (poly A0 eqA ltM)) (p q : poly A0 eqA ltM),
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q (p :: L) ->
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q (addEnd A A0 eqA n ltM p L)`
- **retrieval 증명 top1**: `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `Proof using os minusA invA divA cs A1`
- **생성 top5**: `Proof using os minusA invA divA cs A1`(-1.17) · `Proof`(-2.15) · `Proof using os minusA invA divA cs`(-2.58) · `Proof using os minusA invA divA cs H`(-3.08) · `Proof using os`(-4.93)

### step 1 — ❌miss
- **goal(입력 상태)**: `forall (L : list (poly A0 eqA ltM)) (p q : poly A0 eqA ltM),
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q (p :: L) ->
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q (addEnd A A0 eqA n ltM p L)`
- **retrieval 증명 top1**: `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros L p q H; apply Cb_incl with (1 := cs) (P := p :: L); auto`
- **생성 top5**: `intros L p q H; apply Cb_incl with (1 := cs) (P := addEnd A A0 eqA n ltM p L); auto`(-1.28) · `intros L p q H`(-3.27) · `intros L p q H; apply Cb_incl with (1 := H) (P := addEnd A A0 eqA n ltM p L); auto`(-4.76) · `intros L p q H; apply Cb_equiv with (1 := cs) (P := addEnd A A0 eqA n ltM p L); auto`(-5.18) · `intros L p q H; apply Cb_incl with (1 := cs) (P := addEnd A A0 eqA n ltM p L); auto`(-5.30)

### step 2 — 🔶topk
- **goal(입력 상태)**: `forall a : poly A0 eqA ltM, In a (p :: L) -> In a (addEnd A A0 eqA n ltM p L)`
- **retrieval 증명 top1**: `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `elim L; simpl in |- *; auto`
- **생성 top5**: `elim H; simpl in |- *; auto`(-1.73) · `elim L; simpl in |- *; auto`(-2.17) · `elim H; auto`(-3.11) · `elim H; intros; auto`(-5.09) · `elim H; clear H; simpl in |- *; auto`(-5.29)

### step 3 — ✅top1
- **goal(입력 상태)**: `forall (a : poly A0 eqA ltM) (l : list (poly A0 eqA ltM)),
(forall a0 : poly A0 eqA ltM,
 p = a0 \/ In a0 l -> In a0 (addEnd A A0 eqA n ltM p l)) ->
forall a0 : poly A0 eqA ltM,
p = a0 \/ a = a0 \/ In`
- **retrieval 증명 top1**: `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros a l H0 a0 H1; elim H1; clear H1; intros H1; auto`
- **생성 top5**: `intros a l H0 a0 H1; elim H1; clear H1; intros H1; auto`(-0.66) · `intros a l H0 a0 H1`(-3.50) · `intros a l H0 a0 H1; elim H1; clear H1; intros H1`(-4.63) · `intros a l H1 a0 H2; elim H2; clear H2; intros H2; auto`(-4.83) · `intros a l H0 a' H1; elim H1; clear H1; intros H1; auto`(-4.83)

### step 4 — 🔶topk
- **goal(입력 상태)**: `a = a0 \/ In a0 (addEnd A A0 eqA n ltM p l)`
- **retrieval 증명 top1**: `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `case H1; auto`
- **생성 top5**: `case (H0 a0); auto`(-0.38) · `case H1; auto`(-2.91) · `elim H1; clear H1; intros H1; auto`(-4.09) · `case H1; clear H1; intros H1; auto`(-4.24) · `case H1; clear H1; intros H1`(-4.42)

## buchberger-theories-BuchRed.v · proof#2 — `Definition lex_from_ispullback_connmap_mapino_commsq (H : forall {A B C D} (f : A -> B) (g : C -> D) (h : A -> C) (k : B -> D), (IsConnMap O f) -> (Is`  (5 steps)


### step 0 — ✅top1
- **goal(입력 상태)**: `forall (L : list (poly A0 eqA ltM)) (p q : poly A0 eqA ltM),
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q (p :: L) ->
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec p L ->
Cb A A0 eqA plusA multA eq`
- **retrieval 증명 top2**: `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :` ; `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `Proof using os minusA invA divA cs A1`
- **생성 top5**: `Proof using os minusA invA divA cs A1`(-0.51) · `Proof`(-2.59) · `Proof using os minusA invA divA cs`(-3.47) · `Proof using os minusA divA cs A1`(-4.27) · `Proof using os minusA invA divA cs A1 A0`(-4.88)

### step 1 — ❌miss
- **goal(입력 상태)**: `forall (L : list (poly A0 eqA ltM)) (p q : poly A0 eqA ltM),
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q (p :: L) ->
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec p L ->
Cb A A0 eqA plusA multA eq`
- **retrieval 증명 top2**: `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :` ; `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros L p q H H0`
- **생성 top5**: `intros L p q H; apply Cb_incl with (1 := cs) (P := p :: L); auto`(-2.12) · `intros L p q H; apply Cb_incl with (1 := cs) (P := addEnd A A0 eqA n ltM p L); auto`(-2.65) · `intros L p q H`(-4.00) · `intros L p q H; apply Cb_incl with (1 := cs) (P := addEnd A A0 eqA n ltM p L); auto`(-4.64) · `intros L p q H; apply Cb_incl with (1 := cs) (P := p :: L); auto`(-4.78)

### step 2 — ❌miss
- **goal(입력 상태)**: `Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q L`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply Cb_trans with (1 := cs) (b := p); auto`
- **생성 top5**: `apply Cb_incl with (1 := cs) (P := p :: L); auto`(-2.84) · `elim H; simpl in |- *; auto`(-3.95) · `apply Cb_incl with (1 := cs) (P := q :: L); auto`(-4.00) · `apply Cb_incl with (1 := cs); auto`(-4.19) · `apply Cb_incl with (1 := cs) (P := addEnd A A0 eqA n ltM p L); auto`(-4.97)

### step 3 — ❌miss
- **goal(입력 상태)**: `Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q (addEnd A A0 eqA n ltM p L)`
- **retrieval 증명 top2**: `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :` ; `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply Cb_cons_addEnd; auto`
- **생성 top5**: `elim H; simpl in |- *; auto`(-2.55) · `apply Cb_trans with (1 := cs) (b := q); auto`(-2.58) · `apply Cb_incl with (1 := cs) (P := p :: L); auto`(-3.60) · `elim H; auto`(-4.09) · `apply Cb_incl with (1 := cs) (P := addEnd A A0 eqA n ltM p L); auto`(-4.40)

## buchberger-theories-BuchRed.v · proof#3 — `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A B : Type} (f : A -> B) (b : B), IsEquiv (O_functor_hfiber O `  (10 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (p : poly A0 eqA ltM) (L : list (poly A0 eqA ltM)),
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (nf A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM ltM_dec os p
     L) (p :: L)`
- **retrieval 증명 top2**: `Definition lex_from_ispullback_connmap_mapino_commsq (H : forall {A B C D} (f : A -> B) (g` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros p L; unfold nf, LetP in |- *; auto`
- **생성 top5**: `intros f b`(-3.29) · `intros f b`(-3.64) · `intros f b`(-4.65) · `intros p L`(-4.88) · `intros f b; split`(-5.69)

### step 2 — ❌miss
- **goal(입력 상태)**: `Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (let (x, _) :=
     Reducef A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM
       ltM_dec os L p in
   let (x0, c) := x in
   exist (fun a : `
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_ispullback_connmap_mapino_commsq (H : forall {A B C D} (f : A -> B) (g`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma cmp_of_comparison_swap: forall c x, cmp_of_comparison (swap_comp`
- **gold**: `case (Reducef A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM ltM_dec os L p); simpl in |- *; auto`
- **생성 top5**: `elim (Reducef A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM ltM_dec os L p)`(-5.63) · `case (Reducef A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM ltM_dec os L p)`(-5.72) · `elim (Reducef A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM ltM_dec os L p)`(-5.80) · `case (Reducef A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM ltM_dec os L p)`(-6.25) · `elim (Reducef A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM ltM_dec os L p)`(-6.46)

### step 3 — ❌miss
- **goal(입력 상태)**: `forall x : poly A0 eqA ltM,
reducestar A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec L
  (s2p A A0 eqA n ltM p) (s2p A A0 eqA n ltM x) ->
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (le`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma cmp_of_comparison_swap: forall c x, cmp_of_comparison (swap_comp` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Theorem Bparse_correct: forall b m e (BASE: 2 <= Zpos b), let base := `
- **gold**: `intros x0; case x0; simpl in |- *`
- **생성 top5**: `intros x H`(-3.70) · `intros q H0`(-4.03) · `intros x H0`(-4.26) · `intros p0 H0`(-5.32) · `intros x H; elim H; simpl in |- *; auto`(-6.04)

### step 4 — ❌miss
- **goal(입력 상태)**: `forall (x : list (Term A n)) (c : canonical A0 eqA ltM x),
reducestar A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec L
  (s2p A A0 eqA n ltM p) x ->
CombLinear A A0 eqA plusA multA eqA_dec n`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma cmp_of_comparison_swap: forall c x, cmp_of_comparison (swap_comp` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) `
- **gold**: `intros x c H'`
- **생성 top5**: `intros x1; case x1; simpl in |- *`(-2.57) · `intros x; case x; simpl in |- *`(-4.12) · `intros x1 c; case c; simpl in |- *`(-4.31) · `auto`(-4.74) · `intros x1; case x1; simpl in |- *; auto`(-4.94)

### step 5 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec 
  (p :: L)
  (mults multA (n:=n)
     (match x as l return (canonical A0 eqA ltM l -> Term A n) with
      | nil => fun _ : canonical A0 eqA ltM `
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma HemiMetricHemiMetricStrong : forall (e:Q) A b, hemiMetric X e A `
- **gold**: `change (CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec (p :: L) (mults (A:=A) multA (n:=n) (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM x c)) x)) in |- *`
- **생성 top5**: `case c; simpl in |- *`(-3.67) · `elim H'`(-3.89) · `unfold CombLinear in |- *`(-3.92) · `case c; simpl in |- *; auto`(-3.92) · `elim H'; simpl in |- *; auto`(-3.94)

### step 6 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec 
  (p :: L)
  (mults multA (n:=n) (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM x c))
     x)`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply CombLinear_mults1 with (1 := cs); auto`
- **생성 top5**: `unfold CombLinear in |- *`(-2.94) · `apply H'`(-3.50) · `unfold CombLinear in |- *; simpl in |- *`(-3.95) · `simpl in |- *`(-3.96) · `unfold CombLinear in |- *; auto`(-4.53)

### step 7 — ❌miss
- **goal(입력 상태)**: `~ zeroP A0 eqA (n:=n) (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM x c)) / CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec (p :: L) x`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply unit_nZ with (1 := cs); auto`
- **생성 top5**: `intros H`(-3.10) · `intro H`(-3.49) · `unfold zeroP in |- *`(-3.78) · `simpl in |- *`(-4.38) · `simpl in |- *; auto`(-4.91)

### step 8 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec (p :: L) x`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply reducestar_cb1 with (1 := cs); auto`
- **생성 top5**: `unfold CombLinear in |- *`(-3.85) · `apply CombLinear_mults with (1 := cs); auto`(-3.89) · `apply CombLinear_plus with (1 := cs); auto`(-4.12) · `apply CombLinear_mults1 with (1 := cs); auto`(-4.16) · `apply CombLinear_mults2 with (1 := cs); auto`(-4.36)

## buchberger-theories-BuchRed.v · proof#4 — `Definition lex_gen `{Univalence} (O : Modality) `{IsAccModality O} (lexgen : forall (i : ngen_indices (acc_ngen O)) (x y : ngen_type (acc_ngen O) i), `  (11 steps)


### step 0 — 🔶topk
- **goal(입력 상태)**: `forall L1 L2 : list (poly A0 eqA ltM),
(forall p : poly A0 eqA ltM,
 In p L1 -> Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec p L2) ->
forall q : poly A0 eqA ltM,
Cb A A0 eqA plusA multA eqA_dec n ltM`
- **retrieval 증명 top2**: `Definition lex_from_ispullback_connmap_mapino_commsq (H : forall {A B C D} (f : A -> B) (g` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `Proof using os minusA invA divA cs A1`
- **생성 top5**: `Proof`(-1.34) · `Proof using os minusA invA divA cs A1`(-1.43) · `Proof using os minusA invA divA cs`(-1.88) · `Proof using os minusA invA divA cs Univalence`(-4.01) · `Proof using os`(-4.07)

### step 1 — ❌miss
- **goal(입력 상태)**: `forall L1 L2 : list (poly A0 eqA ltM),
(forall p : poly A0 eqA ltM,
 In p L1 -> Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec p L2) ->
forall q : poly A0 eqA ltM,
Cb A A0 eqA plusA multA eqA_dec n ltM`
- **retrieval 증명 top2**: `Definition lex_from_ispullback_connmap_mapino_commsq (H : forall {A B C D} (f : A -> B) (g` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros L1 L2 H' q; case q; simpl in |- *`
- **생성 top5**: `intros L1 L2 H p q H0`(-3.66) · `intros L1 L2 H q H0`(-4.01) · `intros L1 L2 H L3`(-4.47) · `intros L p q H; apply Cb_trans with (1 := cs) (b := p); auto`(-4.55) · `intros L p q H; apply Cb_incl with (1 := cs) (P := p :: L); auto`(-4.68)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall x : list (Term A n),
canonical A0 eqA ltM x ->
CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec L1 x ->
CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec L2 x`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros x H'0 H'1`
- **생성 top5**: `intros x H0 H1`(-4.34) · `intros x H H0`(-4.96) · `intros x H1 H2`(-5.01) · `intros q0 H0 H1`(-5.94) · `intros x H0 H1; elim H1; clear H1; intros H1; auto`(-6.73)

### step 3 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec L2 x`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply CombLinear_compo with (1 := cs) (L1 := L1); auto`
- **생성 top5**: `unfold CombLinear in |- *`(-4.11) · `case H'1; auto`(-4.60) · `apply Cb_trans with (1 := H'1)`(-4.99) · `apply Cb_trans with (1 := H'0)`(-5.01) · `apply Cb_trans with (1 := H'0); auto`(-5.12)

### step 4 — ✅top1
- **goal(입력 상태)**: `forall q0 : list (Term A n),
inPolySet A A0 eqA n ltM q0 L1 ->
CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec L2 q0`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros q0 H'2`
- **생성 top5**: `intros q0 H'2`(-1.66) · `intros q' H'2`(-3.12) · `intros q0 H'0'`(-3.46) · `intros x0 H'2`(-3.67) · `intros y H'2`(-3.91)

### step 5 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec L2 q0`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `case inPolySet_inv1 with (1 := H'2); auto`
- **생성 top5**: `apply CombLinear_compo with (1 := cs) (L1 := L2); auto`(-1.96) · `apply CombLinear_compo with (1 := cs) (L2 := L2); auto`(-3.26) · `apply CombLinear_compo with (1 := cs) (L1 := L1); auto`(-4.01) · `unfold inPolySet in H'2`(-4.77) · `apply CombLinear_trans with (1 := cs) (L1 := L1); auto`(-4.87)

### step 6 — ❌miss
- **goal(입력 상태)**: `forall x0 : poly A0 eqA ltM,
In x0 L1 /\ q0 = s2p A A0 eqA n ltM x0 ->
CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec L2 q0`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros q1 H; elim H; intros H0 H1; clear H`
- **생성 top5**: `intros q1 H'3`(-2.22) · `intros q' H'3`(-2.68) · `intros q0' H'3`(-3.64) · `intros x0 H'3`(-3.68) · `intros p H'3`(-3.87)

### step 7 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec L2 q0`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `lapply (H' q1); [ intros H'6 | idtac ]; auto`
- **생성 top5**: `apply CombLinear_compo with (1 := cs) (L1 := L1); auto`(-3.34) · `rewrite H1`(-3.70) · `apply CombLinear_compo with (1 := cs) (L1 := L2); auto`(-4.36) · `rewrite <- H1`(-4.53) · `rewrite H1; clear H1`(-4.61)

### step 8 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec L2 q0`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_from_ispullback_connmap_mapino_commsq (H : forall {A B C D} (f : A -> B) (g`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `generalize H'6 H1; case q1; simpl in |- *; auto`
- **생성 top5**: `apply CombLinear_compo with (1 := cs) (L1 := L2); auto`(-3.06) · `apply CombLinear_compo with (1 := cs) (L1 := L1); auto`(-4.57) · `apply CombLinear_compo with (1 := cs) (L2 := L2); auto`(-4.83) · `apply CombLinear_compo with (1 := cs); auto`(-4.98) · `lapply (H' q0); [ intros H'7 | idtac ]; auto`(-5.28)

### step 9 — ❌miss
- **goal(입력 상태)**: `forall x0 : list (Term A n),
canonical A0 eqA ltM x0 ->
CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec L2 x0 ->
q0 = x0 -> CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec L2 q0`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_from_ispullback_connmap_mapino_commsq (H : forall {A B C D} (f : A -> B) (g`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros x0 H'5 H'7 H'8; rewrite H'8; auto`
- **생성 top5**: `intros q2 H'7 H'8 H'9`(-3.65) · `intros q2 H'3 H'4 H'5`(-4.40) · `intros q2 H'5 H'7 H'8`(-5.01) · `intros q0' H'3 H'4 H'5`(-5.99) · `intros q2 H'3 H'4; apply CombLinear_compo with (1 := cs) (L1 := L2); auto`(-6.93)

## buchberger-theories-BuchRed.v · proof#5 — `Fixpoint nSep (n : trunc_index) (O : Subuniverse) : Subuniverse := match n with | -2 => O | n.+1 => Sep (nSep n O) end.`  (34 steps)


### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (p : poly A0 eqA ltM) (L : list (poly A0 eqA ltM)),
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec p
  (nf A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM ltM_dec os p
     L :: L)`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_from_ispullback_connmap_mapino_commsq (H : forall {A B C D} (f : A -> B) (g`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros p L; unfold nf in |- *`
- **생성 top5**: `intros p L`(-2.52) · `intros p L; simpl in |- *`(-4.09) · `intros p L; unfold nf, LetP in |- *; auto`(-4.88) · `intros n O`(-4.89) · `intros p L; unfold nf, LetP in |- *`(-5.16)

### step 2 — ❌miss
- **goal(입력 상태)**: `Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec p
  ((let (x, _) :=
      Reducef A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM
        ltM_dec os L p in
    LetP (poly A0 eqA ltM) (poly A0 `
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_gen `{Univalence} (O : Modality) `{IsAccModality O} (lexgen : forall (i : n`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma cmp_of_comparison_swap: forall c x, cmp_of_comparison (swap_comp` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) `
- **gold**: `case (Reducef A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM ltM_dec os L p); auto`
- **생성 top5**: `case (Reducef A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM ltM_dec os L p); simpl in |- *; auto`(-2.82) · `case (Reducef A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM ltM_dec os L p); simpl in |- *; auto`(-3.29) · `simpl in |- *`(-3.71) · `case (Reducef A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM ltM_dec os L p); simpl in |- *`(-3.72) · `case (Reducef A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM ltM_dec os L p); simpl in |- *`(-4.14)

### step 3 — ❌miss
- **goal(입력 상태)**: `forall x : poly A0 eqA ltM,
reducestar A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec L
  (s2p A A0 eqA n ltM p) (s2p A A0 eqA n ltM x) ->
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec p
  (`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_gen `{Univalence} (O : Modality) `{IsAccModality O} (lexgen : forall (i : n`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma cmp_of_comparison_swap: forall c x, cmp_of_comparison (swap_comp` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) `
- **gold**: `case p`
- **생성 top5**: `intros x0; case x0; simpl in |- *`(-2.46) · `intros x; case x; simpl in |- *`(-2.94) · `intros x0; case x0; auto`(-3.42) · `intros q; case q; simpl in |- *`(-3.57) · `intros x; case x; simpl in |- *; auto`(-4.63)

### step 4 — ❌miss
- **goal(입력 상태)**: `forall (x : list (Term A n)) (c : canonical A0 eqA ltM x)
  (x0 : poly A0 eqA ltM),
reducestar A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec L
  (s2p A A0 eqA n ltM
     (exist (fun a : lis`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_gen `{Univalence} (O : Modality) `{IsAccModality O} (lexgen : forall (i : n`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinSubset_ball_triangle_l : forall e1 e2 x1 x2 l, (ball e1 x1 x2` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) `
- **gold**: `unfold LetP in |- *; intros x H' x0; case x0; simpl in |- *`
- **생성 top5**: `simpl in |- *`(-3.27) · `simpl in |- *; auto`(-3.72) · `intros x; case x; simpl in |- *`(-4.09) · `intros x c x0 H'`(-4.49) · `intros x0; case x0; simpl in |- *`(-4.55)

### step 5 — ✅top1
- **goal(입력 상태)**: `forall (x1 : list (Term A n)) (c : canonical A0 eqA ltM x1),
reducestar A A0 A1 eqA invA minusA multA divA eqA_dec n ltM ltM_dec L x x1 ->
CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (exis`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon`
- **retrieval premise top3**: `Lemma cmp_of_comparison_swap: forall c x, cmp_of_comparison (swap_comp` ; `Lemma FinSubset_ball_triangle_l : forall e1 e2 x1 x2 l, (ball e1 x1 x2` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum`
- **gold**: `intros x1 c H'0`
- **생성 top5**: `intros x1 c H'0`(-2.51) · `intros x1 c H''`(-3.53) · `intros x1 c H'1`(-3.98) · `intros x1; case x1; simpl in |- *`(-4.09) · `intros x1 c H'0; case c; simpl in |- *`(-5.03)

### step 6 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (exist (fun a : list (Term A n) => canonical A0 eqA ltM a)
     (mults multA (n:=n)
        (match x1 as l return (canonical A0 eqA ltM l -> Ter`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma HemiMetricHemiMetricStrong : forall (e:Q) A b, hemiMetric X e A ` ; `Theorem Bparse_correct: forall b m e (BASE: 2 <= Zpos b), let base := `
- **gold**: `change (CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec (mks A A0 eqA n ltM (mults (A:=A) multA (n:=n) (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM x1 c)) x1) (canonical_mults A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM os (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM x1 c)) x1 (unit_nZ A A0 A1 eqA plusA invA minusA multA divA cs n ltM (mks A A0 eqA n ltM x1 c)) c) :: L) x) in |- *`
- **생성 top5**: `apply CombLinear_mults1 with (1 := cs); auto`(-3.70) · `case c; simpl in |- *`(-4.36) · `case c; simpl in |- *; auto`(-5.14) · `apply CombLinear_compo with (1 := cs); auto`(-5.38) · `apply CombLinear_compo with (1 := cs) (P := x1); auto`(-5.55)

### step 7 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (mks A A0 eqA n ltM
     (mults multA (n:=n)
        (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM x1 c)) x1)
     (canonical_mults A A0 A1 e`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_gen `{Univalence} (O : Modality) `{IsAccModality O} (lexgen : forall (i : n`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply CombLinear_compo with (1 := cs) (L1 := mks A A0 eqA n ltM x1 c :: L); auto`
- **생성 top5**: `apply CombLinear_mults1 with (1 := cs); auto`(-1.09) · `apply CombLinear_mults2 with (1 := cs); auto`(-3.47) · `apply CombLinear_mults1 with (1 := cs)`(-3.56) · `apply CombLinear_mults with (1 := cs); auto`(-3.72) · `apply CombLinear_mults; auto`(-4.48)

### step 8 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (mks A A0 eqA n ltM x1 c :: L) x / forall q : list (Term A n),
inPolySet A A0 eqA n ltM q (mks A A0 eqA n ltM x1 c :: L) ->
CombLinear A A0 eqA `
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_gen `{Univalence} (O : Modality) `{IsAccModality O} (lexgen : forall (i : n`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `change (CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec (mks A A0 eqA n ltM x1 c :: L) (s2p A A0 eqA n ltM (mks A A0 eqA n ltM x H'))) in |- *`
- **생성 top5**: `apply unit_nZ with (1 := cs); auto`(-1.90) · `apply reducestar_cb1 with (1 := cs); auto`(-2.35) · `apply CombLinear_mults1 with (1 := cs); auto`(-3.15) · `apply unit_nZ with (1 := cs)`(-4.89) · `apply CombLinear_mults with (1 := cs); auto`(-5.21)

### step 9 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (mks A A0 eqA n ltM x1 c :: L)
  (s2p A A0 eqA n ltM (mks A A0 eqA n ltM x H')) / forall q : list (Term A n),
inPolySet A A0 eqA n ltM q (mks A `
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_gen `{Univalence} (O : Modality) `{IsAccModality O} (lexgen : forall (i : n`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply reducestar_cb2 with (1 := cs); auto`
- **생성 top5**: `apply CombLinear_mults1 with (1 := cs); auto`(-2.56) · `apply CombLinear_mults2 with (1 := cs); auto`(-3.58) · `apply CombLinear_compo with (1 := cs) (L1 := mks A A0 eqA n ltM x1 c :: L); auto`(-3.59) · `apply CombLinear_s2p with (1 := cs); auto`(-3.64) · `apply CombLinear_compo with (1 := cs) (L1 := L); auto`(-3.85)

### step 10 — ❌miss
- **goal(입력 상태)**: `forall q : list (Term A n),
inPolySet A A0 eqA n ltM q (mks A A0 eqA n ltM x1 c :: L) ->
CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (mks A A0 eqA n ltM
     (mults multA (n:=n)
        (u`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_gen `{Univalence} (O : Modality) `{IsAccModality O} (lexgen : forall (i : n`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros q H'1; inversion H'1; auto`
- **생성 top5**: `intros q H'1`(-2.03) · `intros x2 H'1`(-2.45) · `intros q H'1; elim H'1; clear H'1; intros H'1; auto`(-3.61) · `case c`(-3.69) · `intros q; case q; simpl in |- *`(-3.75)

### step 11 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (mks A A0 eqA n ltM
     (mults multA (n:=n)
        (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM x1 c)) x1)
     (canonical_mults A A0 A1 e`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `2: apply CombLinear_id with (1 := cs); auto`
- **생성 top5**: `rewrite H0; auto`(-3.05) · `rewrite H0; rewrite H2; auto`(-3.60) · `rewrite H0`(-3.80) · `apply unit_nZ with (1 := cs); auto`(-4.01) · `rewrite H0; simpl in |- *; auto`(-5.10)

### step 12 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (mks A A0 eqA n ltM
     (mults multA (n:=n)
        (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM x1 c)) x1)
     (canonical_mults A A0 A1 e`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `2: apply inskip; auto`
- **생성 top5**: `rewrite H0; auto`(-3.32) · `intros q H'1; inversion H'1; auto`(-3.60) · `2: apply CombLinear_id with (1 := cs); auto`(-4.64) · `rewrite H0; rewrite H2; auto`(-4.69) · `apply CombLinear_compo with (1 := cs) (L1 := mks A A0 eqA n ltM x1 c :: L); auto`(-6.06)

### step 13 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (mks A A0 eqA n ltM
     (mults multA (n:=n)
        (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM x1 c)) x1)
     (canonical_mults A A0 A1 e`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `generalize c H2; case x1; auto`
- **생성 top5**: `rewrite H0; auto`(-3.14) · `rewrite H0; rewrite H2; auto`(-3.38) · `apply reducestar_cb1 with (1 := cs); auto`(-4.43) · `apply CombLinear_mults1 with (1 := cs); auto`(-4.49) · `rewrite H0, H2; auto`(-4.80)

### step 14 — ❌miss
- **goal(입력 상태)**: `forall c0 : canonical A0 eqA ltM nil,
pX (A:=A) (n:=n) a p0 = nil ->
CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (mks A A0 eqA n ltM
     (mults multA (n:=n)
        (unit A A0 A1 eqA divA`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros c0 H'2; inversion H'2`
- **생성 top5**: `simpl in |- *`(-4.14) · `simpl in |- *; auto`(-4.19) · `intros t l c0 H'4`(-4.68) · `intros t l c0 H'5`(-5.19) · `intros t l c0 H'5; inversion H'5; auto`(-6.56)

### step 15 — ❌miss
- **goal(입력 상태)**: `forall (t : Term A n) (l : list (Term A n))
  (c0 : canonical A0 eqA ltM (t :: l)),
pX (A:=A) (n:=n) a p0 = t :: l ->
CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (mks A A0 eqA n ltM
     (`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon`
- **retrieval premise top3**: `Program Lemma transfer_eval n (t: Term et nat n) (v: Vars et B nat): e` ; `Program Lemma transfer_eval' n (t: Term et nat n) (v: Vars et B nat): ` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) `
- **gold**: `intros a0 l c0 H'2`
- **생성 top5**: `intros t l c0 H'2`(-2.92) · `intros t l c0 H'2; inversion H'2`(-3.75) · `intros t l c0 H'2; inversion H'2; auto`(-4.20) · `simpl in |- *`(-4.51) · `intros t l c' H'2`(-4.57)

### step 16 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (mks A A0 eqA n ltM
     (mults multA (n:=n)
        (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (a0 :: l) c0))
        (a0 :: l))
     (ca`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `cut (~ zeroP (A:=A) A0 eqA (n:=n) (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (a0 :: l) c0))); [ intros nZu | idtac ]; auto`
- **생성 top5**: `rewrite H'2`(-3.25) · `rewrite H'2; clear H'2`(-4.06) · `rewrite H'2; simpl in |- *`(-4.26) · `case c0; simpl in |- *`(-4.57) · `rewrite H'2; auto`(-4.79)

### step 17 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (mks A A0 eqA n ltM
     (mults multA (n:=n)
        (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (a0 :: l) c0))
        (a0 :: l))
     (ca`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply CombLinear_1 with (a := divTerm (A:=A) (A0:=A0) (eqA:=eqA) divA (n:=n) (T1 A1 n) (b:=unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (pX a0 l) c0)) nZu) (p := pO A n) (q := mults (A:=A) multA (n:=n) (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (pX a0 l) c0)) (pX a0 l)); auto`
- **생성 top5**: `elim nZu; auto`(-3.31) · `elim nZu`(-4.35) · `elim nZu; simpl in |- *; auto`(-4.62) · `apply CombLinear_mults1 with (1 := cs); auto`(-4.69) · `apply CombLinear_compo with (1 := cs); auto`(-5.12)

### step 18 — 🔶topk
- **goal(입력 상태)**: `inPolySet A A0 eqA n ltM
  (mults multA (n:=n)
     (unit A A0 A1 eqA divA n ltM
        (mks A A0 eqA n ltM (pX (A:=A) (n:=n) a0 l) c0))
     (pX (A:=A) (n:=n) a0 l))
  (mks A A0 eqA n ltM
     (mult`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `simpl in |- *; auto`
- **생성 top5**: `rewrite H0; auto`(-3.18) · `rewrite H0`(-3.78) · `rewrite H0; simpl in |- *; auto`(-4.38) · `rewrite H0; rewrite H2; auto`(-4.54) · `simpl in |- *`(-4.64)

### step 19 — ❌miss
- **goal(입력 상태)**: `inPolySet A A0 eqA n ltM
  (pX (A:=A) (n:=n)
     (multTerm multA (n:=n)
        ((let
            (a1, m) as p1
             return (canonical A0 eqA ltM (p1 :: l) -> Term A n) := a0 in
          fun`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon`
- **retrieval premise top3**: `Theorem Bparse_correct: forall b m e (BASE: 2 <= Zpos b), let base := ` ; `Lemma AlmostInExists : forall (e d:Q) x (s:FinEnum X), e < d -> FinSub` ; `Lemma cmp_of_comparison_swap: forall c x, cmp_of_comparison (swap_comp`
- **gold**: `change (inPolySet A A0 eqA n ltM (pX (multTerm (A:=A) multA (n:=n) (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (pX a0 l) c0)) a0) (mults (A:=A) multA (n:=n) (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (pX a0 l) c0)) l)) (exist (fun a1 => canonical A0 eqA ltM a1) (pX (multTerm (A:=A) multA (n:=n) (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (a0 :: l) c0)) a0) (mults (A:=A) multA (n:=n) (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (a0 :: l) c0)) l)) (canonical_mults A A0 A1 eqA plusA invA minusA multA divA cs eqA_dec n ltM os (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (pX a0 l) c0)) (pX a0 l) (unit_nZ _ _ _ _ _ _ _ _ _ cs _ ltM (mks A A0 eqA n ltM (pX a0 l) c0)) c0) :: L)) in |- *`
- **생성 top5**: `simpl in |- *; auto`(-2.70) · `rewrite H0; auto`(-3.50) · `rewrite H0; simpl in |- *; auto`(-3.78) · `simpl in |- *`(-3.89) · `unfold eqP in |- *`(-4.08)

### step 20 — ❌miss
- **goal(입력 상태)**: `inPolySet A A0 eqA n ltM
  (pX (A:=A) (n:=n)
     (multTerm multA (n:=n)
        (unit A A0 A1 eqA divA n ltM
           (mks A A0 eqA n ltM (pX (A:=A) (n:=n) a0 l) c0)) a0)
     (mults multA (n:=n)
 `
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma HausdorffBallHausdorffBallStrong : forall (e:Q) (a b:FinEnum), b`
- **gold**: `apply incons; auto`
- **생성 top5**: `simpl in |- *; auto`(-3.25) · `simpl in |- *`(-3.95) · `rewrite H0; auto`(-4.54) · `unfold eqP in |- *`(-5.25) · `apply inPolySet_plus`(-5.47)

### step 21 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec
  (mks A A0 eqA n ltM
     (mults multA (n:=n)
        (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (a0 :: l) c0))
        (a0 :: l))
     (ca`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply CombLinear_0; auto`
- **생성 top5**: `simpl in |- *; auto`(-2.58) · `rewrite H0; auto`(-2.96) · `rewrite H0`(-3.15) · `simpl in |- *`(-3.72) · `rewrite H0; rewrite H2; auto`(-3.81)

### step 22 — ❌miss
- **goal(입력 상태)**: `eqP A eqA n (pX (A:=A) (n:=n) a p0)
  (pluspf A0 (eqA:=eqA) plusA eqA_dec (ltM:=ltM) ltM_dec
     (mults multA (n:=n)
        (divTerm (A0:=A0) (eqA:=eqA) divA (n:=n) (T1 A1 n)
           (b:=unit A A`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply (eqp_trans _ _ _ _ _ _ _ _ _ cs n) with (y := mults (A:=A) multA (n:=n) (divTerm (A:=A) (A0:=A0) (eqA:=eqA) divA (n:=n) (T1 A1 n) (b:=unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (a0 :: l) c0)) nZu) (mults (A:=A) multA (n:=n) (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (a0 :: l) c0)) (a0 :: l))); auto`
- **생성 top5**: `simpl in |- *; auto`(-2.52) · `rewrite H0; auto`(-2.65) · `rewrite H0`(-3.02) · `rewrite H0; simpl in |- *; auto`(-3.48) · `simpl in |- *`(-3.63)

### step 23 — ❌miss
- **goal(입력 상태)**: `eqP A eqA n (pX (A:=A) (n:=n) a p0)
  (mults multA (n:=n)
     (divTerm (A0:=A0) (eqA:=eqA) divA (n:=n) (T1 A1 n)
        (b:=unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (a0 :: l) c0))
        nZu`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `2: apply (eqp_sym _ _ _ _ _ _ _ _ _ cs n); auto`
- **생성 top5**: `apply eqp_refl`(-3.21) · `simpl in |- *`(-3.34) · `apply eqP_refl`(-3.79) · `unfold eqP in |- *`(-4.19) · `simpl in |- *; ring`(-4.64)

### step 24 — ❌miss
- **goal(입력 상태)**: `eqP A eqA n (pX (A:=A) (n:=n) a p0)
  (mults multA (n:=n)
     (divTerm (A0:=A0) (eqA:=eqA) divA (n:=n) (T1 A1 n)
        (b:=unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (a0 :: l) c0))
        nZu`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply (eqp_trans _ _ _ _ _ _ _ _ _ cs n) with (y := mults (A:=A) multA (n:=n) (multTerm (A:=A) multA (n:=n) (divTerm (A:=A) (A0:=A0) (eqA:=eqA) divA (n:=n) (T1 A1 n) (b:=unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (a0 :: l) c0)) nZu) (unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (a0 :: l) c0))) (a0 :: l)); auto`
- **생성 top5**: `2: apply (eqp_sym _ _ _ _ _ _ _ _ _ cs n); auto`(-2.63) · `2: apply (eqp_trans _ _ _ _ _ _ _ _ _ cs n); auto`(-3.99) · `rewrite H0; auto`(-4.11) · `apply eqp_refl`(-4.11) · `simpl in |- *`(-4.50)

### step 25 — ❌miss
- **goal(입력 상태)**: `eqP A eqA n (pX (A:=A) (n:=n) a p0)
  (mults multA (n:=n)
     (multTerm multA (n:=n)
        (divTerm (A0:=A0) (eqA:=eqA) divA (n:=n) (T1 A1 n)
           (b:=unit A A0 A1 eqA divA n ltM (mks A A0 eq`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply (eqp_trans _ _ _ _ _ _ _ _ _ cs n) with (y := mults (A:=A) multA (n:=n) (T1 A1 n) (a0 :: l)); auto`
- **생성 top5**: `2: apply (eqp_sym _ _ _ _ _ _ _ _ _ cs n); auto`(-0.82) · `3: apply (eqp_sym _ _ _ _ _ _ _ _ _ cs n); auto`(-3.60) · `apply CombLinear_mults1 with (1 := cs); auto`(-4.36) · `2: apply (eqp_trans _ _ _ _ _ _ _ _ _ cs n); auto`(-4.39) · `apply eqP_refl`(-4.41)

### step 26 — ❌miss
- **goal(입력 상태)**: `eqP A eqA n (pX (A:=A) (n:=n) a p0) (mults multA (n:=n) (T1 A1 n) (a0 :: l)) / eqP A eqA n (mults multA (n:=n) (T1 A1 n) (a0 :: l))
  (mults multA (n:=n)
     (multTerm multA (n:=n)
        (divTerm (`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `rewrite H'2; auto`
- **생성 top5**: `2: apply (eqp_sym _ _ _ _ _ _ _ _ _ cs n); auto`(-2.66) · `apply eqp_refl`(-3.18) · `apply (eqp_sym _ _ _ _ _ _ _ _ _ cs n); auto`(-3.98) · `apply unit_nZ with (1 := cs); auto`(-4.20) · `apply eqp_sym; auto`(-4.42)

### step 27 — ❌miss
- **goal(입력 상태)**: `eqP A eqA n (a0 :: l) (mults multA (n:=n) (T1 A1 n) (a0 :: l)) / eqP A eqA n (mults multA (n:=n) (T1 A1 n) (a0 :: l))
  (mults multA (n:=n)
     (multTerm multA (n:=n)
        (divTerm (A0:=A0) (eqA:=`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply (eqp_sym _ _ _ _ _ _ _ _ _ cs n); auto`
- **생성 top5**: `apply eqP_refl`(-3.80) · `simpl in |- *`(-3.81) · `rewrite H0; auto`(-3.83) · `apply eqp_refl`(-4.40) · `unfold eqP in |- *`(-4.45)

### step 28 — ❌miss
- **goal(입력 상태)**: `eqP A eqA n (mults multA (n:=n) (T1 A1 n) (a0 :: l))
  (mults multA (n:=n)
     (multTerm multA (n:=n)
        (divTerm (A0:=A0) (eqA:=eqA) divA (n:=n) (T1 A1 n)
           (b:=unit A A0 A1 eqA divA n`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply mults_comp with (1 := cs); auto`
- **생성 top5**: `rewrite H'2; auto`(-3.16) · `apply (eqp_trans _ _ _ _ _ _ _ _ _ cs n); auto`(-3.84) · `apply eqp_refl`(-4.05) · `rewrite H0; auto`(-4.69) · `apply (eqp_trans _ _ _ _ _ _ _ _ _ cs n) with (y := mults (A:=A) multA (n:=n) (multTerm (A:=A) multA (n:=n) (divTerm (A:=A) (A0:=A0) (eqA:=eqA) divA (n:=n) (T1 A1 n) (b:=unit A A0 A1 eqA divA n l`(-4.73)

### step 29 — ❌miss
- **goal(입력 상태)**: `eqTerm eqA (n:=n) (T1 A1 n)
  (multTerm multA (n:=n)
     (divTerm (A0:=A0) (eqA:=eqA) divA (n:=n) (T1 A1 n)
        (b:=unit A A0 A1 eqA divA n ltM (mks A A0 eqA n ltM (a0 :: l) c0))
        nZu) (un`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply divTerm_on_eqT with (1 := cs); auto`
- **생성 top5**: `apply unit_nZ with (1 := cs); auto`(-1.71) · `rewrite H'2; auto`(-2.91) · `apply mults_comp with (1 := cs); auto`(-3.77) · `apply eqp_refl`(-4.34) · `apply (eqp_trans _ _ _ _ _ _ _ _ _ cs n); auto`(-4.38)

## buchberger-theories-BuchRed.v · proof#6 — `Definition nsep_iff_trunc_to_O (n : trunc_index) (O : Modality) `{Lex O} (A : Type) : In (nSep n O) A <-> IsTruncMap n (to O A).`  (13 steps)


### step 0 — 🔶topk
- **goal(입력 상태)**: `forall (L : list (poly A0 eqA ltM)) (p q : poly A0 eqA ltM),
zerop A A0 eqA n ltM p ->
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q (p :: L) ->
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q L`
- **retrieval 증명 top2**: `Definition lex_from_ispullback_connmap_mapino_commsq (H : forall {A B C D} (f : A -> B) (g` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `Proof using os minusA invA divA cs A1`
- **생성 top5**: `Proof`(-0.53) · `Proof using os minusA invA divA cs A1`(-2.63) · `Proof using os minusA invA divA cs`(-3.07) · `Proof using os`(-3.28) · `Proof using os cs`(-4.36)

### step 1 — ❌miss
- **goal(입력 상태)**: `forall (L : list (poly A0 eqA ltM)) (p q : poly A0 eqA ltM),
zerop A A0 eqA n ltM p ->
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q (p :: L) ->
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q L`
- **retrieval 증명 top2**: `Definition lex_from_ispullback_connmap_mapino_commsq (H : forall {A B C D} (f : A -> B) (g` ; `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y :`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros L p q H' H'0`
- **생성 top5**: `intros L p q H H0`(-2.02) · `intros L p q H0 H1`(-3.48) · `intros L p q H`(-4.73) · `intros L p q H H'`(-4.79) · `intros L p q H1 H2`(-4.86)

### step 2 — ❌miss
- **goal(입력 상태)**: `Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec q L`
- **retrieval 증명 top2**: `Definition lex_from_ispullback_connmap_mapino_commsq (H : forall {A B C D} (f : A -> B) (g` ; `Definition lex_gen `{Univalence} (O : Modality) `{IsAccModality O} (lexgen : forall (i : n`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply Cb_comp with (L1 := p :: L); auto`
- **생성 top5**: `elim H'0`(-3.80) · `apply Cb_trans with (1 := cs) (b := p); auto`(-4.02) · `elim H'0; auto`(-4.22) · `inversion_clear H'0`(-4.28) · `elim H'0; clear H'0; intros H'0 H'1`(-4.48)

### step 3 — ❌miss
- **goal(입력 상태)**: `forall p0 : poly A0 eqA ltM,
In p0 (p :: L) -> Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec p0 L`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Fixpoint nSep (n : trunc_index) (O : Subuniverse) : Subuniverse := match n with | -2 => O `
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `simpl in |- *; auto`
- **생성 top5**: `intros r H'1`(-3.37) · `intros p0 H'1`(-4.05) · `intros t H'1`(-4.22) · `intros p0 H'0'`(-4.42) · `intros s H'1`(-4.94)

### step 4 — ❌miss
- **goal(입력 상태)**: `forall p0 : poly A0 eqA ltM,
p = p0 \/ In p0 L -> Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec p0 L`
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Fixpoint nSep (n : trunc_index) (O : Subuniverse) : Subuniverse := match n with | -2 => O `
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros p0 H'1; case H'1; [ intros H'2; rewrite <- H'2; clear H'1 | intros H'2; clear H'1 ]; auto`
- **생성 top5**: `intros r H'1`(-4.07) · `intros p0 H'1`(-4.67) · `intros p0 H'0'`(-5.39) · `intros p0 H'00`(-5.87) · `intros p0 [H'1 | H'1]; auto`(-6.13)

### step 5 — ❌miss
- **goal(입력 상태)**: `Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec p L / Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec p0 L`
- **retrieval 증명 top2**: `Definition lex_gen `{Univalence} (O : Modality) `{IsAccModality O} (lexgen : forall (i : n` ; `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `generalize H'; case p; simpl in |- *; auto`
- **생성 top5**: `rewrite H'2; auto`(-1.63) · `rewrite <- H'2; auto`(-2.54) · `rewrite H'2`(-3.75) · `rewrite H'2; simpl in |- *; auto`(-4.35) · `case H'0; auto`(-4.35)

### step 6 — 🔶topk
- **goal(입력 상태)**: `forall (x : list (Term A n)) (c : canonical A0 eqA ltM x),
match x as l return (canonical A0 eqA ltM l -> Prop) with
| nil => fun _ : canonical A0 eqA ltM nil => True
| t :: l => fun _ : canonical A0 `
- **retrieval 증명 top2**: `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A ` ; `Fixpoint nSep (n : trunc_index) (O : Subuniverse) : Subuniverse := match n with | -2 => O `
- **retrieval premise top3**: `Lemma cmp_of_comparison_swap: forall c x, cmp_of_comparison (swap_comp` ; `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) `
- **gold**: `intros x; case x; simpl in |- *; auto`
- **생성 top5**: `intros x c H'1`(-3.58) · `intros x c H'1; case H'1; auto`(-4.05) · `intros x; case x; simpl in |- *; auto`(-4.24) · `-`(-4.27) · `intros x c H'1; case H'1`(-4.36)

### step 7 — ❌miss
- **goal(입력 상태)**: `canonical A0 eqA ltM nil ->
True -> CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec L nil / forall (t : Term A n) (l : list (Term A n)),
canonical A0 eqA ltM (t :: l) ->
False -> CombLinear A A0`
- **retrieval 증명 top2**: `Fixpoint nSep (n : trunc_index) (O : Subuniverse) : Subuniverse := match n with | -2 => O ` ; `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A `
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros H'1 H'3; try assumption`
- **생성 top5**: `intros _ _; auto`(-2.65) · `intros _ _`(-2.76) · `intros; auto`(-3.44) · `intros _ _; constructor`(-3.54) · `intros _; auto`(-3.89)

### step 8 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec L nil / forall (t : Term A n) (l : list (Term A n)),
canonical A0 eqA ltM (t :: l) ->
False -> CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_d`
- **retrieval 증명 top2**: `Fixpoint nSep (n : trunc_index) (O : Subuniverse) : Subuniverse := match n with | -2 => O ` ; `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A `
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `change (CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec L (pO A n)) in |- *`
- **생성 top5**: `case H'1; auto`(-3.81) · `elim H'1; auto`(-3.83) · `elim H'1`(-4.23) · `unfold CombLinear in |- *`(-4.43) · `apply CombLinear_nil`(-4.49)

### step 9 — ❌miss
- **goal(입력 상태)**: `CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec L (pO A n) / forall (t : Term A n) (l : list (Term A n)),
canonical A0 eqA ltM (t :: l) ->
False -> CombLinear A A0 eqA plusA multA eqA_dec n ltM `
- **retrieval 증명 top2**: `Fixpoint nSep (n : trunc_index) (O : Subuniverse) : Subuniverse := match n with | -2 => O ` ; `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A `
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply CombLinear_0; auto`
- **생성 top5**: `unfold CombLinear in |- *`(-3.89) · `simpl in |- *`(-4.74) · `simpl in |- *; auto`(-5.16) · `unfold pO in |- *`(-5.32) · `elim H'0; auto`(-5.83)

### step 10 — ❌miss
- **goal(입력 상태)**: `forall (t : Term A n) (l : list (Term A n)),
canonical A0 eqA ltM (t :: l) ->
False -> CombLinear A A0 eqA plusA multA eqA_dec n ltM ltM_dec L (t :: l) / Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec `
- **retrieval 증명 top2**: `Fixpoint nSep (n : trunc_index) (O : Subuniverse) : Subuniverse := match n with | -2 => O ` ; `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A `
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros a l H'1 H'3; elim H'3; auto`
- **생성 top5**: `intros t l H'1 H'3; try assumption`(-2.91) · `intros t; case t; simpl in |- *; auto`(-4.10) · `intros t l H'1 H'3`(-4.50) · `intros t l; case l; simpl in |- *; auto`(-4.69) · `intros t L' H'1 H'3; try assumption`(-4.78)

### step 11 — ❌miss
- **goal(입력 상태)**: `Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec p0 L`
- **retrieval 증명 top2**: `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsCon` ; `Definition lex_gen `{Univalence} (O : Modality) `{IsAccModality O} (lexgen : forall (i : n`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply Cb_id with (1 := cs); auto`
- **생성 top5**: `apply Cb_cons_addEnd; auto`(-2.33) · `generalize H'0; case p0; simpl in |- *; auto`(-3.69) · `apply Cb_cons; auto`(-3.77) · `generalize H'0 H'2; case p0; simpl in |- *; auto`(-3.90) · `generalize H'2 H'0; case p0; simpl in |- *; auto`(-4.60)

## buchberger-theories-BuchRed.v · proof#7 — `Definition extendable_over_unit (n : nat) (A : Type@{a}) (C : Unit -> Type@{i}) (D : forall u, C u -> Type@{j}) (ext : ExtendableAlong@{a a i k} n (co`  (4 steps)


### step 0 — 🔶topk
- **goal(입력 상태)**: `forall (p : poly A0 eqA ltM) (L1 : list (poly A0 eqA ltM)),
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec p L1 ->
forall L2 : list (poly A0 eqA ltM),
(forall q : poly A0 eqA ltM,
 In q L1 -> Cb A A0 e`
- **retrieval 증명 top2**: `Definition lex_gen `{Univalence} (O : Modality) `{IsAccModality O} (lexgen : forall (i : n` ; `Definition lex_from_ispullback_connmap_mapino_commsq (H : forall {A B C D} (f : A -> B) (g`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `Proof using os minusA invA divA cs A1`
- **생성 top5**: `Proof`(-0.42) · `Proof`(-2.88) · `Proof using os minusA invA divA cs A1`(-3.21) · `Proof using os`(-3.90) · `Proof using os minusA invA divA cs`(-4.17)

### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (p : poly A0 eqA ltM) (L1 : list (poly A0 eqA ltM)),
Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec p L1 ->
forall L2 : list (poly A0 eqA ltM),
(forall q : poly A0 eqA ltM,
 In q L1 -> Cb A A0 e`
- **retrieval 증명 top2**: `Definition lex_gen `{Univalence} (O : Modality) `{IsAccModality O} (lexgen : forall (i : n` ; `Definition lex_from_ispullback_connmap_mapino_commsq (H : forall {A B C D} (f : A -> B) (g`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `intros p L1 H' L2 H'0`
- **생성 top5**: `intros p L1 H L2 H0`(-5.23) · `intros p L1 H1 L2 H2`(-5.61) · `intros L1 L2 H L3`(-6.15) · `intros L1 L2 H1 L2' H2`(-6.70) · `intros L1 L2 H' L2' H'0`(-6.71)

### step 2 — ❌miss
- **goal(입력 상태)**: `Cb A A0 eqA plusA multA eqA_dec n ltM ltM_dec p L2`
- **retrieval 증명 top2**: `Definition lex_gen `{Univalence} (O : Modality) `{IsAccModality O} (lexgen : forall (i : n` ; `Definition lex_from_ispullback_connmap_mapino_commsq (H : forall {A B C D} (f : A -> B) (g`
- **retrieval premise top3**: `Lemma FinEnum_ball_eq : forall a b : list X, (forall e : Qpos, FinEnum` ; `Lemma FinEnum_ball_e_wd : forall (e1 e2:Q) (a b : list X), (e1 == e2) ` ; `Lemma Qpower_inc : forall (n : nat) (a b : Q), 0 < a -> a <= b -> a ^ `
- **gold**: `apply Cb_comp with (L1 := L1); auto`
- **생성 top5**: `apply Cb_trans with (1 := cs) (b := p); auto`(-3.36) · `apply Cb_trans with (1 := H')`(-4.30) · `apply Cb_trans with (1 := H'); auto`(-4.37) · `apply CombLinear_compo with (1 := cs) (L1 := L1); auto`(-4.55) · `apply Cb_trans with (1 := cs) (b := L1); auto`(-4.64)

## buchberger-theories-Dickson.v · proof#0 — `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a.`  (3 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall R : nat -> nat -> Type,
(forall n : nat, R 0 n) ->
(forall n : nat, R (S n) 0) ->
(forall n m : nat, R n m -> R (S n) (S m)) -> forall n m : nat, R n m`
- **retrieval premise top3**: `Lemma bpow_log_neg: forall (base: radix) n, n < 0 -> (bpow base n <= b` ; `Lemma bpow_log_pos: forall (base: radix) n, 0 < n -> (bpow radix2 (n *` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * `
- **gold**: `simple induction n; simple induction m; auto`
- **생성 top5**: `intros`(-2.22) · `intros`(-2.27) · `auto`(-3.28) · `reflexivity`(-3.76) · `intros; reflexivity`(-3.83)

## buchberger-theories-Dickson.v · proof#1 — `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) * (forall c, IsIndexedBy (j a c) (b c)) end.`  (6 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `DecRel nat lt`
- **retrieval 증명 top1**: `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma bpow_log_neg: forall (base: radix) n, n < 0 -> (bpow base n <= b` ; `Lemma shiftl_spec_from_nat_pow `{SemiRing A} `{SemiRing B} `{!NatPowSp`
- **gold**: `red in |- *; intros; pattern x, y in |- *`
- **생성 top5**: `destruct x`(-4.12) · `simple induction x`(-4.17) · `intros x w`(-4.24) · `refine (Build_DecRel _ _ _)`(-5.94) · `refine (Build_DecRel _ _ _ _)`(-6.52)

### step 2 — ❌miss
- **goal(입력 상태)**: `(fun n n0 : nat => {n < n0} + {~ n < n0}) x y`
- **retrieval 증명 top1**: `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma bpow_log_neg: forall (base: radix) n, n < 0 -> (bpow base n <= b` ; `Lemma bpow_log_pos: forall (base: radix) n, 0 < n -> (bpow radix2 (n *` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * `
- **gold**: `apply nat_double_ind_set; auto with arith`
- **생성 top5**: `elim x; elim y; auto`(-4.53) · `simple induction x; simple induction y; auto`(-5.29) · `simple induction x; simple induction y`(-5.33) · `apply Nat.lt_eq_cases`(-5.41) · `induction x; destruct y; auto`(-5.75)

### step 3 — ❌miss
- **goal(입력 상태)**: `forall n : nat, {0 < n} + {~ 0 < n} / forall n m : nat, {n < m} + {~ n < m} -> {S n < S m} + {~ S n < S m}`
- **retrieval 증명 top1**: `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma bpow_log_neg: forall (base: radix) n, n < 0 -> (bpow base n <= b` ; `Lemma bpow_log_pos: forall (base: radix) n, 0 < n -> (bpow radix2 (n *` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * `
- **gold**: `intros n; case n; auto with arith`
- **생성 top5**: `auto with arith`(-2.22) · `simple induction n; auto with arith`(-2.76) · `apply nat_dec`(-4.07) · `simple induction n; auto`(-4.24) · `apply nat_double_ind_set; auto with arith`(-4.55)

### step 4 — ❌miss
- **goal(입력 상태)**: `forall n m : nat, {n < m} + {~ n < m} -> {S n < S m} + {~ S n < S m}`
- **retrieval 증명 top1**: `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma bpow_log_neg: forall (base: radix) n, n < 0 -> (bpow base n <= b` ; `Lemma bpow_log_pos: forall (base: radix) n, 0 < n -> (bpow radix2 (n *`
- **gold**: `intros n m H'; case H'; auto with arith`
- **생성 top5**: `intros n m H`(-2.92) · `intros n m H; case H; auto with arith`(-3.39) · `simple induction m; auto with arith`(-3.51) · `intros`(-3.67) · `intros n; case n; auto with arith`(-4.00)

## buchberger-theories-Dickson.v · proof#2 — `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b.`  (3 steps)


### step 0 — ❌miss
- **goal(입력 상태)**: `well_founded prod_lt`
- **retrieval 증명 top2**: `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) *` ; `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma bpow_log_neg: forall (base: radix) n, n < 0 -> (bpow base n <= b` ; `Lemma shiftl_spec_from_nat_pow `{SemiRing A} `{SemiRing B} `{!NatPowSp`
- **gold**: `Proof using wfgt`
- **생성 top5**: `Proof`(-0.15) · `Proof`(-2.37) · `Proof`(-5.64) · `Proof`(-6.15) · `destruct p`(-6.40)

### step 1 — ❌miss
- **goal(입력 상태)**: `well_founded prod_lt`
- **retrieval 증명 top2**: `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) *` ; `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma bpow_log_neg: forall (base: radix) n, n < 0 -> (bpow base n <= b` ; `Lemma shiftl_spec_from_nat_pow `{SemiRing A} `{SemiRing B} `{!NatPowSp`
- **gold**: `unfold prod_lt in |- *; apply wf_inverse_image with (B := A); auto`
- **생성 top5**: `destruct p`(-2.97) · `destruct p`(-2.98) · `induction p`(-3.51) · `destruct p`(-3.83) · `induction p`(-3.95)

## buchberger-theories-Dickson.v · proof#3 — `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a b : A) (f : a $-> b), F a $-> F b }.`  (18 steps)


### step 0 — ❌miss
- **goal(입력 상태)**: `forall (l : list (A * B)) (a : A * B),
ExistsL B (fun x : B => R x (snd a)) (sndL l) -> MinD l -> GBarlR (a :: l)`
- **retrieval 증명 top2**: `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. ` ; `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.`
- **gold**: `Proof using declt`
- **생성 top5**: `Proof`(-0.12) · `Proof`(-3.74) · `Proof using wfgt`(-4.49) · `Proof with auto`(-5.36) · `Proof using wfgt`(-5.74)

### step 1 — ❌miss
- **goal(입력 상태)**: `forall (l : list (A * B)) (a : A * B),
ExistsL B (fun x : B => R x (snd a)) (sndL l) -> MinD l -> GBarlR (a :: l)`
- **retrieval 증명 top2**: `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. ` ; `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.`
- **gold**: `intros l; elim l; simpl in |- *; auto`
- **생성 top5**: `simple induction l`(-2.63) · `intros`(-3.64) · `simple induction 1`(-3.71) · `induction l`(-3.76) · `simple induction l; intros`(-3.98)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall a : A * B,
ExistsL B (fun x : B => R x (snd a)) nil -> MinD nil -> GBarlR (a :: nil) / forall (a : A * B) (l0 : list (A * B)),
(forall a0 : A * B,
 ExistsL B (fun x : B => R x (snd a0)) (sndL l`
- **retrieval 증명 top2**: `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. ` ; `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.`
- **gold**: `intros a H' H'0; inversion H'`
- **생성 top5**: `-`(-3.18) · `+`(-4.93) · `intros [a b]; simpl in |- *; auto`(-6.20) · `intros (a, b); red in |- *`(-6.23) · `intros (a, b); simpl in |- *; auto`(-6.31)

### step 3 — ❌miss
- **goal(입력 상태)**: `forall (a : A * B) (l0 : list (A * B)),
(forall a0 : A * B,
 ExistsL B (fun x : B => R x (snd a0)) (sndL l0) ->
 MinD l0 -> GBarlR (a0 :: l0)) ->
forall a0 : A * B,
ExistsL B (fun x : B => R x (snd a0`
- **retrieval 증명 top2**: `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si` ; `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.`
- **gold**: `intros a l0 H' a0 H'0 H'1; inversion H'0`
- **생성 top5**: `intros a0 l0 H' H'0; inversion H'`(-6.60) · `intros [a b] l' H' H'0; inversion H'`(-7.01) · `intros [a b] l' H' H'0; inversion H'0`(-7.02) · `intros a0 l0 H' a1 H'0; inversion H'`(-7.04) · `intros a0 l0 H' a1 H'0; inversion H'0`(-7.08)

### step 4 — ❌miss
- **goal(입력 상태)**: `GBarlR (a0 :: a :: l0) / GBarlR (a0 :: a :: l0)`
- **retrieval 증명 top2**: `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. ` ; `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) *`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `simpl in H0; simpl in H1; simpl in H`
- **생성 top5**: `-`(-2.72) · `inversion H'1`(-4.66) · `left; auto`(-4.69) · `inversion H'0`(-5.16) · `elim H'1; auto`(-5.43)

### step 5 — ❌miss
- **goal(입력 상태)**: `GBarlR (a0 :: a :: l0) / GBarlR (a0 :: a :: l0)`
- **retrieval 증명 top2**: `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. ` ; `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) *`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `case (declt (fst a0) (fst a)); intros LtE`
- **생성 top5**: `-`(-3.24) · `rewrite <- H`(-4.11) · `rewrite H; rewrite H1`(-5.12) · `rewrite H; rewrite H1; auto`(-5.50) · `rewrite <- H in H0`(-5.81)

### step 6 — ❌miss
- **goal(입력 상태)**: `GBarlR (a0 :: a :: l0) / GBarlR (a0 :: a :: l0) / GBarlR (a0 :: a :: l0)`
- **retrieval 증명 top2**: `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. ` ; `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) *`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `change (GBarlR ((a0 :: nil) ++ (a :: nil) ++ l0)) in |- *; auto`
- **생성 top5**: `-`(-3.13) · `left; auto`(-4.20) · `rewrite H in LtE`(-5.18) · `rewrite H in LtE`(-6.02) · `rewrite <- H in H0`(-6.47)

### step 7 — ❌miss
- **goal(입력 상태)**: `GBarlR ((a0 :: nil) ++ (a :: nil) ++ l0) / GBarlR (a0 :: a :: l0) / GBarlR (a0 :: a :: l0)`
- **retrieval 증명 top2**: `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. ` ; `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) *`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `red in |- *; apply monGRBar; simpl in |- *; auto`
- **생성 top5**: `right; auto`(-3.98) · `rewrite <- app_assoc`(-4.44) · `rewrite app_assoc`(-4.51) · `rewrite app_assoc; auto`(-5.01) · `change (GBarlR ((a0 :: nil) ++ (a :: nil) ++ l0)) in |- *; auto`(-5.66)

### step 8 — ❌miss
- **goal(입력 상태)**: `GRBar (A * B) (ProdRel A B leq R) (a0 :: l0) / GBarlR (a0 :: a :: l0) / GBarlR (a0 :: a :: l0)`
- **retrieval 증명 top2**: `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. ` ; `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) *`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `inversion H'1; auto`
- **생성 top5**: `red in |- *; apply monGRBar; simpl in |- *; auto`(-3.86) · `left; auto`(-4.17) · `red in |- *`(-4.39) · `apply GRBar_cons; auto`(-5.01) · `red in |- *; apply grGRBar; simpl in |- *; auto`(-5.52)

### step 9 — ❌miss
- **goal(입력 상태)**: `GBarlR (a0 :: a :: l0) / GBarlR (a0 :: a :: l0)`
- **retrieval 증명 top2**: `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. ` ; `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) *`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `red in |- *; red in |- *; apply Base`
- **생성 top5**: `red in |- *; apply monGRBar; simpl in |- *; auto`(-2.96) · `elim LtE; auto`(-3.11) · `left; auto`(-3.41) · `inversion H'1; auto`(-3.41) · `right; auto`(-3.48)

### step 10 — ❌miss
- **goal(입력 상태)**: `GoodR (A * B) (ProdRel A B leq R) (a0 :: a :: l0) / GBarlR (a0 :: a :: l0)`
- **retrieval 증명 top2**: `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. ` ; `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) *`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `apply FoundG`
- **생성 top5**: `constructor; auto`(-3.34) · `red in |- *; apply Base`(-3.51) · `apply Base`(-4.22) · `elim LtE; auto`(-4.45) · `apply Base; auto`(-4.68)

### step 11 — ❌miss
- **goal(입력 상태)**: `ExistsL (A * B) (fun x : A * B => ProdRel A B leq R x a0) (a :: l0) / GBarlR (a0 :: a :: l0)`
- **retrieval 증명 top2**: `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. ` ; `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) *`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `apply FoundE`
- **생성 top5**: `apply ExistsL_cons; auto`(-2.20) · `constructor; auto`(-3.34) · `apply ExistsL_cons`(-3.35) · `apply ExistsL_cons; simpl in |- *; auto`(-4.37) · `apply ExistsLCons; auto`(-4.41)

### step 12 — ❌miss
- **goal(입력 상태)**: `ProdRel A B leq R a a0 / GBarlR (a0 :: a :: l0)`
- **retrieval 증명 top2**: `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. ` ; `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) *`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `unfold ProdRel in |- *; split; auto`
- **생성 top5**: `split; auto`(-2.84) · `split`(-3.48) · `red in |- *`(-3.93) · `apply Base`(-3.94) · `red in |- *; auto`(-4.18)

### step 13 — 🔶topk
- **goal(입력 상태)**: `GBarlR (a0 :: a :: l0)`
- **retrieval 증명 top2**: `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. ` ; `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) *`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `change (GBarlR ((a0 :: nil) ++ (a :: nil) ++ l0)) in |- *; auto`
- **생성 top5**: `red in |- *; apply monGRBar; simpl in |- *; auto`(-4.06) · `red in |- *; apply Base`(-4.13) · `change (GBarlR ((a0 :: a :: nil) ++ l0)) in |- *; auto`(-4.51) · `case (declt (snd a0) (snd a)); intros LtE`(-4.60) · `case (declt (fst a0) (fst a)); intros LtE`(-4.63)

### step 14 — ✅top1
- **goal(입력 상태)**: `GBarlR ((a0 :: nil) ++ (a :: nil) ++ l0)`
- **retrieval 증명 top2**: `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. ` ; `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) *`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `red in |- *; apply monGRBar; simpl in |- *; auto`
- **생성 top5**: `red in |- *; apply monGRBar; simpl in |- *; auto`(-0.68) · `apply monGRBar; simpl in |- *; auto`(-3.52) · `red in |- *; apply monGRBar`(-3.61) · `red in |- *; red in |- *; apply Base`(-3.88) · `red in |- *; apply Base`(-4.14)

### step 15 — 🔶topk
- **goal(입력 상태)**: `GRBar (A * B) (ProdRel A B leq R) (a0 :: l0)`
- **retrieval 증명 top2**: `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. ` ; `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) *`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `inversion H'1; simpl in |- *; auto`
- **생성 top5**: `inversion H'1; auto`(-0.83) · `apply FoundG`(-3.11) · `inversion H'1`(-3.77) · `unfold ProdRel in |- *; split; auto`(-4.06) · `unfold GRBar in |- *`(-4.43)

### step 16 — ❌miss
- **goal(입력 상태)**: `GRBar (A * B) (ProdRel A B leq R) (a0 :: l0)`
- **retrieval 증명 top2**: `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) *` ; `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. `
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `apply H'; auto`
- **생성 top5**: `red in |- *; red in |- *; apply Base`(-2.49) · `case (declt (fst a0) (fst a)); intros LtE`(-2.92) · `red in |- *; apply Base`(-3.27) · `change (GBarlR ((a0 :: nil) ++ (a :: nil) ++ l0)) in |- *; auto`(-3.33) · `red in |- *; apply monGRBar; simpl in |- *; auto`(-4.39)

## buchberger-theories-Dickson.v · proof#4 — `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b).`  (18 steps)


### step 0 — 🔶topk
- **goal(입력 상태)**: `forall l : list B,
GoodR B R l -> forall us : list (A * B), l = sndL us -> MinD us -> GBarlR us`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. `
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `Proof using declt`
- **생성 top5**: `Proof`(-0.80) · `Proof using wfgt`(-1.78) · `Proof using declt`(-2.53) · `Proof using declt wfgt`(-3.24) · `Proof using wfgt declt`(-3.27)

### step 1 — 🔶topk
- **goal(입력 상태)**: `forall l : list B,
GoodR B R l -> forall us : list (A * B), l = sndL us -> MinD us -> GBarlR us`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. `
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `intros l; elim l; auto`
- **생성 top5**: `intros l; elim l; simpl in |- *; auto`(-3.12) · `simple induction l`(-4.05) · `intros l; elim l; auto`(-4.28) · `intros l; elim l`(-4.66) · `intros l; elim l; simpl in |- *`(-4.67)

### step 2 — ❌miss
- **goal(입력 상태)**: `GoodR B R nil ->
forall us : list (A * B), nil = sndL us -> MinD us -> GBarlR us / forall (a : B) (l0 : list B),
(GoodR B R l0 ->
 forall us : list (A * B), l0 = sndL us -> MinD us -> GBarlR us) ->
Go`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `intros H'; inversion H'`
- **생성 top5**: `intros H'; elim H'; auto`(-5.16) · `intros H'; elim H'`(-5.17) · `intros H' us H'0 H'1; inversion H'1; auto`(-5.19) · `intros H' us H'0 H'1`(-5.27) · `intros H' l0 H'0 H'1; inversion H'`(-5.54)

### step 3 — ❌miss
- **goal(입력 상태)**: `forall (a : B) (l0 : list B),
(GoodR B R l0 ->
 forall us : list (A * B), l0 = sndL us -> MinD us -> GBarlR us) ->
GoodR B R (a :: l0) ->
forall us : list (A * B), a :: l0 = sndL us -> MinD us -> GBar`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * `
- **gold**: `intros a l0 H' H'0; inversion H'0; auto`
- **생성 top5**: `intros a l0 H' H'0; inversion H'0`(-4.04) · `intros a H' H'0; inversion H'0`(-4.57) · `intros a l0 H' a0 H'0 H'1; inversion H'1; auto`(-4.65) · `intros a l0 H' H'0 us H'1 H'2`(-4.85) · `intros a l0 H' H'; inversion H'`(-5.12)

### step 4 — ❌miss
- **goal(입력 상태)**: `forall us : list (A * B), a :: l0 = sndL us -> MinD us -> GBarlR us / forall us : list (A * B), a :: l0 = sndL us -> MinD us -> GBarlR us`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `intros us; elim us; simpl in |- *; auto`
- **생성 top5**: `intros us H'1 H'2; inversion H'2; auto`(-4.08) · `intros l1 H' H'0; inversion H'0; auto`(-4.76) · `intros l1 H' H'0; inversion H'0`(-4.92) · `intros l1 H''; inversion H''; auto`(-4.95) · `intros us H'1 H'2`(-4.96)

### step 5 — 🔶topk
- **goal(입력 상태)**: `a :: l0 = nil -> MinD nil -> GBarlR nil / forall (a1 : A * B) (l2 : list (A * B)),
(a :: l0 = sndL l2 -> MinD l2 -> GBarlR l2) ->
a :: l0 = snd a1 :: sndL l2 -> MinD (a1 :: l2) -> GBarlR (a1 :: l2) / `
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `intros; discriminate`
- **생성 top5**: `inversion 1`(-2.65) · `discriminate`(-3.40) · `intros; discriminate`(-3.57) · `inversion 1; auto`(-3.75) · `intros; inversion H`(-4.38)

### step 6 — ❌miss
- **goal(입력 상태)**: `forall (a1 : A * B) (l2 : list (A * B)),
(a :: l0 = sndL l2 -> MinD l2 -> GBarlR l2) ->
a :: l0 = snd a1 :: sndL l2 -> MinD (a1 :: l2) -> GBarlR (a1 :: l2) / forall us : list (A * B), a :: l0 = sndL u`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `intros a1 l2 H'1 H'2 H'3; inversion H'2`
- **생성 top5**: `intros; discriminate`(-2.71) · `intros a1 l2 H'1 H'2; inversion H'2; auto`(-4.71) · `intros a1 l2 H'1 H'2 H'3`(-5.32) · `intros a1 l2 H'1 H'2; inversion H'2`(-5.78) · `intros a1 l2 H'1 H'2`(-5.92)

### step 7 — ❌miss
- **goal(입력 상태)**: `GBarlR (a1 :: l2) / forall us : list (A * B), a :: l0 = sndL us -> MinD us -> GBarlR us`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. `
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `apply lem0; auto`
- **생성 top5**: `inversion H'3; auto`(-2.71) · `inversion H'3`(-3.31) · `elim H'3; auto`(-4.22) · `simpl in H'2; simpl in H'3`(-4.42) · `inversion H'3; simpl in |- *; auto`(-4.52)

### step 8 — ❌miss
- **goal(입력 상태)**: `ExistsL B (fun x : B => R x (snd a1)) (sndL l2) / MinD l2 / forall us : list (A * B), a :: l0 = sndL us -> MinD us -> GBarlR us`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. `
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `rewrite <- H2; rewrite <- H3; auto`
- **생성 top5**: `apply FoundG`(-3.70) · `apply lem0; auto`(-4.01) · `apply ExistsL_exists; auto`(-4.58) · `apply ExistsL_cons; auto`(-4.69) · `apply ExistsL_snd; auto`(-5.32)

### step 9 — ✅top1
- **goal(입력 상태)**: `MinD l2 / forall us : list (A * B), a :: l0 = sndL us -> MinD us -> GBarlR us`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. `
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma injective_preserves_0 : (∀ x, f x = 0 → x = 0) → Injective f.` ; `Lemma round_NE_underflows: forall x, (0 <= x <= bpow radix2 (emin - 1)`
- **gold**: `inversion H'3; auto`
- **생성 top5**: `inversion H'3; auto`(-1.13) · `apply H'1; auto`(-2.37) · `inversion H'3`(-2.49) · `apply H'1`(-3.43) · `apply lem0; auto`(-3.96)

### step 10 — ❌miss
- **goal(입력 상태)**: `forall us : list (A * B), a :: l0 = sndL us -> MinD us -> GBarlR us`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `intros us; elim us; unfold sndL in |- *; simpl in |- *; auto`
- **생성 top5**: `intros; discriminate`(-1.54) · `intros us; elim us; simpl in |- *; auto`(-1.70) · `intros`(-3.89) · `intros; apply lem0; auto`(-4.22) · `intros us; elim us; auto`(-4.23)

### step 11 — ✅top1
- **goal(입력 상태)**: `a :: l0 = nil -> MinD nil -> GBarlR nil / forall (a1 : A * B) (l2 : list (A * B)),
(a :: l0 = map (fun p : A * B => snd p) l2 -> MinD l2 -> GBarlR l2) ->
a :: l0 = snd a1 :: map (fun p : A * B => snd `
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `intros; discriminate`
- **생성 top5**: `intros; discriminate`(-0.32) · `discriminate`(-3.11) · `inversion 1`(-4.89) · `inversion 1; auto`(-4.96) · `intros H'1 H'2; discriminate`(-4.98)

### step 12 — ✅top1
- **goal(입력 상태)**: `forall (a1 : A * B) (l2 : list (A * B)),
(a :: l0 = map (fun p : A * B => snd p) l2 -> MinD l2 -> GBarlR l2) ->
a :: l0 = snd a1 :: map (fun p : A * B => snd p) l2 ->
MinD (a1 :: l2) -> GBarlR (a1 :: `
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a. Proof. si`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `intros a1 l2 H'1 H'2 H'3; inversion H'2`
- **생성 top5**: `intros a1 l2 H'1 H'2 H'3; inversion H'2`(-1.61) · `intros a1 l2 H'1 H'2 H'3; inversion H'2; auto`(-2.85) · `intros; discriminate`(-2.94) · `intros a1 l2 H'1 H'2; inversion H'2`(-3.49) · `intros a1 l2 H'1 H'2 H'3; inversion H'3`(-3.83)

### step 13 — ❌miss
- **goal(입력 상태)**: `GBarlR (a1 :: l2)`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. `
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `change (GBarlR (nil ++ (a1 :: nil) ++ l2)) in |- *`
- **생성 top5**: `apply lem0; auto`(-1.08) · `apply lem1; auto`(-2.15) · `inversion H'3; auto`(-3.58) · `apply lem; auto`(-4.06) · `rewrite <- H2; rewrite <- H3; auto`(-4.16)

### step 14 — ✅top1
- **goal(입력 상태)**: `GBarlR (nil ++ (a1 :: nil) ++ l2)`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. `
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `red in |- *; apply monGRBar; simpl in |- *; auto`
- **생성 top5**: `red in |- *; apply monGRBar; simpl in |- *; auto`(-2.09) · `auto`(-2.99) · `apply monGRBar; simpl in |- *; auto`(-3.31) · `red in |- *; apply monGRBar; auto`(-3.55) · `rewrite <- H2; rewrite <- H3; auto`(-3.78)

### step 15 — ❌miss
- **goal(입력 상태)**: `GRBar (A * B) (ProdRel A B leq R) l2`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. `
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `apply H'; auto`
- **생성 top5**: `inversion H'3; auto`(-1.38) · `inversion H'3; simpl in |- *; auto`(-2.49) · `apply H'1; auto`(-2.61) · `inversion H'3`(-3.02) · `apply H'1`(-3.31)

### step 16 — ✅top1
- **goal(입력 상태)**: `MinD l2`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b. Proof using wfgt. `
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `inversion H'3; auto`
- **생성 top5**: `inversion H'3; auto`(-0.72) · `inversion H'3; simpl in |- *; auto`(-2.26) · `inversion H'3`(-2.98) · `apply H'1; auto`(-3.22) · `apply H'1`(-3.27)

## buchberger-theories-Dickson.v · proof#5 — `Class Is1Cat (A : Type) `{!IsGraph A, !Is2Graph A, !Is01Cat A} := { is01cat_hom : forall (a b : A), Is01Cat (a $-> b) ; is0gpd_hom : forall (a b : A),`  (4 steps)


### step 0 — ✅top1
- **goal(입력 상태)**: `forall us : list (A * B), GoodR B R (sndL us) -> MinD us -> GBarlR us`
- **retrieval 증명 top2**: `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b` ; `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `Proof using declt`
- **생성 top5**: `Proof using declt`(-1.60) · `Proof using wfgt`(-1.75) · `Proof`(-2.16) · `Proof using wfgt declt wR`(-2.24) · `Proof using declt wfgt`(-2.64)

### step 1 — ❌miss
- **goal(입력 상태)**: `forall us : list (A * B), GoodR B R (sndL us) -> MinD us -> GBarlR us`
- **retrieval 증명 top2**: `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b` ; `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `intros us H' H'0`
- **생성 top5**: `intros us; elim us; auto`(-2.47) · `intros us; elim us; simpl in |- *; auto`(-2.86) · `intros l; elim l; auto`(-3.57) · `intros us`(-3.67) · `intros us H'; elim H'; auto`(-4.41)

### step 2 — ❌miss
- **goal(입력 상태)**: `GBarlR us`
- **retrieval 증명 top2**: `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b` ; `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `apply lem1aux with (l := sndL us); auto`
- **생성 top5**: `elim H'0`(-2.30) · `elim H'0; auto`(-2.58) · `induction us`(-4.01) · `red in |- *`(-4.03) · `pattern us in |- *`(-4.04)

## buchberger-theories-Dickson.v · proof#6 — `Definition cat_assoc_opp {A : Type} `{Is1Cat A} {a b c d : A} (f : a $-> b) (g : b $-> c) (h : c $-> d) : h $o (g $o f) $== (h $o g) $o f := (cat_asso`  (12 steps)


### step 0 — 🔶topk
- **goal(입력 상태)**: `forall bs : list B,
GRBar B R bs ->
forall us : list (A * B), bs = sndL us -> MinD us -> GBarlR us`
- **retrieval 증명 top2**: `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b` ; `Class Is1Cat (A : Type) `{!IsGraph A, !Is2Graph A, !Is01Cat A} := { is01cat_hom : forall (`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `Proof using wfgt declt`
- **생성 top5**: `Proof using declt`(-1.01) · `Proof`(-1.39) · `Proof using wfgt`(-2.77) · `Proof using wfgt declt`(-3.25) · `Proof using declt wfgt`(-3.49)

### step 1 — 🔶topk
- **goal(입력 상태)**: `forall bs : list B,
GRBar B R bs ->
forall us : list (A * B), bs = sndL us -> MinD us -> GBarlR us`
- **retrieval 증명 top2**: `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b` ; `Class Is1Cat (A : Type) `{!IsGraph A, !Is2Graph A, !Is01Cat A} := { is01cat_hom : forall (`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `intros bs H'; elim H'; auto`
- **생성 top5**: `simple induction bs`(-3.43) · `simple induction 1`(-3.67) · `intros bs H' us H'0 H'1`(-4.42) · `intros bs H'; elim H'`(-4.57) · `intros l; elim l; auto`(-4.69)

### step 2 — 🔶topk
- **goal(입력 상태)**: `forall l : list B,
GoodR B R l -> forall us : list (A * B), l = sndL us -> MinD us -> GBarlR us / forall l : list B,
(forall a : B, Bar B (GoodR B R) (a :: l)) ->
(forall (a : B) (us : list (A * B)), `
- **retrieval 증명 top2**: `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b` ; `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `intros l H'0 us H'1 H'2`
- **생성 top5**: `intros l H'0 us H'1`(-4.00) · `intros l H'0 us H'1; elim H'0; auto`(-4.54) · `intros l; elim l; simpl in |- *; auto`(-4.63) · `-`(-4.64) · `intros l H'0 us H'1 H'2`(-4.85)

### step 3 — ❌miss
- **goal(입력 상태)**: `GBarlR us / forall l : list B,
(forall a : B, Bar B (GoodR B R) (a :: l)) ->
(forall (a : B) (us : list (A * B)), a :: l = sndL us -> MinD us -> GBarlR us) ->
forall us : list (A * B), l = sndL us -> `
- **retrieval 증명 top2**: `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b` ; `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `apply lem1; auto`
- **생성 top5**: `elim H'2; auto`(-2.78) · `elim H'2`(-3.53) · `elim H'2; simpl in |- *; auto`(-4.14) · `rewrite <- H'1`(-4.55) · `unfold MinD in H'2`(-4.59)

### step 4 — ✅top1
- **goal(입력 상태)**: `GoodR B R (sndL us) / forall l : list B,
(forall a : B, Bar B (GoodR B R) (a :: l)) ->
(forall (a : B) (us : list (A * B)), a :: l = sndL us -> MinD us -> GBarlR us) ->
forall us : list (A * B), l = s`
- **retrieval 증명 top2**: `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b` ; `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `rewrite <- H'1; auto`
- **생성 top5**: `rewrite <- H'1; auto`(-2.54) · `apply H'0; auto`(-3.04) · `rewrite H'1; auto`(-3.12) · `apply H'0`(-3.27) · `apply FoundG`(-3.29)

### step 5 — ❌miss
- **goal(입력 상태)**: `forall l : list B,
(forall a : B, Bar B (GoodR B R) (a :: l)) ->
(forall (a : B) (us : list (A * B)), a :: l = sndL us -> MinD us -> GBarlR us) ->
forall us : list (A * B), l = sndL us -> MinD us -> G`
- **retrieval 증명 top2**: `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b` ; `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * `
- **gold**: `intros l H'0 H'1 us H'2 H'3; red in |- *`
- **생성 top5**: `intros l H'0 H'1 us H'2 H'3`(-1.76) · `intros l H'0 us H'1 H'2`(-2.85) · `intros us H'0 H'1`(-3.60) · `intros l H'0 H'1 us H'2`(-4.27) · `intros l H'0 H'1; elim H'0; auto`(-4.38)

### step 6 — ❌miss
- **goal(입력 상태)**: `GRBar (A * B) (ProdRel A B leq R) us`
- **retrieval 증명 top2**: `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b` ; `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * `
- **gold**: `apply OpenInd with (lt := prod_lt); auto`
- **생성 top5**: `apply lem0; auto`(-2.06) · `apply lem0`(-2.93) · `apply lem1; auto`(-3.48) · `apply H'1; auto`(-3.73) · `rewrite <- H'1; auto`(-3.81)

### step 7 — ❌miss
- **goal(입력 상태)**: `well_founded prod_lt / forall a : A * B,
Min (A * B) prod_lt (ProdRel A B leq R) (a :: us) ->
GRBar (A * B) (ProdRel A B leq R) (a :: us)`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * `
- **gold**: `exact WFlem1`
- **생성 top5**: `apply wf_inverse_image with (B := B); auto`(-2.52) · `apply wf_inverse_image with (B := A); auto`(-2.99) · `exact wfgt`(-3.83) · `apply wf_inverse_image; auto`(-4.04) · `apply wf_inverse_image with (B := B)`(-4.32)

### step 8 — ❌miss
- **goal(입력 상태)**: `forall a : A * B,
Min (A * B) prod_lt (ProdRel A B leq R) (a :: us) ->
GRBar (A * B) (ProdRel A B leq R) (a :: us)`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * `
- **gold**: `intros a H'4`
- **생성 top5**: `intros us0 H'4`(-3.61) · `intros a H'4; elim H'4; auto`(-4.27) · `intros (a, b) H'4; red in |- *`(-4.30) · `intros a H'4; red in |- *`(-4.32) · `intros (a, b) H'4`(-4.33)

### step 9 — ❌miss
- **goal(입력 상태)**: `GRBar (A * B) (ProdRel A B leq R) (a :: us)`
- **retrieval 증명 top2**: `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b` ; `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `apply H'1 with (a := snd a); auto`
- **생성 top5**: `apply lem1; auto`(-3.03) · `apply lem0; auto`(-3.04) · `elim H'4; auto`(-3.59) · `elim H'4`(-3.81) · `red in |- *`(-3.82)

### step 10 — ❌miss
- **goal(입력 상태)**: `snd a :: l = sndL (a :: us)`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `rewrite H'2; auto`
- **생성 top5**: `simpl in |- *; auto`(-2.21) · `simpl in |- *`(-2.23) · `simpl in |- *; rewrite H'2; auto`(-3.09) · `rewrite <- H'2; auto`(-3.50) · `rewrite H'2`(-3.60)

## buchberger-theories-Dickson.v · proof#7 — `Definition cat_postwhisker {A} `{Is1Cat A} {a b c : A} {f g : a $-> b} (h : b $-> c) (p : f $== g) : h $o f $== h $o g := fmap (cat_postcomp a h) p.`  (5 steps)


### step 0 — 🔶topk
- **goal(입력 상태)**: `WR (A * B) (ProdRel A B leq R)`
- **retrieval 증명 top2**: `Definition cat_assoc_opp {A : Type} `{Is1Cat A} {a b c d : A} (f : a $-> b) (g : b $-> c) ` ; `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `Proof using wfgt wR declt`
- **생성 top5**: `Proof using wfgt declt`(-0.41) · `Proof using wfgt declt wR`(-2.42) · `Proof using wfgt`(-3.27) · `Proof using declt wfgt`(-3.53) · `Proof`(-3.54)

### step 1 — ❌miss
- **goal(입력 상태)**: `WR (A * B) (ProdRel A B leq R)`
- **retrieval 증명 top2**: `Definition cat_assoc_opp {A : Type} `{Is1Cat A} {a b c d : A} (f : a $-> b) (g : b $-> c) ` ; `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `red in |- *; apply keylem with (bs := nil (A:=B)); auto`
- **생성 top5**: `red in |- *`(-2.63) · `intros bs H'; elim H'; auto`(-2.97) · `intros l H'; elim H'; auto`(-3.87) · `red in |- *; red in |- *`(-4.27) · `intros bs H'; elim H'`(-4.38)

### step 2 — 🔶topk
- **goal(입력 상태)**: `MinD nil`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma bpow_log_neg: forall (base: radix) n, n < 0 -> (bpow base n <= b` ; `Lemma shiftl_spec_from_nat_pow `{SemiRing A} `{SemiRing B} `{!NatPowSp`
- **gold**: `red in |- *; auto`
- **생성 top5**: `constructor`(-3.45) · `apply MinD_nil`(-3.70) · `apply FoundG`(-3.96) · `red in |- *`(-4.29) · `red in |- *; apply keylem with (bs := nil (A:=B)); auto`(-4.40)

### step 3 — ❌miss
- **goal(입력 상태)**: `Min (A * B) (fun p q : A * B => lt (fst p) (fst q)) (ProdRel A B leq R) nil`
- **retrieval 증명 top2**: `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a` ; `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b`
- **retrieval premise top3**: `Lemma to_nat_inj {X: Type} {enumX: Enumerable X} {x y: X}: to_nat x = ` ; `Lemma round_integer_underflow: forall (base: radix) e m, e < 0 -> e * ` ; `Lemma round_integer_overflow: forall (base: radix) e m, 0 < e -> emax `
- **gold**: `apply nmin; auto`
- **생성 top5**: `red in |- *; auto`(-3.03) · `apply Min_nil`(-3.68) · `apply FoundG`(-3.94) · `simpl in |- *; auto`(-4.04) · `red in |- *; apply keylem with (bs := nil (A:=B)); auto`(-4.35)

## buchberger-theories-DivTerm.v · proof#0 — `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P x)) s) : nat := takeUntil P ex (λ _, S) O.`  (3 steps)


### step 0 — ❌miss
- **goal(입력 상태)**: `Term A n -> forall b : Term A n, ~ zeroP A0 eqA (n:=n) b -> Term A n`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinSubset_ball_orC : forall e x a l, FinSubset_ball e x (a :: l)` ; `Lemma FinSubset_ball_cons : forall x e a l, FinSubset_ball e x l -> Fi`
- **gold**: `intros H; case H; intros b2 c2 H'; case H'; intros b3 c3; simpl in |- *`
- **생성 top5**: `Proof`(-1.14) · `Proof`(-1.32) · `Proof`(-3.67) · `intros`(-3.78) · `intros P ex`(-4.25)

### step 1 — ❌miss
- **goal(입력 상태)**: `~ eqA b3 A0 -> Term A n`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinSubset_ball_orC : forall e x a l, FinSubset_ball e x (a :: l)` ; `Lemma FinSubset_ball_cons : forall x e a l, FinSubset_ball e x l -> Fi`
- **gold**: `intros nZb3; exact (divA b2 b3 nZb3, div_mon n c2 c3)`
- **생성 top5**: `unfold not in |- *`(-4.22) · `intros H0`(-4.28) · `red in |- *`(-4.72) · `intro H0; exact H`(-5.34) · `red in |- *; intros`(-5.71)

## buchberger-theories-DivTerm.v · proof#1 — `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (P x)) s) : Is_true (P (Str_nth_tl (takeUntil_length P e`  (21 steps)


### step 0 — ❌miss
- **goal(입력 상태)**: `forall (a b c : Term A n) (nZc : ~ zeroP A0 eqA (n:=n) c),
eqT (A:=A) (n:=n) a b ->
eqTerm eqA (n:=n) a (multTerm multA (n:=n) (divTerm a (b:=c) nZc) c) ->
eqTerm eqA (n:=n) b (multTerm multA (n:=n) (`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinSubset_ball_orC : forall e x a l, FinSubset_ball e x (a :: l)` ; `Lemma FinSubset_ball_cons : forall x e a l, FinSubset_ball e x l -> Fi`
- **gold**: `Proof using minusA invA cs A1`
- **생성 top5**: `Proof`(-1.08) · `Proof`(-2.29) · `intros`(-3.68) · `simpl in |- *`(-4.59) · `intros H; case H; intros b2 c2 H'; case H'; intros b3 c3; simpl in |- *`(-4.76)

### step 1 — ❌miss
- **goal(입력 상태)**: `forall (a b c : Term A n) (nZc : ~ zeroP A0 eqA (n:=n) c),
eqT (A:=A) (n:=n) a b ->
eqTerm eqA (n:=n) a (multTerm multA (n:=n) (divTerm a (b:=c) nZc) c) ->
eqTerm eqA (n:=n) b (multTerm multA (n:=n) (`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinSubset_ball_orC : forall e x a l, FinSubset_ball e x (a :: l)` ; `Lemma FinSubset_ball_cons : forall x e a l, FinSubset_ball e x l -> Fi`
- **gold**: `intros a b c; case a; case b; case c; simpl in |- *; auto`
- **생성 top5**: `intros`(-3.39) · `intros; simpl in |- *`(-5.66) · `intros H; case H`(-6.02) · `intros H; case H; intros b2 c2 H'; case H'; intros b3 c3; simpl in |- *`(-6.52) · `intros H; case H`(-6.75)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a0 : A) (m : mon n) (a1 : A) (m0 : mon n) 
  (a2 : A) (m1 : mon n) (nZc : ~ eqA a0 A0),
eqT (A:=A) (n:=n) (a2, m1) (a1, m0) ->
eqA a2 (multA (divA a2 a0 nZc) a0) /\ m1 = mult_mon n (div_mon n `
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `intros a0 m a1 m0 a2 m1 nZc H' H'0 H'1; split; auto`
- **생성 top5**: `-`(-4.19) · `intros a0 m0 a1 m1 a2 m2 nZc H H0`(-8.18) · `intros a0 m0 a1 m1 a2 m2 nZc H'; case H'`(-8.36) · `intros a0 m0 a1 m1 a2 m2 nZc; case a2; case a1; simpl in |- *; auto`(-9.87) · `intros a0 m0 a1 m1 a2 m2 nZc; case a2; case a1; simpl in |- *`(-11.01)

### step 3 — ❌miss
- **goal(입력 상태)**: `eqA (divA (plusA a2 a1) a0 nZc) (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `case H'1; intros H'3 H'4; clear H'1`
- **생성 top5**: `simpl in |- *`(-4.87) · `unfold eqA in |- *`(-5.12) · `unfold eqA in |- *; simpl in |- *`(-5.86) · `destruct H'0, H'1`(-5.94) · `destruct H'0; destruct H'1`(-6.05)

### step 4 — 🔶topk
- **goal(입력 상태)**: `eqA (divA (plusA a2 a1) a0 nZc) (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `case H'0; intros H'2 H'5; clear H'0`
- **생성 top5**: `rewrite H'3`(-3.05) · `case H'0; intros H'5 H'6; clear H'0`(-3.55) · `rewrite <- H'3`(-4.51) · `simpl in |- *`(-4.65) · `rewrite H'3; rewrite H'4`(-5.14)

### step 5 — ❌miss
- **goal(입력 상태)**: `eqA (divA (plusA a2 a1) a0 nZc) (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA (plusA (multA (divA a2 a0 nZc) a0) (multA (divA a1 a0 nZc) a0)) a0 nZc); auto`
- **생성 top5**: `case H'3; intros H'6 H'7; clear H'3`(-3.93) · `case H'; intros H'6 H'7; clear H'`(-4.08) · `rewrite H'2; rewrite H'3`(-4.57) · `rewrite H'2; rewrite H'3; auto`(-4.85) · `rewrite H'3; rewrite H'2; auto`(-5.63)

### step 6 — ❌miss
- **goal(입력 상태)**: `eqA
  (divA (plusA (multA (divA a2 a0 nZc) a0) (multA (divA a1 a0 nZc) a0)) a0
     nZc) (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) a0) a0 nZc); auto`
- **생성 top5**: `simpl in |- *`(-4.11) · `apply divA_correct; auto`(-4.39) · `rewrite <- H'2`(-5.41) · `apply eqA_trans with (y := divA a2 a0 nZc); auto`(-6.09) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs)`(-6.11)

### step 7 — ❌miss
- **goal(입력 상태)**: `eqA
  (divA (plusA (multA (divA a2 a0 nZc) a0) (multA (divA a1 a0 nZc) a0)) a0
     nZc) (divA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) a0) a0 nZc) / eqA (divA (multA (plusA (divA a2 a0 nZc) (`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply divA_eqA_comp with (1 := cs); auto`
- **생성 top5**: `apply eqA_refl`(-4.13) · `apply cs; auto`(-4.37) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA (multA (divA a2 a0 nZc) a0) a0 nZc); auto`(-4.62) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA (multA (divA a2 a0 nZc) a0) a0 nZc); auto`(-4.75) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs)`(-5.51)

### step 8 — ❌miss
- **goal(입력 상태)**: `eqA (plusA (multA (divA a2 a0 nZc) a0) (multA (divA a1 a0 nZc) a0))
  (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) a0) / eqA (divA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) a0) a0 nZc)
  (p`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := plusA (multA a0 (divA a2 a0 nZc)) (multA a0 (divA a1 a0 nZc))); auto`
- **생성 top5**: `apply multA_eqA_comp with (1 := cs); auto`(-3.98) · `apply plusA_eqA_comp with (1 := cs); auto`(-4.06) · `apply eqA_trans with (1 := H'3); auto`(-4.49) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs); auto`(-4.94) · `apply eqA_trans with (2 := H'3); auto`(-4.98)

### step 9 — ❌miss
- **goal(입력 상태)**: `eqA (plusA (multA a0 (divA a2 a0 nZc)) (multA a0 (divA a1 a0 nZc)))
  (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) a0) / eqA (divA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) a0) a0 nZc)
  (p`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := multA a0 (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))); auto`
- **생성 top5**: `apply plusA_eqA_comp with (1 := cs); auto`(-3.08) · `apply eqA_plusA; auto`(-3.86) · `apply multA_eqA_comp with (1 := cs); auto`(-4.43) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := plusA (divA a2 a0 nZc) (multA a0 (divA a1 a0 nZc))); auto`(-4.50) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := plusA (divA a2 a0 nZc) (divA a1 a0 nZc)); auto`(-4.50)

### step 10 — ❌miss
- **goal(입력 상태)**: `eqA (divA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) a0) a0 nZc)
  (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) (divA a0 a0 nZc)); auto`
- **생성 top5**: `apply divA_eqA_comp with (1 := cs); auto`(-1.23) · `apply divA_eqA_comp with (2 := cs); auto`(-3.78) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := plusA (divA a2 a0 nZc) (divA a1 a0 nZc)); auto`(-4.19) · `apply divA_eqA; auto`(-4.53) · `apply divA_eqA_comp; auto`(-4.65)

### step 11 — ❌miss
- **goal(입력 상태)**: `eqA (divA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) a0) a0 nZc)
  (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) (divA a0 a0 nZc)) / eqA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) (divA`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA (multA a0 (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))) a0 nZc); auto`
- **생성 top5**: `apply divA_eqA_comp with (1 := cs); auto`(-1.36) · `apply multA_eqA_comp with (1 := cs); auto`(-3.57) · `apply eqA_refl`(-3.85) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) a0) a0 nZc); auto`(-4.00) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) a0 nZc); auto`(-4.21)

### step 12 — ❌miss
- **goal(입력 상태)**: `eqA (divA (multA a0 (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))) a0 nZc)
  (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) (divA a0 a0 nZc)) / eqA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) (divA`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := multA (divA a0 a0 nZc) (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))); auto`
- **생성 top5**: `apply divA_eqA_comp with (1 := cs); auto`(-1.17) · `apply multA_eqA_comp with (1 := cs); auto`(-3.97) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA (multA a0 (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))) a0 nZc); auto`(-4.14) · `apply divA_eqA_comp with (2 := cs); auto`(-4.27) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA (plusA (multA a0 (divA a2 a0 nZc)) (divA a1 a0 nZc)) a0 nZc); auto`(-4.33)

### step 13 — ❌miss
- **goal(입력 상태)**: `eqA (divA (multA a0 (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))) a0 nZc)
  (multA (divA a0 a0 nZc) (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))) / eqA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) (divA`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply divA_multA_comp_r with (1 := cs); auto`
- **생성 top5**: `apply divA_eqA_comp with (1 := cs); auto`(-1.04) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA (multA a0 (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))) a0 nZc); auto`(-3.32) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA (multA (divA a0 a0 nZc) (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))) a0 nZc); auto`(-3.86) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA (multA a0 (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))) a0 nZc); auto`(-4.07) · `apply multA_eqA_comp with (1 := cs); auto`(-4.77)

### step 14 — ❌miss
- **goal(입력 상태)**: `eqA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) (divA a0 a0 nZc))
  (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) A1); auto`
- **생성 top5**: `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := plusA (divA a2 a0 nZc) (divA a1 a0 nZc)); auto`(-2.73) · `apply eqA_plusA; auto`(-3.35) · `apply eqA_refl`(-3.78) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) (divA a0 a0 nZc)); auto`(-3.98) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := plusA (divA a2 a0 nZc) (divA a1 a0 nZc)); auto`(-4.34)

### step 15 — ❌miss
- **goal(입력 상태)**: `eqA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) (divA a0 a0 nZc))
  (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) A1) / eqA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) A1)
  (plusA (divA `
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); auto`
- **생성 top5**: `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := plusA (divA a2 a0 nZc) (divA a1 a0 nZc)); auto`(-3.39) · `apply divA_multA_comp_r with (1 := cs); auto`(-4.08) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := multA (divA a2 a0 nZc) (plusA (divA a1 a0 nZc) A1)); auto`(-4.15) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) (divA a0 a0 nZc)); auto`(-4.28) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) (divA a0 a0 nZc)); auto`(-4.49)

### step 16 — 🔶topk
- **goal(입력 상태)**: `eqA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) A1)
  (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) (divA a0 a0 nZc)) / eqA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) A1)
  (plusA (divA `
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply multA_eqA_comp with (1 := cs); auto`
- **생성 top5**: `apply divA_eqA_comp with (1 := cs); auto`(-3.65) · `apply multA_plusA_eqA; auto`(-3.96) · `apply divA_multA_comp_r with (1 := cs); auto`(-4.15) · `apply multA_eqA_comp with (1 := cs); auto`(-4.44) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := plusA (divA a2 a0 nZc) (divA a1 a0 nZc)); auto`(-4.51)

### step 17 — 🔶topk
- **goal(입력 상태)**: `eqA A1 (divA a0 a0 nZc) / eqA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) A1)
  (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); auto`
- **생성 top5**: `apply divA_eqA_comp with (1 := cs); auto`(-0.66) · `apply divA_eqA; auto`(-3.04) · `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); auto`(-3.11) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA a0 a0 nZc); auto`(-3.91) · `apply divA_eqA with (1 := cs); auto`(-4.31)

### step 18 — ❌miss
- **goal(입력 상태)**: `eqA (divA a0 a0 nZc) A1 / eqA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) A1)
  (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply divA_A1 with (1 := cs); auto`
- **생성 top5**: `apply divA_eqA_comp with (1 := cs); auto`(-0.59) · `apply divA_eqA; auto`(-3.39) · `apply divA_eqA_r with (1 := cs); auto`(-3.40) · `apply divA_eqA with (1 := cs); auto`(-4.04) · `apply divA_eqA_compat with (1 := cs); auto`(-4.52)

### step 19 — ❌miss
- **goal(입력 상태)**: `eqA (multA (plusA (divA a2 a0 nZc) (divA a1 a0 nZc)) A1)
  (plusA (divA a2 a0 nZc) (divA a1 a0 nZc))`
- **retrieval 증명 top1**: `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply multA_A1_r with (1 := cs); auto`
- **생성 top5**: `apply multA_eqA_comp with (1 := cs); auto`(-3.07) · `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); auto`(-3.38) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := plusA (divA a1 a0 nZc) (divA a2 a0 nZc)); auto`(-3.94) · `apply eqA_sym; auto`(-4.05) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := plusA (divA a2 a0 nZc) (divA a1 a0 nZc)); auto`(-4.19)

## buchberger-theories-DivTerm.v · proof#2 — `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (P x)) s) (cons: A → B → B) (nil : B) : takeUntil P ex cons n`  (15 steps)


### step 0 — ❌miss
- **goal(입력 상태)**: `forall (a b : Term A n) (nZa : ~ zeroP A0 eqA (n:=n) a),
eqTerm eqA (n:=n) b (multTerm multA (n:=n) (divTerm b (b:=a) nZa) a) ->
eqTerm eqA (n:=n) (divTerm (invTerm invA (n:=n) b) (b:=a) nZa)
  (invTe`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinSubset_ball_orC : forall e x a l, FinSubset_ball e x (a :: l)` ; `Lemma FinSubset_ball_cons : forall x e a l, FinSubset_ball e x l -> Fi`
- **gold**: `Proof using plusA minusA cs A1`
- **생성 top5**: `Proof using minusA invA cs A1`(-1.59) · `Proof`(-1.72) · `Proof using minusA invA cs`(-3.42) · `Proof using cs`(-3.87) · `Proof using minusA invA`(-4.23)

### step 1 — ❌miss
- **goal(입력 상태)**: `forall (a b : Term A n) (nZa : ~ zeroP A0 eqA (n:=n) a),
eqTerm eqA (n:=n) b (multTerm multA (n:=n) (divTerm b (b:=a) nZa) a) ->
eqTerm eqA (n:=n) (divTerm (invTerm invA (n:=n) b) (b:=a) nZa)
  (invTe`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinSubset_ball_orC : forall e x a l, FinSubset_ball e x (a :: l)` ; `Lemma FinSubset_ball_cons : forall x e a l, FinSubset_ball e x l -> Fi`
- **gold**: `intros a b; case a; case b; simpl in |- *; auto`
- **생성 top5**: `intros a b c; case a; case b; case c; simpl in |- *; auto`(-2.57) · `intros a b c`(-3.82) · `intros b c; case b; case c; simpl in |- *; auto`(-4.45) · `simpl in |- *`(-4.71) · `intros a b c; case a; case b; case c; simpl in |- *`(-5.25)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a0 : A) (m : mon n) (a1 : A) (m0 : mon n) (nZa : ~ eqA a1 A0),
eqA a0 (multA (divA a0 a1 nZa) a1) /\ m = mult_mon n (div_mon n m m0) m0 ->
eqA (divA (invA a0) a1 nZa) (invA (divA a0 a1 nZa)) /`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `intros d c A0' c0 nZA2 H'0; split; auto`
- **생성 top5**: `intros a0 m a1 m0 nZa H'; split; auto`(-3.47) · `intros a0 m a1 m0 nZa H; split; auto`(-5.11) · `intros a0 m a1 m0 a2 m1 nZc H' H'0 H'1; split; auto`(-5.24) · `intros a0 m b0 m0 nZb H'; split; auto`(-5.26) · `intros a0 m a1 m0 a2 m1 nZa H'; split; auto`(-5.29)

### step 3 — 🔶topk
- **goal(입력 상태)**: `eqA (divA (invA d) A0' nZA2) (invA (divA d A0' nZA2))`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `case H'0; intros H'1 H'2; clear H'0`
- **생성 top5**: `case H'0; intros H'3 H'4; clear H'0`(-2.33) · `case H'0; intros H'1 H'2; clear H'0`(-2.35) · `case H'0; intros H'2 H'3; clear H'0`(-4.45) · `case H'0; intros _ H'1; clear H'0`(-4.74) · `elim H'0; intros H'1 H'2; clear H'0`(-4.77)

### step 4 — ❌miss
- **goal(입력 상태)**: `eqA (divA (invA d) A0' nZA2) (invA (divA d A0' nZA2))`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA (invA (multA (divA d A0' nZA2) A0')) A0' nZA2); auto`
- **생성 top5**: `case nZA2; auto`(-3.89) · `apply divA_eqA_comp with (1 := cs); auto`(-4.08) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA (invA d) A0' nZA2); auto`(-4.49) · `apply divA_eqA_comp with (1 := H'1); auto`(-5.08) · `apply eqA_trans with (y := divA (invA d) A0' nZA2); auto`(-5.50)

### step 5 — ❌miss
- **goal(입력 상태)**: `eqA (divA (invA (multA (divA d A0' nZA2) A0')) A0' nZA2)
  (invA (divA d A0' nZA2))`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA (multA (invA (divA d A0' nZA2)) A0') A0' nZA2); auto`
- **생성 top5**: `apply divA_eqA_comp with (1 := cs); auto`(-3.29) · `apply divA_invA`(-3.49) · `apply invA_eqA_comp with (1 := cs); auto`(-3.52) · `apply divA_invA; auto`(-3.54) · `apply divA_invA_comp; auto`(-3.61)

### step 6 — ✅top1
- **goal(입력 상태)**: `eqA (divA (invA (multA (divA d A0' nZA2) A0')) A0' nZA2)
  (divA (multA (invA (divA d A0' nZA2)) A0') A0' nZA2) / eqA (divA (multA (invA (divA d A0' nZA2)) A0') A0' nZA2)
  (invA (divA d A0' nZA2))`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply divA_eqA_comp with (1 := cs); auto`
- **생성 top5**: `apply divA_eqA_comp with (1 := cs); auto`(-1.23) · `apply divA_invA_comp; auto`(-3.86) · `apply divA_multA_comp_r with (1 := cs); auto`(-3.89) · `apply divA_invA_comp with (1 := cs); auto`(-3.98) · `apply divA_eqA_comp with (1 := cs)`(-4.22)

### step 7 — ❌miss
- **goal(입력 상태)**: `eqA (invA (multA (divA d A0' nZA2) A0')) (multA (invA (divA d A0' nZA2)) A0') / eqA (divA (multA (invA (divA d A0' nZA2)) A0') A0' nZA2)
  (invA (divA d A0' nZA2))`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); apply multA_invA_com_l with (1 := cs); auto`
- **생성 top5**: `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := multA (invA (divA d A0' nZA2)) A0'); auto`(-2.13) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := invA (multA (divA d A0' nZA2) A0')); auto`(-2.26) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := multA (invA (divA d A0' nZA2)) A0'); auto`(-2.63) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := invA (multA (divA d A0' nZA2) A0')); auto`(-2.77) · `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); auto`(-3.38)

### step 8 — ❌miss
- **goal(입력 상태)**: `eqA (divA (multA (invA (divA d A0' nZA2)) A0') A0' nZA2)
  (invA (divA d A0' nZA2))`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := multA (invA (divA d A0' nZA2)) (divA A0' A0' nZA2)); auto`
- **생성 top5**: `apply divA_invA_com_l with (1 := cs); auto`(-2.88) · `apply divA_invA_com_r with (1 := cs); auto`(-2.92) · `apply divA_eqA_comp with (1 := cs); auto`(-2.99) · `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); apply multA_invA_com_r with (1 := cs); auto`(-3.06) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := multA (invA (divA d A0' nZA2)) A0'); auto`(-3.83)

### step 9 — ❌miss
- **goal(입력 상태)**: `eqA (divA (multA (invA (divA d A0' nZA2)) A0') A0' nZA2)
  (multA (invA (divA d A0' nZA2)) (divA A0' A0' nZA2)) / eqA (multA (invA (divA d A0' nZA2)) (divA A0' A0' nZA2))
  (invA (divA d A0' nZA2))`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply divA_multA_comp_l with (1 := cs)`
- **생성 top5**: `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := divA (multA (invA (divA d A0' nZA2)) A0') A0' nZA2); auto`(-1.92) · `apply divA_eqA_comp with (1 := cs); auto`(-3.54) · `apply divA_multA_invA_com_l with (1 := cs); auto`(-3.69) · `apply divA_multA_com_r with (1 := cs); auto`(-3.72) · `apply divA_multA_invA_com_r with (1 := cs); auto`(-4.19)

### step 10 — ❌miss
- **goal(입력 상태)**: `eqA (multA (invA (divA d A0' nZA2)) (divA A0' A0' nZA2))
  (invA (divA d A0' nZA2))`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := multA (invA (divA d A0' nZA2)) A1); auto`
- **생성 top5**: `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs)`(-2.23) · `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); apply multA_invA_com_r with (1 := cs); auto`(-2.23) · `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); apply multA_invA_com_l with (1 := cs); auto`(-2.34) · `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); auto`(-2.88) · `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); apply multA_invA_com_l with (1 := cs)`(-3.18)

### step 11 — 🔶topk
- **goal(입력 상태)**: `eqA (multA (invA (divA d A0' nZA2)) (divA A0' A0' nZA2))
  (multA (invA (divA d A0' nZA2)) A1) / eqA (multA (invA (divA d A0' nZA2)) A1) (invA (divA d A0' nZA2))`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply multA_eqA_comp with (1 := cs); auto`
- **생성 top5**: `apply multA_invA_com_l with (1 := cs); auto`(-2.16) · `apply multA_invA_com_r with (1 := cs); auto`(-2.19) · `apply multA_invA_com_l with (1 := cs)`(-2.64) · `apply multA_invA_com_r with (1 := cs)`(-2.68) · `apply multA_eqA_comp with (1 := cs)`(-3.18)

### step 12 — ❌miss
- **goal(입력 상태)**: `eqA (divA A0' A0' nZA2) A1 / eqA (multA (invA (divA d A0' nZA2)) A1) (invA (divA d A0' nZA2))`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply divA_A1 with (1 := cs)`
- **생성 top5**: `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); auto`(-1.56) · `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); apply divA_A1 with (1 := cs); auto`(-1.59) · `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); apply divA_A1 with (1 := cs); auto`(-3.11) · `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); apply divA_A1 with (1 := cs); auto`(-3.16) · `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); apply multA_invA_com_r with (1 := cs); auto`(-3.52)

### step 13 — ❌miss
- **goal(입력 상태)**: `eqA (multA (invA (divA d A0' nZA2)) A1) (invA (divA d A0' nZA2))`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `apply multA_A1_r with (1 := cs)`
- **생성 top5**: `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); apply multA_invA_com_l with (1 := cs); auto`(-2.41) · `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); apply multA_invA_com_r with (1 := cs); auto`(-2.43) · `apply (eqA_sym _ _ _ _ _ _ _ _ _ cs); auto`(-2.58) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := invA (multA (divA d A0' nZA2) A0')); auto`(-3.19) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs) with (y := multA (invA (divA d A0' nZA2)) (invA A1)); auto`(-3.64)

## buchberger-theories-DivTerm.v · proof#3 — `Lemma takeUntil_length_tl {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (P x)) s) (Ptl : EventuallyForAll (fun x => Is_true (P x)) s)`  (5 steps)


### step 0 — 🔶topk
- **goal(입력 상태)**: `forall (a b : Term A n) (nZa : ~ zeroP A0 eqA (n:=n) a)
  (nZia : ~ zeroP A0 eqA (n:=n) (invTerm invA (n:=n) a)),
eqTerm eqA (n:=n) b (multTerm multA (n:=n) (divTerm b (b:=a) nZa) a) ->
eqTerm eqA (n:`
- **retrieval 증명 top2**: `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (` ; `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinSubset_ball_orC : forall e x a l, FinSubset_ball e x (a :: l)` ; `Lemma FinSubset_ball_cons : forall x e a l, FinSubset_ball e x l -> Fi`
- **gold**: `Proof using plusA minusA cs A1`
- **생성 top5**: `Proof`(-1.33) · `Proof using plusA minusA cs A1`(-1.81) · `Proof using os`(-3.03) · `Proof using plusA minusA cs`(-3.23) · `Proof using n`(-3.71)

### step 1 — ✅top1
- **goal(입력 상태)**: `forall (a b : Term A n) (nZa : ~ zeroP A0 eqA (n:=n) a)
  (nZia : ~ zeroP A0 eqA (n:=n) (invTerm invA (n:=n) a)),
eqTerm eqA (n:=n) b (multTerm multA (n:=n) (divTerm b (b:=a) nZa) a) ->
eqTerm eqA (n:`
- **retrieval 증명 top2**: `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (` ; `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinSubset_ball_orC : forall e x a l, FinSubset_ball e x (a :: l)` ; `Lemma FinSubset_ball_cons : forall x e a l, FinSubset_ball e x l -> Fi`
- **gold**: `intros a b; case a; case b; simpl in |- *; auto`
- **생성 top5**: `intros a b; case a; case b; simpl in |- *; auto`(-2.65) · `intros`(-3.28) · `intros a b`(-3.40) · `simpl in |- *`(-4.59) · `intros; simpl in |- *`(-4.79)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a0 : A) (m : mon n) (a1 : A) (m0 : mon n) 
  (nZa : ~ eqA a1 A0) (nZia : ~ eqA (invA a1) A0),
eqA a0 (multA (divA a0 a1 nZa) a1) /\ m = mult_mon n (div_mon n m m0) m0 ->
eqA (divA a0 (invA a1)`
- **retrieval 증명 top2**: `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (` ; `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `split; auto`
- **생성 top5**: `intros d c A0' c0 nZA2 H'0; split; auto`(-1.40) · `intros d c A0' c0 nZA2 H'0`(-2.70) · `intros d c A0' c0 nZA2 H; split; auto`(-4.08) · `intros d c A0' c0 nZA2 H'; split; auto`(-4.18) · `intros d c A0' c0 nZA2 H'0; split`(-4.36)

### step 3 — ❌miss
- **goal(입력 상태)**: `eqA (divA a0 (invA a1) nZia) (invA (divA a0 a1 nZa))`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `apply divA_invA_r with (1 := cs); auto`
- **생성 top5**: `case H; intros H' H'0; clear H`(-3.18) · `case H; intros H0 H1; clear H`(-3.29) · `destruct H`(-3.40) · `case H; intros H1 H2; clear H`(-4.07) · `elim H; intros H' H'0; clear H`(-4.18)

## buchberger-theories-DivTerm.v · proof#4 — `Lemma takeUntil_length_Str_nth_tl {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (P x)) s) (Ptl : EventuallyForAll (fun x => Is_true (`  (4 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (a b c d : Term A n) (nZc : ~ zeroP A0 eqA (n:=n) c)
  (nZd : ~ zeroP A0 eqA (n:=n) d),
eqT (A:=A) (n:=n) a b ->
eqT (A:=A) (n:=n) c d ->
eqT (A:=A) (n:=n) (divTerm a (b:=c) nZc) (divTerm b (b:`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Lemma takeUntil_length_tl {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinSubset_ball_wd : forall x y d e l, d == e -> msp_eq x y -> (F` ; `Lemma FinSubset_ball_orC : forall e x a l, FinSubset_ball e x (a :: l)`
- **gold**: `intros a b c d; case a; case b; case c; case d; unfold eqT in |- *; simpl in |- *; auto`
- **생성 top5**: `intros a b c d`(-2.65) · `intros a b c d; case a; case b; case c; case d; simpl in |- *; auto`(-3.00) · `intros`(-3.45) · `intros a b; case a; case b; case c; case d; simpl in |- *; auto`(-3.62) · `intros`(-4.20)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a0 : A) (m : mon n) (a1 : A) (m0 : mon n),
A ->
forall m1 : mon n,
A ->
forall m2 : mon n,
~ eqA a1 A0 ->
~ eqA a0 A0 -> m2 = m1 -> m0 = m -> div_mon n m2 m0 = div_mon n m1 m`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `intros A0' c0 d2 c2 H' c3 H'0 c4 H'1 H'2 H'3 H'4; rewrite H'3; rewrite H'4; auto`
- **생성 top5**: `intros a0 m a1 m0 a2 m1 nZc H' H'0 H'1; split; auto`(-3.88) · `intros`(-4.25) · `intros a0 m a1 m0 a2 m1 nZc H' H'0 H'1; subst`(-4.92) · `intros a0 m a1 m0 a2 m1 nZc H' H'0 H'1; simpl in |- *`(-5.22) · `intros a0 m a1 m0 a2 m1 nZc H' H'0 H'1; case H'1; intros H'3 H'4; clear H'1`(-5.45)

## buchberger-theories-DivTerm.v · proof#5 — `Lemma takeUntil_length_ForAllIf {A1 A2} (P1 : Stream A1 → bool) `(ex1 : LazyExists (fun x => Is_true (P1 x)) s1) {P2 : Stream A2 → bool} `(ex2 : LazyE`  (8 steps)


### step 0 — ❌miss
- **goal(입력 상태)**: `forall (a b c d : Term A n) (nZc : ~ zeroP A0 eqA (n:=n) c)
  (nZd : ~ zeroP A0 eqA (n:=n) d),
eqTerm eqA (n:=n) a b ->
eqTerm eqA (n:=n) c d ->
eqTerm eqA (n:=n) (divTerm a (b:=c) nZc) (divTerm b (b:`
- **retrieval 증명 top2**: `Lemma takeUntil_length_Str_nth_tl {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => I` ; `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinSubset_ball_wd : forall x y d e l, d == e -> msp_eq x y -> (F` ; `Lemma FinSubset_ball_orC : forall e x a l, FinSubset_ball e x (a :: l)`
- **gold**: `Proof using plusA multA minusA invA cs A1`
- **생성 top5**: `Proof`(-0.02) · `Proof`(-5.60) · `Proof with auto`(-6.50) · `Proof with eauto`(-6.98) · `intros`(-7.02)

### step 1 — ❌miss
- **goal(입력 상태)**: `forall (a b c d : Term A n) (nZc : ~ zeroP A0 eqA (n:=n) c)
  (nZd : ~ zeroP A0 eqA (n:=n) d),
eqTerm eqA (n:=n) a b ->
eqTerm eqA (n:=n) c d ->
eqTerm eqA (n:=n) (divTerm a (b:=c) nZc) (divTerm b (b:`
- **retrieval 증명 top2**: `Lemma takeUntil_length_Str_nth_tl {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => I` ; `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinSubset_ball_wd : forall x y d e l, d == e -> msp_eq x y -> (F` ; `Lemma FinSubset_ball_orC : forall e x a l, FinSubset_ball e x (a :: l)`
- **gold**: `intros a b c d; case a; case b; case c; case d; simpl in |- *; auto`
- **생성 top5**: `intros a b c d`(-3.07) · `intros`(-3.13) · `intros a b c d; case a; case b; case c; case d; unfold eqT in |- *; simpl in |- *; auto`(-3.83) · `intros`(-3.94) · `unfold eqTerm in |- *`(-4.81)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a0 : A) (m : mon n) (a1 : A) (m0 : mon n) 
  (a2 : A) (m1 : mon n) (a3 : A) (m2 : mon n) (nZc : ~ eqA a1 A0)
  (nZd : ~ eqA a0 A0),
eqA a3 a2 /\ m2 = m1 ->
eqA a1 a0 /\ m0 = m ->
eqA (divA a3 `
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Lemma takeUntil_length_Str_nth_tl {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => I`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `intros A0' c0 d2 c2 d3 c3 d4 c4 nZd2 H'0 H'1 H'2`
- **생성 top5**: `intros a0 m a1 m0 a2 m1 m2 nZc nZd H' H'0; split; auto`(-3.26) · `intros a0 m a1 m0 a2 m1 a3 m2 nZc nZd H' H'0; split; auto`(-3.32) · `intros a0 m a1 m0 a2 m1 m2 nZc nZd H' H'0`(-3.71) · `intros a0 m a1 m0 a2 m1 a3 m2 nZc nZd H' H'0`(-3.86) · `intros a0 m a1 m0 a2 m1 nZc nZd H' H'0; split; auto`(-3.89)

### step 3 — ❌miss
- **goal(입력 상태)**: `eqA (divA d4 d2 nZd2) (divA d3 A0' H'0) /\ div_mon n c4 c2 = div_mon n c3 c0`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `case H'2; intros H'3 H'4; clear H'2`
- **생성 top5**: `split`(-2.13) · `split; auto`(-2.58) · `case H'1; intros H'3 H'4; clear H'1`(-2.87) · `elim H'1; intros H'3 H'4; clear H'1`(-3.99) · `elim H'1; clear H'1; intros H'3 H'4`(-4.45)

### step 4 — 🔶topk
- **goal(입력 상태)**: `eqA (divA d4 d2 nZd2) (divA d3 A0' H'0) /\ div_mon n c4 c2 = div_mon n c3 c0`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `case H'1; intros H'2 H'5; clear H'1`
- **생성 top5**: `case H'1; intros H'5 H'6; clear H'1`(-0.61) · `split`(-2.84) · `split; auto`(-3.59) · `case H'1; intros H'2 H'5; clear H'1`(-3.64) · `case H'3; intros H'5 H'6; clear H'3`(-4.68)

### step 5 — ✅top1
- **goal(입력 상태)**: `eqA (divA d4 d2 nZd2) (divA d3 A0' H'0) /\ div_mon n c4 c2 = div_mon n c3 c0`
- **retrieval 증명 top2**: `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (` ; `Lemma takeUntil_length_tl {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `split; auto`
- **생성 top5**: `split; auto`(-1.25) · `split`(-1.91) · `case H'3; intros H'6 H'7; clear H'3`(-2.66) · `case H'0; intros H'6 H'7; clear H'0`(-3.71) · `case H'0; intros H'1 H'6; clear H'0`(-3.72)

### step 6 — ❌miss
- **goal(입력 상태)**: `div_mon n c4 c2 = div_mon n c3 c0`
- **retrieval 증명 top2**: `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (` ; `Lemma takeUntil_length_tl {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (`
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `rewrite H'5; rewrite H'4; auto`
- **생성 top5**: `case H'3; intros H'6 H'7; clear H'3`(-3.44) · `apply divA_eqA_comp with (1 := cs); auto`(-4.88) · `rewrite H'4; rewrite H'5`(-5.19) · `rewrite H'4; rewrite H'5; auto`(-5.25) · `apply eqA_sym in H'3`(-5.39)

## buchberger-theories-DivTerm.v · proof#6 — `Definition NearBy (l : X) (ε : QposInf) := ForAll (λ s, ball_ex ε (hd s) l).`  (10 steps)


### step 0 — ❌miss
- **goal(입력 상태)**: `forall (a b c : Term A n) (nZa : ~ zeroP A0 eqA (n:=n) a),
eqTerm eqA (n:=n) b (multTerm multA (n:=n) (divTerm b (b:=a) nZa) a) ->
eqTerm eqA (n:=n) (divTerm (multTerm multA (n:=n) c b) (b:=a) nZa)
  `
- **retrieval 증명 top2**: `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (` ; `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinSubset_ball_orC : forall e x a l, FinSubset_ball e x (a :: l)` ; `Lemma FinSubset_ball_cons : forall x e a l, FinSubset_ball e x l -> Fi`
- **gold**: `Proof using plusA minusA invA cs A1`
- **생성 top5**: `Proof`(-0.74) · `Proof`(-2.45) · `intros`(-4.17) · `intros`(-4.18) · `Proof using os`(-4.95)

### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (a b c : Term A n) (nZa : ~ zeroP A0 eqA (n:=n) a),
eqTerm eqA (n:=n) b (multTerm multA (n:=n) (divTerm b (b:=a) nZa) a) ->
eqTerm eqA (n:=n) (divTerm (multTerm multA (n:=n) c b) (b:=a) nZa)
  `
- **retrieval 증명 top2**: `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (` ; `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinSubset_ball_orC : forall e x a l, FinSubset_ball e x (a :: l)` ; `Lemma FinSubset_ball_cons : forall x e a l, FinSubset_ball e x l -> Fi`
- **gold**: `intros a b c; case a; case b; case c; simpl in |- *; auto`
- **생성 top5**: `intros`(-3.40) · `intros l ε`(-3.47) · `intros a b c`(-4.17) · `intros a b c nZa H`(-6.01) · `intros a b c nZa H'`(-6.01)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a0 : A) (m : mon n) (a1 : A) (m0 : mon n) 
  (a2 : A) (m1 : mon n) (nZa : ~ eqA a2 A0),
eqA a1 (multA (divA a1 a2 nZa) a2) /\ m0 = mult_mon n (div_mon n m0 m1) m1 ->
eqA (divA (multA a0 a1) a2`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Lemma takeUntil_length_ForAllIf {A1 A2} (P1 : Stream A1 → bool) `(ex1 : LazyExists (fun x `
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `intros d c0 A0' c2 d2 c3 nZd2 H'0; case H'0; intros H'1 H'2; auto`
- **생성 top5**: `intros a0 m a1 m0 a2 m1 nZa H'; split; auto`(-2.82) · `intros a0 m a1 m0 a2 m1 nZc H' H'0 H'1; split; auto`(-3.19) · `intros a0 m a1 m0 a2 m1 nZa H'`(-3.22) · `intros a0 m a1 m0 a2 m1 nZa H' H'0 H'1; split; auto`(-3.24) · `intros a0 m a1 m0 a2 m1 nZa H'; split`(-3.71)

### step 3 — ✅top1
- **goal(입력 상태)**: `eqA (divA (multA d A0') d2 nZd2) (multA d (divA A0' d2 nZd2)) /\
div_mon n (mult_mon n c0 c2) c3 = mult_mon n c0 (div_mon n c2 c3)`
- **retrieval 증명 top2**: `Lemma takeUntil_length_ForAllIf {A1 A2} (P1 : Stream A1 → bool) `(ex1 : LazyExists (fun x ` ; `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `split; auto`
- **생성 top5**: `split; auto`(-1.56) · `split`(-1.60) · `rewrite H'2`(-4.09) · `case nZd2`(-4.21) · `rewrite <- H'2`(-4.25)

### step 4 — ❌miss
- **goal(입력 상태)**: `eqA (divA (multA d A0') d2 nZd2) (multA d (divA A0' d2 nZd2)) / div_mon n (mult_mon n c0 c2) c3 = mult_mon n c0 (div_mon n c2 c3)`
- **retrieval 증명 top2**: `Lemma takeUntil_length_ForAllIf {A1 A2} (P1 : Stream A1 → bool) `(ex1 : LazyExists (fun x ` ; `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `apply divA_multA_comp_l with (1 := cs)`
- **생성 top5**: `rewrite H'1; rewrite H'2; auto`(-4.12) · `apply divA_eqA_comp with (1 := H'1); auto`(-4.22) · `apply divA_eqA_comp with (1 := H'1)`(-4.62) · `apply divA_eqA_comp with (1 := cs); auto`(-4.89) · `apply multA_eqA_comp with (1 := H'1)`(-5.02)

### step 5 — 🔶topk
- **goal(입력 상태)**: `div_mon n (mult_mon n c0 c2) c3 = mult_mon n c0 (div_mon n c2 c3)`
- **retrieval 증명 top2**: `Lemma takeUntil_length_ForAllIf {A1 A2} (P1 : Stream A1 → bool) `(ex1 : LazyExists (fun x ` ; `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `rewrite H'2`
- **생성 top5**: `rewrite H'2; auto`(-2.36) · `rewrite <- H'2; auto`(-2.68) · `rewrite H'2`(-3.66) · `apply eqA_sym in H'1`(-3.69) · `rewrite <- H'2`(-3.81)

### step 6 — ❌miss
- **goal(입력 상태)**: `div_mon n (mult_mon n c0 (mult_mon n (div_mon n c2 c3) c3)) c3 =
mult_mon n c0 (div_mon n (mult_mon n (div_mon n c2 c3) c3) c3)`
- **retrieval 증명 top2**: `Lemma takeUntil_length_ForAllIf {A1 A2} (P1 : Stream A1 → bool) `(ex1 : LazyExists (fun x ` ; `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `repeat rewrite mult_div_com`
- **생성 top5**: `simpl in |- *`(-3.79) · `apply divA_eqA_comp with (1 := cs); auto`(-3.85) · `apply eqA_sym`(-3.89) · `apply multA_eqA_comp with (1 := cs)`(-3.99) · `apply multA_eqA_comp with (1 := cs); auto`(-4.02)

### step 7 — ❌miss
- **goal(입력 상태)**: `div_mon n (mult_mon n c0 (mult_mon n (div_mon n c2 c3) c3)) c3 =
mult_mon n c0 (div_mon n c2 c3)`
- **retrieval 증명 top2**: `Lemma takeUntil_length_ForAllIf {A1 A2} (P1 : Stream A1 → bool) `(ex1 : LazyExists (fun x ` ; `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `rewrite mult_mon_assoc`
- **생성 top5**: `repeat rewrite mult_assoc`(-3.04) · `rewrite mult_assoc`(-3.75) · `simpl in |- *`(-3.92) · `rewrite H'2`(-4.07) · `rewrite mult_div_com`(-4.11)

### step 8 — ❌miss
- **goal(입력 상태)**: `div_mon n (mult_mon n (mult_mon n c0 (div_mon n c2 c3)) c3) c3 =
mult_mon n c0 (div_mon n c2 c3)`
- **retrieval 증명 top2**: `Lemma takeUntil_length_ForAllIf {A1 A2} (P1 : Stream A1 → bool) `(ex1 : LazyExists (fun x ` ; `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `repeat rewrite mult_div_com; auto`
- **생성 top5**: `rewrite mult_mon_assoc`(-2.78) · `repeat rewrite mult_assoc`(-2.79) · `repeat rewrite mult_mon_assoc`(-3.64) · `rewrite mult_assoc`(-3.79) · `rewrite <- mult_assoc`(-4.44)

## buchberger-theories-DivTerm.v · proof#7 — `Lemma NearBy_comp l1 l2 : l1 = l2 → ∀ ε1 ε2, QposEq ε1 ε2 → ∀ s, (NearBy l1 ε1 s ↔ NearBy l2 ε2 s).`  (11 steps)


### step 0 — 🔶topk
- **goal(입력 상태)**: `forall (a b c : Term A n) (nZa : ~ zeroP A0 eqA (n:=n) a),
eqTerm eqA (n:=n) b (multTerm multA (n:=n) (divTerm b (b:=a) nZa) a) ->
eqTerm eqA (n:=n) (divTerm (multTerm multA (n:=n) b c) (b:=a) nZa)
  `
- **retrieval 증명 top2**: `Definition NearBy (l : X) (ε : QposInf) := ForAll (λ s, ball_ex ε (hd s) l). Proof using p` ; `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinSubset_ball_orC : forall e x a l, FinSubset_ball e x (a :: l)` ; `Lemma FinSubset_ball_cons : forall x e a l, FinSubset_ball e x l -> Fi`
- **gold**: `Proof using plusA minusA invA cs A1`
- **생성 top5**: `Proof`(-1.43) · `Proof using os`(-2.45) · `Proof using cs`(-3.64) · `Proof`(-3.66) · `Proof using plusA minusA invA cs A1`(-3.78)

### step 1 — ❌miss
- **goal(입력 상태)**: `forall (a b c : Term A n) (nZa : ~ zeroP A0 eqA (n:=n) a),
eqTerm eqA (n:=n) b (multTerm multA (n:=n) (divTerm b (b:=a) nZa) a) ->
eqTerm eqA (n:=n) (divTerm (multTerm multA (n:=n) b c) (b:=a) nZa)
  `
- **retrieval 증명 top2**: `Definition NearBy (l : X) (ε : QposInf) := ForAll (λ s, ball_ex ε (hd s) l). Proof using p` ; `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Lemma FinSubset_ball_orC : forall e x a l, FinSubset_ball e x (a :: l)` ; `Lemma FinSubset_ball_cons : forall x e a l, FinSubset_ball e x l -> Fi`
- **gold**: `intros a b c; case a; case b; case c; simpl in |- *; auto`
- **생성 top5**: `intros`(-3.73) · `intros`(-3.77) · `intros l1 l2 Heq ε1 ε2`(-6.04) · `intros l1 l2 H ε1 ε2`(-6.44) · `intros l1 l2 H ε1 ε2 H0 s`(-7.33)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a0 : A) (m : mon n) (a1 : A) (m0 : mon n) 
  (a2 : A) (m1 : mon n) (nZa : ~ eqA a2 A0),
eqA a1 (multA (divA a1 a2 nZa) a2) /\ m0 = mult_mon n (div_mon n m0 m1) m1 ->
eqA (divA (multA a1 a0) a2`
- **retrieval 증명 top2**: `Definition NearBy (l : X) (ε : QposInf) := ForAll (λ s, ball_ex ε (hd s) l). Proof using p` ; `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t`
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `intros a0 m a1 m0 a2 m1 nZa H'; split; auto`
- **생성 top5**: `intros d c0 A0' c2 d2 c3 nZd2 H'0; case H'0; intros H'1 H'2; auto`(-1.10) · `intros d c0 A0' c2 d2 c3 nZd2 H'0`(-4.00) · `intros d c0 A0' c2 d2 c3 H'0; case H'0; intros H'1 H'2; auto`(-4.53) · `intros d c0 A0' c2 d2 c3 nZd2 H'`(-5.43) · `intros d c0 A0' c2 d2 c3 nZd2 H'; case H'`(-5.55)

### step 3 — ❌miss
- **goal(입력 상태)**: `eqA (divA (multA a1 a0) a2 nZa) (multA (divA a1 a2 nZa) a0) / div_mon n (mult_mon n m0 m) m1 = mult_mon n (div_mon n m0 m1) m`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Lemma takeUntil_length_ForAllIf {A1 A2} (P1 : Stream A1 → bool) `(ex1 : LazyExists (fun x `
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `apply divA_multA_comp_r with (1 := cs)`
- **생성 top5**: `case H'; intros H'0 H'1; clear H'`(-2.14) · `case H'; intros H'3 H'4; clear H'`(-2.18) · `case H'`(-2.85) · `case H'; intros H'1 H'2; clear H'`(-3.63) · `-`(-3.70)

### step 4 — ❌miss
- **goal(입력 상태)**: `div_mon n (mult_mon n m0 m) m1 = mult_mon n (div_mon n m0 m1) m`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Lemma takeUntil_length_ForAllIf {A1 A2} (P1 : Stream A1 → bool) `(ex1 : LazyExists (fun x `
- **retrieval premise top3**: `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat` ; `Lemma infinitePidgeonHolePrinicpleB : forall (X:Type) (l:list X) (f:na` ; `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->`
- **gold**: `elim H'; intros H'0 H'1; rewrite H'1; clear H'`
- **생성 top5**: `apply divA_eqA_comp with (1 := cs)`(-3.28) · `destruct H'`(-3.43) · `case H'; intros H'0 H'1; clear H'`(-3.81) · `apply (eqA_trans _ _ _ _ _ _ _ _ _ cs)`(-4.39) · `apply divA_multA_comp_r with (1 := cs)`(-4.56)

### step 5 — ❌miss
- **goal(입력 상태)**: `div_mon n (mult_mon n (mult_mon n (div_mon n m0 m1) m1) m) m1 =
mult_mon n (div_mon n (mult_mon n (div_mon n m0 m1) m1) m1) m`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Lemma takeUntil_length_ForAllIf {A1 A2} (P1 : Stream A1 → bool) `(ex1 : LazyExists (fun x `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `rewrite mult_div_com; auto`
- **생성 top5**: `apply divA_eqA_comp with (1 := cs)`(-4.29) · `apply divA_multA_comp_r with (1 := cs)`(-4.31) · `elim H'; intros H'2 H'3; rewrite H'3; clear H'`(-4.50) · `apply multA_eqA_comp with (1 := cs)`(-4.86) · `unfold div_mon in |- *`(-4.86)

### step 6 — ❌miss
- **goal(입력 상태)**: `div_mon n (mult_mon n (mult_mon n (div_mon n m0 m1) m1) m) m1 =
mult_mon n (div_mon n m0 m1) m`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Lemma takeUntil_length_ForAllIf {A1 A2} (P1 : Stream A1 → bool) `(ex1 : LazyExists (fun x `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `rewrite <- mult_mon_assoc`
- **생성 top5**: `rewrite mult_div_com; auto`(-1.84) · `elim H'; intros H'0 H'1; rewrite H'1; clear H'`(-2.89) · `rewrite mult_assoc; auto`(-3.05) · `apply mult_div_com; auto`(-4.50) · `elim H'; intros H'2 H'3; rewrite H'3; clear H'`(-4.83)

### step 7 — ❌miss
- **goal(입력 상태)**: `div_mon n (mult_mon n (div_mon n m0 m1) (mult_mon n m1 m)) m1 =
mult_mon n (div_mon n m0 m1) m`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Lemma takeUntil_length_ForAllIf {A1 A2} (P1 : Stream A1 → bool) `(ex1 : LazyExists (fun x `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `rewrite (mult_mon_com n m1 m)`
- **생성 top5**: `rewrite <- mult_mon_assoc`(-3.16) · `rewrite <- mult_mon_assoc; auto`(-4.53) · `rewrite mult_mon_assoc; auto`(-4.80) · `rewrite mult_mon_id; auto`(-5.01) · `rewrite mult_mon_assoc`(-5.05)

### step 8 — ✅top1
- **goal(입력 상태)**: `div_mon n (mult_mon n (div_mon n m0 m1) (mult_mon n m m1)) m1 =
mult_mon n (div_mon n m0 m1) m`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Lemma takeUntil_length_ForAllIf {A1 A2} (P1 : Stream A1 → bool) `(ex1 : LazyExists (fun x `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `rewrite mult_mon_assoc`
- **생성 top5**: `rewrite mult_mon_assoc`(-2.76) · `rewrite <- mult_mon_assoc`(-2.76) · `rewrite mult_mon_assoc; auto`(-3.48) · `rewrite mult_div_com; auto`(-3.87) · `rewrite (mult_mon_com n m m1)`(-4.04)

### step 9 — ❌miss
- **goal(입력 상태)**: `div_mon n (mult_mon n (mult_mon n (div_mon n m0 m1) m) m1) m1 =
mult_mon n (div_mon n m0 m1) m`
- **retrieval 증명 top2**: `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_t` ; `Lemma takeUntil_length_ForAllIf {A1 A2} (P1 : Stream A1 → bool) `(ex1 : LazyExists (fun x `
- **retrieval premise top3**: `Lemma existsC_ind : forall (Q:Prop), (~~Q -> Q) -> (forall x:A, P x ->` ; `Lemma orC_ind : forall (P Q G:Prop), (~~G -> G) -> (P -> G) -> (Q -> G` ; `Lemma infinitePidgeonHolePrinicple : forall (X:Type) (l:list X) (P:nat`
- **gold**: `rewrite mult_div_com; auto`
- **생성 top5**: `rewrite <- mult_mon_assoc`(-2.72) · `rewrite mult_mon_assoc`(-2.95) · `rewrite (mult_mon_com n m m1)`(-3.07) · `rewrite (mult_mon_com n m0 m1)`(-3.26) · `rewrite mult_assoc`(-3.93)

## buchberger-theories-Fred.v · proof#0 — `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor F, !Is1Functor F} {a b : A} (e : a $<~> b) : cate_fun (emap `  (4 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (L : list poly) (p : poly), zerop (nf L p) -> cb L p`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros L p H'`
- **생성 top5**: `intros`(-1.52) · `reflexivity`(-3.15) · `intros`(-3.18) · `intros`(-3.29) · `intros L p H`(-3.53)

### step 2 — ❌miss
- **goal(입력 상태)**: `cb L p`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `apply zerop_elim_cb with (p := nf L p); auto`
- **생성 top5**: `induction L`(-3.93) · `unfold zerop in H'`(-4.14) · `apply cb_zerop`(-5.29) · `unfold zerop in *`(-5.67) · `destruct (zerop_elim_cb _ _ _ H')`(-5.71)

## buchberger-theories-Fred.v · proof#1 — `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b).`  (9 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `list poly -> list poly -> list poly`
- **retrieval 증명 top1**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros H'; elim H'`
- **생성 top5**: `intros L1 L2`(-1.98) · `intros`(-3.28) · `intros L1 L2`(-3.30) · `intros`(-3.97) · `intros f g`(-4.27)

### step 2 — ❌miss
- **goal(입력 상태)**: `list poly -> list poly / poly -> list poly -> (list poly -> list poly) -> list poly -> list poly`
- **retrieval 증명 top1**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros L; exact (nil (A:=poly))`
- **생성 top5**: `-`(-0.88) · `-`(-3.34) · `+`(-3.38) · `exact idmap`(-3.99) · `exact (fun L => L)`(-4.43)

### step 3 — ❌miss
- **goal(입력 상태)**: `poly -> list poly -> (list poly -> list poly) -> list poly -> list poly`
- **retrieval 증명 top1**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros a p Rec Acc`
- **생성 top5**: `intros p L; exact (p :: L)`(-4.85) · `intros p L1 L2`(-4.93) · `intros p L1 IH L2`(-5.03) · `intros p L1 f L2`(-5.09) · `intros p L1 e L2`(-5.32)

### step 4 — ❌miss
- **goal(입력 상태)**: `list poly`
- **retrieval 증명 top1**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `apply LetP with (A := poly) (h := nf (p ++ Acc) a)`
- **생성 top5**: `exact (p :: Acc)`(-3.03) · `exact (p ++ Acc)`(-3.76) · `induction Acc`(-4.09) · `exact (a :: Acc)`(-4.20) · `induction p`(-4.26)

### step 5 — ❌miss
- **goal(입력 상태)**: `forall u : poly, u = nf (p ++ Acc) a -> list poly`
- **retrieval 증명 top1**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros u H'0; case (zerop_dec u); intros Z`
- **생성 top5**: `intros u H`(-3.42) · `intros u e`(-3.61) · `intros u Hu`(-4.14) · `intros q Hq`(-4.20) · `intros u Hu`(-4.55)

### step 6 — ❌miss
- **goal(입력 상태)**: `list poly / list poly`
- **retrieval 증명 top1**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `exact (Rec Acc)`
- **생성 top5**: `-`(-1.39) · `+`(-2.89) · `exact (nil (A:=poly))`(-3.52) · `-`(-3.96) · `exact p`(-4.21)

### step 7 — ❌miss
- **goal(입력 상태)**: `list poly`
- **retrieval 증명 top1**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `exact (u :: Rec (u :: Acc))`
- **생성 top5**: `exact p`(-2.31) · `exact (p ++ Acc)`(-2.95) · `elim Z`(-3.73) · `exact (p ++ [u])`(-3.95) · `exact (p ++ [a])`(-4.51)

## buchberger-theories-Fred.v · proof#2 — `Record core (A : Type) := { uncore : A }.`  (13 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (L1 L2 : list poly) (p : poly), In p (redacc L1 L2) -> cb (L1 ++ L2) p`
- **retrieval 증명 top2**: `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro` ; `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros L1; elim L1; auto`
- **생성 top5**: `intros L1 L2 p H`(-2.92) · `intros L1 L2 p H'`(-2.92) · `intros L1 L2 p`(-3.51) · `intros`(-4.12) · `intros L1 L2`(-4.40)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a : poly) (l : list poly),
(forall (L2 : list poly) (p : poly), In p (redacc l L2) -> cb (l ++ L2) p) ->
forall (L2 : list poly) (p : poly),
In p (redacc (a :: l) L2) -> cb ((a :: l) ++ L2) p`
- **retrieval 증명 top2**: `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro` ; `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `simpl in |- *; auto`
- **생성 top5**: `intros a L1' Rec L2 p H'`(-4.59) · `intros a L1' Rec L2 p H`(-5.09) · `-`(-5.11) · `intros a L1' Rec L2' p H'`(-5.95) · `intros a L1' IH L2 p H`(-6.01)

### step 3 — ❌miss
- **goal(입력 상태)**: `forall (a : poly) (l : list poly),
(forall (L2 : list poly) (p : poly), In p (redacc l L2) -> cb (l ++ L2) p) ->
forall (L2 : list poly) (p : poly),
In p
  (LetP poly (list poly) (nf (l ++ L2) a)
    `
- **retrieval 증명 top2**: `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro` ; `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `simpl in |- *; unfold LetP in |- *; intros a l H' L2 p`
- **생성 top5**: `simpl in |- *`(-3.13) · `simpl in |- *; auto`(-3.54) · `intros a L1' Rec L2 p H'`(-5.24) · `intros a L1' Rec L2 p H`(-5.74) · `intros a L1' Rec L2' p H'`(-6.17)

### step 4 — ✅top1
- **goal(입력 상태)**: `In p
  (if zerop_dec (nf (l ++ L2) a)
   then redacc l L2
   else nf (l ++ L2) a :: redacc l (nf (l ++ L2) a :: L2)) ->
cb (a :: l ++ L2) p`
- **retrieval 증명 top2**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor ` ; `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `case (zerop_dec (nf (l ++ L2) a))`
- **생성 top5**: `case (zerop_dec (nf (l ++ L2) a))`(-1.90) · `case (zerop_dec (nf (l ++ L2) a)); intros Z`(-2.78) · `case zerop_dec`(-3.31) · `elim (zerop_dec (nf (l ++ L2) a))`(-3.42) · `case (zerop_dec (nf (l ++ L2) a)); auto`(-3.53)

### step 5 — 🔶topk
- **goal(입력 상태)**: `zerop (nf (l ++ L2) a) -> In p (redacc l L2) -> cb (a :: l ++ L2) p / ~ zerop (nf (l ++ L2) a) ->
In p (nf (l ++ L2) a :: redacc l (nf (l ++ L2) a :: L2)) ->
cb (a :: l ++ L2) p`
- **retrieval 증명 top2**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor ` ; `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros H'0 H'1`
- **생성 top5**: `-`(-3.74) · `simpl in |- *; auto`(-3.75) · `intros Z`(-3.82) · `simpl in |- *`(-4.16) · `auto`(-4.20)

### step 6 — ❌miss
- **goal(입력 상태)**: `cb (a :: l ++ L2) p / ~ zerop (nf (l ++ L2) a) ->
In p (nf (l ++ L2) a :: redacc l (nf (l ++ L2) a :: L2)) ->
cb (a :: l ++ L2) p`
- **retrieval 증명 top2**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor ` ; `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `apply cb_incl with (L1 := l ++ L2); auto`
- **생성 top5**: `apply H'`(-3.92) · `simpl in |- *`(-4.30) · `case (zerop_dec p)`(-4.39) · `simpl in H'1`(-4.45) · `apply zerop_elim_cb with (p := nf (l ++ L2) a); auto`(-4.51)

### step 7 — 🔶topk
- **goal(입력 상태)**: `~ zerop (nf (l ++ L2) a) ->
In p (nf (l ++ L2) a :: redacc l (nf (l ++ L2) a :: L2)) ->
cb (a :: l ++ L2) p`
- **retrieval 증명 top2**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor ` ; `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `simpl in |- *`
- **생성 top5**: `intros H'0 H'1`(-0.86) · `simpl in |- *; intros H'0 H'1`(-3.10) · `simpl in |- *`(-3.52) · `intros`(-4.51) · `intros H'1 H'2`(-4.57)

### step 8 — ❌miss
- **goal(입력 상태)**: `~ zerop (nf (l ++ L2) a) ->
nf (l ++ L2) a = p \/ In p (redacc l (nf (l ++ L2) a :: L2)) ->
cb (a :: l ++ L2) p`
- **retrieval 증명 top2**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor ` ; `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros H'0 H'1; case H'1; [ intros H'2; rewrite <- H'2; clear H'1 | intros H'2; clear H'1 ]; auto`
- **생성 top5**: `intros H'0 H'1`(-1.04) · `case (zerop_dec p)`(-3.37) · `case (zerop_dec p); intros H'0 H'1`(-4.26) · `intro H'0`(-4.45) · `intros H'1 H'2`(-4.70)

### step 9 — ❌miss
- **goal(입력 상태)**: `cb (a :: l ++ L2) p`
- **retrieval 증명 top2**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor ` ; `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `apply cb_trans with (p := nf (l ++ L2) a); auto`
- **생성 top5**: `apply H'`(-2.83) · `simpl in H'2`(-3.12) · `simpl in |- *`(-3.23) · `apply H'; auto`(-3.39) · `apply H'; simpl in |- *; auto`(-3.96)

### step 10 — ❌miss
- **goal(입력 상태)**: `cb (nf (l ++ L2) a :: a :: l ++ L2) p`
- **retrieval 증명 top2**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor ` ; `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `apply cb_incl with (L1 := l ++ nf (l ++ L2) a :: L2); auto`
- **생성 top5**: `simpl in |- *`(-1.71) · `apply H'`(-2.74) · `apply cb_incl with (L1 := l ++ L2); auto`(-2.84) · `apply cb_nf`(-2.94) · `apply cb_nf; auto`(-4.11)

### step 11 — ❌miss
- **goal(입력 상태)**: `incl (l ++ nf (l ++ L2) a :: L2) (nf (l ++ L2) a :: a :: l ++ L2)`
- **retrieval 증명 top2**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor ` ; `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `apply incl_app; auto with datatypes`
- **생성 top5**: `simpl in |- *`(-1.51) · `simpl in |- *; auto`(-3.07) · `intros H'1`(-3.61) · `intros x H'1`(-4.07) · `unfold incl in |- *`(-4.23)

## buchberger-theories-Fred.v · proof#3 — `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A).`  (6 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (L : list poly) (p : poly), In p (red L) -> cb L p`
- **retrieval 증명 top2**: `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro` ; `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `unfold red in |- *`
- **생성 top5**: `intros L p H'`(-3.00) · `intros L p H'; elim H'`(-3.34) · `intros L1; elim L1; auto`(-3.42) · `split`(-4.28) · `intros L p`(-4.31)

### step 2 — ✅top1
- **goal(입력 상태)**: `forall (L : list poly) (p : poly), In p (redacc L nil) -> cb L p`
- **retrieval 증명 top2**: `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro` ; `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros L p H'`
- **생성 top5**: `intros L p H'`(-2.35) · `simpl in |- *`(-3.19) · `intros L p H'; elim H'`(-3.53) · `intros L p H`(-3.85) · `intros L p`(-3.90)

### step 3 — ❌miss
- **goal(입력 상태)**: `cb L p`
- **retrieval 증명 top2**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor ` ; `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `generalize (redacc_cb L nil); simpl in |- *; auto`
- **생성 top5**: `elim H'`(-2.65) · `apply zerop_elim_cb with (p := nf L p); auto`(-3.21) · `elim H'; auto`(-3.80) · `case H'`(-3.81) · `apply zerop_elim_cb with (p := p); auto`(-4.36)

### step 4 — ❌miss
- **goal(입력 상태)**: `(forall p0 : poly, In p0 (redacc L nil) -> cb (L ++ nil) p0) -> cb L p`
- **retrieval 증명 top2**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor ` ; `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `rewrite app_nil_r; auto`
- **생성 top5**: `case H'`(-3.03) · `intros H'0`(-3.27) · `simpl in |- *`(-3.84) · `elim H'`(-4.10) · `elim H'; auto`(-4.48)

## buchberger-theories-Fred.v · proof#4 — `Global Instance is01cat_core {A : Type} `{HasEquivs A} : Is01Cat (core A).`  (21 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (L1 L2 : list poly) (p : poly), In p L1 -> cb (redacc L1 L2 ++ L2) p`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros L1; elim L1; simpl in |- *; auto`
- **생성 top5**: `unfold red in |- *`(-1.88) · `intros L1; elim L1; auto`(-2.04) · `intros L1 L2 p H'`(-2.71) · `intros L1; elim L1`(-3.80) · `intros L1 L2 p H'; elim H'`(-3.91)

### step 2 — 🔶topk
- **goal(입력 상태)**: `forall (L2 : list poly) (p : poly), False -> cb L2 p / forall (a : poly) (l : list poly),
(forall (L2 : list poly) (p : poly), In p l -> cb (redacc l L2 ++ L2) p) ->
forall (L2 : list poly) (p : poly)`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros L2 p H'; elim H'; auto`
- **생성 top5**: `intros L2 p H'; elim H'`(-2.57) · `intros L2 p H'`(-2.72) · `intros L2 p H'; elim H'; auto`(-3.76) · `contradiction`(-3.80) · `intros L2 p H'; case H'`(-4.72)

### step 3 — ❌miss
- **goal(입력 상태)**: `forall (a : poly) (l : list poly),
(forall (L2 : list poly) (p : poly), In p l -> cb (redacc l L2 ++ L2) p) ->
forall (L2 : list poly) (p : poly),
a = p \/ In p l ->
cb
  (LetP poly (list poly) (nf (l`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `unfold LetP in |- *`
- **생성 top5**: `simpl in |- *`(-3.49) · `intros a p Rec L2 p H'`(-3.87) · `intros a p Rec L2 p H'; elim H'`(-5.36) · `intros a L1' Rec L2 p H'`(-5.47) · `simpl in |- *; intros a p Rec L2 p H'`(-5.63)

### step 4 — ❌miss
- **goal(입력 상태)**: `forall (a : poly) (l : list poly),
(forall (L2 : list poly) (p : poly), In p l -> cb (redacc l L2 ++ L2) p) ->
forall (L2 : list poly) (p : poly),
a = p \/ In p l ->
cb
  ((if zerop_dec (nf (l ++ L2) `
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros a l H' L2 p H'0; case H'0; [ intros H'1; rewrite H'1; clear H'0 | intros H'1; clear H'0 ]; auto`
- **생성 top5**: `simpl in |- *`(-3.32) · `intros a p Rec L2 p H'`(-4.14) · `intros a l H' L2 p`(-4.36) · `intros a l Rec L2 p H'`(-4.52) · `intros a L1' Rec L2 p H'`(-5.09)

### step 5 — ❌miss
- **goal(입력 상태)**: `cb
  ((if zerop_dec (nf (l ++ L2) p)
    then redacc l L2
    else nf (l ++ L2) p :: redacc l (nf (l ++ L2) p :: L2)) ++ L2) p / cb
  ((if zerop_dec (nf (l ++ L2) a)
    then redacc l L2
    else nf (`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `case (zerop_dec (nf (l ++ L2) p)); auto`
- **생성 top5**: `simpl in |- *`(-2.64) · `apply cb_trans with (p := nf (l ++ L2) a); auto`(-2.94) · `case (zerop_dec (nf (l ++ L2) a))`(-3.46) · `apply cb_incl with (L1 := l ++ L2); auto`(-3.79) · `apply cb_nf`(-4.10)

### step 6 — ❌miss
- **goal(입력 상태)**: `zerop (nf (l ++ L2) p) -> cb (redacc l L2 ++ L2) p / ~ zerop (nf (l ++ L2) p) ->
cb ((nf (l ++ L2) p :: redacc l (nf (l ++ L2) p :: L2)) ++ L2) p / cb
  ((if zerop_dec (nf (l ++ L2) a)
    then redacc`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros H'0`
- **생성 top5**: `case (zerop_dec (nf (l ++ L2) a)); auto`(-1.01) · `simpl in |- *`(-3.40) · `case (zerop_dec (nf (l ++ L2) a)); intros Z`(-4.08) · `apply cb_incl with (L1 := l ++ L2); auto`(-4.50) · `case (zerop_dec (nf (l ++ L2) a))`(-4.71)

### step 7 — ❌miss
- **goal(입력 상태)**: `cb (redacc l L2 ++ L2) p / ~ zerop (nf (l ++ L2) p) ->
cb ((nf (l ++ L2) p :: redacc l (nf (l ++ L2) p :: L2)) ++ L2) p / cb
  ((if zerop_dec (nf (l ++ L2) a)
    then redacc l L2
    else nf (l ++ L2`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `apply cb_comp with (L1 := l ++ L2); auto`
- **생성 top5**: `case (zerop_dec (nf (l ++ L2) a)); auto`(-2.63) · `apply cb_incl with (L1 := l ++ L2); auto`(-2.92) · `apply cb_incl with (L1 := l ++ nf (l ++ L2) p :: L2); auto`(-3.86) · `apply cb_trans with (p := nf (l ++ L2) p); auto`(-4.46) · `apply cb_nf`(-4.50)

### step 8 — ❌miss
- **goal(입력 상태)**: `forall p0 : poly, In p0 (l ++ L2) -> cb (redacc l L2 ++ L2) p0 / ~ zerop (nf (l ++ L2) p) ->
cb ((nf (l ++ L2) p :: redacc l (nf (l ++ L2) p :: L2)) ++ L2) p / cb
  ((if zerop_dec (nf (l ++ L2) a)
   `
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros p0 H'2`
- **생성 top5**: `simpl in |- *`(-2.30) · `case (zerop_dec (nf (l ++ L2) a)); auto`(-2.46) · `apply cb_incl with (L1 := l ++ nf (l ++ L2) p :: L2); auto`(-3.46) · `apply cb_nf`(-3.87) · `apply cb_incl with (L1 := l ++ L2); auto`(-3.99)

### step 9 — ❌miss
- **goal(입력 상태)**: `cb (redacc l L2 ++ L2) p0 / ~ zerop (nf (l ++ L2) p) ->
cb ((nf (l ++ L2) p :: redacc l (nf (l ++ L2) p :: L2)) ++ L2) p / cb
  ((if zerop_dec (nf (l ++ L2) a)
    then redacc l L2
    else nf (l ++ L`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `lapply (in_app_or l L2 p0); auto`
- **생성 top5**: `case (zerop_dec (nf (l ++ L2) p0)); auto`(-2.62) · `apply cb_incl with (L1 := l ++ L2); auto`(-2.65) · `case (zerop_dec p0); auto`(-2.82) · `simpl in |- *`(-4.07) · `apply cb_trans with (p := nf (l ++ L2) p); auto`(-4.13)

### step 10 — ❌miss
- **goal(입력 상태)**: `In p0 l \/ In p0 L2 -> cb (redacc l L2 ++ L2) p0 / ~ zerop (nf (l ++ L2) p) ->
cb ((nf (l ++ L2) p :: redacc l (nf (l ++ L2) p :: L2)) ++ L2) p / cb
  ((if zerop_dec (nf (l ++ L2) a)
    then redacc l`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros H'3; case H'3; auto`
- **생성 top5**: `case (zerop_dec (nf (l ++ L2) p)); auto`(-2.64) · `simpl in |- *`(-3.51) · `intros H'2`(-3.95) · `intros H'0`(-4.04) · `elim H'2; auto`(-4.42)

### step 11 — ❌miss
- **goal(입력 상태)**: `~ zerop (nf (l ++ L2) p) ->
cb ((nf (l ++ L2) p :: redacc l (nf (l ++ L2) p :: L2)) ++ L2) p / cb
  ((if zerop_dec (nf (l ++ L2) a)
    then redacc l L2
    else nf (l ++ L2) a :: redacc l (nf (l ++ L`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros H'0`
- **생성 top5**: `case (zerop_dec (nf (l ++ L2) p)); auto`(-2.39) · `case (zerop_dec (nf (l ++ L2) a)); auto`(-3.53) · `apply cb_incl with (L1 := l ++ L2); auto`(-3.65) · `simpl in |- *`(-3.68) · `apply cb_nf; auto`(-4.06)

### step 12 — ❌miss
- **goal(입력 상태)**: `cb ((nf (l ++ L2) p :: redacc l (nf (l ++ L2) p :: L2)) ++ L2) p / cb
  ((if zerop_dec (nf (l ++ L2) a)
    then redacc l L2
    else nf (l ++ L2) a :: redacc l (nf (l ++ L2) a :: L2)) ++ L2) p`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `2: case (zerop_dec (nf (l ++ L2) a)); auto`
- **생성 top5**: `apply cb_trans with (p := nf (l ++ L2) p); auto`(-2.67) · `apply cb_incl with (L1 := l ++ L2); auto`(-2.74) · `apply cb_comp with (L1 := l ++ L2); auto`(-2.89) · `case (zerop_dec (nf (l ++ L2) p)); auto`(-3.39) · `apply cb_nf; auto`(-3.52)

### step 13 — ❌miss
- **goal(입력 상태)**: `cb ((nf (l ++ L2) p :: redacc l (nf (l ++ L2) p :: L2)) ++ L2) p / ~ zerop (nf (l ++ L2) a) ->
cb ((nf (l ++ L2) a :: redacc l (nf (l ++ L2) a :: L2)) ++ L2) p`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `2: intros H'0`
- **생성 top5**: `intros H'0`(-1.09) · `intros H'2`(-3.75) · `apply cb_incl with (L1 := l ++ L2); auto`(-3.99) · `intros H'0 H'1`(-4.08) · `apply cb_comp with (L1 := l ++ L2); auto`(-4.30)

### step 14 — ❌miss
- **goal(입력 상태)**: `cb ((nf (l ++ L2) p :: redacc l (nf (l ++ L2) p :: L2)) ++ L2) p / cb ((nf (l ++ L2) a :: redacc l (nf (l ++ L2) a :: L2)) ++ L2) p`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `2: apply cb_incl with (L1 := redacc l (nf (l ++ L2) a :: L2) ++ nf (l ++ L2) a :: L2); auto with datatypes`
- **생성 top5**: `apply cb_incl with (L1 := l ++ L2); auto`(-2.45) · `apply cb_comp with (L1 := l ++ L2); auto`(-2.94) · `apply cb_trans with (p := nf (l ++ L2) a); auto`(-3.40) · `2: case (zerop_dec (nf (l ++ L2) p)); auto`(-3.72) · `3: case (zerop_dec (nf (l ++ L2) a)); auto`(-3.74)

### step 15 — ❌miss
- **goal(입력 상태)**: `cb ((nf (l ++ L2) p :: redacc l (nf (l ++ L2) p :: L2)) ++ L2) p`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `apply cb_compo with (L1 := nf (l ++ L2) p :: l ++ L2); simpl in |- *; auto`
- **생성 top5**: `apply cb_nf`(-2.98) · `simpl in |- *`(-3.18) · `rewrite app_comm_cons`(-3.83) · `apply cb_comp with (L1 := l ++ L2); auto`(-3.92) · `rewrite app_assoc`(-3.99)

### step 16 — ❌miss
- **goal(입력 상태)**: `forall q : poly,
nf (l ++ L2) p = q \/ In q (l ++ L2) ->
cb (nf (l ++ L2) p :: redacc l (nf (l ++ L2) p :: L2) ++ L2) q`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros q H'2; case H'2; [ intros H'3; rewrite <- H'3; clear H'2 | intros H'3; clear H'2 ]; auto with datatypes`
- **생성 top5**: `intros q H'2`(-1.38) · `intros q H'2; case H'2; auto`(-2.59) · `intros q H'3`(-3.38) · `intros p0 H'2`(-3.73) · `intros q H'2; case H'2`(-3.98)

### step 17 — ❌miss
- **goal(입력 상태)**: `cb (nf (l ++ L2) p :: redacc l (nf (l ++ L2) p :: L2) ++ L2) q`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `case (in_app_or l L2 q H'3); auto with datatypes`
- **생성 top5**: `apply cb_nf`(-3.15) · `simpl in |- *`(-3.45) · `apply cb_incl with (L1 := l ++ L2); auto`(-3.79) · `apply nf_cb`(-4.10) · `case (zerop_dec q); auto`(-4.33)

### step 18 — ✅top1
- **goal(입력 상태)**: `In q l -> cb (nf (l ++ L2) p :: redacc l (nf (l ++ L2) p :: L2) ++ L2) q`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros H'2`
- **생성 top5**: `intros H'2`(-1.61) · `intros H'4`(-2.95) · `intros H'2; apply cb_incl with (L1 := l ++ L2); auto`(-4.69) · `intros H'2; apply cb_trans with (p := nf (l ++ L2) p); auto`(-5.20) · `intros H'2; apply cb_incl with (L1 := l ++ L2); auto with datatypes`(-5.21)

### step 19 — 🔶topk
- **goal(입력 상태)**: `cb (nf (l ++ L2) p :: redacc l (nf (l ++ L2) p :: L2) ++ L2) q`
- **retrieval 증명 top2**: `Record core (A : Type) := { uncore : A }. Proof. intros L1; elim L1; auto. simpl in |- *; ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `apply cb_incl with (L1 := redacc l (nf (l ++ L2) p :: L2) ++ nf (l ++ L2) p :: L2); auto with datatypes`
- **생성 top5**: `apply cb_incl with (L1 := l ++ L2); auto`(-3.48) · `apply cb_comp with (L1 := l ++ L2); auto`(-3.73) · `apply cb_nf`(-3.73) · `apply cb_incl with (L1 := l ++ L2); auto with datatypes`(-3.99) · `apply cb_incl with (L1 := redacc l (nf (l ++ L2) p :: L2)); auto`(-4.26)

## buchberger-theories-Fred.v · proof#5 — `Global Instance is2graph_core {A : Type} `{HasEquivs A} : Is2Graph (core A).`  (5 steps)


### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (L : list poly) (p : poly), In p L -> cb (red L) p`
- **retrieval 증명 top2**: `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r` ; `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros L p H'`
- **생성 top5**: `unfold red in |- *`(-1.07) · `intros L p H'`(-2.01) · `intros L p H'; elim H'`(-3.20) · `intros L1; elim L1; simpl in |- *; auto`(-3.63) · `intros L1; elim L1; auto`(-3.97)

### step 2 — ❌miss
- **goal(입력 상태)**: `cb (red L) p`
- **retrieval 증명 top2**: `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor ` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `lapply (cb_redacc L nil p); [ intros H'3; generalize H'3 | idtac ]; simpl in |- *; auto`
- **생성 top5**: `generalize (redacc_cb L nil); simpl in |- *; auto`(-1.82) · `unfold red in |- *`(-1.96) · `generalize (red_cb L nil); simpl in |- *; auto`(-3.37) · `elim H'`(-3.49) · `generalize (redacc_cb L nil); simpl in |- *`(-4.70)

### step 3 — 🔶topk
- **goal(입력 상태)**: `cb (redacc L nil ++ nil) p -> cb (red L) p`
- **retrieval 증명 top2**: `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r` ; `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `rewrite app_nil_r; auto`
- **생성 top5**: `intros H'4`(-2.10) · `rewrite app_nil_r; auto`(-2.78) · `intros H'0`(-2.95) · `intros H'2`(-3.35) · `intros H'4; generalize H'4`(-5.21)

## buchberger-theories-Fred.v · proof#6 — `Global Instance is01cat_core_hom {A : Type} `{HasEquivs A} (a b : core A) : Is01Cat (a $-> b).`  (6 steps)


### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (p : poly) (L : list poly), cb L p -> cb (red L) p`
- **retrieval 증명 top2**: `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r` ; `Global Instance is2graph_core {A : Type} `{HasEquivs A} : Is2Graph (core A). Proof. intros`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros p L H'`
- **생성 top5**: `unfold red in |- *`(-2.46) · `intros p L H'`(-2.67) · `intros L p H'`(-3.14) · `intros L1 L2 H'`(-4.63) · `intros L1 p H'`(-4.66)

### step 2 — ❌miss
- **goal(입력 상태)**: `cb (red L) p`
- **retrieval 증명 top2**: `Global Instance is2graph_core {A : Type} `{HasEquivs A} : Is2Graph (core A). Proof. intros` ; `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `apply cb_compo with (L1 := L); auto`
- **생성 top5**: `unfold red in |- *`(-3.15) · `elim H'`(-3.37) · `elim H'; auto`(-3.63) · `elim H'; simpl in |- *; auto`(-3.77) · `generalize (redacc_cb L nil); simpl in |- *; auto`(-4.56)

### step 3 — ✅top1
- **goal(입력 상태)**: `forall q : poly, In q L -> cb (red L) q`
- **retrieval 증명 top2**: `Global Instance is2graph_core {A : Type} `{HasEquivs A} : Is2Graph (core A). Proof. intros` ; `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor `
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros q H'0`
- **생성 top5**: `intros q H'0`(-1.74) · `intros q H'0; elim H'0; auto`(-3.35) · `unfold red in |- *`(-3.70) · `intros q H'0; case H'0; auto`(-4.06) · `intros q H'0; apply cb_incl with (L1 := L); auto`(-4.23)

### step 4 — ❌miss
- **goal(입력 상태)**: `cb (red L) q`
- **retrieval 증명 top2**: `Global Instance is01cat_core {A : Type} `{HasEquivs A} : Is01Cat (core A). Proof. intros L` ; `Global Instance is2graph_core {A : Type} `{HasEquivs A} : Is2Graph (core A). Proof. intros`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `apply cb_red; auto`
- **생성 top5**: `apply cb_incl with (L1 := L); auto`(-3.24) · `unfold red in |- *`(-3.69) · `lapply (in_app_or L q); auto`(-4.14) · `apply cb_incl with (L1 := red L); auto`(-4.20) · `lapply (in_app_or L nil q H'0); auto`(-4.62)

## buchberger-theories-Fred.v · proof#7 — `Global Instance is0gpd_core_hom {A : Type} `{HasEquivs A} (a b : core A) : Is0Gpd (a $-> b).`  (6 steps)


### step 1 — ✅top1
- **goal(입력 상태)**: `forall (p : poly) (L : list poly), cb (red L) p -> cb L p`
- **retrieval 증명 top2**: `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b). Pro` ; `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A). Proof. unfold r`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros p L H'`
- **생성 top5**: `intros p L H'`(-0.56) · `unfold red in |- *`(-3.14) · `intros p L H'; elim H'`(-3.91) · `intros L1 p H'`(-4.46) · `intros L p H'`(-4.68)

### step 2 — 🔶topk
- **goal(입력 상태)**: `cb L p`
- **retrieval 증명 top2**: `Global Instance is2graph_core {A : Type} `{HasEquivs A} : Is2Graph (core A). Proof. intros` ; `Global Instance is01cat_core_hom {A : Type} `{HasEquivs A} (a b : core A) : Is01Cat (a $->`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `apply cb_compo with (L1 := red L); auto`
- **생성 top5**: `apply cb_compo with (L1 := L); auto`(-1.01) · `apply cb_red; auto`(-3.35) · `apply cb_comp with (L1 := L); auto`(-3.74) · `apply cb_compo with (L1 := red L); auto`(-4.22) · `unfold red in H'`(-4.49)

### step 3 — ✅top1
- **goal(입력 상태)**: `forall q : poly, In q (red L) -> cb L q`
- **retrieval 증명 top2**: `Global Instance is2graph_core {A : Type} `{HasEquivs A} : Is2Graph (core A). Proof. intros` ; `Global Instance is01cat_core_hom {A : Type} `{HasEquivs A} (a b : core A) : Is01Cat (a $->`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `intros q H'0`
- **생성 top5**: `intros q H'0`(-0.22) · `intros q H'0; apply cb_red; auto`(-4.11) · `intros q H''`(-4.18) · `intros q H'0; generalize H'0`(-5.14) · `intros q H'0; case H'0; auto`(-5.23)

### step 4 — ❌miss
- **goal(입력 상태)**: `cb L q`
- **retrieval 증명 top2**: `Global Instance is01cat_core_hom {A : Type} `{HasEquivs A} (a b : core A) : Is01Cat (a $->` ; `Global Instance is01cat_core {A : Type} `{HasEquivs A} : Is01Cat (core A). Proof. intros L`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int`
- **gold**: `apply red_cb; auto`
- **생성 top5**: `apply cb_red; auto`(-0.79) · `apply cb_nf; auto`(-4.13) · `apply cb_red`(-4.23) · `apply cb_compo with (L1 := L); auto`(-4.42) · `unfold red in H'`(-4.43)

## buchberger-theories-ListProps.v · proof#0 — `Definition iw_sup' (x : A) (y : forall z : B x, IW' (j x z)) : IW' (i x) := (w_sup A B x (fun a => pr1 (y a)); (idpath, (fun a => pr2 (y a)))).`  (7 steps)


### step 0 — ❌miss
- **goal(입력 상태)**: `forall (A B : Type) (f : A -> B) (b : B) (xs : list A),
In b (map f xs) -> exists a : A, b = f a /\ In a xs`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A B f b xs; elim xs; simpl in |- *; auto`
- **생성 top5**: `Proof`(-0.36) · `Proof`(-2.27) · `intros`(-3.23) · `intros`(-3.46) · `Defined`(-4.35)

### step 1 — ❌miss
- **goal(입력 상태)**: `False -> exists a : A, b = f a /\ False / forall (a : A) (l : list A),
(In b (map f l) -> exists a0 : A, b = f a0 /\ In a0 l) ->
f a = b \/ In b (map f l) -> exists a0 : A, b = f a0 /\ (a = a0 \/ In a`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros H'; elim H'; auto`
- **생성 top5**: `intros []`(-1.88) · `intros H; elim H`(-2.96) · `contradiction`(-3.13) · `intuition`(-3.15) · `intros H`(-3.65)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a : A) (l : list A),
(In b (map f l) -> exists a0 : A, b = f a0 /\ In a0 l) ->
f a = b \/ In b (map f l) -> exists a0 : A, b = f a0 /\ (a = a0 \/ In a0 l)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros a l H' H'0; elim H'0; [ intros H'1; clear H'0 | intros H'1; clear H'0 ]; auto`
- **생성 top5**: `intros a xs'; elim xs'; simpl in |- *; auto`(-5.07) · `intros x xs'; elim xs'; simpl in |- *; auto`(-5.20) · `intros x xs' H'; elim H'`(-5.44) · `intros x xs' H'; elim H'; auto`(-5.48) · `intros a xs' H'; elim H'; auto`(-5.48)

### step 3 — 🔶topk
- **goal(입력 상태)**: `exists a0 : A, b = f a0 /\ (a = a0 \/ In a0 l) / exists a0 : A, b = f a0 /\ (a = a0 \/ In a0 l)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `exists a; split; auto`
- **생성 top5**: `exists a; auto`(-1.71) · `exists a; split; auto`(-2.07) · `exists a; split; auto`(-2.86) · `exists a; split; auto`(-2.90) · `exists a; auto`(-3.06)

### step 4 — ❌miss
- **goal(입력 상태)**: `exists a0 : A, b = f a0 /\ (a = a0 \/ In a0 l)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `elim H'; [ intros a0 E; elim E; intros H'2 H'3; clear E H' | clear H' ]; auto`
- **생성 top5**: `exists a; split; auto`(-0.91) · `apply H'; auto`(-2.97) · `apply H' in H'1; auto`(-3.53) · `auto`(-3.58) · `elim H'; auto`(-3.69)

### step 5 — ✅top1
- **goal(입력 상태)**: `exists a1 : A, b = f a1 /\ (a = a1 \/ In a1 l)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `exists a0; split; auto`
- **생성 top5**: `exists a0; split; auto`(-0.37) · `exists a0; split`(-3.26) · `exists a0; auto`(-3.74) · `exists a0; split; auto; right; auto`(-4.15) · `exists a0`(-4.17)

## buchberger-theories-ListProps.v · proof#1 — `Definition iw_eta {A B I i j} (l : I) (w : IW I A B i j l) : path_index_iw_label l w # iw_sup I A B i j (iw_label w) (iw_arity l w) = w.`  (3 steps)


### step 0 — ❌miss
- **goal(입력 상태)**: `forall (A B : Type) (f : A -> B) (l1 l2 : list A),
map f (l1 ++ l2) = map f l1 ++ map f l2`
- **retrieval 증명 top1**: `Definition iw_sup' (x : A) (y : forall z : B x, IW' (j x z)) : IW' (i x) := (w_sup A B x (`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A B f l1; elim l1; simpl in |- *; auto with datatypes`
- **생성 top5**: `Proof`(-1.25) · `intros`(-2.46) · `intros A B f l1 l2`(-3.07) · `intros`(-3.92) · `intros A B f l1 l2; elim l1; simpl in |- *; auto`(-4.22)

### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (a : A) (l : list A),
(forall l2 : list A, map f (l ++ l2) = map f l ++ map f l2) ->
forall l2 : list A, f a :: map f (l ++ l2) = f a :: map f l ++ map f l2`
- **retrieval 증명 top1**: `Definition iw_sup' (x : A) (y : forall z : B x, IW' (j x z)) : IW' (i x) := (w_sup A B x (`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros a l H' l2; rewrite H'; auto`
- **생성 top5**: `intros a l IH l2`(-3.96) · `intros a l H' l2; simpl in |- *`(-4.63) · `intros a l IH l2; simpl in |- *`(-4.90) · `intros a l IH l2; rewrite IH; auto`(-5.02) · `intros a l H l2`(-5.03)

## buchberger-theories-ListProps.v · proof#2 — `Definition iw_to_hfiber_index {A B I i j} (l : I) : IW I A B i j l -> hfiber i l.`  (5 steps)

- step 0: get_recs 실패 ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-ListProps.v · proof#3 — `Definition IW'_ind (P : forall i, IW' i -> Type) (S : forall x y, (forall c, P _ (y c)) -> P _ (iw_sup' x y)) : forall x w, P x w.`  (6 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-ListProps.v · proof#4 — `Definition path_index_iw_label {A B I i j} (l : I) (w : IW I A B i j l) : i (iw_label w) = l.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Monomials.v · proof#0 — `Class NaturalsToSemiRing := naturals_to_semiring: ∀ B `{Mult B} `{Plus B} `{One B} `{Zero B}, A → B.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Monomials.v · proof#1 — `Program Definition natural_initial_arrow: InitialArrow (semirings.object A) := λ y u, match u return A → y u with tt => naturals_to_semiring (y tt) en`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Monomials.v · proof#2 — `Lemma natural_initial (same_morphism : ∀ `{SemiRing B} {h : A → B} `{!SemiRing_Morphism h}, naturals_to_semiring B = h) : Initial (semirings.object A)`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Monomials.v · proof#3 — `Global Instance: FullPseudoSemiRingOrder nat_le nat_lt.`  (7 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Monomials.v · proof#4 — `#[global] Instance: Params (@nat_distance) 4 := {}.`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Monomials.v · proof#5 — `Class NatDistance N `{Equiv N} `{Plus N} := nat_distance_sig : ∀ x y : N, { z : N | x + z = y } + { z : N | y + z = x }.`  (6 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Monomials.v · proof#6 — `Definition nat_distance `{nd : NatDistance N} (x y : N) := match nat_distance_sig x y with | inl (n↾_) => n | inr (n↾_) => n end.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Monomials.v · proof#7 — `Infix "^" := pow : mc_scope.`  (6 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-OpenIndGoodRel.v · proof#0 — `Notation "a $== b" := (GpdHom a b).`  (8 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-POrder.v · proof#0 — `Lemma nonpos_plus_compat x y : x ≤ 0 → y ≤ 0 → x + y ≤ 0.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-POrder.v · proof#1 — `Instance nonneg_plus_compat (x y : R) : PropHolds (0 ≤ x) → PropHolds (0 ≤ y) → PropHolds (0 ≤ x + y).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-POrder.v · proof#2 — `Lemma decompose_le {x y} : x ≤ y → ∃ z, 0 ≤ z ∧ y = x + z.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-POrder.v · proof#3 — `Lemma compose_le x y z : 0 ≤ z → y = x + z → x ≤ y.`  (3 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-POrder.v · proof#4 — `Lemma ge_1_mult_le_compat_r x y z : 1 ≤ z → 0 ≤ y → x ≤ y → x ≤ y * z.`  (2 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-POrder.v · proof#5 — `Lemma ge_1_mult_le_compat_l x y z : 1 ≤ z → 0 ≤ y → x ≤ y → x ≤ z * y.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-POrder.v · proof#6 — `Lemma flip_nonpos_mult_l x y z : z ≤ 0 → x ≤ y → z * y ≤ z * x.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-POrder.v · proof#7 — `Lemma flip_nonpos_mult_r x y z : z ≤ 0 → x ≤ y → y * z ≤ x * z.`  (3 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcomb.v · proof#0 — `Definition gpd_rev_rev {A} `{Is1Gpd A} {a0 a1 : A} (g : a0 $== a1) : (g^$)^$ $== g.`  (9 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcomb.v · proof#1 — `Definition gpd_1functor_V {A B} `{Is1Gpd A, Is1Gpd B} (F : A -> B) `{!Is0Functor F, !Is1Functor F} {a0 a1 : A} (f : a0 $== a1) : fmap F f^$ $== (fmap `  (12 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcomb.v · proof#2 — `Definition gpd_strong_V_hh {A} `{Is1Gpd A, !HasMorExt A} {a b c : A} (f : b $-> c) (g : a $-> b) : f^$ $o (f $o g) = g := path_hom (gpd_V_hh f g).`  (16 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcomb.v · proof#3 — `Definition gpd_strong_h_Vh {A} `{Is1Gpd A, !HasMorExt A} {a b c : A} (f : c $-> b) (g : a $-> b) : f $o (f^$ $o g) = g := path_hom (gpd_h_Vh f g).`  (10 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcomb.v · proof#4 — `Definition gpd_strong_hh_V {A} `{Is1Gpd A, !HasMorExt A} {a b c : A} (f : b $-> c) (g : a $-> b) : (f $o g) $o g^$ = f := path_hom (gpd_hh_V f g).`  (7 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcomb.v · proof#5 — `Definition gpd_strong_hV_h {A} `{Is1Gpd A, !HasMorExt A} {a b c : A} (f : b $-> c) (g : b $-> a) : (f $o g^$) $o g = f := path_hom (gpd_hV_h f g).`  (7 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcomb.v · proof#6 — `Definition gpd_strong_rev_pp {A} `{Is1Gpd A, !HasMorExt A} {a b c : A} (f : b $-> c) (g : a $-> b) : (f $o g)^$ = g^$ $o f^$ := path_hom (gpd_rev_pp f`  (16 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcomb.v · proof#7 — `Definition gpd_strong_rev_1 {A} `{Is1Gpd A, !HasMorExt A} {a : A} : (Id a)^$ = Id a := path_hom gpd_rev_1.`  (11 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcrit.v · proof#0 — `Definition compose_cate {A} `{HasEquivs A} {a b c : A} (g : b $<~> c) (f : a $<~> b) : a $<~> c := Build_CatEquiv (g $o f).`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcrit.v · proof#1 — `Notation "g $oE f" := (compose_cate g f).`  (34 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcrit.v · proof#2 — `Definition compose_cate_fun {A} `{HasEquivs A} {a b c : A} (g : b $<~> c) (f : a $<~> b) : cate_fun (g $oE f) $== g $o f.`  (28 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcrit.v · proof#3 — `Definition compose_cate_funinv {A} `{HasEquivs A} {a b c : A} (g : b $<~> c) (f : a $<~> b) : g $o f $== cate_fun (g $oE f).`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcrit.v · proof#4 — `Definition id_cate_fun {A} `{HasEquivs A} (a : A) : cate_fun (id_cate a) $== Id a.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcrit.v · proof#5 — `Definition compose_cate_assoc {A} `{HasEquivs A} {a b c d : A} (f : a $<~> b) (g : b $<~> c) (h : c $<~> d) : cate_fun ((h $oE g) $oE f) $== cate_fun `  (10 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcrit.v · proof#6 — `Definition compose_cate_idl {A} `{HasEquivs A} {a b : A} (f : a $<~> b) : cate_fun (id_cate b $oE f) $== cate_fun f.`  (20 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcrit.v · proof#7 — `Definition compose_cate_idr {A} `{HasEquivs A} {a b : A} (f : a $<~> b) : cate_fun (f $oE id_cate a) $== cate_fun f.`  (6 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Peq.v · proof#0 — `Lemma gt_1_ge_1_mult_compat x y : 1 < x → 1 ≤ y → 1 < x * y.`  (13 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Peq.v · proof#1 — `Lemma ge_1_gt_1_mult_compat x y : 1 ≤ x → 1 < y → 1 < x * y.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Peq.v · proof#2 — `Lemma not_le_1_0 : ¬1 ≤ 0.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Peq.v · proof#3 — `Lemma not_le_2_0 : ¬2 ≤ 0.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Peq.v · proof#4 — `Instance dec_pseudo_srorder: PseudoSemiRingOrder (<).`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Peq.v · proof#5 — `Instance dec_full_pseudo_srorder: FullPseudoSemiRingOrder (≤) (<).`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Peq.v · proof#6 — `Lemma preserving_preserves_nonneg : (∀ x, 0 ≤ x → 0 ≤ f x) → OrderPreserving f.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Peq.v · proof#7 — `Instance preserves_nonneg `{!OrderPreserving f} x : PropHolds (0 ≤ x) → PropHolds (0 ≤ f x).`  (7 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pminus.v · proof#0 — `Lemma flip_nonpos_minus (x y : R) : y - x ≤ 0 ↔ y ≤ x.`  (29 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pminus.v · proof#1 — `Lemma nonneg_minus_compat_back (x y z : R) : 0 ≤ z → x ≤ y - z → x ≤ y.`  (25 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pminus.v · proof#2 — `Lemma between_nonneg (x : R) : 0 ≤ x → -x ≤ x.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pminus.v · proof#3 — `Lemma flip_lt_negate x y : -y < -x ↔ x < y.`  (8 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pminus.v · proof#4 — `Lemma flip_pos_negate x : 0 < x ↔ -x < 0.`  (11 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pminus.v · proof#5 — `Lemma flip_neg_negate x : x < 0 ↔ 0 < -x.`  (18 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pminus.v · proof#6 — `Lemma flip_lt_minus_r (x y z : R) : z < y - x ↔ z + x < y.`  (57 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pminus.v · proof#7 — `Lemma flip_lt_minus_l (x y z : R) : y - x < z ↔ y < z + x.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmult.v · proof#0 — `Definition cate_inv {A} `{HasEquivs A} {a b : A} (f : a $<~> b) : b $<~> a.`  (9 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmult.v · proof#1 — `Notation "f ^-1$" := (cate_inv f).`  (12 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmult.v · proof#2 — `Definition cate_issect {A} `{HasEquivs A} {a b} (f : a $<~> b) : f^-1$ $o f $== Id a.`  (33 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmult.v · proof#3 — `Definition cate_isretr {A} `{HasEquivs A} {a b} (f : a $<~> b) : f $o f^-1$ $== Id b.`  (15 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmult.v · proof#4 — `Definition cate_inverse_sect {A} `{HasEquivs A} {a b} (f : a $<~> b) (g : b $-> a) (p : f $o g $== Id b) : cate_fun f^-1$ $== g.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmult.v · proof#5 — `Definition cate_inverse_retr {A} `{HasEquivs A} {a b} (f : a $<~> b) (g : b $-> a) (p : g $o f $== Id a) : cate_fun f^-1$ $== g.`  (8 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmult.v · proof#6 — `Definition cate_inv_adjointify {A} `{HasEquivs A} {a b : A} (f : a $-> b) (g : b $-> a) (r : f $o g $== Id b) (s : g $o f $== Id a) : cate_fun (cate_a`  (16 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmult.v · proof#7 — `Global Instance catie_id {A} `{HasEquivs A} (a : A) : CatIsEquiv (Id a) := catie_adjointify (Id a) (Id a) (cat_idl (Id a)) (cat_idl (Id a)).`  (28 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmults.v · proof#0 — `Lemma same_morphism: naturals_to_semiring N R ∘ f⁻¹ = h.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmults.v · proof#1 — `Program Instance retract_is_nat: Naturals SR (U:=retract_is_nat_to_sr).`  (19 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmults.v · proof#2 — `Lemma induction (P: Z → Prop) `{!Proper ((=) ==> iff) P}: P 0 → (∀ n, 0 ≤ n → P n → P (1 + n)) → (∀ n, n ≤ 0 → P n → P (n - 1)) → ∀ n, P n.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmults.v · proof#3 — `Lemma induction (P: N → Prop) `{!Proper ((=) ==> iff) P}: P 0 → (∀ n, P n → P (1 + n)) → ∀ n, P n.`  (23 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmults.v · proof#4 — `Lemma from_nat_stmt: ∀ (s: Statement varieties.semirings.theory) (w : Vars varieties.semirings.theory (varieties.semirings.object N) nat), (∀ v: Vars `  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmults.v · proof#5 — `Instance nat_nontrivial: PropHolds ((1:N) ≠ 0).`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmults.v · proof#6 — `Instance nat_nontrivial_apart `{Apart N} `{!TrivialApart N} : PropHolds ((1:N) ≶ 0).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmults.v · proof#7 — `Lemma zero_sum (x y : N) : x + y = 0 → x = 0 ∧ y = 0.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pplus.v · proof#0 — `Lemma nat_induction (P : nat → Prop) : P 0 → (∀ n, P n → P (1 + n)) → ∀ n, P n.`  (31 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pplus.v · proof#1 — `#[global] Instance nat_le: Le nat := Peano.le.`  (19 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pplus.v · proof#2 — `#[global] Instance nat_lt `{Naturals N} : Lt N | 10 := dec_lt.`  (51 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pplus.v · proof#3 — `#[global] Instance nat_lt: Lt nat := Peano.lt.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pplus.v · proof#4 — `#[global] Instance nat_le_dec : `{Decision (x ≤ y)} := le_dec.`  (22 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pplus.v · proof#5 — `#[global] Instance nat_cut_minus: CutMinus nat := minus.`  (30 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pplus.v · proof#6 — `CoInductive Stream_eq_coind (s1 s2: ∞A) : Prop := stream_eq_coind : hd s1 = hd s2 → Stream_eq_coind (tl s1) (tl s2) → Stream_eq_coind s1 s2.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pplus.v · proof#7 — `Global Instance stream_eq: Equiv (∞A) := Stream_eq_coind.`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduce.v · proof#0 — `Lemma InFinEnumC_map : forall (X Y:MetricSpace) (f:X --> Y) a l, InFinEnumC a l -> InFinEnumC (f a) (map f l).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduce.v · proof#1 — `Definition FinEnum_map_modulus (z:Qpos) (muf : Qpos -> QposInf) (e:Qpos) := match (muf e) with | QposInfinity => z | Qpos2QposInf d => d end.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduce.v · proof#2 — `Lemma FinEnum_map_uc : forall z X Y (f:X --> Y), is_UniformlyContinuousFunction (map f:FinEnum X -> FinEnum Y) (FinEnum_map_modulus z (mu f)).`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduce.v · proof#3 — `Definition FinEnum_map z (X Y : MetricSpace) (f:X --> Y) : FinEnum X --> FinEnum Y := Build_UniformlyContinuousFunction (FinEnum_map_uc z f).`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduce.v · proof#4 — `Lemma FinEnum_map_Cunit : forall X (s1 s2:FinEnum X) (e:Qpos), ball (proj1_sig e) s1 s2 <-> ball (proj1_sig e) (map Cunit s1:FinEnum (Complete X)) (ma`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduce.v · proof#5 — `Definition CompleteSubset := forall (f:Complete X), (forall e, P (approximate f e)) -> {y:X | P y & msp_eq (Cunit y) f}.`  (21 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduce.v · proof#6 — `Definition ExtSubset := forall x y, (msp_eq x y) -> (P x <-> P y).`  (19 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduce.v · proof#7 — `Definition TotallyBoundedSubset := forall (e:Qpos), {l : list X | forall y, In y l -> P y & forall x, P x -> exists y, In y l /\ ball (proj1_sig e) x `  (17 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduceplus.v · proof#0 — `Lemma CompactTotallyBoundedA : forall s e y, In y (CompactTotalBound s e) -> inCompact y s.`  (13 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduceplus.v · proof#1 — `Lemma CompactTotallyBoundedB : forall s e x, (inCompact x s) -> exists y, In y (CompactTotalBound s e) /\ ball (proj1_sig e) x y.`  (11 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduceplus.v · proof#2 — `Lemma CompactTotallyBounded : forall s, TotallyBoundedSubset _ (fun z => inCompact z s).`  (8 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduceplus.v · proof#3 — `Lemma CompactAsBishopCompact : forall s, CompactSubset _ (fun z => inCompact z s).`  (11 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduceplus.v · proof#4 — `Definition BishopCompactAsCompact_raw (P:Complete X->Prop) (HP:CompactSubset _ P) (e:QposInf) : (FinEnum X) := match e with |QposInfinity => nil |Qpos`  (16 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduceplus.v · proof#5 — `Lemma BishopCompactAsCompact_prf : forall P (HP:CompactSubset _ P), is_RegularFunction (@ball (FinEnum X)) (BishopCompactAsCompact_raw HP).`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduceplus.v · proof#6 — `Definition BishopCompactAsCompact (P:Complete X->Prop) (HP:CompactSubset _ P) : Compact X := Build_RegularFunction (BishopCompactAsCompact_prf HP).`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduceplus.v · proof#7 — `Lemma BishopCompact_Compact_BishopCompact1 : forall (P:Complete X->Prop) (HP:CompactSubset _ P) x, P x -> inCompact x (BishopCompactAsCompact HP).`  (134 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preducestar.v · proof#0 — `Global Instance is1cat_is1cat_strong (A : Type) `{Is1Cat_Strong A} : Is1Cat A | 1000.`  (7 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preducestar.v · proof#1 — `Definition IsInitial {A : Type} `{Is1Cat A} (x : A) := forall (y : A), {f : x $-> y & forall g, f $== g}.`  (2 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preducestar.v · proof#2 — `Definition mor_initial {A : Type} `{Is1Cat A} (x y : A) {h : IsInitial x} : x $-> y := (h y).1.`  (30 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preducestar.v · proof#3 — `Definition mor_initial_unique {A : Type} `{Is1Cat A} (x y : A) {h : IsInitial x} (f : x $-> y) : mor_initial x y $== f := (h y).2 f.`  (30 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preducestar.v · proof#4 — `Definition IsTerminal {A : Type} `{Is1Cat A} (y : A) := forall (x : A), {f : x $-> y & forall g, f $== g}.`  (64 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preducestar.v · proof#5 — `Definition mor_terminal {A : Type} `{Is1Cat A} (x y : A) {h : IsTerminal y} : x $-> y := (h x).1.`  (7 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preducestar.v · proof#6 — `Definition mor_terminal_unique {A : Type} `{Is1Cat A} (x y : A) {h : IsTerminal y} (f : x $-> y) : mor_terminal x y $== f := (h x).2 f.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preducestar.v · proof#7 — `Class HasMorExt (A : Type) `{Is1Cat A} := { isequiv_Htpy_path : forall a b f g, IsEquiv (@GpdHom_path (a $-> b) _ _ _ f g) }.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspminus.v · proof#0 — `Lemma FinSubset_ball_weak_le : forall (e1 e2:Q) x l, e1 <= e2 -> FinSubset_ball e1 x l -> FinSubset_ball e2 x l.`  (17 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspminus.v · proof#1 — `Lemma FinSubset_ball_nonneg : forall (e:Q) x l, FinSubset_ball e x l -> 0 <= e.`  (16 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspminus.v · proof#2 — `Lemma FinSubset_ball_triangle_l : forall e1 e2 x1 x2 l, (ball e1 x1 x2) -> FinSubset_ball e2 x2 l -> FinSubset_ball (e1 + e2) x1 l.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspminus.v · proof#3 — `Lemma FinSubset_ball_app_l : forall e x l1 l2, FinSubset_ball e x l1 -> FinSubset_ball e x (l1 ++ l2).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspminus.v · proof#4 — `Lemma FinSubset_ball_app_r : forall e x l1 l2, FinSubset_ball e x l2 -> FinSubset_ball e x (l1 ++ l2).`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspminus.v · proof#5 — `Lemma FinSubset_ball_app_orC : forall e x l1 l2, FinSubset_ball e x (l1 ++ l2) -> orC (FinSubset_ball e x l1) (FinSubset_ball e x l2).`  (10 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspminus.v · proof#6 — `Definition FinEnum_eq (a b:list X) : Prop := forall x, InFinEnumC x a <-> InFinEnumC x b.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspminus.v · proof#7 — `Definition FinEnum_ball (e:Q) (x y:list X) := hausdorffBall X e (fun a => InFinEnumC a x) (fun a => InFinEnumC a y).`  (9 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspoly.v · proof#0 — `#[export] Instance isFaithful_idmap {A : Type} `{Is1Cat A}: Faithful idmap.`  (11 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspoly.v · proof#1 — `Global Instance is01functor_const `{IsGraph A} `{Is01Cat B} (x : B) : Is0Functor (fun _ : A => x).`  (9 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspoly.v · proof#2 — `Global Instance is1functor_const `{Is1Cat A} `{Is1Cat B} (x : B) : Is1Functor (fun _ : A => x).`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspoly.v · proof#3 — `Global Instance is0functor_compose {A B C : Type} `{IsGraph A, IsGraph B, IsGraph C} (F : A -> B) (G : B -> C) `{!Is0Functor F, !Is0Functor G} : Is0Fu`  (27 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspoly.v · proof#4 — `Global Instance is1functor_compose {A B C : Type} `{Is1Cat A, Is1Cat B, Is1Cat C} (F : A -> B) `{!Is0Functor F, !Is1Functor F} (G : B -> C) `{!Is0Func`  (7 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspoly.v · proof#5 — `Class Is1Gpd (A : Type) `{Is1Cat A, !Is0Gpd A} := { gpd_issect : forall {a b : A} (f : a $-> b), f^$ $o f $== Id a ; gpd_isretr : forall {a b : A} (f `  (79 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspoly.v · proof#6 — `Definition gpd_V_hh {A} `{Is1Gpd A} {a b c : A} (f : b $-> c) (g : a $-> b) : f^$ $o (f $o g) $== g := (cat_assoc _ _ _)^$ $@ (gpd_issect f $@R g) $@ `  (9 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspoly.v · proof#7 — `Definition gpd_h_Vh {A} `{Is1Gpd A} {a b c : A} (f : c $-> b) (g : a $-> b) : f $o (f^$ $o g) $== g := (cat_assoc _ _ _)^$ $@ (gpd_isretr f $@R g) $@ `  (22 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Relation_Operators_compat.v · proof#0 — `Inductive Laws: EqEntailment sig → Prop := |e_plus_assoc: Laws (x + (y + z) === (x + y) + z) |e_plus_comm: Laws (x + y === y + x) |e_plus_0_l: Laws (0`  (14 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Relation_Operators_compat.v · proof#1 — `Definition theory: EquationalTheory := Build_EquationalTheory sig Laws.`  (17 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Relation_Operators_compat.v · proof#2 — `Instance implementation: AlgebraOps sig (λ _, A) := λ o, match o with plus => (+) | mult => (.*.) | zero => 0: A | one => 1:A end.`  (14 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Relation_Operators_compat.v · proof#3 — `Lemma laws en (l: Laws en) vars: eval_stmt sig vars en.`  (38 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Relation_Operators_compat.v · proof#4 — `Global Instance variety: InVariety theory (λ _, A).`  (57 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Relation_Operators_compat.v · proof#5 — `Definition Object := varieties.Object theory.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Relation_Operators_compat.v · proof#6 — `Definition object: Object := varieties.object theory (λ _, A).`  (16 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Relation_Operators_compat.v · proof#7 — `Lemma mor_from_sr_to_alg `{InVariety theory A} `{InVariety theory B} (f: ∀ u, A u → B u) `{!SemiRing_Morphism (f tt)}: HomoMorphism sig A B f.`  (9 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Term.v · proof#0 — `Lemma pseudo_order_lt_ext x₁ y₁ x₂ y₂ : x₁ < y₁ → x₂ < y₂ ∨ x₁ ≶ x₂ ∨ y₂ ≶ y₁.`  (3 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Term.v · proof#1 — `Lemma ne_total_lt `{!TrivialApart A} x y : x ≠ y → x < y ∨ y < x.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Term.v · proof#2 — `Global Instance lt_trichotomy `{!TrivialApart A} `{∀ x y, Decision (x = y)} : Trichotomy (<).`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Term.v · proof#3 — `Instance strict_po_apart_ne x y : PropHolds (x ≶ y) → PropHolds (x ≠ y).`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Term.v · proof#4 — `Lemma lt_le x y : PropHolds (x < y) → PropHolds (x ≤ y).`  (6 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Term.v · proof#5 — `Lemma not_le_not_lt x y : ¬x ≤ y → ¬x < y.`  (2 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Term.v · proof#6 — `Lemma lt_apart_flip x y : x < y → y ≶ x.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Term.v · proof#7 — `Lemma le_not_lt_flip x y : y ≤ x → ¬x < y.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-WfR0.v · proof#0 — `Definition issig_NatTrans {A B : Type} `{IsGraph A} `{Is1Cat B} (F G : A -> B) {ff : Is0Functor F} {fg : Is0Functor G} : _ <~> NatTrans F G := ltac:(i`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-WfR0.v · proof#1 — `Definition isnat_tr {A B : Type} `{IsGraph A} `{Is1Cat B} {F : A -> B} `{!Is0Functor F} {G : A -> B} `{!Is0Functor G} (alpha : F $=> G) `{!Is1Natural `  (31 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-WfR0.v · proof#2 — `Definition trans_comp {A B : Type} `{Is01Cat B} {F G K : A -> B} (gamma : G $=> K) (alpha : F $=> G) : F $=> K := fun a => gamma a $o alpha a.`  (22 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-WfR0.v · proof#3 — `Definition IW' (x : I) := sig (IsIndexedBy x).`  (13 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-WfR0.v · proof#4 — `Definition trans_prewhisker {A B : Type} {C : B -> Type} {F G : forall x, C x} `{Is01Cat B} `{!forall x, IsGraph (C x)} `{!forall x, Is01Cat (C x)} (g`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-moreCoefStructure.v · proof#0 — `Class EuclidSpec A (d : DivEuclid A) (m : ModEuclid A) `{Equiv A} `{Le A} `{Lt A} `{Zero A} `{Plus A} `{Mult A} := { div_proper : Proper ((=) ==> (=) `  (2 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-moreCoefStructure.v · proof#1 — `Class CutMinus A := cut_minus : A → A → A.`  (2 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-moreCoefStructure.v · proof#2 — `Infix "∸" := cut_minus (at level 50, left associativity) : mc_scope.`  (2 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-moreCoefStructure.v · proof#3 — `Notation "(∸)" := cut_minus (only parsing) : mc_scope.`  (3 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-moreCoefStructure.v · proof#4 — `Notation "( x ∸)" := (cut_minus x) (only parsing) : mc_scope.`  (2 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-moreCoefStructure.v · proof#5 — `Notation "(∸ y )" := (λ x, x ∸ y) (only parsing) : mc_scope.`  (3 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-moreCoefStructure.v · proof#6 — `Class CutMinusSpec A (cm : CutMinus A) `{Equiv A} `{Zero A} `{Plus A} `{Le A} := { cut_minus_le : ∀ x y, y ≤ x → x ∸ y + y = x ; cut_minus_0 : ∀ x y, `  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-moreCoefStructure.v · proof#7 — `Lemma le_flip `{Le A} `{!TotalRelation (≤)} x y : ¬y ≤ x → x ≤ y.`  (9 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Alphabet.v · proof#0 — `Ltac equiv_via mid := apply @equiv_composeR' with (B := mid).`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Alphabet.v · proof#1 — `Ltac decomposing_intros := let x := fresh in intros x; cbn in x; try match type of x with | ?a = ?b => fail 1 (** Don't destruct paths *) | forall y:?`  (12 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Alphabet.v · proof#2 — `Lemma sn_subst : forall T M, sn (subst T M) -> sn M.`  (13 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Alphabet.v · proof#3 — `Implicit Types i k m n p : nat.`  (7 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Alphabet.v · proof#4 — `Implicit Type s : sort.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Alphabet.v · proof#5 — `Implicit Types A B M N T t u v : term.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Alphabet.v · proof#6 — `Ltac decomposing_intros_with_paths := let x := fresh in intros x; cbn in x; multimatch type of x with | _ => try match type of x with | (** Don't dest`  (8 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Alphabet.v · proof#7 — `Ltac make_equiv_contr_basedpaths := simple notypeclasses refine (equiv_adjointify _ _ _ _); (** [solve [ unshelve TAC ]] ensures that [TAC] succeeds w`  (8 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter.v · proof#0 — `Definition equiv_path_sigma `(P : A -> Type) (u v : sig P) : {p : u.1 = v.1 & p # u.2 = v.2} <~> (u = v) := Build_Equiv _ _ (path_sigma_uncurried P u `  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter.v · proof#1 — `Global Instance isequiv_path_sigma_contra `{P : A -> Type} {u v : sig P} : IsEquiv (path_sigma_uncurried_contra P u v) | 0.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter.v · proof#2 — `Definition pr1_path_1 {A : Type} {P : A -> Type} (u : sig P) : (idpath u) ..1 = idpath (u .1) := 1.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter.v · proof#3 — `Definition ap_path_sigma {A B} (P : A -> Type) (F : forall a : A, P a -> B) {x x' : A} {y : P x} {y' : P x'} (p : x = x') (q : p # y = y') : ap (fun w`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter.v · proof#4 — `Definition eta_sigma `{P : A -> Type} (u : sig P) : (u.1; u.2) = u := 1.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter.v · proof#5 — `Definition eta3_sigma `{P : forall (a : A) (b : B a) (c : C a b), Type} (u : sig (fun a => sig (fun b => sig (P a b)))) : (u.1; u.2.1; u.2.2.1; u.2.2.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter.v · proof#6 — `Definition pr1_path `{P : A -> Type} {u v : sig P} (p : u = v) : u.1 = v.1 := ap pr1 p.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter.v · proof#7 — `Definition pr2_path `{P : A -> Type} {u v : sig P} (p : u = v) : p..1 # u.2 = v.2 := (transport_compose P pr1 p u.2)^ @ (@apD {x:A & P x} _ pr2 _ _ p)`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_complete.v · proof#0 — `Lemma eqb_true_b : forall b : bool, eqb true b = b.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_complete.v · proof#1 — `Lemma eqb_b_true : forall b : bool, eqb b true = b.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_complete.v · proof#2 — `Lemma eqb_b_false : forall b : bool, eqb b false = negb b.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_complete.v · proof#3 — `Lemma eqb_false_b : forall b : bool, eqb false b = negb b.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_complete.v · proof#4 — `Lemma eqb_com : forall b1 b2 : bool, eqb b1 b2 = eqb b2 b1.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_complete.v · proof#5 — `Lemma orb_false_2 : forall b b' : bool, b || b' = false -> b' = false.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_complete.v · proof#6 — `Lemma orb_false_1 : forall b b' : bool, b || b' = false -> b = false.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_complete.v · proof#7 — `Definition boolOpFun (n : boolOp) := match n with | ANd => andb | Or => orb | Impl => implb | normalize.Eq => eqb end.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_correct.v · proof#0 — `Definition equiv_sigma_prod_prod {X Y : Type} (P : X -> Type) (Q : Y -> Type) : {z : X * Y & (P (fst z)) * (Q (snd z))} <~> (sig P) * (sig Q) := ltac:`  (17 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_correct.v · proof#1 — `Definition equiv_sigma_symm `(P : A -> B -> Type) : {a : A & {b : B & P a b}} <~> {b : B & {a : A & P a b}}.`  (28 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_correct.v · proof#2 — `Definition equiv_sigma_symm' {A : Type} `(P : A -> Type) `(Q : A -> Type) : { ap : { a : A & P a } & Q ap.1 } <~> { aq : { a : A & Q a } & P aq.1 }.`  (33 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_correct.v · proof#3 — `Definition equiv_sigma_symm0 (A B : Type) : {a : A & B} <~> {b : B & A}.`  (8 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_correct.v · proof#4 — `Global Instance isequiv_sig_ind `{P : A -> Type} (Q : sig P -> Type) : IsEquiv (sig_ind Q) | 0 := Build_IsEquiv _ _ (sig_ind Q) (fun f x y => f (x;y))`  (7 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Main.v · proof#0 — `Lemma implb_elim : forall b1 b2 : bool, implb b1 b2 = negb (b1 && negb b2).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Main.v · proof#1 — `Lemma varTripletTriplet1 : forall (p q r : rZ) (b : rBoolOp) (L : list triplet), In (Triplet b p q r) L -> In p (varTriplets L).`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Main.v · proof#2 — `Theorem eqStateInvInv : forall (S : State) (p q : rZ), eqStateRz S (rZComp p) (rZComp q) -> eqStateRz S p q.`  (18 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_classes.v · proof#0 — `Variant int : Type0 := Pos (d:uint) | Neg (d:uint).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_classes.v · proof#1 — `Variant hexadecimal : Type0 := | Hexadecimal (i:int) (f:uint) | HexadecimalExp (i:int) (f:uint) (e:Decimal.int).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_classes.v · proof#2 — `Fixpoint nb_digits d := match d with | Nil => O | D0 d | D1 d | D2 d | D3 d | D4 d | D5 d | D6 d | D7 d | D8 d | D9 d | Da d | Db d | Dc d | Dd d | De`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_classes.v · proof#3 — `Fixpoint nzhead d := match d with | D0 d => nzhead d | _ => d end.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_classes.v · proof#4 — `Definition unorm d := match nzhead d with | Nil => zero | d => d end.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_classes.v · proof#5 — `Definition norm d := match d with | Pos d => Pos (unorm d) | Neg d => match nzhead d with | Nil => Pos zero | d => Neg d end end.`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_classes.v · proof#6 — `Definition opp (d:int) := match d with | Pos d => Neg d | Neg d => Pos d end.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_complete.v · proof#0 — `Definition tail_mul n m := tail_addmul O n m.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_complete.v · proof#1 — `Fixpoint of_uint_acc (d:Decimal.uint)(acc:nat) := match d with | Decimal.Nil => acc | Decimal.D0 d => of_uint_acc d (tail_mul ten acc) | Decimal.D1 d `  (6 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_complete.v · proof#2 — `Definition of_uint (d:Decimal.uint) := of_uint_acc d O.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_complete.v · proof#3 — `Fixpoint of_hex_uint_acc (d:Hexadecimal.uint)(acc:nat) := match d with | Hexadecimal.Nil => acc | Hexadecimal.D0 d => of_hex_uint_acc d (tail_mul sixt`  (16 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_complete.v · proof#4 — `Definition of_num_uint (d:Numeral.uint) := match d with | Numeral.UIntDec d => of_uint d | Numeral.UIntHex d => of_hex_uint d end.`  (28 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_complete.v · proof#5 — `Fixpoint to_little_uint n acc := match n with | O => acc | S n => to_little_uint n (Decimal.Little.succ acc) end.`  (7 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_complete.v · proof#6 — `Definition trunc_index_inc'_succ (n : nat) (k : trunc_index) : trunc_index_inc' k.+1 n = (trunc_index_inc' k n).+1.`  (6 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_complete.v · proof#7 — `Definition nat_to_trunc_index (n : nat) : trunc_index := (trunc_index_inc minus_two n).+2.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_safe.v · proof#0 — `Global Instance decidable_arrow {A B : Type} `{Decidable A} `{Decidable B} : Decidable (A -> B).`  (9 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_safe.v · proof#1 — `Definition unpack_sigma `{P : A -> Type} (Q : sig P -> Type) (u : sig P) : Q (u.1; u.2) -> Q u := idmap.`  (10 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_safe.v · proof#2 — `Definition path_sigma_uncurried_contra {A : Type} (P : A -> Type) (u v : sig P) (pq : {p : u.1 = v.1 & u.2 = p^ # v.2}) : u = v := (path_sigma_uncurri`  (13 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_safe.v · proof#3 — `Definition path_sigma' {A : Type} (P : A -> Type) {x x' : A} {y : P x} {y' : P x'} (p : x = x') (q : p # y = y') : (x;y) = (x';y') := path_sigma P (x;`  (10 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_safe.v · proof#4 — `Definition eta_path_sigma_uncurried `{P : A -> Type} {u v : sig P} (p : u = v) : path_sigma_uncurried _ _ _ (p..1; p..2) = p.`  (11 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_safe.v · proof#5 — `Definition eta_path_sigma `{P : A -> Type} {u v : sig P} (p : u = v) : path_sigma _ _ _ (p..1) (p..2) = p := eta_path_sigma_uncurried p.`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Archi.v · proof#0 — `Theorem implies_true : forall P, P ⟹ ⊤.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Archi.v · proof#1 — `Theorem Intersection_Union {A : Type} p q : Same_set A (Intersection A p q) (Complement A (Union A (Complement A p) (Complement A q))).`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Archi.v · proof#2 — `Theorem Excluded_Middle {A : Type} p : Same_set A (p ∪ Complement A p) (Full_set A).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Archi.v · proof#3 — `Corollary Complement_Full {A : Type} : Same_set A (Complement A (Full_set A)) (Empty_set A).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Op.v · proof#0 — `Lemma uniq_app_1 : uniq (E ++ F) -> uniq E.`  (11 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Op.v · proof#1 — `Lemma uniq_app_2 : uniq (E ++ F) -> uniq F.`  (11 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Op.v · proof#2 — `Lemma uniq_app_3 : uniq (E ++ F) -> disjoint E F.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Op.v · proof#3 — `Lemma uniq_app_4 : uniq E -> uniq F -> disjoint E F -> uniq (E ++ F).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Op.v · proof#4 — `Lemma uniq_app_iff : uniq (E ++ F) <-> uniq E /\ uniq F /\ disjoint E F.`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Op.v · proof#5 — `Lemma uniq_map_1 : uniq (map f E) -> uniq E.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Op.v · proof#6 — `Lemma uniq_map_2 : uniq E -> uniq (map f E).`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Op.v · proof#7 — `Lemma binds_cons_1 : binds x a ((y, b) :: E) -> (x = y /\ a = b) \/ binds x a E.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Stacklayout.v · proof#0 — `Ltac check_hyp H := match H with _ => idtac end.`  (38 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Stacklayout.v · proof#1 — `Ltac check_equal H1 H2 := match H1 with H2 => idtac end.`  (20 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Stacklayout.v · proof#2 — `Ltac hdes := repeat match goal with | H : ?P |- _ => hdesF P; hdesHP H P end; unfold _HID_ in *.`  (20 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-arm-Archi.v · proof#0 — `Definition commutes (f : S -> S -> S) : Prop := forall x y : S, f x y [=] f y x.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-arm-Archi.v · proof#1 — `Definition CSetoid_un_op := CSetoid_fun S S.`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-arm-Archi.v · proof#2 — `Lemma id_pres_eq : un_op_wd (fun x : S => x).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-arm-Archi.v · proof#3 — `Definition id_un_op := Build_CSetoid_un_op (fun x : S => x) id_strext.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-arm-Stacklayout.v · proof#0 — `Theorem eq_dec_is_path_collaps : forall A : Type, DecidableEq A -> PathCollapsible A.`  (29 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-arm-Stacklayout.v · proof#1 — `Lemma loop_eq : forall A: Type, forall x y: A, forall p: x = y, eq_refl = (p^) @ p.`  (14 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-arm-Stacklayout.v · proof#2 — `Lemma loop_eq' : forall A: Type, forall x y: A, forall p: x = y, eq_refl = p @ (p^).`  (11 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=50371): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=50371): Failed to establish a new connection: [Errno 111] Connection refused"))

