# SFT를 강하게 할수록 held-out이 나빠진다 — sft-1/2/3 실험 (2026-08-07)

> **질문**: "SFT가 underfit이면 더 강하게 하면 되지 않나?" → **아니다. 강하게 할수록 held-out 증명이 나빠진다(overfit).**
> 데이터: 학습 gold = `tst1000tr5091_gold.jsonl`(4228 정리/38k step). held-out = probe100(학습에 없던 valid 정리, gold 커리큘럼과 0 겹침).
> 관련: [[../grpo_failure/MIXED_FAILURE_ANALYSIS_lr3e-4]] · [[../../../memory: coverage-not-wall-selection-reachability]]

## 세 버전의 세팅
| 버전 | lr | 유효배치 | epoch | shuffle | init |
|---|--|--:|--:|:--:|---|
| sft-1 | 1e-6 | 2 | 2 | ✗ | rango baseline(checkpoint-54500) |
| sft-2 | 1e-4 | 4 | 3 | ✗ | 〃 |
| sft-3 | 1e-4 | 4* | 5 | ✓ | 〃 |
*sft-3는 bs8(micro4) 목표였으나 48GB OOM으로 bs4(micro2)로 강등. 즉 sft-2 대비 실제 차이 = **셔플 ON + epoch 3→5**.

## ★ 결과 — 4지표 (일부)
| 모델 | loss(최종 epoch) | training exact-match(normalized, gold 300) | **probe proving(held-out /100)** | baseline 대비 순증 |
|---|--:|--:|--:|--:|
| baseline(rango) | — | 36.7% | 31 | — |
| sft-1 | 약함(lr1e-6) | 40.3% | 30 | ~0 |
| sft-2 | 0.12 | 40.7% | 28 | **−3** |
| sft-3 | **0.061** | **52.7%** | **24** | **−7** |
- probe 짝비교(vs baseline): sft-2 = gain4/loss7(−3), sft-3 = gain3/loss10(−7).
- held-out exact-match(4번째 지표)는 held-out gold 빌드 필요 → 미측정(probe로 결론 확정돼 생략).

## 완벽하게 단조로운 overfitting
```
학습 강도(fit):    sft-1  <  sft-2  <  sft-3      (loss 0.12→0.061, train exact 40→53%)
held-out proving:   30   >   28   >   24          (강할수록 나빠짐, 단조)
```
- **sft-3가 gold를 제일 잘 암기(train exact 52.7%, loss 0.061)했는데 held-out은 제일 나쁨(24, −7).**
- 즉 **gold 암기 ↑ = 일반 증명력 ↓** (catastrophic forgetting). rango baseline이 갖고 있던 넓은 능력을 강한 SFT가 깎는다.

## 세 가지 확정 발견
1. **셔플은 도움 안 됨** — sft-3(셔플O)가 sft-2(셔플X)보다 held-out 더 나쁨. no-shuffle이 overfit 원인이 아니었음(강도·epoch가 원인).
2. **epoch 많을수록 overfit 심함** — ep2<ep3<ep5 순으로 held-out 악화.
3. **벽 = SFT 품질 아님** — 더 강한 SFT는 **반생산적**. "SFT를 더 강하게" 방향은 죽음.

## loss vs 실전 지표의 괴리 (왜 loss만 보면 속나)
- loss(teacher-forced, gold prefix 보고 다음 토큰 확률)는 sft-3에서 크게 떨어짐(0.061) → "잘 배운 것처럼" 보임.
- 그러나 **자유생성 exact-match**는 40→53%로 오르지만 held-out **proving은 오히려 하락** → loss 개선이 실전으로 전이 안 됨(exposure bias + 암기).
- **교훈: SFT 품질은 loss가 아니라 held-out proving으로 봐야 한다.**

## 결론 & 다음 방향
- **SFT 강화는 접는다.** underfit이었지만 강화하면 overfit으로 바로 넘어가고, 그 사이 "일반화되는 sweet spot"이 held-out proving을 baseline 위로 못 올림(sft-1이 baseline과 동급 30이 최선).
- 진짜 벽은 **선택/도달성 일반화 + retrieval 품질** ([[../grpo_failure/TYPE_LEARNING_RESEARCH]] 방향 A: 타입 hard-neg contrastive retriever). SFT 본체를 더 학습시키는 게 아니라 **입력(후보)을 타입으로 좁혀주는 것**이 남은 레버.

## 재현
- 학습: `all_log/sft2_train.sh`(sft-2), `all_log/sft3_train.sh`(sft-3). DDP 2-GPU, `--sft --kl_beta 0.0`.
- 평가: `scripts/eval_sft_gold.py`(training exact-match), `EXEC_ADAPTER=<adapter> scripts/run_all.py --alias rango-grpo --idx-file data/tst1000tr5091_probe100_idx.txt --timeout 120`(probe proving).
- 모델: `models/rango-tst1000tr5091-sft-2`, `models/rango-tst1000tr5091-sft_lr1e-4_bs4_ep5_shuf`.

관련: [[../grpo_failure/TYPE_LEARNING_RESEARCH]] · [[../grpo_failure/MIXED_FAILURE_ANALYSIS_lr3e-4]] · [[../../../memory: sft-iteration-naming]]
