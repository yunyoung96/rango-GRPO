# opener-tac — tactic-단위 retrieval opener (신규 접근, 2026-08-01)

이전 opener(whole-opening, goal만)의 한계를 넘으려는 **3세대 opener**. 결론부터: **여전히 parity(닫기 벽).**

## 무엇이 새로운가 (이전 opener 대비)
| | opener-7b (1세대) | opener-sub (2세대) | **opener-tac (신규)** |
|---|---|---|---|
| 생성 단위 | whole-opening 한 번에 | whole-opening | **tactic 하나씩** |
| 정지 | — | — | **"No More Decomposition"(NMD)** |
| 입력 | goal만 | goal만 | **goal + 후보 + lemma retrieval + proof retrieval** |
| target | 모든 opening tactic | 정리+subgoal opening | **structural 분해만**(intros/unfold/simpl 제외) |
| 비분해 정리 | — | — | **첫 state서 바로 NMD** |

핵심 동기: 이전 opener는 destruct의 **compound 인자**(`destruct (Rle_or_lt 0 x)`)를 못 맞춤(종류 73%/인자 52%). → retrieval+후보를 입력에 넣어 인자를 맞히게.

## 코드
- 데이터: `scripts/build_opener_tac_data.py` → `data/grpo_rollouts/opener_tac.jsonl` (359예시 = structural분해 125 + NMD 234). structural(destruct/induction/inv/case/inversion)만 target, intros/unfold/simpl은 passthrough(executor 몫).
- SFT: `scripts/train_opener_tac.py`. Qwen2.5-Coder-7B LoRA(r16/α32), **epoch 5, lr 1e-4, max_len 3072, gradient checkpointing**(48GB OOM 방지 → 23GB). loss 0.45→0.076.
- 통합(tac_mode): `planner_client.py`(_build_tac_input, NMD 파싱), `planner_server.py`(PLANNER_TAC=1, premises/proofs 수신), `grpo_rollout.py`(retrieval 전달, `__NMD__` 받으면 그 attempt는 opener 중단 → executor만).
- 파이프라인: `all_log/opener_tac_pipeline.sh` (Stage1 SFT → Stage2 롤아웃 → Stage3 GRPO). **GPU1 전용**(외부유저 회피), 여유 대기+재시도.
- 최종 모델: `models/opener-7b-tac`(opener), `models/rango-opener-tac-grpo`(executor GRPO).

## 입력 프롬프트 (예)
```
GOAL:
  forall x : R, F x -> succ (pred x) = x
CANDIDATE DECOMPOSITIONS:
- destruct (Rle_or_lt 0 x).
- destruct (Rlt_le_dec 0 x).
- induction x. ...
RELEVANT LEMMAS:   (TF-IDF premise 30개)
- Theorem pred_opp : ...
RELEVANT PROOFS:   (BM25 proof 4개, 축약)
- Lemma ... | intros ...
→ TARGET: destruct (Rle_or_lt 0 x) as [[Hx|Hx]|Hx].   (또는 "No More Decomposition")
```

## 검증: tac_mode 작동 O
- opener가 **compound 인자를 정확히** 생성: `destruct (Rle_or_lt 0 x) as [[Hx|Hx]|Hx].` ← 이전에 못 맞추던 것.
- **NMD 절제**: opener_step 전체의 9%뿐(과분해 안 함). opener-every(과분해로 mixed 붕괴 10%)와 대조.
- opener 발동: attempt의 31%(hedge+NMD로 절제), opener tactic valid율 53%, compound destruct 110개 생성.

## Stage2 롤아웃 결과 (train 100 → 97그룹, executor=subgoal모델)
| 방법 | mixed | attempt 성공 | 정리≥1 |
|---|---|---|---|
| plain SFT | 27% | 18.9% | 34% |
| opener-once | 30% | 17.4% | 33% |
| combo(subgoal+opener-once) | 27% | 17.0% | 32% |
| **opener-tac (신규)** | **28%** | 16.8% | (all 4/mixed 27/dead 66) |

→ **여전히 parity.** retrieval+compound인자+NMD로 opener 품질을 최대치로 올렸는데도 mixed 28%.

## Stage3 GRPO
- init=subgoal모델, 97그룹으로 GRPO(epoch2). metrics: mixed_frac 0.278, dead_frac 0.68, entropy 0.11, avg_group_std 0.116. → `rango-opener-tac-grpo`.

## rand200 test (opener 없이, executor 단독) — 확정
| 모델 | rand200@300s w8 |
|---|---|
| **opener-tac 최종**(SFT-opener→롤아웃→GRPO) | **62/200 = 31.0%** |
| **subgoal 모델**(init 대조, 동일조건) | **61/200 = 30.5%** |
| 차이 | **+0.5%p (동급, 노이즈)** |
- ※ 31%는 회귀 아님 — **@300s** 시간예산 때문(기존 37%는 @600s). **동일조건 대조(subgoal 30.5%)로 parity 확정.**
- (참고: plain SFT→GRPO 37.5% / leaf-subgoal 37.0% 는 @600s.)

## 결론 (확정)
- **opener 4연속(once / combo / opener-tac) 모두 parity.** 이번엔 opener가 **인자까지 정확히** 냈는데도 mixed 28%·test 31.0%(vs subgoal 30.5%) = 안 오름.
- = **"opener를 아무리 잘 만들어도(품질 최대: retrieval+compound인자+NMD) 닫기 capacity가 벽이라 무효"의 결정적 확증** — 이번엔 **test 숫자까지 매칭 대조**로 못박음.
- 병목은 여전히 **닫기**(도메인 lemma 적용 = 1.3B capacity), 열기 아님.
- 남은 레버 = 더 큰 executor(별도 서버, 진행중).

관련: [[OPENER_RANGO_ANALYSIS]] · [[README]] · `architecture_bigscale.md`
