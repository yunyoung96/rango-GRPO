# GlobRef — 전역 참조

```ocaml
type GlobRef.t =
  | VarRef       of Id.t            지역/섹션 변수
  | ConstRef     of Constant.t      Definition, Lemma, Theorem, Axiom
  | IndRef       of inductive       Inductive 타입 자체 (nat, list, and)
  | ConstructRef of constructor     그 생성자 (O, S, cons, conj)
```

**판별트리의 라벨이 이것**이다:

```ocaml
type term_label = GRLabel of GlobRef.t | ProdLabel | SortLabel
```

## 비교는 `CanOrd`

```ocaml
GlobRef.CanOrd.compare
```

**정준(canonical) 이름**으로 비교한다. 모듈 별칭 때문에 같은 것이 다른
이름으로 보일 수 있는데, 정준 이름으로 맞추면 같은 것으로 본다.
(`UserOrd` 는 사용자가 쓴 이름으로 본다 — 트리에는 `CanOrd` 가 맞다.)

## 우리가 순회하는 법

```ocaml
Environ.fold_constants   (fun c body acc -> …) env acc
Environ.fold_inductives  (fun ind mib acc -> …) env acc
```

현재 환경에 **로드된 모든** 상수/귀납형을 훑어 색인에 넣는다.
`Search` 명령이 하는 것과 같은 순회다.

## 관련

[[qualid]] · [[prod]]
