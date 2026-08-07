# apply·eapply·rewrite·destruct는 왜 실패했나 — 실제 사례 모음 (lr3e-4 GRPO)

> ⚙️ **데이터**: 이전 GRPO(`tst1000tr5091_bc_lr3e-4_...`, b000~b039 롤아웃 36 gz)의 **INVALID(거부된) tactic** 실사례.
> ⚠️ **주의**: 이 롤아웃엔 `coq_error`가 없어(RECORD_ERROR 꺼져 있었음), 실패 사유는 **goal과 lemma 문장의 모양으로 추론**한 것이다(정확한 coq 메시지 아님). 앞으로 롤아웃은 `coq_error` 저장하니([[record-rollout-errors]]) 다음엔 실측 사유로 갱신 가능.
> 분류·통계 근거는 [[MIXED_FAILURE_ANALYSIS_lr3e-4]] 참조.

## 이 문서 읽는 법
- **GOAL** = proof state. `이름: 타입` 줄들 = 가설(hypotheses), 맨 아래 줄 = 증명할 목표(goal). (coq-lsp는 `⊢` 없이 마지막 줄이 goal.)
- **TACTIC** = 모델이 시도해서 **Coq이 거부한** tactic.
- **쓴 lemma / 그 문장** = 그 tactic이 넣은 lemma 이름과, 그게 **검색후보(50개)에 있었으면 그 lemma의 실제 문장**(타입). 문장이 보이면 goal과 대조해 왜 안 맞는지 알 수 있다.

## 한눈 요약 — tactic마다 "실패의 성격"이 다르다
| tactic | 인자 | 주 실패 메커니즘 |
|---|---|---|
| **apply / eapply** | lemma(또는 가설) | **lemma의 결론/전제 타입이 goal·가설과 안 맞음** (선택 실패) |
| **rewrite** | 등식 lemma | **lemma 좌변(LHS) 패턴이 goal에 그대로 안 나타남**(매칭 실패) |
| **destruct** | 항/가설 | **대상이 context에 없거나·귀납형이 아니거나·분해 패턴이 틀림** (lemma 선택 아님) |

즉 **apply/rewrite = "무슨 lemma를 넣나"의 실패**, **destruct = "무엇을·어떻게 쪼개나"의 실패**로 성격이 다르다.

---

# 1. `apply` / `eapply` — lemma 타입 불일치

`apply L`은 **L의 결론이 goal과 일치**해야(또는 `apply L in H`는 H가 L의 전제와 일치해야) 성공한다. 실패의 핵심은 **"그럴듯한데 타입이 미세하게 어긋난 lemma"**를 고르는 것.

## ⭐ 대표 패턴: FLX ↔ FLT 혼동 (부동소수점 포맷 헷갈림)
Flocq엔 **`FLX_exp`(고정정밀도)와 `FLT_exp`(정밀도+하한)** 라는 **비슷하게 생긴 두 지수함수**가 있다. lemma는 둘 중 하나에만 맞는데, 모델이 자주 뒤바꾼다.

**[apply #3] 결론은 맞는데 전제(가설) 타입이 FLX vs FLT로 어긋남**
```
GOAL(발췌):
  Hb: generic_format beta (FLX_exp prec) x     ← 가설은 FLX
  ⊢  generic_format beta FLT_exp x             ← 목표는 FLT
TACTIC:  apply generic_format_FLT in Hb.
쓴 lemma: generic_format_FLT
  = "forall x, FLT_format x -> generic_format beta FLT_exp x"
```
→ `apply ... in Hb`는 **Hb가 lemma의 전제(`FLT_format x`)여야** 하는데, Hb는 `generic_format beta (FLX_exp prec) x`(FLX). **FLT_format ≠ FLX generic_format → 타입 불일치로 거부.**

**[apply #5] 결론이 FLX인 lemma를 FLT goal에 적용**
```
GOAL: ⊢ generic_format beta FLT_exp x          ← FLT
TACTIC: apply generic_format_FLX with (emin:=emin)(prec:=prec)...
쓴 lemma: generic_format_FLX
  = "forall x, FLX_format x -> generic_format beta FLX_exp x"   ← 결론이 FLX
```
→ lemma **결론이 `generic_format beta FLX_exp x`**인데 goal은 `FLT_exp`. **FLX ≠ FLT → 결론이 goal과 안 맞아 거부.** (검색 3위에 있던 lemma를 골랐는데도 이 미세차이를 못 봄.)

**[apply #6] 결론이 상수 1에 대한 lemma를 일반 goal에 적용**
```
GOAL: ⊢ FLT_format x
TACTIC: apply generic_format_FLX_1 with emin.
쓴 lemma: generic_format_FLX_1 = "generic_format beta FLX_exp 1"   ← 오직 '1'에 대한 사실
```
→ lemma는 **특정 상수 `1`** 에 대한 사실. goal은 임의 `x`의 `FLT_format`. 완전히 다른 명제 → 거부. (이름이 `generic_format_FLX_...`라 그럴듯해 고른 것.)

**[apply #7] 결론은 goal과 일치하나 전제를 충족할 가설이 없음**
```
GOAL:
  H0: generic_format beta (FLX_exp prec) x     ← FLX 가설뿐
  ⊢  FLT_format x
TACTIC: apply FLT_format_generic; assumption.
쓴 lemma: FLT_format_generic
  = "forall x, generic_format beta FLT_exp x -> FLT_format x"
```
→ 결론(`FLT_format x`)은 goal과 **맞다**. 하지만 apply 후 남는 전제 `generic_format beta FLT_exp x`(FLT)를 `assumption`으로 닫으려는데, **가설엔 FLX(`FLX_exp`)뿐** → 못 닫아 실패. **"결론만 보고 골랐다가 전제에서 막히는"** 전형.

## 조합형 이름 창작 (없는 lemma를 지어냄)
검색후보에도 사전에도 없는 이름 — 실존 조각을 조합해 지어낸 것.
```
[apply #4]  apply generic_format_generic_format_inversion with (1:=Hx0).
            → 'generic_format' 접두어 중복 조합. 없는 이름.
[apply #8]  apply generic_format_generic.       → 마찬가지로 존재하지 않음.
[apply #1]  apply Zle_0_eq in H.  (H: Z.pos p <= 0)  → 'Zle_0_eq' 없음(Z.le_0_eq 오기 가능).
[eapply #7~9] getv_rule / mem_update_1 / getv_spec → 그럴듯한 이름 연쇄 창작.
```
→ **존재하지 않는 이름이라 "reference not found"로 거부**(타입 이전에 이름부터 없음).

## 실존이나 검색 안 된 lemma를 기억서 꺼냄 (off-book)
```
[eapply #11~13]  eapply Mem.loadbytes_store_same / Mem.load_unchanged_on ...
   GOAL: Mem.loadbytes m' b i 1 = Some (Byte Byte.zero :: nil)
   → 다 CompCert 실존 Mem lemma지만 그 step의 검색후보 50개엔 없었음.
     이름은 실존이라 "not found"는 아닐 수 있으나, 이 goal엔 타입/전제가 안 맞아 거부.
[eapply #3]  eapply Zle_trans; eauto.  (⊢ unsigned x <= unsigned y)
   → Zle_trans(추이성)는 실존이나 '중간항'을 eauto가 못 찾아 실패.
```

## eapply 특유: 귀납가설(IH) 인자 순서 어긋남
```
[eapply #2]
  IHreachable: code!n0=Some i -> In n3 (successors i) -> reachable n2 n3   ← 결론 reachable n2 n3
  ⊢ reachable n3 n2                                                        ← 목표는 n3 n2 (순서 반대!)
TACTIC: eapply IHreachable; eauto.
```
→ IH의 결론은 `reachable n2 n3`인데 goal은 `reachable n3 n2` — **인자 순서가 뒤집혀** unify 실패.

---

# 2. `rewrite` — lemma 좌변 패턴이 goal에 안 나타남

`rewrite L`은 **L이 등식(`A = B`)** 이고 **goal에 `A`(좌변) 모양이 실제로 있어야** 그걸 `B`로 바꾼다. 실패의 핵심은 **좌변 패턴이 goal에 (그 형태로) 없음**.

**[rewrite #7] `combine_l`을 찾는데 goal엔 `combine`만 있음**
```
GOAL(발췌): ⊢ get i (combine Empty (Node l o ...)) = ...
TACTIC: rewrite gcombine_l, gcombine_r.
쓴 lemma: gcombine_l = "get i (combine_l m) = f (get i m) None"
```
→ lemma 좌변은 **`get i (combine_l m)`** (인자 1개짜리 `combine_l`). 하지만 goal엔 **`combine Empty ...`**(인자 2개짜리 일반 `combine`)만 있다. **`combine_l` 형태가 goal에 없어 → 바꿀 대상 못 찾아 거부.** (`combine` vs `combine_l` — 이름·타입이 비슷해 헷갈림.)

**[rewrite #9] 같은 혼동, 더 명확**
```
GOAL: ⊢ get i (combine m1 m2) = f (Some a) (Some b)
TACTIC: rewrite gcombine_l.
쓴 lemma: gcombine_l = "get i (combine_l m) = ..."
```
→ goal은 `combine m1 m2`(2-인자), lemma 좌변은 `combine_l m`(1-인자). **매칭 안 됨.**

**[rewrite #10~13] map_filter1 / filter1 계열도 좌변 함수가 goal에 없음**
```
GOAL: ⊢ get i (match m1 with Empty => ... | Nodes a' => ...) = ...   ← match 식
TACTIC: rewrite gmap_filter1.  (좌변: get i (map_filter1 f m))
      / rewrite gfilter1.      (좌변: get i (filter1 pred m))
```
→ goal의 피연산자는 `match m1 ...`(아직 안 펼쳐진 정의)라 `map_filter1`/`filter1` 형태가 **표면에 안 드러남** → 좌변 매칭 실패. (먼저 `simpl`/`unfold`로 펼쳤어야.)

## rewrite도 없는 이름 창작
```
[rewrite #2~4]  rewrite Z.iter_base / Z.iter_small / Z.iter_forall
   GOAL: Z.iter (Zshiftin b x0) f x = x
   → 'Z.iter_base' 등은 없는 이름(Z.iter에 _base/_small/_forall 접미어 창작).
[rewrite #1]  rewrite <- (Zshiftin_pos_base b).   → 'Zshiftin_pos_base' 없음.
```

---

# 3. `destruct` — 대상·패턴 문제 (lemma 선택 아님)

`destruct t`는 **t를 경우로 쪼갠다**. 실패는 lemma가 아니라 **(a) t가 context에 없거나 (b) t가 귀납형이 아니거나 (c) 분해 패턴이 t의 생성자 수와 안 맞음**.

**[destruct #6] 생성자 수 안 맞는 패턴 — `int`는 record인데 2-분기 패턴**
```
GOAL:  x, y: int   ⊢ unsigned x <= unsigned y
TACTIC: destruct x as [|x].
```
→ `[|x]`는 **생성자 2개짜리**(nat의 O/S, list의 nil/cons 같은) 패턴. 그런데 `int`(Integers.int)는 **생성자 1개짜리 record**(`{intval; intrange}`). **패턴 분기 수 불일치 → 거부.** (`destruct x as [v r]`처럼 1-생성자 패턴이어야.)

**[destruct #1] 귀납형 아닌 것을 destruct — 추상 타입 `A`**
```
GOAL:  A: Type   f: A -> A   x: A   ⊢ Pos.iter f x p = x
TACTIC: destruct (Z.iter 0 f x).
```
→ `Z.iter 0 f x`의 타입은 **추상 타입 `A`**(임의 Type). **A는 생성자를 모르는 타입**이라 경우 분해 불가 → 거부.

**[destruct #7] 존재하지 않는 대상 — `unsignedy`(오타)**
```
GOAL:  x, y: int  (context에 'unsignedy' 없음)
TACTIC: destruct x, y, unsignedy.
```
→ `unsignedy`는 context에 **없는 이름**(아마 `unsigned y`의 오타). **없는 대상 destruct → 거부.**

**[destruct #14] 분해 패턴이 대상 구조와 안 맞음**
```
GOAL:  H: integer_representable p   ⊢ Bminus ... = BofZ (p - q)
TACTIC: destruct H as (A & B & C).
```
→ `(A & B & C)`는 **3-요소 곱(∧∧ 또는 ∃∃)** 분해 패턴. `integer_representable p`가 그 구조(3-way conjunction)가 **아니면** 패턴 불일치 → 거부. (구조를 잘못 가정.)

**[destruct #4] 대상은 맞으나 뒤 체인이 깨짐**
```
GOAL:  ofs: Z   ⊢ ofs <= size_callee_save_area {| ... |}
TACTIC: destruct ofs; simpl; rewrite Pos2Z.inj_nle; auto with zarith.
```
→ `destruct ofs`(Z는 0/pos/neg로 분해 가능) 자체는 되지만, 이어지는 `rewrite Pos2Z.inj_nle`의 좌변이 그 분기 goal에 없어 **체인 전체가 INVALID**. (destruct 성격보다 rewrite 문제가 섞인 케이스.)

> 참고: destruct가 **성공하는** 정상 사례도 많다(예: `destruct q`(q: EqSet.elt), `destruct oid`(option ident) — 생성자 아는 귀납형이라 OK). 실패는 위 (a)~(c) 조건에 걸릴 때만.

---

# 4. 종합 — tactic별 실패 메커니즘 표

| tactic | 실패 유형 | 예시 | 근본 |
|---|---|---|---|
| apply | 결론이 goal과 다름(FLX≠FLT) | #5,#9 | 타입 선택 |
| apply | 전제(가설)가 lemma 전제와 다름 | #3,#10 | 타입 선택 |
| apply | 결론 맞으나 전제 못 닫음 | #7 | 타입 선택(2차) |
| apply/eapply | 없는 이름 창작 | #4,#8 / e#7~9 | 이름 생성 |
| apply/eapply | 실존이나 미검색/타입 안 맞음 | e#11~13 | 검색+타입 |
| eapply | IH 인자 순서 뒤바뀜 | e#2 | unify |
| rewrite | 좌변 함수가 goal에 없음(combine≠combine_l) | #7,#9 | 패턴 매칭 |
| rewrite | 정의 안 펼쳐져 좌변 안 보임(match식) | #10~13 | 패턴 매칭 |
| rewrite | 없는 이름 창작 | #1~4 | 이름 생성 |
| destruct | 생성자 수 안 맞는 패턴(int=record) | #6 | 구조 |
| destruct | 귀납형 아님(추상 A) | #1 | 구조 |
| destruct | 없는 대상(오타) | #7 | 참조 |
| destruct | 분해 패턴 구조 오판 | #14 | 구조 |

## 큰 그림
- **apply/eapply/rewrite = 선택/타입/패턴** 문제. 특히 **"비슷하게 생긴 것 혼동"**(FLX↔FLT, combine↔combine_l, Z.iter에 없는 접미어)이 반복 — **타입 정합을 세밀히 못 봄**.
- **destruct = 구조/참조** 문제(귀납형 여부·생성자 수·대상 존재). lemma 선택과 성격이 다르다.
- 처방 연결: apply/rewrite의 타입 선택 실패 → [[TYPE_LEARNING_RESEARCH]] 방향 A(타입 hard-neg retriever: FLX/FLT·combine/combine_l 구분 학습) + B(type-check process reward). destruct의 구조 실패는 goal 타입 정보(귀납형/생성자) 주입이 도움([[../grpo/rango_augmented/AUGMENTED_FINAL]] [TYPES]).

관련: [[MIXED_FAILURE_ANALYSIS_lr3e-4]] · [[TYPE_LEARNING_RESEARCH]] · [[record-rollout-errors]] · [[../grpo/rango_augmented/AUGMENTED_FINAL]]
