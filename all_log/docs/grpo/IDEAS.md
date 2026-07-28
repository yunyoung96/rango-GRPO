# IDEAS — SFT→GRPO(37.5%) 이후 시도 후보 (우선순위·비용·기대효과)

작성 2026-07-27. 관련: [[sft-subgoal-grpo-naming]], `SUBGOAL_PAPER_ASSESSMENT.md`(§10 도달성 진단), `HARVEST_ROUND.md`. EI 상세는 이 문서 **부록 A**.

---

## 0. 맥락 & 진단

- **최고 성능 = 단순 SFT→GRPO 37.5%** (baseline SFT `rango` 33.5%). subgoal/cascade/harvest 모두 **held-out에서 이걸 못 넘음.**
- **정량 진단**(§10): 병목은 세 가지.
  1. **희소보상** — s0 롤아웃의 **62%가 dead**(전멸, gradient 0).
  2. **도달성(reachability)** — 배운 subgoal의 83%를 완전체 풀이 중 미도달. "닫기"만 배우고 "도달"은 못 배움.
  3. **테스트가 compute/timeout-bound** — 실패의 ~99%가 600s 타임아웃. **시간·탐색을 더 주면 성공↑.**
- **원칙**: 싼 것·즉효부터. 커리큘럼 트릭은 접음. EI/스케일은 그다음.

---

## 1. 우선순위 표

비용/기대효과 = {낮음 / 중 / 높음}. 우선순위 P1(먼저)~P4(천장).

| # | 아이디어 | 공략 대상 | 비용 | 기대효과 | novelty | 우선 | 자산/상태 |
|---|---|---|---|---|---|---|---|
| **3** | **추론시간 탐색 강화 (RMaxTS/센 BFS)** | 도달·compute-bound | 낮음 | **중~높음** | 낮음 | **P1** | `rmaxts`·`bfs-prover` alias 有 |
| **2** | GRPO 탐색 튜닝 (clip-higher+dyn-sampling+temp↑) | 희소보상·탐색 | **낮음** | 낮~중 | 낮음 | **P1** | `clip_eps_high`·`dyn_resample` 훅 有 (P0.5 TODO) |
| **1** | Dense/process 보상 (goal감소·깊이 부분크레딧) | 희소보상(62% dead) | 낮음 | 중 | 중 | **P1** | §4-③ 엔진 훅 有. ⚠reward hacking |
| **EI** | **Expert iteration (검색→성공 학습, 다라운드)** | 도달+닫기·희소 | 중 | **중~높음** | 중 | **P2** | 자산 대부분 有 (부록 A) |
| **4** | Retrieval/premise 선택 개선 (dense 임베딩) | 후보 질 | 중~높음 | 중~높음 | 낮음 | P2 | 지금 BM25+TF-IDF |
| **5** | 보조 lemma 라이브러리 학습 (전제 DB 추가) | 정리 간 조립 | 중 | 중 | 중~높음 | P2 | 신규 |
| **6** | SFT 데이터 확대/증강 (all-CoqStoq) | 바닥 | 중 | 중 | 낮음 | P3 | 신규 |
| ~~7~~ | ~~PPO (actor-critic, 학습 value head)~~ | 분산·희소 | 중 | **❌** | 낮음 | **접음** | **파일럿 critic 실패(explained_var≈0)** |
| **8** | DPO (성공 vs dead 선호쌍) | 희소·안정 | 낮~중 | 낮~중 | 낮음 | P3 | 신규 |
| **9** | Tree-GRPO / VinePPO (step별 credit) | 긴 증명 공로배분 | 높음 | 중 | 중 | P3 | §4 ①-심층2 |
| **10** | Reachability-aware 학습 (도달에 보상/backward) | 도달성(정면) | 중~높음 | 중 | 중~높음 | P3 | 신규 |
| **11** | 스케일 (7B / DeepSeek-Prover base) | 용량(천장) | 높음 | **높음** | 낮음 | P4 | 신규 |

---

## 2. 아이디어 상세 (그룹별)

**A. 희소보상(62% dead) 직접 공략 — 싸고 근거 확실**
- **①Dense/process 보상**: Qed 이진보상 대신 열린 goal 수 감소·증명 깊이에 부분크레딧 → dead 그룹을 gradient-보유로. 위험: 진짜 못 풀고 부분진행만 챙기는 reward hacking.
- **②GRPO 탐색 튜닝(P0.5)**: clip-higher(DAPO)+dynamic sampling+롤아웃 temperature↑. entropy 0.11(확신과다) 완화 → 낮은확률 tactic 성장 → 새 증명 발굴. 가장 쌈(플래그만).

**B. 추론시간 탐색 강화 — 최고 가성비 (학습 0)**
- **③RMaxTS/센 BFS**: 학습 안 하고 탐색만 세게 해도 pass@600s 직접↑(dead 대부분 타임아웃). length-norm 스코어링·후보 다양화·재시도. **제일 먼저.** EI의 탐색 단계로도 재사용.

**C. Retrieval/데이터 — 정리증명의 알려진 큰 레버**
- **④Retrieval 개선**: BM25+TF-IDF → dense 임베딩·더 나은 전제선택 → tactic 후보 질↑. RL과 직교.
- **⑤보조 lemma 라이브러리(DreamCoder식)**: 증명한 유용 lemma를 전제 DB에 추가 → 이후 증명이 인용 → 정리 간 조립 재사용. subgoal(정리 내부)과 달리 도달성 우회.
- **⑥SFT 데이터 확대**: all-CoqStoq·증강 → 바닥↑.

**D. RL 정식화 바꾸기**
- **⑦PPO**: 학습 value head로 group-mean baseline 대체 → 분산↓. 큐에 있음.
- **⑧DPO**: (성공 vs dead 시도) 선호쌍. value 불필요·안정·간단.
- **⑨Tree-GRPO/VinePPO**: 트리 롤아웃 step별 credit assignment(긴 증명). 복잡·불확실.

**E. 도달성 직접 공략 (진단 정면)**
- **⑩Reachability-aware**: "닫기" 말고 **"도달"에 보상** — 닫을 수 있는 상태 도달 시 크레딧, 또는 닫을 수 있는 goal에서 backward 확장. 진단된 병목 직접. novel-ish·불확실.

**F. 스케일 (정직한 천장)**
- **⑪7B/DeepSeek-Prover base**: 용량↑. 위가 정체하면 가장 확실한 점프. 이미 proof-tuned base 활용 가능.

---

## 3. 추천 순서

**P1 싼 즉효 3종 먼저**: ③추론탐색 → ②GRPO 튜닝 → ①dense 보상. (테스트가 compute-bound이라 ③이 학습 없이 숫자 올릴 확률 최고.)
→ 그래도 37.5% 못 넘으면 **EI(다라운드)** 또는 **④retrieval** → 최후에 **⑪스케일**.

지금은 `refair`(cascade-s0/s0r2 공정 w2 재측정) 완주로 **진짜 baseline 확정**이 선행. 그 위에서 위 순서로.

---

## 4. dead group 문제 정면 — 어느 아이디어가 어디까지 푸나

**dead group** = 62% 정리에서 G개 시도 전멸 → advantage=(r−평균)/std=0 → **gradient 0**(학습 기여 0). "이걸 EI/아이디어들이 진짜 푸나?"에 대한 정직한 분석.

**dead를 3종으로 쪼개면:**
| 종류 | 정의 | 누가 공략 |
|---|---|---|
| (a) **부분진행-dead** | Qed는 못 하나 일부 goal은 닫는 진행 있음 | **dense/process 보상**(부분크레딧→variance→mixed화) |
| (b) **탐색가능-dead** | 단일 롤아웃(G8/step20)엔 실패, 더 센 탐색/후보질이면 증명 존재 | 검색/EI/RMaxTS·retrieval·lemma |
| (c) **하드코어-dead** | 모델 용량(+검색+분해) 밖. 뭘 해도 dead | **스케일(더 큰/proof-tuned base)만** |

**정직한 답:**
- **EI 포함 대부분은 dead를 "완전히" 못 풂** — (b) slice를 얼마나 깨느냐일 뿐, (c)하드코어는 그대로.
- **dense 보상**이 dead 메커니즘(신호 0)을 가장 정면으로 침 — 부분진행 variance로 (a) 신호화. 단 완전정지(진행 0)엔 dense도 0 → 무력, + reward hacking 위험.
- **(c)하드코어는 스케일만** 건드림.

**핵심 리프레임 — dead를 다 풀 필요는 없다:**
- held-out을 올리려면 **(a)+(b) slice만 신호로 전환**해도 됨. dead는 "poison"이 아니라 **"낭비된 batch"**(dynamic sampling으로 효율화하면 그만).
- 진짜 천장은 (c)하드코어 = **스케일 문제**. 소규모(1.3B)에선 (a)(b)를 긁어 **+1~3pp** 여지, 그 이상은 스케일.
- → 전략: **(a)dense + (b)검색/EI로 긁을 수 있는 만큼 긁고, (c)는 스케일로 미룬다.** "dead 완전 해결"은 목표가 아니라 착시.

---
---

# 부록 A. Expert Iteration 상세 계획

검색으로 찾은 **완전체 증명**을 학습(도달+닫기 동시). 위 표의 "EI" 항목 상세.

## A.0 왜 (진단 재확인)
subgoal 방법은 모델을 subgoal에 갖다 놓고 **"닫기"만** 훈련 → 완전체는 그 상태까지 **"도달"**해야 하는데 안 가르침 → 배운 스킬 83% orphan(§10). 레벨끼리도 0% 중첩. **해법 = 완전체 증명을 검색으로 찾아 통째 학습**(도달+닫기 end-to-end, 모델이 실제 방문한 상태 = on-policy p_reach=1).

## A.1 Expert Iteration이란 (STaR/RFT/DeepSeek-Prover 계열)
```
반복 k:
  1) [탐색] π_k 로 학습정리 증명 시도 — 단일 롤아웃 아닌 검색(BFS, 큰 budget)으로 깊이.
  2) [수집] Coq 검증 성공(전체 증명)만. 실패 버림.
  3) [학습] 성공들로 π_k→π_{k+1} (RFT=--sft, 또는 성공=positive GRPO).
  4) [평가] rand200 held-out. coverage(≥1증명 정리 수) 추적. plateau까지.
```
**이론**: 학습데이터=자기 정책 생성+Coq 검증 성공 → on-policy, covariate-shift 없음(Ross&Bagnell O(εT²) 회피). Polu&Sutskever expert iteration·STaR·DeepSeek-Prover(RMaxTS) 계열. 단조개선(정책반복 가정 하).

## A.2 왜 subgoal 병폐를 고치나
| | subgoal(cascade/harvest) | Expert Iteration |
|---|---|---|
| 학습 대상 | subgoal **닫기**만 | **완전체 증명**(도달+닫기) |
| 데이터 | gold 분해(off-policy) / 부분 harvest | 검색이 찾은 자기 성공(on-policy, p_reach=1) |
| 도달 훈련 | ✗(갖다 놓음) | ✓(처음~끝) |
| 레벨 조립 문제 | 있음(0% 중첩) | 없음(단일 완전체) |

harvest는 "부분-증명 EI"의 특수형(닫기만 강화→도달 그대로→신호 정체). EI가 도달까지 메움.

## A.3 우리 환경 구체 설계
- **데이터**: 학습 `compcert_bs2_train_idx.txt`(300, dead 62%가 검색 타깃). held-out `compcert_bs2_rand200_idx.txt`(**w2로만 평가**, g2w4 오염 금지).
- **탐색(핵심 레버)**: `bfs_prover_searcher.py`(BFS, expansion당 E개 temp 샘플). budget을 롤아웃(G8/step≤20)보다 크게 — E=8~16, 깊이↑, per-thm timeout 300~600s. **dead 정리에서 새 증명 발굴**이 목적.
- **병렬**: `run_all.py --gpus 0,1 --workers 2`(GPU당 2, 오염 방지 밀도).
- **학습**: 1차 **RFT(`grpo_train --sft`)** — 찾은 완전체 증명 MLE(항상 gradient·안전). 2차 옵션 GRPO(성공=positive)+dynamic sampling. `--kl_beta 0.04 --lr 1e-6 --epochs 2`.
- **반복(진짜 미시도 레버)**: 기존은 **1라운드**. EI는 collect→train 다라운드(3~5). 라운드당 반나절~하루.

## A.4 단계별 프로토콜
```
Round 0: π_0 = 현재 SFT→GRPO(rango-grpo). rand200 = 37.5% (기준선).   ※ π_0=SFT(rango)로 할지 결정 필요(clean ablation)
Round k (1..K):
  1) 검색: run_all --alias <bfs> --idx-file bs2_train --gpus 0,1 --workers 2 --timeout 600 → 성공증명 jsonl
  2) 필터: Coq 성공만 + 중복제거(정리별 최단 1개) + 쉬운문제 과대표집 방지
  3) 학습: grpo_train --sft --init_adapter π_{k-1} --rollouts <found> → π_k (+원 SFT 일부 혼합)
  4) 평가: run_all --alias π_k --idx-file rand200 --timeout 600 --workers 2
  5) 기록: coverage_k, heldout_k. plateau면 중단.
```
결과표: `| round | coverage(train) | rand200 | Δ vs 37.5% |`.

## A.5 하이퍼파라미터 & 리스크
| 리스크 | 대응 |
|---|---|
| 검색 비용(1.3B 단일노드) | budget 점증, GPU당 2병렬, dead에만 큰 budget |
| 쉬운문제 편식→collapse | 잘 푸는 정리 downweight, 원 SFT 혼합 |
| 중복·과적합 | 정리별 성공 1~2개 dedup, 경로 다양성 |
| KL 폭주(max_ρ) | kl_beta 유지, lr 낮게, 라운드마다 held-out 감시 |
| 검색해도 새 증명 거의 없음 | 병목=스케일 → 표 ⑪ |

## A.6 성공 판정 (우리 것끼리, published 비교 금지)
- 1차: rand200 held-out(w2) — **37.5% 넘나** (노이즈 ±2~3%p, 가능하면 2회 평균).
- 2차: train coverage↑, 도달-매트릭스(§10) 재측정 성공경로 등장률↑(도달 학습 실제 발생 확인).
- 판정: 넘으면 "검색으로 더 돌리는 게 답"; 정체면 **스케일**(⑪).

## A.7 기존 자산 매핑
| 필요 | 기존 | 할 일 |
|---|---|---|
| 검색 | `bfs_prover_searcher.py` | budget 플래그 노출 + 성공증명 jsonl 덤프 |
| 병렬 | `run_all.py`(--gpus/--workers) | 그대로 |
| RFT | `grpo_train --sft` | 대상만 full proof |
| 평가 | `run_all.py` rand200 w2 | 그대로 |
| alias | `run_thm.py` | π_k 등록 |

## A.8 다음 액션
1. `refair` 완주 → 진짜 baseline 확정.
2. `bfs_prover_searcher.py` budget 플래그 + 성공-증명 덤프 확인(작은 구현).
3. Round 1 파일럿: bs2 300 검색(중간 budget) → 새 증명 수 → RFT → rand200. 넘으면 다라운드.

---
---

# 부록 B. Dense/process 보상 (dead group 정면 — P1)

- **목적**: dead 62%의 **(a)부분진행-dead**를 신호로 전환.
- **메커니즘**: Qed 이진보상 대신/추가로 **부분크레딧**: `reward = α·(1 − open_goals/init_goals) + [Qed]1.0`. 또는 step별 process 보상(PRM). dead group도 부분진행 variance → mixed화 → advantage≠0.
- **우리 설계**: `grpo_rollout`에 이미 subgoal reward(`len(goals)<seed_level`) 로직 있음 → **완전체 롤아웃에 goal-감소 부분보상**으로 확장(§4-③ 엔진 훅). α 작게(0.1~0.3) 시작.
- **dead-group 관계**: (a) 공략. **(c)완전정지-dead엔 무력**(진행 0 → dense도 variance 0). (b)엔 간접.
- **리스크**: reward hacking — `admit`/얕은 진행으로 goal 수만 줄이기. → verifier로 admit 금지, "닫힘"만 크레딧, α 작게, **held-out로 반드시 검증**(부분보상↑인데 held-out↓면 hacking).
- **성공판정**: dead→mixed 비율↑ + **held-out↑**(부분보상 자체가 아니라).

# 부록 C. GRPO 탐색 튜닝 (P0.5 — P1)

- **목적**: 저엔트로피(0.11) collapse 완화, dead→mixed 전환 기회↑, 배치낭비 제거.
- **메커니즘**: ① **clip-higher**(`--clip_eps_high 0.28`, DAPO) — 낮은확률 tactic 성장 허용. ② **dynamic sampling**(`dyn_resample>0`) — mixed 그룹 찰 때까지 롤아웃 이어 수집, dead/all-solved 스킵. ③ 롤아웃 **temperature↑** — 다양성.
- **우리 설계**: **플래그만**(추가 구현 거의 0). clip_eps_high·dyn_resample·temperature 켜고 재실행.
- **dead-group 관계**: (b)탐색가능-dead를 mixed로 전환할 확률↑(**신호 창조는 아님**). dynamic sampling은 dead를 "스킵"(효율↑)이지 해결 아님.
- **리스크**: temp↑ → 노이즈↑·KL 폭주(max_ρ). lr·kl_beta 관리. epoch 2→1도 검토(drift↓).
- **성공판정**: entropy↑, mixed 비율↑, held-out.

# 부록 D. 추론시간 탐색 (RMaxTS/센 BFS — P1, 학습 0·즉효)

- **목적**: 테스트가 compute/timeout-bound → **탐색 세게 = pass@600s 직접↑**(학습 없이).
- **메커니즘**: BFS/best-first/MCTS의 확장수·샘플수·깊이↑, length-norm 스코어링, retrieval-augmented 후보 다양화, 실패 시 재시도.
- **우리 설계**: `rmaxts`·`bfs-prover` alias 튜닝. rand200 w2에서 **budget sweep**(budget↔pass 곡선).
- **dead-group 관계**: 학습 안 하므로 dead(학습신호)와 무관 — 대신 **(b)탐색가능-dead를 테스트에서 직접 풀어** 숫자를 올림. + **EI의 데이터 생성 단계로 재사용**.
- **리스크**: 시간 비용. budget↔pass 곡선으로 손익 판단.
- **성공판정**: rand200 pass↑ (vs 37.5%).

# 부록 E. Retrieval/premise 선택 개선 (P2)

- **목적**: tactic 후보 질↑ → 직접 성공↑ (정리증명의 알려진 큰 레버).
- **메커니즘**: 현재 BM25(증명)+TF-IDF(전제) → **dense 임베딩**(코드/수학 특화) 재랭킹, 전제선택 정확도↑.
- **우리 설계**: retriever 교체/재학습 또는 후보 재랭킹 계층 추가. RL과 직교 → SFT/EI와 결합.
- **dead-group 관계**: (b) 일부를 "더 나은 후보"로 solvable화. 간접.
- **리스크**: 재학습 비용, 파이프라인 변경.
- **성공판정**: 후보 recall↑, pass↑.

# 부록 F. 보조 lemma 라이브러리 학습 (P2 — 정리 간 조립)

- **목적**: 증명한 유용 lemma를 재사용 → **cross-theorem 조립**(정리 내부 subgoal과 다른 축, §10 도달성 우회).
- **메커니즘**: 성공 증명에서 재사용성 높은 lemma 추출 → **전제 DB에 추가** → 이후 증명이 `apply`/`rewrite`로 인용. DreamCoder식 library learning.
- **우리 설계**: `harvest_subgoals.py` 확장(lemma 추출) → retrieval DB 주입.
- **dead-group 관계**: 어려운 정리를 "이미 증명된 lemma 인용"으로 (b)→solvable화.
- **리스크**: lemma 폭증·노이즈, 인용 실패.
- **성공판정**: lemma 인용률, pass↑.

# 부록 G. PPO (actor-critic, 학습 value head — ❌파일럿 실패, 접음)

- **목적**: 학습 value baseline으로 분산↓ (GRPO의 group-mean 대체).
- **메커니즘**: value head + GAE. `V(s)` 학습해 advantage 추정.
- **⚠️실측(파일럿, 2026-07-27)**: **critic 학습 실패** — `explained_var ≈ 0`(18샘플 평균 −0.008, max 0.037, 음수 빈번). value head가 모든 상태에 ~0 예측(v_mean~0.001–0.04). 희소보상(return 대부분 0)이라 "그냥 0"이 최적 → **분산 못 줄임 = critic 존재 이유 소멸.** value-head 3구조(linear/mlp/mlp2) 다 실패. 평가는 조각(N=5~50)에서만 돌고 접음. [[ppo-bigscale-pending]]
- **dead-group 관계**: **근본 해결 아님**(실증) — dead=reward 0이면 value 타깃도 0.
- **결론**: **접음.** 이게 GRPO가 critic-free인 이유를 실측 재현. bigscale PPO 안 함.

# 부록 H. DPO (선호학습 — P3)

- **목적**: value·advantage 없이 안정 학습.
- **메커니즘**: (성공 proof=chosen, dead 시도=rejected) 쌍으로 preference loss.
- **우리 설계**: 같은 정리의 성공/실패 쌍 구성.
- **dead-group 관계**: dead 정리는 **성공쌍이 없어 preference 못 만듦 → dead 미해결.** mixed/solved에서만.
- **리스크**: 쌍 구성 편향, 완전-dead 활용 불가.
- **성공판정**: held-out.

# 부록 I. Tree-GRPO / VinePPO (step별 credit — P3)

- **목적**: 긴 증명의 **step별 공로배분**(어느 tactic이 좋았나).
- **메커니즘**: 트리 롤아웃, 각 노드 Monte-Carlo value로 step-level advantage. (§4 ①-심층2.)
- **우리 설계**: 롤아웃을 트리로 확장(공유 prefix 재사용) + 노드 value 추정.
- **dead-group 관계**: dead에서도 "어느 step까지가 문제였나" 부분신호 가능(부분).
- **리스크**: 구현·비용 큼, 소규모 효과 불확실.
- **성공판정**: 긴 증명 pass↑, 공로배분 품질.

# 부록 J. Reachability-aware 학습 (P3 — 진단 정면)

- **목적**: §10 진단 정면 — "닫기" 말고 **"도달"**을 훈련.
- **메커니즘**: 닫을 수 있는 상태에 **도달하면 크레딧**(reach reward); 또는 닫을 수 있는 goal에서 **backward 확장**해 도달 경로를 학습.
- **우리 설계**: 모델이 닫는 subgoal 집합을 알고(harvest), 그 상태로의 도달을 보상하는 롤아웃 설계.
- **dead-group 관계**: dead 원인이 "도달 실패"인 (b) 정면.
- **리스크**: 보상설계 난이도, novel·불확실.
- **성공판정**: 도달-매트릭스(§10) 성공경로 등장률↑, held-out.

# 부록 K. 스케일 (P4 — 하드코어 유일 해법)

- **목적**: **(c)하드코어-dead** 상향 = 진짜 천장 올리기.
- **메커니즘**: 1.3B → **7B / DeepSeek-Prover-V1.5·V2 base**(이미 proof-tuned), 더 많은 데이터/컨텍스트, 더 긴 검색.
- **우리 설계**: base 교체 후 SFT→GRPO/EI 재실행. **단일노드 2GPU 제약** → LoRA·양자화 필수. ⚠OCaml/opam 환경 불변 준수([[no-ocaml-version-change]]).
- **dead-group 관계**: **(c)를 건드리는 유일한 축.** 용량↑ = 이전엔 무조건 dead였던 게 mixed 가능 → 근본적 dead↓.
- **리스크**: 비용·메모리(7B 로드), 환경 리스크.
- **성공판정**: **dead 비율↓(근본)** + held-out 큰폭↑.
