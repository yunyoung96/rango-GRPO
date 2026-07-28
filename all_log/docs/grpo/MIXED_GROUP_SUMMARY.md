# MIXED GROUP % 완전체 — 전 GRPO 실험 실측

작성 2026-07-27. 롤아웃 jsonl **28개 전수 실측**(`data/grpo_rollouts/*.jsonl`). 관련: `SUBGOAL_PAPER_ASSESSMENT.md`(§3-C·§9.2), `GRPO_ROLLOUT_ANALYSIS.md`, `GOLD_PROOF_METHODS.md`, `IDEAS.md`.

## 정의 & 주의

- **그룹** = 한 seed에서 뽑은 G개 롤아웃. **all-solved**=G개 다 성공 · **dead**=다 실패 · **mixed**=일부만.
- **all-solved·dead는 advantage=0 → gradient 0(낭비). mixed만 학습신호.**
- ⚠ **reward 정의가 실험마다 다름**: subgoal 스테이지(s1/s2/s3)=per-subgoal(goal<seed) · 완전체(s0)·plain=Qed. **RFT 데이터**(gold-SFT/harvest)=설계상 전부 reward=1. → 여기 mixed%는 "그 실험에서 **GRPO가 실제로 본 신호량**".

## 마스터 표 (family별, 실측)

| family | 실험 | 그룹 | all-solved | **mixed(신호)** | dead | 낭비(all+dead) |
|---|---|---|---|---|---|---|
| **plain GRPO** | GRPO 초기(rollouts) | 76 | 1% | 19% | 78% | 79% |
| plain GRPO | GRPO round1-fixed | 39 | 2% | 28% | 69% | 71% |
| plain GRPO | GRPO bigscale | 133 | 0% | 25% | 73% | 74% |
| plain GRPO | **GRPO bigscale2(300)** | 300 | 0% | **22%** | 77% | 78% |
| **SFT→GRPO** | **SFT→GRPO bigscale2(300)** | 293 | 0% | **25%** | 73% | 75% |
| 변형 | GRPO +retry | 39 | 5% | 38% | 56% | 61% |
| 변형 | VinePPO(MC value) | 39 | 2% | 17% | 79% | 82% |
| 변형 | dense reward(E2) | 40 | 2% | 27% | 70% | 72% |
| 변형 | curriculum(E3) | 37 | 0% | 10% | 89% | 89% |
| 변형 | G=16(E4) | 7 | 0% | 14% | 85% | 85% |
| 변형 | pass@k | 40 | 0% | 22% | 77% | 77% |
| **gold 주입** | **LUFFY** | 37 | 5% | **86%** | 8% | 13% |
| gold 주입 | backward curriculum | 77 | 9% | 42% | 48% | 57% |
| gold 주입 | reverse curriculum | 167 | 18% | 42% | 38% | 56% |
| gold 주입 | **gold-SFT bs2** (RFT) | 254 | **100%** | 0% | 0% | 100% |
| gold 주입 | adaptive prefix | 25 | 4% | 52% | 44% | 48% |
| **leaf subgoal 초기** | leaf s1(r4) | 40 | 12% | 52% | 35% | 47% |
| leaf subgoal 초기 | leaf s2(r6) | 40 | 2% | 47% | 50% | 52% |
| leaf subgoal 초기 | leaf s3(r8) | 40 | 7% | 30% | 62% | 69% |
| **leaf subgoal 원판(300)** | leaf-bs2 s1(leaf) | 324 | 41% | 36% | 21% | 63% |
| leaf subgoal 원판(300) | leaf-bs2 s2 | 17 | 17% | 35% | 47% | 64% |
| leaf subgoal 원판(300) | leaf-bs2 s3 | 3 | 0% | 0% | 100% | 100% |
| leaf subgoal 원판(300) | **leaf-bs2 s0(완전체)** | 297 | 7% | **26%** | 65% | 73% |
| **cascade(300)** | cascade s1 | 307 | 38% | 42% | 18% | 56% |
| cascade(300) | cascade s2 | 17 | 11% | 41% | 47% | 58% |
| cascade(300) | cascade s3 | 3 | 0% | 0% | 100% | 100% |
| cascade(300) | **cascade s0(완전체)** | 285 | 8% | **30%** | 61% | 69% |
| **harvest** | harvest RFT 데이터 (RFT) | 151 | **100%** | 0% | 0% | 100% |
| harvest | **harvest s0r2(완전체)** | 290 | 7% | **31%** | 60% | 67% |

## 핵심 통찰

1. **mixed%(신호량)와 held-out은 상관이 없다 — 이 프로젝트의 핵심 역설.**
   - gold 주입은 mixed **42~86%**까지 치솟지만 **test 회귀**(covariate shift). plain/SFT→GRPO는 mixed **22~25%**인데 **test 최고**. → 신호의 **양이 아니라 방향/분포**가 중요.
2. **plain GRPO ≈ SFT→GRPO** (mixed 22% vs 25%, dead 77% vs 73%) — 롤아웃 신호 거의 동일. held-out 격차(33.5→37.5%)도 작음.
3. **RFT 데이터는 100% all-solved(0 mixed)** — gold-SFT·harvest는 전부 reward=1 → GRPO advantage=0 → **반드시 `--sft`(RFT)로 학습.** GRPO 돌리면 gradient 0.
4. **subgoal 분해는 조각(s1) mixed를 36~42%로 올리지만, 완전체(s0)는 26~31%로 도로 낮고 dead 60%+.** 조각은 살려도 완전체는 여전히 죽음 → `SUBGOAL_PAPER_ASSESSMENT.md` §10 도달성 진단.
5. **harvest s0r2 mixed 31% ≈ cascade s0 30%** — harvest RFT가 완전체 롤아웃 신호를 거의 못 바꿈(닫기만 강화, 도달 그대로).
6. gold mixed 순위: LUFFY 86% > adaptprefix 52% > backward/revcurr 42%. dead 부활 효과는 크나 전부 전이 실패.

## held-out(rand200 w2)과의 대조 (완전체 s0 기준, 아는 값만)

| 실험 | 완전체 mixed% | held-out pass |
|---|---|---|
| plain GRPO | 22% | ~baseline(33.5%) |
| SFT→GRPO | 25% | **37.5%** (최고) |
| leaf-subgoal | 26% | 37.0% |
| cascade-s0r2(harvest) | 31% | **37.5%** (w2 공정, p90 360s=오염없음) |

**★ 오염 확정(2026-07-27)**: cascade의 g2w4 33.5%(p90 477s)는 **측정 오염**. 공정 w2로 재측정하니 **harvest = 37.5%(=SFT→GRPO 동률), p90 360s(부풀림 없음)**. → subgoal 계열은 **회귀 아님, 단 SFT→GRPO 못 넘고 동률**. 모든 방법 ~37.5% 수렴.

→ **완전체 mixed%가 오를수록 held-out이 오히려 안 오름(무관/역행).** mixed를 늘리는 게 목표가 아니라, **올바른 방향의 신호**(on-policy·도달가능)를 늘려야 함. IDEAS의 dense보상·EI·검색이 이 방향.
