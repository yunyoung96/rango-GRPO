# 표현(representation) 한계와 타입정보 주입 — cross-project 전이를 위해

작성 2026-08-02. 질문: **"goal 텍스트만으로 학습하면 다른 프로젝트의 타입/패턴에 전이가 안 되는데, 완전한 정보를 넣으려면 어떻게?"**
근거: [[opener/DDR_COMPOUND_RETRIEVAL]] — decider 인덱스 조회(Mode2)가 15%로 약함, 원인이 **표현**(notation·타입정보 부재).

## 문제 (실측으로 확정)

### 1. goal은 타입의 **이름만** 준다 (구조 없음)
gold `destruct v` / `destruct H`에서 goal이 주는 건 `v : T`의 **T 이름**뿐:
- `I : In (v,i) (... :: join s s0)` → 타입 `In`의 **이름만**. constructor 몇 개? 안 알려줌.
- `H : Z_is_power2 (unsigned n) = Some ...` / `H : Loc.diff l a /\ ...` → 마찬가지.

destruct를 **올바로** 하려면 (case 몇 개, 어떤 constructor) T의 **정의(constructor 목록·arity)**가 필요한데, 텍스트 goal엔 없음.

### 2. notation이 연산을 가린다 (DDR Mode2 15%의 원인)
gold `destruct (Pos.compare_spec v0 v1)`인데 goal엔 `Pos.compare`가 아니라 **`(v0 ?= v1)%positive`**. `Z.ltb_spec`←`x <? y`, `Int.eq`←`i == j`. → 연산 이름이 텍스트에 안 보여 decider 조회 실패.

### 3. → cross-project 전이 실패 (질문의 핵심)
텍스트만으로 학습하면:
- train에서 `destruct (T_eq_dec a b)` 패턴을 배워도, **T의 구조를 안 배웠으니** "T는 등호결정가능"이라는 걸 이름 `T`에 결부시킬 뿐.
- test에서 새 타입 `T'`(train에 없던)가 나오면, `T'`도 등호결정가능인지 **이름만으론 모름** → 패턴 미전이.
- 즉 **모델이 배우는 건 "이 이름엔 이 tactic" 표층 연상**이지 "결정가능한 타입엔 eq_dec을 destruct" 같은 **구조적 규칙**이 아님. 프로젝트가 바뀌면 이름이 바뀌어 무너짐.

**이게 opener/compound가 test에서 안 오른 한 원인**(도달성 벽과 별개로, 표현 벽): 후보를 잘 만들어도 모델이 그걸 **일반화 가능한 형태로 배우지 못함**.

## 무엇을 넣어야 "완전한 정보"인가

goal 텍스트에 빠진 것 = **타입 세계의 구조**. 넣을 후보(재료는 코퍼스에 다 있음 — INDUCTIVE 988개 등):

| # | 주입 재료 | 무엇을 해결 | 비용 |
|---|---|---|---|
| **A. notation 확장 goal** | `Set Printing All` 류(연산 이름·implicit 노출) | 문제2 (연산 가림) → decider 조회 | goal 길어짐(2~4×) |
| **B. 타입 컨텍스트** | goal에 등장하는 각 타입 T의 **Inductive 정의**(constructor 목록+arity) | 문제1 (destruct 방법) + 전이(구조 공유) | 타입당 1~3줄 |
| **C. decidability 사실** | T의 eq_dec/decider 존재 여부([[opener/DDR_COMPOUND_RETRIEVAL]] 인덱스) | compound decider 선택 | decider당 1줄 |
| **D. 변수 타입 전개** | `x : T`에서 T가 축약되면 full-qualified/전개 | 타입 식별 | 작음 |

### 예시 (B 타입 컨텍스트 주입)
goal: `... c : comparison ...`, gold `destruct c`.
- **지금**: 모델은 `comparison`이 3-case인지 모름 → 다른 프로젝트 3-case 타입에 전이 안 됨.
- **주입 후**: `[TYPE] comparison := Eq | Lt | Gt` (코퍼스에 실재) → 모델이 "3 constructor면 destruct가 3-case 연다"는 **구조**를 봄 → `option`(Some/None), 새 프로젝트 타입에도 전이.

## 근본 해법 두 방향

### (i) 텍스트에 구조를 얹기 (싸고 지금 가능)
현재 프롬프트 `[STATE]/[SCRIPT]/[PROOFS]/[PREMISES]`에 **`[TYPES]` 섹션 추가**:
- goal의 각 타입 head → 코퍼스 INDUCTIVE 정의(constructor)를 검색해 주입(B).
- goal의 각 연산 head → decider 인덱스(C).
- (선택) notation-확장 goal(A).
→ retrieval의 일종이지만 **대상이 "관련 증명/lemma"가 아니라 "goal에 등장한 타입·연산의 정의·decider"** = **구조 retrieval**. 기존 content-retrieval이 못 주던 것.
- 장점: 지금 파이프라인에 섹션만 추가. CPU 사전색인.
- 한계: 여전히 텍스트 인코딩(모델이 구조를 "읽어" 이해해야). context 길이 압박(1.3B).

### (ii) 구조를 1급 feature로 (원리적, 큼)
**Graph2Tac류**([[../LITERATURE]] arXiv:2401.02949): term을 **typed AST/graph**로 인코딩 → 타입 구조·constructor·공유 서브텀이 **feature 자체** → 이름이 달라도 **구조가 같으면 전이**. text transformer 대비 1.48× 보고.
- 장점: cross-project 전이의 정공법(구조 공유). notation 문제 자동 해소(AST는 desugar됨).
- 한계: 아키텍처 변경(현 1.3B LLM 파이프라인과 별개), 큰 작업. 1.3B 규모엔 GNN이 오히려 맞을 수도(Graph2Tac는 노트북 GPU-less).

## 정직한 평가 (뭘 기대할 수 있나)

- **표현 개선은 "도달성/선택" 벽과 다른 축**: 지금까지 벽=capacity(선택·도달)로 봤는데, 표현 부족은 **그 capacity를 낭비**시킴(모델이 구조 대신 이름 표층을 외움). 표현을 주면 같은 1.3B가 **더 잘 일반화**할 여지 → 질문(2)의 답과 연결.
- **단 만능 아님**: closing의 lemma-selection(oracle +2pp)은 표현만으론 다 안 풀림(그건 도메인 지식·capacity). 표현은 **compound/destruct 같은 구조적 tactic의 전이**에 특히 유효.
- **검증 우선순위**: (i)-B(타입 컨텍스트 주입)가 싸고 빠름 → gold destruct의 test-split 전이율(train에 없던 타입에 적용되나) A/B로 측정 가치. 효과 있으면 (i)-A,C 추가, 크면 (ii) 고려.

## 질문(2)에 대한 답 — "이걸 학습하면 1.3B라도 오를까"
- **현재 표현(텍스트)으로 compound를 더 학습**: 제한적. 이유 (a) opening/compound는 병목이 아님(닫기·도달이 벽, 여러 실측), (b) **위 전이 실패** — train 타입에 과적합, test 새 타입 미전이.
- **표현을 고쳐서(타입 컨텍스트 주입) 학습**: 가능성 있음. 구조를 주면 "결정가능 타입→eq_dec destruct" 같은 **전이되는 규칙**을 배울 수 있어, 같은 1.3B로도 test에서 오를 여지. **이게 유망한 실험**.
- 순서: DDR Mode1(부분식 추출, +9pp, 즉시) → 타입컨텍스트 주입 후 전이율 측정 → 되면 SFT/GRPO에 반영.

관련: [[opener/DDR_COMPOUND_RETRIEVAL]] · [[opener/COMPOUND_CANDIDATES]] · [[SUBGOAL_PAPER_ASSESSMENT]] · [[../LITERATURE]](Graph2Tac) · [[BOTTLENECK_ANALYSIS]]
