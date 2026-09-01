# Prod / Lambda / App — 커널의 항 모양

`Constr.kind` 이 돌려주는 것들. 우리가 실제로 가르는 것만.

```ocaml
| Prod (x, A, B)     forall x:A, B   또는   A -> B      ← 타입
| Lambda (x, A, b)   fun x:A => b                       ← 함수
| App (f, [|a;b|])   f a b                              ← 적용
| Const (c, u)       정의된 상수  (PTree.get, plus …)
| Ind (i, u)         귀납형       (nat, list, and, or …)
| Construct (k, u)   생성자       (O, S, cons, conj …)
| Var id             지역 가설 이름
| Rel n              de Bruijn                          ← [[de-bruijn]]
| Evar (e, args)     미지수                              ← [[evar]]
| Sort s             Prop / Set / Type
| Case / Fix / CoFix / Proj / LetIn / Cast
```

## 헷갈리기 쉬운 것 셋

1. **`Prod` 는 타입, `Lambda` 는 값.** `A -> B` 는 `Prod` 다. → [../concepts/pi-binder.md](../concepts/pi-binder.md)
2. **`iff` 는 `Ind` 가 아니라 `Const` 다.** `Definition iff A B := (A->B)/\(B->A)`.
   귀납형인 줄 알고 `Ind` 만 보다가 `apply Liff` 를 놓쳤다. → [../versions/r7.md](../versions/r7.md)
3. **`App` 은 평평하다.** `f a b` 는 `App(f,[|a;b|])` 이지 `App(App(f,a),b)` 가 아니다.
   `decompose_app` 이 머리와 인자열로 갈라 준다.

## 관련

[[noccurn]] · [[econstr]]
