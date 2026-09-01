# rig (rigidity · 경직도)

```
rig(L) = 매칭 항의 전위 순회 라벨 중 `*` 아닌 라벨의 개수
```

매칭 항 = 채널마다 다르다: ap 는 lemma 결론, in 은 비의존 전제,
rw/rwh 는 등식 패턴 변. `*` 는 판별트리의 Everything(무엇과도 맞는 라벨)이다.

## 값 읽는 법

| rig | 뜻 | 예 |
|---|---|---|
| 0 | 전부 유연 — 어떤 goal 에나 후보로 뜬다 | `Basics.const` 응용 |
| 1 | 머리 하나만 경직 | `Nat.add_comm` (`add`) |
| 4+ | 특정 자료구조·함수에 박힘 | `PTree.gso` (`get`·`set`…) |

VAL 실측: 후보의 91%가 rig=0, gold 중앙값 rig=1 —
**gold 는 풀 평균보다 경직**이다. 랭킹 가중치도 그렇게 나온다:
`w(rig=4)=+7.98 bit`, `w(rig=0)=−4.50 bit` (TRAIN 학습).

## 왜 IDF 인가

`Î(L) = rig(L)·log₂b` — 통과 확률의 로그. 유도는 [[structural-idf]],
격자 쪽 근거는 [[lattice]], 트라이 쪽 근거는 [[baire]] 참조.
경험적 조회표 [[applic-idf]] 의 스플릿 전이 문제를 구조로 대체한다.

## 구현

`applic_main.ml`:
```ocaml
let rigidity (a : string array) =
  Array.fold_left (fun n x -> if x = "*" then n else n + 1) 0 a
```
`preorder_of` 가 이미 만드는 열을 세기만 한다 — 추가 비용 0.
네 채널 출력 줄(`APPLIC`·`APPLICIN`·`DNRW`·`DNRWH`)에 `rig=` 로 실린다.
