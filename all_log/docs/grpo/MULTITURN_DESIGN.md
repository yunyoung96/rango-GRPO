# multi-turn 에러 피드백 — 프롬프트 설계

작성 2026-08-01. rango(1.3B)가 coq-lsp 에러를 받아 tactic을 고치는 multi-turn 설계.
목표: INVALID 시 그냥 재샘플하지 말고, **에러 메시지를 프롬프트에 재주입**해 모델이 수정하게.

## 배경: rango 기존 프롬프트 포맷 (`src/tactic_gen/tactic_data.py`)
```
[STATE]
<proof_state = 현재 goal>
[SCRIPT]
<proof_script = 지금까지 실행한 tactic들>
[PROOFS]                 (BM25 검색 유사증명 20, <PROOF_SEP> 구분)
...
[PREMISES]               (TF-IDF 검색 lemma 50, <PREM_SEP> 구분)
...
### Response:            (= response_template, 여기 뒤가 학습 타겟)
<next tactic>
```
- 모델이 읽는 핵심 = `[STATE]`(goal) + `[SCRIPT]`(진행) + retrieval. → 여기에 에러를 얹는다.

## 핵심 원칙
1. **에러가 rango 학습분포 밖(OOD)** — rango는 에러 피드백으로 학습된 적 없음. → inference 점검은 **최대한 in-format**으로, 학습(GRPO)은 **명시 섹션**으로.
2. **누적**: 한 state에서 실패한 **모든** 시도+에러를 누적(마지막 하나만 X). 안 그러면 같은 실패 반복(cycle).
3. **에러 축약**: coq 에러는 길다. 핵심 첫 줄(보통 "Unable to unify"/"not found")만 ~200자.

---

## 설계 A — inference 점검용 (in-format, 주석으로)
rango가 안 배운 새 토큰 없이, **Coq 주석**으로 실패 이력을 SCRIPT에 얹음 (deepseek-coder는 코드모델이라 주석 이해).
```
[STATE]
<goal>
[SCRIPT]
<script 지금까지>
(* Failed here — do NOT repeat, pick a DIFFERENT tactic:
   apply Ropp_involutive.  ⟶ Unable to unify "- - x" with "x"
   rewrite succ_le.        ⟶ The reference succ_le was not found *)
[PROOFS] ...
[PREMISES] ...
### Response:
```
- 장점: 포맷 그대로(섹션 안 바뀜) → OOD 최소. inference에서 "학습 없이도 에러 쓰나" 판정에 적합.
- 단점: 주석이라 모델이 무시할 수도(약한 신호).

## 설계 B — multi-turn GRPO 학습용 (명시 섹션)
학습으로 에러 활용을 **가르치므로** 명시 섹션이 깔끔:
```
[STATE] <goal>
[SCRIPT] <script>
[FAILED]
apply Ropp_involutive. | ERROR: Unable to unify "- - x" with "x"
rewrite succ_le.        | ERROR: reference succ_le not found
[PROOFS] ... [PREMISES] ...
### Response:
<고친 tactic>
```
- 장점: 에러가 뚜렷한 신호로. 학습 시 "이 에러들 → 이렇게 고침" 매핑을 배움 → OOD 해소.
- 학습 데이터: 성공한 multi-turn 궤적(에러 후 고쳐서 VALID)을 [FAILED] 섹션 포함해 SFT/GRPO.

---

## multi-turn 루프 의미 (동작)
한 proof state S에서:
```
attempts_at_S = []   # (tactic, error) 누적
for turn in range(max_turns):        # max_turns = 재시도 예산(예 4)
    prompt = base(S) + FAILED(attempts_at_S)    # 설계 A 또는 B
    tactic = model.generate(prompt)
    res = coq_lsp.check(script + tactic)
    if res == COMPLETE: return 성공
    if res == VALID:    S ← 새 state; break   # 다음 goal로 전진
    else:  # INVALID
        attempts_at_S.append((tactic, coq_lsp.last_error()))   # 누적 → 다음 turn에 재주입
# 예산 소진 → 이 state에서 막힘(dead)
```
- **VALID/COMPLETE**면 전진(에러 이력 리셋), **INVALID**면 에러 누적 후 재생성.
- 지금(single-turn)과 차이 = INVALID 시 **에러를 프롬프트에 넣어** 재생성(지금은 그냥 재샘플).

## 두 레벨
| 레벨 | 학습? | 프롬프트 | 목적 |
|---|---|---|---|
| (a) inference 점검 | X | 설계 A(주석) | **1.3B가 에러로 고치나** 값싸게 판정 |
| (b) multi-turn GRPO | O | 설계 B(명시) | 수정 전략을 정책에 내재화 |

## 점검(a) 측정 지표 — A/B
- 대조(A0): INVALID 후 [state]만으로 재샘플 → 새 tactic valid율 (=지금 방식)
- 처리(A1): INVALID 후 [state + 실패이력+에러]로 재샘플 → 새 tactic valid율
- **A1 valid율 > A0면 1.3B가 에러 활용 능력 있음** → (b)로.
- 추가: 에러 유형별(unify/not-found/syntax) 수정 성공률 — 어떤 에러를 잘 고치나.

## 구현 상태
- ✅ `proof_manager.last_error()` — coq-lsp 에러 저장·반환 (구현됨)
- ✅ `RECORD_ERROR=1` — 롤아웃 INVALID step에 `coq_error` 기록 (구현됨) → **먼저 에러 품질 확인용**
- ⬜ 에러 재주입(설계 A) — get_recs가 example 내부재구성 → generate_raw 우회 or example.proof_script 수정 필요
- ⬜ A/B 점검 스크립트

## 선결 조건 (구현 전 값싼 확인)
`RECORD_ERROR=1` 소수 롤아웃 → coq-lsp 에러가 **의미적**("Unable to unify", "not found")인가 vs **쓸모없음**("Syntax error"만/빈값)인가.
- 의미적이면 → 재주입 구현 → A/B 점검
- 쓸모없으면 → multi-turn 접음 (값싸게 판정)

관련: [[RANKING_GOLD_VS_APPLIED]] · [[CLOSING_FAILURE_ANALYSIS]]
