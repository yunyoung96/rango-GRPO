# rango-augmented 사전검토 (비싼 학습 전 실수방지) — 2026-08-02

목적: 학습 1회에 1.5~2일 → **실행 전 다각도 적대적 검토**. 실제 프롬프트 렌더링으로 버그를 미리 잡음.
방법: `scripts/render_augmented_examples.py`로 **실제 ProofPremiseCollator**를 써서 train 예시에 프롬프트를 렌더 → 눈으로·토큰수로 검증.

## ★ 렌더링으로 잡은 버그 (수정완료)
| # | 버그 | 증거 | 수정 |
|---|---|---|---|
| B1 | **[TYPES] 빈 생성자 오염** | `R := `(빈칸), `F := `, 138개 비-inductive | `ind_constructors_clean.json`(776→626, 빈생성자·1글자 제거) |
| B2 | **[DECIDERS] 키워드/변수 노이즈** | `forall: forall_dec`, `if: if_eq_dec`, `d/s/x`에 랜덤매칭 | KW blocklist + 결론부 연산head만 + len≥2 |
| B3 | **rerank score가 등식(rewrite)에 약함** | Ex5 `Zpower_plus` base 9/12→rerank 1/13(멀어짐) | `_rr_ops` 연산head 중첩 추가(Ex4 7/10→10/10 개선) |

**→ 이 셋은 프롬프트에 노이즈를 넣거나 gold를 잘못 배치 = 학습 저하 요인. 렌더링 안 했으면 학습에 그대로 들어갔음.**

## 검증된 것 (안전 확인)
### V1. 재랭킹 배선 정확 (reverse+truncation)
- `whole_number_allocate`: 리스트 **앞쪽 유지**(뒤 자름). `allocate_and_fmt reverse=True`: 유지분 뒤집어 출력.
- 파이프라인: rerank[best..worst] → truncation이 **best 유지** → reverse로 best가 **[STATE] 최근접(recency)**.
- 렌더 확인: Ex3 base에서 truncation됐던 gold를 rerank가 **9/9(state 최근접)으로 구제** ✓. Ex4 7/10→10/10 ✓.
- **결론: 배선 올바름. reverse가 오히려 유리(best near state).**

### V2. 프롬프트 크기 안전 (§PLAN 4b + 렌더)
- augmented가 base 대비 중앙 **+50토큰**, budget초과 +0.4pp. selective [TYPES] 평균 21토큰.
- 렌더 예시: base 1593~2127 → rerank/aug 거의 동일(±수십토큰). **안 터짐.**

### V3. 누수(leakage) 위험 낮음
- **재랭킹**: 이미 retrieve된(premise_filter 적용된) premise를 **재정렬만** → 새 누수 없음.
- **[TYPES]**: inductive **타입정의**(val/comparison 등) = 공유 인프라, 증명내용 아님 → 누수 아님.
- **[DECIDERS]/[SIGNATURES]**: ⚠️ 라이브러리 decider/시그니처는 대체로 안전하나, **반드시 premise와 동일 exclusion scope**(same-theorem/file-future 제외, `premise_filter`)로 조회해야. (규칙: 인덱스 조회 결과를 premise_filter 통과분으로 제한.)

## 남은 리스크 (실행 전 처리 필요)
| R | 리스크 | 대응 |
|---|---|---|
| R1 | **train/infer 포맷 불일치** = OOD 저하 | 학습·추론 **동일 collator·동일 selective 규칙**. RERANK env + [TYPES]섹션 둘 다 양쪽 적용. |
| R2 | **[TYPES] 섹션 collator 미구현** | 현재 RERANK만 배선됨. [TYPES]/[DECIDERS]는 **독립 토큰예산**으로 collator에 추가 필요(premise 안 뺏게). |
| R3 | **multi-rewrite 엣지케이스**(Ex1 pred_0) | rerank가 첫 head만 최적화 → 나머지 lemma 밀릴 수 있음. aggregate는 +14pp이나 개별 regression 존재. **A/B가 net 판정**(수용). |
| R4 | **[DECIDERS] 잔여 노이즈**(`m1: Equal_dec` 변수매칭) | 1차 실험선 **[DECIDERS] 보수적/생략** 권장. 핵심 = 재랭킹 premise + [TYPES]. |
| R5 | **통제군** | tst1000tr5091-sft(비증강, 같은split)와 A/B. 증강만 다르게. |

## 권고: 1차 augmented 구성 (리스크 최소)
**핵심 2종만** (검증·고신뢰):
1. **재랭킹 premise** (RERANK_PREMISES=1, 배선완료·검증완료, +14pp selection)
2. **[TYPES] selective 생성자** (정제인덱스, 100% 필요타입커버, 평균21토큰)

**보류(2차)**: [DECIDERS](노이즈), [SIGNATURES](premise와 중복·누수주의). 1차에서 핵심 2종 효과 확인 후 추가.

## 사전비행 체크리스트 (학습 직전)
- [ ] tst1000tr5091-sft 완료(=비증강 baseline) 확보
- [ ] [TYPES] collator 섹션 구현 + 독립예산(예 state_tokens에서 분리, ≤200)
- [ ] selective 규칙 학습·추론 동일 (결정적, 정제인덱스)
- [ ] [TYPES]/decider 조회에 premise_filter exclusion 적용(누수)
- [ ] 증강 데이터 = base rango 위 continue-SFT (from-scratch 아님)
- [ ] 평가: (a) gold lemma top-1(vs base +2pp 하한) (b) rand200 성공률(vs 비증강 baseline)
- [ ] 소규모 dry-eval(20정리)로 포맷·서버 확인 후 전체

## ★★ 종합검증 + 블렌드 개선 (2026-08-02, `scripts/validate_augmented.py`)

7개 데이터셋(gold 2 + 롤아웃 5, 분포 다름) × 다차원 검증 → **디버깅으로 핵심 개선 발견**:
- **통과**: 순열보존·결정성·top-1개선(7/7)·[TYPES]노이즈0·크래시0·누수0·프롬프트안전 (모두 ✓).
- **발견된 문제**: 순수 rerank가 **top-5를 롤아웃 쉬운케이스서 저하**(gold가 이미 BM25상위인데 흔듦).
- **원인**: gold가 BM25 상위인 쉬운케이스를 rerank가 다른신호로 재배치 → 손해. 어려운케이스(gold 묻힘)만 도움.
- **해결 = 블렌드**(`rerank_premises`, α=5): **BM25 원순위 prior + α×타입점수**. 쉬운케이스는 BM25가 지키고 묻힌 gold만 끌어올림.

**블렌드 최종 검증 (7/7 전부 top-1·top-5 모두 ≥BM25):**
| 데이터 | top-1 | top-5 |
|---|---|---|
| goldsft_bs2 | 22→**40** | 58→**71** |
| tst1000tr5091_gold | 28→**40** | 58→**68** |
| once_v2(성공스텝) | 49→**62** | 84→**93** |
| cascade-s0 | 36→**45** | 80→**91** |
| bigscale2 | 33→**44** | 83→**92** |
| subgoal-s0 | 37→**51** | 87→**93** |
| opener_once | 44→**58** | 88→**93** |

→ **블렌드는 모든 데이터셋서 BM25 대비 strict 개선**(top-1 +11~18pp, top-5 regression 0). 순수 rerank보다도 우수. **채택.**

## 다양한 방향 재검토 (혹시 놓친 것)
- **재랭킹이 비-truncation 93%서도 순서만 바꿈**: 순서만 바뀌어도 recency로 영향. 단 score 틀리면 gold를 멀리 보낼 위험(Ex5) → net +14pp라 수용, but score 개선여지.
- **gold lemma가 애초 retrieve 안 된 경우**(recall<100%)는 재랭킹 무관 → [SIGNATURES]/Search로 recall 보강은 별개 레버(2차).
- **학습이 재랭킹 순서에 과적합**할 수도: 추론 재랭킹이 학습과 다르면 저하 → 동일 규칙 필수(R1).
- **[TYPES]가 항상 같은 타입정의 반복** → 모델이 무시학습 가능. 그래도 새 타입엔 도움(전이). 무해.

관련: [[PLAN]] · [[../TYPED_RERANK_AND_COMPOSITION]] · [[../STRUCTURED_CONTEXT]] · [[../SELECTION_REPRESENTATION_INDEX]]
