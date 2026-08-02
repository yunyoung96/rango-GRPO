# decider 주입 심층분석 — 근본까지 (2026-08-02)

질문: decider는 goal당 몇 개 나오나? 랭킹 필요한가? 어떻게 주입해야 하나?
**결론: decider 인덱스 조회가 실제 유효한 건 compound의 12%뿐. 62%는 goal 스캔(Mode1), 26%는 capacity 벽.**
스크립트: 아래 측정들. CPU. n=1066~4000 gold.

## 0. ⚠️ 이전 "79% 커버"의 정정 (중요)
- 앞 [[NOTATION_AND_COVERAGE]]의 "조회 base매칭 79%"는 **역방향 측정**(gold decider를 알 때 "그 base가 goal에 있나")이었음.
- **실제 주입(정방향: goal만 보고 뭘 넣을지)은 다름.** goal head→decider 조회는 goal당 평균 2개, gold 커버 **1%**.
- → **79%는 주입에 못 쓰는 아티팩트.** decider 주입은 생각보다 훨씬 어려움. 이 문서가 그 진짜 구조.

## 1. decider 조회하면 몇 개 나오나 (goal당)
| 조회 방식 | goal당 개수 | 문제 |
|---|---|---|
| 느슨(결론 모든 식별자→decider) | **평균 89개** (86% goal이 15개↑) | 노이즈 범벅(`x:EqDec`,`x:K_dec_set` 변수 포괄매칭) |
| 정방향 엄격(함수head→decider) | 평균 2개 | gold 1%밖에 못 잡음 |

→ **랭킹+캡 필수**(느슨은 89개라 터짐). 단 랭킹만으론 gold가 잘림(3~5%). **개수가 많은 이유 자체가 노이즈.**

## 2. ★ compound destruct 완전분해 (n=1066)
gold 예시 뜯어보니 근본이 두 부류:
```
compound destruct 100%
├─ 부류A (62%) — destruct 표현식이 goal의 if/match/부분식에 이미 존재
│    예: `destruct (if ident_eq id id0 ...)` — 결론에 `if ident_eq id id0 then` 그대로 있음
│    → Mode1(goal 스캔)으로 추출. ★decider 조회 불필요.
│
└─ 부류B (38%) — goal에 표현식 없음, 진짜 조회 필요
     ├─ B1 진짜 decider (12% 전체) — Req_dec, Rle_or_lt, zle, zlt, compare_spec, eq_dec
     │    → decider 인덱스로 잡힘. ★여기가 유일하게 인덱스 필요.
     └─ B2 도메인 완결성 lemma (26% 전체) — mag, classic, andb_prop, ZofB_range,
          parmove_initial_reg_or_temp, generic_format_EM
          → decider 아님. lemma-selection = capacity 벽. 인덱스로 못 잡음.
```

## 3. 핵심 결론
**decider "인덱스 조회"가 실제 기여하는 건 전체 compound의 12%(부류B1)뿐.**
| 부류 | 비율 | 해결 |
|---|---|---|
| A: goal 스캔 | **62%** | Mode1 (if/match scrutinee 추출). `_targeted_cands`의 ②가 이미 함 |
| B1: decider 조회 | **12%** | 소수 흔한 decider (Z→zle/zlt/zeq, R→Rle_or_lt/Req_dec, eq_dec류) |
| B2: 도메인 lemma | **26%** | 못 잡음 (capacity/도달성, 학습이 담당) |

## 4. 랭킹 필요한가 — 부류별로 다름
- **부류A(62%)**: 랭킹 아님. **goal의 if/match를 순서대로 추출**(goal 위치가 곧 관련도).
- **부류B1(12%)**: decider 조회 대상. 근데 12%라 후보 적음(변수 타입 몇 개) → **랭킹보다 강한 필터**(변수 포괄매칭 `x:EqDec` 제거)가 핵심.
- **89개 인덱스 조회 + 랭킹은 과설계**: 실익 12%에 노이즈 리스크만 큼.

## 5. ★ 권장 구현 (89개 인덱스 대신)
decider 전용 무거운 인덱스+랭킹 접근 **비권장**. 대신:
1. **부류A(62%)**: goal의 `if E then`/`match E with`에서 E 추출 → `destruct (E)` 후보.
   (기존 `_targeted_cands` ② scrutinee가 이미 구현 — [[../opener/COMPOUND_CANDIDATES]])
2. **부류B1(12%)**: 변수 타입 → **소수 하드코딩 결정절차**만.
   Z→[zeq,zlt,zle], R→[Rle_or_lt,Req_dec,Rlt_le_dec], positive→[peq], nat→[eq_dec,le_lt_dec], eq_dec류.
   (89개 인덱스 불필요. 기존 `_targeted_cands` ③ _DEC_* 테이블이 이미 이것)
3. **부류B2(26%)**: 포기. capacity 벽(oracle +2pp). 학습/도달성 영역.

**즉 [DECIDERS] 전용 프롬프트 섹션 자체가 실익 작음.** 이미 `_targeted_cands`(②scrutinee + ③결정절차 테이블)가 부류A+B1을 커버. 새 인덱스·랭킹 안 만들어도 됨.

## 5b. ★ 프로젝트-독립성 (사용자 지적: B1 하드코딩은 CompCert 특정)
B1의 ③ _DEC_* 테이블(Z→zle, R→Rle_or_lt)은 **CompCert/stdlib 특정 → 다른 프로젝트 전이 안 됨.** 하드코딩 없는 대안 검증:
| 부류 | 비율 | 프로젝트-독립 방법 | 상한 |
|---|---|---|---|
| **A: goal 스캔** | **62%** | ✅ **완전 독립**(goal의 if/match 추출, 텍스트만) | 62% |
| B1a: decider+인자타입 goal에 | 7% | ⚠️ 타입→sumbool decider **자동인덱스**(코퍼스 `{_}+{_}` 추출) — 원리상 독립. 단 정규식파싱 약해 실측 1~4%(AST면 7%) | ~7% |
| B1b: 인자타입 goal에 없음 | 2% | ❌ 표현 문제(타입정보 부족) | — |
| B2: 도메인 lemma | 29% | ❌ capacity(mag,classic,ZofB_range) | — |

**결론**: 프로젝트-독립 주력 = **부류A(62%)**. 하드코딩 없이 goal 스캔만으로. B1은 자동인덱스(타입→sumbool)로 원리상 독립이나 상한 7%(AST 필요). **B1 하드코딩 테이블은 전이성 위해 자동인덱스로 대체 권장**(단 이득 7%로 작음).

## 5c. ★ B1/B2 재료가 어디에 있나 (2026-08-02, 후속측정)
"compound 후보를 뽑고 싶다"의 진짜 대상 = premise/proof retrieval로 안 잡히는 것. 각 부류 재료 위치:

### B1 (결정절차, n=112) — **어디에도 없음(생성 필요)**
| 위치 | 비율 |
|---|---|
| 가설에 있음 | **0%** |
| premise retrieval에 있음 | 9% |
| **둘 다 없음(순수 생성/조회)** | **91%** |
→ B1 decider(`Rle_or_lt`,`zeq`,`eq_dec`)는 goal·가설·premise 어디에도 없음. **모델이 "여기서 0과 x를 비교하자"고 스스로 떠올려 생성**해야. decider는 "사실(fact)"이 아니라 "결정 연산"이라 텍스트에 안 적힘. → **이게 "compound 후보 뽑기"의 진짜 대상**(retrieval 못 잡음). 단 자동생성 상한 1~7%.

### B2 (도메인 lemma, n=288) — **재료는 있으나 조합을 못 함**
| 요소 | 위치 |
|---|---|
| **인자**(te,e,v,H,H') | **가설에 79%**(전부 가설 41%) |
| **lemma head**(type_instr_complete 등) | **premise retrieval에 54%**, 가설 6% |
→ B2 = `destruct (lemma 가설)` = **retrieval된 lemma를 가설에 apply**. 예: `Zle_lt_or_eq _ _ H'` = premise의 Zle_lt_or_eq를 가설 H'(≤사실)에 적용. **재료(가설+premise)가 절반쯤 이미 프롬프트에 있음.** 못 하는 이유 = "정보 없어서"가 아니라 **"있는 재료를 조합(lemma선택+가설매칭+apply)할 능력이 없어서"** = capacity 벽(oracle +2pp).

### 종합: 세 부류의 근본 차이
| 부류 | destruct 대상 | 재료 위치 | 벽 |
|---|---|---|---|
| A (62%) | goal의 if/match | **goal에 통째로** | 없음(복사) |
| B1 (12%) | 결정절차 | **어디에도 없음(91%)** | 생성(타입→decider, 상한 낮음) |
| B2 (26%) | lemma를 가설에 apply | **가설79%+premise54%** | **조합/선택(capacity)** |

**→ B2는 정보문제 아님(재료 있음). 조합 사고력 문제.** [[COMPOSITION_IS_THE_WALL]] 참조.

## 6. 함의 (rango-augmented 방향)
- **decider는 [TYPES]만큼 명확한 이득이 없음.** [TYPES]는 goal당 3개·커버 87~100%·노이즈0. decider는 goal당 89개(노이즈)·순수조회 커버 12%.
- 굳이 넣는다면 **프롬프트 섹션이 아니라, `_targeted_cands` 후보를 rollout에서 시도**하는 기존 방식이 맞음(opener/subgoal이 이미 함).
- **결론: 2차에서도 [DECIDERS] 프롬프트 섹션은 낮은 우선순위.** 재랭킹+[TYPES](1차)가 실익 큼. decider는 `_targeted_cands` 후보시도(비-프롬프트)로 충분.

관련: [[NOTATION_AND_COVERAGE]] · [[PHASE2_DECIDER_GUIDE]] · [[../opener/COMPOUND_CANDIDATES]] · [[../opener/DDR_INVESTIGATION_SUMMARY]] · [[INDEX_VS_PROMPT]]
