# 조립 학습 — SFT 방향 vs GRPO 방향 (2026-08-03)

조립(apply THIS lemma to THESE hyps)을 decoder에 학습시키는 **두 경로**. 사용자 우선순위 = SFT 기반.
바탕: [[DESIGN]](왜 조립이 벽) · [[RESEARCH]](논문).

---

# 왜 두 방향인가 (한눈에)

| | **SFT 방향** | **GRPO 방향** |
|---|---|---|
| 배우는 것 | "정답 조립을 흉내" (gold 모방) | "내가 한 조립이 좋았나로 강화" |
| 데이터 | gold 증명 (고정 정답) | 모델 자신의 롤아웃 (성공/실패) |
| 신호 | 정답 tactic MLE(항상 있음) | reward(희소, dead=0) |
| 장점 | 안정·값쌈·신호 항상 | 자기 실수 교정, on-policy |
| 단점 | gold 분포 과적합, 조립 "왜"는 암묵 | 희소보상, 이미 여러번 시도됨 |
| 구현 | `grpo_train --sft` | `grpo_train`(GRPO) |

**핵심 차이**: SFT는 "이런 조립을 해라"(정답 복사), GRPO는 "네 조립이 productive했나"(자기 평가).
→ **SFT로 조립을 "가르치고", GRPO로 "다듬는" 게 자연스러운 순서.**

---

# ══════════ SFT 방향 (우선) ══════════

목표: gold 증명의 조립을 **더 잘 배우게** 데이터/타겟을 재설계. 인프라 = 기존 `--sft`(성공궤적 MLE).

## SFT-1 ⭐ rationale SFT (조립 근거를 먼저 생성) — 가장 값쌈
### 무엇
tactic만 배우지 말고, **"왜 이 lemma를 이 가설에"를 근거로 먼저** 생성하게 학습.
```
지금 SFT target:  "apply unsigned_repr; exact H1."
제안 SFT target:  "(* H1: 0<=n<=max. unsigned_repr: forall z, 0<=z<=max -> unsigned(repr z)=z.
                     H1이 전제를 만족 → apply. *)
                   apply unsigned_repr; exact H1."
```
### 왜 조립 학습
근거를 쓰며 **lemma 전제 ↔ 가설 매칭을 언어화** → 조립 사고를 명시적으로 배움(암묵 아님).
### 데이터 만들기
gold `apply L; exact H`마다:
1. L의 시그니처(코퍼스서), H의 타입(goal 가설부) 파싱
2. 근거 합성 = 템플릿(`{H}: {H타입}. {L}: {L시그니처}. 전제 매칭 → apply`) or 7B 생성
3. SFT target = `근거\ntactic`
### 학습
`grpo_train --sft`에 데이터만 교체(target에 근거 포함). **새 인프라 0.**
### 리스크
근거 틀리면 방해. 추론 시 근거 토큰 추가(느림).

## SFT-2 rationale 없이 재료 정렬 (구조 SFT)
### 무엇
근거 대신 **입력에 재료를 조립하기 쉽게 정렬**해서 SFT.
```
[MATERIALS]
  goal 전제 ↔ lemma 전제 나란히:
  H1: 0<=n<=max   ←매칭→   unsigned_repr 전제: 0<=z<=max
[STATE] unsigned(repr n)=n
→ target: apply unsigned_repr; exact H1.
```
### 왜
attention이 "가설↔lemma전제" 매칭을 입력 구조에서 바로 봄.
### 구현
collator에 [MATERIALS] 섹션([TYPES]처럼 env 가드). = rango-augmented [DEFINITIONS] 확장.

## SFT-3 조립 sub-step 분해 SFT (select→bind→emit)
### 무엇
tactic 생성을 3단계로 쪼개 각각 학습.
```
target: [SELECT] unsigned_repr
        [BIND] z:=n via H1
        [EMIT] apply unsigned_repr; exact H1.
```
### 왜
"선택"과 "인자바인딩"을 분리 학습 → 어디서 틀리는지 신호 분리. (고전 select→args의 LLM판, 논문 갭=novel)
### 구현
gold를 3단계로 재작성해 SFT. constrained decoding(SELECT는 premise 중, BIND는 가설 중)도 가능.

## SFT 방향 요약
- **SFT-1(rationale)이 1순위** — 값싸고(target만 변경) 조립을 언어화.
- SFT-2(재료정렬)는 rango-augmented와 합침.
- SFT-3(분해)는 novel하나 데이터 재작성 부담.
- **공통 한계**: gold 모방이라 gold 분포 밖(모델이 다르게 푸는 경우) 안 배움 → 그래서 GRPO로 보완.

---

# ══════════ GRPO 방향 ══════════

목표: 모델 자신의 조립이 **productive했나**로 강화. 인프라 = 기존 `grpo_train`(+`--process`).

## GRPO-1 ⭐ 조립 dense reward (productive-VALID 판정) — GRPO의 핵심
### 무엇
전체 증명 성공(outcome) 대신, **각 apply 스텝이 goal을 진전시켰나**를 coq-lsp로 판정해 per-step 보상.
```
스텝 보상:
  COMPLETE: +1.0
  productive VALID (subgoal↓ or goal크기↓): +0.3
  non-productive VALID (제자리 simpl/auto): 0.0
  INVALID: -0.1
```
### 왜 조립 학습
- dead 정리(전체 실패)여도 **그 안의 productive apply는 +보상** → 좋은 조립 살림(희소보상 완화).
- "이 조립이 productive했나"를 스텝단위로 배움.
### productive 판정 (verifier 공짜 라벨)
롤아웃이 이미 기록한 `state_key`(goal 상태) 연속 비교:
```
productive = len(subgoals) 줄었나 or len(goal텍스트) 줄었나 or COMPLETE로 향했나
```
### 구현
`grpo_train --process` 강화 — 현재 단순(에러-0.10/유효-0.05)을 **state_key 진전 기반**으로.
롤아웃에 state_key 있으니 **재수집 없이** flatten_group에서 계산. GRPO=critic-free=1.3B OK.
### 리스크
기존 --process도 outcome 못넘음 → **productive 판정 정교화** 필수. "막다른 진전"(진전했으나 결국 실패)이 노이즈.

## GRPO-2 조립 credit 분리 (선택 vs 바인딩)
### 무엇
INVALID 실패를 "lemma 선택이 틀림 vs 인자만 틀림"으로 나눠 다른 벌점.
```
gold와 lemma head 같은데 INVALID(인자/시점만 틀림): -0.05 (아까움)
gold에 없는 lemma(선택 자체 틀림): -0.15 (더 나쁨)
```
### 왜
조립의 "선택" 실패와 "적용" 실패를 구별해 학습 (앞서 68% 다른 tactic종류·90% 오lemma 분석 활용).
### 구현
grpo_train flatten_group에서 gold tactic과 비교(RECORD_TOPK/gold 매칭).

## GRPO-3 하드-네거티브 GRPO/DPO (조립 대조)
### 무엇
같은 goal에서 gold 조립 vs 타입호환 오답 조립(coq INVALID) 대조.
### ★ 과거 DPO 실패(unique-0) 고침
- 하드-네거티브(아무 오답 X, retrieval상위·타입호환 INVALID lemma)
- 커리큘럼(쉬운→어려운)
### 구현
`--dpo` + hard-neg 데이터. **단 DPO 계열은 GRPO-1보다 약한 베팅.**

## GRPO 방향 요약
- **GRPO-1(dense reward)이 1순위** — verifier 공짜라벨, dead도 신호.
- GRPO-2(credit분리)는 GRPO-1에 얹는 정밀화.
- GRPO-3(하드네거)는 novel하나 과거실패 이력.

---

# ══════════ 통합 권장 (SFT→GRPO 파이프라인) ══════════

```
1단계 SFT: SFT-1(rationale) — gold 조립을 "왜"까지 배움 (조립 가르치기)
              [+ SFT-2 재료정렬 = rango-augmented [MATERIALS]]
2단계 롤아웃: SFT모델로 재롤아웃 (on-policy)
3단계 GRPO: GRPO-1(dense reward) + GRPO-2(credit분리) — 자기 조립 다듬기
```
- **SFT가 조립을 가르치고, GRPO가 productive 신호로 다듬는** 자연스러운 순서.
- 통제군: rationale/dense-reward 없는 기존 SFT→GRPO(tst1000tr5091).
- 평가: (a) gold apply top-1 (b) 성공률 (c) **조립 특화 held-out**(재료 다 주고 조립만 시키는 셋).

# 정직한 회의
- 조립 개선이 test 전이는 별개(과거 DPO unique-0, process 못넘음). 벽이 도달성일 수도(§10).
- 단 조립특화 dense objective(GRPO-1)·rationale(SFT-1)은 아직 안 해봄. novelty 확실.

# 지금 CPU 사전검증 (학습 전, GPU 안 씀)
- **GRPO-1 실현가능성**: 롤아웃 state_key 연속비교 → productive VALID가 실제 구별되나, dead에 productive step 얼마나.
- **SFT-1 실현가능성**: gold apply의 근거를 템플릿으로 깨끗이 합성되나(L시그니처·H타입 파싱).
- **GRPO-3 실현가능성**: hard-neg(타입호환 INVALID lemma)가 실제 뽑히나.

관련: [[DESIGN]] · [[RESEARCH]] · [[../rango_augmented/COMPOSITION_IS_THE_WALL]] · [[../SUBGOAL_PAPER_ASSESSMENT]] §10
