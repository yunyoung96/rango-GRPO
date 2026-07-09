# Oracle-prefix teacher-forcing ablation — `rango` · 조건 both (normal retrieval)

> 각 target×prefix에서 oracle prefix(gold) 상태 → retrieval+생성 → gold와 비교.

> exact-match(정규화 문자열)은 **하한**(다른 유효 tactic 미인정). nbest=8


---
# Summary

- 총 (target,prefix) 스텝: **12**
- **top-1 exact-match (A)**: 0/12 = **0.0%**
- **top-8 exact-match**: 5/12 = **41.7%**
- **[B gold-lemma] top-1**: 0/12 = **0.0%**  (vs A 0.0%, Δ=+0.0%)
- **[B gold-lemma] top-8**: 4/12 = **33.3%**

## prefix 위치별 top-1 (0..9, 10=10+)

| pos | top1 | n | rate |
|---|---|---|---|
| 1 | 0 | 7 | 0.0% |
| 2 | 0 | 4 | 0.0% |
| 3 | 0 | 1 | 0.0% |

## buchberger-theories-Bar.v · proof#0 — `Definition iwpath_sup_refl (x : A) (a : forall c : B x, IW I A B i j (j x c)) : iwpath_sup (x; (a, a)) (apD10 1) = idpath.`  (3 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (A : Type) (P : Pred A) (xs bs : list A),
ExistsL A P bs -> ExistsL A P (xs ++ bs)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A P xs; elim xs; simpl in |- *; auto`
- **생성 top5**: `intros`(-0.92) · `intros`(-2.68) · `intros`(-3.40) · `induction xs`(-3.68) · `reflexivity`(-4.09)

## buchberger-theories-Bar.v · proof#1 — `Definition IWPath_ind_refl : forall l a, P (l ; (a, a)) idpath.`  (4 steps)


### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (A : Type) (P : Pred A) (xs bs cs : list A),
ExistsL A P (xs ++ bs) -> ExistsL A P (xs ++ cs ++ bs)`
- **retrieval 증명 top1**: `Definition iwpath_sup_refl (x : A) (a : forall c : B x, IW I A B i j (j x c)) : iwpath_sup`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A P xs; elim xs; simpl in |- *; auto`
- **생성 top5**: `intros`(-1.95) · `intros`(-2.57) · `intros A P l a`(-3.01) · `intros A P xs bs cs`(-3.72) · `intros A P l a`(-4.31)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a : A) (l : list A),
(forall bs cs : list A, ExistsL A P (l ++ bs) -> ExistsL A P (l ++ cs ++ bs)) ->
forall bs cs : list A,
ExistsL A P (a :: l ++ bs) -> ExistsL A P (a :: l ++ cs ++ bs)`
- **retrieval 증명 top1**: `Definition iwpath_sup_refl (x : A) (a : forall c : B x, IW I A B i j (j x c)) : iwpath_sup`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros a l H' bs cs H'0; inversion H'0; auto`
- **생성 top5**: `intros a l Hrec bs cs H`(-5.71) · `intros a l Hrec l' Hrec'`(-6.90) · `intros a l IHl bs cs H`(-7.10) · `intros a l IHl bs cs E`(-7.12) · `intros x xs' Hrec l bs cs H`(-7.81)

## buchberger-theories-Bar.v · proof#2 — `Definition IWPath_ind_beta_iwpath_sup (x : A') (h : forall y : B' x, IWPath (j' x y)) : IWPath_ind _ (iwpath_sup x h) = S x h (fun c => IWPath_ind _ (`  (3 steps)


### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (A : Type) (R : Rel A) (xs bs : list A),
GoodR A R bs -> GoodR A R (xs ++ bs)`
- **retrieval 증명 top2**: `Definition iwpath_sup_refl (x : A) (a : forall c : B x, IW I A B i j (j x c)) : iwpath_sup` ; `Definition IWPath_ind_refl : forall l a, P (l ; (a, a)) idpath. Proof. intros A P xs; elim`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A R xs; elim xs; simpl in |- *; auto`
- **생성 top5**: `intros`(-2.48) · `intros A R xs; elim xs; simpl in |- *; auto`(-3.14) · `intros A R xs`(-3.78) · `intros; reflexivity`(-4.30) · `intros A R xs; elim xs; simpl in |- *`(-4.42)

## buchberger-theories-Bar.v · proof#3 — `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)) <~> a = b.`  (4 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (A : Type) (R : Rel A) (xs bs cs : list A),
GoodR A R (xs ++ bs) -> GoodR A R (xs ++ cs ++ bs)`
- **retrieval 증명 top2**: `Definition IWPath_ind_beta_iwpath_sup (x : A') (h : forall y : B' x, IWPath (j' x y)) : IW` ; `Definition IWPath_ind_refl : forall l a, P (l ; (a, a)) idpath. Proof. intros A P xs; elim`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A R xs bs cs; elim xs; simpl in |- *; auto`
- **생성 top5**: `intros`(-2.37) · `intros A R xs; elim xs; simpl in |- *; auto`(-3.64) · `intros A R xs bs cs H`(-3.91) · `intros A R xs`(-4.53) · `intros A R`(-4.61)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a : A) (l : list A),
(GoodR A R (l ++ bs) -> GoodR A R (l ++ cs ++ bs)) ->
GoodR A R (a :: l ++ bs) -> GoodR A R (a :: l ++ cs ++ bs)`
- **retrieval 증명 top2**: `Definition IWPath_ind_refl : forall l a, P (l ; (a, a)) idpath. Proof. intros A P xs; elim` ; `Definition IWPath_ind_beta_iwpath_sup (x : A') (h : forall y : B' x, IWPath (j' x y)) : IW`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros a l H' H'0; inversion H'0; simpl in |- *; auto`
- **생성 top5**: `intros a l H' H'0; inversion H'0; auto`(-3.23) · `intros a l H' bs cs H'0; inversion H'0; auto`(-3.48) · `intros a l H' bs' cs' H'0; inversion H'0; auto`(-4.67) · `intros a l H' H''; inversion H''; auto`(-5.09) · `intros a xs H' H'0; inversion H'0; auto`(-5.17)

## buchberger-theories-Bar.v · proof#4 — `Definition equiv_path_hfiber_index (l : I) (a b : IW I A B i j l) : iw_to_hfiber_index l a = iw_to_hfiber_index l b <~> hfiber i' (l; (a, b)).`  (3 steps)


### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (A B : Type) (P : Pred A) (S : Pred B) (f : A -> B),
(forall a : A, P a -> S (f a)) ->
forall l : list A, ExistsL A P l -> ExistsL B S (map f l)`
- **retrieval 증명 top2**: `Definition IWPath_ind_refl : forall l a, P (l ; (a, a)) idpath. Proof. intros A P xs; elim` ; `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A B P S f H' l H'0; elim H'0; simpl in |- *; auto`
- **생성 top5**: `intros A R xs bs; elim xs; simpl in |- *; auto`(-4.48) · `intros A R xs bs cs; elim xs; simpl in |- *; auto`(-4.52) · `intros`(-5.10) · `intros A B P l xs; elim xs; simpl in |- *; auto`(-5.30) · `intros A B P S f H' l H'0; elim H'0; simpl in |- *; auto`(-6.47)

## buchberger-theories-Bar.v · proof#5 — `Global Instance ishprop_iwtype `{Funext} (I : Type) (A : Type) (B : A -> Type) (i : A -> I) (j : forall x, B x -> I) {h : IsEmbedding i} : forall x, I`  (5 steps)


### step 1 — 🔶topk
- **goal(입력 상태)**: `forall (A B : Type) (R : Rel A) (S : Rel B) (f : A -> B),
(forall a b : A, R a b -> S (f a) (f b)) ->
forall l : list A, GoodR A R l -> GoodR B S (map f l)`
- **retrieval 증명 top2**: `Definition equiv_path_hfiber_index (l : I) (a b : IW I A B i j l) : iw_to_hfiber_index l a` ; `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A B R S f H' l H'0; elim H'0; simpl in |- *; auto`
- **생성 top5**: `intros`(-3.03) · `intros A B`(-4.16) · `intros A B R S f H' l H'0`(-4.33) · `intros A B R S f H' l H'0; elim H'0; simpl in |- *; auto`(-4.57) · `intros`(-4.91)

### step 2 — ❌miss
- **goal(입력 상태)**: `forall (a : A) (l0 : list A),
ExistsL A (fun x : A => R x a) l0 -> GoodR B S (f a :: map f l0)`
- **retrieval 증명 top2**: `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)` ; `Definition equiv_path_hfiber_index (l : I) (a b : IW I A B i j l) : iw_to_hfiber_index l a`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros a l0 H'1; apply FoundG; auto`
- **생성 top5**: `intros a l' H'1; elim H'1; simpl in |- *; auto`(-2.76) · `intros a l' H'1; inversion H'1; auto`(-2.77) · `intros a l' H'1; inversion H'1; simpl in |- *; auto`(-2.83) · `intros a l' H'1`(-3.59) · `intros a l0 H'1; inversion H'1; auto`(-3.83)

### step 3 — ❌miss
- **goal(입력 상태)**: `ExistsL B (fun x : B => S x (f a)) (map f l0)`
- **retrieval 증명 top2**: `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)` ; `Definition IWPath_ind_beta_iwpath_sup (x : A') (h : forall y : B' x, IWPath (j' x y)) : IW`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `apply subPredExistsL with (P := fun x : A => R x a); auto`
- **생성 top5**: `apply ExistsL_map; auto`(-2.82) · `induction l0`(-3.00) · `elim H'1; auto`(-3.16) · `elim H'1; simpl in |- *; auto`(-3.33) · `induction H'1`(-3.62)

## buchberger-theories-Bar.v · proof#6 — `Class IsGraph (A : Type) := { Hom : A -> A -> Type }.`  (11 steps)


### step 1 — ❌miss
- **goal(입력 상태)**: `forall (A B : Type) (R : Rel A) (S : Rel B) (f : A -> B),
(forall a b : A, R a b -> S (f a) (f b)) ->
(forall b : B, {a : A | b = f a}) ->
forall l : list A, GRBar A R l -> GRBar B S (map f l)`
- **retrieval 증명 top2**: `Global Instance ishprop_iwtype `{Funext} (I : Type) (A : Type) (B : A -> Type) (i : A -> I` ; `Definition equiv_path_hfiber_index (l : I) (a b : IW I A B i j l) : iw_to_hfiber_index l a`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros A B R S f H' H'0 l H'1; elim H'1; simpl in |- *; auto`
- **생성 top5**: `intros`(-3.27) · `intros A B R S f H' l H'0; elim H'0; simpl in |- *; auto`(-4.33) · `intros A B R S f H' l H'0`(-4.40) · `intros A B`(-4.87) · `intros A B R S f H' l; elim l; simpl in |- *; auto`(-5.15)

### step 2 — 🔶topk
- **goal(입력 상태)**: `forall l0 : list A, GoodR A R l0 -> GRBar B S (map f l0) / forall l0 : list A,
(forall a : A, Bar A (GoodR A R) (a :: l0)) ->
(forall a : A, GRBar B S (f a :: map f l0)) -> GRBar B S (map f l0)`
- **retrieval 증명 top2**: `Global Instance ishprop_iwtype `{Funext} (I : Type) (A : Type) (B : A -> Type) (i : A -> I` ; `Definition equiv_path_iwtype (x : I) (a b : IW I A B i j x) : IW I' A' B' i' j' (x; (a, b)`
- **retrieval premise top3**: `Lemma lift_eq_complete_2 : forall (A B C: MetricSpace) (f g : Complete` ; `Theorem cmp_ne_1_optbool: forall ob, cmp Cne (of_optbool ob) (Vint Int` ; `Theorem cmpu_ne_0_optbool: forall valid_ptr ob, cmpu valid_ptr Cne (of`
- **gold**: `intros l0 H'2`
- **생성 top5**: `intros l0 H'2; elim H'2; simpl in |- *; auto`(-2.05) · `-`(-2.69) · `intros l' H'2; elim H'2; simpl in |- *; auto`(-2.96) · `intros l0 H'2; elim H'2; auto`(-4.06) · `intros l0 H'2; inversion H'2; auto`(-4.20)
- step 3: get_recs 실패 ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Bar.v · proof#7 — `Notation "a $-> b" := (Hom a b).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Buch.v · proof#0 — `Global Instance is1natural_comp {A B : Type} `{IsGraph A} `{Is1Cat B} {F G K : A -> B} `{!Is0Functor F} `{!Is0Functor G} `{!Is0Functor K} (gamma : G $`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Buch.v · proof#1 — `Global Instance is1natural_prewhisker {A B C : Type} {F G : B -> C} (K : A -> B) `{IsGraph A, Is01Cat B, Is1Cat C, !Is0Functor F, !Is0Functor G, !Is0F`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Buch.v · proof#2 — `Global Instance is1natural_postwhisker {A B C : Type} {F G : A -> B} (K : B -> C) `{IsGraph A, Is1Cat B, Is1Cat C, !Is0Functor F, !Is0Functor G, !Is0F`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Buch.v · proof#3 — `Definition nattrans_comp {A B : Type} {F G K : A -> B} `{IsGraph A, Is1Cat B, !Is0Functor F, !Is0Functor G, !Is0Functor K} : NatTrans G K -> NatTrans `  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Buch.v · proof#4 — `Definition nattrans_prewhisker {A B C : Type} {F G : B -> C} `{IsGraph A, Is1Cat B, Is1Cat C, !Is0Functor F, !Is0Functor G} (alpha : NatTrans F G) (K `  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Buch.v · proof#5 — `Definition is1natural_homotopic {A B : Type} `{Is01Cat A} `{Is1Cat B} {F : A -> B} `{!Is0Functor F} {G : A -> B} `{!Is0Functor G} {alpha : F $=> G} (g`  (9 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Buch.v · proof#6 — `Definition issig_NatEquiv {A B : Type} `{IsGraph A} `{HasEquivs B} (F G : A -> B) `{!Is0Functor F, !Is0Functor G} : _ <~> NatEquiv F G := ltac:(issig)`  (2 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Buch.v · proof#7 — `Lemma nattrans_natequiv {A B : Type} `{IsGraph A} `{HasEquivs B} {F G : A -> B} `{!Is0Functor F, !Is0Functor G} : NatEquiv F G -> NatTrans F G.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-BuchAux.v · proof#0 — `Global Instance is0gpd_core {A : Type} `{HasEquivs A} : Is0Gpd (core A).`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-BuchAux.v · proof#1 — `Global Instance is1gpd_core {A : Type} `{HasEquivs A} : Is1Gpd (core A).`  (6 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-BuchAux.v · proof#2 — `Global Instance hasequivs_core {A : Type} `{HasEquivs A} : HasEquivs (core A).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-BuchAux.v · proof#3 — `Lemma cate_isinitial A `{HasEquivs A} (x y : A) : IsInitial x -> IsInitial y -> x $<~> y.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-BuchAux.v · proof#4 — `Lemma cate_isterminal A `{HasEquivs A} (x y : A) : IsTerminal x -> IsTerminal y -> x $<~> y.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-BuchAux.v · proof#5 — `Lemma isinitial_cate A `{HasEquivs A} (x y : A) : x $<~> y -> IsInitial x -> IsInitial y.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-BuchAux.v · proof#6 — `Lemma isterminal_cate A `{HasEquivs A} (x y : A) : x $<~> y -> IsTerminal x -> IsTerminal y.`  (15 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-BuchAux.v · proof#7 — `Class Cat_IsBiInv {A} `{Is1Cat A} {x y : A} (f : x $-> y) := { cat_equiv_inv : y $-> x; cat_eisretr : f $o cat_equiv_inv $== Id y; cat_equiv_inv' : y `  (6 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-BuchRed.v · proof#0 — `Definition lex_from_isconnected_paths (H : forall (A : Type) (Ac : IsConnected O A) (x y : A), IsConnected O (x = y)) : Lex O.`  (6 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-BuchRed.v · proof#1 — `Definition lex_from_isequiv_ismodal_isconnected_types (H : forall A B (f : A -> B), (IsConnected O A) -> (IsConnected O B) -> (MapIn O f) -> IsEquiv f`  (6 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-BuchRed.v · proof#2 — `Definition lex_from_ispullback_connmap_mapino_commsq (H : forall {A B C D} (f : A -> B) (g : C -> D) (h : A -> C) (k : B -> D), (IsConnMap O f) -> (Is`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-BuchRed.v · proof#3 — `Definition ismodality_isequiv_O_functor_hfiber (O : ReflectiveSubuniverse) (H : forall {A B : Type} (f : A -> B) (b : B), IsEquiv (O_functor_hfiber O `  (10 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-BuchRed.v · proof#4 — `Definition lex_gen `{Univalence} (O : Modality) `{IsAccModality O} (lexgen : forall (i : ngen_indices (acc_ngen O)) (x y : ngen_type (acc_ngen O) i), `  (11 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-BuchRed.v · proof#5 — `Fixpoint nSep (n : trunc_index) (O : Subuniverse) : Subuniverse := match n with | -2 => O | n.+1 => Sep (nSep n O) end.`  (34 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-BuchRed.v · proof#6 — `Definition nsep_iff_trunc_to_O (n : trunc_index) (O : Modality) `{Lex O} (A : Type) : In (nSep n O) A <-> IsTruncMap n (to O A).`  (13 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-BuchRed.v · proof#7 — `Definition extendable_over_unit (n : nat) (A : Type@{a}) (C : Unit -> Type@{i}) (D : forall u, C u -> Type@{j}) (ext : ExtendableAlong@{a a i k} n (co`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Dickson.v · proof#0 — `Global Instance reflexive_Hom {A} `{Is01Cat A} : Reflexive Hom := fun a => Id a.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Dickson.v · proof#1 — `Fixpoint IsIndexedBy (x : I) (w : W A B) : Type := match w with | w_sup a b => (i a = x) * (forall c, IsIndexedBy (j a c) (b c)) end.`  (6 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Dickson.v · proof#2 — `Definition GpdHom_path {A} `{Is0Gpd A} {a b : A} (p : a = b) : a $== b.`  (3 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Dickson.v · proof#3 — `Class Is0Functor {A B : Type} `{IsGraph A} `{IsGraph B} (F : A -> B) := { fmap : forall (a b : A) (f : a $-> b), F a $-> F b }.`  (18 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Dickson.v · proof#4 — `Class Is2Graph (A : Type) `{IsGraph A} := isgraph_hom : forall (a b : A), IsGraph (a $-> b).`  (18 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Dickson.v · proof#5 — `Class Is1Cat (A : Type) `{!IsGraph A, !Is2Graph A, !Is01Cat A} := { is01cat_hom : forall (a b : A), Is01Cat (a $-> b) ; is0gpd_hom : forall (a b : A),`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Dickson.v · proof#6 — `Definition cat_assoc_opp {A : Type} `{Is1Cat A} {a b c d : A} (f : a $-> b) (g : b $-> c) (h : c $-> d) : h $o (g $o f) $== (h $o g) $o f := (cat_asso`  (12 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Dickson.v · proof#7 — `Definition cat_postwhisker {A} `{Is1Cat A} {a b c : A} {f g : a $-> b} (h : b $-> c) (p : f $== g) : h $o f $== h $o g := fmap (cat_postcomp a h) p.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-DivTerm.v · proof#0 — `Definition takeUntil_length `(P : Stream A → bool) `(ex : LazyExists (fun x => Is_true (P x)) s) : nat := takeUntil P ex (λ _, S) O.`  (3 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-DivTerm.v · proof#1 — `Lemma takeUntil_length_correct {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (P x)) s) : Is_true (P (Str_nth_tl (takeUntil_length P e`  (21 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-DivTerm.v · proof#2 — `Lemma takeUntil_correct {A B} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (P x)) s) (cons: A → B → B) (nil : B) : takeUntil P ex cons n`  (15 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-DivTerm.v · proof#3 — `Lemma takeUntil_length_tl {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (P x)) s) (Ptl : EventuallyForAll (fun x => Is_true (P x)) s)`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-DivTerm.v · proof#4 — `Lemma takeUntil_length_Str_nth_tl {A} (P : Stream A → bool) `(ex : !LazyExists (fun x => Is_true (P x)) s) (Ptl : EventuallyForAll (fun x => Is_true (`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-DivTerm.v · proof#5 — `Lemma takeUntil_length_ForAllIf {A1 A2} (P1 : Stream A1 → bool) `(ex1 : LazyExists (fun x => Is_true (P1 x)) s1) {P2 : Stream A2 → bool} `(ex2 : LazyE`  (8 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-DivTerm.v · proof#6 — `Definition NearBy (l : X) (ε : QposInf) := ForAll (λ s, ball_ex ε (hd s) l).`  (10 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-DivTerm.v · proof#7 — `Lemma NearBy_comp l1 l2 : l1 = l2 → ∀ ε1 ε2, QposEq ε1 ε2 → ∀ s, (NearBy l1 ε1 s ↔ NearBy l2 ε2 s).`  (11 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Fred.v · proof#0 — `Definition emap_inv {A B : Type} `{HasEquivs A} `{HasEquivs B} (F : A -> B) `{!Is0Functor F, !Is1Functor F} {a b : A} (e : a $<~> b) : cate_fun (emap `  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Fred.v · proof#1 — `Definition cat_equiv_path {A : Type} `{HasEquivs A} (a b : A) : (a = b) -> (a $<~> b).`  (9 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Fred.v · proof#2 — `Record core (A : Type) := { uncore : A }.`  (13 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Fred.v · proof#3 — `Global Instance isgraph_core {A : Type} `{HasEquivs A} : IsGraph (core A).`  (6 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Fred.v · proof#4 — `Global Instance is01cat_core {A : Type} `{HasEquivs A} : Is01Cat (core A).`  (21 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Fred.v · proof#5 — `Global Instance is2graph_core {A : Type} `{HasEquivs A} : Is2Graph (core A).`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Fred.v · proof#6 — `Global Instance is01cat_core_hom {A : Type} `{HasEquivs A} (a b : core A) : Is01Cat (a $-> b).`  (6 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Fred.v · proof#7 — `Global Instance is0gpd_core_hom {A : Type} `{HasEquivs A} (a b : core A) : Is0Gpd (a $-> b).`  (6 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-ListProps.v · proof#0 — `Definition iw_sup' (x : A) (y : forall z : B x, IW' (j x z)) : IW' (i x) := (w_sup A B x (fun a => pr1 (y a)); (idpath, (fun a => pr2 (y a)))).`  (7 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-ListProps.v · proof#1 — `Definition iw_eta {A B I i j} (l : I) (w : IW I A B i j l) : path_index_iw_label l w # iw_sup I A B i j (iw_label w) (iw_arity l w) = w.`  (3 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-ListProps.v · proof#2 — `Definition iw_to_hfiber_index {A B I i j} (l : I) : IW I A B i j l -> hfiber i l.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-ListProps.v · proof#3 — `Definition IW'_ind (P : forall i, IW' i -> Type) (S : forall x y, (forall c, P _ (y c)) -> P _ (iw_sup' x y)) : forall x w, P x w.`  (6 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-ListProps.v · proof#4 — `Definition path_index_iw_label {A B I i j} (l : I) (w : IW I A B i j l) : i (iw_label w) = l.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Monomials.v · proof#0 — `Class NaturalsToSemiRing := naturals_to_semiring: ∀ B `{Mult B} `{Plus B} `{One B} `{Zero B}, A → B.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Monomials.v · proof#1 — `Program Definition natural_initial_arrow: InitialArrow (semirings.object A) := λ y u, match u return A → y u with tt => naturals_to_semiring (y tt) en`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Monomials.v · proof#2 — `Lemma natural_initial (same_morphism : ∀ `{SemiRing B} {h : A → B} `{!SemiRing_Morphism h}, naturals_to_semiring B = h) : Initial (semirings.object A)`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Monomials.v · proof#3 — `Global Instance: FullPseudoSemiRingOrder nat_le nat_lt.`  (7 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Monomials.v · proof#4 — `#[global] Instance: Params (@nat_distance) 4 := {}.`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Monomials.v · proof#5 — `Class NatDistance N `{Equiv N} `{Plus N} := nat_distance_sig : ∀ x y : N, { z : N | x + z = y } + { z : N | y + z = x }.`  (6 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Monomials.v · proof#6 — `Definition nat_distance `{nd : NatDistance N} (x y : N) := match nat_distance_sig x y with | inl (n↾_) => n | inr (n↾_) => n end.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Monomials.v · proof#7 — `Infix "^" := pow : mc_scope.`  (6 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-OpenIndGoodRel.v · proof#0 — `Notation "a $== b" := (GpdHom a b).`  (8 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-POrder.v · proof#0 — `Lemma nonpos_plus_compat x y : x ≤ 0 → y ≤ 0 → x + y ≤ 0.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-POrder.v · proof#1 — `Instance nonneg_plus_compat (x y : R) : PropHolds (0 ≤ x) → PropHolds (0 ≤ y) → PropHolds (0 ≤ x + y).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-POrder.v · proof#2 — `Lemma decompose_le {x y} : x ≤ y → ∃ z, 0 ≤ z ∧ y = x + z.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-POrder.v · proof#3 — `Lemma compose_le x y z : 0 ≤ z → y = x + z → x ≤ y.`  (3 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-POrder.v · proof#4 — `Lemma ge_1_mult_le_compat_r x y z : 1 ≤ z → 0 ≤ y → x ≤ y → x ≤ y * z.`  (2 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-POrder.v · proof#5 — `Lemma ge_1_mult_le_compat_l x y z : 1 ≤ z → 0 ≤ y → x ≤ y → x ≤ z * y.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-POrder.v · proof#6 — `Lemma flip_nonpos_mult_l x y z : z ≤ 0 → x ≤ y → z * y ≤ z * x.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-POrder.v · proof#7 — `Lemma flip_nonpos_mult_r x y z : z ≤ 0 → x ≤ y → y * z ≤ x * z.`  (3 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcomb.v · proof#0 — `Definition gpd_rev_rev {A} `{Is1Gpd A} {a0 a1 : A} (g : a0 $== a1) : (g^$)^$ $== g.`  (9 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcomb.v · proof#1 — `Definition gpd_1functor_V {A B} `{Is1Gpd A, Is1Gpd B} (F : A -> B) `{!Is0Functor F, !Is1Functor F} {a0 a1 : A} (f : a0 $== a1) : fmap F f^$ $== (fmap `  (12 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcomb.v · proof#2 — `Definition gpd_strong_V_hh {A} `{Is1Gpd A, !HasMorExt A} {a b c : A} (f : b $-> c) (g : a $-> b) : f^$ $o (f $o g) = g := path_hom (gpd_V_hh f g).`  (16 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcomb.v · proof#3 — `Definition gpd_strong_h_Vh {A} `{Is1Gpd A, !HasMorExt A} {a b c : A} (f : c $-> b) (g : a $-> b) : f $o (f^$ $o g) = g := path_hom (gpd_h_Vh f g).`  (10 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcomb.v · proof#4 — `Definition gpd_strong_hh_V {A} `{Is1Gpd A, !HasMorExt A} {a b c : A} (f : b $-> c) (g : a $-> b) : (f $o g) $o g^$ = f := path_hom (gpd_hh_V f g).`  (7 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcomb.v · proof#5 — `Definition gpd_strong_hV_h {A} `{Is1Gpd A, !HasMorExt A} {a b c : A} (f : b $-> c) (g : b $-> a) : (f $o g^$) $o g = f := path_hom (gpd_hV_h f g).`  (7 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcomb.v · proof#6 — `Definition gpd_strong_rev_pp {A} `{Is1Gpd A, !HasMorExt A} {a b c : A} (f : b $-> c) (g : a $-> b) : (f $o g)^$ = g^$ $o f^$ := path_hom (gpd_rev_pp f`  (16 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcomb.v · proof#7 — `Definition gpd_strong_rev_1 {A} `{Is1Gpd A, !HasMorExt A} {a : A} : (Id a)^$ = Id a := path_hom gpd_rev_1.`  (11 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcrit.v · proof#0 — `Definition compose_cate {A} `{HasEquivs A} {a b c : A} (g : b $<~> c) (f : a $<~> b) : a $<~> c := Build_CatEquiv (g $o f).`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcrit.v · proof#1 — `Notation "g $oE f" := (compose_cate g f).`  (34 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcrit.v · proof#2 — `Definition compose_cate_fun {A} `{HasEquivs A} {a b c : A} (g : b $<~> c) (f : a $<~> b) : cate_fun (g $oE f) $== g $o f.`  (28 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcrit.v · proof#3 — `Definition compose_cate_funinv {A} `{HasEquivs A} {a b c : A} (g : b $<~> c) (f : a $<~> b) : g $o f $== cate_fun (g $oE f).`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcrit.v · proof#4 — `Definition id_cate_fun {A} `{HasEquivs A} (a : A) : cate_fun (id_cate a) $== Id a.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcrit.v · proof#5 — `Definition compose_cate_assoc {A} `{HasEquivs A} {a b c d : A} (f : a $<~> b) (g : b $<~> c) (h : c $<~> d) : cate_fun ((h $oE g) $oE f) $== cate_fun `  (10 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcrit.v · proof#6 — `Definition compose_cate_idl {A} `{HasEquivs A} {a b : A} (f : a $<~> b) : cate_fun (id_cate b $oE f) $== cate_fun f.`  (20 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pcrit.v · proof#7 — `Definition compose_cate_idr {A} `{HasEquivs A} {a b : A} (f : a $<~> b) : cate_fun (f $oE id_cate a) $== cate_fun f.`  (6 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Peq.v · proof#0 — `Lemma gt_1_ge_1_mult_compat x y : 1 < x → 1 ≤ y → 1 < x * y.`  (13 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Peq.v · proof#1 — `Lemma ge_1_gt_1_mult_compat x y : 1 ≤ x → 1 < y → 1 < x * y.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Peq.v · proof#2 — `Lemma not_le_1_0 : ¬1 ≤ 0.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Peq.v · proof#3 — `Lemma not_le_2_0 : ¬2 ≤ 0.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Peq.v · proof#4 — `Instance dec_pseudo_srorder: PseudoSemiRingOrder (<).`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Peq.v · proof#5 — `Instance dec_full_pseudo_srorder: FullPseudoSemiRingOrder (≤) (<).`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Peq.v · proof#6 — `Lemma preserving_preserves_nonneg : (∀ x, 0 ≤ x → 0 ≤ f x) → OrderPreserving f.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Peq.v · proof#7 — `Instance preserves_nonneg `{!OrderPreserving f} x : PropHolds (0 ≤ x) → PropHolds (0 ≤ f x).`  (7 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pminus.v · proof#0 — `Lemma flip_nonpos_minus (x y : R) : y - x ≤ 0 ↔ y ≤ x.`  (29 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pminus.v · proof#1 — `Lemma nonneg_minus_compat_back (x y z : R) : 0 ≤ z → x ≤ y - z → x ≤ y.`  (25 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pminus.v · proof#2 — `Lemma between_nonneg (x : R) : 0 ≤ x → -x ≤ x.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pminus.v · proof#3 — `Lemma flip_lt_negate x y : -y < -x ↔ x < y.`  (8 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pminus.v · proof#4 — `Lemma flip_pos_negate x : 0 < x ↔ -x < 0.`  (11 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pminus.v · proof#5 — `Lemma flip_neg_negate x : x < 0 ↔ 0 < -x.`  (18 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pminus.v · proof#6 — `Lemma flip_lt_minus_r (x y z : R) : z < y - x ↔ z + x < y.`  (57 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pminus.v · proof#7 — `Lemma flip_lt_minus_l (x y z : R) : y - x < z ↔ y < z + x.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmult.v · proof#0 — `Definition cate_inv {A} `{HasEquivs A} {a b : A} (f : a $<~> b) : b $<~> a.`  (9 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmult.v · proof#1 — `Notation "f ^-1$" := (cate_inv f).`  (12 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmult.v · proof#2 — `Definition cate_issect {A} `{HasEquivs A} {a b} (f : a $<~> b) : f^-1$ $o f $== Id a.`  (33 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmult.v · proof#3 — `Definition cate_isretr {A} `{HasEquivs A} {a b} (f : a $<~> b) : f $o f^-1$ $== Id b.`  (15 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmult.v · proof#4 — `Definition cate_inverse_sect {A} `{HasEquivs A} {a b} (f : a $<~> b) (g : b $-> a) (p : f $o g $== Id b) : cate_fun f^-1$ $== g.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmult.v · proof#5 — `Definition cate_inverse_retr {A} `{HasEquivs A} {a b} (f : a $<~> b) (g : b $-> a) (p : g $o f $== Id a) : cate_fun f^-1$ $== g.`  (8 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmult.v · proof#6 — `Definition cate_inv_adjointify {A} `{HasEquivs A} {a b : A} (f : a $-> b) (g : b $-> a) (r : f $o g $== Id b) (s : g $o f $== Id a) : cate_fun (cate_a`  (16 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmult.v · proof#7 — `Global Instance catie_id {A} `{HasEquivs A} (a : A) : CatIsEquiv (Id a) := catie_adjointify (Id a) (Id a) (cat_idl (Id a)) (cat_idl (Id a)).`  (28 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmults.v · proof#0 — `Lemma same_morphism: naturals_to_semiring N R ∘ f⁻¹ = h.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmults.v · proof#1 — `Program Instance retract_is_nat: Naturals SR (U:=retract_is_nat_to_sr).`  (19 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmults.v · proof#2 — `Lemma induction (P: Z → Prop) `{!Proper ((=) ==> iff) P}: P 0 → (∀ n, 0 ≤ n → P n → P (1 + n)) → (∀ n, n ≤ 0 → P n → P (n - 1)) → ∀ n, P n.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmults.v · proof#3 — `Lemma induction (P: N → Prop) `{!Proper ((=) ==> iff) P}: P 0 → (∀ n, P n → P (1 + n)) → ∀ n, P n.`  (23 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmults.v · proof#4 — `Lemma from_nat_stmt: ∀ (s: Statement varieties.semirings.theory) (w : Vars varieties.semirings.theory (varieties.semirings.object N) nat), (∀ v: Vars `  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmults.v · proof#5 — `Instance nat_nontrivial: PropHolds ((1:N) ≠ 0).`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmults.v · proof#6 — `Instance nat_nontrivial_apart `{Apart N} `{!TrivialApart N} : PropHolds ((1:N) ≶ 0).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pmults.v · proof#7 — `Lemma zero_sum (x y : N) : x + y = 0 → x = 0 ∧ y = 0.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pplus.v · proof#0 — `Lemma nat_induction (P : nat → Prop) : P 0 → (∀ n, P n → P (1 + n)) → ∀ n, P n.`  (31 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pplus.v · proof#1 — `#[global] Instance nat_le: Le nat := Peano.le.`  (19 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pplus.v · proof#2 — `#[global] Instance nat_lt `{Naturals N} : Lt N | 10 := dec_lt.`  (51 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pplus.v · proof#3 — `#[global] Instance nat_lt: Lt nat := Peano.lt.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pplus.v · proof#4 — `#[global] Instance nat_le_dec : `{Decision (x ≤ y)} := le_dec.`  (22 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pplus.v · proof#5 — `#[global] Instance nat_cut_minus: CutMinus nat := minus.`  (30 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pplus.v · proof#6 — `CoInductive Stream_eq_coind (s1 s2: ∞A) : Prop := stream_eq_coind : hd s1 = hd s2 → Stream_eq_coind (tl s1) (tl s2) → Stream_eq_coind s1 s2.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pplus.v · proof#7 — `Global Instance stream_eq: Equiv (∞A) := Stream_eq_coind.`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduce.v · proof#0 — `Lemma InFinEnumC_map : forall (X Y:MetricSpace) (f:X --> Y) a l, InFinEnumC a l -> InFinEnumC (f a) (map f l).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduce.v · proof#1 — `Definition FinEnum_map_modulus (z:Qpos) (muf : Qpos -> QposInf) (e:Qpos) := match (muf e) with | QposInfinity => z | Qpos2QposInf d => d end.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduce.v · proof#2 — `Lemma FinEnum_map_uc : forall z X Y (f:X --> Y), is_UniformlyContinuousFunction (map f:FinEnum X -> FinEnum Y) (FinEnum_map_modulus z (mu f)).`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduce.v · proof#3 — `Definition FinEnum_map z (X Y : MetricSpace) (f:X --> Y) : FinEnum X --> FinEnum Y := Build_UniformlyContinuousFunction (FinEnum_map_uc z f).`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduce.v · proof#4 — `Lemma FinEnum_map_Cunit : forall X (s1 s2:FinEnum X) (e:Qpos), ball (proj1_sig e) s1 s2 <-> ball (proj1_sig e) (map Cunit s1:FinEnum (Complete X)) (ma`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduce.v · proof#5 — `Definition CompleteSubset := forall (f:Complete X), (forall e, P (approximate f e)) -> {y:X | P y & msp_eq (Cunit y) f}.`  (21 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduce.v · proof#6 — `Definition ExtSubset := forall x y, (msp_eq x y) -> (P x <-> P y).`  (19 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduce.v · proof#7 — `Definition TotallyBoundedSubset := forall (e:Qpos), {l : list X | forall y, In y l -> P y & forall x, P x -> exists y, In y l /\ ball (proj1_sig e) x `  (17 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduceplus.v · proof#0 — `Lemma CompactTotallyBoundedA : forall s e y, In y (CompactTotalBound s e) -> inCompact y s.`  (13 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduceplus.v · proof#1 — `Lemma CompactTotallyBoundedB : forall s e x, (inCompact x s) -> exists y, In y (CompactTotalBound s e) /\ ball (proj1_sig e) x y.`  (11 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduceplus.v · proof#2 — `Lemma CompactTotallyBounded : forall s, TotallyBoundedSubset _ (fun z => inCompact z s).`  (8 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduceplus.v · proof#3 — `Lemma CompactAsBishopCompact : forall s, CompactSubset _ (fun z => inCompact z s).`  (11 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduceplus.v · proof#4 — `Definition BishopCompactAsCompact_raw (P:Complete X->Prop) (HP:CompactSubset _ P) (e:QposInf) : (FinEnum X) := match e with |QposInfinity => nil |Qpos`  (16 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduceplus.v · proof#5 — `Lemma BishopCompactAsCompact_prf : forall P (HP:CompactSubset _ P), is_RegularFunction (@ball (FinEnum X)) (BishopCompactAsCompact_raw HP).`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduceplus.v · proof#6 — `Definition BishopCompactAsCompact (P:Complete X->Prop) (HP:CompactSubset _ P) : Compact X := Build_RegularFunction (BishopCompactAsCompact_prf HP).`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preduceplus.v · proof#7 — `Lemma BishopCompact_Compact_BishopCompact1 : forall (P:Complete X->Prop) (HP:CompactSubset _ P) x, P x -> inCompact x (BishopCompactAsCompact HP).`  (134 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preducestar.v · proof#0 — `Global Instance is1cat_is1cat_strong (A : Type) `{Is1Cat_Strong A} : Is1Cat A | 1000.`  (7 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preducestar.v · proof#1 — `Definition IsInitial {A : Type} `{Is1Cat A} (x : A) := forall (y : A), {f : x $-> y & forall g, f $== g}.`  (2 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preducestar.v · proof#2 — `Definition mor_initial {A : Type} `{Is1Cat A} (x y : A) {h : IsInitial x} : x $-> y := (h y).1.`  (30 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preducestar.v · proof#3 — `Definition mor_initial_unique {A : Type} `{Is1Cat A} (x y : A) {h : IsInitial x} (f : x $-> y) : mor_initial x y $== f := (h y).2 f.`  (30 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preducestar.v · proof#4 — `Definition IsTerminal {A : Type} `{Is1Cat A} (y : A) := forall (x : A), {f : x $-> y & forall g, f $== g}.`  (64 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preducestar.v · proof#5 — `Definition mor_terminal {A : Type} `{Is1Cat A} (x y : A) {h : IsTerminal y} : x $-> y := (h x).1.`  (7 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preducestar.v · proof#6 — `Definition mor_terminal_unique {A : Type} `{Is1Cat A} (x y : A) {h : IsTerminal y} (f : x $-> y) : mor_terminal x y $== f := (h x).2 f.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Preducestar.v · proof#7 — `Class HasMorExt (A : Type) `{Is1Cat A} := { isequiv_Htpy_path : forall a b f g, IsEquiv (@GpdHom_path (a $-> b) _ _ _ f g) }.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspminus.v · proof#0 — `Lemma FinSubset_ball_weak_le : forall (e1 e2:Q) x l, e1 <= e2 -> FinSubset_ball e1 x l -> FinSubset_ball e2 x l.`  (17 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspminus.v · proof#1 — `Lemma FinSubset_ball_nonneg : forall (e:Q) x l, FinSubset_ball e x l -> 0 <= e.`  (16 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspminus.v · proof#2 — `Lemma FinSubset_ball_triangle_l : forall e1 e2 x1 x2 l, (ball e1 x1 x2) -> FinSubset_ball e2 x2 l -> FinSubset_ball (e1 + e2) x1 l.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspminus.v · proof#3 — `Lemma FinSubset_ball_app_l : forall e x l1 l2, FinSubset_ball e x l1 -> FinSubset_ball e x (l1 ++ l2).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspminus.v · proof#4 — `Lemma FinSubset_ball_app_r : forall e x l1 l2, FinSubset_ball e x l2 -> FinSubset_ball e x (l1 ++ l2).`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspminus.v · proof#5 — `Lemma FinSubset_ball_app_orC : forall e x l1 l2, FinSubset_ball e x (l1 ++ l2) -> orC (FinSubset_ball e x l1) (FinSubset_ball e x l2).`  (10 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspminus.v · proof#6 — `Definition FinEnum_eq (a b:list X) : Prop := forall x, InFinEnumC x a <-> InFinEnumC x b.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspminus.v · proof#7 — `Definition FinEnum_ball (e:Q) (x y:list X) := hausdorffBall X e (fun a => InFinEnumC a x) (fun a => InFinEnumC a y).`  (9 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspoly.v · proof#0 — `#[export] Instance isFaithful_idmap {A : Type} `{Is1Cat A}: Faithful idmap.`  (11 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspoly.v · proof#1 — `Global Instance is01functor_const `{IsGraph A} `{Is01Cat B} (x : B) : Is0Functor (fun _ : A => x).`  (9 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspoly.v · proof#2 — `Global Instance is1functor_const `{Is1Cat A} `{Is1Cat B} (x : B) : Is1Functor (fun _ : A => x).`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspoly.v · proof#3 — `Global Instance is0functor_compose {A B C : Type} `{IsGraph A, IsGraph B, IsGraph C} (F : A -> B) (G : B -> C) `{!Is0Functor F, !Is0Functor G} : Is0Fu`  (27 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspoly.v · proof#4 — `Global Instance is1functor_compose {A B C : Type} `{Is1Cat A, Is1Cat B, Is1Cat C} (F : A -> B) `{!Is0Functor F, !Is1Functor F} (G : B -> C) `{!Is0Func`  (7 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspoly.v · proof#5 — `Class Is1Gpd (A : Type) `{Is1Cat A, !Is0Gpd A} := { gpd_issect : forall {a b : A} (f : a $-> b), f^$ $o f $== Id a ; gpd_isretr : forall {a b : A} (f `  (79 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspoly.v · proof#6 — `Definition gpd_V_hh {A} `{Is1Gpd A} {a b c : A} (f : b $-> c) (g : a $-> b) : f^$ $o (f $o g) $== g := (cat_assoc _ _ _)^$ $@ (gpd_issect f $@R g) $@ `  (9 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Pspoly.v · proof#7 — `Definition gpd_h_Vh {A} `{Is1Gpd A} {a b c : A} (f : c $-> b) (g : a $-> b) : f $o (f^$ $o g) $== g := (cat_assoc _ _ _)^$ $@ (gpd_isretr f $@R g) $@ `  (22 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Relation_Operators_compat.v · proof#0 — `Inductive Laws: EqEntailment sig → Prop := |e_plus_assoc: Laws (x + (y + z) === (x + y) + z) |e_plus_comm: Laws (x + y === y + x) |e_plus_0_l: Laws (0`  (14 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Relation_Operators_compat.v · proof#1 — `Definition theory: EquationalTheory := Build_EquationalTheory sig Laws.`  (17 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Relation_Operators_compat.v · proof#2 — `Instance implementation: AlgebraOps sig (λ _, A) := λ o, match o with plus => (+) | mult => (.*.) | zero => 0: A | one => 1:A end.`  (14 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Relation_Operators_compat.v · proof#3 — `Lemma laws en (l: Laws en) vars: eval_stmt sig vars en.`  (38 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Relation_Operators_compat.v · proof#4 — `Global Instance variety: InVariety theory (λ _, A).`  (57 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Relation_Operators_compat.v · proof#5 — `Definition Object := varieties.Object theory.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Relation_Operators_compat.v · proof#6 — `Definition object: Object := varieties.object theory (λ _, A).`  (16 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Relation_Operators_compat.v · proof#7 — `Lemma mor_from_sr_to_alg `{InVariety theory A} `{InVariety theory B} (f: ∀ u, A u → B u) `{!SemiRing_Morphism (f tt)}: HomoMorphism sig A B f.`  (9 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Term.v · proof#0 — `Lemma pseudo_order_lt_ext x₁ y₁ x₂ y₂ : x₁ < y₁ → x₂ < y₂ ∨ x₁ ≶ x₂ ∨ y₂ ≶ y₁.`  (3 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Term.v · proof#1 — `Lemma ne_total_lt `{!TrivialApart A} x y : x ≠ y → x < y ∨ y < x.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Term.v · proof#2 — `Global Instance lt_trichotomy `{!TrivialApart A} `{∀ x y, Decision (x = y)} : Trichotomy (<).`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Term.v · proof#3 — `Instance strict_po_apart_ne x y : PropHolds (x ≶ y) → PropHolds (x ≠ y).`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Term.v · proof#4 — `Lemma lt_le x y : PropHolds (x < y) → PropHolds (x ≤ y).`  (6 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Term.v · proof#5 — `Lemma not_le_not_lt x y : ¬x ≤ y → ¬x < y.`  (2 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Term.v · proof#6 — `Lemma lt_apart_flip x y : x < y → y ≶ x.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-Term.v · proof#7 — `Lemma le_not_lt_flip x y : y ≤ x → ¬x < y.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-WfR0.v · proof#0 — `Definition issig_NatTrans {A B : Type} `{IsGraph A} `{Is1Cat B} (F G : A -> B) {ff : Is0Functor F} {fg : Is0Functor G} : _ <~> NatTrans F G := ltac:(i`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-WfR0.v · proof#1 — `Definition isnat_tr {A B : Type} `{IsGraph A} `{Is1Cat B} {F : A -> B} `{!Is0Functor F} {G : A -> B} `{!Is0Functor G} (alpha : F $=> G) `{!Is1Natural `  (31 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-WfR0.v · proof#2 — `Definition trans_comp {A B : Type} `{Is01Cat B} {F G K : A -> B} (gamma : G $=> K) (alpha : F $=> G) : F $=> K := fun a => gamma a $o alpha a.`  (22 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-WfR0.v · proof#3 — `Definition IW' (x : I) := sig (IsIndexedBy x).`  (13 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-WfR0.v · proof#4 — `Definition trans_prewhisker {A B : Type} {C : B -> Type} {F G : forall x, C x} `{Is01Cat B} `{!forall x, IsGraph (C x)} `{!forall x, Is01Cat (C x)} (g`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-moreCoefStructure.v · proof#0 — `Class EuclidSpec A (d : DivEuclid A) (m : ModEuclid A) `{Equiv A} `{Le A} `{Lt A} `{Zero A} `{Plus A} `{Mult A} := { div_proper : Proper ((=) ==> (=) `  (2 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-moreCoefStructure.v · proof#1 — `Class CutMinus A := cut_minus : A → A → A.`  (2 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-moreCoefStructure.v · proof#2 — `Infix "∸" := cut_minus (at level 50, left associativity) : mc_scope.`  (2 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-moreCoefStructure.v · proof#3 — `Notation "(∸)" := cut_minus (only parsing) : mc_scope.`  (3 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-moreCoefStructure.v · proof#4 — `Notation "( x ∸)" := (cut_minus x) (only parsing) : mc_scope.`  (2 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-moreCoefStructure.v · proof#5 — `Notation "(∸ y )" := (λ x, x ∸ y) (only parsing) : mc_scope.`  (3 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-moreCoefStructure.v · proof#6 — `Class CutMinusSpec A (cm : CutMinus A) `{Equiv A} `{Zero A} `{Plus A} `{Le A} := { cut_minus_le : ∀ x y, y ≤ x → x ∸ y + y = x ; cut_minus_0 : ∀ x y, `  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## buchberger-theories-moreCoefStructure.v · proof#7 — `Lemma le_flip `{Le A} `{!TotalRelation (≤)} x y : ¬y ≤ x → x ≤ y.`  (9 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Alphabet.v · proof#0 — `Ltac equiv_via mid := apply @equiv_composeR' with (B := mid).`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Alphabet.v · proof#1 — `Ltac decomposing_intros := let x := fresh in intros x; cbn in x; try match type of x with | ?a = ?b => fail 1 (** Don't destruct paths *) | forall y:?`  (12 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Alphabet.v · proof#2 — `Lemma sn_subst : forall T M, sn (subst T M) -> sn M.`  (13 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Alphabet.v · proof#3 — `Implicit Types i k m n p : nat.`  (7 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Alphabet.v · proof#4 — `Implicit Type s : sort.`  (5 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Alphabet.v · proof#5 — `Implicit Types A B M N T t u v : term.`  (4 steps)

- step 0: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Alphabet.v · proof#6 — `Ltac decomposing_intros_with_paths := let x := fresh in intros x; cbn in x; multimatch type of x with | _ => try match type of x with | (** Don't dest`  (8 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Alphabet.v · proof#7 — `Ltac make_equiv_contr_basedpaths := simple notypeclasses refine (equiv_adjointify _ _ _ _); (** [solve [ unshelve TAC ]] ensures that [TAC] succeeds w`  (8 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter.v · proof#0 — `Definition equiv_path_sigma `(P : A -> Type) (u v : sig P) : {p : u.1 = v.1 & p # u.2 = v.2} <~> (u = v) := Build_Equiv _ _ (path_sigma_uncurried P u `  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter.v · proof#1 — `Global Instance isequiv_path_sigma_contra `{P : A -> Type} {u v : sig P} : IsEquiv (path_sigma_uncurried_contra P u v) | 0.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter.v · proof#2 — `Definition pr1_path_1 {A : Type} {P : A -> Type} (u : sig P) : (idpath u) ..1 = idpath (u .1) := 1.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter.v · proof#3 — `Definition ap_path_sigma {A B} (P : A -> Type) (F : forall a : A, P a -> B) {x x' : A} {y : P x} {y' : P x'} (p : x = x') (q : p # y = y') : ap (fun w`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter.v · proof#4 — `Definition eta_sigma `{P : A -> Type} (u : sig P) : (u.1; u.2) = u := 1.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter.v · proof#5 — `Definition eta3_sigma `{P : forall (a : A) (b : B a) (c : C a b), Type} (u : sig (fun a => sig (fun b => sig (P a b)))) : (u.1; u.2.1; u.2.2.1; u.2.2.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter.v · proof#6 — `Definition pr1_path `{P : A -> Type} {u v : sig P} (p : u = v) : u.1 = v.1 := ap pr1 p.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter.v · proof#7 — `Definition pr2_path `{P : A -> Type} {u v : sig P} (p : u = v) : p..1 # u.2 = v.2 := (transport_compose P pr1 p u.2)^ @ (@apD {x:A & P x} _ pr2 _ _ p)`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_complete.v · proof#0 — `Lemma eqb_true_b : forall b : bool, eqb true b = b.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_complete.v · proof#1 — `Lemma eqb_b_true : forall b : bool, eqb b true = b.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_complete.v · proof#2 — `Lemma eqb_b_false : forall b : bool, eqb b false = negb b.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_complete.v · proof#3 — `Lemma eqb_false_b : forall b : bool, eqb false b = negb b.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_complete.v · proof#4 — `Lemma eqb_com : forall b1 b2 : bool, eqb b1 b2 = eqb b2 b1.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_complete.v · proof#5 — `Lemma orb_false_2 : forall b b' : bool, b || b' = false -> b' = false.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_complete.v · proof#6 — `Lemma orb_false_1 : forall b b' : bool, b || b' = false -> b = false.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_complete.v · proof#7 — `Definition boolOpFun (n : boolOp) := match n with | ANd => andb | Or => orb | Impl => implb | normalize.Eq => eqb end.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_correct.v · proof#0 — `Definition equiv_sigma_prod_prod {X Y : Type} (P : X -> Type) (Q : Y -> Type) : {z : X * Y & (P (fst z)) * (Q (snd z))} <~> (sig P) * (sig Q) := ltac:`  (17 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_correct.v · proof#1 — `Definition equiv_sigma_symm `(P : A -> B -> Type) : {a : A & {b : B & P a b}} <~> {b : B & {a : A & P a b}}.`  (28 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_correct.v · proof#2 — `Definition equiv_sigma_symm' {A : Type} `(P : A -> Type) `(Q : A -> Type) : { ap : { a : A & P a } & Q ap.1 } <~> { aq : { a : A & Q a } & P aq.1 }.`  (33 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_correct.v · proof#3 — `Definition equiv_sigma_symm0 (A B : Type) : {a : A & B} <~> {b : B & A}.`  (8 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Interpreter_correct.v · proof#4 — `Global Instance isequiv_sig_ind `{P : A -> Type} (Q : sig P -> Type) : IsEquiv (sig_ind Q) | 0 := Build_IsEquiv _ _ (sig_ind Q) (fun f x y => f (x;y))`  (7 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Main.v · proof#0 — `Lemma implb_elim : forall b1 b2 : bool, implb b1 b2 = negb (b1 && negb b2).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Main.v · proof#1 — `Lemma varTripletTriplet1 : forall (p q r : rZ) (b : rBoolOp) (L : list triplet), In (Triplet b p q r) L -> In p (varTriplets L).`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Main.v · proof#2 — `Theorem eqStateInvInv : forall (S : State) (p q : rZ), eqStateRz S (rZComp p) (rZComp q) -> eqStateRz S p q.`  (18 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_classes.v · proof#0 — `Variant int : Type0 := Pos (d:uint) | Neg (d:uint).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_classes.v · proof#1 — `Variant hexadecimal : Type0 := | Hexadecimal (i:int) (f:uint) | HexadecimalExp (i:int) (f:uint) (e:Decimal.int).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_classes.v · proof#2 — `Fixpoint nb_digits d := match d with | Nil => O | D0 d | D1 d | D2 d | D3 d | D4 d | D5 d | D6 d | D7 d | D8 d | D9 d | Da d | Db d | Dc d | Dd d | De`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_classes.v · proof#3 — `Fixpoint nzhead d := match d with | D0 d => nzhead d | _ => d end.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_classes.v · proof#4 — `Definition unorm d := match nzhead d with | Nil => zero | d => d end.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_classes.v · proof#5 — `Definition norm d := match d with | Pos d => Pos (unorm d) | Neg d => match nzhead d with | Nil => Pos zero | d => Neg d end end.`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_classes.v · proof#6 — `Definition opp (d:int) := match d with | Pos d => Neg d | Neg d => Pos d end.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_complete.v · proof#0 — `Definition tail_mul n m := tail_addmul O n m.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_complete.v · proof#1 — `Fixpoint of_uint_acc (d:Decimal.uint)(acc:nat) := match d with | Decimal.Nil => acc | Decimal.D0 d => of_uint_acc d (tail_mul ten acc) | Decimal.D1 d `  (6 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_complete.v · proof#2 — `Definition of_uint (d:Decimal.uint) := of_uint_acc d O.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_complete.v · proof#3 — `Fixpoint of_hex_uint_acc (d:Hexadecimal.uint)(acc:nat) := match d with | Hexadecimal.Nil => acc | Hexadecimal.D0 d => of_hex_uint_acc d (tail_mul sixt`  (16 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_complete.v · proof#4 — `Definition of_num_uint (d:Numeral.uint) := match d with | Numeral.UIntDec d => of_uint d | Numeral.UIntHex d => of_hex_uint d end.`  (28 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_complete.v · proof#5 — `Fixpoint to_little_uint n acc := match n with | O => acc | S n => to_little_uint n (Decimal.Little.succ acc) end.`  (7 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_complete.v · proof#6 — `Definition trunc_index_inc'_succ (n : nat) (k : trunc_index) : trunc_index_inc' k.+1 n = (trunc_index_inc' k n).+1.`  (6 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_complete.v · proof#7 — `Definition nat_to_trunc_index (n : nat) : trunc_index := (trunc_index_inc minus_two n).+2.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_safe.v · proof#0 — `Global Instance decidable_arrow {A B : Type} `{Decidable A} `{Decidable B} : Decidable (A -> B).`  (9 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_safe.v · proof#1 — `Definition unpack_sigma `{P : A -> Type} (Q : sig P -> Type) (u : sig P) : Q (u.1; u.2) -> Q u := idmap.`  (10 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_safe.v · proof#2 — `Definition path_sigma_uncurried_contra {A : Type} (P : A -> Type) (u v : sig P) (pq : {p : u.1 = v.1 & u.2 = p^ # v.2}) : u = v := (path_sigma_uncurri`  (13 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_safe.v · proof#3 — `Definition path_sigma' {A : Type} (P : A -> Type) {x x' : A} {y : P x} {y' : P x'} (p : x = x') (q : p # y = y') : (x;y) = (x';y') := path_sigma P (x;`  (10 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_safe.v · proof#4 — `Definition eta_path_sigma_uncurried `{P : A -> Type} {u v : sig P} (p : u = v) : path_sigma_uncurried _ _ _ (p..1; p..2) = p.`  (11 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-MenhirLib-Validator_safe.v · proof#5 — `Definition eta_path_sigma `{P : A -> Type} {u v : sig P} (p : u = v) : path_sigma _ _ _ (p..1) (p..2) = p := eta_path_sigma_uncurried p.`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Archi.v · proof#0 — `Theorem implies_true : forall P, P ⟹ ⊤.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Archi.v · proof#1 — `Theorem Intersection_Union {A : Type} p q : Same_set A (Intersection A p q) (Complement A (Union A (Complement A p) (Complement A q))).`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Archi.v · proof#2 — `Theorem Excluded_Middle {A : Type} p : Same_set A (p ∪ Complement A p) (Full_set A).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Archi.v · proof#3 — `Corollary Complement_Full {A : Type} : Same_set A (Complement A (Full_set A)) (Empty_set A).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Op.v · proof#0 — `Lemma uniq_app_1 : uniq (E ++ F) -> uniq E.`  (11 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Op.v · proof#1 — `Lemma uniq_app_2 : uniq (E ++ F) -> uniq F.`  (11 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Op.v · proof#2 — `Lemma uniq_app_3 : uniq (E ++ F) -> disjoint E F.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Op.v · proof#3 — `Lemma uniq_app_4 : uniq E -> uniq F -> disjoint E F -> uniq (E ++ F).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Op.v · proof#4 — `Lemma uniq_app_iff : uniq (E ++ F) <-> uniq E /\ uniq F /\ disjoint E F.`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Op.v · proof#5 — `Lemma uniq_map_1 : uniq (map f E) -> uniq E.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Op.v · proof#6 — `Lemma uniq_map_2 : uniq E -> uniq (map f E).`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Op.v · proof#7 — `Lemma binds_cons_1 : binds x a ((y, b) :: E) -> (x = y /\ a = b) \/ binds x a E.`  (4 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Stacklayout.v · proof#0 — `Ltac check_hyp H := match H with _ => idtac end.`  (38 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 28: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 29: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Stacklayout.v · proof#1 — `Ltac check_equal H1 H2 := match H1 with H2 => idtac end.`  (20 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-aarch64-Stacklayout.v · proof#2 — `Ltac hdes := repeat match goal with | H : ?P |- _ => hdesF P; hdesHP H P end; unfold _HID_ in *.`  (20 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-arm-Archi.v · proof#0 — `Definition commutes (f : S -> S -> S) : Prop := forall x y : S, f x y [=] f y x.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-arm-Archi.v · proof#1 — `Definition CSetoid_un_op := CSetoid_fun S S.`  (5 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-arm-Archi.v · proof#2 — `Lemma id_pres_eq : un_op_wd (fun x : S => x).`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-arm-Archi.v · proof#3 — `Definition id_un_op := Build_CSetoid_un_op (fun x : S => x) id_strext.`  (3 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-arm-Stacklayout.v · proof#0 — `Theorem eq_dec_is_path_collaps : forall A : Type, DecidableEq A -> PathCollapsible A.`  (29 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 13: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 14: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 15: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 16: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 17: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 18: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 19: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 20: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 21: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 22: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 23: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 24: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 25: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 26: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 27: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-arm-Stacklayout.v · proof#1 — `Lemma loop_eq : forall A: Type, forall x y: A, forall p: x = y, eq_refl = (p^) @ p.`  (14 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 10: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 11: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 12: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))


## compcert-arm-Stacklayout.v · proof#2 — `Lemma loop_eq' : forall A: Type, forall x y: A, forall p: x = y, eq_refl = p @ (p^).`  (11 steps)

- step 1: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 2: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 3: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 4: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 5: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 6: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 7: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 8: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

- step 9: get_recs 실패 HTTPConnectionPool(host='172.17.0.3', port=45873): Max retries exceeded with url: / (Caused by NewConnectionError("HTTPConnection(host='172.17.0.3', port=45873): Failed to establish a new connection: [Errno 111] Connection refused"))

