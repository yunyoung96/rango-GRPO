# pass@K 진단 + 롤아웃/결과 분석

> 2026-07-18. "왜 fix 말고는 아무것도 우리 rango·fix를 못 넘나"를 롤아웃 신호·union·pass@K 로 진단.
> 비교기준: 우리 rango @20=11 @40=15 @180=61 | fix @20=13 @40=19 @180=66. published 비교 안 함.

---

## 1. 결정적 결과 — 모든 기법이 fix의 부분집합 (union +0)

@40 기준, fix 가 푸는 19개에 대해 각 기법이 **새로 푸는 정리(union 증가분)**:

| 기법 | solves | fix가 못푸는데 새로 푼 것 |
|---|---|---|
| vine | 16 | **0** |
| prm | 16 | **0** |
| retry | 15 | **0** |
| revcurr | 15 | **0** |
| luffy-kl | 14 | **0** |
| **fix ∪ 전부** | **19** | **+0** |

→ **RL 파인튜닝이 능력을 확장하지 못하고 fix 범위 안에서 재배치만 함.** fix 가 못 푸는 정리는 어떤 기법도 못 건드림.

## 2. 롤아웃 신호 분석 — 왜 그런가

각 롤아웃의 그룹 신호 분포(mixed=일부성공/일부실패=학습신호 있음):

| 롤아웃 | mixed(신호) | dead-fail | 해석 |
|---|---|---|---|
| luffy(gold주입) | **86%** | 8% | 신호는 넘치는데 **회귀** → 문제는 신호量 아닌 **방향**(covariate shift) |
| adaptprefix | 54% (선택밴드 ~100%) | 42% | pass-rate 조준 작동 — 정보성 최상 |
| revcurr | 43% (r4·r5 55~59% 최고) | 38% | sweet-spot=중간 remaining, r7·r8은 25~30%(너무 어려움) |
| vine | 18% | 79% | s0 backbone 대부분 실패 → 신호 희박 |

**핵심:** 신호 있는 mixed 그룹은 전부 **fix 가 이미 푸는 경계선 정리**. fix 가 못 푸는 정리는 near-goal 커리큘럼에서조차 all-fail(그래디언트 0) → 절대 개선 안 됨. gold 는 그 fail 정리에 신호를 주지만(86%) 방향이 틀려 회귀.

## 3. pass@K 진단 — "천장이 능력이냐 디코딩이냐"

fix 정책으로 첫 40정리, 정리당 8개 완증명 시도(온도 1.0 샘플) → 하나라도 COMPLETE 면 solved@K.
- **pass@K ≫ pass@1** 이면 → 능력은 있는데 **디코딩(greedy)이 병목** → 추론 시 샘플+검증으로 solves 추가 가능
- **pass@K ≈ pass@1(낮음)** 이면 → 진짜 **능력 천장** → 데이터/모델 규모로 가야 함

### 결과 (pass@K, fix, 첫 40정리)

<!-- PASSK_RESULT -->
| K | solved (첫 40정리) |
|---|---|
| pass@1 | 4/40 |
| pass@2 | 6/40 |
| pass@3 | 7/40 |
| pass@4 | 7/40 |
| pass@5 | 7/40 |
| pass@6 | 8/40 |
| pass@7 | 8/40 |
| pass@8 | 9/40 |

> ⚠️ **정정(2026-07-19, 코드감사):** "fix @40=19"는 **greedy pass@1이 아니다.** searcher(StraightLineSearcher)의 생성이
> `do_sample=True, temperature=1.0`(model_wrapper.py:177-178)이라 **온도 1.0 다중시도**다 → 19는 사실상 pass@(timeout 내 시도수, ≫8).
> 따라서 "19 ≫ pass@8=9"는 **greedy가 샘플보다 낫다는 근거가 아니라, 그냥 시도수(search budget) 차이**일 뿐이다.
> **⇒ 이 데이터로는 "능력 천장 vs 디코딩 병목"을 판정할 수 없다(confound).** 제대로 재려면:
> (a) **진짜 greedy**(do_sample=False)로 pass@1, (b) **동일 budget** coverage@k, (c) temp 0.6~0.8 sweep. 셋 다 미측정.
> 앞서 이 문서/보고에서 내린 "greedy 19 ≫ 샘플 → 능력 천장" 결론은 **철회**한다.

## 4. 대응 — 실행 중/예정 구현

- **RFT / expert-iteration (SFT)** ⭐ 추천 #2 — 성공 궤적을 순수 MLE 지도학습(advantage/clip 없음).
  - `rft-gold`: luffy.jsonl 의 gold 궤적 SFT → **fail set 직접 겨냥**. fix anchor(KL). LUFFY(RL주입)와 달리 gentle MLE.
  - `rft-self`: revcurr.jsonl 자기 성공만 SFT → **on-policy = covariate shift 없음**(STaR/RFT). 단 ceiling 한계.
- **추론 시 pass@K 활용**: pass@K 가 높으면, 학습 없이 **best-of-N 샘플+Coq검증**으로 solves 추가(추후).
- (큐) anneal-to-s0 / luffy-ch / dapo / bigscale — 단 union +0 예측이 강함.

## 5. 잠정 결론
RL 계열은 **fix 천장에 막혀** union 을 못 늘림. 돌파구는 (a) fail set 에 직접 신호를 넣는 **gold-SFT(rft-gold)**, (b) 능력이 이미 있으면 **추론 샘플링(pass@K)**, (c) 데이터/모델 **규모**. pass@K 결과가 (b) vs (a·c) 방향을 가른다.
