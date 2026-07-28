# Invertible 분해 기반 subgoal 커리큘럼 — 도달성 보존 분해를 LLM에 가르치기

작성 2026-07-27. 관련: `SUBGOAL_PAPER_ASSESSMENT.md` §10(도달성 진단), `IDEAS.md` ⑩(reachability-aware)·부록A(EI), `MIXED_GROUP_SUMMARY.md`. IDEAS ⑩의 구체화.

---

## 0. 왜 (§10 진단에서 출발)

기존 subgoal(leaf/cascade)은 **gold 분해**에 모델을 갖다 놓고 **"닫기"만** 학습 → 완전체 풀이 중 그 상태에 **83% 미도달**(§10). 병목은 "닫기"가 아니라 **"거기까지 가기(분해·도달)"**.
→ 해법: **모델이 스스로 도달 가능한(reachable) 분해를 생성하도록 가르친다.** 그 분해를 **invertible(안전) 전술**로 만들면 도달성·on-policy 안전성이 구조적으로 보장됨.

**Invertible rule**(증명론): 전제 증명가능 ⟺ 결론 증명가능 → 적용해도 증명가능성 안 잃음 → **백트랙 없이 안전**. canonical·결정적이라 모델이 매번 같은 subgoal에 도달 → **도달성 갭 0**, 자기 생성 → **covariate shift 0**.

---

## 1. CompCert 실측 — 무엇으로 쪼개나 (693 .v, 전술 15만+)

| 분류 | 비중 | 전술 |
|---|---|---|
| strictly-invertible | 19% | intros/split/constructor/subst/injection |
| **case-invertible(타깃선택)** | 13% | **destruct/induction/inversion/case** |
| 비-invertible(선택) | 30% | apply/rewrite/exists/left/right |
| 자동닫기 | 22% | auto/eauto/omega/lia |
| 기타(변형) | 13% | simpl/unfold/assert |

> **모수 주의**: %의 분모 = **내가 센 전술 세트(~26개)의 총 등장 횟수(≈15만)**, *증명 step 수도 전체 전술도 아님.* 리스트 밖 전술(reflexivity·discriminate·커스텀 Ltac 등) 제외, **등장 횟수**로 셈(닫기 전술이 여기저기 많아 비중 부풀 수 있음), regex라 `inv`/`case`/`left`/`right`가 변수명에 오매칭 가능. → "대략 분포"로만. 정확한 분해 census는 §4.5(정리 260 단위).

**해석**: raw 빈도는 apply/auto/rewrite가 높지만 **이건 "쪼개기"가 아니라 조각 내부 추론·닫기.** 실제 **분해(branching)를 만드는 건 invertible 계열**(destruct 8%·inv 3%·split 3%·constructor 3%·induction 1%). **`inversion`이 CompCert 핵심 분해기**(step 관계·typing 판정). → **CompCert의 쪼개기 구조는 invertible로 대부분 커버 가능.**

---

## 2. 분해 연산자 생성 — 많이·다양하게·다 커버 (타입 지향 열거)

**연산자 패밀리:**
- **strict(항상 포화)**: `intros`·`split`·`constructor`/`econstructor`(유일 ctor)·`subst`·`injection`.
- **case-invertible(타깃별 1개)**: `destruct t`·`induction t`·**`inversion H`**·`case`.

**타입 지향 열거(type-directed):** goal+context 스캔 → **inductive 타입인 모든 변수/가설/부분항**마다 연산자 1개 생성.
- 후보원 = CompCert 타입 전부: `val`(Vint/Vptr/…)·`memval`·AST(`instruction`/`expr`/`stmt`)·`list`/`option`·`Z`/`positive`/`nat`·**step/typing 관계**(→inversion).
- **다양성** = {타깃 집합} × {destruct/induction/inversion} × 재귀 깊이.
- **커버리지** = 모든 inductive 위치 열거 → CompCert가 칠 수 있는 구조적 split 원리상 포함. (검증: CompCert 실측 타깃을 생성기가 재현하나 측정 — TODO.)

**invertible이 못 덮는 것(정직)**: `apply lemma`(가설→subgoal, lemma 선택=non-invertible)·`exists witness`. → "쪼개기"가 아니라 도메인 추론 → **모델 + Rango retrieval + 검색** 몫. 이 분업이 곧 도달성 안전 커리큘럼.

**폭발 제어**: goal-관련 타깃 우선·재귀타입 우선(IH)·CompCert 빈도 우선·결과 state 중복제거(state_key)·깊이 제한·열거 아닌 탐색.

---

## 3. ★ LLM에게 "쪼개는 방식"을 가르치기 (핵심)

**전제**: next-tactic 세팅에서 **분해 tactic이 곧 tactic** → 쪼개기 학습 = "어떤 state에서 어떤 분해 tactic(+타깃)을 낼지" 학습. 기존은 subgoal에 갖다 놓고 **닫기만** 가르쳐 분해 스텝이 데이터에 없었음 → **이번엔 분해 tactic을 포함한 full 궤적**으로.

### 데이터 생성
1. invertible 분해 탐색으로 **모든 leaf가 닫히는 full 증명트리** 발견(Coq 검증).
2. **(state, next-tactic) 쌍으로 선형화** — **분해 스텝(`induction n`·`inversion H`…)을 포함.**
3. → 학습데이터. 분해 tactic이 궤적 안에 살아있음.

### 학습 방식
**(a) full-궤적 RFT/EI (암묵적)**: 성공 full 증명 SFT/RFT → 분해를 next-tactic으로 흡수. 단순, 단 분해 스텝 소수라 신호 약함.

**(b) 분해-집중 (step-level 보상) — 진짜 "쪼개는 법":**
- 분해 지점에서 **여러 후보 분해 샘플**(`destruct x` vs `induction y` vs `inversion H`) → 각각 나머지 롤아웃 → **모든 subgoal 닫히면 reward=1** → group-relative advantage로 **"어느 split이 통하는지" 학습.** = 분해 결정에 대한 **process-level GRPO**(Tree-GRPO/VinePPO 계열).
- invertible이라 **어떤 split도 valid(안전)** → 학습 대상 = "valid"가 아니라 **"닫기 쉬운(useful) split"**. 보상이 그걸 포착.

**(c) 분업 (harness + 학습 분리) — 고전(Isabelle safe/aesop):**
- **strictly-invertible**: harness가 **자동 포화** → 모델 안 배워도 됨(궤적 단축).
- **case-invertible 타깃 선택**: **모델 학습**(= 쪼개기 핵심).
- **non-invertible**: 모델 + retrieval + 검색.

### 왜 §10을 고치나
- full 궤적(분해+닫기)을 **reachable state** 위에서 **자기 탐색(on-policy)** 데이터로 학습 → **covariate shift 0, 도달성 갭 0.**
- 모델이 **"거기까지 가는 법(분해)"을 처음으로 학습** — 기존이 못 하던 절반.

---

## 4. 후보군 & 추천

| # | 방법 | 도달성 | novelty |
|---|---|---|---|
| A | RFT↔GRPO 반복(EI, 자기성공 full 증명) | ✓ | 낮음 |
| B | **invertible 포화 분해** → 선택지만 탐색 | ✓✓ canonical | 중~높음 |
| C | 휴리스틱 분해 탐색(kSubS/AdaSubS식) | ✓ | 중 |
| D | lemma-cut/have-search(DS-Prover-V2/DSP식) | 부분 | 중 |
| **E** | **하이브리드(추천)**: B(invertible 뼈대)+C/D(선택·cut 탐색)+분해-집중 GRPO(3-b)+EI(A) | **✓✓** | **높음** |

**추천 E**: invertible로 **도달가능 canonical 뼈대** 생성(§10 갭 제거) → 남는 선택·cut은 검색/retrieval → **성공 분해를 full 궤적으로 RFT + 분해-집중 GRPO**로 "쪼개는 법" 학습 → EI로 반복. **도달성 안전 + on-policy + 신규성** 동시.

**신규성 포인트**: §10(gold subgoal이 도달성으로 실패)을 **invertible-rule 포화로 도달성 보존 subgoal 커리큘럼**을 만들어 정면 해결 + **분해 정책 자체를 process-GRPO로 학습**. Coq/verifier 하에서 이 프레이밍은 선례 약함.

---

## 4.5 실측 — 300 train gold 증명의 invertible 커버리지 (2026-07-27)

`gold_bs2.json`의 260개(=300 train 중 gold 있는 것) gold 증명을 정적 분류.

| | 정리 수 | 비중 |
|---|---|---|
| ✅ **invertible+closer만으로 커버**(gold에 apply/rewrite/exists 등 없음) | 55/260 | **21%** |
| └ 분해도 불필요, closer 한방(auto/intuition/now) | 5 | 1% |
| ❌ **non-invertible 필요** | 205/260 | **78%** |

**걸림돌 tactic**(등장 정리수): apply 49% · rewrite 40% · eapply 19% · exists/generalize/assert 각 7%. 증명 길이 median 8 step(p90 21).

**해석(기대치 보정):**
- **순수 invertible+auto로 끝나는 train 정리는 ~21%뿐** — CompCert는 apply(도메인 lemma)·rewrite가 지배 → **invertible 단독은 standalone prover 아님**(21% < baseline 33.5%).
- 단 이건 *full 증명* 커버; **분해 골격은 별개**: 78%도 intros/destruct/inversion으로 **분해는 되고**, apply/rewrite는 **각 leaf의 도메인 추론(모델+retrieval 몫)**.
- → **invertible의 역할 = "많이 푼다"가 아니라 reachable canonical 분해 골격**으로 모델이 apply/rewrite를 **도달가능한 state에서** 배우게 함(§10 정면). 21%는 공짜 보너스.
- 분류 가정: `induction`을 invertible군에 포함(완전분기, 단 변수선택 있음), `assert`/`replace`는 non-inv(lemma-cut). 이는 **정적(gold 증명 스타일)** 측정 — 동적(invertible+hammer가 *실제로* 닫는가)은 별개(아래 액션 1').

## 4.6 실측 — 동적 invertible 롤아웃 (generic vs targeted, 2026-07-27)

정적(§4.5, gold 스타일) 말고 **실제 실행**: invertible 스크립트를 Coq에 적용 → cascade-s0+retrieval이 닫나. (상세 알고리즘: `INVERTIBLE_EI_ALGORITHM.md`)

| 방식 | 유효분해(실제 쪼갬) | 모델 closure(reward>0) |
|---|---|---|
| **generic**(intros/split/destruct-hyps) | **≈0%** (CompCert goal이 ∧/∃ 아님) | 0/6 |
| **targeted**(가설별 destruct/induction/inversion, 17정리·78후보) | **62/78 = 79%** | **3/78 = 3%** ⚠ |

**재귀 하이브리드 A/B (2026-07-28, 완전체 34정리):** cascade가 각 스텝에 invertible-포화+auto 주입 + targeted 후보 검색 → **plain cascade 2/32 vs hybrid 0/23 닫힘.** **하이브리드가 오히려 못 닫음** — auto=CompCert 0%, blanket 변수-destruct/induction이 gold의 유용분해(compound-항) 아니라 엉뚱하게 쪼개 궤적 흐림. → **"invertible로 rollout 뚫어 SFT 데이터 만들기"는 현 구현으론 실패.** compound-항 분해(§4.6 v2) 없이는 안 됨.

**결론:**
- ✅ **targeted invertible은 CompCert를 잘 쪼갬(79%)** — generic(≈0)과 극명한 차이. **"어느 변수/가설에 destruct/induction/inversion"을 열거하면 Coq이 유효분해를 79% 만듦.** (인자 = 탐색 차원, Coq이 무효 필터.)
- ⚠ **그러나 모델이 닫는 건 3%뿐** — 분해된 subgoal도 apply/rewrite 도메인추론 필요, 약한 cascade-s0가 못 함. **분해는 은탄환 아님, closing이 병목.**
- **다음(핵심)**: (a) **분해 + built-in `auto`/`lia`/`intuition` 닫기**(모델만 쓰지 말고) — base case·산술 subgoal 싸게 닫힐 것. (b) **v2 강한 IH**(§2.2 revert;induction). (c) 더 강한 모델.

**⚠ 정정 (gold 대비 실측, 2026-07-27):** "79% 유효분해"는 **과대평가**였음.
- gold 분해 20스텝 중 **변수 대상 10개(내 후보 커버 20%) + compound-항 대상 10개(`destruct (Rle_or_lt 0 x)` 등, 내 변수-전용 열거기가 0% 커버)** → **gold 유용분해의 ~10%만 재현.**
- "valid"의 상당수는 **진짜 split이 아님**(`destruct valid_exp`=record 풀기→goal 1개 그대로). "적용됨 ≠ 의미있게 쪼갬".
- **closure 3%의 진짜 원인**: 변수 destruct는 **엉뚱한 걸 쪼갬** — CompCert 유용분해는 **goal의 "부분항(computed term)에 대한 case 분석"**(`destruct (조건항)`)인데 이건 변수 열거로 안 나옴.
- **v2 핵심 수정**: destruct 대상을 **context 변수가 아니라 goal 부분항(subterm) 열거**로 확장 — 큰 공간이라 **어느 항을 가를지에 retrieval/모델 개입** 필요. (gold `inv`(inversion) 3개도 반영.)

## 5. 다음 액션
1. CompCert 실측 **타깃 커버리지** 측정(destruct/induction/inversion을 *무엇에* 치나 → 생성기가 재현하나).
2. invertible 포화 + 타입지향 열거 **분해기 프로토타입**(harness에 safe-saturation 훅).
3. 소규모 파일럿: 분해기로 dead 정리 몇 개에서 **성공 분해트리** 뽑아 full 궤적 RFT → rand200 확인.
4. 되면 분해-집중 GRPO(3-b) + EI 반복.

**참고문헌**: [DeepSeek-Prover-V2 2504.21801](https://arxiv.org/abs/2504.21801)(have-분해) · [Draft-Sketch-Prove 2210.12283](https://arxiv.org/abs/2210.12283) · [ReST-EM 2312.06585](https://arxiv.org/abs/2312.06585) · aesop(Lean safe rules) · Isabelle `safe`/`clarify`.
