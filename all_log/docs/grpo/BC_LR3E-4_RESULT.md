# batch-chunk GRPO 결과 — lr=3e-4 실험 (보존 요약, 2026-08-06)

> **이 문서 = lr 3e-4→3e-5 실험을 lr=1e-3로 바꾸기 전 "지금 한 것까지" 저장한 요약.**
> 실험태그 `tst1000tr5091_bc_lr3e-4_kl0.015_B100_G8`. 상세 실패분석은 [[../grpo_failure/MIXED_FAILURE_ANALYSIS_lr3e-4]].

## 세팅
- SFT→bottom-up-subgoal GRPO, B=100·G=8·KL=0.015·clip=0.2, full_batch_update(batch당 1 update), **cosine lr 3e-4→3e-5**, ref_snapshot(STALL_THRESH=4, 10 batch마다).
- 데이터: train pool 4560 / valid 500 / probe 100(held-out, valid⊂) / test 1000. 단일 GPU1.
- 진행: **epoch 0, batch b000~b039 (40 batch)** 까지 돌리고 중단(lr 전환).

## ★ 핵심 결과 — probe 정체 (negative)
| gt | probe/100 | 직전 대비 |
|--:|--:|--:|
| baseline(SFT) | 29 | — |
| 9 | 29 | +0 |
| 19 | 30 | +1 |
| 29 | 30 | +0 |
| 39 | 30 | +0 |
- **40 batch 학습 → probe 29→30 (사실상 flat).** +1은 노이즈(±4.5, n=100 이항) 안. **held-out 성능 못 올림 = negative result.**

## KL·ratio (건강하나 비생산적)
- KL: 비영 batch 0.011~0.033, 평균 0.019. ref_snapshot 사이클(10 batch)마다 리셋되며 **사이클 평균 0.0227→0.0197→0.0177→0.0159 감소**.
- max_ρ: 4~56(소수 outlier), **clip% 7~13%로 안정** → 단일 GPU라 폭발 없음([[../../../memory: ddp-grpo-ratio-explode]]).
- 해석: **정책은 매 batch 움직이는데(KL>0) probe는 정체** = 이동이 생산적이지 않음.

## mixed/dead (신호 희소)
- 전체 3,288 group: **mixed 28.4% / all-solved 8.2% / dead 63.5%.** 학습에 쓰는 mixed가 batch당 17~28개뿐, 나머지 72%는 advantage=0.
- batch 진행돼도 비율 거의 불변(mixed 소폭 감소) → 풀 수 있는 문제 구성이 안 바뀜.

## 왜 정체했나 (인과)
- rollout 품질(apply INVALID율 62→65% 불변)이 안 변함 → held-out probe 불변이 당연.
- 병목 = **타입 정합 lemma 선택** (상세 [[../grpo_failure/MIXED_FAILURE_ANALYSIS_lr3e-4]] · [[../grpo_failure/TYPE_LEARNING_RESEARCH]]).

## 보존물 (삭제 안 함, [[../../../memory: preserve-all-rollouts]])
- 로그: `all_log/tst1000tr5091_bc_lr3e-4_kl0.015_B100_G8.log`
- 롤아웃 40개: `data/grpo_rollouts/tst1000tr5091_bc_lr3e-4_kl0.015_B100_G8_ep0_b*_roll.jsonl.gz`
- harvest 백업: `data/grpo_rollouts/harvest_tst1000tr5091_lr3e-4_kl0.015_B100_G8/`
- 모델: `models/rango-tst1000tr5091-bc_lr3e-4_kl0.015_B100_G8/`
- 결과: `all_results/tst1000tr5091_bc_lr3e-4_kl0.015_B100_G8_probe_*`

## 다음 (이 결과 위에서 결정)
- **lr=1e-3 화끈 테스트 시작**(2026-08-06 21:01, `tst1000tr5091_bc_lr1e-3_kl0.015_B100_G8`). 가설: lr↑로 KL 커지나 probe는 아마 정체(near-peak lr에서도 flat했음) — 확인용.
- 근본 처방은 lr이 아니라 **retriever(방향A)/process reward(방향B)** — [[../grpo_failure/TYPE_LEARNING_RESEARCH]].
