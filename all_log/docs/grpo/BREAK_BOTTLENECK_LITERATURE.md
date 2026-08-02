# 병목을 실제로 깨는 방법 — 문헌조사 (2026-07-29)

관련: [[BOTTLENECK_ANALYSIS]](진단), [[VALUE_FREE_SEARCH]](17% 붕괴한 시도), [[DECOMPOSITION_IDEAS]].

**질문**: 우리가 실측한 병목 — **작은 모델(1.3B)이 초반 분해(어느 변수 induction / 어느 hyp destruct / 어느 lemma)를 아예 생성 못 함(coverage 22% = generation 문제)** — 을 **실제로 깰 수 있는** 방법이 문헌에 있나? RL·gold 6종·subgoal·PPO·selection-DPO 다 37.5% 천장. **value-free MC-search는 32.5→17%로 붕괴**(1.3B가 롤아웃서 QED를 못 내 MC 신호가 다 0).

---

## 0. 결론 (가장 유망한 3방향, 순위)

| 순위 | 방향 | 왜 우리 병목을 깨나 | 1.3B/단일GPU/Coq 판정 |
|---|---|---|---|
| **★1** | **Planner–Executor (추론시 분해 분리)** | 분해(=우리 병목)를 **1.3B 밖 강한 LLM**이 함. 1.3B는 subgoal별 tactic만 채움(강점). **capacity 벽을 구조적으로 우회** | **최유망**. 학습 안 함 → 우리 학습 실패 전부 회피. planner=API/큰모델 1콜/정리 |
| **★2** | **구조적 decomposition score (dense 채점)** | value-free가 죽은 이유=MC 신호 sparse(0). 분해를 **QED-롤아웃이 아니라 구조 복잡도 감소·로컬 재구성으로 dense 채점** | **바로 시도 가능**. net 불요. value-free 재설계 |
| **★3** | **Reward-free 학습 value (QEDCartographer)** | 우리 PPO critic(outcome-reward)·value-free MC(sparse) 둘 다 죽은 sparse-reward 문제를 **proof-tree 분기구조에서 value 학습**으로 우회. Coq 네이티브 | 우리 스케일서 실증됨(CoqGym 21.4%). value net 학습 필요(중간 비용) |
| ✗ | teacher-분해 **distill→1.3B** | 이론상 covariate-shift 안전하나… | **capacity 벽 위험**(§4): 1B/1.5B는 distill해도 목표 도달 실패 보고 |

**한 줄 처방**: **분해를 1.3B에 학습시키려 하지 말고(=우리가 계속 실패한 것), 추론시 강한 planner에게 맡기고 1.3B는 실행만** 한다. 이게 우리 진단(분해=generation 병목)이 **직접 지시하는** 유일하게 capacity 벽을 피하는 길.

---

## 1. (F/B) Planner–Executor — 추론시 분해 분리 ★최유망

**핵심 통찰**: 우리 병목은 "1.3B가 분해를 **생성** 못 함". 그러면 분해를 **1.3B가 안 하게** 하면 된다. 강한 범용 LLM(planner)이 "induction on n, then case split on l" 같은 **고수준 계획/subgoal**을 내고, 우리 1.3B(executor)는 **각 subgoal의 tactic만** 채운다 — 이건 1.3B의 **강점**(built-in automation VALID 57–61%, tactic 수준은 됨).

| 논문 | id | 메커니즘 | 우리 적용 판정 |
|---|---|---|---|
| **BFS-Prover-V2** | 2509.06493 (2025-09) | 추론시 **hierarchical Planner–Prover**: 범용 LLM이 main goal→subgoal 분해, 전문 prover가 각 subgoal 병렬 증명(공유 캐시). miniF2F 95.08% | **직접 템플릿**. planner=강한 LLM, prover=우리 1.3B. Lean이지만 구조 이식 가능 |
| **Goedel-Code-Prover** | 2603.19329 (2026-03) | **코드검증**(Lean). decompose(sub-lemma 재귀)→complete(각 leaf tactic). **8B가 671B(84×)를 능가**. Verina/Clever/AlgoVeri 62.0% | **가장 우리 도메인(코드검증)에 근접**. 분해가 핵심임을 코드에서 실증. §2 score도 여기서 |
| **Draft-Sketch-Prove (DSP)** | 2210.12283 | informal 증명→formal **sketch**(고수준 뼈대)→ATP가 gap 채움. LLM이 sketch 생성 | 원조 planner-executor. sketch=분해 계획. Isabelle이지만 개념 동일 |
| Decoupled (IMO) | 2507.06804 | reasoning과 증명 분리(decoupled) | planner-executor의 수학 버전 |

**왜 이게 우리 진단에 완벽히 맞나**:
- 병목 = 분해 **생성**(coverage 22%). planner가 분해를 **주니** 1.3B는 생성할 필요 없음 → coverage 문제 소멸.
- 우리 실패의 61%가 초반 분해 divergence → planner가 그 초반만 잡아주면 됨.
- 1.3B는 "정답이 프롬프트에 있으면 실행은 됨"(retrieval-generation gap의 실행측). subgoal이 주어지면 tactic은 낸다.

**비용**: planner LLM 1콜/정리(또는 stuck 시점만). 강한 API(Claude/GPT/DeepSeek-V3) 또는 로컬 큰 모델. **1.3B 재학습 0** = 우리가 겪은 모든 학습 불안정 회피.

**논문 novelty**: 대부분 planner-executor는 **Lean 수학**. **Coq/CompCert(코드검증)에서 big-plans/small-executes**는 공백. 게다가 우리는 **"왜 작은 모델엔 이 분리가 필수인가"를 진단(coverage 22%)으로 동기부여** → diagnosis-driven method 스토리(약한 음성결과 논문보다 강함).

---

## 2. (D/search) 구조적 decomposition score — value-free를 되살리는 dense 신호 ★

**value-free가 17%로 죽은 진짜 이유**: 분해 후보를 **MC-롤아웃 QED 성공률**로 채점했는데 1.3B가 QED를 거의 못 내 **점수가 다 0**(sparse) → 랭킹 붕괴 + MC가 compute 낭비.

**Goedel-Code-Prover(2603.19329)의 처방**: 분해를 **"decomposition score"**로 채점 — (a) **constructive justification**(proof 재구성 + quickcheck) + (b) **structural effectiveness**(operator footprint/goal 복잡도 **감소량**). 이건 **QED 없이도 dense**(분해가 goal을 실제로 단순화했는지). **학습·배포 동일 기준**으로 씀.

**우리 적용**: VALUE_FREE_SEARCH를 재설계 — MC 대신 **dense 구조 점수**로 분해 후보 랭킹:
- goal 수 감소 / 각 subgoal의 term-size·hyp 수 감소
- 각 subgoal에 **built-in auto(auto/lia/congruence) 즉시 닫힘 여부**(우리 automation VALID 57–61%를 dense 신호로)
- QED 롤아웃 **불요** → sparse 붕괴 회피 + compute 급감

관련: SubgoalXL(2408.11172) subgoal-level supervision. RMaxTS/DS-Prover-1.5(2408.08152) intrinsic-reward MCTS.

---

## 3. (D) Reward-free 학습 value — QEDCartographer ★Coq 네이티브

| 논문 | id | 메커니즘 | 판정 |
|---|---|---|---|
| **QEDCartographer** | 2408.09237 (ICSE'25) | **reward-free RL**로 proof state **난이도**를 **proof 분기구조**에서 학습(=sparse-reward 우회). CoqGym 21.4% 자동증명, Proverbot 대비 27% 빠름 | 우리 **PPO critic(outcome-reward, explained_var≈0)·value-free MC(sparse) 둘 다 죽은 문제를 정확히 겨냥**. Coq·우리 스케일서 실증. value net 학습 필요 |
| HTPS | 2205.11491 | AlphaZero식 hypertree search + 학습 policy/value | 강력하나 대규모 compute·Lean |

**핵심 대조(논문거리)**: 우리 value 시도 2번(PPO critic=outcome-reward, value-free=MC-rollout) 다 sparse로 죽음. QEDCartographer는 **outcome이 아니라 분기구조**에서 value를 학습 → **"sparse-reward Coq에서 value를 얻는 올바른 방법"**. 우리 실패와 직접 대조하면 강한 클레임.

---

## 4. ✗ teacher-분해 distill→1.3B — capacity 벽 위험 (정직)

| 논문 | id | 메커니즘 |
|---|---|---|
| DeepSeek-Prover-V2 | 2504.21801 | DeepSeek-V3가 subgoal 분해→검증된 subgoal 증명을 CoT로 합성→cold-start RL. **671B**. dual-stage(큰 범용+작은 prover) |

**이론상 매력**: gold-injection(LUFFY)은 **인간 gold**라 모델이 못 가는 state(covariate shift, Ross-Bagnell O(εT²))로 실패. teacher-distill은 **teacher 자신의 검증된 self-consistent 분해**라 on-policy(teacher 기준)라 덜 위험.

**하지만 실측 경고(직접 관련)**: 소규모 distill 연구에서 **"1B·1.5B 모델은 distill해도 목표 정확도 도달 실패"**, **"teacher 크기엔 최댓값이 아니라 최적값"**, **"distill은 출력을 개선하나 teacher fidelity는 이식 안 됨"**. → **분해를 1.3B에 distill해도, 1.3B가 그걸 재현할 capacity가 없으면** 우리가 진단한 바로 그 generation-capacity 벽에 다시 부딪힘. covariate-shift 문제를 **capacity 문제로 옮길 뿐**.

**결론**: distill은 planner-executor보다 **열등**. planner-executor는 분해를 **추론시 1.3B 밖**에 두므로 학습할 분포 자체가 없어 **capacity 벽·covariate-shift 둘 다 원천 회피**. → **§1이 이론적으로도 우월.**

---

## 5. 기타 (직교 레버)

- **Graph2Tac (2401.02949)**: **online learning** — 같은 프로젝트의 최근 증명에서 test-time 학습, **locality**(가까운 lemma는 비슷한 증명구조) 활용. offline 대비 1.5–1.72×. CompCert(단일 대형 프로젝트)의 공유 타입/lemma에 유리(사용자 관심사와 연결). 단 **GNN 스택**이라 우리 LLM에 바로 못 붙임 — 별도 실험.
- kSubS/AdaSubS (2108.11204/2206.00702): subgoal 생성+검색. planner의 학습형 버전.
- LEGO-Prover (2310.00656): 재사용 skill(lemma) 라이브러리 성장.

---

## 6. 이론: 왜 planner-executor가 covariate-shift·capacity 벽을 둘 다 피하나

1. **gold-injection(실패)**: 인간 gold tactic을 1.3B에 주입 → 1.3B는 gold state에 못 도달 → 분포 불일치 → 압축오차 O(εT²). (우리 6종 전멸.)
2. **teacher-distill(위험)**: teacher의 검증된 분해를 1.3B에 학습 → 분포는 self-consistent(덜 위험)이나 **1.3B capacity가 부족하면 재현 실패** → capacity 벽(§4 실측).
3. **planner-executor(안전)**: 분해를 **추론시 외부 planner가 제공** → 1.3B는 **분해를 학습·생성할 필요 자체가 없음** → 학습할 분포가 없어 **covariate-shift 정의상 없음**, 1.3B는 항상 **in-distribution(subgoal별 tactic 예측)** 만 함. **우리 진단(분해=1.3B가 못하는 것)이 곧 "분해를 1.3B에서 빼라"는 처방.**

---

## 7. 권고 (급한 논문)

1. **★ 즉시 프로토타입 — Planner–Executor(§1)**: 강한 LLM이 stuck 정리에 고수준 Coq 계획(induction/destruct/핵심 lemma) 제시 → 1.3B가 각 subgoal tactic 실행. rand200 w2 600s로 37.5% 대비. **학습 0, 정리당 planner 1~수콜.**
2. **★ 결합 — 구조 decomposition score(§2)**: planner가 여러 분해 후보 낼 때 MC 아닌 **dense 구조점수**로 랭킹(value-free 재설계). sparse 붕괴 회피.
3. **fallback — reward-free value(§3, QEDCartographer)**: value 학습형 ablation이 필요하면.
4. **스토리**: "진단(coverage 22%=분해 generation 병목) → 학습형 개입 7종 실패(distill도 capacity 벽) → **분해를 추론시 분리(planner-executor)해 천장 돌파**". positive-number 후보 + 강한 diagnosis-driven novelty(**Coq/CompCert planner-executor 공백**).

---

## Sources
- QEDCartographer 2408.09237 — https://arxiv.org/abs/2408.09237 ; ICSE'25 https://people.cs.umass.edu/~brun/pubs/pubs/Sanchez-Stern25icse.pdf
- DeepSeek-Prover-V2 2504.21801 — https://arxiv.org/abs/2504.21801
- BFS-Prover-V2 (Planner–Prover) 2509.06493 — https://arxiv.org/abs/2509.06493
- Goedel-Code-Prover 2603.19329 — https://arxiv.org/html/2603.19329v1
- Draft-Sketch-Prove 2210.12283 — https://arxiv.org/abs/2210.12283
- Decoupled IMO 2507.06804 — https://arxiv.org/pdf/2507.06804
- SubgoalXL 2408.11172 — https://arxiv.org/pdf/2408.11172
- Graph2Tac 2401.02949 — https://arxiv.org/abs/2401.02949
- HTPS 2205.11491 ; RMaxTS/DS-Prover-1.5 2408.08152 ; kSubS 2108.11204 ; AdaSubS 2206.00702 ; LEGO-Prover 2310.00656
- 소규모 distill capacity 벽: "Teach Small Models to Reason by Curriculum Distillation" (EMNLP'25); PaD 2305.13888
