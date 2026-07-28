# Gold proof를 정책에 넘겨준 실험 총정리 (2026-07-24)

**질문**: GRPO 롤아웃이 정답을 거의 못 찾는다(dead group 78%, advantage 0). 그러면 **외부 gold proof(정답 증명)를 학습에 쓸 수 있나?** 여러 방식으로 gold를 정책에 주입해봤고, 그 논문·구현·결과·실패원인을 정리한다.

관련 문서: [[SUBGOAL_RL_RESEARCH_ALL]](SUBGOAL_RL_RESEARCH_ALL.md)(covariate-shift 이론), [[RESEARCH_GOLD_CURRICULUM]](RESEARCH_GOLD_CURRICULUM.md).

## 결과 요약표 (작은 scale, on-fix, smart_eval @20→@40)

기준선 = **fix(우리 rango 재현) @40 = 19/40**. gold 계열은 전부 이 밑이거나 동급.

| 기법 | 논문 | gold 사용법 | @20 | @40 | vs fix | 판정 |
|---|---|---|---|---|---|---|
| **fix (baseline)** | — | gold 안 씀(순수 GRPO on-fix) | 13/20 | **19/40** | — | 기준 |
| **LUFFY** | [2504.14945](https://arxiv.org/abs/2504.14945) | gold 궤적을 롤아웃 그룹에 주입 + shaping f(π)=π/(π+γ) | 6/13 | 6/13 | **회귀** | ❌ |
| **KL-LUFFY** | (LUFFY+KL, 자작) | LUFFY + gold 항에 KL(π‖fix) 앵커 | 10/20 | 14/40 | **−5** | ❌ |
| **revcurr** | [Florensa 1707.05300](https://arxiv.org/abs/1707.05300) | gold 모든 중간상태에서 시작(역커리큘럼 완전형) | 10/20 | 15/40 | **−4** | ❌ |
| **backward** | [Salimans&Chen 1812.03381](https://arxiv.org/abs/1812.03381) | gold 끝에서 한 점(remaining=4)만 시작 | 6/12 | 6/12 | **회귀** | ❌ |
| **backward-prm** | 위 + process reward | backward + PRM credit | 0/0 | 0/0 | **붕괴** | ❌ |
| **DAPG** | [Rajeswaran 1709.10087](https://arxiv.org/abs/1709.10087) | gold를 감쇠 BC(λ₀·λ₁^k)로 | 11/20 | 16/40 | **−3** | ❌ |
| **RFT-gold** | [RFT 2308.01825](https://arxiv.org/abs/2308.01825), [STaR 2203.14465](https://arxiv.org/abs/2203.14465) | gold를 그냥 SFT(teacher forcing) | 9/17 | 9/17 | 동급~하락 | ❌ |
| **BREAD** | (prefix-splice, [2602.24110](https://arxiv.org/abs/2602.24110) 계열) | on-policy 궤적 + INVALID 지점에 gold 다리 splice | 미학습 | — | — | ⬜ |

**(참고 — gold 안 쓴 대조군)**: vine(VinePPO [2410.01679](https://arxiv.org/abs/2410.01679)) @40=16, prm(process reward [2606.20068](https://arxiv.org/abs/2606.20068)) @40=16 — 이들도 fix(19) 못 넘음.

**핵심**: **gold를 정책에 "주입/모방"시키는 모든 방식이 fix baseline을 못 넘고, 대부분 회귀(성능 하락)했다.** union 증가(fix가 못 푸는 새 정리) = **전 기법 +0**.

## 각 기법 상세 (무엇을 구현했나 / 왜 실패했나)

### 1. LUFFY ([2504.14945](https://arxiv.org/abs/2504.14945)) — gold를 롤아웃 그룹에 주입
- **구현**: gold 증명을 재생(검증)해 off_policy=True 시도로 s0 그룹에 1개 주입. gold 토큰은 `luffy_batch_loss`(clip 없이 shaping f(π_θ)=π_θ/(π_θ+γ), std-floor advantage), on-policy는 표준 GRPO.
- **결과**: @20 6/13, @40 6/13 — fix가 풀던 10·11·15를 **회귀**시킴.
- **왜 실패**: gold 항이 KL 없이(무제약) 정책을 **gold 상태 방향으로 끌어당김**. gold는 gold-방문 상태에서 gold tactic을 가르치는데, 배포 시 모델은 자기 경로를 가므로 **학습한 게 안 쓰임**(covariate shift, d^gold≠d^π). 얻는 것(안 쓰는 gold-상태 능력) < 잃는 것(자기-상태 능력) → 회귀. shaping은 gradient-flow는 고쳤지만 **방향(분포) 문제는 못 고침**.

### 2. KL-LUFFY (자작 = [LUFFY 2504.14945](https://arxiv.org/abs/2504.14945) + KL) — gold 항에 KL 복원
- **구현**: LUFFY와 유일 차이 = gold 항에 KL(π_θ‖fix) 앵커(`luffy_kl_batch_loss`). fix 근처에 묶어 회귀 방지.
- **결과**: @20 10/20, @40 14/40 (−5). 회귀는 줄었으나 여전히 fix 밑.
- **왜 실패**: KL이 당기는 힘만 줄일 뿐, gold가 가리키는 **방향 자체가 배포 분포 밖**이라 근본 해결 안 됨. "덜 나쁘게" 만들 뿐.

### 3. revcurr — 역커리큘럼 완전형 (Florensa [1707.05300](https://arxiv.org/abs/1707.05300))
- **구현**: backward가 gold 끝 한 점만 쓰는 걸, **gold 모든 중간상태**(remaining 2~8, 정리당 평균 4.8시작점=총 174)에서 시작하도록 확장. `build_revcurr_curriculum.py`→`revcurr.json`, searcher 다중시작.
- **결과**: @20 10/20, @40 15/40 (−4).
- **왜 실패**: gold 중간상태들도 결국 **gold 궤적 위의 점**이라 배포(s0에서 자기경로) 분포와 다름. near-goal 능력을 배워도 s0 전이가 안 됨.

### 4. backward — gold 끝에서 역행 (Salimans & Chen [1812.03381](https://arxiv.org/abs/1812.03381))
- **구현**: gold 증명의 끝 근처(remaining=4) 상태에서 시작해 GRPO. "쉬운 곳부터" 역으로.
- **결과**: @20 6/12, @40 6/12 — **회귀**. sparse-reward 구조적 해법인데 크게 하락.
- **왜 실패**: 시작상태가 gold 위라 covariate shift. + 한 점만 써서 커버리지도 부족.

### 5. backward-prm — backward ([1812.03381](https://arxiv.org/abs/1812.03381)) + process reward ([2606.20068](https://arxiv.org/abs/2606.20068))
- **결과**: @20 0/20, @40 0/40 — **완전 붕괴**.
- **왜 실패**: backward의 분포문제 + PRM의 "valid≠correct" 문제(에러 안 낸 tactic 보상 → dead-end 강화)가 겹쳐 최악. 조기 폐기.

### 6. DAPG (Rajeswaran [1709.10087](https://arxiv.org/abs/1709.10087)) — 감쇠 BC
- **구현**: gold를 demo로 BC하되 가중치를 λ₀·λ₁^k로 **기하 감쇠**시켜 gold 영향이 사라지게. `dapg_demo_loss`.
- **결과**: @20 11/20, @40 16/40 (−3). 감쇠 덕에 회귀는 막음(fix 풀던 것 안 깨짐)이나 **새 정리 0개**.
- **왜 실패**: 감쇠로 "안 해치기"는 달성했지만, gold-상태 능력이 s0 배포로 **전이 안 되는 건 여전히 못 고침**. 안전하나 무익.

### 7. RFT-gold (RFT [2308.01825](https://arxiv.org/abs/2308.01825) / STaR [2203.14465](https://arxiv.org/abs/2203.14465)) — gold를 SFT
- **구현**: gold 증명을 그냥 teacher-forcing SFT(next-tactic). RFT/STaR인데 self-generated 대신 gold.
- **결과**: @20 9/17, @40 9/17 — 동급~하락.
- **왜 실패**: RFT/STaR의 안전성은 "**자기 성공**을 모방"에서 오는데, gold는 **외부 궤적**이라 그 안전성이 깨짐(covariate shift). self-RFT였으면 안전했을 것.

### 8. BREAD — prefix-splice (미학습, Recycling Failures [2602.24110](https://arxiv.org/abs/2602.24110) 계열)
- **구현**: on-policy 궤적을 따라가다 INVALID 지점에서 gold로 **다리(splice)**, 다리 step만 off_policy. 코드는 있으나 학습 안 함(⬜).

## 공통 실패 진단 — covariate shift (분포 불일치)

**한 줄**: gold를 정책에 넣으면 신호는 생기지만(dead group 부활 86%), 그 신호가 가리키는 방향이 **배포 분포 밖**이라 — 배우면 배울수록 자기 분포에서 나빠진다.

- **이론**: BC on gold는 d^gold에서 최적화하나 배포는 d^π. 첫 수가 gold와 다르면 gold가 안 덮은 상태로 가고 오차 복리(Ross-Bagnell O(εT²)). [[SUBGOAL_RL_RESEARCH_ALL]] 파트 I 참조.
- **실증**: 회귀(LUFFY/backward) 또는 무익(DAPG/revcurr, 새 정리 +0). shaping(gradient)·KL(당김)·감쇠(안전)로 증상은 눌러도 방향 문제는 못 고침.
- **rollout 신호는 개선됐다**: LUFFY dead group 부활 19/23, 롤아웃 성공률↑. 그런데 **test 성능은 안 오름** → "롤아웃 신호↑ ≠ 성능↑"가 gold 계열의 일관된 패턴.

## 그런데 — gold가 **성공한** 유일한 방식 (bigscale)

gold를 **정책에 주입(그룹/BC)하지 말고, 별도 SFT 사전학습으로만** 쓰면 다르다:
- **bigscale SFT→GRPO**: gold 254개로 SFT(사전학습) → 그 위에 순수 on-policy GRPO. gold를 롤아웃에 안 섞음.
- **결과**: SFT→GRPO = **338/1191 (28.4%)**, GRPO(328)·baseline(322) 대비 **+10/+16**. **gold가 이긴 유일한 경로.**
- **왜 됐나**: gold-SFT가 정책의 **롤아웃 성공률을 22%→27%로** 올려(더 잘 풀게) → GRPO에 **더 많은 on-policy 신호**를 줌. gold를 "타깃"이 아니라 "**더 나은 탐색 정책을 만드는 사전학습**"으로 쓴 것 → covariate shift 회피.
- 즉 **gold 사용법의 정답 = 그룹 주입(❌) 아니라 사전 SFT(✅)**. 이후 RL은 순수 on-policy로 분리.

## 결론
| gold 사용법 | 예시 | 결과 |
|---|---|---|
| 롤아웃 그룹에 주입 | LUFFY, KL-LUFFY | ❌ 회귀 |
| gold 상태에서 시작 | backward, revcurr | ❌ 회귀/무익 |
| gold를 BC/SFT 타깃 | DAPG, RFT-gold | ❌ 무익/하락 |
| **별도 SFT 사전학습 → 순수 on-policy RL** | **SFT→GRPO** | ✅ **+10~16** |

**교훈**: gold proof를 "직접 모방하게" 하면 전부 실패(covariate shift). gold는 "**정책을 더 좋게 만드는 사전학습**"으로만 유효하고, RL 자체는 self-generated(on-policy) 신호로 해야 한다.

## 더 시도해볼 아이디어 + 신규 논문 조사 (2026-07-24)

**핵심 필터**: 지금까지 실패한 6종(LUFFY·KL-LUFFY·revcurr·backward·DAPG·RFT-gold)은 전부 **정책의 gradient가 gold 토큰/gold-방문 상태를 타깃**으로 삼는다 → covariate shift. SFT→GRPO만 성공한 이유는 SFT가 **분리된 밀도-정합 사전학습**이고 이후 GRPO는 **순수 on-policy**라서다. 그래서 아래 후보를 하나의 기준으로 걸렀다:

> **정책이 gold-방문 상태로 되돌아가는가(❌), 아니면 gold는 시작상태·힌트·보상·문제셋만 바꾸고 정책은 항상 자기 궤적으로만 채점되는가(✅)?**

두 번째 부류만이 신규로 시도할 가치가 있다.

### Tier 1 — 다음 큐 우선

#### A. AdaPrefix-GRPO — gold prefix seeding + loss-mask + anneal ([2607.07674](https://arxiv.org/abs/2607.07674))
- **메커니즘**: gold 증명의 **맞는 prefix를 롤아웃 앞에 붙여** 시작하되, **prefix 토큰의 loss를 마스킹**해 모델은 **자기 continuation에만** gradient를 받음. 피드백 컨트롤러가 문제별 prefix 길이를 조절해 성공률을 ~50%(GRPO 신호 최대)로 유지 → 학습 ~80% 지점부터 **prefix 길이를 0으로 감쇠**시켜 배포 시엔 무보조.
- **covariate-shift 판정 — 최상급**: gold는 *시작상태*만 바꿈, 모델은 gold 텍스트를 모방하지 않음(loss 마스킹), advantage는 prefix 그룹 내 상대값, 보조는 결국 회수. 우리 우려를 논문이 정확히 겨냥하고, prefix 없이 pass@1로 dead-set의 ~17%를 품.
- **SFT-warmup→GRPO를 이기나?**: 논문 내 head-to-head로 **이김** (Qwen3-1.7B, MATH-500/DeepMath-hold: AdaPrefix 70.1/48.2 vs SFT-warmup→GRPO 64.7/33.1 vs vanilla 63.7/30.1). off-policy prefix(rejection-sampled)로도 46.2 — gold 없는 정리엔 대체 가능.
- **1.3B/단일 GPU**: 최대 비례이득이 **0.6B**(19.6→41.8)에서 나옴. 구현 = "데이터 준비 + prefix 토큰 loss 마스크", 트레이너는 스톡. Coq 매핑: gold **tactic prefix**가 자연스러운 seed, mid-proof 시작이라는 잔여 off-dist는 anneal-to-0가 중화.
- **유일 caveat**: math에서만 검증(증명 아님) → 컨트롤러 포팅은 우리 몫. **→ backward/revcurr의 "gold 시작상태" 아이디어를 loss-mask+anneal로 올바르게 고친 버전. 최우선 후보.**

#### B. gold 기반 데이터 증강 → 풀 수 있는 easier variant ([DSP-V1 2405.14333](https://arxiv.org/abs/2405.14333) · [ATLAS 2502.05567](https://arxiv.org/abs/2502.05567) · [Goedel 2502.07640](https://arxiv.org/abs/2502.07640))
- **메커니즘**: gold 정리/증명으로 **더 쉽거나 이웃한 statement를 대량 생성**(대우, gold 증명상태에서 뽑은 sub-lemma, 약화된 가설, mutated goal) → Coq로 검증 → **현재 약한 정책이 실제로 푸는 것만** on-policy GRPO 문제풀에 추가.
- **covariate-shift 판정 — 구조적으로 0**: 정책 타깃 분포를 전혀 안 건드림, 난이도만 낮춰 dead group(우리 78%)에 진짜 보상신호를 줌. 정책은 여전히 전부 자기가 on-policy로 품.
- **실현성**: 매우 높음(생성+검증, 단일 GPU). **dead-group 문제를 모방이 아니라 난이도의 근본에서 공략** — SFT→GRPO와 직교적으로 병행 가능. **가장 안전한 추가.**

#### C. HINT — 정답 대신 추상 힌트, gradient는 무힌트 쿼리로 ([2510.09388](https://arxiv.org/abs/2510.09388))
- **메커니즘**: dead group에 **추상 Meta-Hint**(핵심 통찰, gold 답/tactic 아님)를 넣어 롤아웃을 성공시키되, **gradient는 원래 무힌트 쿼리로** 계산 → 모델은 독립적으로 푸는 법을 배움. 힌트는 테스트 때 제거. covariate shift를 직접 진단하는 Affinity 지표(EUR·exp(−UC/τ)) 제공.
- **판정**: BC와 명확히 다르고 우리 실패모드를 명시적으로 겨냥. AdaPrefix보다 약간 덜 깨끗함(성공 궤적이 힌트-조건부라 미미한 off-dist 잔여). **힌트 생성기 필요**(gold 증명을 "n에 induction 후 lemma X" 식 meta-hint로 추상화). 3B–8B/8×A100 검증이나 1.3B 구동 가능, 힌트 생성 비용 추가.

### Tier 2 — 유망하나 엔지니어링 부담

#### D. gold로 value/PRM 학습 → 그 dense 신호로 GRPO (IRL-lite, GAIL 아님) ([R-AIRL 2510.01857](https://arxiv.org/abs/2510.01857) · [VerifierQ/QLASS 2502.02584](https://arxiv.org/abs/2502.02584))
- **메커니즘**: gold 증명으로 **process reward/value 모델**만 학습, 정책은 **자기 롤아웃**을 그 dense 신호로 shaping. 정책은 gold 상태를 모방하지 않고 gold는 critic만 감독.
- **판정**: covariate shift에 대한 올바른 decoupling. 단 (a) 우리는 이미 **완벽한 terminal 보상(verifier)** 이 있어 가치는 sparse QED를 **densify**하는 것뿐 → verifier 대체가 아니라 PRM/value head로 프레이밍, (b) **full adversarial IRL(GAIL/AIRL)은 불안정+과함 → 스킵**. 실용형: gold 증명상태에 value head 학습 → 보상 shaping/랭킹. 1.3B 실현 가능. **우리 PPO value-head 실험과 수렴하는 방향.**

#### E. STP — self-play, gold로 seed한 conjecturing ([2502.00212](https://arxiv.org/abs/2502.00212), ICML 2025)
- **메커니즘**: conjecturer(**gold lemma/statement로 seed**)가 *간신히 풀리는* 관련 명제를 제안 → prover가 학습 → 상호 강화. 난이도-정합 self-scaling 커리큘럼.
- **판정**: B와 같은 anti-shift 논리(정책이 자기 타깃을 품)이나 **학습된** 난이도 생성기. **Lean whole-proof SOTA로 실증**. 두 역할+반복이라 무거움. 1.3B 노력 시 가능.

#### F. gold-seeded 탐색: truncate-and-resume + subgoal 분해 ([DSP-V1.5 2408.08152](https://arxiv.org/abs/2408.08152) RMaxTS · [DSP-V2 2504.21801](https://arxiv.org/abs/2504.21801) subgoal)
- **메커니즘**: MCTS/탐색을 **gold subgoal/부분 gold 증명에서 seed**, truncation 지점부터 resume. AdaPrefix(A)의 **탐색-시간 버전**: gold가 exploration을 seed, 모델이 완성.
- **판정**: 모방 회피(완성은 on-policy·verifier 채점), V2의 subgoal split은 자연스러운 gold 커리큘럼. 비용은 모델이 아니라 MCTS/탐색 인프라. **우리 subgoal-harvest([harvest_subgoals.py](../../scripts/harvest_subgoals.py))와 결이 같음.** [[SUBGOAL_RL_RESEARCH_ALL]] 참조.

### Tier 3 — 원리적이나 우리 스케일엔 위험/과중

#### G. 분포/support 제약 offline RL: IQL·AWAC·CQL·Cal-QL·ReBRAC·ILQL ([IQL 2110.06169](https://arxiv.org/abs/2110.06169) · [AWAC 2006.09359](https://arxiv.org/abs/2006.09359) · [CQL 2006.04779](https://arxiv.org/abs/2006.04779) · Cal-QL NeurIPS'23 · [ReBRAC 2305.09836](https://arxiv.org/abs/2305.09836) · [ILQL 2206.11871](https://arxiv.org/abs/2206.11871))
- **어느 게 verifier-보상 세팅에 진짜 보장을 주나**: IQL·AWAC가 가장 깨끗한 **support 제약**(OOD action 안 물음, in-support로 advantage-가중) = 형식적 covariate-shift 경계. **Cal-QL**이 우리에겐 가장 흥미 — **offline→online 전이**(=우리 SFT-offline→GRPO-online 파이프라인)를 위해 설계돼 online fine-tune이 붕괴 안 하게 value를 calibrate.
- **정직한 판정 — 회의적**: (a) 전부 **token-level critic** 필요, **sparse binary verifier 보상**+무한 텍스트 action에서 Q-learning은 악명높게 불안정(ILQL/VerifierQ가 문서화), (b) **AWAC = advantage-weighted BC** → 기계적으로 여전히 gold action으로 회귀 → advantage가 gold hard tactic을 강하게 down-weight 안 하면 **같은 함정 재진입**. 최고 난이도. 굳이면 **Cal-QL(offline→online seam)** 또는 **IQL식 value head로 reward shaping**(D와 수렴)만, full offline-RL 정책은 금지.
  - ⚠️ **재포장 BC 경고**: AWAC와 RFT식 advantage-가중 업데이트는 "offline RL" 라벨에도 불구하고 **여전히 gold action으로 회귀** → 이미 실패한 것들의 형제로 취급.

#### H. weak-to-strong / on-policy distillation ([DoPD 2607.05394](https://arxiv.org/abs/2607.05394)) — **우리에겐 대체로 N/A**
- on-policy distillation(학생이 생성, 교사가 학생 자기 토큰을 채점)은 covariate shift를 피하나 **정적 gold가 아니라 더 강한 교사 모델**이 필요. 우리는 gold만 있어 SFT로 환원됨. 외부 prover(예: DeepSeek-Prover)를 교사로 들이면 다른 프로젝트. **보류.**

### 정리 — 4개의 진짜 신규 메커니즘 (SFT→GRPO가 이미 됨을 전제)
| # | 기법 | gold 역할 | 정책 채점 | 우선도 |
|---|---|---|---|---|
| A | **AdaPrefix-GRPO** | 시작 prefix(loss-mask+anneal) | 자기 continuation | ★ 최우선 (논문 내 SFT→GRPO 이김) |
| B | **gold 데이터증강** | 쉬운 변형 문제 생성 | 자기 on-policy | ★ 최안전·병행 |
| C | **HINT 추상힌트** | dead group 힌트 | 무힌트 쿼리 gradient | ○ 힌트생성기 필요 |
| D | **gold→critic(PRM)** | value/PRM 감독 | 자기 롤아웃(shaped) | ○ PPO value-head와 수렴 |

**한 줄 결론**: gold를 "직접 모방"시키면 전부 실패(covariate shift). 진짜 신규는 정책을 **자기 궤적으로만 채점**하는 4가지 — prefix-seeding(A)·easier-문제생성(B)·추상힌트+무힌트 gradient(C)·gold가 정책 아닌 critic을 학습(D). AWAC/RFT식 advantage-가중은 라벨과 무관하게 gold로 회귀하므로 실패한 것들의 형제.

## 참고문헌
- LUFFY — [2504.14945](https://arxiv.org/abs/2504.14945)
- Reverse Curriculum (Florensa) — [1707.05300](https://arxiv.org/abs/1707.05300)
- Backward from demo (Salimans & Chen, Montezuma) — [1812.03381](https://arxiv.org/abs/1812.03381)
- DAPG (Rajeswaran) — [1709.10087](https://arxiv.org/abs/1709.10087)
- RFT (Yuan) — [2308.01825](https://arxiv.org/abs/2308.01825) · STaR (Zelikman) — [2203.14465](https://arxiv.org/abs/2203.14465)
- Recycling Failures (BREAD 계열) — [2602.24110](https://arxiv.org/abs/2602.24110)
- VinePPO(대조) — [2410.01679](https://arxiv.org/abs/2410.01679) · Process-Verified RL(대조) — [2606.20068](https://arxiv.org/abs/2606.20068)
- covariate shift 이론 — [[SUBGOAL_RL_RESEARCH_ALL]] (Ross-Bagnell, DAgger)
- **신규 조사(2026-07-24)**:
  - AdaPrefix-GRPO — [2607.07674](https://arxiv.org/abs/2607.07674)
  - HINT (추상힌트/무힌트 gradient) — [2510.09388](https://arxiv.org/abs/2510.09388)
  - 데이터증강: DeepSeek-Prover-V1 [2405.14333](https://arxiv.org/abs/2405.14333) · ATLAS [2502.05567](https://arxiv.org/abs/2502.05567) · Goedel-Prover [2502.07640](https://arxiv.org/abs/2502.07640)
  - IRL-lite/PRM-from-gold: R-AIRL [2510.01857](https://arxiv.org/abs/2510.01857) · VerifierQ/QLASS [2502.02584](https://arxiv.org/abs/2502.02584)
  - STP self-play — [2502.00212](https://arxiv.org/abs/2502.00212)
  - gold-seeded 탐색: DSP-V1.5 [2408.08152](https://arxiv.org/abs/2408.08152) · DSP-V2 [2504.21801](https://arxiv.org/abs/2504.21801)
  - offline RL: IQL [2110.06169](https://arxiv.org/abs/2110.06169) · AWAC [2006.09359](https://arxiv.org/abs/2006.09359) · CQL [2006.04779](https://arxiv.org/abs/2006.04779) · ReBRAC [2305.09836](https://arxiv.org/abs/2305.09836) · ILQL [2206.11871](https://arxiv.org/abs/2206.11871)
  - on-policy distillation — [2607.05394](https://arxiv.org/abs/2607.05394)
