# 검색 판본 이력

> 판본은 `ocaml/applic/applic_main.ml` 의 `retrieval_version` 에 박혀 있고,
> **모든 출력에 찍힌다** — `APPLIC_STAT ver=r11 …` · `CHECK ver=r11 …`.
> 그래서 나중에 "이 수치가 어느 판본 것인가" 를 되짚을 수 있다.

## 판본 표

| 판본 | 한 줄 | 대표 실측 |
|---|---|---|
| [r1](r1.md) | `assert_succeeds` 배터리 — Coq 안에서 tactic 을 실제로 실행 | 12배 축소 · gold 생존 80.8% · 후보당 0.11ms |
| [r2](r2.md) | OCaml 플러그인 — `fold_constants` + `w_unify`, apply 만 | 11,766 → 236 · 0.276s |
| [r3](r3.md) | `Btermdn` 판별트리로 rewrite 채널 | 11,766 → 77 · **0.039s** |
| [r4](r4.md) | 지역 가설 · `apply L in H` · 가설 안 redex | apply gold 의 12.7% 회수 |
| [r5](r5.md) | 모듈 정규화 · `elim_flags` · keyed matching · 진술문 출력 | 후보의 34.7% 가 항상 실패하던 것 해소 |
| [r6](r6.md) | `max_arrows` 8→20 · 결론 분해 · redex 수정 · setoid 캐시 | rewrite **95.5%** · apply **91.6%** |
| [r7](r7.md) | unfold · destruct · decide 채널 | **unfold 0% → 100%** |
| [r8](r8.md) | 랭킹 신호(lgg·lcp·e·z·nm·ing·occ) · HYPS/GBIND | @10 47.1% → **75.0%** |
| [r9](r9.md) | decide 채널 조임 · `check_tac` 도 지역이름 출력 | decide 490 → **91** |
| [r10](r10.md) | `rewrite` 를 goal(`rw`) / 가설(`rwh`) 로 분리 | goal 163 · 가설만 147 · **교집합 0** |
| [r11](r11.md) | 채널 4개로 축소 · ssreflect 묶음규칙 · 속도 −14% · 메모리 봉쇄 | `ds`·`dc` 단독기여 **0** · 노드당 **0.39초** |

## 판본을 올리는 규칙

1. 판정 결과가 **바뀌는** 변경이면 올린다 (신호 추가·채널 추가·조건 변경).
2. 성능만 바뀌는 최적화는 안 올린다 (캐시·자료구조).
3. 올릴 때 `versions/rN.md` 를 새로 쓴다 — **바꾼 것 · 왜 · 실측 · 코드 위치**.
4. 이전 판본 수치를 지우지 않는다. 회귀를 되짚을 수 있어야 한다.

## 실측을 읽을 때 주의

- 판본마다 **측정 표본이 다르다** (지점 수·프로젝트·분모 정의).
- 특히 **분모**가 여러 번 바뀌었다:
  - r8 이전: 지역 변수를 인자로 쓰는 스텝을 미검출로 셌다 → **과소평가**
  - r6 이전: 죽은 지점을 분모에서 뺐다 → **과대평가**
- 그래서 판본 간 직접 비교는 **같은 스크립트로 다시 잰 값**만 유효하다.
