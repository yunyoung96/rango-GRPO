# Harvest 라운드 — s0 실패 롤아웃에서 닫힌 subgoal 재활용

작성 2026-07-26. 관련: [[sft-subgoal-grpo-naming]], `SUBGOAL_PAPER_ASSESSMENT.md`(§3-B self-harvest, §6 OSR), `scripts/harvest_subgoals.py`, `all_log/run_cascade_bigscale.sh`(HARVEST_ROUND 플래그).

---

## 1. 아이디어

cascade의 **s0(완전체) 롤아웃은 대부분 실패**(dead 61%)한다. 그러나 그 **실패한 시도 안에서도 모델이 중간 subgoal은 닫았을 수 있다**(예: `induction`→base case는 닫고 귀납은 실패). 그 **닫힌 subgoal을 추출(harvest)해 재활용**하면, 버려지던 dead 그룹에서 학습 신호를 건진다.

**왜 이론적으로 깨끗한가** (§3-B HER-for-provers / §6 OSR):
- harvest한 subgoal은 **모델 자신이 방문한 state**(gold seed 아님) + **자신이 생성한 tactic** + **Coq가 롤아웃 중 실제로 닫아준** 것.
- → **p_reach=1, covariate-shift 0** (§6 T1). gold-injection(LUFFY/backward)의 실패원인을 구조적으로 회피.
- = STaR/RFT/expert-iteration(Polu-Sutskever)의 "자기성공 강화" 계열, verifier로 확인된 성공만.

**흐름**: s0 학습 후 → harvest(닫힌 subgoal 추출) → 그걸 학습 → **s0 한 번 더**(재롤아웃+GRPO). = 라운드 추가(진짜 레버) + on-policy.

---

## 2. 구현 (플래그, 기본 OFF)

`run_cascade_bigscale.sh`에 **`HARVEST_ROUND`** 플래그 (기본 `0`=안 함):
```bash
HARVEST_ROUND=1 bash all_log/run_cascade_bigscale.sh   # 켜기
```

HARVEST_ROUND=1 일 때, s0 gtrain 후:
1. **harvest**: `harvest_subgoals.py --dead_only` → s0 실패 롤아웃의 **닫힌 subgoal 추출**(reward=1 트레이스).
2. **gradient update = RFT(`--sft`)**: harvested 트레이스가 **전부 reward=1** → GRPO는 all-solved=advantage 0(gradient 0) → **순수 MLE(--sft)로 학습**(init=s0 모델).
3. **s0 재롤아웃**(정책=harvest 모델, Qed 보상) → 4. **s0 GRPO** → 최종 = `rango-grpo-cascade-s0r2`.

서빙 alias(`cascade-harvest`, `cascade-s0r2`) 추가. FINAL은 s0r2 있으면 우선.

---

## 3. A vs B (학습 방식 선택)

harvest 데이터를 어떻게 쓰나:
- **A (RFT, --sft)**: 닫힌 트레이스를 **imitate**(MLE). 구현 완료. 항상 gradient, on-policy 안전, 넓지만 얕음(이미 하는 것 강화).
- **B (harvested subgoal *seed*에서 fresh 롤아웃 + GRPO)**: 그 subgoal state에 모델 놓고 **새로 생성**(mixed면 GRPO 신호). 탐색 있음, 좁지만 깊음. **seed-빌더 추가 구현 필요.**

**B의 관건**: harvest한 subgoal은 "이미 닫힌 것"이라, 재롤아웃하면 **다시 닫혀(all-solved) gradient 0**일 수 있음. B가 의미 있으려면 **"가끔만 닫히는(mixed)" seed**여야 함.

---

## 4. 재폐쇄 변동 조사 (B 유효성) — s0 롤아웃 실측

"닫힌 subgoal을 재롤아웃하면 all-solved(B무의미)냐 mixed(B유효)냐"를 s0 롤아웃 데이터로 조사.

**방법**: 각 subgoal-state(=`state_key`, 정확한 goal+가설)가 여러 attempt에 등장했을 때 닫힘이 갈리는지. (theorem 무시, 전역 state 키.)

**결과** (s0 롤아웃 ~285그룹):
| distinct subgoal-state | 비율 |
|---|---|
| **1회만 등장** (재폐쇄 변동 측정 불가 — 샘플 1개) | **89%** |
| ≥2회 등장 (측정 가능) | 10% |

≥2회 등장(측정 가능한 10%) 중:
| | 비율 |
|---|---|
| all-solved(모든 등장서 닫힘) → B gradient 0 | 38% |
| **mixed(일부만 닫힘)** → **B 신호 있음** | **19% (닫힌것 중 33%)** |
| dead(아무도 못 닫음, harvest 대상 아님) | 41% |

**해석**:
- **subgoal state가 theorem마다 고유**해서 89%가 1회만 등장 → 재폐쇄 변동을 **기존 데이터로 알 수 없음**.
- 측정 가능한 10%에선 **harvested 중 33%가 mixed** → B가 그만큼엔 신호를 냄. 하지만 **대표성 약함**(89%는 미지).
- → **B 유효성은 기존 롤아웃으로 판정 불가.** 확답하려면 **파일럿**: 닫힌 seed 샘플(수십 개)을 실제 재롤아웃해 mixed 비율 실측.

---

## 5. harvest 수확량 (실측)

s0 롤아웃 285그룹 → **닫힌 subgoal 1154개** (전부 dead 그룹 출신, 총 2513 step) → 151그룹 저장.
→ A(RFT) 학습 데이터로는 충분.

---

## 6. 권고

| 선택 | 언제 |
|---|---|
| **A (RFT)** | 빠르고 안전한 부스트. 1154 전부 활용, 재폐쇄 변동 무관, 항상 gradient. 구현 완료·기본 OFF. |
| **B (fresh 롤아웃+GRPO)** | 어려운 subgoal 실제 개선. 단 유효성 미지 → **먼저 파일럿**(seed 재롤아웃 mixed 실측). seed-빌더 필요. |
| **B + dynamic sampling** | B의 효율판(all-solved 그룹 스킵). 이론상 최적 B. |
| **하이브리드** | all-solved엔 A, mixed엔 B. 최적이나 복잡. |

**순서**: cascade 완주(s0 학습+평가) → **held-out 결과 먼저** 확인. 좋으면 harvest 불필요. 나쁘면 → **A로 붙이거나 B-파일럿**으로 결정.

---

## 7. 상태 (2026-07-26)

- cascade s0 롤아웃 완료(285그룹, mixed 30% — 원판 26%보다 좋음). **s0 학습 전 일시정지**(사용자 지정).
- harvest 구현 완료(A, 플래그 기본 OFF). 파일럿·B는 미구현.
- 다음: s0 학습 → rand200@600s g2w4 held-out 결과 보고 → harvest 여부 결정.
