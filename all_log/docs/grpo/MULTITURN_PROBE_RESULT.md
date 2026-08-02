# multi-turn 에러 피드백 A/B 프로브 결과

작성 데이터: `/tmp/mt_probe.jsonl` · 케이스 251개 (executor=subgoal 1.3B, INVALID state, 같은 예산 n=8샘플)

## 핵심 — A0(에러 없이) vs A1(에러 주석 재주입)

| | 고침(valid 만듦) | 비율 | 95% CI(Wilson) |
|---|---|---|---|
| A0 (대조: [STATE]만 재샘플) | 237/251 | **94.4%** | [90.9, 96.6]% |
| A1 (처리: +실패tactic·에러 주석) | 242/251 | **96.4%** | [93.3, 98.1]% |
| Δ (A1−A0) | +5 | **+2.0pp** | (CI 겹치면 무의미) |

### 짝지은 변화 (같은 케이스에서)
- A1만 고침(A0 실패): **13** ← 에러가 도운 순증거
- A0만 고침(A1 실패): **8** ← 주석이 오히려 방해(OOD 노이즈)
- 둘 다 고침: 229 · 둘 다 실패: 1
- 순 효과 = 13−8 = **+5** (A1 우세)

## 에러 유형별 (품질 + 유형별 고침율)

| 유형 | 케이스 | A0 고침 | A1 고침 | A1−A0 |
|---|---|---|---|---|
| other | 126 | 96.0% | 97.6% | +1.6pp |
| not_found | 71 | 95.8% | 93.0% | -2.8pp |
| unify | 39 | 87.2% | 97.4% | +10.3pp |
| syntax | 15 | 93.3% | 100.0% | +6.7pp |
| empty | 0 | 0.0% | 0.0% | +0.0pp |

- **의미적 에러**(unify+not_found) = 110/251 (43.8%) — 모델이 고칠 단서 있음
- **무의미 에러**(empty+syntax) = 15/251 (6.0%) — 재주입해도 소용 없을 가능성

## 판정 (McNemar 정확검정 — paired)

- 불일치쌍: only_A1=13, only_A0=8 (합 21) → **McNemar 양측 p = 0.383**
- 순 효과 Δ = +2.0pp (+5케이스). ※ paired라 Δ의 유의성은 p값이 판정(절대 pp 아님).

**A0 ≈ A1, 유의차 없음 (p=0.383)** → 인퍼런스만으론 에러 활용 능력이 통계적으로 확인 안 됨(Δ=+2.0pp는 노이즈). → 설계 B(학습으로 가르치기)로 가거나, 효과가 크지 않으면 접기. 단 '의미적 에러 비율'(위)이 높으면 학습판은 시도해볼 여지.

> 참고: p<0.05를 얻으려면 대략 불일치쌍이 한쪽으로 크게 쏠려야 함(예 12:2, 15:4). 단순 순 +3~4케이스(≈+3pp)는 p≈0.3~0.4로 **노이즈**라 '능력 있음'으로 못 봄.

## 실제 예시 (A1이 고친 것 / 못 고친 것)
### A1이 고침 (에러 준 덕에):
- 실패: `set (P := fun m p => (m!n)!n = Some instr ->
                  Pos.eq_dec s k -> In n (make_predecessors m)!s ->
       ` — 에러[syntax]: Syntax Error: Lexer: Undefined token
  → A1 고침: `
  unfold make_predecessors at 1.`
- 실패: `rewrite succs_spec.` — 에러[not_found]: The variable succs_spec was not found in the current environment.
  → A1 고침: `
  unfold make_predecessors.`
- 실패: `set (P := fun m p => code! n = Some instr ->
                      In s (successors instr) ->
                      exis` — 에러[other]: In environment
  → A1 고침: `
  clear.`
### 둘 다 실패 (에러 줘도 못 고침):
- 실패: `apply (Pos.compare_eq x x); auto.` — 에러[unify]: In environment

## ★ 더 중요한 함의 (A0=94.4%가 진짜 발견)

에러 피드백 자체는 무의미(p=0.383)지만, **A0=94.4%**가 훨씬 큰 결과다:
- INVALID state 251개 중 **250개(99.6%)를 재샘플만으로 VALID로 되돌릴 수 있다**(둘 다 실패=1개뿐).
- 즉 **"국소적으로 유효한 tactic 생성"은 병목이 전혀 아니다.** 1.3B는 거의 모든 state에서 8샘플 안에 붙는 tactic을 찾는다.
- 그런데도 증명은 실패(dead 62%). → **벽은 valid가 아니라 productive다**: 붙긴 붙는데(simpl/auto/intros 등) **Qed로 가는 tactic**이 아니다.

### 결론 (연구방향 정합)
1. **multi-turn 에러 피드백 = 접는다.** 재샘플이 이미 94% 고침 → 에러 단서 불필요(+2pp, p=0.38). "valid tactic 생성을 돕는" 계열 전체(에러피드백/문법교육)가 **이미 풀린 문제를 공격**.
   - 유일한 미약 신호: `unify` 에러 +10.3pp(n=39) — 그래도 전체 유의성 없어 학습판(설계 B) 투자 비추.
2. **이게 §10(도달성)/[[CLOSING_FAILURE_ANALYSIS]]를 강하게 재확인**: per-step 유효성은 ~해결됨(94%) → 진짜 벽 = **전역 navigation/도달**(valid한 스텝은 밟지만 leaf/Qed로 못 감).
3. → 지금 돌리는 **도달성 측정 + opener/subgoal(reachability 공략)이 옳은 표적**. multi-turn은 비표적이었음(값싸게 판정하고 접음 = 목적 달성).

관련: [[MULTITURN_DESIGN]] · [[CLOSING_FAILURE_ANALYSIS]] · [[RANKING_GOLD_VS_APPLIED]]
