# keyed unification — rewrite 의 매칭 규칙

Coq 8.5 부터 `rewrite` 의 redex 찾기가 바뀌었다.

> **머리(head)가 구문적으로 먼저 맞아야** 그다음에 인자를 환원까지 써서 맞춘다.

```coq
(* L : f a = b,  goal 에 g a 가 있을 때 *)
(* f 와 g 가 δ 로 같아도 rewrite 는 안 잡는다 — 머리가 다르니까 *)
```

`Unset Keyed Unification` 으로 끌 수 있지만 기본은 켜져 있다.

## 왜 우리에게 좋은 소식인가

**rewrite 는 Coq 자신이 이미 머리에 대해 구문적이다.**
그러니 경직(rigid) 판별트리로 좁혀도 rewrite 는 안 잃는다.

실측이 정확히 그 모양이었다 — 경직 트리로 좁혔을 때:

| | 변화 |
|---|---|
| rewrite 적중 | 42.7% → **45.1%** (유지) |
| apply 적중 | 78.2% → **37.3%** (반토막) |

→ rewrite 는 트리로, apply 는 선형 훑기로 갈랐다. → [../versions/r3.md](../versions/r3.md)

## 관련

[[delta-reduction]] · [[transparent-state]] · [[w-unify]]
