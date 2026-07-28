# Deep Research — Gold/Curriculum/Sparse-reward RL for LLM 정리증명

> 2026-07-17. deep-research 워크플로우(94 에이전트, 소스 14, 주장 25 검증: 24 confirmed / 1 refuted).
> 4개 질문: (1) reverse curriculum s0 전이 (2) gold 주입 covariate shift (3) expert-iteration/RFT 소규모 가능성 (4) dead-group GRPO 처방.
> 비교는 우리 내부 baseline 기준(published 리더보드 비교 안 함).

---

## Q1. Reverse curriculum — s0 전이 갭은 "설계로" 닫힌다 (우리 revcurr에 직접 시사)

**핵심 발견 (confidence: high, 3-0):** reverse curriculum이 **from-scratch(s0) 성능을 실제로 올린다** — 단, Florensa(2017)와 그 LLM판 R³(ICML 2024) **둘 다 시작상태 분포를 s0까지 바깥으로 다시 넓히며(anneal), 평가는 항상 s0에서** 하기 때문. 전이 갭을 무시하는 게 아니라 **커리큘럼이 s0을 커버하도록 키워서 구조적으로 닫는다.**
- Florensa: 근접상태에서 시작 → Brownian walk로 바깥 확장, 평가는 항상 ρ0=Unif(S0). 이론: support 일치 시 shifted ρ 최적정책 = ρ0 최적정책 (Kakade-Langford 2002). 실측: 순수 TRPO는 근접에서만 풀고(ring~10%, key~2%) 먼 시작은 못 품 → reverse curriculum은 같은 RL로 먼 시작도 성공.
- **R³ (2402.05808):** gold 데모의 **끝→앞으로** RL 시작점 슬라이드 → outcome-only를 step-level 신호로. **8개 추론과제 평균 +4.1점**, program-GSM8K **+4.2점**, s0에서 평가.

**⚠️ 우리에게 직접 시사 (caveat, high):**
- **모든 증거가 로봇/GSM8K이고 Coq/Lean 정리증명은 없음.** R³는 PPO(우리는 GRPO). 정리증명 전이는 "sparse 신호 밀집화" 유추일 뿐 실증 안 됨.
- **결정적:** 우리 revcurr는 remaining 2~8 밴드를 **한꺼번에 정적으로** 쓴다. R³/Florensa의 핵심인 **"s0까지 바깥으로 annealing"이 빠져 있다.** 문헌이 말하는 전이 성립 조건(커리큘럼이 s0을 커버)을 우리 정적 버전은 만족 안 할 수 있음 → **revcurr에 anneal-to-s0 스케줄 추가가 개선 포인트.**

## Q2. Gold 주입 covariate shift — "되긴 되는데, 반드시 mismatch를 명시적으로 제어해야" (우리 LUFFY 실패 설명)

**핵심 (high, 3-0):** off-policy gold를 GRPO에 주입하면 **순수 on-policy가 실패하는 영역에서도 학습이 된다(LUFFY, LLaMA3.1-8B)** — 단 **분포 불일치를 명시적 처방으로 잡을 때만.**
- LUFFY(2504.14945, NeurIPS 2025)의 처방 = **regularized importance sampling 기반 policy shaping**: 저확률-핵심 행동을 증폭해 "표면적·경직된 모방"과 entropy collapse를 방지. 이게 없으면 모방이 붕괴.
- Tree-OPO(2509.09284): teacher MCTS prefix를 GRPO 커리큘럼으로 재활용(직교 처방). **단 Tree-OPO의 정확도 향상 주장은 0-3으로 REFUTED** — 메커니즘만 확인, 성능 우위는 신뢰 불가.

**→ 우리 LUFFY 실패 원인 확정:** 우리는 **gold 토큰 직주입(policy shaping 없이)** 했다. LUFFY가 성공한 이유가 바로 우리가 뺀 그 부품(regularized importance sampling)이다. KL-LUFFY(KL 복원)는 그 방향의 한 근사지만, LUFFY 원판은 **importance-sampling 증폭**이 핵심.

## Q3. Expert-iteration / RFT 소규모 가능성 — **문헌 공백 (우리 질문 미해결)**

- DeepSeek-Prover-V1.5(2408.08152, ICLR 2025): RLPAF = **GRPO on sparse binary Lean 보상**(프롬프트당 32후보, Lean 검증 1/0) + RMaxTS(intrinsic-reward MCTS로 sparse 탐색 보완). SFT 후 refinement 단계.
- **소규모(1 GPU, 수백~수천 정리, 소수 iteration)에서 유의미 이득이 가능한지 확립하는 증거를 찾지 못함.** STaR/Polu 2022/RFT 스케일링 곡선은 살아남은 주장 없음. 모든 증거가 **대규모 병렬 표집** 전제.
- **→ 우리의 "천장 근처라 소규모론 이득 작다"는 반증도 확증도 안 됨 — 진짜 열린 문제.**

## Q4. Dead-group / zero-advantage — 수학적으로 정밀 규명됨

**핵심 (high, 3-0):** binary 보상에서 프롬프트당 업데이트 크기 = **그룹 표준편차 σ=√(k(G−k))/G.** 만장일치 그룹은 σ=0 → 학습 0. **silent 확률 = p^G+(1−p)^G** (정확히 DAPO가 버리는 질량). **신호는 p=0.5에서 최대** (|adv| 기대값 = 2√(p(1−p))). 실측 붕괴율 **28–45%** (Qwen2.5-0.5B ACR=0.45).
- GRPO/Dr.GRPO/DAPO = σ에 대한 세 연산(나눔/안나눔/버림). (Bay & Yearick 2607.00152)

**처방 비교:**
- **DAPO dynamic sampling** (best-attested): σ=0 그룹 oversample-후-폐기. AIME 2024 **50 vs 47, 학습스텝 절반**. **⚠️ 단 50점은 4개 기법(dynamic sampling+clip-higher+token-level loss+overlong shaping) 합작이지 dynamic sampling 단독 아님** — 바닐라 GRPO는 ~30%.
- **난이도 정합 커리큘럼(SEC 2505.14970 / GAR 2510.11769):** 문제 난이도를 p≈0.5로 조종해 **상류에서** dead-group 회피. GAR: **Lean pass@32 +4.2% rel, ProofNet 22.58→25.81%** (DeepSeek-Prover-V2). SEC: 밴딧으로 |adv| 최대 카테고리 우선 → p=0.5로 수렴.

**→ 우리 실험에 시사:**
- **fixdyn(dynamic sampling 단독)** 버그 고쳐도 큰 이득은 기대난망 — DAPO는 4개 합작. 소폭 예상.
- **신호는 p=0.5에서 최대** → **adaptprefix(pass-rate~0.5 조준)가 SEC/GAR로 이론적 지지받음.** revcurr의 "밴드 전부" 샷건보다 **p≈0.5만 고르는 게 문헌 정합.**

---

## 종합 판단 (우리 다음 수)

1. **revcurr**(진행중): 그대로 두되, **anneal-to-s0 스케줄**을 넣은 변형이 문헌상 "제대로 된" reverse curriculum. 현재 정적 버전은 전이 갭이 안 닫힐 위험.
2. **adaptprefix**(큐 대기): **SEC/GAR가 가장 강하게 지지**(p=0.5 = 신호 최대). gold 계열 중 이론 근거 최상. 우선순위 올릴 가치.
3. **LUFFY 재도전 시**: gold 토큰 직주입 금지, **regularized importance-sampling policy shaping** 탑재해야 원판 성능. (우리 실패는 이 부품 누락.)
4. **fixdyn**: 단독 이득 작을 것(문헌). 그래도 버그 고친 clean 측정값은 확보 가치.
5. **소규모 expert-iteration**: 문헌 공백 = 우리가 하면 **새로운 데이터포인트**. 다만 대규모 전제라 리스크 높음.

## Refuted / 공백
- ❌ Tree-OPO SAE 정확도 향상·분산 감소 (0-3). 메커니즘만 확인.
- 공백: 정리증명(Coq/Lean)에서 reverse-curriculum-from-gold의 s0 실증 / 소규모 RFT 이득 / LUFFY식 주입이 정리증명 dead-group을 실제로 고치는지 head-to-head.

## 소스 (primary)
- Florensa 2017 (CoRL) reverse curriculum: ri.cmu.edu/.../florensa17a.pdf
- R³ (Xi 2024, ICML): arxiv.org/abs/2402.05808 · code: github.com/WooooDyy/LLM-Reverse-Curriculum-RL
- LUFFY (2025, NeurIPS): arxiv.org/abs/2504.14945
- Tree-OPO: arxiv.org/abs/2509.09284
- DeepSeek-Prover-V1.5 (ICLR 2025): arxiv.org/pdf/2408.08152
- DAPO: arxiv.org/pdf/2503.14476
- GRPO σ-identity (Bay & Yearick): arxiv.org/pdf/2607.00152
- SEC: arxiv.org/html/2505.14970v1 · GAR: arxiv.org/pdf/2510.11769
