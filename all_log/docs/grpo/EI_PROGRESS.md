# Expert Iteration 진행 현황 & mixed 변화율

기준: **2026-07-28 10:56 KST** (자동 갱신 아님 — 스냅샷). π₀ = SFT→GRPO, 3라운드 학습(coverage로 수렴 판단) → 최종만 rand200 w2 600s(GPU1) 평가. 전부 GPU1(rollout=g1w8, gtrain, test=w2).

---

## 1. 진행률

| 라운드 | rollout(성공정리/총) = coverage | RFT(--sft) | GRPO | 상태 |
|---|---|---|---|---|
| **R1** | **101/283 = 35.7%** | ✅ r1sft | ✅ rango-grpo-ei-r1 | 완료 |
| **R2** | **108/288 = 37.5%** (+1.8pp) | ✅ r2sft | ✅ rango-grpo-ei-r2 (11:46) | 완료 |
| **R3** | 🔵 rollout 진행 중(11:46 시작) | — | — | rollout 중 |
| 최종 | rand200 w2 600s eval | | | 대기 |

- 실행 프로세스: `grpo_train` **1개**(pid 2830999, CUDA_VISIBLE_DEVICES=1, GPU1), `run_ei.sh` 1개. **중복 없음.**
- coverage 추세: R1 35.7% → R2 37.5% (**+1.8pp**). SFT→GRPO 단일(37.5%) 수준으로 **수렴 신호**(폭발적 상승 없음).

---

## 2. ETA (실측 보정)

각 단계 실측 소요:
- **rollout(300정리 g1w8, timeout600)**: R1 3h08m, R2 3h10m → **~3h10m**
- **RFT(--sft, 성공궤적 MLE, 2epoch)**: **~45m**
- **GRPO(전체 rollout, 2epoch)**: **~1h32m**
- **최종 rand200 w2 eval**: 과거 w2 실측 `tot_attempt_초/2worker` = **~12.5h**
  (baseline 13.4h, sft→grpo 12.9h, harvest 12.6h, leaf 12.6h — fail 125~133개가 각 ~650s 타임아웃, w2라 2개씩만 병렬 → 이게 EI 최장 구간)

**예상 타임라인 (±2h):**

| 단계 | 예상 완료 (KST) |
|---|---|
| ~~R2 GRPO~~ | ✅ 11:46 (07-28) |
| R3 rollout | ~14:56 |
| R3 RFT | ~15:41 |
| R3 GRPO | ~17:13 |
| **학습 전체(R3까지) 완료** | **~17:15 (07-28)** |
| **최종 rand200 w2 eval 완료** | **~05:45 (07-29)** |

→ **학습은 오늘 저녁(~17:30)**, **최종 성공률은 내일 새벽(~06:00 07-29)**. eval(12.5h)이 사실상 전체 시간의 절반 이상.

---

## 3. mixed 변화율 (GRPO 그룹 신호)

GRPO는 그룹(정리당 G=8 rollout) 단위로 학습. 그룹 종류:
- **dead** (전부 실패): advantage 0 → **학습 신호 없음**
- **mixed** (일부 성공/일부 실패): 그룹내 std>0 → **유효 gradient**
- **all-success** (전부 성공): std 0 → 신호 없음(이미 품)

관계식: **coverage(≥1 성공) = mixed + all-success**. 즉 mixed%가 실제 "배울 게 있는" 신호량.

| 라운드(GRPO) | groups | dead% | **mixed%** | all-succ% | grp_std | coverage(=mixed+allsucc) |
|---|---|---|---|---|---|---|
| **R1** | 283 | 64.3% | **31.1%** (88개) | 4.6% (13개) | 0.133 | 35.7% (101) |
| **R2** | 288 | 62.5% | **29.5%** (85개) | 8.0% (23개) | 0.125 | 37.5% (108) |
| **R3** | — | — | — | — | — | 대기 |
| **R1→R2 변화** | | **−1.8pp** | **−1.6pp** | **+3.4pp** | −0.008 | **+1.8pp** |

- RFT(--sft) 단계는 성공궤적만 MLE라 그룹 개념 없음 → mixed=0(위 표에서 제외).
- **R1 해석**: 신호 있는 그룹 31.1%뿐, **dead 64.3%**가 EI 근본 병목(대부분 정리가 8번 다 실패 → 못 배움). coverage 35.7% = mixed 31.1% + all-succ 4.6% 정확 분해(검산 OK).
- **R2 진단 — rich-get-richer(경계 경고)**: coverage +1.8pp는 **dead→mixed 전환이 아니라 mixed→all-success 졸업**으로 발생.
  - dead 64.3→62.5% (**−1.8pp뿐**, 어려운 정리 거의 못 뚫음)
  - mixed(유효 gradient) 31.1→**29.5% 감소** — 풀던 정리가 all-success로 졸업(std0=신호 소멸)해 신호 풀이 **오히려 축소**
  - all-success 4.6→8.0% (+3.4pp) — 이미 풀던 것을 8/8로 더 확신
  - grp_std 0.133→0.125 (그룹내 분산 감소 = 정책이 결정론적으로 수렴 중)
- **함의**: EI가 **hard theorem을 크래킹하지 못하고 solvable set만 강화**하는 전형적 정체. 신호(mixed)가 줄어드는 추세라 R3에서 coverage가 37.5% 부근에서 **평탄화(수렴)** 가능성 큼 → subgoal에서 본 **도달성/dead-group 병목과 동일 계열**. 근본 해결엔 dead 정리를 mixed로 바꿀 외부 신호(분해/커리큘럼/hindsight)가 필요.

---

## 3b. R3 rollout — all/mixed/dead 분해 & 새로 푼 정리 (동일 157개 부분집합)

라운드 간 정리 매칭은 **(file_name, proof_idx)** 안정키 사용(주의: rollout의 `theorem` 필드는 `abs(hash(text))`라 프로세스마다 랜덤 → 매칭 불가). R3 롤아웃 진행 중(168/~288 처리) 시점 스냅샷, R1·R2·R3에 공통 존재하는 **157개** 기준.

| 라운드 | all-solved | mixed | dead | coverage(all+mixed) |
|---|---|---|---|---|
| R1 | 6 | 48 | 103 | 54 (34.4%) |
| R2 | 13 | 45 | 99 | 58 (36.9%) |
| **R3** | **23** | 45 | **89** | **68 (43.3%)** |

- dead **103→99→89** (−14), all-solved **6→13→23** (+17), mixed 평탄(45~48).
- coverage 상승이 **mixed→all(확신) + dead→mixed(신규 크래킹) 두 경로 동시**.

**전이 R2 → R3:**

| 전이 | 개수 |
|---|---|
| dead → dead | 87 |
| mixed → mixed | 33 |
| all → all | 13 |
| **dead → mixed (★새로 풀림)** | **12** |
| mixed → all (확신 졸업) | 10 |
| mixed → dead (▽퇴보) | 2 |

→ dead→solved **+12 / 퇴보 −2 = 순증 +10**.

**기존에 한 번도 못 풀던 정리(R1·R2 모두 dead) 93개 중 R3 처음 풀림 = 7개** (전부 mixed):
`Constpropproof.v#6`, `ValueDomain.v#124`, `SelectOpproof.v#40`, `Globalenvs.v#35`, `Inliningspec.v#25`, `Integers.v#215`, `Interpreter_complete.v#16`.

**해석**: R2 GRPO metrics(mixed 감소)만으로 "정체"라 본 것은 **성급했음** — R3 rollout은 EI가 실제로 dead를 뚫어(103→89) **처음 푸는 정리 7개**를 만들었음을 보여줌. 단, 이는 **train셋 coverage**이며 최종 판정은 held-out rand200 w2 eval. train↑가 held-out↑을 보장하진 않음(과적합 여지).

## 4. 참고
- 최종 비교 기준: **SFT→GRPO 75/200=37.5% (p90 399s)**. EI가 이를 유의미하게 넘겨야 성공.
- 관련: [[research-direction-2026-07]] 도달성 병목(§10), dead group 문제는 [[SUBGOAL_PAPER_ASSESSMENT]] 참조.
