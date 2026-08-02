# 구조 컨텍스트 주입 ([TYPES]/[SIGNATURES]) — 커버리지 실측 + capacity 가설 검증

작성 2026-08-02. 질문: "(i) [TYPES] 구조 retrieval을 구현해 필요한 후보를 다 커버하나? 이걸 학습하면 capacity(lemma 못 찾는 것)도 풀리나? apply 형식맞추기 전이 문제도?"
근거·연장: [[opener/DDR_COMPOUND_RETRIEVAL]] · [[REPRESENTATION_FOR_TRANSFER]] · [[opener/CLOSING_FAILURE_ANALYSIS]].

## 0. TL;DR
- **재료는 존재한다**(코퍼스 인덱싱, CPU): destruct 타입의 **생성자/연결자 76%**, apply lemma **시그니처 79%**(현 retrieval 62% → **+17pp** 새로 줄 수 있음).
- **하지만 capacity 자동해결은 아니다**: 닫기 실패의 **인자(형식) 오류=0%**, **68% 잘못된 tactic 종류 + 90% 잘못된 lemma 선택**. 즉 벽은 **형식맞추기가 아니라 "무엇을 고를지"(선택)**.
- → [SIGNATURES]는 **선택을 informed하게**(각 후보가 뭘 하는지 보여줌) + **cross-project 전이**(시그니처 읽는 법을 배움)에 유효. 단 **apply 형식 문제는 관측되지 않음**(가설 정정).

## 1. [TYPES]/[SIGNATURES] 구현 & 커버리지 (실측)

### 인덱스 (오프라인, CPU, 코퍼스 53387 sentence)
- `data/ind_constructors.json` — Inductive **776타입 → 생성자 목록** (`comparison→[Ceq,Cne,Clt,Cle,Cgt,Cge]`, `val→[Vundef,Vint,Vlong,Vfloat,Vsingle,Vptr]`...).
- lemma/def **시그니처 36257개** (이름 → statement).
- decider 인덱스 505개([[opener/DDR_COMPOUND_RETRIEVAL]]).

### 커버리지 (gold, goldsft_bs2)
| 재료 | 확보율 | 비고 |
|---|---|---|
| **destruct 타입의 생성자/연결자** | **76%** | 별칭(ident→positive)·notation(`/\`→and,`exists`→ex)·등식 해소 후 (raw 25% → 76%) |
| **apply lemma 시그니처** | **79%** | 코퍼스에 statement 존재 |
| ─ 현재 retrieval(premise)이 주는 것 | 62% | |
| ─ **[SIGNATURES] 주입으로 추가** | **+17pp** | stdlib lemma(`Ropp_0`,`Rmult_1_l`,`eq_add_S`...)가 CompCert retrieval서 누락된 것 |

**→ 답(i): 필요한 후보의 대부분(76~79%)을 [TYPES]/[SIGNATURES]로 커버 가능.** 재료가 코퍼스에 실재. 못 채우는 24%는 record/predicate(`valid_access`,`behavior_improves`)·깊은 라이브러리.

### [STRUCT] 섹션 설계 (기존 프롬프트에 추가)
```
[STATE] <goal>
[SCRIPT] <script>
[TYPES]                     ← 새로: goal 등장 타입의 생성자
  val := Vundef | Vint | Vlong | Vfloat | Vsingle | Vptr
  comparison := Ceq | Cne | Clt | Cle | Cgt | Cge
[DECIDERS]                  ← 새로: goal 타입/연산의 decider (DDR)
  block: eq_block | ptrofs: Ptrofs.eq_dec | Pos.compare: Pos.compare_spec
[SIGNATURES]                ← 새로: 후보 lemma의 forall-시그니처
  Ropp_involutive : forall x, - - x = x
[PROOFS]/[PREMISES] ...      (기존 retrieval)
### Response:
```
= **구조 retrieval**: 대상이 "관련 증명"이 아니라 "goal에 등장한 타입·연산·lemma의 정의·시그니처". CPU 사전색인, 지금 파이프라인에 섹션만 추가.

## 2. "이걸 학습하면 capacity가 풀리나?" — 정직한 검증

### 핵심 반증 데이터: 닫기 실패는 형식이 아니라 선택
[[opener/CLOSING_FAILURE_ANALYSIS]] 실측:
- **apply 인자만 틀림(형식) = 0%** ← 모델은 lemma를 고르면 **형식은 맞춘다**.
- **68% = gold와 다른 tactic 종류**(접근 자체가 다름).
- **90% = gold에 없는 lemma 선택**(있는데 다른 걸 고름).

→ 벽 = **"무엇을 적용할지 선택"**(what), **"어떻게 형식 맞출지"(how)가 아님**.

### 그럼 [SIGNATURES]가 선택을 고칠까?
- **부분적으로 그렇다(전이 각도)**: 지금 모델은 lemma를 **이름의 표층 연상**으로 고름 → 시그니처(무엇을 증명하나)를 안 보니 "이 goal엔 이 lemma"를 **구조적으로** 못 판단, cross-project서 무너짐. 시그니처를 주고 **그걸 읽어 고르게 학습**하면 **일반화되는 선택 능력** 획득 가능.
- **단 만능 아님(경고)**: **oracle 실험** — gold lemma를 직접 줘도 top-1 정답률 8%→10%(+2pp). "올바른 lemma를 알아도" 성능 소폭 → 선택 위에 **다단계 경로(도달성)**가 더 큰 벽. 시그니처 주입도 이 천장에 부딪힐 수 있음.

### 사용자 가설 "생성자 정보 없이 학습해서 조합능력 부족" — 평가
- **일리 있음(전이·구성)**: 생성자/시그니처 구조 없이 텍스트만 배우면 "결정가능 타입→eq_dec", "forall a b, P→Q 시그니처→apply 후 a,b 채움" 같은 **재사용 규칙**을 못 배우고 이름을 외움 → 새 프로젝트서 깨짐. 구조를 주면 이게 개선될 여지.
- **단 데이터가 말하는 주 실패는 "선택(what)"**이지 "조합/형식(how)"이 아님(인자오류 0%). 따라서 구조 주입의 이득은 **"조합을 잘하게"보다 "선택을 구조적으로·전이가능하게"**에서 나올 것.

## 3. apply 형식맞추기 cross-project 문제 — 가설 정정
- 사용자 직관: "apply는 형식맞추기라 다른 프로젝트서 형식 몰라 깨진다."
- **데이터 정정**: apply **인자/형식 오류 ≈ 0%**. 모델은 lemma를 고르면 형식은 맞춤. **깨지는 건 형식이 아니라 "어떤 lemma를 고를지"**(90% 오선택).
- 따라서 [SIGNATURES]의 진짜 값 = **형식교정이 아니라 선택정보 제공 + 전이가능한 선택규칙 학습**. "형식맞추기" 프레임은 관측과 안 맞음.

## 4. 다른 아이디어 (구조 주입 외)
1. **타입-지향 premise 선택**: 지금 BM25(어휘)로 premise 랭킹 → **"결론이 goal과 타입-단일화되는 lemma"**로 재랭킹. lemma 시그니처의 결론을 goal과 매칭(구조). selection(90% 오선택)을 직접 겨냥.
2. **elaborated goal**: `Set Printing All`류로 notation 확장·implicit 노출 → decider/연산 head가 텍스트에 드러남(Mode2 15%→↑). desugar가 전이도 도움.
3. **usage-example retrieval**: "이 lemma가 다른 증명서 **어떻게** 쓰였나"(apply 문맥) 검색 → 형식·선택 둘 다 예시로. (proof-retrieval의 lemma-조건화 버전.)
4. **Graph2Tac류 구조표현**(원리적, 큼): term을 typed AST/graph로 → 타입구조·생성자가 feature → 이름 달라도 전이. [[LITERATURE]] arXiv:2401.02949.
5. **self-play + 구조주석**: 성공 궤적을 [TYPES]/[SIGNATURES] 붙여 재학습(expert-iteration) → 도달+선택+구조를 함께.

## 5. 결론 & 검증 우선순위
- **재료는 있다**(생성자 76%, 시그니처 79%, +17pp). 구현은 CPU 섹션추가로 지금 가능.
- **기대치 보정**: capacity의 주 실패는 **선택(what)**. 구조주입은 선택을 **informed·전이가능**하게 만드는 데 유효하나, **oracle +2pp 천장**(도달성)이 상한일 수 있음.
- **가장 싼 결정적 실험**: [TYPES]+[SIGNATURES] 섹션 붙여 **train에 없던 타입/lemma가 test에 나올 때 전이율** A/B. 오르면 SFT/GRPO 반영. (opening 부품개선과 달리 **선택·전이**를 직접 겨냥하므로 이전 opener 실험들과 다른 각도.)

관련: [[REPRESENTATION_FOR_TRANSFER]] · [[opener/DDR_COMPOUND_RETRIEVAL]] · [[opener/CLOSING_FAILURE_ANALYSIS]] · [[opener/RANKING_GOLD_VS_APPLIED]] · [[SUBGOAL_PAPER_ASSESSMENT]]
