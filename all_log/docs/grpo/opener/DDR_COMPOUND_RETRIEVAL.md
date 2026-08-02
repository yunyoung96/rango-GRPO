# DDR — Decidability-Directed Retrieval (compound 생성 재료 추출)

작성 2026-08-02. **올바른 compound `destruct (DECIDER 인자들)`을 만들기 위한 재료를 추출하는 새 retrieval 설계.**
근거: [[COMPOUND_CANDIDATES]] §compound 커버리지 실측 — 기존 방법은 compound의 ~20%만 커버.

## 문제 재정의 (측정으로 확정)

compound destruct를 만들려면 **재료 2개**: (1) **decider**, (2) **인자**.

측정 결과 (gold, goldsft_bs2, n=59 — 아래 프로토타입서 확정):
- **전체 방법(`_targeted_cands` ①~⑤) 커버 = 59%**(초기 "21%"는 as절 비교 버그, 정정).
- destruct 대상 두 갈래: **~68%는 goal에 이미 있는 함수적용 부분식**(직접 추출 가능), 나머지는 goal에 없는 **decider/spec lemma**(타입/술어/연산으로 조회해야 하나 **notation이 가려 텍스트론 어려움**).
- decider가 **retrieve된 premise에 lemma명으로 있는 건 9%**(42% 부재). content-retrieval이 decider를 못 잡음.

**핵심 통찰: (1) destruct 대상 부분식은 대개 goal 안에 있으나 기존 추출이 `match/if`만 봐서 일부 놓침 → 부분식 전수추출로 68%. (2) goal에 없는 decider는 구조적 대상이나, pretty-print goal은 notation이 연산을 가려 텍스트 조회가 약함(Mode2 15%) → 표현(desugar/타입/AST) 없이는 한계.** DDR union 69%(기준선 +10pp), 이득 대부분이 (1).

## 설계

기존 retrieval = lemma **문장 어휘**를 색인 → goal 어휘 유사도로 질의.
**DDR** = lemma가 **결정하는 대상**(타입/술어/연산)을 색인 → goal의 **타입·Prop·연산 head**로 질의.

### 재료 추출 3계열 (goal에서 case-split 지점 뽑기)

| 계열 | goal에서 뽑는 것 | 찾을 decider | 인자 |
|---|---|---|---|
| **A. 타입 등호/순서** | 같은 타입 T의 항 2개(변수 or 부분식) | `{x=y}+{x≠y}` / 순서 decider | 그 두 항 |
| **B. 술어(Prop)** | goal의 `P a b …`(Prop 반환) | `{P a b}+{~P a b}`(`_dec`) | P의 인자들 |
| **C. 연산(bool/cmp)** | goal의 `f a b`(bool/comparison 반환) | `f`의 spec lemma(`_spec`) | f의 인자들 |

### "새 retrieval" = decidability 인덱스 (오프라인 사전구축)
라이브러리 전체 스캔 → 반환형이 `{_}+{_}`(sumbool)이거나 이름이 `*_dec`/`*eq_dec`/`*_spec`/reflection인 것 수집 → 각각의 **결정 대상**(타입 T, 술어 head P, 연산 head f)을 파싱해 맵 구축:
```
index = { 타입T → [T.eq_dec, 순서decider...],
          술어head P → [P_dec...],
          연산head f → [f_spec...] }
```
인퍼런스: goal에서 (a) 항의 타입, (b) Prop-적용 head, (c) bool/cmp-적용 head 추출 → 인덱스 조회 → decider + 인자.

---

## 예시 (기존 retrieval 못 찾음 → DDR 찾음)

**예1 — `destruct (Ptrofs.eq_dec ofs1 ofs2)`** [A]
- goal: `ofs1, ofs2 : ptrofs`.
- 기존: `Ptrofs.eq_dec`(타입-제네릭 등호 decider)는 goal 어휘와 안 겹침 → **못 찾음**.
- DDR: 타입 `ptrofs` → 인덱스[ptrofs 등호] = `Ptrofs.eq_dec` → 인자 ofs1,ofs2 → `destruct (Ptrofs.eq_dec ofs1 ofs2)` ✓

**예2 — `destruct (range_perm_dec m b lo hi Cur Writable)`** [B]
- goal: `range_perm m b lo hi Cur Writable` 등장.
- 기존: `range_perm`에 관한 lemma는 나와도 decider `range_perm_dec`는 랭킹 밖/부재.
- DDR: Prop-적용 `range_perm …` head → 인덱스[술어 range_perm] = `range_perm_dec` → 인자 그대로 ✓

**예3 — `destruct (Pos.compare_spec v0 v1)`** [C]
- goal: `Pos.compare v0 v1` 또는 `(v0 ?= v1)%positive`.
- 기존: stdlib 반영 lemma `Pos.compare_spec` 못 찾음(실측 미커버 목록에 있었음).
- DDR: 연산 `Pos.compare` head → 인덱스[Pos.compare] = `Pos.compare_spec` → 인자 v0,v1 ✓

**예4 — `destruct (eq_block b1 b2)`** [A]
- goal: `b1, b2 : block`.
- 기존: `eq_block` 어휘 안 겹침 → 못 찾음.
- DDR: 타입 `block` → `eq_block` → `destruct (eq_block b1 b2)` ✓

**예5 — `destruct (Loc.diff_dec l1 l2)`** [B]
- goal: `Loc.diff l1 l2`(위치 disjoint Prop).
- 기존: decider 부재.
- DDR: 술어 `Loc.diff` → `Loc.diff_dec` ✓

**예6 — `destruct (zlt (Int.unsigned n) (Int.unsigned m))`** [A, **인자가 복합식**]
- 기존 `_targeted_cands`: `zlt`는 테이블에 있지만 **첫 두 Z변수**로 채움 → `zlt n m`(틀림). gold는 `Int.unsigned n/m`.
- DDR: goal의 **Z-타입 부분식**(`Int.unsigned n`, `Int.unsigned m`) 추출 → 인자로 → 정답 ✓ (인자를 "변수"가 아니라 "goal의 타입-맞는 부분식"으로 확장한 게 핵심)

**예7 — `destruct (valid_access_dec m chunk b ofs Writable)`** [B]
- goal: `valid_access m chunk b ofs Writable`.
- DDR: 술어 `valid_access` → `valid_access_dec` → 인자 그대로 ✓

**예8 — `destruct (Z.ltb_spec x y)` / `Int.eq …`** [C]
- goal: `x <? y`(`Z.ltb x y`) / `Int.eq i j`.
- 기존: `Z.ltb_spec`(136회·미커버 1위) 부재.
- DDR: 연산 `Z.ltb`/`Int.eq` → spec 인덱스 → `Z.ltb_spec x y` / `Int.eq_spec i j` ✓

## 기존 retrieval vs DDR (요약)
| | 기존(BM25/TF-IDF) | **DDR** |
|---|---|---|
| 색인 키 | lemma 문장 어휘 | lemma가 결정하는 타입/술어/연산 |
| 질의 | goal 어휘 유사도 | goal의 타입·Prop·연산 head |
| 잡는 것 | 어휘 겹치는 rewrite/apply lemma | decider(eq_dec/_dec/_spec) — 어휘 안 겹쳐도 |
| 인자 | (안 함) | goal의 타입-맞는 항/부분식 |

## 구축 방법 (구체)
1. **오프라인 인덱스**: 라이브러리 lemma/def 스캔 → sumbool 반환 or `*_dec`/`*eq_dec`/`*_spec` 이름 수집 → 결정 대상(타입/술어/연산) 파싱 → `{대상 → decider}` 맵. (한 번; `coq_search`(lm_example.py)로 교차검증)
2. **인퍼런스 추출기**: goal 파싱 → (a) 항 타입, (b) Prop-적용 head, (c) bool/cmp-적용 head → 인덱스 조회 → decider+인자 채움 → `destruct (…)` 후보.
3. coq-lsp 유효성 필터로 거름(기존과 동일).

## 한계 (정직)
- 인자가 goal에 없고 **가설에서 오는** 극소수(`parmove_initial_reg_or_temp _ _ _ A` 류)는 어려움 → 가설의 항도 인자후보에 포함하면 상당수 커버.
- AST 없이 문자열 파싱이면 중첩/개행 놓침 → coq-lsp AST 쓰면 견고.
- **opening 재료 개선**이라 end 성능 벽(닫기/도달·capacity)은 별개일 수 있음(opener 실험들 참조). 단 "compound 생성 재료 추출" 목표엔 정확히 부합.

## ★ 프로토타입 검증 (2026-08-02, CPU-only, n=53 goldsft_bs2)

### 측정 방법 (재현 가능)
- **데이터**: `data/grpo_rollouts/goldsft_bs2.jsonl` — gold 증명의 각 step에 `example.proof_state`(goal)와 `tactic`(gold) 있음.
- **대상 추출**: tactic이 `destruct (E)` 정규식 매칭 & E의 head가 **단순변수 아님**(`[a-z]`,`v\d`,`H\w`,`f`,`g` 등 제외) → gold compound destruct. proof_state 있는 것만 = **n=53**.
- **기준선(21%)**: 각 state에 실제로 `_targeted_cands([proof_state])` 호출 → gold destruct(공백정규화)가 그 후보 리스트에 있나.
- **Mode 1 판정**: gold destruct 대상 `E`가 goal에 등장하나 — (a) `norm(E)`가 `norm(goal)`의 substring, 또는 (b) 관대: head_short가 goal에 있고 **인자 토큰의 ≥60%**가 goal에 등장.
- **Mode 2 판정**: head가 decider 패턴(`_dec$`/`eq_dec$`/`_spec$`/`zeq`/`zlt`/`zle`/`peq`/`plt`/`ple`/`eq_block`/`ident_eq`/`Rle_or_lt`/`Rlt_le_dec`/`_lt_dec`/`_le_dec`) 매칭 & **base**(head에서 접미사 제거 = 술어/연산 이름)가 goal에 등장. (zeq/eq_block류 타입등호는 패턴만으로 인정.)
- **DDR 커버 = Mode1 ∨ Mode2.**
- 실행: `CUDA_VISIBLE_DEVICES=""` (GPU 미사용, 순수 텍스트).
- **한계**: "goal에 등장"을 substring/토큰 매칭으로 근사(AST 아님), decider는 실제 인덱스 대신 **이름 패턴**으로 근사(실제 인덱스면 더 잡거나 덜 잡을 수 있음), n=53 표본. → 방향·규모는 견고(21%↔75%), 절대치는 ±.

**구현**: `scripts/build_decider_index.py`(코퍼스 53387 sentence → decider 505개: type_eq 90/pred_dec 175/op_spec 202 → `data/ddr_index.json`) + `scripts/test_ddr_coverage.py`(실제 인덱스로 측정).

DDR 후보생성 커버리지 실측 (gold, goldsft_bs2, **n=59**):
| 모드 | 커버 |
|---|---|
| 기준선 `_targeted_cands` | **59%** |
| **Mode 1** — destruct 대상이 goal에 등장 → 직접 추출(모든 함수적용 부분식) | **68%** |
| **Mode 2** — **실제** decider 인덱스 조회(타입/술어/연산이 goal에) | **15%** |
| **★ DDR union** | **69%** (기준선 +10pp) |

### ⚠️⚠️ 큰 정정 (2번)
1. **기존 `_targeted_cands`는 21%가 아니라 59%.** 초기 "21%/20%"는 gold의 `as절`을 후보와 비교하다 매칭 실패한 버그. as절 떼면 59%. → **기존 방법이 이미 gold compound 절반 이상 커버.**
2. **DDR union = 69% (75% 아님).** +10pp뿐. 그중 대부분은 Mode 1(부분식 추출 일반화)이고, **"새 retrieval"인 Mode 2는 실제 인덱스로 15%로 약함**(이전 34%는 이름패턴 근사의 과대치).

### ★ Mode 2가 약한 결정적 이유 = notation이 연산을 가림 (표현 한계)
gold `destruct (Pos.compare_spec v0 v1)`인데 goal엔 `Pos.compare`가 아니라 **`(v0 ?= v1)%positive`**(notation). `Z.ltb_spec`←`x <? y`, `Int.eq`←`i == j`. → **pretty-print된 goal 텍스트에 연산 이름이 안 보여** 인덱스 조회 실패.
→ **decider retrieval을 제대로 하려면 goal의 desugar(notation 확장)/타입정보/AST가 필요.** 텍스트만으론 원리적 한계. (→ 표현 문제: [[../REPRESENTATION]] 및 질문(3) MD 참조.)

### 두 모드 (검증으로 확정)
- **Mode 1 (68%, 최대 레버)**: goal의 `f args` 부분식 전부 → `destruct (f args)`. 기존 ②(match/if scrutinee)의 일반화. **이건 즉시 구현가치 있음**(기존 59%에서 부분식 추출만 넓혀도 +9pp).
- **Mode 2 (15%, 약함)**: goal에 없는 decider 인덱스 조회. notation/타입정보 없이는 한계. 표현 개선 없이는 큰 이득 어려움.
- union 69%.

**주의**: 69%는 **후보생성** 상한(gold가 후보에 드나)이지 모델 선택·coq-lsp 유효성·end 성능은 별개. n=59 표본 ±.

관련: [[COMPOUND_CANDIDATES]] · [[CLOSING_FAILURE_ANALYSIS]] · [[RANKING_GOLD_VS_APPLIED]] · [[OPENER_TAC]]
