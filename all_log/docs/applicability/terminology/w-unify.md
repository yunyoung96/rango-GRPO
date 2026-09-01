# `w_unify` — 단일화 (필터의 최종 판정기)

```ocaml
Unification.w_unify :
  env -> evar_map -> conv_pb -> ?flags:unify_flags -> constr -> constr -> evar_map
```

두 항을 **같게 만드는 치환**을 찾는다. 성공하면 갱신된 [[sigma]], 실패하면 예외.
판별트리는 **상한**만 주고, 실제로 적용 가능한지는 **이것이 정한다.**

---

## 0. 개괄 — 어디에 있는 부품인가

```
   ┌─────────────────────────────────────────────────────────┐
   │  판별트리 lookup      12,652 → 34,461개 (구문, 과대근사)  │  빠름 (ms)
   │        ↓  suffix_compat  값싼 머리-라벨 선별              │
   │                        →  5,821개                        │
   │        ↓  ★ w_unify      커널 단일화                     │  느림 (μs×N)
   │                        →    596개  (의미, 정확)          │
   └─────────────────────────────────────────────────────────┘
```

- 트리를 먼저 쓰는 이유: `w_unify` 는 후보 하나당 수십~수백 μs 다.
  12,652개에 다 돌리면 지점당 초 단위가 된다.
- 트리만 쓰면 안 되는 이유: 트리는 **구문**만 본다. `2+2` 와 `4` 를 다르게 본다.

**트리 → `w_unify`** 순서만 건전하다. 뒤집으면 느려서 못 쓰고, 트리만 쓰면 오탐이 남는다.
→ [../concepts/limits.md](../concepts/limits.md)

### 이름의 `w`

Coq 역사에서 온 접두사다(`Wcclausenv`/"workaround" 계열의 잔재).
지금은 **"전술 층 단일화"** 로 읽으면 된다. 커널의 변환 검사(`Conversion`)와는 다른 층이다.

---

## 1. 무엇을 하나

```
   a = PTree.get ?i (PTree.set ?j ?x ?m) = PTree.get ?i ?m      ← concl(lemma)
   b = PTree.get i  (PTree.set j  x  m)  = PTree.get i  m       ← goal

   w_unify a b   →   sigma' = { ?i↦i, ?j↦j, ?x↦x, ?m↦m }
```

```
   성공 = "이 lemma 의 결론이 이 goal 이 될 수 있다"  =  apply 가 통한다
   실패 = 예외
```

### ★ 결과를 버리면 안 된다

```ocaml
let sg' = Unification.w_unify env sg Conversion.CONV a b in
(* ← 여기부터 sg 가 아니라 sg' 를 써야 한다 *)
```

우리는 이걸로 실제 버그를 냈다 — `depth_of` 가 `new_evar` 로 만든 sigma 를 버리고
바깥 sigma 로 재귀해서 `Anomaly "in retyping: Unknown evar"`.
→ [sigma.md](sigma.md) · [../versions/r5.md](../versions/r5.md)

---

## 2. `conv_pb` — 어떤 "같음" 인가

```
   Conversion.CONV     a 와 b 가 같아야 한다              (우리가 쓰는 것)
   Conversion.CUMUL    a 가 b 의 부분형이면 된다 (Type_i ≤ Type_j)
```

우주(universe) 포함관계까지 허용할지의 차이다. 우리는 `CONV` 를 쓴다 —
`apply` 판정에는 정확한 일치가 맞고, `CUMUL` 은 더 느슨해서 오탐이 는다.

---

## 3. `flags` — 여기가 진짜 중요하다

`w_unify` 는 **플래그에 따라 완전히 다른 함수**가 된다.

```ocaml
type core_unify_flags = {
  modulo_conv_on_closed_terms : TransparentState.t option;   (* 닫힌 항끼리 변환 허용? *)
  modulo_delta                : TransparentState.t;          (* 어느 상수를 펼치나 *)
  modulo_delta_types          : TransparentState.t;
  modulo_betaiota             : bool;                        (* β·ι 환원 허용? *)
  modulo_eta                  : bool;
  use_pattern_unification     : bool;                        (* ?P x = t 를 푸나 *)
  check_applied_meta_types    : bool;
  … }
```

### 우리는 `apply` 가 쓰는 것과 **같은 플래그**를 쓴다

```ocaml
let unify_ap env sigma a b =
  try let _ = Unification.w_unify env sigma Conversion.CONV
      ~flags:(Unification.elim_flags ()) a b in true
  with e when CErrors.noncritical e -> false
```

**우리가 고른 게 아니다.** `apply`/`elim` 이 쓰는 그대로여야 판정이 실제 전술과 같아진다.
그래서 정밀도가 나온다 — apply **96.9%**, apply…in **99.8%**.

### 기본값을 쓰면 무슨 일이 나나 — 실측

Coq 소스에서 둘의 차이는 **딱 한 줄**이다.

```ocaml
let default_unify_flags () = { …
  allow_K_in_toplevel_higher_order_unification = false; (* Why not? *)   ← Coq 자신의 주석
  … }

let elim_flags_evars sigma = { …
  allow_K_in_toplevel_higher_order_unification = true;                   ← 이것
  subterm_unify_flags = { flags with modulo_delta = TransparentState.empty };
  … }
```

이 플래그가 **이차 패턴** `?P ?n` 을 풀 수 있는지를 정한다.

```
   귀납원리    N.binary_ind : forall (P : N -> Prop), … -> forall n, P n
                                                                 ▲
                                              goal 과 맞추려면 ?P 를 **함수로** 찍어야 한다

   default 플래그  →  ?P ?n 을 못 푼다  →  귀납원리·Morphism 을 통째로 놓친다
   elim_flags     →  푼다
```

**실측 위음성 7.0%** 가 이 한 줄에서 나왔다. `N.binary_ind`,
`Equivalence.equiv_symmetric` 부류가 전부 사라졌었다.

### 플래그 세 벌을 나눠 쓴다

```
   core_unify_flags       t(?x) = u(?x)  꼴의 본 문제
   merge_unify_flags      같은 메타가 여러 번 나올 때 합치기
   subterm_unify_flags    ?X a₁…aₙ = u  꼴 (rewrite·elim 이 쓴다)
                          ▲ elim_flags 는 여기만 modulo_delta = empty (경직)
```

`apply` 는 상수를 펼쳐 가며 맞추지만, **부분항 찾기는 경직**으로 한다.
이게 다음 절과 이어진다.

---

## 4. 우리 코드의 두 갈래

```ocaml
let unify_ap env sigma a b =                              (* apply 계열 *)
  … ~flags:(Unification.elim_flags ()) …

let unify1 env sigma a b =                                (* rewrite·destruct·decide *)
  … Unification.w_unify env sigma Conversion.CONV a b …   (* 기본 플래그 *)
```

| | 쓰는 곳 | 플래그 | 왜 |
|---|---|---|---|
| `unify_ap` | apply · apply…in · concl_parts | `elim_flags` | 이차 패턴을 풀어야 한다 |
| `unify1` | rewrite redex · decide · descend | 기본 | redex 매칭은 일차면 충분 |

### rewrite 는 `unify1` 만으로 부족하다 — 조건 셋

```ocaml
let keyed sg d st =
     same_head sg d st                                  (* ① keyed matching *)
  && unify1 env sg d st                                 (* ② 커널 단일화   *)
  && (not !type_check_rw || abstract_ok env sg concl0 st)  (* ③ 추상화 타입검사 *)
```

```
   ①  머리가 delta 없이 맞나
       Coq 8.5+ 의 keyed unification 규칙. `w_unify` 는 delta 를 허용하므로
       우리가 따로 확인한다.            → 거짓양성 28.7% 의 자리
       [[keyed-unification]]

   ②  w_unify — 인자는 환원까지 써서 맞춘다

   ③  redex 를 λx.C[x] 로 뽑았을 때 타입이 맞나
       의존 자리면 rewrite 가 실패한다.  → 거짓양성 35.8% 의 자리
       Termops.subst_term → Typing.type_of
```

**셋을 다 봐야 실제 `rewrite` 와 같아진다.** 그래도 rewrite 정밀도는 64.5% 로
apply(96.9%)보다 낮다 — setoid 관계의 A/B 귀속이 남은 원인이다.

---

## 5. 비슷한 것들과 뭐가 다른가

| | evar 를 정하나 | 결과 | 쓰는 곳 |
|---|---|---|---|
| **`w_unify`** | **정한다** | 새 sigma | apply/rewrite 판정 |
| `Reductionops.is_conv` | 못 정한다 | `bool` | 이미 닫힌 두 항 비교 |
| `Evarconv.unify` | 정한다 | sigma | elaboration 층(더 완전, 더 느림) |
| `Constr.equal` | — | `bool` | 구문 동일성만 |
| 판별트리 `lookup` | — | 후보 목록 | **상한** |

```
   Constr.equal   ──  구문만            2+2 ≠ 4
   is_conv        ──  변환 포함         2+2 = 4      evar 없음
   w_unify        ──  변환 + evar 결정   ?n+2 = 4  →  ?n↦2
   판별트리        ──  구문 상한          빠르지만 과대근사
```

---

## 6. 비용

```
   후보 1개당      수십 ~ 수백 μs      (항 크기·delta 깊이에 따라)
   지점당 5,821개  →  0.3 ~ 0.6 초     (실측 sec=0.31~0.54)
```

- `w_unify` 는 **실패도 비싸다** — 실패하려면 다 해 봐야 한다.
- 그래서 `suffix_compat`(값싼 머리 비교)로 먼저 12,652 → 4,812 로 줄인다.
- 예외 잡기(`with e when CErrors.noncritical e`)를 제어 흐름으로 쓴다.
  OCaml 예외는 싸지만 **`noncritical` 을 빼면 안 된다** — `Stack_overflow` 같은
  치명적 예외까지 삼켜 조용히 틀린 답이 된다.

---

## 코드

`ocaml/applic/applic_main.ml` — `unify_ap`(333) · `unify1`(338) ·
`descend`(345) · `unifies_upto`(388) · `keyed`(870)

## 관련

[[sigma]] · [[evar]] · [[transparent-state]] · [[keyed-unification]] ·
[[delta-reduction]] · [[econstr]]
