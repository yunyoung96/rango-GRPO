# Π-바인더 — `forall` 과 `->` 는 같은 것이다

## 1. 하나의 구성자

Coq 커널에는 `Prod(x : A, B)` 하나뿐이다. 표기만 둘로 갈린다.

```
Prod(x : A, B)
   │
   ├─ B 가 x 를 쓴다     →  의존(dependent)    →  `forall x : A, B`
   └─ B 가 x 를 안 쓴다   →  비의존             →  `A -> B`
```

```coq
forall n : nat, n + 0 = n      Prod(n : nat, n + 0 = n)      n 을 쓴다 → 의존
nat -> bool                     Prod(_ : nat, bool)           안 쓴다   → 화살표
```

**같은 노드다.** `->` 는 "바인더를 안 쓰는 `forall`" 의 표기법일 뿐이다.

코드에서 가르는 법:

```ocaml
EConstr.Vars.noccurn sigma 1 b     (* b 가 1번 de Bruijn(=그 바인더)을 안 쓰나 *)
```

→ [`noccurn`](../terminology/noccurn.md) · [`sigma`](../terminology/sigma.md) ·
[`de Bruijn`](../terminology/de-bruijn.md)

---

## 2. lemma 는 Π 의 사슬이다

```coq
PTree.gso : forall (A : Type) (i j : positive) (x : A) (m : PTree.tree A),
              i <> j -> PTree.get i (PTree.set j x m) = PTree.get i m
```

커널에서는:

```
Prod(A : Type,
  Prod(i : positive,
    Prod(j : positive,
      Prod(x : A,
        Prod(m : tree A,
          Prod(_ : i <> j,                    ← 비의존 = 전제
            get i (set j x m) = get i m ))))))   ← 결론
```

```
깊이  0 ─ forall A          의존   (암묵 인자)
      1 ─ forall i          의존
      2 ─ forall j          의존
      3 ─ forall x          의존
      4 ─ forall m          의존
      5 ─ i <> j ->         비의존  ← 진짜 "전제"
      6 ─ 결론
```

---

## 3. 왜 이게 중요한가 — 셋

### ① `apply` 는 Π 를 벗긴다

`apply L` 은 `L` 의 결론을 goal 과 맞춘다. 그런데 **몇 개를 벗겨야 결론인지 모른다.**

```
x -> y -> z
   z         로도 맞을 수 있고
   y -> z    로도 맞을 수 있고
   x -> y -> z  통째로도 맞을 수 있다
```

그래서 **모든 화살표 접미사**를 본다. 벗길 때 그 자리에 evar 를 넣는다 — `eapply` 가 하는 일이다.

```
descend(ty, d)  =  d 개 벗기고 evar 로 채운 것
```

**코드**: [`applic_main.ml:345` `descend`](../../../../ocaml/applic/applic_main.ml) ·
[`:388` `unifies_upto`](../../../../ocaml/applic/applic_main.ml)

### ② 암묵 인자도 바인더로 센다 — `max_arrows` 함정

`{A}` 처럼 사용자가 안 쓰는 인자도 커널에서는 똑같은 `Prod` 다.

```
forall {A} {B} (x y z : T) (H1 H2 : P), … -> concl
       └───── 6개가 결론 전에 있다 ─────┘
```

`max_arrows = 8` 로는 부족하다. 실측:

| max_arrows | gold 생존 |
|---|---|
| 4 | 65.4% |
| 8 | 88.8% |
| **12** | **92.5%** |
| 20 | 93.5% |

→ 20 으로 올렸다. [../versions/r6.md](../versions/r6.md)

#### 실제로 20개가 필요한 건 무엇인가 — 실측

107 지점 중 **8보다 큰 값이 필요한 건 5개뿐**이다. 꼬리가 길 뿐이다.

```
처음 살아나는 arrows 값        지점
   4  ██████████████████████████████████████  70
   8  █████████████                           25
  12  ██                                       4
  20  █                                        1
  ✗   ████                                     7  (끝까지 실패)
```

그 **1개**를 직접 열어 봤다 — CompCert `match_stacks_inside_invariant`.
소스에서 사용자가 쓴 건 이것뿐이다:

```coq
Section MATCH_STACKS.
Variable F: meminj.  Variables m m': mem.
Variable F1: meminj. Variables m1 m1': mem.
Hypothesis INCR: inject_incr F F1.
…
Lemma match_stacks_inside_invariant:
  forall stk stk' f' ctx sp' rs1,          (* 6개 *)
  match_stacks_inside F m m' stk … rs1 ->  (* 1개 *)
  forall rs2 (RS: …) (INJ: …) (PERM1: …) (PERM2: …) (PERM3: …),   (* 6개 *)
  match_stacks_inside F1 m1 m1' stk stk' f' ctx sp' rs2.
```

눈으로 세면 **13개**다. 그런데 Coq 에게 물어보면:

```
Arguments match_stacks_inside_invariant
  prog F m m' F1 m1 m1' INCR   stk stk' f' ctx sp' rs1 _ rs2   RS INJ PERM1 PERM2 PERM3
  └──── Section 변수 8개 ────┘  └────── 사용자가 쓴 13개 ──────┘
                                                              = 모두 21개
```

**범인은 Section 변수 방출(discharge)이다.**

```
   Section 안에서 보이는 것            Section 이 닫힌 뒤 커널이 보는 것
   ───────────────────────────    ─────────────────────────────────
   Lemma L : forall a b c, …      Lemma L : forall prog F m m' F1 m1 m1' INCR,
                                              forall a b c, …
                                              ▲
                                    Section 이 쓰던 변수·가설이
                                    **전부 앞에 붙는다**
```

CompCert 은 큰 `Section` 을 쓴다. `Inliningproof.v` 의 `Section INLINING`
안에 `Section MATCH_STACKS` 가 또 있고, 그 안의 lemma 는 **바깥 Section
변수까지 전부** 짊어진다. 사용자가 `apply match_stacks_inside_invariant` 라고
쓸 때 그 8개는 통일화가 알아서 채우므로 **보이지 않는다.**

정리하면 화살표를 크게 잡아야 하는 이유는 셋이다:

| | |
|---|---|
| **Section 변수 방출** | 8개 추가. CompCert·mathcomp 처럼 Section 을 많이 쓰는 코드베이스에서 크다 |
| **암묵 인자** `{A}` | 사용자가 안 쓰지만 커널에는 `Prod` |
| **이름 붙은 전제** `(RS: …)` | 문법은 바인더지만 뜻은 전제 |

> 비용은 싸다. `max_arrows` 는 **탐색 상한**일 뿐 20번 다 시도하지 않는다 —
> 결론이 맞는 순간 멈춘다. 4→20 으로 올렸을 때 지점당 초는 거의 안 변했다.

### ③ `apply L in H` 는 **비의존** 전제를 본다

Coq 매뉴얼: *"non-dependent premise 를 오른쪽부터 맞춘다."*

```
PTree.gso 의 첫 Prod 는 `A : Type` 이다 — 의존이고, 가설이 아니다.
비의존인 것은 깊이 5 의 `i <> j` 하나뿐이다.
```

첫 `Prod` 만 보면 `A : Type` 을 전제로 착각한다. 실측으로 걸렸다.
[../versions/r4.md](../versions/r4.md)

---

## 4. 판별트리에서의 Π

`Btermdn` 은 `Prod` 에 **고유 라벨**을 준다:

```ocaml
| Prod (n, d, c) -> Label(ProdLabel, [d; c])
```

즉 `A -> B` 는 `ProdLabel` 아래 자식 둘(`A`, `B`)로 갈린다.

**우리 쪽 함정**: `suffix_compat` 의 값싼 선별에서 `decompose_app` 을 썼는데,
`Prod` 는 적용이 아니라 자기 자신이 머리로 나온다. 그걸 "유연" 으로 분류해
**모든 후보가 선별을 통과**했다(11,222/11,766 = 95%). 깊이 0 에서는 거의 모든
lemma 가 `forall …` 이기 때문이다.

`Prod` 에 고유 라벨을 주고서야 선별이 12,652 → 4,812 로 들었다.
[../versions/r6.md](../versions/r6.md)

---

## 5. 용어 정리

| | |
|---|---|
| **Π-타입** | 의존 함수 타입. `forall x : A, B(x)` |
| **바인더** | `x : A` 부분. 이름과 타입 |
| **de Bruijn 인덱스** | 커널은 이름 대신 번호를 쓴다. `Rel 1` = 가장 가까운 바인더 |
| **닫힌 항** | 자유 de Bruijn 이 없다 (`Vars.closed0`). 바깥 문맥에서 뜻이 있다 |
| **evar** | 미지수. 바인더를 벗길 때 그 자리에 넣는다 |
| **의존 / 비의존** | 몸통이 그 바인더를 쓰나 / 안 쓰나 |
