# TransparentState — 어느 상수를 펼칠까

```ocaml
type t = { tr_var : Id.Pred.t ; tr_cst : Cpred.t }
```

**펼쳐도 되는(투명한) 상수·변수의 집합.** `δ-환원`을 어디까지 허용할지 정한다.

```
TransparentState.empty   아무것도 안 편다 (전부 경직 rigid)
TransparentState.full    전부 편다
```

## 판별트리에서의 효과 — 이분법이 아니다

`btermdn` 은 `ts : TransparentState.t option` 을 받는다.

| `ts` | 상수를 만나면 | 결과 |
|---|---|---|
| `None` | 전부 펼 수 있다고 봄 → `Everything` | **트리가 안 거른다** |
| `Some empty` | 아무것도 못 폄 → `Label` | **최대 판별력** |
| `Some {f}` | `f` 만 `Everything` | 그 하나만 느슨 |

실측:

| | raw 후보 | 시간 |
|---|---|---|
| `Some empty` | 29,381 | 710 ms |
| `None` | **518,546** | **28,758 ms** |

`None` 은 "완전한 트리" 가 아니라 **트리를 끄는 것**에 가깝다.

## Coq 자신도 이걸 손잡이로 쓴다

hint DB 마다 투명도 집합을 들고 다니고 `Hint Unfold f` 가 거기에 넣는다.
Lean 4 의 `DiscrTree` 도 키를 만들 때 `@[reducible]` 만 펼친다(`whnfR`).
**정말 펼쳐야 하는 소수만 투명으로** 표시하는 것이 설계된 해법이다.

## 우리 코드

```ocaml
let rigid_mode = ref true
let extra_ts   = ref TransparentState.empty
let ts () = if !rigid_mode then Some !extra_ts else None
```

`ApplicTransparent f` 로 `f` 하나씩 투명 집합에 넣어볼 수 있게 해 뒀다.

## 관련

[[w-unify]] · [[keyed-unification]] · [[delta-reduction]]
