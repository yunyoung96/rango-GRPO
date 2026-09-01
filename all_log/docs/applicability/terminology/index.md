# 색인(index) — 미리 만들어 두는 조회용 자료구조

## 0. 한 줄

```
   색인이 없으면   후보를 처음부터 끝까지 하나씩 확인한다
   색인이 있으면   질의로 곧장 **작은 부분집합**으로 뛴다
```

책 뒤의 "찾아보기" 와 같다. 단어 하나로 페이지 몇 개만 찍어 준다.
전체를 읽지 않아도 된다.

---

## 1. 무엇이 문제였나

goal 하나에 어떤 lemma 가 쓰일 수 있는지 알려면 **단일화**를 돌려야 한다.

```
   후보 12,652개  ×  단일화 1회 (수십~수백 μs)  =  지점당 초 단위
                                                  스텝마다 이러면 못 쓴다
```

그런데 대부분은 **머리 기호부터 안 맞는다.** 굳이 단일화까지 갈 필요가 없다.

---

## 2. 무엇을 키로 삼나

우리 색인의 키는 **항의 구문 모양**이다. 항을 라벨 열로 펴서 트라이 경로로 쓴다.

```
   get i (set j x m)
        │  전위 순회
        ▼
   [ get/2 , * , set/3 , * , * , * ]     ← 이 열이 트라이 경로
     └ 이름/인자수 ┘   └ `*` = 와일드카드
```

같은 접두사를 가진 lemma 는 **같은 가지를 공유**한다. 조회는 그 가지를 따라 내려가며
안 맞는 가지를 통째로 버린다. → [../concepts/tree-shape.md](../concepts/tree-shape.md)

---

## 3. 한 번 만들고 여러 번 쓴다

```
   색인 구축   파일당 1회   1.13초   ← nb_globals 가 바뀔 때만 다시
   조회        스텝마다     ~ms
```

```ocaml
if idx.nglob <> nb_globals env then build_index env sigma;
```

구축이 비싸도 조회가 수백 번이면 남는다. **분할상환**이 색인의 본질이다.

---

## 4. 실측 — 우리 경우

```
   후보 lemma      12,652
        │ index_cand — 깊이마다 A·P·R 세 트리에
        ▼
   패턴            87,139        (후보당 6.9개)
        │ 조회
        ▼
   raw             34,461        ← 트리가 준 상한
        │ suffix_compat (값싼 머리 비교)
        ▼
   keypass          5,821
        │ w_unify (커널)
        ▼
   진짜 후보          596
```

> **패턴이 후보보다 많은 이유**: lemma 하나를 깊이마다·좌우변마다 따로 넣는다.
> `PTree.gso` 는 깊이 0~6 × (결론·전제·좌변·우변) 으로 여러 자리를 차지한다.
> → [../concepts/three-indexes.md](../concepts/three-indexes.md)

---

## 5. ★ 색인이 지켜야 하는 조건 — 상한이어야 한다

```
   색인이 주는 집합  ⊇  실제로 적용 가능한 집합
```

```
   오탐(false positive)   실제로는 안 되는 걸 줬다   →  커널이 걸러 낸다. 안전
   미탐(false negative)   되는 걸 안 줬다            →  **되돌릴 수 없다**
```

그래서 색인은 **느슨하게** 만들고 판정은 커널에 맡긴다.
순서를 뒤집으면(커널 먼저) 느려서 못 쓰고, 색인만 쓰면 오탐이 남는다.

우리 색인은 **구문적**이고 적용가능성은 **의미적**이라 완전한 상한이 못 된다 —
실측 미탐 5.97%. 이건 구현 문제가 아니라 내재적이다.
→ [../concepts/limits.md](../concepts/limits.md)

---

## 6. 색인 ≠ 판별트리

| | |
|---|---|
| **색인** | 일반 개념 — "조회를 빠르게 하려고 미리 만든 것" |
| **판별트리** | 그 개념의 한 구현 — 항을 라벨 열로 펴서 트라이에 넣는 방식 |

DB 의 B-트리 인덱스, 검색엔진의 역색인(inverted index)도 전부 색인이다.
우리가 쓰는 건 그중 **자동정리증명 쪽에서 쓰는 판별트리**다.
→ [../concepts/btermdn.md](../concepts/btermdn.md)

```
   역색인 (검색엔진)     단어 → 그 단어가 든 문서 목록
   판별트리 (우리)       항의 모양 → 그 모양과 맞을 수 있는 lemma 목록
```

---

## 7. 우리 색인의 실체

```ocaml
type t = {
  mutable apply : DN.t;    (* A 트리 — 결론 *)
  mutable prem  : DN.t;    (* P 트리 — 비의존 전제 *)
  mutable rw    : DN.t;    (* R 트리 — 관계 좌·우변 *)
  mutable cands : cand array;   (* 후보 원본 *)
  mutable rawty : Constr.t array;  (* 선언 타입 — 값싼 선별용 *)
  mutable nglob : int;          (* 언제 다시 만들지 *)
  mutable npat  : int;
}
```

**코드**: `applic_main.ml:108` (레코드) · `:237` `index_cand` · `:280` `build_index`

## 관련

[[globref]] · [../concepts/btermdn.md](../concepts/btermdn.md) ·
[../concepts/three-indexes.md](../concepts/three-indexes.md) ·
[../concepts/tree-shape.md](../concepts/tree-shape.md)
