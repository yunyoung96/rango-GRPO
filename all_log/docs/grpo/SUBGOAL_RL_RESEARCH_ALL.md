# Subgoal 재활용 · PPO/GRPO 설계 · Gold RL 연구 종합 (2026-07-23)

> 3개 문서 통합: (I) subgoal 재활용 선행연구+이론, (II) PPO/GRPO 설계·hybrid·GRPO 타당성, (III) gold-lemma RL 조사.

---

# 파트 I — Subgoal 재활용: 선행연구 + 이론적 배경


**아이디어**: GRPO 롤아웃이 정리 전체를 못 풀어(dead group, advantage 0) 통째로 버려지는 경우에도, 그 안에서 induction/case/destruct 또는 bullet(`-`,`+`,`*`)로 **완전히 닫힌 subgoal**들이 있다. 이걸 추출해 next-tactic 정책의 positive 학습데이터로 재활용한다.

**우리 데이터 실측**(bigscale2 300그룹): dead group 233개 안에 **닫힌 subgoal 1923개**(추출 후보 501개, dead 출신 377개). bullet 재출현으로 확인되는 것만 98개 시도. → harvester(`scripts/harvest_subgoals.py`) 구현·검증 완료.

---

## Q1. 선행연구 — 이 접근을 취한 논문이 있나

**핵심 결론: 개념(실패 탐색에서 증명된 부분결과를 hindsight로 재활용)은 선행연구가 있으나, 우리의 구체적 인스턴스(Coq 실패 GRPO 롤아웃의 닫힌 tactic-level subgoal → next-tactic 정책 positive)는 미청구(unclaimed).**

### Tier 1 — 같은 핵심 아이디어 (실패 탐색에서 증명된 결과 → 정책 학습)
- **Minimo** — "Learning Formal Mathematics From Intrinsic Motivation", Poesia et al., NeurIPS 2024 (Oral), [2407.00695](https://arxiv.org/abs/2407.00695). **가장 가까움.** 실패한 탐색 트리에서 중간 statement가 증명된 노드를 찾아 hindsight relabel → 정책+value 학습(교과서적 HER). 차이: self-play 추측, dependent type theory, forward-reasoning 산물(고정 라이브러리 next-tactic 아님).
- **HER-for-provers** — Aygün et al., ICML 2022, [2112.10664](https://arxiv.org/abs/2112.10664). 실패한 refutation 중 유도된 clause D를 **자체 정리로 승격**(D는 공리에서 따라오므로)해 clause-scoring 정책의 positive로. 차이: first-order 포화 prover라 "reached=proved"가 일치 → "미증명 state를 relabel"이 아님. "닫힌 subgoal 재활용"과 정확히 같진 않음.

### Tier 2 — 인접: 증명된 subgoal을 쓰되 **정책이 아니라 critic**에
- **HTPS / Evariste** — Lample et al., NeurIPS 2022, [2205.11491](https://arxiv.org/abs/2205.11491). root를 못 닫은 탐색에서도 증명된 노드 = value=1 **critic** 타깃. 정책은 완전 증명에서만. 전조(precursor).

### Tier 3 — 인접: 실패 롤아웃에서 dense reward (subgoal 추출은 안 함)
- **Process-Verified RL for Theorem Proving via Lean** — Kim & Yun, 2026, [2606.20068](https://arxiv.org/abs/2606.20068). Lean elaboration으로 step별 dense reward → GRPO. **우리 "dense reward + GRPO" 프레이밍에 가장 가까우나**, 실패 궤적을 따라 credit 배분일 뿐 닫힌 subgoal을 별도 예제로 추출하지 않음.
- **GRPO is Secretly a PRM** — Sullivan & Koller, 2025, [2509.21154](https://arxiv.org/abs/2509.21154). GRPO가 암묵적 step credit. TP 특화 아님.

### Tier 4 — 인접이지만 **역방향**: 열린 goal 채굴 / 실패를 negative로
- **Goedel-Prover-V2** — Yong Lin et al., 2025, [2508.03613](https://arxiv.org/abs/2508.03613). 실패 시도에서 `extract_goal`로 subgoal 마이닝하나 **미해결(open) goal을 새 문제로**(우리의 거울상 — 닫힌 게 아니라 열린 것).
- **BFS-Prover** — 2025, [2502.03438](https://arxiv.org/abs/2502.03438). 실패의 INVALID tactic을 DPO **negative**로. (우리 validity DPO 근거)

### Tier 5 — 인접: 실패에서 subgoal 채굴하나 **추론시 guidance**(정책 학습 아님)
- **ProofCompass** — Wischermann et al., 2025, [2507.14335](https://arxiv.org/abs/2507.14335). N=16 다 실패하면 실패 시도들의 `have` subgoal을 모아 LLM이 ≤5개 선택 → 같은 문제 재유도. 학습 아님, 검증-닫힘도 아님.

### Tier 6 — 인접: **사전(up-front)** decomposition (실패 채굴 아님)
- **DeepSeek-Prover-V2** — 2025, [2504.21801](https://arxiv.org/abs/2504.21801). 671B가 사전에 `have...sorry` 골격 분해 → 7B가 각 subgoal. **우리와 반대**(사전 분해 vs 실패에서 사후 수확).
- DSP [2210.12283](https://arxiv.org/abs/2210.12283), Decomposing the Enigma [2305.16366](https://arxiv.org/abs/2305.16366), SubgoalXL [2408.11172](https://arxiv.org/abs/2408.11172), POETRY [2405.14414](https://arxiv.org/abs/2405.14414) — 전부 사전/재귀 분해.

### Tier 7 — STaR/RFT/expert-iteration: outcome-level, **실패를 버림**
정책을 실패 시도의 닫힌 subgoal로 학습하는 것은 없음 = 우리의 clean baseline gap.
- Lean-STaR [2407.10040](https://arxiv.org/abs/2407.10040), STaR [2203.14465](https://arxiv.org/abs/2203.14465), GPT-f [2009.03393](https://arxiv.org/abs/2009.03393): 성공만.
- Formal Math Curriculum Learning [2202.01344](https://arxiv.org/abs/2202.01344): **"실패 탐색은 명시적으로 제외"**(negative만 남으므로). subgoal 라벨은 성공 트리 내부에서만, value용.
- DeepSeek-Prover-V1/V1.5 [2405.14333](https://arxiv.org/abs/2405.14333)/[2408.08152](https://arxiv.org/abs/2408.08152): Lean 검증 완전 증명만. RFT [2308.01825](https://arxiv.org/abs/2308.01825): 정답 경로만.

### Tier 8 — 성공 코퍼스/사전 추측에서 렘마 마이닝 (실패 아님)
- REFACTOR [2402.17032](https://arxiv.org/abs/2402.17032): 성공한 Metamath 증명에서 재사용 정리 추출. LEGO-Prover [2310.00656](https://arxiv.org/abs/2310.00656): 자체 생성·검증 렘마 라이브러리. Lemmanaid [2504.04942](https://arxiv.org/abs/2504.04942): 정의에서 렘마 추측.

### Coq 특화
Rango [2412.14063](https://arxiv.org/abs/2412.14063), Graph2Tac [2401.02949](https://arxiv.org/abs/2401.02949), QEDCartographer [2408.09237](https://arxiv.org/abs/2408.09237) — 실패의 닫힌 subgoal로 정책 학습하는 것 없음.

### 신규성 정직하게 위치짓기
- **개념(hindsight harvesting)은 선행 있음**: Aygün 2022, Minimo 2024. "개념적으로 새롭다" 주장 금지.
- **구체적 인스턴스는 미청구**: **닫힌**(open 아님, vs Goedel-V2) tactic-level subgoal을, **정책 positive로**(critic 아님 vs HTPS/GPT-f; negative 아님 vs BFS-Prover; 새 문제 아님 vs Goedel-V2; 추론 guidance 아님 vs ProofCompass), **고정 실제 라이브러리의 실패 롤아웃에서**(vs Minimo self-play; vs Aygün FOL), **Coq+GRPO+tactic 분해**(bullet/induction, vs 사전 have/sorry).
- 인용 전략: "같은 아이디어 다른 세팅" = **Minimo**; named HER baseline = **Aygün**.

---

## Q2. 이론적 배경 — 왜 covariate-shift-free인가

### 한 문단 요약
gold BC는 **demonstrator 분포 d_{π*}** 에서 tactic 예측오차를 최소화하지만, 배포 시 정책은 **자기 분포 d_{π̂}** 를 만든다. 다르면 첫 실수가 gold가 안 덮은 state로 밀어넣고 오차가 **길이 T에 대해 이차(O(εT²))** 로 누적(Ross-Bagnell, tight). 자기 롤아웃의 닫힌 subgoal 수확은 **바로 그 변수를 뒤집는다**: 학습 (state→tactic) 쌍이 **d_{π̂} 자체**(정책이 실제 도달한 state)에서 나오고 verifier가 무결 positive 라벨을 준다 → DAgger식 on-policy aggregation → 학습손실=테스트손실 → **O(εT²)가 O(εT)로** 붕괴. 이게 전부다. 단, 이 보장은 **transition level에선 강하지만 task/goal-분포 level에선 약해진다**(context 벗기기·easy subgoal 편향·새 정리).

### Part 1 — Ross-Bagnell / DAgger 정확한 정리
- **BC(이차, tight)** [RB2010, AISTATS]: `E_{s∼d_{π*}}[e_{π̂}]≤ε` 이면 **J(π̂) ≤ J(π*) + T²ε** (Thm 2.1). 기전: "π̂가 실수하는 순간 π*가 안 본 state로 가서 이후 매 step 최대비용 1." Kääriäinen 하한 `Θ(T²ε)`로 tight.
- **on-distribution(선형)** [DAgger, [1011.0686](https://arxiv.org/abs/1011.0686)]: `E_{s∼d_π}[ℓ]=ε` 이면 **J(π) ≤ J(π*)+uTε** (Thm 2.2); DAgger는 aggregated on-policy 데이터로 **J(π̂) ≤ J(π*)+uTε_N+O(1)** (Thm 3.2). 0-1 비용이면 u≤1 → **O(εT)**. 유일 치환: d_{π*}→d_{π}.

### Part 2 — STaR/ReST-EM/RFT: 자기 성공은 **구성상** on-policy
- **STaR** [2203.14465]: 정답필터 SFT = policy-gradient의 indicator 항(`∇J=Σ E[𝟙(ŷ=y)∇log p]`) — 유도된 항등식(단 명시적 근사).
- **ReST-EM** [2312.06585]: max-reward를 ELBO로, E-step=현재정책 샘플+필터(이진보상이면 정확히 generate-and-filter), M-step=보상가중 SFT → **단조 ELBO 개선**(EM, 증명됨). **당신 논지의 가장 명시적 진술이나 "가설"로**: "모델 생성 해가 사람 해보다 in-distribution이라 추정."
- RFT [2308.01825]: 경험적, 서로 다른 정답경로 多 → 이득 多, 약한 모델일수록 큼.

### Part 3 — Expert Iteration + CPI: 정책개선 보장
- **ExIt** [1705.08439]: 개념적 policy-iteration 프레임(search=expert, network=apprentice), **보장 증명은 없음**. AlphaGo Zero=accept-only-if-superior 게이트.
- **엄밀함은 CPI** [Kakade & Langford, ICML 2002]: `π_new=(1−α)π+απ′`. **Thm 4.1**: `η(π_new)−η(π) ≥ (α/(1−γ))(𝔸 − 2αγε/(1−γ(1−α)))`. **Cor 4.2**: 𝔸≥0이면 적절한 α로 **≥ 𝔸²/8R²** 개선. α=1(무제약 모방)은 **성능 저하 가능** → GRPO의 KL/trust-region이 이론적으로 필요한 이유.
- **Performance Difference Lemma**: `J(π′)−J(π)=(1/(1−γ))E_{s∼d^{π′}}[A^π]` — advantage를 **새 정책 분포**로 적분 → per-state 이득≥0만으로는 부족, π′ 방문 state 통제 필요. **주의**: 같은 정책의 relabel 샘플은 policy advantage=0 → 보장 이득 없음.

### Part 4 — HER: 닫힌 subgoal = "achieved goal"
- HER [1707.01495]: achieved-goal map `m:S→G`, `∀s f_{m(s)}(s)=1`. 유효성: "goal은 행동엔 영향, dynamics엔 무영향 → 임의 goal로 replay 가능" → relabel transition은 g'의 참 dynamics 샘플, **분포 불일치 없음**.
- 대응: Coq 커널 = HER의 predicate f(단 **sound oracle**, false positive 0 → HER의 tolerance-ball보다 강함). 닫힌 subgoal = achieved goal in 3 senses: 자기생성(d_{π̂}), verifier hard positive, 실패한 outer라도 g'엔 valid 성공.
- **불일치(정확히)**: HER는 **off-policy value RL**(reward relabel + Bellman rebootstrap → off-policy 알고리즘 필요). subgoal 수확 SFT는 **positive-only BC**(critic/bootstrap 없음) → HER의 goal-independent-dynamics 논증조차 불필요(진짜 g'를 증명한 demonstration을 clone). 즉 "relabel goal의 on-distribution 성공" 주장이 HER보다 **더 직접 참**.

### Part 5 — 정직한 한계: transition(강) vs task-분포(약)
"내 정책이 도달한 state니 shift-free"는 **transition level 참, task-분포 level 과대주장.** 4채널로 shift 재유입:
1. **context 벗기기**: mid-proof state를 **그대로(full context) 학습**하면 input shift 최소(강한 주장 유지). **standalone 렘마로 hoist**(주변 goal 제거·가설 재양화)하면 input 분포 달라짐 → shift 재유입. (LEGO-Prover의 evolver, "Library Learning Doesn't" [2410.20274]가 근거)
2. **수확 편향(easy subgoal)**: Aygün 2112.10664이 직접 인정 — 도달한 clause는 "몇 step만 더 하면 닫힘"이라 subsampling 필요. near-terminal 과대표집, 정작 막는 hard state 과소.
3. **다양성 붕괴**: harvest→SFT 반복이 tactic 분포 좁힘. ReST-EM이 고정 문제셋에서 2 iter 후 퇴화 관측 → solution 수 cutoff 안전장치.
4. **새 정리에서 이차 누적 재출현**: DAgger 보장은 수집 task 분포에 지표됨. 새 정리는 다른 궤적 → 정적 harvest 밖 → T²ε 복귀. online 재수집만 해결(그래서 expert-iter provers가 target 전체증명 재수집; STP는 새 추측 생성).
5. **닫혔지만 쓸모없는 subgoal**: sound라 무효증명은 아니나, trivial/무관(`auto` on vacuous)한 것이 cheap-closer로 prior 편향 — reward-hacking 인접.

**성립 조건**: full-context 그대로 학습 + 유사 중간분포 평가 + 대표성 유지(easy 과대표집 금지) + trivial 필터.
**약화/붕괴**: standalone hoist / easy 편향 / 가드 없는 반복 자기학습 / 정적 harvest로 새 정리 평가 / 무필터.

### 비교표
| | 학습 state 분포 | 라벨 | 누적 bound | covariate shift |
|---|---|---|---|---|
| gold BC / LUFFY | d_{π*} (외부) ≠ d_{π̂} | 외부(도달불가 가능) | **O(εT²)** (tight) | **있음** |
| 자기생성 verified 닫힌 subgoal(full context) | d_{π̂} = 테스트분포 | verifier(sound, 𝔸≥0) | **O(εT)** (u=O(1)) | transition level **없음**; task level 잔여 |

---

## 우리 설계에의 함의
1. **full context 유지가 결정적**(Part 5-1): harvester가 standalone 렘마로 hoist하지 말고 **원본 proof_state 그대로** 학습(현재 구현이 이미 이 방식 — `example` 통째 보존). ✅
2. **easy subgoal 편향 완화**(Part 5-2): `--min_tactics`로 자명한 1-tactic 닫힘 비중 조절, 또는 subsampling.
3. **trivial closer 필터**(Part 5-5): `auto/trivial/reflexivity` 단독 닫힘 down-weight 고려.
4. **KL 제약 유지**(Part 3): SFT→GRPO처럼 conservative update(무제약 모방은 CPI상 저하 가능).
5. **bullet-aware 추출 추가**: 두 번째 `-` 출현 = 첫 subgoal 완결(Coq 강제) → goal-count가 놓치는 98개 시도 회수.
6. **정직한 포지셔닝**: "개념은 Minimo/Aygün 선행, 인스턴스(Coq 실패 롤아웃 닫힌 tactic subgoal → 정책 positive)는 미청구."

## 참고문헌 (전체)
Q1: Minimo [2407.00695], Aygün HER [2112.10664], HTPS [2205.11491], Process-Verified RL [2606.20068], GRPO-as-PRM [2509.21154], Goedel-V2 [2508.03613], BFS-Prover [2502.03438], ProofCompass [2507.14335], DeepSeek-Prover-V2 [2504.21801], DSP [2210.12283], POETRY [2405.14414], SubgoalXL [2408.11172], Decomposing Enigma [2305.16366], Lean-STaR [2407.10040], STaR [2203.14465], GPT-f [2009.03393], Curriculum [2202.01344], DS-Prover-V1.5 [2408.08152], RFT [2308.01825], REFACTOR [2402.17032], LEGO-Prover [2310.00656], Lemmanaid [2504.04942], kSubS [2108.11204], AdaSubS [2206.00702], Rango [2412.14063], Graph2Tac [2401.02949], QEDCartographer [2408.09237].
Q2: RB2010 (AISTATS 2010), DAgger [1011.0686], STaR [2203.14465], ReST [2308.08998], ReST-EM [2312.06585], RFT [2308.01825], ExIt [1705.08439], Kakade&Langford CPI (ICML 2002), HER [1707.01495], Library Learning Doesn't [2410.20274], STP [2502.00212].

> ⚠️ 이론 인용 정직성: RB/DAgger/CPI/HER/ReST-EM/Aygün는 원문 verbatim. Process-Verified RL(2606.20068)은 검증됨. 2026-dated ID 일부는 재검증 제한 — 논리 자체로 성립.

---

# 파트 II — Subgoal × PPO/GRPO 설계 + hybrid + GRPO 타당성


닫힌 subgoal(실패 롤아웃에서 완전히 닫힌 subchain)을 학습에 재활용하는 방법의 설계 논의. 배경: [[SUBGOAL_RECYCLING_RESEARCH]](SUBGOAL_RECYCLING_RESEARCH.md)(선행연구 Minimo/Aygün + covariate-shift 이론).

## 0. 왜 subchain을 살리려 하나 — "14 step 가고 15번째에 사망" 문제

동기: 8개 시도가 다 14 step VALID 통과 후 15번째 INVALID로 사망 → 전부 reward=0 → std=0 → advantage=0 → 그룹 통째로 학습 제외. "멀쩡한 14개가 아깝다."

**⚠️ 결정적 구분: VALID(에러 안 남) ≠ correct(증명으로 이어짐).** 증명이 실패했다는 건 그 14개 VALID 중 어딘가가 **dead-end로 빠졌다**는 뜻 — 어느 게 함정인지 모름.

**실측(bigscale2 dead group의 VALID step 6353개 분류)**:
| 분류 | 개수 | 살릴 수 있나 |
|---|---|---|
| (A) 닫힌 subgoal 안 = 검증됨 | 476 (**7%**) | ✅ 안전 |
| (B) VALID인데 미완 분기 = 정답 보장 없음 | 5877 (**93%**) | ⚠️ dead-end 학습 위험 |

→ **버려지는 valid의 93%는 "실패한 분기의 tactic"** — 통째 학습하면 "실패하는 길 재현"을 가르침. **이게 PRM(process reward)이 union +0으로 실패한 이유.** 살릴 수 있는 건 **(A) 검증된 닫힌 부분 7% + bullet 완결 분기**뿐(= harvester가 뽑는 것). 나머지는 못 믿음.

교정: all-fail 그룹은 std=0→adv=0이라 GRPO가 14개를 "나쁘다 학습"하는 게 아니라 **"무시"(gradient 0)**. 섞인 그룹에서만 reward=0이 음수 벌점.

## 1. 닫힌 subchain 하나만 GRPO에? → 안 됨

GRPO advantage = 같은 state의 G개 attempt 그룹상대: `A_i=(r_i−mean)/std`. harvested subchain은 **이미 성공한 하나**뿐 → mean=r, std→0 → **advantage=0, gradient 없음**. 단일 chain은 GRPO에 무의미. 자연스러운 집은 **RFT(자기성공 모방)** 또는 **PPO**.

## 2. s3에서 여러 번 추출해 평균? → 목적에 따라

- **RFT/PPO면 불필요** — 이미 닫힌 증명이니 그 tactic을 positive로 모방. group·평균 불필요.
- **GRPO 고집하면** — s3 재롤아웃해 group 생성(= on-policy backward). s3는 모델이 스스로 도달한 state라 gold-backward보다 깨끗(covariate shift 없음). 단 이미 성공을 아는 state 재롤아웃은 대체로 낭비.

## 3. PPO 질문 (핵심) — subgoal은 PPO에 더 적합

PPO는 group이 아니라 **학습된 critic V(s)** 로 baseline → **단일 chain에도** advantage:
```
A(s,a) = return − V(s)   ← 우리 PPO 구현 그대로. subgoal이면 A = 1 − V(s3)
```
group 불필요 → **subgoal 재활용은 GRPO보다 PPO에 구조적으로 적합.**

**보너스**: subgoal 재활용의 최대 약점 "easy subgoal 과대표집"을 PPO의 V(s)가 자동 완화:
- easy → V(s)≈1 → A≈0 → 거의 안 배움
- hard(못 풀 줄 알았는데 닫음) → V낮음 → A큼 → 강하게 배움

즉 critic이 "놀라운 성공"만 골라 학습 → RFT의 uniform 모방보다 원리적으로 낫다. (단 이 효과는 V가 여물어야 성립 — single-round·얇은 linear critic이면 약함. → critic warmup/MLP 필요.)

## 3b. 우리 V(s) target 문제 — γ 없어서 "state 가치"가 아니라 "시도 결말"을 배움

**코드 확인**(`grpo_train.py` flatten_group ppo + `grpo.py` value_loss):
```python
returns.append(float(a["reward"]))    # a["reward"] = 그 attempt COMPLETE=1, 아니면 0
value_loss = (returns - values)²       # V를 그 return에 회귀. γ 없음 → 모든 step 동일 target
```
→ **성공 시도의 모든 state → V target=1, 실패 시도의 모든 state → V target=0.**

**⚠️ 이게 "QED로 이어질 수 있으면 V=1"이라는 의도와 미묘하게 다름**: 같은 state s3라도 **어느 시도에 속했냐**에 따라 target이 갈림.
| | 의도한 V (state 본질가치) | 우리 구현 V (시도 결말) |
|---|---|---|
| 실패 시도의 좋은 초기 state | 1 (풀 수 있음) | **0** (그 시도가 죽음) |

**문제**: 14 step 가고 15번째 죽은 시도에서 a_0~a_13 state가 전부 V target=0 → "이 state들은 가망 없다"고 **틀리게** 학습(초반 state는 멀쩡했는데). advantage A=return−V도 왜곡. §0의 "valid≠correct"가 critic 학습에도 그대로 재현됨.

**제대로 하려면 = γ 도입 = distance-to-QED**(§ 파트III 조사, QEDCartographer/LeanProgress):
```
V(s) = γ^(그 state에서 QED까지 남은 step)   # 성공 시도만, state별 다른 target
```
- 성공: QED 1 step 전 → γ¹, 5 step 전 → γ⁵ (가까울수록↑). γ<1이 "거리" 인코딩.
- **실패 시도의 state는 target 안 줌**(QED 거리 미정의) → 틀린 0을 안 배움.
- → 작은 PPO 실험에 **binary target vs γ^(남은step) target** 비교 추가 후보.

## 4. 세 가지 설계

| 방법 | group? | easy-bias | 비용 | 근거 |
|---|---|---|---|---|
| ① subgoal-RFT→GRPO ⭐ | ❌ | 수동 필터 | 저 | 이긴 SFT→GRPO에서 gold-SFT를 self-subgoal-RFT로 교체(on-policy로 더 깨끗) |
| ② subgoal-PPO ⭐ | ❌(critic) | 자동(V(s)) | 저 | subgoal은 PPO에 적합, critic이 easy 완화 |
| ③ subgoal-GRPO(재롤아웃) | ✅ | group std | 고 | on-policy backward, 대체로 낭비 |

추가 아이디어: **같은 subgoal의 서로 다른 해법 chain 다 학습**(auto vs lia;auto) → 다양성↑, mode collapse 완화. harvester가 tactic 다르면 둘 다 보존.

## 5. PPO+GRPO 병행 — 이론적으로 타당한가? → **네, 타당합니다**

당신 아이디어: 같은 policy π에서 **전체 정리는 GRPO 롤아웃, subgoal subchain은 PPO**.

**핵심 근거**: GRPO와 PPO는 **같은 목적**(∇J = E[A·∇logπ])을 최적화하고, **advantage 추정 방식만 다릅니다**:
- GRPO: A = (r−group_mean)/std (그룹 baseline, critic 없음)
- PPO: A = return − V(s) (학습 critic baseline)

policy gradient는 **transition별로 A를 어떻게 추정하든**(그룹/critic/MC) 각각 유효한 advantage면 합쳐도 유효합니다(baseline b(s)는 action 독립이라 `E_a[b(s)∇logπ]=0` → 불편). 그래서:
```
L = L_GRPO(전체정리 그룹)  +  λ·L_PPO(subgoal chain, critic baseline)
∇L = 두 유효 정책그래디언트의 가중합 → 유효한 ascent 방향
```
= **mixed-baseline policy gradient**. multi-objective/auxiliary-task RL의 표준. 이론적으로 문제없음.

**실무 주의점 2개**:
1. **scale 불일치**: GRPO A는 std로 정규화돼 ~단위 스케일, PPO A=return−V는 raw 보상 단위 → 한쪽이 지배할 수 있음. **λ로 가중 or 각각 정규화** 필요.
2. **critic 학습 범위**: V는 subgoal state에서만 쓰이니 그 state들에 대해서만 잘 fit되면 됨. GRPO 부분은 V 안 씀.

**우리 구현 관점**: `flatten_group`이 이미 ppo/일반 GRPO를 분기 처리하니, "전체정리 group은 GRPO loss, subgoal chain은 ppo_batch_loss"로 **한 배치 안에서 섞는** 것은 배선 가능. 두 loss를 λ로 합치면 됨.

### 선행연구 조사 결과 (2026-07-23) — GRPO+PPO 진짜 병행은 사실상 없음 = **미청구 방향**
"같은 policy에 그룹 baseline + 학습 critic V(s) 동시 사용"을 조사한 결과:
- **유일한 문자 그대로 hybrid**: Hybrid GRPO (Sane 2025, [2502.01652](https://arxiv.org/abs/2502.01652)) — PPO의 bootstrapped V(s) 유지 + GRPO multi-sample 추가. **단 단독저자, synthetic control RL만, LLM 적용 안 됨.** 개념적 선례일 뿐.
- **pre-LLM 원조**: Q-Prop/IPG (2017, [1706.00387](https://arxiv.org/abs/1706.00387)) — MC baseline과 critic interpolation. 고전 control.
- **착각 주의(전부 hybrid 아님)**: VinePPO/RLOO/ReMax/PRIME/DAPO/GPG = critic **제거**, 그룹만. VAPO([2504.05118](https://arxiv.org/abs/2504.05118))/VC-PPO = critic **only**, 그룹 baseline 없음(mirror). 2026 "critic 재도입" 계열 = critic이 그룹을 **대체**, 병행 아님.
- **우리 도메인 최근접**: Process-Verified RL for TP via Lean (Kim&Yun 2026, [2606.20068](https://arxiv.org/abs/2606.20068)) — sequence-level GRPO 그룹 + tactic-level process advantage 결합. **당신 아이디어의 Lean 판이나 critic 대신 process reward**(둘 다 그룹/MC 기반, 학습 critic 없음).
- **결론**: 분야가 critic-free 그룹 계열 vs value 기반 계열로 **갈라져 경쟁**, 합치질 않음. "그룹 baseline ⊕ 학습 V(s)를 LLM에서 병행 학습"은 **search miss가 아니라 진짜 open direction.** → 참신성 있으나, 유일 선례가 synthetic만 검증 = LLM 작동 미지수.

## 6. 애초에 GRPO는 이론적으로 타당한가? → **부분적으로. mean은 건전, /std는 휴리스틱(편향)**

정직하게 나눠야 합니다.

### 건전한 부분: (r − mean) baseline
표준 policy gradient `∇J=E[A·∇logπ]`, A=Q−V. baseline b(s)가 action 독립이면 불편(`E_a[b∇logπ]=0`). GRPO의 group mean ≈ V(s)(그 prompt의 MC 상태가치 추정) → **유효 baseline**. `(r−mean)·∇logπ`는 REINFORCE-with-baseline → **건전, (거의) 불편**.
- 단 미세 편향: r_i가 자기 baseline(mean)에 **포함**됨(leave-one-out 아님) → O(1/G) 자기포함 편향. **RLOO**(Ahmadian 2024, [2402.14740](https://arxiv.org/abs/2402.14740))가 leave-one-out mean으로 이걸 제거 → RLOO가 GRPO보다 이론적으로 깨끗.

### 문제 부분: /std 정규화
`A_i=(r_i−mean)/std`의 **÷std는 policy gradient 이론에서 유도되지 않는 휴리스틱**입니다. 그룹별로 1/std_group 가중 → **objective를 바꿉니다**:
- std 작은 그룹(보상 거의 균일) **up-weight**, std 큰 그룹 down-weight.
- 결과: GRPO는 순수 E[r]의 gradient가 **아니라** "그룹 난이도로 재가중된 목적"을 최적화. → **편향된(biased) 추정량**. fixed point가 E[r] 최적과 다름.

**문헌이 이걸 지적**: **Dr. GRPO**(Liu et al. 2025, "Understanding R1-Zero-Like Training", [2503.20783](https://arxiv.org/abs/2503.20783))가 GRPO의 **(a) response-length 편향**(토큰평균 정규화)과 **(b) question-difficulty 편향**(÷std)을 지목하고 **둘 다 제거**한 debiased 버전을 제안. DAPO([2503.14476](https://arxiv.org/abs/2503.14476))도 관련 편향 일부를 손봄.

우리 이진보상(0/1) 경우: std=√(p(1−p)), p=성공비율. mixed(p≈0.5) 그룹 std 최대, all-fail/all-success 근처 std 작음 → **÷std가 "거의 다 실패하는 그룹의 드문 성공"을 증폭**. 그럴듯하지만 여전히 편향.

### 결론
- **"GRPO가 이론적으로 완전 타당한가?"** → **아니오, 완전하진 않음.** (r−mean)은 건전하나 ÷std와 토큰평균은 유도되지 않은 휴리스틱으로 **편향**을 넣음. E[r]의 unbiased PG가 아님.
- **"그럼 틀렸나?"** → 아니오. 실무적 안정화 휴리스틱(분산감소·스케일불변)으로 **경험적으로 잘 작동**. 다만 이론적으로 더 깨끗한 대안 존재: **RLOO**(자기포함 편향 제거), **Dr. GRPO**(std·length 편향 제거).
- 우리 함의: GRPO를 쓰되 편향을 안다면, 필요시 **std 제거(Dr. GRPO)** 나 **RLOO** 로 바꿔볼 수 있음. 다만 우리 병목은 편향이 아니라 **신호 부족(dead 78%)** 이라, 이 debias가 성능을 크게 바꿀 가능성은 낮음(우선순위 낮음).

## 7. 더 좋은 아이디어

### ⭐ (A) 트리에서 "공짜 sibling group" 수확 — 재롤아웃 없이 GRPO group
§2에서 "s3 재롤아웃은 낭비"라 했지만, **더 나은 길**: 롤아웃 트리에서 **여러 attempt가 이미 같은 state s3를 지나간 경우**, 그 sibling들이 **공짜 group**을 이룹니다. 재롤아웃 없이:
- s3를 지난 attempt들의 (s3 이후) 결과로 group-relative advantage 계산 가능.
- 단일 chain 문제(§1) + 재롤아웃 낭비(§2) 둘 다 회피.
- VinePPO/tree-credit과 연결. 우리 데이터에 sibling-공유 state가 얼마나 있는지는 측정 필요(이전 tactic-GRPO 분석에서 step0~1은 8개 공유, 깊을수록 갈라짐 → 얕은 subgoal에 유효).

### (B) critic warmup from subgoal (single-round 한계 해결)
subgoal의 (state, distance-to-QED=γ^남은step) 라벨로 **value head를 supervised 먼저 fit** → 그 위에 PPO. LeanProgress([2502.17925](https://arxiv.org/abs/2502.17925))가 DeepSeek-1.3B로 검증. §3의 "V가 여물어야 easy-완화 성립"을 직접 해결. subgoal 데이터가 critic 학습에도 재사용됨.

### (C) 정직한 천장 인식
(A)(B) 모두 **기존 신호를 재활용/재분배**할 뿐 — 롤아웃이 못 찾는 증명을 만들진 못함. **subgoal 재활용의 유일한 진짜 강점 = dead group 78%에서 새 신호 추출**(재분배 아님). 그래서 우선순위: subgoal-RFT/PPO > hybrid > sibling-group > debias.

## 실행 우선순위 (현재 큐 뒤)
1. **작은 PPO critic 4종**(진행 예정) → 최고 critic 확정
2. **subgoal-RFT→GRPO** ①, **subgoal-PPO** ②(최고 critic + distance-to-QED critic warmup) — 작은 scale @20 게이트
3. hybrid(GRPO 전체 + PPO subgoal) — ②가 되면
4. (옵션) RLOO/Dr.GRPO debias — 우선순위 낮음(병목은 신호부족)

## 참고문헌
- RLOO — Ahmadian et al. 2024, [2402.14740](https://arxiv.org/abs/2402.14740) (leave-one-out baseline)
- Dr. GRPO — Liu et al. 2025, [2503.20783](https://arxiv.org/abs/2503.20783) (GRPO std·length 편향 제거)
- DAPO — [2503.14476](https://arxiv.org/abs/2503.14476)
- LeanProgress — [2502.17925](https://arxiv.org/abs/2502.17925) (DeepSeek-1.3B distance-to-QED)
- GRPO 원전 — DeepSeekMath [2402.03300](https://arxiv.org/abs/2402.03300)
- 이론 배경 전체 — [[SUBGOAL_RECYCLING_RESEARCH]](SUBGOAL_RECYCLING_RESEARCH.md) (Ross-Bagnell, DAgger, HER, CPI)

---

# 파트 III — Gold-lemma RL: 적용 가능한 신규 논문 조사


3개 독립 웹조사(RL 레시피 / gold-demo 활용 / exploration) 종합. 우리 셋업 = DeepSeek-Coder-1.3B + LoRA, next-tactic, single-round GRPO, CompCert, single GPU, gold proof 보유.

## 핵심 수렴 발견 (세 조사가 독립적으로 같은 답)

우리 실패는 **두 개의 서로 다른 병**이다:
- **병 A (covariate shift)**: gold를 *학습 타깃*으로 쓰면 발생. LUFFY·KL-LUFFY·DAPG·backward 전부 여기 걸림(gold state는 배포 분포 밖).
- **병 B (신호 없음)**: 롤아웃이 정답을 못 찾아 dead group → advantage 0.

세 조사 공통 처방: **gold는 "어디를 탐색할지"를 바꾸는 데만 쓰고, gradient는 정책 자신의 on-policy(도달 가능한) 성공에만 준다.** 즉 gold를 그룹에 타깃으로 넣지 말고, gold로 탐색을 유도하되 학습은 un-hinted/on-policy 부분에만.

## Tier 1 — 세 조사가 공통 지목 (최우선, 저비용, 우리 규모 검증됨)

### ⭐ ①  Gradient-masked gold-prefix + annealing
- 논문: **HINT** ([2510.09388](https://arxiv.org/abs/2510.09388)), **Adaptive Trace Prefix Control** ([2607.07674](https://arxiv.org/abs/2607.07674)), **DeepSeek-Prover proof-seeding** ([2408.08152](https://arxiv.org/abs/2408.08152)). 세 조사가 각각 top-pick.
- 기법: gold proof의 prefix k개를 롤아웃 **컨텍스트로만** 주입 → dead group이 live로. 단 **(a) prefix 토큰엔 gradient 마스킹**(모델 자기 continuation만 학습), **(b) reward는 full sequence**, **(c) k를 학습 끝까지 0으로 anneal**(배포는 prefix 없이). HINT는 한발 더: gradient를 *un-hinted 원query*에 대해 계산.
- **우리 adaptprefix와의 차이(중요)**: 우리 `rango-grpo-adaptprefix`는 prefix를 골라 그룹 만들고 **plain GRPO** — annealing 없음, un-hinted 프레이밍 없음. → **"done right" 버전은 미구현.** 이게 가장 크게 놓친 부분.
- 검증 규모: 0.6B–1.7B LoRA, ~6e18 FLOPs(= vanilla GRPO 1회). **정확히 우리 규모.**

### ② HER-for-provers (실패 롤아웃 relabel)
- 논문: **Aygün et al., ICML 2022** — "Proving Theorems using Incremental Learning and Hindsight Experience Replay" ([PMLR v162](https://proceedings.mlr.press/v162/aygun22a.html), [arXiv 2112.10664](https://arxiv.org/abs/2112.10664)).
- 기법: 실패한 증명 시도에서 **실제로 도달한 state를 goal로 재라벨** → 풀린 보조 정리 다수 생성 → dead여도 dense 신호. 재라벨 타깃은 정책이 실제 도달한 state라 **covariate shift 없음**.
- 우리 상황: 실패 롤아웃 로그 이미 있음. 병 B를 gold 없이도 공략. **미시도, 저비용.**

### ③ DAPO dead-group 동적 필터링
- 이미 `fixdyn`(dyn_resample)으로 보유(버그 수정함). 신호를 만들진 못하나 78% dead가 22% live를 희석하는 낭비 차단. 몇 줄.

## Tier 2 — gold로 exploration 강화 (on-distribution이라 안전)

### ④ gold에서 subgoal 커리큘럼 채굴
- 논문: DeepSeek-Prover-V2 ([2504.21801](https://arxiv.org/abs/2504.21801)), Subgoal Demo Learning ([2305.16366](https://arxiv.org/abs/2305.16366)).
- 핵심: **CompCert gold 증명이 이미 decomposition을 포함** — 모든 중간 proof-state / `assert`가 known-solvable 쉬운 sub-theorem. 이를 채굴 → 롤아웃 성공률↑ → live group. (우리 revcurr/backward의 확장이되 "정책 자신의 subgoal-도달 구간만 학습"이 차이)
- STP ([2502.00212](https://arxiv.org/abs/2502.00212))의 **pass-rate (0, 0.25] 필터**로 어떤 sub-theorem에 GRPO 예산 쓸지 선택.

### ⑤ RMaxTS intrinsic novelty bonus
- 논문: DeepSeek-Prover-V1.5 ([2408.08152](https://arxiv.org/abs/2408.08152)).
- 기법: search가 **미방문 proof-state 도달 시 보너스** → reward-free 탐색을 dense 탐색으로. gold와 직교, 원생성률↑. state hash 몇 줄. **미시도.**

## Tier 3 — 진단·필터로 빌리기 (구축 X)

### ⑥ HiLL "hint reliance" 진단 지표
- 논문: HiLL ([2604.00698](https://arxiv.org/abs/2604.00698)). "hinted 성공이 hint에 얼마나 의존하나" 측정 → **낮으면 hint 제거 후에도 전이**됨을 이론적으로 보장.
- 활용: 전체 구축 말고, **gold-seed 성공 중 어떤 걸 학습해도 안전한지 사전 스크리닝**하는 지표로만.

## Exploration 각도 추가 (CompCert 특이 레버)

### ⑦ 구조적 다양성 best-of-n
- 논문: Inference-Time Diversity diagnostic ([2601.16172](https://arxiv.org/abs/2601.16172)). iid 샘플링은 k=32→64에서 **새 정리 0개**(mode collapse). **고정된 tactic-skeleton prefix 스케줄 + NL 힌트**로 커버리지 강제 → +45% relative. **재학습 없음, 거의 무료.**

### ⑧ retrieval recall/ranking 강화
- 논문: Rango ([2412.14063](https://arxiv.org/abs/2412.14063), =우리 시스템), Graph2Tac ([2401.02949](https://arxiv.org/abs/2401.02949), 미방문 def 온라인 학습, 미방문 프로젝트 1.5×), Coq Structural Context ([2507.02541](https://arxiv.org/abs/2507.02541), 2.1×).
- 세 조사 공통: **unseen CompCert에서 1.3B가 증명 찾는 가장 확실한 레버는 retrieval** — "lemma 암기(능력)"를 "lookup(컨텍스트)"으로 치환. 우리 `replug_lsr` probe가 옳은 방향.

## 정직한 능력 천장 경고 (세 조사 공통)

이 중 어느 것도 **1.3B가 근본적으로 못 찾는 증명을 만들어내지 못한다.** search/pass@k류(class B)는 이미 정책이 nonzero mass 둔 경로만 재분배. 새 정보 주입(retrieval, decomposition-with-drafter) 또는 분포 커버리지 강제(skeleton)만이 class A로 새 증명 가능. 그래도 안 나오면 = 천장이 binding = 답은 더 큰 base 모델/distillation, RL 기계장치 아님.

## 실행 우선순위 (bigscale 종료 후)

1. **gradient-masked gold-prefix + annealing** (①) — 우리 adaptprefix를 "done right"로 개조(annealing/마스킹/un-hinted). 가장 정확히 우리 실패 겨냥, 우리 규모 검증. **최우선.**
2. **HER 실패 relabel** (②) — 병 B를 gold 없이 저비용 공략.
3. **RMaxTS novelty bonus** (⑤) + **구조적 다양성 best-of-n** (⑦) — 원생성률↑, 거의 무료.
4. **gold subgoal 커리큘럼** (④) — 오프라인 최대 레버.
5. 진단: **hint-reliance** (⑥)로 안전한 gold-seed만 학습.

이미 큐: AWAC·goldshape(이론보장 2종). ①은 AWAC보다 우리 실패에 더 정확히 대응(AWAC ≈ advantage-가중 SFT라 SFT 동률 넘기 어려움).

---

## 참고문헌 (전체 링크)

### Tier 1 — gold를 안전하게 (gradient-masked, on-policy만 학습)
- HINT — Don't Tell the Answer, Truly Guide the Reasoning During RL Rollouts — https://arxiv.org/abs/2510.09388
- Max Out GRPO Signal: Adaptive Trace Prefix Control — https://arxiv.org/abs/2607.07674
- Reuse your FLOPs: Conditioning on Very Off-Policy Prefixes — https://arxiv.org/abs/2601.18795
- Recycling Failures: Salvaging Exploration in RLVR via Fine-Grained Off-Policy Guidance — https://arxiv.org/abs/2602.24110
- LUFFY — Learning to Reason under Off-Policy Guidance (f(π)=π/(π+γ) shaping) — https://arxiv.org/abs/2504.14945
- MENTOR — Selective Expert Guidance (critical-token만 주입) — https://arxiv.org/abs/2510.04140
- Aygün et al. — Proving Theorems using Incremental Learning and HER — https://proceedings.mlr.press/v162/aygun22a.html · https://arxiv.org/abs/2112.10664
- DAgger — Ross/Gordon/Bagnell 2011 (no-regret, O(εT)) — https://arxiv.org/abs/1011.0686
- AggreVaTe — https://arxiv.org/abs/1406.5979 · DART — https://arxiv.org/abs/1703.09327

### Tier 2 — exploration / 원생성률↑ (proving-native)
- DeepSeek-Prover-V1.5 (RMaxTS intrinsic novelty, prefix/proof-seeding) — https://arxiv.org/abs/2408.08152
- DeepSeek-Prover-V2 (subgoal decomposition curriculum) — https://arxiv.org/abs/2504.21801
- STP — Self-play Theorem Prover (pass-rate (0,¼] 필터) — https://arxiv.org/abs/2502.00212
- Subgoal-based Demonstration Learning — https://arxiv.org/abs/2305.16366
- Go-Explore (return-to-state then explore) — https://arxiv.org/abs/1901.10995
- POETRY — Prove Theorems Recursively (sorry/level 분해) — https://arxiv.org/abs/2405.14414

### Tier 3 — 진단·필터
- HiLL — Learning to Hint for RL ("hint reliance" 지표) — https://arxiv.org/abs/2604.00698

### GRPO 계열 개선 (dead-group / 신호)
- DAPO — Decoupled Clip and Dynamic Sampling — https://arxiv.org/abs/2503.14476
- Rewarding the Unlikely (rare 정답 up-weight) — https://arxiv.org/abs/2506.02355
- NGRPO (all-negative 그룹도 기여) — https://arxiv.org/abs/2509.18851

### Exploration / diversity / retrieval (CompCert 레버)
- Inference-Time Diversity diagnostic (skeleton 스케줄, iid 붕괴) — https://arxiv.org/abs/2601.16172
- Goedel-Prover-V2 (diversity collapse 대응 학습) — https://arxiv.org/abs/2508.03613
- Rango (우리 시스템, ICSE'25) — https://arxiv.org/abs/2412.14063
- Graph2Tac (미방문 def 온라인 학습) — https://arxiv.org/abs/2401.02949
- Clarifying Before Reasoning: Coq Prover with Structural Context — https://arxiv.org/abs/2507.02541
- LeanDojo / ReProver (retrieval + best-first 기준선) — https://arxiv.org/abs/2306.15626
- Lean-STaR (reasoning-before-tactic) — https://arxiv.org/abs/2407.10040

### offline / offline-to-online RL (참고, 대체로 same wall)
- AWAC — Accelerating Online RL with Offline Datasets — https://arxiv.org/abs/2006.09359
- AWR — Advantage-Weighted Regression — https://arxiv.org/abs/1910.00177
- IQL — Implicit Q-Learning — https://arxiv.org/abs/2110.06169
- CQL — Conservative Q-Learning — https://arxiv.org/abs/2006.04779
- Cal-QL — https://arxiv.org/abs/2303.05479 · RLPD — https://arxiv.org/abs/2302.02948
- Decision Transformer — https://arxiv.org/abs/2106.01345
- RFCL — Reverse-Forward Curriculum Learning (ICLR'24) — https://reverseforward-cl.github.io/

### 검색 / 능력천장 관련
- HTPS — HyperTree Proof Search — https://arxiv.org/abs/2205.11491
- LeanProgress (남은 step 예측 critic, DeepSeek-Coder-1.3B 기반) — https://arxiv.org/abs/2502.17925
- InternLM2.5-StepProver (critic=난이도 선택) — https://arxiv.org/abs/2410.15700
- BFS-Prover — https://arxiv.org/abs/2502.03438
- DSP — Draft-Sketch-Prove — https://arxiv.org/abs/2210.12283 · DSP+ — https://arxiv.org/abs/2506.11487
- LEGO-Prover — https://arxiv.org/abs/2310.00656 · LLM Library Learning Fails (compute-matched 반박) — https://arxiv.org/abs/2504.03048

> ⚠️ 최신 preprint(2601.*, 2602.*, 2604.*, 2607.*)는 각 1회 fetch로 확인 — 구현 전 PDF에서 세부(localizer/advantage/annealing 스케줄) 재확인 권장. 메커니즘 자체는 일관.
