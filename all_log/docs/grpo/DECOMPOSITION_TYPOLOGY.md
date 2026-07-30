# 분해(decomposition) tactic 유형학 — gold 증명 실측 분류

작성 2026-07-30. 데이터: `goldsft_bs2.jsonl` (사람 gold 증명 254개, 의미tactic 1800개) 실측 분류.
목적: "goal/subgoal을 쪼개는 tactic 조합에 유형이 있나" → **있음.** 도입→분해→작업의 문법 + 분해 대상의 3분류.

관련: [[BOTTLENECK_ANALYSIS]](divergence 61%·coverage 22%), [[VFSEARCH_RESULTS]], [[CEILING_ANALYSIS]].

---

## 0. 한 눈에
- **첫 수(opening)의 61%가 INTRO** — 거의 항상 가설 도입으로 시작. 그다음 INDUCTION(13%)/SIMP(12%)/DESTRUCT(5%)로 갈림.
- **DESTRUCT의 52%가 compound(계산항)** = `destruct (계산식)` — **모델이 스스로 잘 못 만드는 유형**(모델 생성 coverage 11%). var 30%, hyp 17%.
  - ★**정정(2026-07-30)**: "모델 생성 11%"를 "열거로도 못 만든다"로 오독했었음. **실측하니 gold destruct 대상의 ~80%는 goal에 그대로 있어 열거로 생성 가능**(§5). 벽은 **coverage(생성 가능성)가 아니라 선택(selection)+도달(reachability)**.
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
| **C1 compound(계산항)** | **52%** | `destruct (Rle_or_lt 0 x)`, `destruct (f a) eqn:E` | **가장 어려움**. 결정절차/match scrutinee. 모델 생성 coverage 11%(스스로 잘 못 냄) — 단 **열거로는 ~80% 생성 가능**(§5). non-invertible + 후보 과다. |
| C2 var(변수) | 30% | `destruct n`, `destruct l` | 얕은 induction. 선택 필요(non-invertible). |
| C3 hyp(가설) | 17% | `destruct H`(H:∧/∨/∃) | **invertible(안전-자동화 가능)**. |

→ **DESTRUCT의 과반이 compound** — "조건을 넣어 쪼개는" 유형. ★**정정**: 이 gold 대상의 **~80%는 열거로 생성 가능**(§5 실측). 즉 [[VFSEARCH_RESULTS]] 0/34의 실패는 **열거 coverage가 벽이어서가 아니라**, ① 선택(같은 goal에서 후보 5~18개 중 gold를 고를 local 신호가 없음) ② 도달(옳게 쪼개도 뒤 subgoal을 못 닫아 그 destruct에 credit을 못 줌) 때문.

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
| **C1. DESTRUCT-compound(52%)** | ⚠ 열거는 ~80% 생성가능 — **선택+도달**이 벽 | **최악**(모델생성 11% / 열거 80%, VFSEARCH 0/34) |
| D. SPLIT-goal | ✅ 대부분 결정적(∧→split) | 부분 자동화 |

→ **분해의 절반 이상(C1 compound + B induction + C2 var)이 "어느 것을 고를지" 선택 문제**. 특히 **C1 compound(전체 DESTRUCT의 52%)**가 진짜 벽인데, ★**정정**: 벽은 "열거로 못 만든다"가 아님 — **열거로는 gold의 ~80%를 만들 수 있음**(§5). 벽은 (i) **선택**: 같은 goal에서 후보가 5~18개인데 어느 것이 gold인지 local 신호가 없음, (ii) **도달**: 옳게 쪼개도 나온 subgoal을 policy가 못 닫아 그 destruct에 보상 credit이 안 감. 반면 INTRO/hyp-destruct(invertible)는 이미 자동화됨(효과 marginal).

**함의**: 성능을 올리려면 **C1(compound destruct)의 선택+도달**을 맞춰야 함 — (a) gold 주입=covariate-shift 실패, (b) 열거+search=VFSEARCH 후퇴(coverage 부족이 아니라 선택·도달·MC예산). APPLY-인자 자동화(A/B)는 이 C1 문제를 **안 건드림**(apply 단계만 회복). 즉 이 유형학은 "왜 apply-자동화의 상한이 있는지"도 설명함.

---

## 5. ★열거(destruct 후보군)는 정확히 어떻게 만들었나 + coverage 재측정
코드: `src/tactic_gen/grpo_rollout.py`의 `_targeted_cands(goals)` (+ `_scrutinees`, `_IND_TYPES`, `_DEC_UN/_DEC_CONST/_DEC_BIN`). 입력은 **현재(첫) goal 텍스트 하나**. 이를 첫 빈 줄 기준으로 `hyp_txt`(가설부)·`goal_txt`(결론부)로 가르고, 아래 4단계로 후보를 모은 뒤 **dedup 후 앞 18개**로 컷. (생성만 하고 유효성은 Coq LSP가 필터 — 무효 후보는 버려짐.)

### 4단계 구성 규칙
| 단계 | 소스 | 규칙 | 만드는 tactic |
|---|---|---|---|
| **① 문맥 변수** | 가설 `name : type` 파싱 | type head가 `_IND_TYPES`에 있거나(∈아래) **대문자로 시작하는 사용자 inductive**(단 `Type/Set/Prop/R/Q/radix` 제외), 그리고 `->`(함수)가 아니면 → 변수 수집. **앞 3개** | `destruct v.`, `induction v.` |
| **② scrutinee** | goal_txt + hyp_txt | `_scrutinees`: `match E with` / `if E then`의 **E**(괄호 balanced, ≤80자, 개행X) 추출. **앞 4개** | `destruct (E).` ← **compound destruct의 핵심 소스** |
| **③ 타입-지향 결정절차** | 가설을 타입 head로 그룹핑 | 하드코딩 템플릿(CompCert 특화). 단항/상수0-비교/두변수-쌍 | `destruct (zeq a 0)` 등(아래 표) |
| **④ 가설 inversion** | 가설 | type에 `=`가 있거나 이름이 `H*`이고 `->`아니면. **앞 2개** | `inversion H.` |

`_IND_TYPES` = {`nat, positive, Z, N, bool, list, option, comparison, ident, block, val, memval, instruction, sumbool, prod`}.

③ 결정절차 템플릿 (타입 head → destruct 후보):
| 타입 | 단항(`_DEC_UN`) | 상수0 비교(`_DEC_CONST`) | 두 변수쌍(`_DEC_BIN`, 같은타입 ≥2개) |
|---|---|---|---|
| Z | — | `zeq a 0`, `zlt a 0`, `zle 0 a` | `zeq a b`, `zlt a b`, `zle a b` |
| R | — | `Rle_or_lt 0 a`, `Rlt_le_dec 0 a` | `Rle_or_lt a b`, `Rlt_le_dec a b` |
| positive/ident | — | — | `peq a b` |
| nat | — | — | `Nat.eq_dec a b`, `le_lt_dec a b` |
| bool/val/option/comparison/sumbool | `destruct a` | — | — |

### Worked example — 이 goal이 들어오면
```
n : nat
z : Z
H : a = b
============================
match Z.compare z 0 with Lt => P z | _ => Q end
```
- **①** dv = [`n`(nat∈_IND), `z`(Z∈_IND)] → `destruct n.` `induction n.` `destruct z.` `induction z.`
- **②** `_scrutinees(goal)` = [`Z.compare z 0`] → `destruct (Z.compare z 0).`
- **③** byty = {nat:[n], Z:[z]}. Z∈`_DEC_CONST` → `destruct (zeq z 0).` `destruct (zlt z 0).` `destruct (zle 0 z).` (nat `_DEC_BIN`은 nat 변수 1개뿐이라 skip)
- **④** pr = [`H`(`=` 포함)] → `inversion H.`
- **최종(9개)**: `destruct n` · `induction n` · `destruct z` · `induction z` · `destruct (Z.compare z 0)` · `destruct (zeq z 0)` · `destruct (zlt z 0)` · `destruct (zle 0 z)` · `inversion H`

gold가 `destruct (Z.compare z 0) eqn:E`였다면 **②가 `destruct (Z.compare z 0)`를 이미 만들었음**(`eqn:E` 라벨만 다름) → **열거 안에 gold가 존재**. 이게 "80% in-goal"의 전형.

### coverage 재측정 (정정의 근거)
`goldsft_bs2.jsonl`에서 **gold가 destruct인 스텝 250개**를 뽑아, 각 스텝의 destruct 대상(변수/식)이 그 시점 goal 텍스트에 문자열로 존재하는지 판정:

| 판정 | 비율 | 의미 | 열거가 잡나? |
|---|---|---|---|
| goal/hyp에 그대로 있음 | **~80%** | 변수·match scrutinee·결정절차 인자 | ✅ ①②③가 생성 |
| 부분적(템플릿 필요) | ~10% | `Rle_or_lt 0 x`처럼 결정절차 wrapping | △ `_DEC_*`에 그 타입 있으면 |
| 위치기반(N번째 등) | ~6% | 텍스트만으론 특정 어려움 | ✕ |
| 진짜 전략도입 | ~2% | 앞선 assert/pose로 생긴 항 | ✕ |

→ **결론: gold destruct의 ~80%는 열거로 생성 가능. coverage(생성 가능성)는 벽이 아니다.** 앞서 "compound가 goal에 안 드러나 열거로 못 만든다"고 한 진단은 **틀렸고**, 실제 벽은 **선택**(같은 goal에서 위 9~18개 후보 중 gold를 고를 local 신호 없음)+**도달**(옳게 쪼개도 subgoal을 못 닫아 그 destruct에 보상 credit이 안 감). VFSEARCH가 이 후보들을 실제로 넣어봤지만 0/34였던 것도 coverage가 아니라 이 둘 + MC 예산 소진 때문.
