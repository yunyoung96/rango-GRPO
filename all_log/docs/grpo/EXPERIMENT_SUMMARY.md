# CompCert 정리증명 RL — 전체 실험 종합 (2026-07-29)

Rango(DeepSeek-Coder-1.3B + LoRA r64 + BM25 proof/TF-IDF premise retrieval, next-tactic, CompCert/coq-lsp) 위에서
"SFT→GRPO로 dead group을 깨 성능을 올린다"를 목표로 한 전체 실험의 종합. 관련: [[CEILING_ANALYSIS]], [[worker-timeout-confound]], [[research-direction-2026-07]].

---

## 0. TL;DR (3줄)
1. **학습 방식(SFT/GRPO/DPO/SRFT/subgoal/harvest/gold/PPO)은 뭘 해도 ~37% 천장**에 수렴. 방법이 아니라 정리 난이도가 지배.
2. **"28% 천장"은 착시** — BFS 검색 탓. 같은 조건에서 **classical rango = 37% ≫ BFS = 28%**. 워커·GPU 아님.
3. **진짜 병목 = 도달성(capability)** — Coq 실행검증: 실패의 **57~59%는 자동화로도 못 닫는 진짜 어려운 잔여**(train·test 일치). → 다음 레버 = **큰 base(Qwen2.5-Coder-7B) 재학습**(진행중).

---

## 1. ★마스터 결과표 (rand200, 모두 우리 자체 측정)
> ⚠️ 성공률은 **(검색·워커·HW)** 세 축에 confound. 다른 축끼리 직접 비교 금지. Ada=RTX6000 Ada 48GB, BW=Blackwell 96GB.

| 방법 | 검색 | 워커 | HW | rand200 성공률 |
|---|---|---|---|---|
| SFT→GRPO | classical | w2 | Ada | **37.5%** (75/200) |
| cascade s0r2 (harvest) | classical | w2 | Ada | **37.5%** (75/200) |
| leaf-subgoal | classical | w2 | Ada | 37.0% (74/200) |
| **#5 순수 rango** | classical | **w6** | **BW** | **37.0%** (74/200) |
| **#6 SFT→GRPO** | classical | w6 | BW | 34.5% (69/200) — 순수 rango(37%) 못 넘음 |
| baseline (rango SFT) | classical | w2 | Ada | 33.5% (67/200) |
| **combo-U (SRFT)** | BFS | w6 | BW | 32.5% (65/200) |
| combo-D (SFT+GRPO+DPO, EI2) | BFS | w6 | BW | 28.5% (57/200) |
| baseline (rango SFT) | **BFS** | w6 | BW | 28.0% (56/200) |
| B-EI (BFS-Prover SFT+DPO) | BFS | w6 | BW | 27.0% (54/200) |

**읽는 법**: classical 계열은 전부 **33.5~37.5%**, BFS 계열은 전부 **27~32.5%**. classical·w6·BW(#5 37%)가 classical·w2·Ada(33.5~37.5%)와 같은 무리 → **워커·HW가 아니라 검색(classical≫BFS)이 갈림의 축.**

---

## 2. 두 개의 confound (착시의 정체)
### 검색 축 — classical ≫ BFS (지배적)
같은 워커(w6)·HW(BW)에서 **classical 37% vs BFS 28% (+9%p).** BFS-Prover(length-norm best-first)는 우리 1.3B에 classical rango(누적 logprob)보다 나쁨. "28% 천장"은 BFS 선택 탓이었고, **classical rango의 진짜 천장은 ~37%.**

### 워커 축 — w2 > w6 (부차적, HW 의존)
**실패 정리의 100%가 timeout(600s)에서 죽음** → 워커↑=정리당 CPU↓=탐색노드↓=성공↓. 과거 고득점은 전부 w2. 단 **현재 BW는 58코어 load~17로 CPU 여유** → w6가 안 굶겨서, 현재 HW에선 이 효과 약함(그래서 #5 w6가 37%로 w2급).

**GPU 속도는 성공률을 직접 안 바꿈**(노드/600s를 통한 간접효과, BW가 더 빠름).

---

## 3. ★병목 진단 — Coq 실행검증 (텍스트 아님, goal 기준)
### 실패 = 긴 증명
성공 gold ~9 step vs 실패 gold ~28 step. train·test 동일 패턴.

### 실패지점에서 정말 필요했나 (all-solvers 배터리)
각 실패 정리에서 정책이 **실제 도달한 최심 state**에서 강력탐색(`auto|lia|nia|ring|congruence|...`)으로 나머지가 닫히나:

| 결과 | train(189) | rand200(113) | 레버 |
|---|---|---|---|
| 자동화로 닫힘(도달했으나 놓침) | 42% | 40% | **싼 자동화** |
| 자동화도 못 닫음(진짜 어려움) | **57%** | **59%** | **capability(큰 모델)** |
| gold 도달률(중앙) | 67% | 78% | — |

- **train↔rand200 일치**(42↔40, 57↔59) = 병목이 셋·방법 무관한 **구조적 사실.**
- 개별 step은 96% 자동대체 가능하지만(step-level), 잔여 **전체**는 40~42%만 — 차이는 **중간 state 도달**을 자동화가 못 해서. → **57~59%는 순수 도달성(§10: "닫기는 배우나 도달을 못 배움").**
- **retrieval/rerank는 실병목 아님** — 96% 자동대체가 반증. (reranker 넣으면 2-agent만 되고 효과 작음.)

---

## 4. 시도했고 천장 못 넘은 것 (전부 ~37% 수렴 또는 실패)
| 방법 | 결과 | 핵심 이유 |
|---|---|---|
| SFT→GRPO | 37.5%(최고) | — (기준) |
| subgoal (leaf/cascade) | 37.5% 동률 | 도달성 안 늘음 |
| **harvest** (실패롤아웃 닫힌 subgoal RFT) | 37.5% 동률 | "닫기만 강화, 도달 그대로" |
| gold 주입 6종 (LUFFY·KL-LUFFY·backward·revcurr·DAPG·RFT-gold) | 전멸 | covariate-shift (gold state가 배포분포 밖) |
| PPO | 실패 | critic 학습 실패(explained_var≈0, 희소보상) |
| SRFT (단일단계 융합) | 32.5%(w6) | BFS·w6 기준, classical 환산 시 ~37%대 예상 |
| invertible 재귀분해 | 사망(0/34) | 분해 후보가 탐색 안 도움 |

**결론: 훈련-쪽 공간은 소진.** 1.3B 도달성 벽이 근본.

---

## 5. 다음 레버 (병목별)
| 몫 | 레버 | 상태 |
|---|---|---|
| **57~59% (진짜 어려움=capability)** | **큰 base(Qwen2.5-Coder-7B) 재학습** | **진행중** (파이프라인 검증 완료, 학습 대기) |
| 40~42% (도달했으나 놓침) | §2.5-특화 자동화(모델은 뼈대, leaf는 lra/nia/auto) | 미시도(sauto 일부 선행) |
| — | 부정 결과·진단 자체를 기여로 정리 | CEILING_ANALYSIS.md 완비 |

**포기/비추천**: reranker(2-agent, 실효 작음) · 추가 훈련변형(interleaved/flywheel, ~37% 수렴 예상) · invertible(사망).

---

## 6. 진행중 (2026-07-29)
- **#6 SFT→GRPO** (classical·w6·BW) 재측정 — ~35%, 마무리 중.
- **Qwen2.5-Coder-7B 전면 재학습** — rango 동일 레시피(bm25+tfidf, r64, on-the-fly 검색)에 base만 교체.
  - 토크나이저 drop-in 호환 확인(pad≠eos, add_eos 작동). transformers 4.46+ 버그 2건(`evaluation_strategy`, `Trainer(tokenizer=)`) 수정.
  - smoke(30step)→전체 QLoRA SFT(2-GPU) 자동 파이프라인 대기중.
  - 목표: 위 **57~59% capability 몫**을 큰 base가 실제로 미는지 검증.
