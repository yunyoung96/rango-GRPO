# rango-augmented 실제 프롬프트 예시 (2026-08-02)

`scripts/render_augmented_examples.py`가 **실제 ProofPremiseCollator**로 렌더한 것.
train split(goldsft_bs2 = CompCert train gold)에서 apply/destruct 예시 선별.
정제 인덱스(ind_constructors_clean) + 키워드필터 적용본.

**읽는 법**: base=현재 프롬프트, rerank=재랭킹 적용, [TYPES]/[DECIDERS]=추가할 구조섹션,
'위치'=gold lemma가 [PREMISES] 블록 몇째줄(아래=state근접=recency 유리).

```
==============================================================================
[TRAIN] want=apply | gold tactic: rewrite pred_0, succ_opp, pred_ulp_0.
  base 토큰 1593 | rerank 토큰 1592
  [TYPES](0tok): (none)
  [DECIDERS](12tok): pred: pred_spec || succ: succ_spec
  gold lemma 'pred_0' 위치 — base: 9/17줄 (state에서 먼→위)
                        rerank: 블록에 없음(truncation됨?)
  --- augmented 프롬프트 (앞 900자) ---
  
  [PREMISES]
  Lemma mag_div : forall x y : R, x <> 0%R -> y <> 0%R -> (mag x - mag y <= mag (x / y) <= mag x - mag y + 1)%Z.
  Lemma cexp_le_bpow : forall (x : R) (e : Z), x <> 0%R -> (Rabs x < bpow e)%R -> (cexp x <= fexp e)%Z.
  Theorem pred_le_id : forall x, (pred x <= x)%R.
  Theorem pred_plus_ulp : forall x, (0 < x)%R -> F x -> (pred x + ulp (pred x))%R = x.
  Theorem succ_ge_id : forall x, (x <= succ x)%R.
  Theorem generic_format_pred : forall x, F x -> F (pred x).
  Theorem eq_0_F2R : forall m e : Z, F2R (Float beta m e) = 0%R -> m = Z0.
  Theorem canonical_0 : canonical (Float beta 0 (fexp (mag beta 0%R))).
  Theorem pred_0 : pred 0 = Ropp (ulp 0).
  Theorem generic_format_succ : forall x, F x -> F (succ x).
  Lemma succ_pred_pos : forall x, F x -> (0 < x)%R -> succ (pred x) = x.
  Lemma pred_succ_pos : forall x, F x -> (0 < x)%R -> pred (succ x) = x.
  Theorem pred_ulp_0 : pred (ulp 0) = 0%R.
  Lemma roun
==============================================================================
[TRAIN] want=apply | gold tactic: rewrite dests_disjoint_sym.
  base 토큰 1683 | rerank 토큰 1661
  [TYPES](6tok): list := nil | cons
  [DECIDERS](13tok): In: In_dec || m1: Equal_dec
  gold lemma 'dests_disjoint_sym' 위치 — base: 10/11줄 (state에 가까움→아래=recency)
                        rerank: 9/10줄 (state에 가까움→아래=recency)
  --- augmented 프롬프트 (앞 900자) ---
  
  [PREMISES]
  Lemma srcs_dests_combine: forall s d, List.length s = List.length d -> srcs (List.combine s d) = s /\ dests (List.combine s d) = d.
  Lemma in_cns: forall (A: Type) (x y: A) (l: list A), In x (y :: l) <-> y = x \/ In x l.
  Lemma in_app: forall (A: Type) (x: A) (l1 l2: list A), In x (l1 ++ l2) <-> In x l1 \/ In x l2.
  Lemma list_norepet_app: forall (A: Type) (l1 l2: list A), list_norepet (l1 ++ l2) <-> list_norepet l1 /\ list_norepet l2 /\ list_disjoint l1 l2.
  Lemma list_disjoint_notin: forall (A: Type) (l1 l2: list A) (a: A), list_disjoint l1 l2 -> In a l1 -> ~(In a l2).
  Lemma dests_decomp: forall m1 s d m2, dests (m1 ++ (s, d) :: m2) = dests m1 ++ d :: dests m2.
  Lemma Plt_strict: forall p, ~ Plt p p.
  Lemma dests_append: forall m1 m2, dests (m1 ++ m2) = dests m1 ++ dests m2.
  Lemma dests_disjoint_cons_left: forall m1 s d m2, dests_disjoint ((s, d) :: m1) m2 <-> dests_disjoint m1 m
```
