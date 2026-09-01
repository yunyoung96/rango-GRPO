# EConstr vs Constr — 두 항 타입

| | `Constr.t` | `EConstr.t` |
|---|---|---|
| 뭐냐 | 커널의 항 | **evar 가 들어갈 수 있는** 항 |
| evar | 없다고 본다 | 있을 수 있다 |
| 읽기 | `Constr.kind t` | `EConstr.kind sigma t` ← [[sigma]] 필요 |

`EConstr.t` 는 사실 `Constr.t` 와 같은 표현인데 **타입으로 구분**해서
"sigma 없이 읽지 마라" 를 컴파일러가 강제하게 한 것이다.

```ocaml
EConstr.of_constr   c      (* Constr → EConstr : 공짜 *)
EConstr.Unsafe.to_constr t (* EConstr → Constr : 위험 — evar 를 안 펼친다 *)
EConstr.to_constr sigma t  (* 안전 — 정해진 evar 를 다 펼치고 없으면 예외 *)
```

## 우리 코드에서

전역 환경에서 꺼낸 lemma 타입은 `Constr` 이므로 `of_constr` 로 올린다.
반대로 해시테이블 키로 쓸 때는 `Unsafe.to_constr` 로 내린다 —
이때 항에 evar 가 **없다는 것을 우리가 알고** 있어야 한다.

## 관련

[[sigma]] · [[evar]]
