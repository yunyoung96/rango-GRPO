# OPENER (planner-executor) — 문서 모음

Coq 정리증명에서 **강한 opener(Qwen-7B)가 분해를 열고 → rango(1.3B)가 닫는** planner-executor 실험 모음.
작성/정리 2026-07-31.

## ★ 한 줄 결론
**opener는 성능을 못 올린다 (parity).** opener는 첫 분해를 90% VALID로 잘 열지만(gold 정확일치 52%), 롤아웃의 병목은 **열기가 아니라 닫기(closing)**다. 열기·닫기가 **직렬 벽**이라 opener로 열기만 고쳐도 닫기(도메인 lemma 지식·증명 경로 = 1.3B capacity)가 여전히 막아서 성능 0 개선. opener-once ≈ plain SFT ≈ 조합 모두 ~32-34% 천장. opener-**every**(매 분기)는 오히려 악화(19%, 과분해). → 진짜 레버는 **더 큰 executor(7B)**.

## 문서 목록
| 파일 | 내용 |
|---|---|
| `OPENER_RANGO_ANALYSIS.md` | **종합 분석** — 성공률 표, 기호/롤아웃 형식(❌→✅ 원리), opener/rango 역할분담, 두 벽(열기 vs 닫기), 닫기 실패 원인(INVALID 1455 분석), 결론 + 예시 |
| `OPENER_RANGO_SOLVED.md` | ✅ **맞춘 예시 20개** — GOLD 전문 vs opener+rango vs plain SFT (step별 validity 정렬) |
| `OPENER_RANGO_FAILED.md` | ❌ **틀린 예시 20개** — 같은 3단 비교 |
| `OPENER_TRAINING.md` | opener 학습 방법 (생성형/선택형, subgoal opening 포함, 데이터·하이퍼) |
| `PLANNER_EXECUTOR_DESIGN.md` | planner-executor 구현 설계 (초기) |
| `COMPOUND_CANDIDATES.md` | compound 후보 생성(`_targeted_cands`) — 5단계, 인자 추출 알고리즘, **커버리지 실측(compound ~20%만 커버)** |
| `DDR_COMPOUND_RETRIEVAL.md` | **Decidability-Directed Retrieval** — compound decider를 타입/술어/연산으로 찾는 새 retrieval 설계(기존 content-retrieval이 못 찾는 것 겨냥, 예시多) |

## 관련 모델
- `models/opener-7b/adapter` — 정리 opening만 학습 (147예시)
- `models/opener-7b-sub/adapter` — **정리+subgoal opening** 학습 (276예시, 130 subgoal) ← 최종
- `models/rango-grpo-bs2-sft/adapter` — gold-SFT 1.3B (executor, epoch 2, retrieval증강)
- `models/rango-grpo-subgoal-bs2/adapter` — subgoal-학습 executor (닫기 시도, test~40%)

## 관련 스크립트
- `scripts/build_opener_data.py` / `build_opener_sub_data.py` — opener 학습데이터 (분해지점→opening)
- `scripts/train_opener_sft.py` — opener LoRA SFT (max_len 2048, NaN가드)
- `scripts/train_opener_sel.py` — 선택형 opener
- `all_log/full_pipeline.sh` — gold-SFT + opener-every 파이프라인
- `all_log/pipe_once.sh` — opener-once 파이프라인
- `all_log/combo_rollout.sh` — subgoal모델 + opener-once 조합 검증

## 관련 롤아웃 데이터
- `data/grpo_rollouts/opener_gen_sub.jsonl` — opener-7b-sub 학습데이터
- `data/grpo_rollouts/opener_sub_pipe.jsonl` — opener-every 롤아웃 (mixed 10%)
- `data/grpo_rollouts/opener_once_pipe.jsonl` — opener-once 롤아웃 (mixed 30%)
- `data/grpo_rollouts/combo_subgoal_opener.jsonl` — subgoal모델+opener 조합
- `data/grpo_rollouts/rango-grpo-subgoal-bs2-s0.jsonl` — plain SFT baseline (재활용)

## 성공률 요약 (롤아웃 100 train, greedy)
| 방법 | 정리 ≥1성공 | mixed | attempt |
|---|---|---|---|
| opener+rango (subgoal모델) | 32% | 27% | 17.0% |
| plain SFT→GRPO | 34% | 27% | 18.9% |
| gold-SFT + opener-once | 33% | 29% | 17.4% |
| opener-every (매 분기) | 19% | 8% | 12.6% |
| opener-once-comp (300, 전체opening) | 32% | 31% | 13.8% |

관련: [[opener-x-subgoal-integration]] · [[coverage-not-wall-selection-reachability]] · [[research-direction-2026-07]]
