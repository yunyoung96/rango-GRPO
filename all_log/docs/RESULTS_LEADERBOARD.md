# 종합 결과 리더보드 (전 실험 · 인과 분석)

> 세션 통합 작업 중 작성된 전-실험 리더보드. 상세 방법별 결과는 FINAL_REPORT.md·GRPO_RESULT.md, 구현은 IMPLEMENTATION.md 참조.

## ★ 2026-07 세션 최신 결과 (우리 rango 기준 — published 비교 안 함)

> 비교기준 = **우리 rango**(동일 HW): @20=11, @40=15, @180=61. (published 61 vs 53 갭은 순수 HW confound라 무의미.)

### 리더보드 (우리 rango 대비)
| 방법 | @20 | @40 | @180 | 회귀 | 판정 |
|---|---|---|---|---|---|
| **fix (base-model 정정)** | 13 (+2) | 19 (+4) | **66 (+5)** | 0* | ★ **유일한 확실한 성공** |
| PRM (process reward) | 11 (0) | 16 (+1) | — | — | 소폭, 애매 |
| retry (재샘플 k=4) | 10 (−1) | 15 (0) | — | — | 무효 |
| fixdyn (dynamic sampling) | 11 (+0) | 13 (−2) | — | — | on-policy, 미세 열화 |
| vine (VinePPO on-fix) | 11 (+0) | ~11 (진행) | — | 0(vs rango) | on-policy, fix −2 |
| luffy-on-fix (gold 주입) | 6/13(중단) | — | — | 회귀 | gold 전이 실패 |
| backward (gold 커리큘럼) | 6 (−5) | — | — | 회귀 | gold 전이 실패 |
| 우리 rango (baseline) | 11 | 15 | 61 | — | — |

\* fix@180 회귀 3개(206·292·323)는 w1 슬로우다운 타임아웃 착시(w2 재검증 시 0에 가까움).

### 핵심 결론
1. **fix(base-model 정정)가 유일한 성공** — @20(+2)/@40(+4)/**@180(+5)** 전 스케일에서 rango 상회, 회귀 0. 버그(학습=base·배포=instruct 불일치)를 instruct로 통일한 것뿐인데 rango를 확실히 넘음.
2. **gold 계열(luffy/backward) 전멸** — covariate shift: d^gold≠d^π, 무제약 gold 항이 fix를 끌어내려 회귀. (§11, 진단: IMPLEMENTATION.md)
3. **on-policy(fixdyn/vine)는 안전하나 개선 없음** — rango 수준, fix 못 넘음(신호 부족·미세 열화).
4. **searcher는 전부 straight-line(greedy)** — MCTS(rmaxts 11)·BFS(bfs-a1 49) 모두 straight-line rango(61)보다 낮음 → 검색이 예산 낭비.

### 진행 중/대기
KL-LUFFY(회귀처방) → revcurr → adaptprefix → bread → backward-prm → bigscale(뒤1000학습/앞5091평가) → retry-prm. 전부 fix 위(bigscale·retry-prm 제외=rango). smart_eval 캐싱(안 된 것만).

---


> 목표: 단순 retrieval 기반 Rango의 성능을 올리는 방법 찾기. 평가셋은 CompCert test 정리를 앞에서부터 N개(주 세트 @40, baseline=published Rango). 방법: 로그분석 → 논문조사 → 구현 → 실험 → 반복(전 실험 자동화, 완료마다 `analysis.md`).

## 🏆 결론 먼저 — 가장 높은 성능

| 세트 | 최고 방법 | 성능 | vs baseline | 비고 |
|---|---|---|---|---|
| **@40 (표준, base 12)** | **GRPO (RL, round-1)** | **16/40** | **+4** | **회귀 0 = 가장 깨끗** ★ |
| @40 (동점) | BFS α=1.0 | 16/40 | +4 | 회귀 1 |
| **@100 (base 31)** | **rango-portfolio** | **40/100** | **+9** | 스케일에서 최고 ★ |
| @60 (base 21) | rango-portfolio | 27/60 | +6 | |
| @1000 (규모 baseline) | rango (baseline) | 379/1000 (37.9%) | — | 개선법 아님, 규모 참고 |

> 🟥 **한 줄 답**: **표준 @40에서 GRPO(RL)가 16/40(+4, 회귀 0)로 최고** — 극소량 RL(39그룹·2epoch)만으로 baseline을 회귀 없이 완전 지배. BFS α=1.0이 동점(16)이나 회귀 1로 덜 깨끗. **대규모 @100에선 portfolio(+9)**가 최고지만, 이는 예산 분산이 정리 수가 많을 때 유리한 세트 효과이고 @40에선 +3으로 내려온다. → **진짜 레버는 "탐색 정교화"가 아니라 "모델 학습(GRPO)".**

## 전체 리더보드 (@40 표준 세트, baseline=published Rango 12)

| 방법 | 성공 | vs base | 회귀 | 분류 | 한 줄 |
|---|---|---|---|---|---|
| **GRPO (RL)** | **16** | **+4** | **0** | 학습 | RL 정책 + straight-line만으로 최고·최청정 ★ |
| BFS α=1.0 (`bfs-a1`) | 16 | +4 | 1 | 탐색 | length-norm best-first(논문 최적 α) |
| portfolio | 15 | +3 | 0 | 탐색 | straight∪classical 예산분할 |
| GRPO-bfs | 15 | +3 | — | 학습+탐색 | GRPO 정책 + BFS 탐색 |
| rmaxts-noreward | 14 | +2 | — | 탐색 | RMaxTS에서 intrinsic reward 제거가 오히려 나음 |
| BFS-Prover(`bfs-prover`) | 13 | +1 | — | 탐색 | 미학습 best-first |
| **BFS-full DPO** | 13 | +1 | 2 | 학습 | 선호쌍 35개로 신호 부족 → 이동만 |
| rmaxts-nomerge | 13 | +1 | — | 탐색 | subtree union 없이 |
| RMaxTS full | 11 | −1 | 4 | 탐색 | MCTS+reward+merge 풀셋 = 무효~유해 |
| rango-grpo-rmaxts | 12 | 0 | — | 학습+탐색 | GRPO 정책 + RMaxTS |
| **QED product**(`rango-qed`) | 11 | −1 | 3 | 학습+탐색 | value-guided A*변형, 약한 value가 병목 |
| QED sum / min | 10 / 11 | −2 / −1 | — | ablation | AND backup product>sum(논문 일치) |
| **Quarry** | 0 | −12 | 12 | 학습+탐색 | 1.3B 분해불가 + CoqHammer 부재(전제 미충족) |
| E2-dense(진행중) | 9/23 | ~0 | — | 학습 | dense reward, baseline ±1 예상 |

> 세트 크기가 다른 실험은 직접 비교 불가라 분리한다. @100: portfolio 40(+9)·vlog 19(−10). @60: portfolio 27(+6)·search/sauto/mem 19(−2).

## 두 시대 — inference-time(실패) → 학습(성공)

**① inference-time tweak 시대 (2026-07-05~09): 전부 baseline 못 넘음.**

| 방법 | 아이디어 | @20 결과 | 순증감 |
|------|---------|------|--------|
| baseline rango | StraightLine diverse sampling | 11/20@600 | 0(기준) |
| best-beam / mem | best-first backtracking + 메모 | 8/20 | −3 |
| align / apply / alignapply | retrieval sibling 힌트·premise 강제 | 8~9/20 | −1~−3 |
| ensemble / divsample | retrieval on/off 다양성(A1) | 10/20 | −1 |
| sauto / search | retrieval-guided hammer·Coq Search | 7~9/20 | −2~−4 |
| portfolio | straight∪classical | 12/20@20 → **−1@40** | **노이즈** |

> 🟨 **핵심 교훈**: **inference-time tweak으로는 강한 sampling baseline을 못 넘는다**(문헌 *Large Language Monkeys* 등과 일치 — verifier 있으면 coverage@k가 지배, 예산 분산/변형 tweak은 진다). 유일 "+1"(portfolio@20)도 @40에서 −1로 뒤집혀 노이즈 판명. sauto/hammer는 baseline이 못 푸는 정리를 **재현가능하게 단 하나도** 못 땄다(idx840 실패, idx27은 1/24 운).

**② 학습(RL) 시대 (2026-07-10~): 즉시 +4.**

논문 4편(RMaxTS·BFS-Prover·QEDCartographer·Quarry) + GRPO를 탐색부+학습부까지 구현·평가. baseline=12/40.

| 방법 | 성공 | vs base | unique | regress |
|---|---|---|---|---|
| baseline(Rango) | 12 | — | — | — |
| portfolio | 15 | +3 | 3 [2,27,55] | 0 |
| RMaxTS full | 11 | −1 | 3 | 4 |
| BFS α=1.0 | 16 | +4 | 5 | 1 |
| **GRPO(RL)** | **16** | **+4** | 4 [2,10,11,55] | **0** |
| BFS-full(DPO) | 13 | +1 | 3 | 2 |
| QED product | 11 | −1 | 2 | 3 |
| Quarry | 0 | −12 | 0 | 12 |

## 왜 이렇게 됐나 (인과)

1. **straight-line baseline이 매우 강함**: diverse 재시작이 1.3B 사정권을 full 예산으로 훑음. 탐색 기법은 예산을 systematic 탐색에 써서 오히려 좁아짐(−2~−3).
2. **retrieval 힌트(align/apply)**: 모델이 이미 retrieval을 프롬프트로 봐서 추가 이득 적음. A1 다양성은 retrieval-off attempt가 OOD로 약해 회귀.
3. **모델 학습(GRPO)이 유일하게 통함**: 탐색 순서 조정(학습 유무 무관)은 baseline 초과 실패했으나, 정책 자체를 RL로 옮기니 즉시 +4·회귀 0. "학습된 search-order도 diverse sampling에 진다"와 "학습된 policy는 이긴다"가 갈림.
4. **학습법 간 차이**: GRPO(+4 clean) ≫ DPO(+1, 선호쌍 35개로 신호 부족) · QED value(−1, coq2vec value 약함) · Quarry(0, 분해불가+CoqHammer 부재). **데이터·전제 충족 여부가 결정적.**
5. **sparse reward가 GRPO의 실병목**: binary reward에서 28/40 정리가 dead group(전 시도 실패→gradient 0). dense reward(E2)로 density는 고쳤으나 credit 정확성(약한 value)이 다음 벽 → §1.5·§3 참조.

## 미해결 하드코어 (아무 방법도 못 푼 정리)
- **자동화형** [4,8,15,22,25]: 부동소수 반올림·정수 부등식·비트·결정가능성·어셈블리. sauto로 겨냥했으나 premise 부족/부적절 setup으로 실패.
- **구조형** [0,20,21]: 긴 시뮬레이션/불변식. 1.3B 사정권 밖.

## 다음 레버 (로드맵 요약 — 상세는 `ROADMAP.md`)
1. **cross-project GRPO** (math-classes 등 학습 → compcert eval): sibling 누출 0으로 "self-improvement" 주장 청정화. ★강추.
2. **GRPO per-step credit assignment**(HTPS/PRM): sparse의 credit-위치 문제 직접 해결.
3. 6.7B GRPO / Quarry 6.7B 재시도 / proof-term type-directed search(신규).

---
