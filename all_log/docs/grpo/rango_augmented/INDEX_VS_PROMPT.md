# 인덱스 vs 프롬프트 — 무엇이 무엇인가 (2026-08-02)

혼동 방지: "인덱스"와 "프롬프트에 들어가는 것"은 **완전히 다른 것**. 이 문서가 구분.

## 1. 인덱스 = 오프라인 사전 (프롬프트 아님)

코퍼스에서 **미리 만들어둔 조회용 표**. 모델이 보는 게 아니라, collator가 프롬프트를 만들 때 **참고**하는 것.

| 인덱스 파일 | 내용 | 예 | 만드는 법 |
|---|---|---|---|
| `data/ind_constructors_clean.json` | 타입 → 생성자 | `list → [nil, cons]`, `val → [Vundef, Vint, ...]` | `scripts/build_ind_constructors.py` |
| `data/ddr_index.json` | 연산/타입 → decider | `compare → [compare_spec]`, `bool → [bool_dec]` | `scripts/build_decider_index.py` |
| (2차) notation-map | 심볼 → 함수명 | `^ → [Zpower, pow]`, `?= → [compare]` | coqstoq Notation 자동추출 |

**용도**: goal에 `c : comparison`이 있으면 → 인덱스에서 `comparison → [Ceq,Cne,...]`를 찾아 → 프롬프트에 넣을 [TYPES] 줄을 만듦. **인덱스 자체는 프롬프트에 안 들어감.**

## 2. 프롬프트 = 모델이 실제 읽는 텍스트

### 현재 (rango baseline) — 4섹션
```
[PREMISES]        ← retrieve된 lemma (이름 + 시그니처, 예 "Lemma app_nil_r : forall l, l++[]=l.")
Lemma ...
[PROOFS]          ← 유사 증명
...
[STATE]           ← 현재 goal (가설 + 결론)
n: nat
...
[SCRIPT]          ← 지금까지 실행한 tactic
Proof. intros.
[TACTIC]          ← 여기 뒤가 모델이 생성할 다음 tactic (학습 타겟)
```
**★ 현재 [TYPES]/[DECIDERS] 없음.** (인덱스는 있지만 프롬프트 배선 안 됨)

### rango-augmented (구현 시) — [TYPES] 추가
```
[TYPES]                              ← 새로: goal 타입의 생성자 (인덱스에서 조회)
val := Vundef | Vint | Vlong | ...
comparison := Ceq | Cne | Clt | ...
[DECIDERS]                           ← (2차) goal 연산의 decider
block: eq_block
[PREMISES] ... [STATE] ... [SCRIPT] ... [TACTIC]
```

## 3. 흐름 (인덱스 → 프롬프트)
```
[오프라인 1회]  코퍼스 스캔 → 인덱스 파일 (ind_constructors, ddr_index)
                                    │
[학습/추론 매 step]  goal 보고 → 인덱스 조회(관련 타입/연산만) → selective_types()
                                    │
                          [TYPES] 섹션 텍스트 생성 → collator가 프롬프트에 삽입
                                    │
                              모델이 프롬프트 읽고 다음 tactic 생성
```

## 4. 재랭킹은 프롬프트에 "새 섹션"을 안 넣음 (순서만 바꿈)
- [TYPES]/[DECIDERS] = **새 섹션 추가**(정보 주입).
- **재랭킹** = 기존 [PREMISES] 안 lemma들의 **순서를 재배치**(gold를 앞으로). 새 텍스트 없음, 프롬프트 크기 그대로.

## 5. 현재 구현 상태 (명확히)
| 항목 | 인덱스(사전) | 프롬프트 배선 | 검증 |
|---|---|---|---|
| 재랭킹 | (인덱스 불필요, goal-premise 매칭) | ✅ `RERANK_PREMISES=1` | ✅ 7데이터셋 |
| [TYPES] | ✅ ind_constructors_clean.json | ❌ 미배선 | dry-run만 |
| [DECIDERS] | ✅ ddr_index.json (+2차 개선 레시피) | ❌ 미배선(2차) | 커버 2→79% |
| [SIGNATURES] | 시그니처 코퍼스 있음 | ❌ 미배선(2차, 대부분 premise중복) | — |

→ **1차 = 재랭킹(배선완료) + [TYPES](배선 필요).** decider/signature는 2차.

관련: [[NOTATION_AND_COVERAGE]] · [[PLAN]] · [[REVIEW]] · [[EXPERIMENT_SETUP]]
