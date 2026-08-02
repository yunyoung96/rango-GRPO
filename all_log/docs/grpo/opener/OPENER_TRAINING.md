# Opener 학습 — 정확한 방법 (2026-07-30)

목표: 병목인 **분해 선택**을 학습으로 뚫기. 범용 32B는 gold 분해 **대상 일치 14%**(강제 시 dead 59→78% 악화). → **Qwen2.5-Coder-7B를 CompCert opening에 fine-tune**해 대상을 맞히게. (32B는 GPU1 단독서 학습 불가 — bf16 초과/bnb로더 버그/AWQ 학습불가.)

## 0. 두 변형
- **(a) 생성형**: goal → gold opening을 **직접 생성**.
- **(b) 하이브리드 선택형**: goal + **열거후보(`_targeted_cands`, gold 대상 45% 포함)** → 후보에 있으면 **선택**, 없으면 생성. (7B가 대상을 생성 대신 인식.)

## 1. 학습 데이터 (147개, `data/grpo_rollouts/goldsft_bs2.jsonl`)
- 300 train gold 증명에서, **첫 structural tactic**(induction/destruct/inversion/case/inv)이 있는 정리만 → **147개**. (107개는 분해 없이 automation으로 닫혀 제외.)
- 각 정리:
  - `goal` = 첫 분해 step의 proof_state(=결정 지점 상태).
  - `opening`(생성형) = 시작~첫 분해까지 gold tactic 리스트.
  - `gold`(선택형) = gold 첫 분해 tactic 전체(예: `destruct (Rle_or_lt 0 x) as [[Hx|Hx]|Hx].`).
  - `candidates`(선택형) = `_targeted_cands([goal])` 열거.
- 빌더: `scripts/build_opener_data.py`(생성) · `scripts/build_opener_sel_data.py`(선택).

## 2. 후보 열거 `_targeted_cands` (선택형 입력, `src/tactic_gen/grpo_rollout.py`)
goal을 첫 빈 줄로 hyp/결론 가르고 5단계 → dedup → 앞 18개. (유효성은 coq-lsp가 필터.)
1. **① 문맥 변수**: 가설 `name:type`에서 head가 `_IND_TYPES`(nat/Z/list/…)이거나 대문자 inductive(Type/Set/Prop/R/Q/radix 제외), `->`아님 → `destruct v.`/`induction v.` (앞3)
2. **② scrutinee**: `match E with`/`if E then`의 E(balanced, ≤80자) → `destruct (E).` (앞4) — compound destruct 핵심
3. **③ 결정절차**(CompCert 하드코딩 `_DEC_UN/_DEC_CONST/_DEC_BIN`): Z→`zeq/zlt/zle`, R→`Rle_or_lt/Rlt_le_dec`, positive→`peq`, nat→`Nat.eq_dec/le_lt_dec`, bool/val/option→`destruct a`
4. **④ inversion**: `=`포함 또는 H* 가설 → `inversion H.` (앞2)
5. **⑤ forall-bound + `induction 1`**: 결론 `forall x…`의 x → induction/destruct + generic 첫-premise 귀납
- **gold 열거 포함률**: 확장 전 5%(destruct) → 확장 후 **45%**(전체).

## 3. 학습 설정 (공통)
- **모델**: `Qwen/Qwen2.5-Coder-7B-Instruct` (bf16, GPU1 단독, ~15GB)
- **LoRA**: r=16, alpha=32, dropout=0.05, bias=none, target=all-linear, task=CAUSAL_LM
- **옵티마이저**: AdamW, lr **1e-4**, grad-clip 1.0
- **에폭**: 4, **max_len** 1024(생성)/1536(선택)
- **손실**: causal LM, **프롬프트는 마스킹**(labels=-100), assistant completion + eos에만 gradient
- 저장: LoRA 어댑터 (`models/opener-7b/adapter`, `models/opener-sel-7b/adapter`)
- 스크립트: `scripts/train_opener_sft.py`(생성) · `scripts/train_opener_sel.py`(선택)

## 4. 프롬프트 (chat 포맷)
**생성형**
```
system: You are a Coq proof strategist. Given the current GOAL, output ONLY a JSON array
        of the opening Coq tactics that decompose it (induction/destruct/inversion on the
        right target), most-promising first. No prose.
user:   GOAL:\n{goal}
assistant: ["destruct x; simpl; auto."]        ← gold opening (JSON)
```
**선택형** (system은 "Given the GOAL and enumerated CANDIDATE decompositions … Pick a candidate if one fits, otherwise write your own.")
```
user:   GOAL:\n{goal}\n\nCANDIDATES:\n- destruct valid_exp.\n- destruct (Rle_or_lt 0 x).\n …
assistant: ["destruct (Rle_or_lt 0 x) as [[Hx|Hx]|Hx]."]
```

## 5. 통합 (학습 후 어떻게 씀)
- **planner_server**(`src/model_deployment/planner_server.py`): Qwen-7B base + opener 어댑터를 한 번 로드, HTTP `/plan`. env `PLANNER_ADAPTER`(어댑터), `PLANNER_OPENER=1`(학습 프롬프트).
- **rollout hedge**(`grpo_rollout.rollout_attempt`): env `PLANNER_FIRST_URL`+`PLANNER_HEDGE=1` → **짝수 seed 롤아웃만 opener opening 적용, 홀수는 순수 rango**(regress 방지). opening은 coq-lsp 검증하며 순차 적용, 이후 rango가 이어감.
- executor는 **π₀=rango-grpo(SFT→GRPO)**, alias `grpo-rollout-pf`.

## 6. 결과
- **생성형 opener**: 학습 loss 1.52→0.85→0.47→0.25. target 대상 일치 **14%(범용 32B)→68%(학습, train셋)**.
- **opener-hedge 롤아웃**(train 90 matched, vs SFT→GRPO): dead **68%→64%**, revive 6 / regress 3 (순 +3).
- **성공/실패 대조**: 성공한 opener 롤아웃 **100% gold일치**, 실패도 **66% gold일치** → 선택은 필요조건, **도달이 충분조건 아님**(상한).
- **선택형 opener**: 학습 loss 1.16→0.62→0.36→0.18. 대상 일치 **80%**(생성형 68%·범용 32B 14% 대비 개선) — **열거후보 입력이 대상 선택을 올림**(생성 대신 인식). ★님 가설 입증.

### target 대상 일치 요약
| 방법 | 대상 일치 |
|---|---|
| 범용 32B (학습 X) | 14% |
| 생성형 7B (학습) | 68% |
| **선택형 7B (열거후보 입력)** | **80%** |
(모두 train셋 기준=암기 포함. 상대 개선이 요점.)

## 7. 한계 / 다음
- **도달 벽**: gold로 옳게 열어도 66% 실패 → opener만으론 상한. 다음 = 도달(모든 분해 지점 opener / rango 기회↑ / leaf 자동닫기).
- 데이터 147개는 작음 — 300 전체·augmentation 여지.

관련: [[coverage-not-wall-selection-reachability]] · [[PLANNER_EXECUTOR_DESIGN]] · [[PAPER_FINDINGS]]
