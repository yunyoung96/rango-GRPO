# 토큰마다 LLM state(입력 context)가 어떻게 달라지나 — 실제 예시 (2026-08-06)

질문: "`destruct H` 를 `dest`/`ruct`/` H` 로 생성할 때, 각 토큰 생성 시점의 **LLM state(입력)가 다 다르다**.
어떻게 다른지 예시로."

## 핵심: autoregressive — 이전에 생성한 토큰이 다음 입력에 누적된다
LLM은 한 토큰을 뽑을 때마다 **그때까지의 모든 토큰**을 입력으로 다시 본다.
그래서 `destruct H`의 3토큰은 **매번 입력이 1토큰씩 길어진 서로 다른 state**에서 생성된다.

실제 토크나이징 (deepseek-coder-1.3b): `destruct H` = `['dest', 'ruct', ' H']` (3토큰)

## 고정 프롬프트 (RL state, 3토큰 내내 안 바뀜)
```
[PREMISES] and_comm : A /\ B -> B /\ A ...
[PROOFS]   ...유사 증명...
[STATE]    H : A /\ B          ← Coq proof state (열린 goal + 가설)
           ⊢ B /\ A
[SCRIPT]   Theorem ...  Proof.  intros H.   ← 지금까지 친 tactic
[TACTIC]                        ← 여기서부터 생성 시작
```
이 전체를 `P` 라 하자 (프롬프트).

## 토큰별 생성 시점의 LLM state (입력) — 누적됨

| step | 생성할 토큰 | **그 시점 LLM 입력 (state)** | 나오는 확률 |
|---|---|---|---|
| 1 | `dest` | `P` | `logp(dest │ P)` |
| 2 | `ruct` | `P` + `dest` | `logp(ruct │ P, dest)` |
| 3 | ` H` | `P` + `dest` + `ruct` | `logp( H │ P, dest, ruct)` |

즉:
```
step1 입력:  … [TACTIC]                    → 'dest' 예측
step2 입력:  … [TACTIC] dest                → 'ruct' 예측   (dest 추가됨)
step3 입력:  … [TACTIC] destruct            → ' H' 예측     (ruct 추가됨 → "destruct")
(끝)  결과:  … [TACTIC] destruct H
```
**같은 프롬프트 P인데, 뒤에 붙는 생성 토큰이 1개씩 늘어 매번 다른 입력** → 그래서 확률도 토큰마다 따로.

## 그럼 이게 RL의 "state"와 같은가? → 아니다 (구분 중요)
- 위 3개의 "입력 차이"는 **한 tactic(action)을 발화하는 내부 과정**이다 (LLM의 autoregressive context).
- **RL state는 안 바뀐다** — `H : A/\B ⊢ B/\A` 그대로. `destruct H` 가 **완성돼 Coq이 실행한 뒤에야** RL state가 새 goal로 바뀐다.

```
RL state s0:  H : A/\B ⊢ B/\A
  action a0 = "destruct H"  ← LLM이 dest→ruct→ H 3토큰으로 발화 (내부 context는 누적)
Coq 실행 →
RL state s1:  a : A,  b : B ⊢ B /\ A     ← 이제서야 RL state 변화, 다음 tactic 입력
```

## 두 종류의 "context/state" 요약
| | 무엇 | 언제 바뀌나 | 예시 |
|---|---|---|---|
| **LLM 입력(생성 context)** | 프롬프트 + 지금까지 생성한 토큰 | **매 토큰** | P → P+dest → P+dest+ruct |
| **RL state** | Coq proof state (goal+가설) | **tactic 완성·실행 후** | s0(H:A/\B) → s1(a:A,b:B) |

- 확률/logp: **LLM 입력**(매 토큰 다름) 기준으로 계산 → 토큰마다 값 다름
- 보상/advantage: **RL state·action**(tactic) 기준 → tactic 하나에 1개, 3토큰이 공유
  (자세히는 [[TOKEN_VS_TACTIC_CREDIT]])

## 한 문장
`dest`/`ruct`/` H`는 **같은 프롬프트 뒤에 생성 토큰이 1개씩 누적된 서로 다른 LLM 입력**에서 뽑히지만(그래서 확률이 각각), 이 셋은 **하나의 RL action(`destruct H`)을 발화하는 과정**이라 RL state는 그 사이 안 바뀌고 보상도 하나로 공유된다.

관련: [[TOKEN_VS_TACTIC_CREDIT]] · [[IMPLEMENTATION]] · grpo_train.py `sequence_token_logprobs`(토큰별 logp) / `build_completion_batch`(프롬프트+완성 정렬)
