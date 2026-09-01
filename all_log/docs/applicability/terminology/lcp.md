# LCP — 최장 공통 접두사

두 라벨 열이 트라이에서 **몇 층까지 같이 내려가나**.

```
goal :  [ c:PTree.get , * , c:PTree.set , * , * , * ]
gso  :  [ c:PTree.get , * , c:PTree.set , * , * , * ]   LCP = 6
grs  :  [ c:PTree.get , * , c:PTree.remove , … ]        LCP = 2
```

거리로 쓰면 **초거리(ultrametric)** 가 된다:

```
d(s,t) = 2^(−LCP(s,t))          d(s,u) ≤ max( d(s,t), d(t,u) )
```

→ [../concepts/baire.md](../concepts/baire.md)

## 공짜다

판별트리가 **이미** 그 열을 만들었다. 자료구조를 하나 더 안 만들어도 된다.
필터는 트리를 집합 연산으로 쓰고, 같은 트리가 거리도 준다.

## 이미 로그우도다

가지치기 계수 `b` 인 트라이에서 길이 `k` 접두사를 맞추면 대략 `k·log₂b` 비트다.
따로 가중치를 줄 필요가 없다.

## `lgg` 와의 관계

같은 것을 두 수준에서 본다.

| | 수준 | 정밀도 | 비용 |
|---|---|---|---|
| lgg | 항 | 높음 | 재귀 |
| LCP | 문자열 | 낮음 | 트리가 이미 계산 |

실측에서 둘이 거의 같이 움직인다 — `PTree.gso` 는 `lgg=15 lcp=15`.

## 관련

[[applic-idf]] · [[naive-bayes]]
