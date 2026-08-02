# RL-for-Coq가 왜 정체하나 — 진단 + 포괄적 음성결과 (paper-ready)

작성 2026-07-30. 대상: DeepSeek-Coder-1.3B + LoRA + BM25/TF-IDF retrieval, CompCert(Coq/coq-lsp) next-tactic. 비교는 우리 rango만(published 미비교).

## 한 줄 주장
**모든 방법이 rand200 held-out ~37.5%에 수렴.** 병목은 **retrieval도 ranking도 generation-coverage도 아니고**, **분해 선택(selection)** + **도달성(reachability)**. 이는 **1.3B 스케일의 capacity 벽**이며, 알고리즘으로 안 뚫림.

## 1. 최고 성능 & 천장
| 방법 | rand200 (held-out) |
|---|---|
| SFT | 33.5% |
| **SFT→GRPO (최고)** | **37.5%** |
| 안전-EI (overfit-hardened) | 35.0% |
| divergence-DPO | 35.7% (부분, **unique solve 0**) |

## 2. 3단계 소거 진단 (실측)
- **retrieval — 병목 아님**: gold lemma recall **88.5%**(top-50), rank median **2~3**. 필요한 건 상위에 있음.
- **built-in/환경 — 병목 아님**: automation(lia/auto/ring) VALID **57~61%**.
- **★ 진짜 병목 = 분해 selection + 도달**:
  - retrieval이 정답을 top-3에 줘도 정책은 dead에서 66% 오선택 — 그중 **80%가 이미 앞서 분해를 틀려 off-path**된 증상. 순수 lemma 오선택 8%.
  - **capability 벽(과적합 아님)**: train dead ~58% ≈ test 실패 ~62%.

## 3. ★정정 — coverage(생성)는 벽이 아니다
초기 진단의 "coverage 22% = 생성 못 함"은 부정확. **재측정**: gold destruct의 **~80%가 열거(`_targeted_cands`)로 생성 가능**(post-intros destruct 기준). 실제 벽은:
1. **선택**: 같은 goal의 9~18 후보 중 gold를 고를 **local 신호 없음**.
2. **도달**: 옳게 쪼개도 subgoal을 못 닫아 그 분해에 **보상 credit이 안 감**(sparse).

## 4. 포괄적 음성결과 (모든 원칙적 개입이 실패)
| 방법 | 결과 | 왜 실패 |
|---|---|---|
| Expert Iteration / safe-EI | 35% | dead group(신호 0) 못 살림 |
| gold 주입 6종(LUFFY·KL-LUFFY·revcurr·backward·DAPG·RFT-gold) | 전부 baseline 미달, 회귀. union +0 | **covariate shift**(d^gold≠d^π, 도달 16.7%); dead group 86% 부활시켜도 test 0 상승 |
| subgoal(leaf/cascade) | ≤37.5% | 도달성(§10) |
| PPO(critic) | 실패(explained_var≈0) | 희소보상 critic 학습 불가 |
| selection-DPO(divergence) | 35.7%, unique 0 | margin↑(acc 0.54→0.65)지만 생성확률·solve 불변 |
| **value-free MC search** | **32.5→17% 붕괴** | 1.3B가 롤아웃서 QED 못 내 MC 신호 sparse=0 → 랭킹 붕괴+예산 소진 |
| **32B planner (추론, inference)** | ~37.5%(천장 근처) | 범용 32B가 CompCert 분해 대상을 못 고름 |
| **32B-opening (학습 롤아웃)** | **dead 59→78%(악화)** | 강제 opening이 valid하나 gold와 다른 대상(target 일치 14%) → rango가 풀던 것도 죽임(regress 8, revive 1) |

## 5. 결정적 증거들 (논문 figure 후보)
- **"신호↑ ≠ 성능↑"**: gold-injection이 dead group 86% 부활(롤아웃 성공률↑)해도 test 성능 0 상승 → covariate shift 실증.
- **value-free 붕괴 32.5→17%**: net 없는 MC value는 이 스케일서 무의미(신호 0).
- **32B target-match 14%**: 강한 32B조차 gold의 분해 대상을 86% 못 맞힘 = 선택이 벽(coverage 아님).
- **32B-opening net-harm(revive 1/regress 8)**: 잘못된 강제 분해가 rango의 옳은 분해를 덮어씀 + 좋게 열어도 도달 벽으로 revive 1뿐.

## 6. 논문 프레이밍
"**작은 formal-prover(1.3B)의 성능 천장을 엄밀히 진단**: retrieval(88.5%)·ranking·generation-coverage(80% 열거가능)가 아니라 **분해 선택(local 신호 부재)+도달(희소 credit)**. **10+ 원칙적 개입**(EI, gold 6종, subgoal, PPO, selection-DPO, value-free search, 32B planner/opening)이 모두 37.5%를 못 넘고, **강한 32B조차 분해 대상을 14%만 맞히며 강제 시 오히려 악화**. → 병목은 알고리즘이 아니라 **스케일(capacity)**. " 
- 기여: (1) 실패 공간의 포괄적 지도, (2) coverage-아닌-선택+도달 국소화(정정), (3) covariate-shift·MC-sparsity·selection의 실증.

## 7. 유일하게 남은 레버 (알고리즘 밖)
- **더 큰 executor** (capacity 직접 증대) — Qwen2.5-Coder-7B rango 재학습(별도 서버 큐). 알고리즘 공간은 소진.

---
근거 문서: [[BOTTLENECK_ANALYSIS]] · [[GOLD_PROOF_METHODS]] · [[BREAK_BOTTLENECK_LITERATURE]] · [[PLANNER_EXECUTOR_DESIGN]] · 메모리 [[coverage-not-wall-selection-reachability]]
