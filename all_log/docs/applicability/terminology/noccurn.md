# noccurn — "그 변수 안 쓰나?"

```ocaml
EConstr.Vars.noccurn sigma n t   : bool
```

**"항 `t` 안에 de Bruijn 인덱스 `n` 이 안 나오나?"** `n` 이 안 나오면 `true`.

- `n` = **occur**s **n**ot → `noccurn`. 짝은 `occur_between`, `noccur_between`.
- 인덱스는 1부터. `1` 은 **가장 가까운 바인더**다.

## 어디에 쓰나 — 의존/비의존 가르기

```ocaml
match kind sigma ty with
| Prod (_, a, b) ->
    if Vars.noccurn sigma 1 b
    then (* b 가 그 바인더를 안 쓴다 → `a -> b`  = 전제 *)
    else (* 쓴다              → `forall x:a, b` = 바인더 *)
```

```coq
nat -> bool                Prod(_ : nat, bool)
                                        └ `bool` 에 Rel 1 없음 → noccurn = true  → 전제

forall n : nat, n + 0 = n  Prod(n : nat, Rel 1 + 0 = Rel 1)
                                         └ Rel 1 있음 → noccurn = false → 바인더
```

이게 왜 중요한지는 [pi-binder.md](../concepts/pi-binder.md) — `apply … in` 은
**비의존** 전제만 본다. `PTree.gso` 의 첫 `Prod` 는 `A : Type` 이라 의존이고,
그걸 전제로 착각하면 채널이 통째로 틀린다.

## 주의 — `sigma` 가 필요한 이유

`t` 안에 evar 가 있고 그 evar 가 **이미 정해져** 있으면, 정해진 값 안에 `Rel n` 이
숨어 있을 수 있다. 그래서 `sigma` 를 넘겨 펼쳐 보고 판단한다.

## 관련

[[de-bruijn]] · [[sigma]] · [[prod]]
