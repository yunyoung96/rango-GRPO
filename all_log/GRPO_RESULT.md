# GRPO 실학습 결과 (DeepSeek-Prover-V1.5 방식) — 2026-07-11 12:28 UTC

## 파이프라인 (실제 구동 완료)
1. rollout 수집: train(start=200) 39정리, 정리당 8시도 → 신호 그룹 11개(성공·실패 혼합).
2. GRPO 학습: 그룹상대 advantage + 클립목적 −β·KL, 2 epoch, 208 step/epoch, KL~0.01(안정).
   → models/rango-grpo/adapter (LoRA, base=deepseek-coder-1.3b-instruct).
3. 평가: eval(0-40), straight-line 탐색 + GRPO adapter.  결과 디렉토리: all_results/20260711-072435/

## 결과 @40 (baseline = published Rango 12/40)
- rango-grpo: **16/40 (+4)**, unique [2,10,11,55], **regress 0**.

## 비교 (@40)
| 방법 | 성공 | vs base | unique | regress |
|---|---|---|---|---|
| baseline(Rango) | 12 | — | — | — |
| BFS α=1.0(최고 탐색) | 16 | +4 | 5 | 1 |
| portfolio | 15 | +3 | 3 | 0 |
| **GRPO(RL)** | **16** | **+4** | 4 | **0** |

## 결론
- GRPO는 단순 straight-line 탐색 + RL 학습된 정책만으로 최고 탐색법과 동일 성능, regress 0(더 깨끗).
- 탐색 정교화(RMaxTS MCTS/reward/merge)는 40-라운드에서 전부 무효였으나 모델 학습은 즉시 +4.
- 극소량 학습(39그룹/2epoch)으로도 baseline 완전 지배 → "진짜 레버는 모델 학습" 가설 실증.

## BFS-full (expert-iter + DPO) 결과 @40
- 13/40 (+1 vs baseline 12), unique [2,11,55], regress [5,41].
- untrained BFS-Prover@40(13)와 동수 — DPO 학습 약함(35쌍,acc0.58) → 순증 없이 이동만.
- 대조: GRPO는 +4 clean. DPO는 선호쌍 부족으로 효과 미미(정직한 결과).
