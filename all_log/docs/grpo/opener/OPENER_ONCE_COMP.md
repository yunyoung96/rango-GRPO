# opener-once (with compound) — 전체 opening을 첫 한 번에

작성 2026-08-01. 사용자 설계: opener가 **Theorem → Proof → intros → destruct(compound) → ... 를 분해 가능한 만큼(NMD까지) 첫 한 번에 다 열고**, 그 뒤 closing은 **전부 rango**.

## 이전 opener-tac과의 차이
| | opener-tac (structural만) | **opener-once-comp (신규)** |
|---|---|---|
| opener 담당 | structural만(destruct/induction/inv). intros는 rango | **전체 opening**(Proof/intros/simpl/unfold/destruct/induction/inv) |
| 적용 방식 | PLANNER_EVERY (매 스텝, rango와 interleave) | **PLANNER_PRELOOP** (첫 한 번에 opening 블록 다 → 그 뒤 rango만) |
| 순서 | rango(intros)→opener(destruct)→rango(close) | **opener(Proof·intros·destruct 다)→rango(close)** |
| 입력 | goal+후보+retrieval | 동일 (compound 후보 + lemma/proof retrieval) |

동기: 이전엔 rango가 intros를 사이사이 해서 "opener가 여러 번 끼어드는" 형태였음. 사용자 의도 = **opener가 열 수 있는 만큼 통째로 열고 넘기기**.

## 데이터 (`scripts/build_opener_once_data.py`)
- gold 증명에서 **첫 closing 전까지의 모든 opening tactic**(Proof/intros/destruct/…)을 opener target으로, 첫 closing 지점에서 **NMD**.
- **875 예시** = 전체opening 648 + NMD 227. target: Proof 254, NMD 227, intros 160, destruct 74, unfold 69, induction 36, inv 19, ...
- 입력엔 compound 후보(`_targeted_cands`) + lemma(30)/proof(4) retrieval.

## 학습 (`scripts/train_opener_tac.py --data opener_once.jsonl`)
- Qwen2.5-Coder-7B LoRA(r16/α32), **epoch 4**, lr 1e-4, max_len 3072, gradient checkpointing.
- 저장: `models/opener-7b-once-comp`.

## 롤아웃 통합 (`PLANNER_PRELOOP`, `_apply_planner_opening_iter`)
- rollout 시작 시 opener를 **반복 호출**(매 iteration 현재 state의 retrieval 넣어 다음 opening tactic 1개) → 적용(coq-lsp) → **NMD/INVALID/COMPLETE까지 반복** → 그 뒤 rango 메인 루프(opener 안 씀).
- hedge: 홀수 seed 순수 rango(대조).
- executor = subgoal 모델.

## 결과 (300 train 롤아웃, 정식 규모)
- **Stage2 롤아웃 288그룹**: all-solved 3 / **mixed 90 (31%)** / dead 195 | attempt 13.8%
- rand200 (w2, opener 없이): **(미완)**
- 비교(정식 300): plain SFT→GRPO(bigscale2_sft) mixed 26% / leaf-subgoal 27% / opener-tac 28%(100) / opener-once 30%(100)
- 판정: mixed 31% → plain(26%) 대비 상승. 단 mixed↑≠test↑ 주의 — rand200으로 확인.


## ★ once-v2 최종 결과 (2026-08-01, opener degeneracy 버그 3개 수정 후)

이전 once-comp 실행은 **opener가 "Proof."만 뱉는 버그**(데이터에 Proof-target 지배 + pre-loop이 Proof 전 state서 opener 무한호출)로 opening이 안 됐음. 3개 수정:
1. 데이터 빌더: `Proof.` target 제외(`build_opener_once_data.py`) → OPENING 394 + NMD 227 = 621예시.
2. pre-loop(`_apply_planner_opening_iter`): Proof는 코드가 직접 emit + no-progress 가드.
3. GRPO(`grpo_train.flatten_group`): opener step(`example=None`/`planner_opening`) 건너뜀(collate 크래시 방지).

재학습 opener = `models/opener-7b-once-v2/adapter`(SFT loss 0.69→0.17). 검증게이트 PASS(Proof→intros→unfold 실제 opening).

**300 롤아웃 (opener 정상 작동, 첫 클린):**
| 지표 | once-v2 | plain | 이전 버그판 |
|---|---|---|---|
| mixed | **33%** | 26% | 31% |
| attempt | **19.5%** | 18.9% | 14.0% |

→ 단, 위 mixed 33% vs plain 26%는 **불공정 비교**(서로 다른 실행). opener만의 효과는 아래 hedge 대조로 봐야 함.

**★ hedge 대조(같은 롤아웃 내, opener 유무만 차이 — 가장 깨끗한 격리):**
| (같은 정리·같은 예산) | 성공 |
|---|---|
| opener 붙은 attempt | 245/1148 = **21.3%** |
| 순수 rango(hedge) | 203/1148 = **17.7%** |
| per-theorem opener 경로 | 91/287 = **31.7%** |
| per-theorem rango 경로 | 86/287 = **30.0%** |
| opener만 푼 정리 20 / rango만 15 / 공통 71 |

→ opener 진짜 marginal 효과 = **per-theorem +1.7pp**(attempt +3.6pp). mixed 33%는 opener 이득을 과대표현.

**GRPO:** executor step 2460개(opener step 제외), epoch 0→1 loss 0.117→0.107, kl 0.0035→0.0068 안정.

**rand200 (w2, @300s) — 최종 판정:**
| | 성공 | % |
|---|---|---|
| **once-v2 opener** | **64/200** | **32.0%** |
| subgoal base | 61/200 | 30.5% |
| opener-tac | 62/200 | 31.0% |

**★ rand200 (w2, @600s) — 공정 비교 (2026-08-02, executor 단독):**
@300s에선 parity였으나 compute를 2배 주자 **top-tier로 상승**:
| | 성공 | % | vs plain |
|---|---|---|---|
| SFT→GRPO / cascade-s0r2 | 75/200 | 37.5% | +4.0pp |
| **once-v2 opener** | **74/200** | **37.0%** | **+3.5pp** |
| leaf-subgoal | 74/200 | 37.0% | +3.5pp |
| eisafe | 70/200 | 35.0% | +1.5pp |
| plain (기준선) | 67/200 | 33.5% | — |

- once-v2 @600s = **37.0%** — plain 대비 +3.5pp(~1σ), **SFT→GRPO와 parity(−1정리)**, leaf-subgoal과 동률.
- 해석: opener-assisted GRPO executor는 **@300s parity(32%) → @600s top-tier(37%)**. "test는 compute-bound"(도달을 더 오래 탐색하면 opener 학습이 살아남) 가설과 일치. 단 **SFT→GRPO를 넘진 못하고 동률**, leaf-subgoal(37.0%)과 정확히 같아 **opener-rollout GRPO가 subgoal-family 천장(37%) 위로 밀진 못함**.

- 순 차이 **+3정리(+1.5pp)** — 이항 1σ≈3.3pp 안, **통계적으로 parity**(롤아웃 지표 개선이 test 성능으로 유의하게 전이되진 않음 = closing capacity 벽 재확인).
- **단, complementarity 발견**: 공통 55 / **opener만 9정리** / subgoal만 6정리 / **합집합 70=35.0%**(단독 대비 +3~4.5pp).
  - opener-only 9정리 = 467·998·1337·1614·1676·1918·1964·1977·2063 → 실제 증명이 `induction rs`, `unfold…destruct v; inv H0`, `induction c1; inversion H1` 등 **분해 opening 필요 정리**. opener가 이런 데서 강함.
  - → opener는 "더 낫다"기보다 **부분적으로 disjoint한 정리집합을 탐색**. 앙상블/union 각도에서만 의미.

**결론(negative, 단 nuance):** opener 5변형(every/once/combo/tac/once-v2) **모두 순 성능 parity**. opener 부품 품질(opening valid율)은 오르지만 순 test 성능 기여는 노이즈 내. 벽=**closing capacity**(선택 65%+구성 35%, [[RANKING_GOLD_VS_APPLIED]] [[CLOSING_FAILURE_ANALYSIS]]). 유일한 양성 신호는 **분해정리에서의 complementarity(union 35%)** — 논문엔 "opener는 성능이 아니라 커버리지 상보성을 준다"로 정직히 기술.

## 관전 포인트 (사전 예상 — 결과로 확인됨)
- ~~opener가 전체 opening을 통째로 열면 성능이 plain을 넘는가~~ → **아니오, parity**. 예상대로 닫기 벽 여전.
- opener valid율/롤아웃 mixed는 상승(예상 적중), 하지만 test 순성능엔 전이 안 됨.

관련: [[OPENER_TAC]] · [[COMPOUND_CANDIDATES]] · [[CLOSING_FAILURE_ANALYSIS]] · [[RANKING_GOLD_VS_APPLIED]] · [[README]]
