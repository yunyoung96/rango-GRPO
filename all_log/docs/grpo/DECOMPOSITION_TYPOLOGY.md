# 분해(decomposition) tactic 유형학 — gold 증명 실측 분류

작성 2026-07-30. 데이터: `goldsft_bs2.jsonl` (사람 gold 증명 254개, 의미tactic 1800개) 실측 분류.
목적: "goal/subgoal을 쪼개는 tactic 조합에 유형이 있나" → **있음.** 도입→분해→작업의 문법 + 분해 대상의 3분류.

관련: [[BOTTLENECK_ANALYSIS]](divergence 61%·coverage 22%), [[VFSEARCH_RESULTS]], [[CEILING_ANALYSIS]].

---

## 0. 한 눈에
- **첫 수(opening)의 61%가 INTRO** — 거의 항상 가설 도입으로 시작. 그다음 INDUCTION(13%)/SIMP(12%)/DESTRUCT(5%)로 갈림.
- **DESTRUCT의 52%가 compound(계산항)** = `destruct (계산식)` — **가장 어렵고 모델이 못 만드는 유형**(coverage 11%). var 30%, hyp 17%.
- 조합은 **"셋업(INTRO→분해) → 작업(REWRITE↔APPLY↔AUTO 사슬)"** 문법을 따름.

---

## 1. 카테고리 분포 (전체 1800 tactic)
| 카테고리 | 비율 | 역할 |
|---|---|---|
| APPLY(lemma) | 19% | lemma 적용(작업) |
| AUTO(자동화) | 14% | auto/lia/ring 마감 |
| **INTRO(도입)** | 14% | ∀/→ 가설 도입 |
| REWRITE | 12% | 등식 치환(작업) |
| **DESTRUCT(케이스분석)** | 11% | 케이스 분할 |
| SIMP(전개/단순화) | 9% | unfold/simpl |
| SPLIT-goal(목표분할) | 6% | ∧/∨/∃/생성자 |
| **INDUCTION(귀납)** | 2% | 구조적 재귀 |
| ASSERT/CUT | 1% | 보조명제 |

→ **분해/네비게이션(INTRO+DESTRUCT+INDUCTION+SPLIT+SIMP) = 42%**, 작업(APPLY+REWRITE+AUTO) = 45%.

---

## 2. ★분해 tactic 5대 유형 (조합 특징)

### A. 도입 우선 (INTRO) — opening 61%
`intros` / `revert` / `generalize`. **거의 모든 증명의 첫 수**. 보통 invertible(선택 여지 없음, 안전-자동화 가능).

### B. 구조적 재귀 (INDUCTION) — opening 13%, 전체 2%
`induction x` / `elim`. **저빈도·고레버리지**(재귀 증명 뼈대). ★**"어느 변수 induction"이 divergence 병목의 핵심**(non-invertible, 선택 필요).

### C. 케이스 분석 (DESTRUCT) — 전체 11% — ★대상 3분류가 핵심
| 하위유형 | 비율 | 예 | 성격 |
|---|---|---|---|
| **C1 compound(계산항)** | **52%** | `destruct (Rle_or_lt 0 x)`, `destruct (f a) eqn:E` | **가장 어려움**. 결정절차/match scrutinee. 모델 coverage 11%(거의 못 생성). non-invertible + 무한 후보공간. |
| C2 var(변수) | 30% | `destruct n`, `destruct l` | 얕은 induction. 선택 필요(non-invertible). |
| C3 hyp(가설) | 17% | `destruct H`(H:∧/∨/∃) | **invertible(안전-자동화 가능)**. |

→ **DESTRUCT의 과반이 compound** — 이게 "조건을 넣어 쪼개는" 유형이고, 열거·search로도 못 뚫린 부분([[VFSEARCH_RESULTS]] 0/34).

### D. 목표 분할 (SPLIT-goal) — 6%
`split`(∧) / `exists`·`eexists`(∃) / `constructor`·`econstructor` / `left`·`right`(∨). goal 구조를 쪼갬. **대개 SPLIT→APPLY**(각 부분 증명).

### E. 전개/단순화 (SIMP) — 9%, opening 12%
`simpl` / `unfold` / `cbn` / `change`. **정의를 펼쳐 구조를 드러냄**. 보통 REWRITE/DESTRUCT 앞에 옴(전처리).

---

## 3. ★조합 문법 (2-gram 실측)
분해 tactic들은 무작위가 아니라 **단계적 문법**을 따름:

```
[셋업]  INTRO ─┬→ SIMP        (41)   정의 펼치기
               ├→ DESTRUCT    (42)   케이스 분할
               └→ APPLY       (41)   바로 lemma
[분할]  SPLIT ──→ APPLY       (38)   각 conjunct/case 증명
[작업]  REWRITE↔APPLY↔AUTO 사슬:
          APPLY→APPLY (107) · REWRITE→REWRITE (53) · REWRITE→APPLY (53)
          REWRITE→AUTO (45) · APPLY→AUTO (61) · AUTO→AUTO (39)
[전처리] SIMP → REWRITE (43)
```

**해석 — 증명의 3-phase 구조:**
1. **셋업(navigation)**: INTRO → {SIMP | DESTRUCT | INDUCTION}. goal을 "작업 가능한 형태"로 만듦.
2. **분할(shaping)**: SPLIT/DESTRUCT/INDUCTION → 여러 subgoal.
3. **작업(closing)**: 각 subgoal을 REWRITE↔APPLY↔AUTO 사슬로 마감.

---

## 4. 병목과의 연결 (왜 이 유형학이 중요한가)
분해 유형을 **자동화 가능 vs 선택 필요**로 가르면 병목이 정확히 보임:

| 유형 | 자동화 가능? | 상태 |
|---|---|---|
| A. INTRO | ✅ 대부분 invertible | 자동화 됨 |
| C3. DESTRUCT-hyp(∧/∨/∃) | ✅ invertible | 자동화 됨(SUBGOAL_HYBRID) |
| B. INDUCTION(어느 변수) | ❌ 선택 필요 | **divergence 병목** |
| C2. DESTRUCT-var | ❌ 선택 필요 | 병목 |
| **C1. DESTRUCT-compound(52%)** | ❌❌ 선택+무한 후보 | **최악**(coverage 11%, VFSEARCH 0/34) |
| D. SPLIT-goal | ✅ 대부분 결정적(∧→split) | 부분 자동화 |

→ **분해의 절반 이상(C1 compound + B induction + C2 var)이 "어느 것을 고를지" 선택 문제**이고, 특히 **C1 compound(전체 DESTRUCT의 52%)가 자동화·열거·search 모두 실패한 진짜 벽**. 반면 INTRO/hyp-destruct(invertible)는 이미 자동화됨(효과 marginal).

**함의**: 성능을 올리려면 **C1(compound destruct) 선택**을 어떻게든 맞춰야 하는데, 이건 (a) gold=covariate-shift 실패, (b) 열거+search=VFSEARCH 후퇴 — 미해결. APPLY-인자 자동화(현재 A/B)는 이 C1 문제를 **안 건드림**(apply 단계만 회복). 즉 이 유형학은 "왜 apply-자동화의 상한이 있는지"도 설명함.
