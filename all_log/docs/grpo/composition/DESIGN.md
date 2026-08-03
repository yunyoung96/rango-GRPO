# 조립(composition) 학습 — 바닥부터 설계 (2026-08-03)

논문 안 읽어도 이해되게 처음부터. **문제 → 왜 지금 안 되나 → 어떻게 고칠지(3방법) → 각각 정확한 구현.**

---

# Part 0. 문제를 한 문장으로

rango(1.3B)가 증명 한 스텝을 만들 때 `apply unsigned_repr; exact H1.` 같은 걸 생성해야 하는데,
**재료(lemma `unsigned_repr`는 [PREMISES]에 있고, 가설 `H1`은 goal에 있음)는 다 있는데 "이 둘을 결합"을 못 한다.**
증거: gold lemma를 직접 손에 쥐여줘도 top-1 정답률이 8%→10%(+2pp)밖에 안 오름 = **정보 부족이 아니라 조립 능력 부족.**

---

# Part 1. 왜 지금 학습으론 조립이 안 느나 (핵심)

## 지금 학습 방식 = "전체 증명 성공했나"로만 보상
```
rango가 정리 하나를 8번 시도(롤아웃) → 각 시도가 Qed까지 갔나(성공1/실패0)
→ GRPO가 "성공한 시도의 모든 tactic 확률↑, 실패한 시도 확률↓"
```
**문제 2가지:**
1. **희소보상(sparse)**: 65%의 정리는 8번 다 실패(dead) → 보상 0 → **학습 신호 아예 없음.**
   그 실패 시도 안에 "올바른 조립 스텝 3개 + 틀린 스텝 1개"가 있어도, 전체가 실패라 **좋은 조립도 벌점**받음.
2. **credit이 뭉개짐(coarse)**: "전체 증명 성공"은 어느 스텝의 조립이 좋았는지 안 알려줌.
   → 모델은 "이 apply가 옳았다"를 스텝 단위로 못 배움.

## 즉 벽 = "조립 스텝 단위 신호가 없음"
전체 성공/실패(outcome)로만 배우니, **한 스텝의 조립이 맞았는지**를 직접 못 배운다.

---

# Part 2. 고치는 3가지 방법 (쉬운 순)

## 방법 A ⭐⭐⭐ — 조립 스텝마다 보상 주기 (dense/process reward)

### 아이디어 (한 줄)
전체 증명 성공이 아니라, **"이 한 스텝(apply)이 goal을 진전시켰나"**를 coq-lsp가 판정해서 스텝마다 보상.

### 왜 조립에 좋나
- dead 정리(전체 실패)여도, **그 안의 "goal을 진전시킨 apply"는 +보상** → 좋은 조립을 살림.
- "이 apply가 productive했나"를 스텝 단위로 배움 = **조립을 직접 학습.**

### coq-lsp가 주는 공짜 신호 (이미 롤아웃에 기록됨)
각 스텝의 `result` 필드:
- `COMPLETE` = 이 tactic이 증명 끝냄 (최고)
- `VALID` = goal이 바뀜(진전) — 근데 **VALID도 두 종류**:
  - **productive VALID**: goal이 진짜 단순해짐/subgoal 닫힘 → 좋은 조립
  - **non-productive VALID**: 붙긴 붙는데(simpl/auto) 앞으로 안 감 → 헛수고
- `INVALID` = coq이 거부 (조립 실패)

**핵심**: 지금은 "VALID면 다 같은 대접"인데, **"productive VALID(진전) vs non-productive(제자리)"를 구별**해서 보상을 주면 조립을 배운다.

### productive를 어떻게 판정 (verifier 공짜 라벨)
스텝 후 goal 상태(`state_key`)를 비교:
```
productive = (subgoal 수 줄었나) or (goal 크기 줄었나) or (COMPLETE로 향했나)
```
- 롤아웃이 이미 `state_key`(goal 상태) 기록 → **다음 스텝 state_key와 비교**하면 진전 측정 가능.
- 이게 논문 arXiv:2606.20068의 핵심(Lean elaborator를 process 오라클로) = **우린 coq-lsp로 동일하게.**

### 구현 (기존 인프라 확장)
- `grpo_train --process` 가 이미 있음. 근데 현재는 "에러(-0.10) vs 유효-미완(-0.05)" 단순 구분.
- **강화**: `result`+`state_key 진전`으로 per-step advantage:
  ```
  COMPLETE: +1.0
  productive VALID(subgoal↓ or goal크기↓): +0.3
  non-productive VALID(제자리): 0.0
  INVALID: -0.1
  ```
- 롤아웃 스텝에 `state_key` 있으니 **재수집 없이** grpo_train의 flatten_group에서 계산 가능.
- GRPO라 critic 불필요 → 1.3B single-GPU OK.

### 정직한 리스크
- 기존 `--process`도 outcome(전체성공)을 못 넘었음. → **productive 판정을 정교하게**(단순 VALID 구분 말고 진짜 진전) 해야 다름.
- productive라도 "막다른 진전"(진전은 했으나 결국 못 풂)이 있음 → 완벽한 신호 아님.

---

## 방법 B ⭐⭐ — "왜 이 조립인지" 근거를 먼저 생성 (rationale, Lean-STaR식)

### 아이디어 (한 줄)
tactic을 바로 생성하지 말고, **"왜 이 lemma를 이 가설에 쓰는지" 한 줄 설명을 먼저** 생성한 뒤 tactic.

### 지금 vs 제안
```
지금:  [입력] → "apply unsigned_repr; exact H1."   (조립을 한 방에)
제안:  [입력] → "H1은 0≤n≤max를 주고, unsigned_repr는 그 조건에서 unsigned(repr n)=n.
                따라서 unsigned_repr를 H1에 적용."       ← 근거(rationale)
              → "apply unsigned_repr; exact H1."         ← tactic
```

### 왜 조립에 좋나
- 근거를 생성하며 **"lemma의 전제 ↔ 가설"을 명시적으로 매칭** → 조립 사고를 언어화 → 학습.
- chain-of-thought처럼, 조립 과정을 중간 단계로 펼쳐 attention이 매칭을 배움.

### 데이터 만들기 (gold에서)
gold `apply L; exact H`가 있을 때, **더 큰 모델(또는 규칙)로 근거를 사후 합성**:
```
입력: goal + gold tactic(apply L; exact H) + L의 시그니처 + H의 타입
출력(근거): "H는 <타입>. L은 <시그니처>. L의 전제가 H와 맞으므로 apply."
```
→ (goal → 근거+tactic) SFT 데이터. 그 다음 rango를 근거→tactic 생성하게 SFT.

### 구현
- 근거 합성: 7B 모델이나 템플릿(L 시그니처+H 타입 파싱해 채움).
- 학습: 기존 SFT(`--sft`)에 target을 "근거\ntactic"으로 바꾸면 됨. **가장 값쌈**(새 인프라 거의 불필요).
- 추론: 근거 먼저 뽑고 tactic (약간 느림, but 조립 정확도↑ 기대).

### 리스크
- 근거가 틀리면(hallucinate) 오히려 방해. 근거 품질이 관건.
- 추론 시 근거 생성이 토큰·시간 추가.

---

## 방법 C ⭐ — 틀린 조립과 대조 학습 (하드-네거티브, novel but 조심)

### 아이디어 (한 줄)
같은 goal에서 **맞는 조립 vs 그럴듯하지만 틀린 조립**을 나란히 주고, 맞는 쪽 확률을 높이게.

### 예
```
goal: unsigned (repr n) = n
positive(gold): apply unsigned_repr        (성공)
negative(hard): apply unsigned_repr_eq     (이름 비슷·타입 비슷, 근데 결론 안 맞음 → INVALID)
→ decoder가 positive에 높은 확률, negative에 낮은 확률
```

### 왜 조립에 좋나
- "타입은 맞는데 결론이 안 맞는" 미묘한 오답을 구별 → **조립의 정밀도** 예리화.
- 재료 대조: 같은 재료로 맞는/틀린 조립을 보여줘 "차이"를 배움.

### ★ 왜 예전 DPO는 실패했나 (unique-solve 0) — 반드시 고칠 것
- 예전 DPO = **아무 오답이나** negative로 씀 → 너무 쉬워서 gradient 무의미(2502.18532 CuDIP가 지적).
- **고칠 2가지**:
  1. **하드-네거티브**: 아무 오답 말고 **타입-호환·이름유사·retrieval 상위**인 그럴듯한 오답(coq-lsp가 INVALID 판정한 것).
  2. **커리큘럼**: 쉬운 정리→어려운 정리 순.

### 구현
- hard-neg 만들기: 각 gold apply의 goal에서 retrieval 상위 lemma 중 **적용하면 INVALID인 것** = 그럴듯한 오답.
- 학습: `--dpo`(인프라 있음) + hard-neg 데이터 + 커리큘럼 순.

### 리스크
- DPO 계열은 process-reward(방법A)보다 약한 베팅(과거 실패 이력).
- decoder측 조립 대조는 **아무도 안 함(novel)** — 잘 되면 기여, 안 될 위험도.

---

# Part 3. 정직한 회의 (미리 알 것)

- **조립을 잘해도 test 성능 전이는 별개일 수 있음.** 이미 시도한 것들(DPO unique-0, process도 outcome 못넘음, EI≤37%)이 경고.
- **벽이 조립이 아니라 "조립 위 도달성(navigation, 여러 스텝 앞 계획)"**일 수 있음(§10). 한 스텝 조립을 완벽히 해도 증명 전체 경로는 별개.
- **단**: CREME(arXiv:2402.14328)이 "조립은 학습가능한 국소 회로"라 하고, 우린 **조립특화 dense objective를 아직 안 해봄** → 시도가치 있음. novelty도 확실(조립특화 decoder objective 논문 없음).

# Part 4. 추천 실행 순서

| 순 | 방법 | 이유 | 비용 |
|---|---|---|---|
| 1 | **A. 조립 dense reward** | verifier 공짜라벨, dead도 신호, critic-free 1.3B | 중(process 강화) |
| 2 | **B. rationale** | 가장 값쌈(SFT target만 변경) | 저(근거합성 필요) |
| 3 | **C. 하드-네거티브** | novel, but DPO 약함·과거실패 | 중(hard-neg 채굴) |

**먼저 A를 프로토타입**(productive-VALID 판정 → per-step advantage → GRPO). CPU로 먼저 "gold에서 productive step이 얼마나 깨끗이 판정되나" 측정 가능.

# Part 5. 지금 CPU로 검증 가능한 것 (학습 전)
- 방법A: 롤아웃의 `state_key` 연속 비교 → "productive VALID vs non-productive"가 실제 구별되나, dead 정리에 productive step이 얼마나 있나.
- 방법C: gold apply의 goal에서 hard-neg(type-호환 INVALID lemma)가 실제로 뽑히나.
→ 이게 되면 방법이 실현가능. GPU 학습은 tst1000tr5091 완료 후.

관련: [[COMPOSITION_TRAINING_RESEARCH]](논문) · [[rango_augmented/COMPOSITION_IS_THE_WALL]](왜 조립이벽) · [[SUBGOAL_PAPER_ASSESSMENT]] §10(도달성) · [[rango_augmented/DECIDER_DEEP_DIVE]](B2=재료있음)
