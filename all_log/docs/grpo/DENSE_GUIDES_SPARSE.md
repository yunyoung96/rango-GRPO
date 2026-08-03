# Dense가 Sparse(Qed)를 "이끈다" — 두 신호 RL 정리 + PBRS로 본 우리 E2 실패 (2026-08-03)

## 질문 (원래 아이디어)
> "GRPO가 너무 sparse(Qed 0/1)한데, **progress가 있으면 dense reward를 주는 agent**와 **그냥 Qed를 찍어야만 하는 agent** 둘을 두고, **전자가 후자를 이끌어** 주면 도움이 되려나? 이런 강화학습이 기존에 있나?"

## 한 줄 답
- **"dense가 sparse를 이끈다"는 RL에서 이미 잘 정의된 문제**다. 단 **핵심은 dense 신호를 *어디에* 넣느냐**이고, 넣는 위치에 따라 (1) 목적이 바뀜(위험) (2) 최적정책 보존(안전) (3) 분산만 감소(항상 안전)로 완전히 갈린다.
- **우리는 이미 두 번 시도했고 둘 다 실패**했는데, 이 렌즈로 보면 **실패 원인이 서로 다르다**: E2-dense는 *틀린 자리(보상)*에 *틀린 형태(비-potential)*로 넣어 목적을 편향시켰고, PPO는 *맞는 자리(critic)*에 넣었으나 sparse 때문에 critic이 **못 배웠다**.
- **미시도의 sweet spot**: dense를 **coq-lsp로 grounded된 potential Φ(s)=닫은 goal 수**로 만들어 **per-step potential-based shaping**으로 넣으면 → **최적정책 보존(편향 0) + critic 학습 불필요**. 이게 이론상 유일하게 깨끗한 "dense가 sparse를 이끄는" 설계다.

---

## 1. dense를 "어디에" 넣느냐 — 세 자리 (이게 전부)

같은 dense 신호라도 들어가는 위치가 다르면 성질이 정반대다.

| 넣는 자리 | 형태 | 최적정책 | 우리 대응 | 판정 |
|---|---|---|---|---|
| **① 목적(objective)** = 보상에 직접 더함 | `R = R_qed + b(s)` (raw bonus) | **바뀔 수 있음**(편향) | **E2-dense**(terminal `0.3·V`) | ❌ progress를 Qed보다 좇게 됨 |
| **② shaping** = potential 차분으로 더함 | `F = γΦ(s') − Φ(s)` per-step | **보존**(Ng 1999 정리) | **미시도** | ⭐ 유일하게 깨끗 |
| **③ baseline/critic** = advantage 안에서만 | `A = r + γV(s') − V(s)` | **보존**(baseline 불편) | **PPO**(critic 못 배움) | ○자리는 맞음, 학습이 벽 |

②와 ③은 사실 **같은 것의 두 얼굴**이다(아래 §3). ①만 위험하다.

---

## 2. PBRS 정리 — 왜 "형태"가 목적을 바꾸는가 (Ng, Harada & Russell 1999)

**Policy invariance under reward transformations** (Ng et al., ICML 1999):
> 보상에 더하는 shaping 항 `F(s,a,s')`가 **어떤 potential Φ:S→ℝ에 대해 `F = γΦ(s') − Φ(s)` 꼴일 때에만**, 원문제와 shaping된 문제의 **최적정책이 동일**하다. 그 외 형태의 `F`는 최적정책을 바꿀 수 있다.

직관: potential 차분은 궤적을 따라 **telescoping**한다.
```
Σ_t γ^t F(s_t,s_{t+1}) = γ^T Φ(s_T) − Φ(s_0)   (경로 무관, 끝-시작만 남음)
```
→ 어떤 정책이 좋은지 **순서를 안 바꾸고**, 중간 step마다 gradient만 **촘촘하게** 만들어 준다. (Wiewiora 2003: PBRS ≡ Q를 Φ로 초기화하는 것과 등가.)

반대로 **raw bonus `b(s)`**(차분이 아닌 절대 보너스)는 telescoping이 안 돼 **누적되어 목적을 바꾼다** → "progress가 높은 상태로 끝나면 이득"을 학습 → **Qed 없이 진전만 하다 죽는 정책**으로 편향.

---

## 3. 왜 ②(shaping)와 ③(critic)이 같은가 — actor-critic이 곧 potential shaping

Φ = V(가치함수)로 두면:
```
A(s,a) = r + γV(s') − V(s)  =  r + [ potential-based shaping term, Φ=V ]
```
즉 **actor-critic의 advantage는 "Φ=V인 PBRS로 densify된 return"과 정확히 같다.** critic V는 baseline이라 policy gradient에 **편향을 안 준다**(`E_a[b(s)∇logπ]=0`). 그래서 "dense critic이 sparse actor를 이끈다"는 **표준 actor-critic 그 자체**이고, 이론적으로 흠이 없다.

**결론**: "dense가 sparse를 이끈다"의 이론적 정답은 **dense를 potential/critic으로만 넣는 것**(②③). dense를 **보상 자체로** 넣으면(①) 편향된다.

---

## 4. 우리 두 실패를 이 렌즈로 재해석 (핵심)

### 4.1 E2-dense = ①(틀린 자리 · 틀린 형태)
실제 구현([[IMPLEMENTATION]] §(3)):
```
R(τ) = 1.0                        (COMPLETE)
     = 0.3 · V(마지막 valid goal)   (미완)      # shaping_coef=0.3, V=QEDCartographer
```
- 이건 **궤적 끝 상태의 절대 보너스**(`0.3·V(s_last)`)를 통째 보상에 얹은 것 = **potential 차분이 아님** = Ng 정리의 "위험한 형태".
- 게다가 credit assignment는 이 스칼라를 **시도의 모든 step에 균등 분배**([[IMPLEMENTATION]] §(4)) → "진전하다 죽은" 시도의 **모든 tactic에 +advantage** → **"진전 후 사망" 행동을 강화**.
- 결과: **E2-dense = 9/23, baseline 대비 ~0**([[RESULTS_LEADERBOARD]]). "density(신호 있는 그룹 수)는 고쳤으나 credit 정확성이 다음 벽"이라 기록 — 이론상 **목적 편향**이 그 정체.
- (`0.3`으로 눌러 완결 1.0을 못 넘게 한 건 순서보존 *시도*였지만, 그건 "완결 > 미완"만 보장할 뿐 **미완들 사이 순서**를 여전히 바꿔 편향을 못 막는다.)

### 4.2 PPO = ③(맞는 자리인데 학습 실패)
- PPO는 dense를 **critic V(s)**에 넣었다 = **이론적으로 옳은 자리**(baseline, 불편).
- 그러나 **critic explained_var ≈ 0**([[architecture]], [[IDEAS]] #7, 메모리 [[ppo-bigscale-pending]]) — **sparse 보상이라 V가 bootstrap할 신호가 없어** 학습 자체가 안 됨. → 자리는 맞았으나 **추정(estimation)이 벽**.

### 4.3 정리
| 시도 | dense를 넣은 자리 | 편향? | 왜 실패 |
|---|---|---|---|
| E2-dense | ① 보상(raw terminal) | **편향됨** | 목적이 "진전"으로 이동, test ~0 |
| PPO | ③ critic V(s) | 불편(OK) | **critic이 못 배움**(sparse→EV≈0) |
| **미시도** | **② grounded potential** | **불편(OK)** | **학습 불필요**(§5) |

---

## 5. 이론상 sweet spot (미시도) — grounded potential shaping

두 실패가 정확히 상보적이다: E2는 자리가 틀렸고, PPO는 자리는 맞으나 못 배웠다. **둘을 동시에 피하는 설계**:

**Φ(s) = coq-lsp가 알려주는 "닫은 goal 수"** (또는 −남은 goal 수). 학습된 V가 아니라 **verifier로 grounded**된 값 → critic 학습이 필요 없다.

```
per-step shaping:  F(s_t → s_{t+1}) = γ·Φ(s_{t+1}) − Φ(s_t)
학습 신호:          A_step = A_qed(그룹상대)  +  β·F(s_t→s_{t+1})
```
- **편향 0**: F가 potential 차분이라 Ng 정리로 최적정책(=Qed) 보존.
- **critic 불필요**: Φ가 verifier grounded라 explained_var 문제 없음.
- **densify**: dead 그룹(전 시도 Qed 실패)도 step마다 "goal 하나 닫음"에서 +F를 받아 **gradient가 생김** — sparse의 정공법.
- **주의**: credit을 **step별로** 줘야 함(E2처럼 시도-스칼라 균등분배 금지). 지금 `--process` 배선을 potential-차분으로 바꾸면 됨.

**subgoal-GRPO와의 관계**: "subgoal 닫히면 +1"([[SUBGOAL_PAPER_ASSESSMENT]] §③)도 Φ=닫은-subgoal-수의 거친 potential 버전이다. 본 설계는 그 연속판.

---

## 6. 선행연구 매핑 (dense가 sparse를 이끄는 기존 RL)

| 논문/개념 | dense를 넣는 자리 | 우리와의 관계 |
|---|---|---|
| **Ng, Harada & Russell 1999** (PBRS 정리) | ② shaping | **이론 근거.** 형태(차분)만이 불편 |
| **Wiewiora 2003** (shaping ≡ Q-init) | ②≡③ | ②와 ③이 같음을 증명 |
| **Actor-Critic** (Sutton, 표준) | ③ critic baseline | "dense critic이 sparse actor를 이끈다"의 원형 |
| **Math-Shepherd** [2312.08935](https://arxiv.org/abs/2312.08935) | ① PRM이 목적(학습 dense) | dense가 *목적*이라 편향 가능 → 최종성공 예측하게 PRM 학습해 완화. 우린 **verifier로 대체=편향 원천 제거** |
| **Process-Verified RL for TP** [2606.20068](https://arxiv.org/abs/2606.20068) | ② verifier-grounded per-step | **우리 §5의 Lean 판.** 가장 on-point |
| **LeanProgress** [2502.17925](https://arxiv.org/abs/2502.17925) | ③ 학습 progress value | Φ를 학습으로 추정(PPO와 같은 위험: 학습 가능해야) |
| **QEDCartographer** [2408.09237](https://arxiv.org/abs/2408.09237) | ③ 학습 V로 search 유도 | E2의 V 출처. 학습 V라 sparse서 약함 |
| **PPO/GRPO 병행**([[SUBGOAL_RL_RESEARCH_ALL]] §5) | ③+① 혼합 | subgoal=PPO(critic) + 전체=GRPO(그룹). "mixed-baseline PG" |

**빈칸(novelty)**: **verifier-grounded potential(=학습 없는 Φ)로 per-step PBRS를 sparse Qed-GRPO에 얹은** Coq 소형모델 사례는 거의 없음(2606.20068이 Lean 최근접). → 시도가치 있음.

---

## 7. 판정 (우리 규모 1.3B·CompCert)

- **하지 말 것**: E2식 raw dense bonus(①) — 편향 재현. 학습 critic(③-PPO) 단독 — sparse서 EV≈0 재현.
- **할 것(권장)**: **Φ=닫은 goal 수(coq-lsp grounded) 로 per-step potential shaping**(②). `--process`를 potential-차분·step별 credit으로 개조. 편향 0 + critic 없음 + dead 그룹 densify.
- **정직한 천장 경고**: 모든 알고리즘이 rand200 **~33.5–37.5%로 수렴**, SFT→GRPO 37.5%가 천장([[architecture]]). dense가 **신호 밀도**는 고쳐도, 벽이 조립 위의 **도달성/능력 천장**이면([[SUBGOAL_PAPER_ASSESSMENT]] §10, [[rango_augmented/COMPOSITION_IS_THE_WALL]]) 밀도만으로 test가 안 오를 수 있다. dense-shaping은 **필요조건이지 충분조건이 아님**.

---

## 8. 우리 문제 세팅에서는 정확히 어떻게 하나 (실전 처방)

우리 세팅: **1.3B + LoRA, 정리당 G=8 rollout, GRPO(critic-free, group-mean baseline), 보상=coq-lsp의 Qed 0/1.** 벽=대부분 그룹이 8개 다 실패(dead)라 gradient 0.

### 8.1 3단계 레시피
**① potential Φ(s)를 coq-lsp로 정의 (학습 없음)**
- 가장 단순: `Φ(s) = −(현재 열린 goal 수)`. goal이 닫힐수록 Φ가 0에 가까워짐(=좋아짐).
- **분기 함정 주의**: `destruct`/`induction`은 goal을 **늘린다**(1→3). 그러면 Φ가 일시적으로 **떨어져** "쪼개기"를 벌하게 됨. 두 보정 중 하나:
  - (a) `Φ(s) = 닫은 goal 수 / 원래 필요한 총 goal 수` (0→1 진행률) — 분기로 분모가 커져도 단조.
  - (b) `Φ(s) = −(남은 goal들의 크기 합)` — 큰 goal 하나가 작은 여럿으로 쪼개지면 합이 줄어 **진전으로 인식**.
- 실무 시작점: (a) 진행률. coq-lsp가 step마다 goal 리스트를 주므로 **공짜**.

**② per-step shaping을 advantage에 더한다 (E2식 균등분배 금지)**
```
A_step(s_t, a_t) = A_group(outcome)          # 기존 GRPO: (r−mean)/std, 시도 전체 공유
                 + β · [ γ·Φ(s_{t+1}) − Φ(s_t) ]   # ★ step별 potential 차분(=PBRS)
```
- `A_group`는 지금처럼 시도 단위, `β·F`는 **step마다 다르게** 더함 → 어느 tactic이 진전을 만들었는지 credit이 붙음.
- **왜 편향 0인가**: `Σ_t γ^t F_t = γ^T Φ(끝) − Φ(시작)` 로 telescoping → 궤적 총점의 순서를 안 바꿈(§2). Qed가 여전히 최고.

**③ β 튜닝 + 검증**
- `β`는 작게(0.1~0.3). F가 outcome을 압도하면 "진전만" 좇는 편향 재발(E2). GRPO A는 std정규화라 ~1스케일이니 β로 F를 그 아래로.
- 검증 지표: **dead 그룹(8개 다 실패)이 이제 gradient≠0을 받나?** (`n_dead_revived` 류 로깅). 이게 늘면 densify 성공.

### 8.2 구현 위치 (이미 있는 인프라)
- `grpo_rollout.py`가 `--process` 경로에서 **step별 result(goal 상태)를 이미 기록**([[IMPLEMENTATION]] §(4)·(5)).
- 거기서 각 step goal 수 → Φ 계산 → `flatten_group`이 step advantage를 만들 때 `β·F`를 더하면 됨. **새 모델·critic 학습 없음.**
- 즉 **`--process`를 "raw 부분점수"가 아니라 "potential 차분"으로 바꾸는 소규모 수정**이 전부.

### 8.3 하지 말 것 (우리가 이미 데본 것)
- ❌ E2식 `0.3·V(끝상태)`를 보상에 통째로 (편향, test ~0).
- ❌ 학습 critic PPO 단독 (sparse→EV≈0, 학습 실패).
- ❌ F를 시도 스칼라로 균등분배 (credit 뭉개짐 = E2와 같은 실수).

---

## 9. critic이 꼭 필요한가? → **아니오 (우리 권장 설계에선 불필요)**

| 질문 | 답 |
|---|---|
| critic의 역할이 뭔데? | "이 상태가 얼마나 좋은가" `V(s)`를 **추정**하는 학습된 근사기. advantage의 baseline. |
| 왜 우리는 없어도 되나? | **coq-lsp가 `V(s)`를 정확히 알려주기 때문.** "goal 몇 개 닫혔나"는 **추정할 필요 없이 verifier가 공짜로 주는 grounded 값** → 학습 critic 대신 `Φ`로 직접 계산. |
| PPO는 왜 critic이 필요했고 왜 실패했나 | PPO는 `V`를 **학습**으로 추정하려 함. 그런데 우리 보상이 sparse(대부분 0)라 V가 **bootstrap할 신호가 없어** explained_var≈0 = 학습 자체 실패([[architecture]]). |
| GRPO는 이미 critic이 없잖아? | 맞다. GRPO는 group-mean을 baseline으로 써서 **이미 critic-free**. 우리는 거기에 **grounded Φ**만 얹는 것 → 여전히 critic 0개. |
| 그럼 critic이 *필요한* 경우는? | potential을 verifier로 **못 만들 때**(도메인에 진행 신호가 없음). 그땐 학습 V가 필요 → 하지만 sparse면 어렵다(우리 PPO 교훈). **우리 도메인은 다행히 coq-lsp가 있어 해당 안 됨.** |

**한 줄**: critic은 "progress를 스스로 추정해야 할 때"만 필요하다. 우리는 **coq-lsp라는 완벽·무편향·무료 progress 측정기**가 있으니 **critic이 전혀 필요 없다.** 오히려 critic을 억지로 학습시키려다 실패한 게 PPO였다.

---

## 10. 초등학생도 이해하는 비유 (보물찾기 게임)

숲에서 **보물상자**를 찾는 게임. 상자를 열면 이김(=Qed). 로봇(정책)에게 어디로 갈지 가르치는 중.

- **Sparse 보상(지금 GRPO)**: 상자를 **딱 열었을 때만** "딩동!" 소리. 그 전엔 **아무 말도 안 해줌.** → 로봇이 숲에서 헤매기만 하고 **뭘 잘했는지 몰라서** 못 배움. (우리 벽: 8번 시도해서 8번 다 못 찾으면 힌트가 0개 = 배울 게 없음.)

- **Dense 힌트**: 중간중간 **"따뜻해~ / 차가워~"**를 말해줌. 이게 "progress를 주는 도우미".

- **① 힌트를 상으로 주면 (E2가 한 실수)**: "따뜻해질 때마다 **사탕**!" → 로봇이 **보물은 안 찾고 따뜻한 자리에서 뱅뱅** 돌며 사탕만 먹음. 나쁜 버릇! (=목적이 "보물"에서 "따뜻함"으로 바뀜 = 편향.)

- **② 힌트를 "가까워진 만큼만" 점수로 주고 멀어지면 도로 뺏으면 (올바른 방법=PBRS)**: 보물에 한 걸음 **가까워지면 +1, 멀어지면 −1.** → 왔다갔다 하면 점수가 **서로 상쇄**돼 0. **결국 상자를 열어야 총점 최고.** 나쁜 버릇이 안 생기면서 "이 방향이 맞아"는 배움. ← **우리가 해야 할 것.**

- **③ 심판을 두면 (critic)**: 옆에서 **"지금 위치 7점!"** 외쳐주는 심판. 로봇은 그 점수로 방향을 잡음. **문제**: 우리 게임은 보물을 거의 못 찾아서(sparse), 심판이 **뭘 보고 점수를 매길지 배우질 못함** → 심판이 안 자람(=PPO 실패).

- **우리의 정답**: 우리 게임엔 **coq-lsp라는 완벽한 심판이 공짜로 이미 있다.** "goal 3개 중 1개 닫혔어 = 33% 왔어"를 **정확히** 알려줌. → 심판을 키울 필요 없이(②처럼) **그 정확한 점수의 *차이*를 힌트로** 쓰면 됨.

**한 문장 요약**: "따뜻해"를 **사탕(상)으로 주면 애가 망가지고(E2)**, **가까워진 만큼의 점수차이로 주면 잘 배운다(우리 목표)**. 그리고 그 점수를 매길 **심판(coq-lsp)이 공짜로 있어서 따로 심판을 키울 필요가 없다(critic 불필요).**

---
관련: [[SUBGOAL_RL_RESEARCH_ALL]] §5(PPO+GRPO 병행) · [[SUBGOAL_PAPER_ASSESSMENT]] §③④·§10 · [[IMPLEMENTATION]] §(3)(4) dense/credit · [[RESULTS_LEADERBOARD]] E2 · [[architecture]] PPO critic · 메모리 [[ppo-bigscale-pending]] · [[rango_augmented/COMPOSITION_IS_THE_WALL]]
