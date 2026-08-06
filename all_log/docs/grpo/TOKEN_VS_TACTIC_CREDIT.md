# 토큰 확률 vs tactic 보상 — 불일치를 어떻게 잇나 (2026-08-06)

질문: "LLM은 `destruct H`를 토큰 `dest`/`ru`/`ct`/` H` 로 따로 생성하고 **확률도 토큰마다** 나온다.
그런데 **보상은 tactic 하나 단위**(증명 성공=1). 이 불일치를 어떻게 처리하나?"

## 한 줄 답
- **확률**: 토큰마다 각각 (autoregressive, `dest`가 `ru`의 조건). `sequence_token_logprobs`.
- **보상/advantage**: tactic이 속한 **시도(attempt) 하나에 값 1개** → 그 tactic의 **모든 토큰에 똑같이 브로드캐스트**.
- **loss**: 토큰별 surrogate를 **완성 토큰 평균**으로 합쳐 시퀀스 1개의 기여로.
- 즉 **credit assignment 단위 = tactic(action)**, 토큰은 그 action을 발화하는 부품이라 **같은 credit 공유**.

## 두 층위의 MDP (먼저 정리)
| 층위 | state | action | 언제 바뀌나 |
|---|---|---|---|
| **증명 수준(RL)** | proof state = 열린 goal + 가설 (`[STATE]`) | **tactic 하나** (`destruct H`) | tactic 실행 후 Coq이 새 goal 반환 |
| **토큰 수준(LLM 발화)** | 프롬프트 + 지금까지 친 토큰 | 토큰 하나 (`dest`) | 매 토큰 (autoregressive) |
- `dest`,`ru`,`ct`,` H`는 **같은 하나의 action(`destruct H`) 내부**. RL state는 그 사이 안 바뀜.
- LLM 입력=`[PREMISES][PROOFS][STATE](현재 goal)[SCRIPT](지금까지 tactic)[TACTIC]` → 다음 tactic 생성.

## ① 확률 — 토큰별 (각각)
`sequence_token_logprobs` (grpo_train.py:90): 한 forward로 각 위치의 `logp(token_t | <t)` 반환.
```
logp(dest | [STATE][SCRIPT])   = -0.50   p=0.607
logp(ru   | …dest)             = -0.10   p=0.905   ← 이전 토큰 dest가 context
logp(ct   | …dest,ru)          = -0.05   p=0.951
logp( H   | …dest,ru,ct)       = -0.80   p=0.449
tactic 전체 logp = Σ = -1.45   →  P(destruct H)=∏p=0.235
```
→ 확률은 **토큰마다 따로** 나온다(맞음). tactic 확률은 그 합(=곱).

## ② 보상/advantage — tactic 하나에 1개, 토큰에 공유
- Coq 검증은 **시도(attempt) 단위 binary**: 그 시도가 Qed면 reward=1, 아니면 0.
- 그룹(같은 정리 G=8 시도) 상대 advantage: `A_i = (r_i − mean)/std` — **시도당 스칼라 1개**.
- 코드(grpo.py `grpo_batch_loss`): `adv = advantages.unsqueeze(1)` → `(B,1)` 로 **모든 토큰에 브로드캐스트**.
```
destruct H 가 속한 시도의 A = 0.7  (시퀀스 1개 = 값 1개)
 → dest, ru, ct, H  4토큰 전부 같은 A=0.7 사용
```
→ **"어느 토큰이 잘했나"는 모름. tactic 전체가 좋았다/나빴다만 안다.** (binary 검증의 한계)

## ③ loss — 토큰 surrogate → 완성 토큰 평균
grpo.py `grpo_batch_loss`:
```
ratio_t   = exp(logp_new_t − logp_old_t)          # 토큰별
surr_t    = min(ratio_t·A, clip(ratio_t)·A)       # 토큰별 (A는 공유)
seq_obj   = Σ_t (surr_t · mask_t) / (완성토큰수)   # ★ 완성 토큰 평균
loss      = − mean_over_seq(seq_obj) + β·KL
```
실측 예 (A=0.7, 위 토큰들):
```
dest: ratio 1.051 → surr 0.736
ru  : ratio 1.020 → surr 0.714
ct  : ratio 1.010 → surr 0.707
 H  : ratio 1.051 → surr 0.736
seq_obj = 평균(4) = 0.723   ← 이 tactic의 loss 기여
```
- **mask**: `[STATE][SCRIPT]`(프롬프트) 토큰은 mask=0 (loss 제외), **완성(tactic) 토큰만 mask=1**. 즉 프롬프트 확률은 학습 안 하고 tactic 토큰만.
- **평균(sum/len)**이라 tactic 길이에 무관하게 정규화 (긴 tactic이 과대반영 안 됨).

## 그래서 gradient 방향 (직관)
`−seq_obj` 최소화 = `seq_obj` 최대화 = **A>0(성공 시도)면 그 tactic 토큰들의 logp를 올림**(그 tactic을 더 자주 생성), A<0(실패)면 내림.
- dest/ru/ct/H 다 같은 A로 밀리므로 → "`destruct H`라는 발화 전체"를 강화/억제.

## 한계 (우리 문제와 연결)
1. **binary·tactic 단위 credit**: "13 step 중 12개 맞고 마지막 틀림"도 reward=0 → 맞은 12개 tactic도 −. 부분 진전에 신호 없음 → sparse 극대화.
2. **토큰별 credit 없음**: `destruct` 자체는 옳고 `H` 대상만 틀렸어도, 두 토큰이 같은 A. "어느 토큰이 문제였나" 구분 불가.
3. → 이게 process/dense reward([[DENSE_GUIDES_SPARSE]]) 나 sub-step 분해가 공략하는 지점: **credit을 더 잘게(goal 닫힘/토큰 그룹)**.

관련: [[IMPLEMENTATION]] §(4) credit assignment · [[DENSE_GUIDES_SPARSE]] · grpo.py `grpo_batch_loss` · grpo_train.py `sequence_token_logprobs`/`flatten_group`
