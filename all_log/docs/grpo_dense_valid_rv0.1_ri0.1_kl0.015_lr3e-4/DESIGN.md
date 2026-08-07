# Dense(potential-style) 보상 GRPO — 설계 (2026-08-07)

> **한 줄**: sparse GRPO(Qed=1만)가 "인자 생성이 valid한지"에 신호를 못 줘서 apply/rewrite 인자 생성을 못 배운다.
> → **인자-필요 tactic이 VALID면 +보상(타입 맞는 인자 생성 성공), INVALID면 −보상, Qed는 +1.** 자동화는 0.
> 실험태그: `dense_valid_rv0.1_ri0.1_kl0.015_lr3e-4`. 드라이버: `all_log/grpo_dense_train.sh`.

## 1. 동기 — 왜 dense인가
- 실증([[../grpo_failure/MIXED_FAILURE_ANALYSIS_lr3e-4]] · [[../grpo_failure/TACTIC_FAILURE_EXAMPLES_lr3e-4]]): 실패의 다수가 **apply/rewrite에서 타입 안 맞는 인자(lemma/term) 생성 → INVALID**.
- **sparse 보상(Qed=1/else 0)의 문제**: 한 시도 안에서 "이 tactic이 valid했나"에 **gradient 신호가 0**. 증명이 최종 성공/실패한 것만 안다. → "valid한 인자를 생성하는 법"을 배울 신호가 없다.
- sft 강화도 안 됨([[../grpo/SFT_STRENGTH_OVERFIT]]: 강할수록 held-out↓). 그래서 **보상 쪽**을 손본다.

## 2. 두 가지 보상 설계 (이론 정직하게)

### (A) dense_valid — raw validity 보너스 ★이번 실행
```
COMPLETE (any tactic)        → +r_complete (=1.0, 증명 종결이 지배)
ARG tactic + VALID           → +r_valid    (=+0.1, 타입 맞는 인자 생성 성공!)
ARG tactic + INVALID         → −r_invalid  (=−0.1, 틀린 인자)
비-ARG (auto/intros/simpl…)   → 0           (auto-spam gaming 방지)
```
- **ARG tactic** = 인자(lemma/term/식)를 생성해야 하는 것: apply/eapply/rewrite/erewrite/destruct/induction/exists/specialize/replace/assert/elim/case/inversion/injection/generalize/pose/set/remember/change/unfold/fold.
- 코드: `process_reward.py: dense_valid_process_rewards`.

### (B) potential_shaping — 진짜 Ng1999 PBRS (Φ over state)
```
Φ(s) = −(goal 복잡도)          # state s에 정의 (goal 수, 폴백=크기)
F(s→s') = γ·Φ(s') − Φ(s)       # 차분 → telescoping → 최적정책 불변(invariance)
COMPLETE: Φ(terminal)=0.  INVALID: s'=s → F≈0.
```
- 코드: `process_reward.py: potential_shaping_rewards`.

### ⚠️ 이론적 구분 (중요)
- **potential은 state s에 대해 정의**(Ng1999). F=γΦ(s')−Φ(s) 형태여야 최적정책 불변.
- **"valid 인자 생성"은 Φ(s)로 표현 불가** — validity는 **(s,a) 전이의 성공여부**(state가 아님). → dense_valid는 **raw 보너스**이지 potential이 아니다.
- 즉 (A)는 **병목(인자 생성) 직공이나 불변 보장 없음**, (B)는 **불변이나 "진전"만 보상**(valid 인자 생성을 직접 안 겨냥).
- 완화책(A의 bias): ① ARG tactic만(auto-spam 차단), ② COMPLETE=+1로 종결 지배, ③ 그룹 정규화, ④ 작은 크기(0.1 ≪ 1.0).
- 첫 실행은 **병목 직공이 목적**이라 (A) dense_valid. (B) potential은 비교군으로 `REWARD_MODE=potential`로 언제든 실행 가능.

## 3. GRPO 통합 (기존 --process 인프라 재사용)
- `flatten_group`의 process 분기 → `REWARD_MODE` env로 (A)/(B)/checker 선택. φ를 **그룹 단위 정규화**(`normalize_process`).
- 손실: `grpo_batch_loss_perstep`. **outcome advantage(전체 완성토큰) + process φ(각 tactic 첫 토큰)**. 논문(2606.20068): first-token credit이 최적. 길이보정으로 PRM 희석 방지.
- 즉 **sparse outcome 신호는 유지하고**, 그 위에 **per-tactic dense 신호를 더한다**.

## 4. 하이퍼파라미터
| 항목 | 값 | env/flag |
|---|---|---|
| REWARD_MODE | dense_valid | `REWARD_MODE` |
| r_valid | +0.1 | `DENSE_R_VALID` |
| r_invalid | −0.1 | `DENSE_R_INVALID` |
| r_complete | +1.0 | `DENSE_R_COMPLETE` |
| arg_only | 1 | `DENSE_ARG_ONLY` |
| lr | 3e-4→3e-5 (cosine) | (sparse baseline과 동일) |
| kl_beta | 0.015 | `--kl_beta` |
| clip | 0.2 | `--clip_eps` |
| B/G | 100/8 | batch-chunk |
| base | sft-1 (`rango-tst1000tr5091-sft`) | `--init_adapter` |
| GPU | **GPU1 단독** (gpu0_foreign로 GPU0 회피) | `GPUS="1"` |

## 5. 검증(디버깅) — 완료
- **단위테스트 12/12**: dense_valid 값(arg VALID→+0.1, INVALID→−0.1, 비-arg→0, COMPLETE→+1, arg_only 토글, head추출), potential(진전 F>0, INVALID F≈0), flatten_group 통합(mixed 그룹서 정규화된 비영 process advantage), grpo_batch_loss_perstep 무크래시.
- **e2e**: `grpo_train --process REWARD_MODE=dense_valid`를 실제 15 mixed 그룹·GPU1에서 무크래시 학습 확인.

## 6. 실행 방법
```bash
# 이 서버 (GPU1)
bash all_log/grpo_dense_train.sh    # (run_in_background/nohup 아님 — 환경상 harness bg 권장)
# 다른 GPU 서버: git pull 후 동일. GPU 바꾸려면 GPUS/CUDA 조정, gpu0_foreign 유무 확인.
```
- 산출물: `models/rango-tst1000tr5091-bc_dense_valid_...`, 로그 `all_log/tst1000tr5091_bc_dense_valid_....log`, 롤아웃 gz 보존.

## 7. 무엇을 볼까 (성공 판정)
- **1차 = probe100(held-out 증명성공률)**: sparse GRPO는 29→30 정체([[../grpo/BC_LR3E-4_RESULT]]). **dense가 30을 넘기면 성공.**
- **2차 = rollout INVALID율(특히 apply/rewrite)**: sparse는 62→65% 불변. **dense가 이걸 내리면** "valid 인자 생성"을 배운 직접 증거.
- flywheel: probe 매 10 batch. baseline(sft-1)=~29-31.

## 8. 리스크 / 정직한 한계
- **불변 아님**(raw 보너스) → 최악의 경우 valid-but-unproductive 편향. 완화책(§2)으로 억제하나 관찰 필요.
- **auto-spam**: 비-arg를 0으로 뒀지만, 모델이 "안전한 arg tactic"(항상 통과하는 자명 apply)로 farming 가능성. rollout에서 tactic 분포 감시.
- **potential(B)가 더 이론적으로 안전** — dense(A)가 편향 조짐 보이면 (B)로 전환하거나 (A)+(B) 하이브리드.
- SFT 실험처럼 **held-out으로 판정**(training 신호만 보고 속지 말 것).

관련: [[../grpo_failure/TYPE_LEARNING_RESEARCH]] · [[../grpo/DENSE_GUIDES_SPARSE]] · [[../grpo/BC_LR3E-4_RESULT]] · [[../grpo_failure/TACTIC_FAILURE_EXAMPLES_lr3e-4]]
