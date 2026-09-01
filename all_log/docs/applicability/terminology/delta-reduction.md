# βδιζη — 다섯 가지 환원

| | 이름 | 하는 일 |
|---|---|---|
| **β** | beta | `(fun x => b) a` → `b[x:=a]` |
| **δ** | delta | 정의된 상수를 몸통으로 펼침. `plus` → `fix …` |
| **ι** | iota | `match` 를 생성자에 대해 계산. `match S n with S k => k end` → `n` |
| **ζ** | zeta | `let x := a in b` → `b[x:=a]` |
| **η** | eta | `fun x => f x` → `f` |

## 왜 이게 우리 문제인가

Coq 의 "같다" 는 **환원을 포함**한다 (정의적 동등, definitional equality).

```coq
2 + 2   와   4   는 ι·δ 로 같다.
```

판별트리는 **구문**만 본다. `2 + 2` 와 `4` 는 다른 라벨 열이다.
그래서 트리는 놓칠 수 있고, 커널은 안 놓친다.
**이 틈이 우리 방법의 내재적 한계**다 → [../concepts/limits.md](../concepts/limits.md)

δ 를 어디까지 허용할지가 [[transparent-state]] 다.

## 고전 ATP 에는 이 문제가 없다

Otter·E·Vampire 의 단일화는 **순수 구문**이라 색인이 완전하다.
정의적 동등이 있는 체계로 넘어오는 순간 생기는 틈이다.

## 관련

[[transparent-state]] · [[keyed-unification]]
