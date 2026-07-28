# SFT→subgoal-GRPO(leaf-first) — 논문 가능성 평가 + novelty 확장 아이디어

작성 2026-07-25. 관련: [[LEAF_SUBGOAL_METHOD]], [[sft-subgoal-grpo-naming]], [[no-published-baseline]].
현재 상태: SFT→bottom-up-subgoal-GRPO 실행 중. 중간 신호 = **root 롤아웃 성공률 ~36%** (SFT→GRPO 26% 대비 +10%p, 학습셋 기준). held-out 1191(비교 A) 미확정.

**held-out rand200@600s 중간 비교(같은 127개 정리로 공정 매칭, 채점 127/200 진행중)**: baseline **34.6%**(44/127) · SFT→GRPO **38.6%**(49/127) · **본 방법 40.2%**(51/127). → SFT→GRPO 대비 **+1.6%p(순 +2개: 4승 2패)**로 리드는 작고 미확정. *(full-200 기준 baseline 33.5%/SFT→GRPO 37.5%와 달리, 이 127개는 먼저 끝난 다소 쉬운 부분집합이라 세 방법 다 소폭 높음 — 완주 후 재확정.)*

---

## 0. 용어 사전 (Glossary) — 이 문서에서 각 용어를 쓰는 "느낌"

textbook 정의가 아니라 **이 문서/이 프로젝트 맥락에서** 어떤 뉘앙스로 쓰는지를 적는다.

### 0.1 핵심 메커니즘 용어
| 용어 | 뜻 + 이 문서에서의 느낌 |
|---|---|
| **seed** | 모델이 롤아웃을 **시작하는 상태**. gold prefix를 Coq에 replay해 만들어준 `initial_proof`. "모델을 증명의 **어디에 내려놓고** 시작시키나"의 그 지점. 얕은 seed=정리 처음, 깊은 seed=증명 안쪽. (자세히 §5) |
| **canonical / canonicality** | seed에 도달하는 decompose가 **거의 강제·자명**한 성질. 유일 귀납가설에 `induction`, 변수에 `destruct`처럼 "누가 풀어도 여기서 이걸 친다"는 느낌. 반대는 **idiosyncratic**(특정 `apply lemma_X`처럼 그 증명에만 있는 선택). canonical할수록 정책이 실제로 그 state에 감(=p_reach↑). |
| **per-subgoal 보상** | Qed(전체 완결)가 아니라 **focused subgoal 하나가 닫히면**(goal 수가 seed 레벨 아래로 떨어지면) reward=1. "부분 성공에도 신용을 준다"는 느낌. 이게 dead였을 그룹을 signal로 살리는 핵심 장치. |
| **bottom-up / leaf-first** | subgoal 트리를 **leaf(가장 깊은 말단)→root(완전체)** 순서로 학습. "안쪽 쉬운 조각 먼저 마스터하고 바깥으로 확장". "(leaf)"는 leaf만 본다는 오해라 **bottom-up**으로 개명. |
| **subgoal-start / size** | **subgoal-start** = goal 수가 바뀌는 지점(분해로 새 subgoal 생기거나 형제로 넘어가는 곳) = seed 후보. **size** = 그 subgoal을 닫기까지의 step 수 = 그 subgoal 증명 길이. size 작음=leaf=쉬움. |
| **stage s1/s2/s3/s0** | size로 나눈 커리큘럼 단계. **s1**=size≤2(leaf), **s2**=3-5(중간), **s3**=≥6(큰 subgoal), **s0**=완전체 root(gold prefix 없음, Qed 보상=원래 SFT→GRPO와 동일). s1→s2→s3→s0 순으로 부트스트랩. |
| **decompose** | 한 goal을 여러 subgoal로 **쪼개는 tactic**(induction/destruct/assert/apply). "decompose-node에서 seed"=쪼개는 지점에서 시작(→실패한 변형), "decompose 제안 학습"(§3-A)=**언제 뭘 쪼갤지**를 배우게 하는 것. |

### 0.2 그룹·신호 용어 (GRPO)
| 용어 | 뜻 + 이 문서에서의 느낌 |
|---|---|
| **그룹(group)** | 하나의 seed에서 뽑은 **G개 롤아웃 묶음**. GRPO는 이 그룹 안에서 상대 비교로 advantage를 만든다. |
| **all-solved / mixed / dead** | 그룹의 성공 분포. **all-solved**=G개 다 성공(N/N), **dead**=다 실패(0/N), **mixed**=일부만 성공. all-solved·dead는 그룹 내 편차 0 → advantage 0 → **gradient 0(낭비)**. **mixed만 학습신호**. "s1 낭비 63%"=all-solved+dead가 63%란 뜻. |
| **advantage (A_i)** | `A_i=(r_i−mean)/std`, 그룹 상대 우위. 그룹이 다 같으면(0 or 1) std·편차가 0 → A=0 → 학습 안 됨. |
| **GRPO** | critic 없이 **그룹 상대 advantage**로 policy gradient. γ=1. dead group 문제(=신호 0)가 이 프로젝트 핵심 난제. |
| **RLOO (leave-one-out baseline)** | advantage baseline을 "**자기 뺀 나머지 평균**"으로. std-정규화([Dr.GRPO](https://arxiv.org/abs/2503.20783)가 편향이라 지적)와 달리 **무편향**이라 채택. |
| **baseline** | (1) advantage의 기준값(위 RLOO), (2) 성능 비교 기준선(우리 rango 322/328/338). 문맥으로 구분. |

### 0.3 transfer·이론 용어
| 용어 | 뜻 + 이 문서에서의 느낌 |
|---|---|
| **transfer / transfer gap** | subgoal state에서 배운 실력이 **배포(정리 처음부터 풀기)에서 현금화되는가**. "롤아웃 성공률↑인데 test↑ 안 되면" transfer 실패. **gap**=학습에서 얻은 것과 배포에서 나타나는 것의 차이. 이 프로젝트의 일관된 리스크. |
| **p_reach(s)** | 배포 정책 π가 정리 처음부터 **자기경로로 state `s`에 도달할 확률**. 높으면 그 state에서의 개선이 배포에 전이됨. canonical seed=p_reach↑, 깊은 backward seed=p_reach↓. **transfer 이득 ∝ p_reach**. |
| **covariate shift** | **학습 때 본 state 분포 ≠ 배포 때 만나는 state 분포**. gold로 특정 state에 데려다 놓고 배웠는데 정책 혼자선 거기 못 가면 배운 게 헛됨. gold-injection([LUFFY](https://arxiv.org/abs/2504.14945)/backward) 실패의 이론적 원인. |
| **on-policy / off-policy** | **on-policy**=학습 데이터가 **정책 자신의 분포**에서 나옴(안전). **off-policy**=gold 등 **남의 궤적**에서 나옴(covariate shift 위험). per-subgoal 보상으로 닫힌 subgoal은 정책이 실제 도달한 state라 on-policy-safe. |
| **compounding error / 복리오차 O(εT²)** | per-step 오차 ε가 **긴 궤적에서 복리로 누적**(틀린 state→더 틀린 state). horizon T에 **제곱**으로 커짐([Ross-Bagnell](https://arxiv.org/abs/1011.0686)). subgoal 분할로 T→T/k 줄이면 **O(εT²/k)** 로 완화. |
| **horizon T / k** | **T**=한 증명의 길이(step 수, CompCert 중앙값 ~14). **k**=한 증명이 쪼개진 subgoal 개수. 분할이 많을수록(k↑) 복리오차↓. |
| **ε / ε_sub** | **ε**=per-step 정책 오차(대략 INVALID/틀린 tactic 비율). **ε_sub**=subgoal state에서의 per-step 오차. bound의 상수. |
| **suboptimality** | 최적 대비 배포 성능 손실. bound의 좌변(`≲ O(ε_sub·T²/k)`). 작을수록 좋음. |
| **occupancy / 점유분포 d^π** | 정책 π가 배포 중 각 state에 **머무는 빈도 분포**. on-policy 학습=학습분포가 곧 d^π라 gap 0. |
| **unbiased / 무편향** | advantage·gradient 추정이 **참값을 평균적으로 맞힘**(체계적 치우침 없음). RLOO·MC 평균이 무편향. std-정규화는 편향. |
| **monotonic improvement / 단조개선** | 라운드마다 성능이 **떨어지지 않음**(`J(π_{r+1})≥J(π_r)`). expert iteration·on-policy PG의 성질. gold-injection은 이걸 깨서 회귀. |
| **MC value / mc_value** | 한 state에서 **여러 번 굴려 성공 비율**로 그 state의 value(=닫힐 확률) 추정. [VinePPO](https://arxiv.org/abs/2410.01679) 스타일. 코드 `mc_value()` 재사용. |
| **HER / relabel** | Hindsight Experience Replay. 전체는 실패했어도 **달성한 subgoal을 "성공 목표"로 되라벨**해 학습에 씀. per-subgoal 보상이 이 relabel의 특수형. |
| **options (계층 RL)** | 각 subgoal을 하나의 **시간적 추상 행동(option)** 으로 봄. option-level MDP는 유효 horizon이 T/k라 sample-complexity 이득. |
| **verifier** | Coq/coq-lsp. tactic이 유효한지·Qed됐는지 **정확히 0/1로 판정**. RLHF의 학습된 보상모델과 달리 **편향 0**이라 "perfect reward" 프레이밍 가능. |
| **credit assignment** | 성공했을 때 **어느 행동에 공을 돌릴지**. Qed-only는 마지막까지 가야 credit(멀어서 어려움), per-subgoal은 subgoal 경계에서 credit(가까움). |

### 0.4 평가·방법 용어
| 용어 | 뜻 + 이 문서에서의 느낌 |
|---|---|
| **held-out / heldout-1191 / rand200** | 학습에 **안 쓴 test 집합**. **heldout-1191**=CompCert test 1191개(@120s), **rand200**=무작위 200개(@600s, 더 긴 시간). 학습셋 성공률(친숙성 부풀림 가능)과 달리 **진짜 일반화**를 봄. "비교 A"=held-out에서 SFT→GRPO를 이기는가. |
| **비교 A / 비교 B** | **A**=held-out(1191/rand200) 성공률 대조(진짜 관문). **B**=**학습셋** root 롤아웃 성공률 대조(친숙성 있어 참고용). |
| **SFT warmup** | 본 RL 전에 gold로 한 번 SFT(`rango-grpo-bs2-sft`). 여기선 **탐색 부트스트랩** 역할 — 정책이 decompose를 더 자주 쳐서 subgoal state 방문분포(support)를 넓힘. |
| **expert iteration / STaR** | **자기 성공(완전체 증명)만 SFT → 재롤아웃 → 반복**. covariate shift 0, 단조개선 보장. 가장 깨끗한 대조군 — subgoal이 이걸 이겨야 복잡도 정당화. |
| **OSR (On-policy Subgoal Reinforcement)** | §6의 **보장 있는** 변형. seed를 gold가 아니라 **정책 자신이 방문한 subgoal state**로 → p_reach=1(구조적으로 covariate shift 0). 현재 방법의 "이론적으로 안전한" 상한판. |
| **process / dense reward** | Qed(0/1, sparse) 대신 **닫은 goal 수·QED까지 거리**로 부분크레딧. dead 그룹(신호 0)을 살리는 가장 싼 개선. |
| **importance ratio ρ / clip** | off-policy 보정비 `ρ=π_new/π_old`. 너무 크면 clip(PPO식). 로그에 max_ρ·clip_frac로 나타남. |

---

## 1. 결과가 좋으면 논문 감인가?

**메커니즘은 novel이 맞다** (조사 확인: 정확한 선례 없음. [R³](https://arxiv.org/abs/2402.05808)=선형·비형식, [DSP-V2](https://arxiv.org/abs/2504.21801)=state 아닌 problem seed). "verifier-scored, tree-structured **leaf-first** seeding + **per-subgoal 보상** + on-policy"는 formal proving RL에 없던 조합.

**그러나 이것만으론 탑 학회엔 부족.** 정직한 갭:

| 약점 | 리뷰어 질문 |
|---|---|
| 베이스라인이 **"우리 rango"**(322/328/338) | 왜 published SOTA([Rango 논문](https://arxiv.org/abs/2412.14063), [DeepSeek-Prover](https://arxiv.org/abs/2504.21801))와 비교 안 했나 |
| **1.3B, CompCert 단일** | 다른 모델/벤치(miniF2F, Lean)에서도? 일반성? |
| 개선폭 작을 수 있음 | held-out +2~5개면 노이즈 아니냐 |
| **transfer 미확정** | 롤아웃 신호↑ ≠ test↑ (이번 프로젝트 일관 패턴). 36%는 학습셋이라 held-out이 안 오르면 "친숙성 부풀림"으로 반박 |

**판정**:
- held-out(1191/rand200)이 SFT→GRPO를 **노이즈 넘게** 이기고 + **ablation**(per-subgoal 보상 vs leaf 순서 vs s0 단계 분리)까지 하면 → **워크샵~중견 학회**.
- 지금 상태로는 "유망한 예비 결과 / 워크샵 tier".

**"HER/relabel의 특수형이면 novelty가 떨어지나?" — 정직한 판정**

"X는 Y의 특수형"이란 사실 자체는 novelty를 죽이지 않는다(GRPO도 policy gradient의 특수형, PPO도 TRPO계열의 특수형). 리뷰어가 보는 건 **원시개념의 최초성이 아니라 delta·이론·결과**. 단 **contribution 전체가 알려진 원시개념으로 환원되면** 약해진다. 그래서 정밀히 구분해야 한다:

1. **HER 원시개념**(실패한 **자기 궤적**의 달성 goal을 성공으로 relabel; [Andrychowicz 2017](https://arxiv.org/abs/1707.01495) 일반, [Aygün 2022](https://arxiv.org/abs/2112.10664) 정리증명) = **이미 있음**. 이걸 headline으로 내걸면 Aygün과 정면으로 겹쳐 **약함**.
2. **우리 현재 방법(bottom-up gold-subgoal)은 엄밀히는 HER가 아니다.** HER는 정책이 스스로 도달한 goal을 relabel하지만, 우리는 **gold prefix를 replay해 subgoal 상태에 정책을 갖다 놓고(reverse-curriculum) 그 subgoal을 닫게 학습**한다 — 데이터 소스가 "자기 hindsight"가 아니라 "gold 커리큘럼". HER스러운 건 "부분 성공에 보상"이란 **보상 규칙**뿐이고, 뼈대는 [R³](https://arxiv.org/abs/2402.05808)/[Florensa](https://arxiv.org/abs/1707.05300) 역커리큘럼 + subgoal 커리큘럼에 가깝다. → **HER 겹침 작음.**
3. **HER와 정말 겹치는 건 OSR/self-harvest 변형**(§3-B, §6) — 실패한 on-policy 롤아웃의 닫힌 subgoal harvest = 사실상 Aygün의 확장. 여기선 정직하게 "그들의 확장"으로 포지셔닝.

**HER가 못 가진(=우리 novelty) 축**: ① **트리 구조 bottom-up 커리큘럼**(HER엔 커리큘럼 구조 자체가 없음) · ② **subgoal 상태로 seed해 "그 지점부터 연습"**(HER는 시작상태를 안 옮김) · ③ **per-subgoal 보상 = horizon 분할** O(εT²/k) 이론(HER 논문에 없는 credit-assignment 기여) · ④ **canonicality→p_reach→transfer** 프레이밍 · ⑤ **§3-A decompose 제안 학습**(만들기+닫기 2수준, HER와 완전 무관 — 가장 강한 진짜 novelty).

**결론**: relabel **원시개념은 novel 아님**(HER). 하지만 우리 뼈대는 HER와 **다른 메커니즘**이고, HER-겹치는 부분(OSR)조차 on-policy-safety 이론(T1)·horizon 분할(T4)·verifier-perfect-reward와 결합하면 새로워진다. **Novelty는 relabel 단일 원시가 아니라 "조합 + 이론 + 도메인 결과"에 있다.** 논문 전술: relabel을 headline로 삼지 말고 Aygün을 눈에 띄게 인용해 "확장/차이"로 두고, ①~⑤(특히 ⑤ decompose 학습 + 이론)를 전면에.

---

## 2. +10% + all-CoqStoq + 다양한 비교 → 탑티어 가능?

**정직한 답: 현실적으로 경쟁권에 든다. 단 조건부.**

- **+10%p(held-out)**: SFT→GRPO 대비 +10%p면 **노이즈가 아닌 큰 이득**. 그 자체로 강한 결과. (지금 학습셋 롤아웃 +10%p가 held-out에서도 유지되면.)
- **all-CoqStoq(전 프로젝트)**: CompCert만이 아니라 CoqStoq 전체(여러 Coq 프로젝트)를 돌리면 "단일 벤치" 우려를 **부분** 해소(같은 Coq지만 다중 도메인).
- **다양한 알고리즘 비교**: 우리가 이미 가진 LUFFY/backward/DAPG/vDPO/PPO/DAPO/VAPO/revcurr + subgoal 계열 = 10+ 방법 대조표 → **thorough**.

**탑티어(NeurIPS/ICML/ICLR main)에 남는 리스크**:
1. **1.3B 단일 모델** — 스케일(7B) 또는 Lean/miniF2F(가장 표준 벤치) 검증이 있으면 안전. CoqStoq은 miniF2F만큼 established 아님.
2. **published SOTA 포지셔닝** — our-baselines만이 아니라 최선 published 수치 대비.

**결론**:
- **+10%p + all-CoqStoq + 다양한 비교 + 좋은 ablation + 이론(D) + 가능하면 decompose novelty(A)** → **탑티어 진지 경쟁권**. 보장은 아니나 real contender.
- 안전하게 하려면 **Lean/miniF2F 교차검증 1개** 또는 **더 큰 모델 1개**를 추가해 "Coq-only, 1.3B-only" 리스크를 닫는 것.
- 한 줄: **+10%p가 워크샵→탑티어 경쟁권으로 넘어가는 임계점**. 단 novelty(A)와 rigor(ablation·all-CoqStoq·다양한 비교), 이상적으로 cross-domain(Lean)이 함께여야.

---

## 3. Novelty 확장 아이디어 (A/B/C/D) + 구현 방법

### A. Decompose 제안 학습 — 가장 novel, headline감
**개념**: 지금은 subgoal을 *푸는* 것만 배움. 완전체의 진짜 병목은 **"언제/무엇을 decompose할지"**(s0에서 induction/assert를 치는 것). → 모델이 **decompose tactic을 제안**하게 하고, **그 결과 subgoal들의 solvability로 보상**(자기채점, on-policy). "subgoal 닫기 + subgoal 만들기" **2수준 목표** = formal proving RL에 없음. compositionality gap 직접 공략.

**구현**:
1. **롤아웃**: s0(또는 상위 노드)에서 모델이 첫 tactic(decompose 후보) 생성 → Coq 적용 → 생긴 자식 subgoal들 각각을 **현재(subgoal-학습된) 모델로 k회 probe 롤아웃**(per-subgoal 보상) → 자식 solve-rate 측정.
2. **보상**: decompose tactic의 shaped reward = 자식들의 (평균 or 최소) solve-rate. "모든 자식이 풀 만함(≥τ)"이면 그 decompose가 좋은 것.
3. **학습**: 그 보상으로 **첫 액션(decompose)에 GRPO**. s1~s3(subgoal 닫기)와 병행 → 만들기+닫기 동시.
4. **코드 재사용**: `mc_value()`(이미 grpo_rollout.py에 있음, [VinePPO](https://arxiv.org/abs/2410.01679) 스타일 MC value 추정)로 자식 solve-rate 추정. rollout_attempt에 "decompose 노드에서 멈춰 자식 solvability로 보상" 모드 추가.
5. **엔진 변경**: `decompose_reward` 플래그 → 첫 tactic 적용 후 자식마다 mc_value, decompose 보상 산출.

**리스크**: probe 비용(자식마다 k회) → 느림. τ·k 튜닝 필요.

### B. 이중 소스 — gold subgoal + self-harvested subgoal (HER)
**개념**: gold 트리 leaf(지금) + **실패한 s0 롤아웃에서 모델이 스스로 닫은 subgoal**을 둘 다 학습. 두 on-policy-safe 신호 결합. [HER-for-provers(Aygün 2022, 2112.10664)](https://arxiv.org/abs/2112.10664) 근거 있음.

**구현**:
1. s0 롤아웃(이미 수행) 중 **실패한 시도**에서 `harvest_subgoals.py`(이미 있음)로 **닫힌 subgoal subtree** 추출 → reward=1 데이터(self, on-policy).
2. gold leaf 커리큘럼 + self-harvested subgoal을 **합쳐** GRPO.
3. **코드 재사용**: `harvest_subgoals.py`를 s0 롤아웃 jsonl에 적용 → 합쳐서 gtrain. 추가 코드 최소.

**장점**: 구현 쉬움(도구 있음), 인용 근거, gold가 못 덮는 정리도 self-subgoal로 커버.

### C. 적응형 난이도 targeting — [AdaPrefix](https://arxiv.org/abs/2607.07674) 계열
**개념**: 각 스테이지 그룹의 **all-solved(N/N)·dead(0/N)는 둘 다 advantage=0 → gradient 0(낭비)**, **mixed만 신호**. 실측 분포(그룹 = 하나의 seed에서 뽑은 **G=6** 롤아웃 묶음; `SUBGOAL_GS` 기본 6, max_steps 16, max_retries 2 — 전부 속도용 축소).

> **⚠ 버전 표기** (아래 표는 여러 버전이 생기므로 어떤 실행인지 명시):
> - **[버전 A] 원판 subgoal** = `SFT→bottom-up-subgoal-GRPO` — s1/s2/s3 롤아웃을 **전부 SFT 고정**(off-policy), **w2**. (아래 표 = 이 버전.)
> - **[버전 B] cascade** = `SFT→cascade-subgoal-GRPO` — 롤아웃 정책을 **각 스테이지 init에 맞춤**(on-policy 정정: s1=SFT/s2=s1/s3=s2/s0=s3), **w4**. (`run_cascade_bigscale.sh`, 실행 후 아래 [버전 B] 표 갱신.)

**[버전 A — 원판 subgoal, s1/s2/s3 롤아웃=SFT 고정, w2]**
| 스테이지 | 그룹수 | all-solved | mixed(신호) | dead | 낭비(all-solved+dead) |
|---|---|---|---|---|---|
| **s1** (leaf, size≤2, per-subgoal 보상) | 324 | 134 (**41%**) | 119 (**36%**) | 71 (**21%**) | **63%** |
| **s2** (중간, size 3-5) | 17 | 3 (17%) | 6 (35%) | 8 (47%) | 64% |
| **s3** (큰, size≥6) | 3 | 0 (0%) | 0 (0%) | 3 (100%) | 100% |
| **s0** (완전체 root, Qed 보상) | 297 | 22 (7%) | 80 (**26%**) | 195 (**65%**) | 73% |

**[버전 B — cascade, on-policy 정정, w4, G=8]** *(실측 완료. 전 실험 비교: `grpo/MIXED_GROUP_SUMMARY.md`)*
| 스테이지 | 그룹수 | all-solved | mixed(신호) | dead | 낭비 |
|---|---|---|---|---|---|
| **s1** | 307 | 117 (38%) | 132 (**42%**) | 58 (18%) | 56% |
| **s2** | 17 | 2 (11%) | 7 (41%) | 8 (47%) | 58% |
| **s3** | 3 | 0 (0%) | 0 (0%) | 3 (100%) | 100% |
| **s0** (완전체) | 285 | 23 (8%) | 86 (**30%**) | 176 (61%) | 69% |

*(cascade는 원판[버전 A]보다 s1 mixed 36→42%, s0 mixed 26→30%로 소폭↑ — on-policy 효과. 그러나 held-out은 오히려 회귀(g2w4 오염 의심, w2 재측정중). "mixed↑≠test↑" — MIXED_GROUP_SUMMARY.md 핵심 통찰.)*

**읽는 법**(버전 A): 난이도가 오를수록(s1→s2→s3, 그리고 s0) all-solved가 줄고 dead가 는다 — s1은 easy-leaf라 all-solved(41%)가 많아 낭비, s0은 sparse full-theorem이라 dead(65%)가 많아 낭비. mixed(신호)는 어디서나 **26~36%뿐**이고 나머지 63~100%는 gradient 0. subgoal마다 **성공률~0.5인 seed를 자동 선택**하면 이 낭비를 mixed로 돌려 신호를 극대화(§3-C 구현). *(s3는 3그룹뿐이라 통계적 의미 약함 — max-per-thm 2로 큰 subgoal이 적게 뽑힘.)*

**구현**:
1. **엔진에 이미 있음**: `adapt_prefix=True` + `probe_k`. 각 subgoal-start 후보를 probe_k회 탐침 → 성공률~0.5 선택.
2. leaf 커리큘럼의 `starts`(여러 subgoal-start)를 adapt_prefix로 넘기면 정리별 sweet-spot 자동선택.
3. **대안**: seed 깊이 조절 — all-solved면 subgoal 안에서 더 얕게(어렵게), dead면 더 깊게(쉽게).
4. **코드 재사용**: `grpo-rollout-subgoal` alias에 `adapt_prefix` env 추가(현재 non-adapt).

**장점**: 낭비 64% 제거 → 효율↑, ablatable 컴포넌트.

### D. 이론적 프레이밍 — transfer gap을 canonicality + subgoal 분할로 bound

**세팅**
- 정책 π: next-tactic. 배포 시 **s0(정리)에서 시작해 자기경로로** tactic 생성 → Qed or 실패.
- subgoal 학습: gold prefix를 replay해 seed state `s`에 모델을 놓고 그 subgoal을 닫게 학습.
- 질문: state `s`에서 학습하면 배포(s0부터) 성능이 오르나?

**핵심량: p_reach(s)**
- `p_reach(s)` = 배포 정책 π가 s0에서 **자기경로로** state `s`를 방문할 확률.
- `s`에서 학습 → π의 `s`(및 근방) 행동 개선. 배포에서 이 개선을 "현금화"하려면 **π가 실제로 `s`에 가야** 함.
- 따라서 **transfer 이득 ∝ p_reach(s)**. 높으면(on-distribution) 전이됨, 낮으면(gold로만 도달) 낭비/역효과.

**정리 1 (canonical → p_reach 높음 → gap 작음)**
- **canonical seed** = decompose 선택이 거의 강제/자명한 상태 — 유일 귀납가설에 `induction`, 변수에 `destruct`. 결과 subgoal state는 **(s0, decompose tactic)에만 의존**, 특정 경로에 무의존.
- π가 그 자명한 decompose를 높은 확률로 침 → **p_reach 높음** → gap 작음.
- 대조: backward 깊은 seed(remaining=4)는 **긴 특정 gold 경로**(여러 idiosyncratic tactic)로만 도달 → π가 그 경로를 재현해야 → **p_reach 낮음** → gap 큼. → **backward 회귀의 이론적 이유.**

**정리 2 (per-subgoal 보상이 유효 horizon T를 쪼갬 → 복리오차 완화)**
- [Ross-Bagnell/DAgger](https://arxiv.org/abs/1011.0686): per-step 오차 ε인 정책의 배포 총오차 = **O(εT²)** (T=horizon; 틀린 state 방문 → 더 틀린 state로 복리).
- **완전체 학습**: T = 전체 증명 길이(CompCert 중앙값 ~14) → εT² 큼.
- **subgoal + per-subgoal 보상**: 각 subgoal 길이 `T_sub`(leaf는 1-3), 보상은 **subgoal 닫힘(T_sub step)** 에 부여(Qed=T step 아님).
- 증명이 k개 subgoal(각 ~T/k)로 분할되면: 총오차 ~ **k·ε·(T/k)² = εT²/k** → 복리오차가 **k배 감소**.
- 직관: 긴 궤적 하나(오차 복리 T²)를 짧은 궤적 k개(각 T²/k², 합 T²/k)로 쪼갬. per-subgoal 보상이 "언제 신용을 주는가"를 subgoal 경계로 당겨 T를 T_sub로 축소.

**종합**
| | p_reach (transfer) | 유효 horizon (복리) |
|---|---|---|
| canonical subgoal seed (이것) | **높음** (전이 O) | **T_sub 짧음** (약함) |
| gold-injection/backward | 낮음 (전이 X) | T 김 (강함) |
→ gold-injection 실패(LUFFY/backward)와 canonical-subgoal 성공 가능성을 **동시에** 설명.

**bound 스케치**
- 배포 오차 ≲ **O(ε_sub · T²/k)**, 단 seed가 canonical(p_reach≈1)일 때. (ε_sub = subgoal state에서의 per-step 오차.)
- transfer gap ≲ **Σ_s (1 − p_reach(s)) · v(s)** (v(s)=s 학습가치): off-distribution seed일수록 낭비. canonical이면 p_reach≈1 → gap≈0.

**goal-conditioned RL / HER 연결**
- 달성한 subgoal을 goal로 relabel([HER, Andrychowicz 2017](https://arxiv.org/abs/1707.01495); [HER-for-provers Aygün 2022](https://arxiv.org/abs/2112.10664))은 **on-policy-safe**(달성 state는 π 분포 위). 우리 **per-subgoal 보상이 이 relabel의 특수형** — "닫힌 subgoal을 성공으로 취급".

**실증 (우리 데이터로 바로 가능)**
1. **p_reach(s) 측정**: 배포 정책 π를 s0에서 롤아웃(우리 s0 롤아웃 데이터) → 어떤 subgoal state를 통과하는지 기록 → p_reach(s) = 그 state 통과 비율.
2. **p_reach ↔ transfer 이득 상관**: 높은 p_reach seed를 학습한 게 root 성공을 더 올리나(seed별 ablation).
3. **canonical vs idiosyncratic**: induction/destruct-직후 seed의 p_reach vs backward-deep seed의 p_reach 비교(후자 낮아야).
4. **εT²/k 스케일링**: 배포 오차 vs 분할수 k (subgoal 많이 쪼갠 정리가 오차 적어야).

**장점**: 이번 프로젝트의 covariate-shift 분석(왜 gold 계열이 다 실패했나)이 그대로 이론 절이 되고, 실증도 기존 롤아웃 데이터로 가능. 이론(정리1·2) + 실증(1~4)이 있으면 논문 강도가 크게 오름.

### D+. 이론적 배경을 더 강화하는 방법 (강한 순)

지금의 bound는 "스케치". 아래로 격상하면 이론 기여가 논문급이 됨.

**1. 스케치 → 정식 정리 (가정 명시 + 증명)**
- 가정을 명확히: **A1(ε-canonical)** 모든 seed s에 p_reach(s) ≥ 1−δ. **A2(분할)** 증명이 k개 subgoal(각 길이 ≤ T/k). **A3(verifier)** 보상 정확(0/1, 편향 0).
- **정리**: 배포 suboptimality ≤ O(ε_sub·T²/k + δ·V_max·T). → 첫 항=분할 이득, 둘째 항=off-canonical seed의 대가. "framing"이 아니라 "theorem".

**2. Sample-complexity via 계층 RL(options) — 표준적·강력**
- 각 subgoal = **option**([Sutton-Precup-Singh 1999](https://www.sciencedirect.com/science/article/pii/S0004370299000521), arXiv 없음). option-level MDP는 유효 horizon T/k.
- **결과**: subgoal 분할이 sample complexity를 **k배(또는 credit-assignment까지 하면 k²배)** 감소. 계층 RL의 확립된 sample-complexity 이득을 우리 세팅에 정리로.

**3. Lower bound — "필요성" 증명 (가장 강한 주장)**
- **sparse full-theorem RL은 horizon T에 지수적**: s0 균일탐색 성공확률 ~p^T → 필요 롤아웃 ~(1/p)^T.
- subgoal 분할은 이를 **k·(1/p)^(T/k)** 로 → 지수를 T/k로 축소.
- 메시지: decomposition이 "도움"이 아니라 **필수**(없으면 지수적으로 불가능). Lower bound는 리뷰어에게 강함.

**4. Goal-conditioned RL / HER unbiasedness**
- per-subgoal 보상 = achieved-subgoal **relabel**([HER, Andrychowicz 2017](https://arxiv.org/abs/1707.01495)). HER가 policy gradient를 편향시키는 조건을 우리 세팅에 적용.
- **증명 목표**: canonical seed에서 relabel은 **unbiased**(또는 bounded bias) → GRPO 그래디언트가 참 목적으로 수렴. (일반 HER은 편향 있으나, verifier+canonical이면 무편향 특수 케이스라는 게 새로움.)

**5. Monotonic improvement / policy iteration**
- expert-iteration 단조개선([Polu&Sutskever 2020](https://arxiv.org/abs/2009.03393))을 per-subgoal로 확장: verifier 성공만 강화 → policy iteration → 성능 **단조 non-decreasing**(증명). GRPO의 unbiased gradient(RLOO baseline)와 결합.

**6. Verifier = perfect reward 프레이밍 (RLHF와 차별화)**
- verifier는 정확한 0/1 → **reward-model 편향 없음**(RLHF 대비). 유일 문제 = 탐색·credit assignment.
- 기여 재정의: "**perfect verifier 하에서 subgoal 분할이 탐색·credit 예산을 (near-)최적 배분**". RLHF 이론(보상 오지정)과 다른 축이라 novelty.

**7. 이론-실증 밀착 (theory-driven experiments)**
- 정리의 예측을 **직접 실험으로 검증**: 정리1→p_reach 상관, 정리2→εT²/k 스케일링, §2→k별 sample complexity. 예측이 맞으면 "validated theory"로 격상.

**우선순위**: **1(정식 정리) + 3(lower bound)** 이 가장 임팩트 — "분할이 필요조건"이라는 하한 + "canonical이면 전이 보장"이라는 상한. 5(단조개선)로 수렴성, 6(perfect verifier)로 RLHF와 차별화, 7로 실증 밀착. 이 중 3~4개면 이론 절이 논문의 강한 기둥이 됨.

---

## 추천 로드맵
1. **1차 관문**: 지금 실행의 held-out 1191(비교 A)이 SFT→GRPO 338을 넘는지 확인.
2. 넘으면 → **A(decompose 제안) + D(이론)** 를 headline으로, **B/C**를 ablation/보강으로.
3. **all-CoqStoq + 다양한 방법 대조표** + (가능하면) **Lean/miniF2F 또는 큰 모델** 1개 → 탑티어 경쟁권.
4. 핵심 스토리: **"subgoal을 만들고 푸는 것을 동시에 배우는 verifier-scored curriculum RL — covariate-shift를 canonicality로 회피"**.

**정직한 전제**: 이 모든 건 held-out transfer(비교 A)가 확인돼야 성립. 안 되면 novelty와 무관하게 "롤아웃↑ test↔"의 또 다른 사례가 됨.

---

## 4. "subgoal만 GRPO"보다 더 좋을 수 있는 방법 (다른 축)

subgoal-GRPO는 "**어려운 문제를 쉽게 쪼개기**"라는 한 축. sparse-reward(root 74% dead)를 공략하는 다른 축들이 있고 일부는 더 임팩트가 큼.

| 축 | 방법 | 임팩트 |
|---|---|---|
| 난이도 낮추기 | subgoal 커리큘럼 (지금) | 중 |
| **더 잘 탐색(증명 더 찾기)** | 검색 유도 학습 | **높음(SOTA 방식)** |
| 더 촘촘한 보상 | process/dense reward | 중~높 |
| **자기개선 루프** | expert iteration/STaR | 높음(가장 깨끗) |
| decompose를 배우기 | 제안 학습(§3-A) | 높음(병목 직공) |

### ① 검색 유도 학습 (best-first/MCTS로 증명 찾아 학습) — 천장 가장 높음
독립 롤아웃 대신 **트리 검색(MCTS/RMaxTS/HTPS)으로 증명을 찾고, 그 증명으로 학습**. 검색은 정책 혼자 못 찾는 증명을 찾음(커버리지↑)→학습신호↑→정책↑. **SOTA 프루버([DeepSeek-Prover](https://arxiv.org/abs/2504.21801), [HTPS](https://arxiv.org/abs/2205.11491))가 다 이 방식.** subgoal="쉬운 문제 만들기", 검색="더 잘 탐색"인데 **탐색 개선이 대개 더 큰 이득.** 인프라에 RMaxTS/BFS-Prover alias 이미 있음.

#### ①-심층: GRPO × MCTS — 이득 있나? (우리 로그 근거)

**한 줄 판정: 이론적으로 우리 두 병목(§9)에 정확히 들어맞아 이득 가능성 높음. 단 비용·coq-lsp 병목·GRPO 편향 주의 때문에 "full MCTS-in-loop"보다 싼 변형부터.**

**왜 우리 상황에 특히 맞나 (§9 메트릭과 연결)**
- **병목1: dead 63~73%(신호 0).** flat GRPO는 seed당 G개 **i.i.d.** 롤아웃 → 어려운 정리는 G개 다 실패=dead. MCTS는 **UCB로 탐색·백트래킹·트리 공유**로 flat 샘플링이 놓친 증명을 찾음 → dead(0/N)를 ≥1 성공 그룹으로 전환 = **없던 그래디언트를 만든다.** sparse-reward의 정공법.
- **병목2: entropy 0.11(collapse).** 정책이 거의 결정적이라 flat 샘플은 **같은 실패 tactic만 반복**(§9). MCTS의 UCB 탐색은 **정책 엔트로피와 무관하게 외부에서** 탐색을 공급 → collapse된 정책에 **가장 잘 듣는 보완**. (clip-higher/entropy-bonus가 정책 내부 탐색을 살리는 것과 상보적.)
- **credit assignment.** 트리 노드별 MC value(코드 `mc_value` 이미 있음, [VinePPO](https://arxiv.org/abs/2410.01679))로 **step-level advantage** → outcome-only GRPO의 약한 advantage(avg_group_std 0.12~0.16)를 촘촘하게.

**변형 3가지 (싼 것 → 비싼 것)**
| 변형 | 방식 | 비용 | 우리 적합 | 코드 |
|---|---|---|---|---|
| **(a) search-for-data** (STaR류) | RMaxTS/BFS로 **dead 정리의 증명을 찾아** positive 학습데이터로 추가 | 낮음(추론시 1회) | **높음** — dead 그룹 직접 채움 | RMaxTS/BFS alias 있음 |
| **(b) tree-MC-advantage GRPO** | 트리 노드 `mc_value`를 step-level advantage로(VinePPO식) | 중 | 높음 — credit↑ | `mc_value` 있음 |
| **(c) full MCTS-in-loop** (AlphaZero류) | policy+value를 MCTS로 공동 학습 | **높음** | 천장 최고이나 1.3B·단일GPU엔 과함 | 신규 |

**정직한 한계**
- **비용·coq-lsp 병목이 최대 리스크.** 증명탐색 속도는 GPU가 아니라 **verifier(coq-lsp) 호출 수**가 지배 — MCTS는 노드 확장마다 tactic 적용+goal 체크라 verifier 호출이 몇 배. 이미 롤아웃 타임아웃 이슈가 있던 단일-GPU 환경엔 부담. → **(a)부터.**
- **idiosyncratic tail엔 여전히 무력.** 방금 본 size-6 subgoal(특정 lemma 체인 `F2R_Zabs`·`Int64.lo_ofwords`…)처럼 정책의 per-step 확률이 ~0이면 MCTS도 현실 예산 내 못 찾음(Coq tactic 분기 폭 큼). MCTS는 **중간 난이도 band**를 살리지, 완전 dead tail은 subgoal 분해가 답.
- **GRPO 그룹-baseline 편향 주의.** MCTS 궤적은 **상관됨**(prefix 공유·UCB 비균일 샘플) → group-relative advantage의 무편향(§6 T2) 깨짐. → naive 그룹평균 대신 **(b) tree-MC-advantage**나 importance 보정 필요.
- **논문 ablation 순수성.** MCTS를 코어에 섞으면 "이득이 subgoal 덕인가 검색 덕인가"가 흐려짐 → **subgoal 코어와 분리해 "검색을 얹으면 얼마 더"의 스택 실험/천장 비교**로 두는 게 스토리에 유리.

**추천**: **(a) search-for-data**를 dead 정리에 먼저(가장 싸고 proven, expert-iteration ②와 자연 결합) → 이득 확인되면 **(b) tree-MC-advantage**로 credit 강화. **(c) full MCTS-in-loop**은 스케일(7B/멀티GPU) 확보 후. 즉 **"이득 있음, 단 (a)→(b) 순으로, 코어와 분리."**

#### ①-심층2: MCTS를 "학습 과정"에 쓰면 효과 있나? (Tree-GRPO 등 + all-solved 살리기 + 이론)

**질문**: 추론(inference)뿐 아니라 **학습(training) 루프에서 MCTS**를 쓰면? 특히 all-solved 41%(gradient 0)도 "다양한 exploration"으로 살아나나?

**GRPO+MCTS-at-training은 이미 존재한다 (핵심 선행):**
- **[Tree-GRPO](https://arxiv.org/abs/2509.21240)** (Tree Search for LLM Agent RL) — flat 그룹 샘플링을 **트리 샘플링**으로 교체. 공유 prefix로 예산 내 롤아웃↑ + **outcome 보상에서 step-level process 신호** 추출, intra/inter-tree 이중 group advantage. **이론: intra-tree GRPO ≡ step-level DPO**(등가성). 11 데이터셋 최대 +69%, 예산↓.
- **[ReST-MCTS*](https://arxiv.org/abs/2406.03816)** (NeurIPS 2024) — MCTS로 증명/추론 trace 수집 + **정답에서 process 보상을 역추정**(PRM) → policy·PRM 공동 self-training 반복.
- **[TreeRL](https://arxiv.org/abs/2506.11902)** — on-policy 트리 검색 RL.

**"all-solved도 MCTS로 살아나나?" — 방향은 맞지만 메커니즘 정정.**
- binary Qed + flat 샘플이면 all-solved는 **분산 0**이라 exploration을 아무리 늘려도 gradient 0(다 성공하므로). **"다양한 exploration" 자체로는 안 살아난다.**
- 그러나 **트리 내부 노드 value가 서로 다르면, outcome이 균일(all-solved)이어도 step-level advantage에 분산이 생긴다** → gradient. 즉 Tree-GRPO/ReST-MCTS*는 **process-level advantage** 덕에 all-solved를 살린다(탐색 다양성이 아니라 **트리 value 분산**이 핵심). 결과적으로 MCTS-at-training은 우리 낭비의 **양쪽**을 동시에 공략: **dead 살리기**(검색이 성공을 찾음=커버리지) + **all-solved 살리기**(트리 process 분산).

**우리만의 강점(차별점): verifier가 process 보상을 공짜로 "정확히" 준다.** ReST-MCTS*는 PRM으로 process 보상을 *추정*(오차·편향)하지만, 우리는 **subgoal 닫힘(goal 수 하락) = 정확한 0/1 process 신호** → PRM 불필요. "**verifier-exact process reward tree-RL**"은 process-RL 계열과 구별되는 새 포지션.

**이론(정직하게):**
- MCTS = **policy improvement operator** `π'=MCTS(π)`([AlphaZero](https://arxiv.org/abs/1712.01815)). **단 제한된 sim에선 개선 보장 없음** — root의 모든 action을 방문해야 보장.
- **[Gumbel MuZero/AlphaZero](https://openreview.net/forum?id=bERaNdoegnO)** (Danihelka 2022, ICLR) — Gumbel top-k·비복원 샘플로 **few-sim에서도 정책개선 보장**. 우리처럼 **sim 예산이 적은(coq-lsp 비쌈)** 세팅엔 이 Gumbel식이 이론적으로 정확히 맞는 선택.
- Tree-GRPO의 등가성(≡ step-DPO)은 "정리"지 단조개선 bound는 아님 → 우리 §6 T3(단조개선)와 결합하면 보강 여지.

**착안한 개선 알고리즘 아이디어:**
1. **subgoal-seed × Tree-GRPO 융합** — 각 subgoal seed에서 flat G개 대신 **트리 전개**(공유 prefix), intra-tree process advantage로 **all-solved·dead 동시 살림**. 우리 §9 낭비 63~73%의 정공 해법.
2. **per-subgoal 보상 = verifier-exact process reward를 트리 step advantage로** — PRM 없이 ReST-MCTS*의 이득(process 신호)을 편향 없이.
3. **Gumbel top-k로 tactic/subgoal 확장 선택** — few-sim 개선보장(단일-GPU·적은 예산에 적합), §6 보장 스펙트럼에 "Gumbel-guaranteed 행" 추가.

**정직한 한계**: 여전히 coq-lsp 호출이 병목이나, Tree-GRPO의 **공유-prefix가 예산당 롤아웃을 늘려 naive MCTS보다 오히려 쌈**(완화 요소). all-solved 살리기는 **process 보상/트리 value 설계**에 달려 있고, 단순 트리 확장만으론 안 됨.

### ② Expert iteration / STaR — 가장 깨끗·proven
s0 롤아웃 → **푼 완전체 증명만 SFT → 재롤아웃 → 반복.** self-success만 쓰니 covariate shift 0, 단조개선 이론보장([Polu&Sutskever](https://arxiv.org/abs/2009.03393)). subgoal보다 단순. **subgoal이 이걸 이겨야** 복잡도가 정당화됨(= 필수 대조군).

### ③ Dense/process 보상 — dead 74%를 살림
s0 롤아웃 74%가 dead(신호 0). **닫은 goal 수/QED까지 거리**로 부분보상([QEDCartographer](https://arxiv.org/abs/2408.09237) 스타일)→dead 그룹도 신호. 엔진에 value_fn/shaping_coef 훅 이미 있음.

### ④ Decompose 제안 학습 — §3-A와 동일(병목 직공)

### 핵심: 상보적, 조합이 최강
배타적이 아님. **subgoal(난이도↓) + 검색(탐색↑) + expert-iteration(자기개선)** 조합이 가장 강함. SOTA = "좋은 정책 + 검색 + 반복".

### 현실적 추천 순서
1. 지금 subgoal 결과(비교 A) 확인.
2. **검색 유도 학습(RMaxTS로 증명 수집→학습)** 을 subgoal 위에 얹기 — 정책↑×탐색↑ 조합 효과.
3. **expert iteration 대조군** — subgoal이 정말 이기는지 확인.
4. **dense 보상**(goals-closed 부분크레딧)으로 s0 dead 74% 살리기 — 가장 싼 개선.

→ "subgoal만 GRPO"보다 **subgoal + 검색유도 + (dense 보상)** 조합이 더 좋을 가능성 높음.

---

## 5. 용어: "seed"란 (적응형 난이도 §3-C 관련)

**seed = 모델이 롤아웃을 시작하는 지점** = gold prefix를 Coq에 replay해 만들어준 시작 상태(`initial_proof`). 모델은 그 seed에서부터 자기 tactic을 생성한다.

```
initial_proof(seed) = "Proof. induction 1; intros; simpl."
        └── gold로 여기까지 만들어줌 = seed ──┘
모델은 이 상태(subgoal {base, 귀납})에서 시작해 롤아웃
```

각 seed는 **난이도(성공률)** 를 가짐:
- **쉬운 지점**(작은 leaf, Qed 코앞) → 6/6 다 풀림 = **all-solved**(gradient 0)
- **어려운 지점**(큰 subgoal, 갈 길 멈) → 0/6 = **dead**(gradient 0)
- **~0.5 성공** → **mixed** = 학습신호 있음

실측(이번 실행) — 네 스테이지 모두 낭비가 큼(all-solved+dead가 gradient 0):

| 스테이지 | all-solved | mixed(신호) | dead | 낭비 |
|---|---|---|---|---|
| s1 (leaf) | 41% | 36% | 21% | 63% |
| s2 (중간) | 17% | 35% | 47% | 64% |
| s3 (큰) | 0% | 0% | 100% | 100% |
| s0 (root) | 7% | 26% | 65% | 73% |

즉 어느 스테이지든 신호(mixed)는 **26~36%뿐**, 나머지는 낭비. s1은 너무 쉬워(all-solved) 낭비, s0은 너무 어려워(dead) 낭비. 적응형 seed는 이 둘을 mixed 쪽으로 당김.

**적응형 seed 선택(§3-C)** = subgoal마다 seed 지점을 조절해 성공률을 ~0.5로:
- **(a) seed 깊이 조절**: all-solved면 seed를 더 얕게(gold 덜 줌=어렵게), dead면 더 깊게(gold 더 줌=쉽게).
- **(b) 후보 중 선택**: 정리마다 여러 seed 후보를 probe_k회 탐침 → 성공률~0.5인 것만 수집(엔진 `adapt_prefix`).

즉 seed = "모델을 어디에 놓고 시작시킬지". 지금은 고정이라 64%가 낭비되고, 적응형은 seed를 조절해 mixed(신호)를 극대화.

**§3-D의 p_reach와의 관계**: seed의 **깊이·canonicality가 p_reach를 결정**. 얕고 canonical한 seed(induction 직후)는 p_reach 높음(전이 O), 깊은 seed(backward식)는 p_reach 낮음(전이 X). 적응형은 난이도(~0.5)를 맞추되 **canonical zone 안에서** 골라야 전이까지 챙김.

---

## 6. 이론적 보장 알고리즘 설계 (OSR + 보장 스펙트럼)

지금의 gold-subgoal 방법은 **경험적**(canonical seed가 대략 안전하다는 heuristic). 이를 **보장 있는 알고리즘**으로 격상한다. 핵심: 학습 상태를 **정책 자신의 분포**로 옮기면 covariate-shift가 구조적으로 0이 되고, per-subgoal 보상이 horizon을 쪼개 복리오차를 줄인다.

### 6.1 형식화 (MDP · 목적 · covariate-shift 문제)
- episodic MDP `M=(S,A,P,r,T)`: `S`=proof state(goals+context), `A`=tactic, `P`=Coq(유효 tactic이면 결정적), `r`=**verifier**(Qed 또는 subgoal 닫힘=1, 아니면 0 — **정확, 편향 0**), `T`=최대 step.
- 정책 `π_θ: S→Δ(A)`. 목적 `J(π)=E_{θ0~D}[1{π가 s0(θ0)에서 T내 Qed}]`.
- 점유분포 `d^π_h`=step h에서 π의 state 분포(s0 시작), `d^π=(1/T)Σ_h d^π_h`.
- **covariate shift([Ross-Bagnell](https://arxiv.org/abs/1011.0686))**: gold를 오차 `ε_gold=E_{s~d^gold}[π≠expert]`로 모방하면 `J(expert)−J(π) ≤ O(ε_gold·T²)`(복리). DAgger(π 자신 분포 `d^π`로 학습) → `O(ε_π·T)`(선형).

### 6.2 설계 목표 (달성할 보장 4가지)
- **G1(무 covariate-shift)**: 학습 상태 ∈ `d^π` → transfer gap `Σ_s(1−p_reach(s))v(s)=0`.
- **G2(unbiased gradient)**: advantage가 참 목적의 무편향 추정.
- **G3(단조개선)**: 각 라운드 `J(π_{r+1})≥J(π_r)`(policy iteration).
- **G4(복리 완화)**: per-subgoal 보상으로 `O(εT²)→O(εT²/k)`.

### 6.3 알고리즘: OSR (On-policy Subgoal Reinforcement)
```
입력: SFT warmup 정책 π_0 (gold-SFT; 탐색 부트스트랩), 브랜치수 k, 라운드 R
for r = 0..R-1:
  for 각 정리 θ:
    (1) π_r 로 s0(θ)에서 G개 on-policy 롤아웃 → 방문 state 전부 기록
        (특히 decompose 직후 subgoal state = goal 수 증가 지점)
    (2) 각 방문 subgoal state s 에서 k개 추가 브랜치 롤아웃(같은 s, 온도샘플)
        → V̂(s) = focused subgoal 닫힘 비율 (per-subgoal 보상; mc_value 재사용)
    (3) advantage(같은 s 그룹 baseline, RLOO): Â(s,a)= R(s,a) − (1/(k−1))Σ_{j≠i}R_j(s)
    (4) HER: 전체는 실패했으나 닫힌 subgoal 은 성공으로 relabel(reward=1) 추가
             (harvest_subgoals 재사용)
  (5) Â 로 policy gradient 업데이트 → π_{r+1}
```
**요점**: seed가 gold가 아니라 **π 자신이 방문한 subgoal state** → p_reach=1(구조적). 브랜치(2)로 무편향 MC value, RLOO(3)로 무편향 advantage, HER(4)로 실패 롤아웃의 닫힌 subgoal 재활용.

### 6.4 정리 + 증명 스케치 (가정 명시; design-doc 수준, 논문엔 완전증명 필요)

**T1 (on-policy 안전 = 무 covariate-shift).** *가정 A1*: OSR은 `s~d^{π_r}`(π_r 자신 롤아웃)에서만 학습.
*주장*: 학습분포 = 배포분포(`d^train=d^{π_r}`), importance ratio=1 → **transfer gap=0**. 따라서 `J`-gap은 BC의 `O(ε T²)`가 아니라 **[DAgger](https://arxiv.org/abs/1011.0686)의 `O(ε_π T)`**(per-subgoal이면 아래 T4로 더 축소).
*증명 스케치*: 학습된 모든 state는 π_r이 s0에서 실제 방문 → 방문빈도=점유 `d^{π_r}(s)>0`, `p_reach(s)=1`. gap항 `Σ(1−p_reach)v=0`. ∎

**T2 (무편향 advantage).** *가정 A2*: `V̂(s)=(1/k)Σ_i R_i(s)`, k개 독립 브랜치.
*주장*: `E[V̂(s)]=V^{π_r}(s)`이고 RLOO baseline의 `Â(s,a)=R(s,a)−(1/(k−1))Σ_{j≠i}R_j(s)`는 참 advantage `A^{π_r}(s,a)`의 **무편향** 추정.
*증명*: MC 평균은 value의 무편향 추정; leave-one-out baseline은 샘플 액션과 독립 → 무편향([Kool et al. 2019 RLOO](https://openreview.net/forum?id=r1lgTGL5DE)). ∎

**T3 (단조개선).** *가정 A3*: verifier 정확(보상 편향 0), step size 작음, 충분탐색(개선가능 state가 확률>0로 방문).
*주장*: 자기검증 성공을 on-policy로 강화 = 근사 policy iteration → `J(π_{r+1}) ≥ J(π_r) − O(η²)`(작은 η에서 단조 non-decreasing).
*증명 스케치*: T2로 무편향 advantage → PG가 `J` 상승 방향; T1(on-policy)+정확보상으로 편향 없는 상승 → 작은 η에서 단조(표준 PG 개선정리 + expert-iteration 단조성 [Polu-Sutskever 2020](https://arxiv.org/abs/2009.03393)). gold-injection은 이 조건(무편향·on-policy)을 깨서 단조성 없음(→ backward 회귀 설명). ∎

**T4 (복리 완화).** *가정 A4*: 증명이 k개 subgoal(각 길이 ≤ T/k)로 분해, per-subgoal 보상이 subgoal 닫힘에 credit.
*주장*: 학습정책의 복리오차 `O(εT²/k)` (Qed-only credit의 `O(εT²)` 대비 k배↓).
*증명 스케치*: per-subgoal 보상이 길이-T credit 문제를 **독립 길이-(T/k) 문제 k개**로 변환. 각 복리 `O(ε(T/k)²)`, 합 `k·ε(T/k)²=εT²/k`. ∎

**종합**: T1(gap=0)+T4(복리 εT²/k) → 배포 suboptimality `≲ O(ε_sub·T/k)` 수준(선형×분할). T3로 라운드 단조개선. **gold 계열이 다 실패한 이유**(off-policy=T1 위배, Qed-only=T4 미적용, 편향baseline=T2 위배)를 한 프레임으로 설명.

### 6.5 보장 스펙트럼 (coverage ↔ guarantee 트레이드오프)
| 방법 | seed 출처 | 보장 | coverage | 비용 |
|---|---|---|---|---|
| **OSR(순수 on-policy)** | π 자신 방문 subgoal | T1~T4 **완전보장**(gap=0) | π가 도달하는 것만(좁음) | 브랜치 k배↑ |
| **p_reach-filtered gold** | gold subgoal 중 측정 p_reach≥1−δ만 | gap ≤ **δ·V_max·T**(bounded) | 중간 | probe 비용 |
| **unfiltered gold(현재)** | gold subgoal 전부 | gap 보장 없음(canonical heuristic) | 넓음 | 싸다 |
- **핵심 통찰**: on-policy를 완화할수록 coverage↑, 보장↓. **논문 기여 = 이 스펙트럼을 특성화**하고 OSR/filtered에 bound를 증명, 실증으로 트레이드오프를 보임.
- **gold-SFT warmup의 역할(형식화)**: OSR은 π가 subgoal state를 **방문해야** 작동. gold-SFT가 decompose 비율↑(롤아웃 성공 22%→27%)로 방문분포를 확장 → "on-policy subgoal RL을 가능케 하는 탐색 부트스트랩". 즉 SFT는 covariate-shift 없는 방식으로 d^π의 support를 넓힌다.

### 6.6 현재(실행중) 방법과의 관계
현재 SFT→bottom-up-subgoal-GRPO는 **unfiltered gold-subgoal**(스펙트럼 3행) — 넓은 coverage, 보장은 canonicality heuristic. OSR/filtered로 옮기면 **보장을 얻는 대신 coverage를 좁힘**. 논문 실험은 **셋 다 돌려** "현재는 왜 되(안 되)나 + 보장버전은 얼마나 안전한가"를 대조.

---

## 7. 이론 뒷받침 실험 설계 (각 정리 ↔ 실험)

정리마다 **예측 → 측정법 → 재사용 코드**를 명시. 대부분 기존 데이터/도구로 가능.

### E1 — p_reach → transfer (T1 검증)
- **측정**: π를 s0에서 롤아웃(우리 s0 롤아웃 데이터) → 각 gold-subgoal seed state `s`를 π가 통과하는 비율 = `p_reach(s)`(state 매칭: 정규화 goals 해시).
- **실험**: seed를 p_reach로 3분위(low/mid/high) → 각 bin만으로 학습한 모델의 **held-out 개선** 측정.
- **예측(T1)**: high-p_reach bin → 개선 큼; low-p_reach bin → 개선≈0 또는 회귀. → p_reach↔transfer 링크 입증.
- **코드**: s0 롤아웃 jsonl + build_leaf_subgoal_curriculum 의 state, 분위 분할 스크립트만 추가.

### E2 — 복리 O(εT²/k) 스케일링 (T4 검증)
- **측정**: 정리를 분해수 `k`(subgoal 개수)로 그룹화. 각 그룹의 per-step 오차 `ε`(INVALID 비율)와 배포 오차 측정.
- **실험**: **per-subgoal 보상** vs **Qed-only 보상** 두 모델의 (배포오차 vs k) 곡선.
- **예측(T4)**: per-subgoal은 오차 ∝ `T²/k`(k 클수록 오차↓), Qed-only는 ∝ `T²`(k 무관). 곡선 fit로 확인.
- **코드**: 롤아웃의 goal-수 궤적에서 k 계산(build_leaf_subgoal 재사용), 두 보상 모드(SUBGOAL_REWARD 0/1) 각 학습.

### E3 — 무편향 advantage (T2 검증)
- **측정**: 브랜치 k개 `V̂(s)` vs 다수 브랜치 `V^π(s)`(정답근사). k↑에서 `V̂` 평균이 수렴(무편향), 분산은 1/k.
- **실험**: baseline ablation — **RLOO(무편향)** vs **std-정규화([Dr.GRPO](https://arxiv.org/abs/2503.20783) 편향)** → gradient 편향/분산·최종 성능 비교.
- **예측(T2)**: RLOO 무편향, std-정규화는 그룹크기 편향. mc_value로 V̂ 측정.

### E4 — 단조개선 (T3 검증)
- **측정**: OSR을 R라운드 → `J(π_r)`(held-out) 라운드별 plot.
- **예측(T3)**: **단조 non-decreasing**. 대조로 gold-injection([LUFFY](https://arxiv.org/abs/2504.14945))은 비단조(회귀) → T3 가정 위배가 회귀의 원인임을 실증.

### E5 — canonicality → p_reach → transfer (D-정리1 직접 검증)
- **측정**: gold-subgoal seed를 decompose 종류로 분류 — **구조적**(induction/destruct/case=canonical) vs **특정-lemma**(apply X=idiosyncratic).
- **예측**: 구조적 seed는 p_reach 높음(E1) + transfer 큼; 특정-lemma seed는 p_reach 낮음 + transfer 작음. → canonicality→p_reach→transfer 사슬 전체 입증.
- **코드**: seed의 마지막 tactic 파싱으로 분류.

### E6 — 보장 스펙트럼 트레이드오프 (6.5 검증)
- **실험**: **OSR / p_reach-filtered gold / unfiltered gold(현재)** 셋을 같은 조건으로 학습·held-out 평가.
- **예측**: OSR=최고 안전성(전이율 높음, coverage 좁음), filtered=중간, unfiltered=넓지만 위험(회귀 가능). coverage×전이율 트레이드오프 곡선.

### E7 — 이론-관련 ablation (컴포넌트 분리)
- **per-subgoal 보상 ON/OFF**(T4: horizon 분할 효과) — `SUBGOAL_REWARD` 토글.
- **on-policy seed vs gold seed**(T1: p_reach 효과) — OSR vs 현재.
- **SFT warmup ON/OFF**(6.5: 탐색 부트스트랩) — init 토글.
- **RLOO vs std-norm baseline**(T2: 무편향).
- **출력**: 각 컴포넌트의 held-out 기여 + 이론 예측과의 일치 여부표.

### 실험-정리 매핑 요약
| 정리 | 실험 | 핵심 예측 |
|---|---|---|
| T1(gap=0) | E1, E5, E7 | high-p_reach·canonical seed만 전이 |
| T2(무편향) | E3, E7 | RLOO 무편향, V̂ 수렴 |
| T3(단조) | E4 | OSR 단조↑, LUFFY 비단조 |
| T4(εT²/k) | E2, E7 | per-subgoal이 오차를 1/k로 |
| 스펙트럼 | E6 | coverage↔guarantee 트레이드오프 |

**논문 스토리 완결**: (이론) OSR가 T1~T4 보장 → (스펙트럼) 현재 방법은 그 완화형 → (실증) E1~E7이 정리 예측을 확인 → "verifier 하에서 on-policy subgoal 분할이 covariate-shift를 회피하며 복리오차를 1/k로 줄인다"는 **이론+실증 일치**가 핵심 기여.

---

## 8. 참고문헌 + 우리와의 차이 (한 문장, 주어·목적어 명시)

**우리 방법 = SFT→bottom-up-subgoal-GRPO**: *우리는* gold 증명 트리를 goal-수로 복원해 **leaf→root로 분할**하고, 각 **subgoal 경계 state에 seed**해 **per-subgoal verifier 보상**으로 on-policy GRPO를 돌린다 (Coq/CompCert, 1.3B).

> 표기: **발표처(학회/저널) 연도**. `arXiv preprint`는 미발표(또는 발표처 미확인) 프리프린트, 연도는 arXiv ID(YYMM)로 확정.

### 8.1 가장 가까운 선행 (반드시 구별)
- **R³ — Reverse Curriculum RL** ([2402.05808](https://arxiv.org/abs/2402.05808), **ICML 2024**) — *그들은* **하나의 선형 reasoning chain**에서 RL 시작점을 끝→처음으로 밀며(일반 추론·verifier 없음); *우리는* **분기하는 증명 트리**의 subgoal 경계에서 seed하고 verifier로 채점한다.
- **DeepSeek-Prover-V2** ([2504.21801](https://arxiv.org/abs/2504.21801), **arXiv preprint 2025**) — *그들은* subgoal을 **독립 `have`-lemma(문제)로 분리**해 따로 증명 후 재조립하고 GRPO를 완전체 프롬프트에서 돌리며; *우리는* subgoal의 **중간 state에 seed**하고 그 subgoal 닫힘을 보상해 트리를 leaf→root로 밟는다.

### 8.2 정리증명 RL / 탐색
- **HTPS (HyperTree Proof Search)** ([2205.11491](https://arxiv.org/abs/2205.11491), **NeurIPS 2022**) — *그들은* 추론-시간 **MCTS 탐색**으로 증명을 찾아 자기 최소트리를 학습하며; *우리는* 탐색이 아니라 **gold-트리 seed 커리큘럼**으로 학습분포를 설계한다.
- **DeepSeek-Prover-V1** ([2405.14333](https://arxiv.org/abs/2405.14333), **arXiv preprint 2024**) — *그들은* gold로 **쉬운 변형 문제를 생성**해 데이터를 늘리며; *우리는* gold로 **subgoal seed 상태**를 만든다.
- **DeepSeek-Prover-V1.5 (RMaxTS)** ([2408.08152](https://arxiv.org/abs/2408.08152), **ICLR 2025**) — *그들은* 추론-시간 truncate-and-resume MCTS를 쓰며; *우리는* 학습-시간 subgoal 커리큘럼을 쓴다.
- **GPT-f / Expert Iteration** ([2009.03393](https://arxiv.org/abs/2009.03393), **arXiv preprint 2020**, Polu & Sutskever) · **Formal Math Statement Curriculum Learning** ([2202.01344](https://arxiv.org/abs/2202.01344), **arXiv preprint 2022**) — *그들은* **자기 성공(완전체)** 을 SFT 반복하거나 **문제 난이도**로 커리큘럼하며; *우리는* **subgoal 트리 깊이**로 커리큘럼하고 subgoal 닫힘을 보상한다.
- **Lean-STaR** ([2407.10040](https://arxiv.org/abs/2407.10040), **ICLR 2025**) — *그들은* gold tactic에서 **CoT 근거(rationale)** 를 합성해 SFT하며; *우리는* rationale이 아니라 subgoal state에서 롤아웃한다.
- **STP (Self-play Theorem Prover)** ([2502.00212](https://arxiv.org/abs/2502.00212), **arXiv preprint 2025**) — *그들은* **conjecturer가 새 명제를 생성**하는 self-play를 하며; *우리는* 기존 정리의 subgoal을 seed한다.
- **kSubS** ([2108.11204](https://arxiv.org/abs/2108.11204), **NeurIPS 2021**) · **AdaSubS** ([2206.00702](https://arxiv.org/abs/2206.00702), **arXiv preprint 2022**) — *그들은* **forward subgoal 생성기**로 탐색을 안내하며; *우리는* gold의 **backward subgoal state**로 학습을 안내한다.
- **BFS-Prover** ([2502.03438](https://arxiv.org/abs/2502.03438), **arXiv preprint 2025**) — *그들은* DPO+best-first 탐색을 쓰며; *우리는* subgoal seed GRPO를 쓴다.
- **Goedel-Prover** ([2502.07640](https://arxiv.org/abs/2502.07640), **arXiv preprint 2025**) · **-V2** ([2508.03613](https://arxiv.org/abs/2508.03613), **arXiv preprint 2025**) — *그들은* **합성 문제 난이도**로 커리큘럼하며; *우리는* gold subgoal 트리로 커리큘럼한다.
- **Rango** ([2412.14063](https://arxiv.org/abs/2412.14063), **ICSE 2025**) — *그들은* retrieval+SFT next-tactic이며(RL 없음, **우리 baseline 계열**); *우리는* 그 위에 subgoal RL을 얹는다.
- **Graph2Tac** ([2401.02949](https://arxiv.org/abs/2401.02949), **ICML 2024**) — *그들은* 지도학습 GNN tactic 예측이며; *우리는* RL 커리큘럼이다.

### 8.3 역커리큘럼 / demo-backward
- **Reverse Curriculum (Florensa)** ([1707.05300](https://arxiv.org/abs/1707.05300), **CoRL 2017**) — *그들은* 로봇 goal 근방에서 **state-space를 역으로 확장**하며; *우리는* 증명 트리의 subgoal 경계에서 역으로 seed한다.
- **Single-Demo backward (Salimans & Chen)** ([1812.03381](https://arxiv.org/abs/1812.03381), **arXiv/OpenAI tech report 2018**) · **Backplay** ([1807.06919](https://arxiv.org/abs/1807.06919), **arXiv preprint 2018**) — *그들은* **하나의 선형 demo**를 timestep으로 역행하며(우리가 시도→회귀); *우리는* **트리 subgoal 경계**(canonical)에서 시작하고 per-subgoal 보상을 쓴다.
- **AdaPrefix-GRPO** ([2607.07674](https://arxiv.org/abs/2607.07674), **arXiv 2026 ⚠ ID 미검증**) — *그들은* **선형 prefix 길이**를 성공률로 적응·anneal하며; *우리는* **트리 subgoal**을 seed하고 per-subgoal 보상을 쓴다.

### 8.4 gold-injection / subgoal 재활용 (우리 프로젝트가 시도해 실패한 것 포함)
- **LUFFY** ([2504.14945](https://arxiv.org/abs/2504.14945), **arXiv preprint 2025**) — *그들은* gold 궤적을 **롤아웃 그룹에 주입**해 off-policy로 섞으며(우리가 시도→무익); *우리는* gold를 **seed 상태**로만 쓰고 정책은 자기 롤아웃으로 채점한다.
- **HER-for-provers (Aygün 등)** ([2112.10664](https://arxiv.org/abs/2112.10664), **ICML 2022**) — *그들은* **실패한 자기 시도**의 달성 subgoal을 hindsight relabel하며; *우리는* **gold 트리**의 subgoal을 seed한다(단 OSR 변형은 그들과 합류).
- **HER (Andrychowicz 등)** ([1707.01495](https://arxiv.org/abs/1707.01495), **NeurIPS 2017**) — *그들은* 일반 RL의 달성 goal을 relabel하며; *우리는* 그 아이디어를 verifier 정리증명의 subgoal 닫힘에 특수화한다.
- **QEDCartographer** ([2408.09237](https://arxiv.org/abs/2408.09237), **arXiv 2024 ⚠ 철회판**) — *그들은* 보상 없이 **QED까지 거리 value**를 추정해 탐색하며; *우리는* per-subgoal 이진 verifier 보상을 쓴다.

### 8.5 RL 이론·기법 토대 (§6 증명이 인용)
- **Ross & Bagnell (DAgger)** ([1011.0686](https://arxiv.org/abs/1011.0686), **AISTATS 2011**) — *그들은* off-policy 모방의 복리오차 O(εT²)와 on-policy 보정 O(εT)를 증명하며; *우리는* 이를 **subgoal 분할로 O(εT²/k)** 까지 확장한다(T4).
- **Options framework (Sutton, Precup, Singh)** — **Artificial Intelligence 저널 1999** *(arXiv 없음)* — *그들은* 시간적 추상화(option)의 계층 MDP를 정의하며; *우리는* 각 subgoal을 option으로 보아 sample-complexity 이득을 적용한다.
- **RLOO** (Kool 등, [openreview](https://openreview.net/forum?id=r1lgTGL5DE), **ICLR 2019 workshop** · Ahmadian 등, [2402.14740](https://arxiv.org/abs/2402.14740), **ACL 2024**) — *그들은* leave-one-out baseline의 무편향 그래디언트를 제시하며; *우리는* 이를 **같은 subgoal state 그룹**에 적용해 무편향 advantage를 얻는다(T2).
- **VinePPO** ([2410.01679](https://arxiv.org/abs/2410.01679), **ICML 2025**) — *그들은* state당 MC value로 step-level advantage를 추정하며; *우리는* 이 브랜칭을 **subgoal state의 closability 추정**에 재사용한다(OSR §6.3, 코드 `mc_value`).
- **Dr.GRPO** ([2503.20783](https://arxiv.org/abs/2503.20783), **arXiv preprint 2025**) — *그들은* GRPO의 std-정규화가 편향임을 지적하며; *우리는* 그래서 **RLOO baseline**을 채택한다(T2, 실험 E3).
- **DAPO** ([2503.14476](https://arxiv.org/abs/2503.14476), **arXiv preprint 2025**) · **GSPO** ([2507.18071](https://arxiv.org/abs/2507.18071), **arXiv preprint 2025**) — *그들은* dynamic sampling·clip-higher(DAPO)·sequence-level ratio(GSPO)로 GRPO를 개선하며; *우리는* §9 로그 진단에 따라 dynamic sampling·clip-higher를 채택한다.

### 8.6 학습-중 MCTS / 트리-GRPO · sub-episode 강화 (§4 ①-심층2 관련)
- **Tree-GRPO** ([2509.21240](https://arxiv.org/abs/2509.21240), **arXiv preprint 2025**) — *그들은* flat 그룹 샘플을 **트리 샘플**로 바꿔 outcome 보상에서 step-level process advantage를 뽑고(intra-tree GRPO ≡ step-DPO); *우리는* 이를 **subgoal seed 트리 + verifier-exact process 보상**으로 특수화할 수 있다.
- **ReST-MCTS\*** ([2406.03816](https://arxiv.org/abs/2406.03816), **NeurIPS 2024**) — *그들은* MCTS로 trace 수집 + 정답에서 **PRM으로 process 보상 추정**해 self-training; *우리는* PRM 없이 **verifier가 process 보상을 정확히** 준다.
- **TreeRL** ([2506.11902](https://arxiv.org/abs/2506.11902), **arXiv preprint 2025**) — *그들은* on-policy 트리 검색 RL을 하며; *우리는* subgoal 커리큘럼 위에 얹는다.
- **AlphaZero** ([1712.01815](https://arxiv.org/abs/1712.01815), **Science 2018**) · **Gumbel AlphaZero/MuZero** ([Danihelka 등](https://openreview.net/forum?id=bERaNdoegnO), **ICLR 2022**) — *그들은* MCTS를 정책개선 연산자로 쓰되 Gumbel로 **few-sim 개선을 보장**하며; *우리는* 적은 sim 예산(coq-lsp 비쌈)에 Gumbel식 보장을 채택할 수 있다.
- **Strict Subgoal Execution** ([2506.21039](https://arxiv.org/abs/2506.21039), **arXiv preprint 2025**) · **Uncertainty-Guided Diffusional Subgoals** ([2505.21750](https://arxiv.org/abs/2505.21750), **arXiv preprint 2025**) — *그들은* HRL에서 subgoal 분해로 sparse-reward 장기 과제 성공률↑(regret·정책개선 보장); *우리는* 같은 논리를 정리증명 subgoal 트리에 적용(§6 T4).

### 정직한 주의
- **미검증**: AdaPrefix-GRPO(2607.07674), QEDCartographer(2408.09237, 철회) — arXiv ID/상태 재확인 필요(단일 소스). 논문 제출 전 검증.
- **우리 비교 baseline은 our-rango**(322/328/338)로 유지([[no-published-baseline]]) — 위 논문들과의 **수치 직접비교가 아니라 방법론 차이**를 명시하는 용도.

---

## 9. 학습 로그 메트릭 실측 → GRPO 개선 알고리즘 적용성

이번 실행의 GRPO 학습 로그(`[metrics]`)와 롤아웃 데이터를 실측해, **GRPO를 개선한 후속 알고리즘(DAPO·Dr.GRPO·GSPO 등)이 우리 상황에 실제로 유효한지**를 근거 기반으로 판정한다.

### 9.1 (먼저, 헷갈리는 점) 왜 s3는 mixed 0%(100% dead)인데 s0(root)는 mixed 26%가 나오나?

직관: "s0=완전체 정리가 s3=큰 subgoal보다 **더 어려워야** 하는데, 왜 root가 신호(mixed·all-solved)가 더 많나?" → **모순 아님. 표본·분포 착시.**

- **s3는 그룹이 딱 3개.** 실측: `thmID 302115293070/920505041881/104120853509`(모두 max_reward=0). max-per-thm=2 + 큰 subgoal(size≥6)이 애초에 드물어 전 train에서 **3개만** 추출됨. "100% dead"는 **3/3** = 통계적 의미 없음(이미 §3-C·§5에 caveat). 이 3개가 우연히 다 어려웠을 뿐, "큰 subgoal은 100% 못 푼다"는 뜻이 아님.
- **s0는 그룹이 297개 — 전 정리 분포 전체.** CompCert엔 **짧은 정리가 많다**: 실측한 348개 성공 root 증명의 **step 수 중앙값=5, 최소=2**(2-step 21개, 3-step 32, 4-step 65, 5-step 68 → 절반 이상이 ≤5 step). 이런 4~5줄짜리 완전체는 **≥6 step짜리 큰 subgoal 하나보다 쉽다.**
- **결론**: root가 s3보다 쉬운 게 아니라, **모집단이 다르다.** s3=어려운 큰-subgoal 3개(비대표 표본), s0=**쉬운 짧은 정리 tail을 포함한** 297개 전체. 그래서 s0의 mixed 26%·all-solved 7%는 그 **쉬운 tail**에서 나온다. 3(=noise) vs 297(=분포) 비교라 apples-to-oranges.

### 9.2 스테이지별 학습 로그 메트릭 (실측, epoch1 기준)

| 스테이지 | 학습 steps | dead | mixed(신호) | all-solved | **entropy** | avg_group_std | max_ρ(ep0→1) | clip hi/lo | len_adv_corr | kl |
|---|---|---|---|---|---|---|---|---|---|---|
| **s1** | 2116 | 22% | 37% | 41% | **0.124** | 0.158 | 2.6→**4.1** | .03/.07 | −0.00 | .005→.010 |
| **s2** | 162 | 47% | 35% | 18% | **0.126** | 0.145 | 2.0→1.6 | .03/.05 | +0.14 | .004→.009 |
| **s3** | **0**(전부 dead→그래디언트 없음) | 100% | 0% | 0% | 0 | 0 | 0 | — | — | 0 |
| **s0** | 2318 | 66% | 27% | 7% | **0.110** | 0.116 | 2.4→2.7 | .02/.05 | −0.04 | .004→.007 |

### 9.3 로그가 드러내는 3대 병목

1. **낭비 63~73%** (dead+all-solved = advantage 0). s0는 dead만 66%. → 배치의 대부분이 그래디언트에 기여 안 함.
2. **엔트로피 0.11~0.13 nats로 매우 낮음** = 정책이 거의 결정적 = **exploration collapse**. s0에서 0.110으로 더 낮음. dead 66%와 겹쳐 보면 "어려운 그룹에서 같은(실패하는) tactic만 반복 → 못 벗어남 → dead" 그림.
3. **advantage가 약함**: avg_group_std 0.12~0.16 → advantage 크기 작음 → loss가 epoch0→1에 거의 안 움직임(s0 0.189→0.180). 게다가 **std-정규화 자체가 난이도 편향**([Dr.GRPO](https://arxiv.org/abs/2503.20783)).

부차: max_ρ가 2epoch에서 2.6→4.1로 상승(off-policy drift) · **len_adv_corr≈0**(길이 편향 없음) · kl 작음(0.004~0.010, 정상).

### 9.4 GRPO 개선 알고리즘 적용성 (우리 로그 근거로 판정)

| 알고리즘(기법) | 겨냥 병목 | 우리 로그 근거 | 가치 | 코드 상태 |
|---|---|---|---|---|
| **[DAPO](https://arxiv.org/abs/2503.14476) dynamic sampling** | 낭비 63~73% | dead+all-solved가 그래디언트 0 | **★★★ 최고** | **있음**(`dyn_resample`), 이번 run 미사용 |
| **[DAPO](https://arxiv.org/abs/2503.14476) clip-higher**(ε_low/ε_high 분리·상한↑) | entropy 0.11 collapse | 저엔트로피+dead 동반 | **★★ 높음** | **있음**(`clip_eps_high`, 기본 None=대칭 0.2), 미사용 |
| **[Dr.GRPO](https://arxiv.org/abs/2503.20783)**(std-정규화 제거→RLOO 무편향) | 약한·편향된 advantage | avg_group_std 0.12 + std편향 | **★★ 높음** | 현재 `group_advantages`=(r−mean)/std → RLOO로 교체 |
| **entropy bonus**(loss에 +βH) | entropy 0.11 | 직접 레버 | ★ 중 | **없음**(loss에 항 추가 필요) — 단 verifier RL은 과하면 정밀도↓ |
| **[GSPO](https://arxiv.org/abs/2507.18071)**(sequence-level importance ratio) | ρ 불안정 | max_ρ 4.1(중간) | ☆ 낮음 | 없음(스케일 커지면 재고) |
| **epoch 2→1** | ρ 상승(drift) | 2.6→4.1 | ☆ 낮음(무료) | `--epochs`(기본 1인데 이번 run은 2) |
| ~~DAPO overlong shaping~~ | 길이 편향 | **len_adv_corr≈0 → 불필요** | ✗ | 있음(끔) |
| ~~Dr.GRPO length-norm~~ | 길이 편향 | **len_adv_corr≈0 → 불필요** | ✗ | — |

**핵심**: DAPO·Dr.GRPO의 기계장치는 **대부분 이미 코드에 있고(clip_eps_high·dyn_resample·overlong·std-floor) 이번 subgoal run에서 켜지지 않았을 뿐.** 즉 추가 구현 거의 없이 ablation 가능.

### 9.5 추천 적용 순서 + 정직한 한계

1. **dynamic sampling(`dyn_resample>0`)** — 롤아웃을 mixed 그룹이 찰 때까지 이어 수집 → 배치 낭비 63~73% 제거. 가장 싸고 근거 확실.
2. **clip-higher(`--clip_eps_high 0.28`)** — 저엔트로피(0.11) collapse 완화, 낮은 확률 tactic이 자라게.
3. **RLOO baseline(std-정규화 off)** — 무편향 advantage(§6 T2, 실험 E3와 직결).
4. (선택) **epoch 2→1** — off-policy drift(ρ 4.1) 축소, 공짜.

**정직한 한계**: dynamic sampling은 **신호를 만들어내지 못한다** — 0/6 dead 그룹은 리샘플해도 여전히 0이면 그냥 건너뛸 뿐(배치 효율↑이지 없던 성공을 창조하지 않음). 영구 dead(s0 66%)의 진짜 해법은 **탐색 강화(clip-higher/entropy)** 또는 **subgoal 분해 자체**(이 방법의 본령) 또는 **dense/process 보상**(§4-③, 엔진 훅 있음)이다. 즉 이 절의 GRPO-개선들은 **효율·안정성**을 올리지만, sparse-reward의 근본은 §3·§4의 subgoal·탐색·dense 축이 담당한다. 셋을 **함께** 쓰는 게 정답.

---

## 10. 도달성(reachability) 진단 — cascade 전이 실패의 정량 근본원인 (실측)

subgoal/cascade가 held-out에서 안 오른 이유를 롤아웃 `state_key`(goal 상태)로 직접 측정. **질문: 모델이 "닫는 법"을 배운 subgoal 상태를, 정작 더 큰 문제를 풀 때 실제로 도달(방문)하는가?**

### 10.1 교차 도달 매트릭스 (cascade 롤아웃 실측)

[행] 각 단계에서 학습한 subgoal-entry 상태가 → [열] 각 단계 롤아웃에서 방문되는 비율. (컨테인 방향상 큰 문제 s0⊃s3⊃s2⊃s1 이 작은 subgoal 을 통과해야 정상. 대각=자명.)

| subgoal＼롤아웃 | s0(완전체) | s3 | s2 | s1 | **s0 성공경로** |
|---|---|---|---|---|---|
| **s1 (size4, 가장 깊음, n=287)** | **16.7%** | 0.0% | 0.0% | 100%·자명 | **9.4%** |
| s2 (size6, n=17) | 35.3% | 0.0% | 100%·자명 | 0.0% | 17.6% |
| s3 (size8, 얕음, n=3) | 33.3% | 100%·자명 | 0.0% | 0.0% | 0.0% |

### 10.2 두 가지 발견

1. **orphan-skill**: 학습한 깊은(s1) subgoal의 **83%를 s0 풀이 중 한 번도 안 마주침**(도달 16.7%). 성공한 s0 경로에 등장하는 건 **9.4%**뿐 → 배운 "닫기" 스킬의 대부분이 완전체 성공에 기여 못 함. (깊을수록 도달↓.)
2. **레벨 비중첩**: **s3 롤아웃이 s2·s1 subgoal을 0% 통과, s2 롤아웃도 s1을 0% 통과.** → gold에서 뽑은 subgoal이 **중첩(nested)이 아니라 병렬(parallel) 조각** → "작은 걸 배우면 큰 것 안에서 재사용된다"는 **cascade 대전제가 실측에서 거짓.** 오직 s0(완전체)만 하위를 통과(그것도 약하게).

### 10.3 원인 (사용자 "mixed 전환 낮아서" 직관과 일치)

도달확률 = P(충분히 진도 뺌) × P(gold 분해 경로를 따름). 둘 다 낮음:
- s0의 **62%가 dead**(전멸) → 진도 자체를 못 빼 깊은 subgoal 근처도 못 감.
- subgoal은 **gold 분해**(gold induction/destruct)에서 추출 → s0에선 모델이 자기 tactic을 써서 gold 경로를 안 밟음 → 그 정확한 상태 미도달.

### 10.4 함의

- subgoal 방법(cascade/harvest)은 **"닫기"만 훈련하고 "도달(navigation)"은 안 가르침** → 어려운 절반 방치 → 전이 실패. harvest가 s0r2 롤아웃 신호를 30→31%로밖에 못 옮긴 것도 같은 원인(닫기 강화·도달 그대로).
- 평범한 **SFT→GRPO(s0)는 도달+닫기를 end-to-end 훈련** → 그래서 오히려 안 밀림.
- → 해법은 커리큘럼이 아니라 **도달까지 함께 훈련하는 검색 유도 expert-iteration** (완전체 증명을 검색으로 찾아 통째 학습, on-policy p_reach=1). 상세: `IDEAS.md` 부록 A.

*(측정 주의: `state_key` 정확일치라 alpha-동치 상태는 놓쳐 실제 도달률은 이보다 약간 높을 수 있음. 단 "성공경로 9.4%"·"레벨 0%"는 견고.)*
