# rango-augmented — 증강 프롬프트로 재학습 계획 + 프롬프트예산 실측

작성 2026-08-02. 목표: 우리가 개선한 기술(재랭킹 + [TYPES]/[DECIDERS]/[SIGNATURES] 구조컨텍스트)을 **프롬프트에 넣어 1.3B decoder를 재학습** → (a) gold lemma 매칭 (b) CompCert 성공률 상승 검증.

## 1. training set 위치 (확인)
- 원래 처리셋 `data/bm25-proof-tfidf-proj-thm-prem-final-clean` = **삭제됨**.
- **원본 소스**: `raw-data/coqstoq-test/data_points/`(750M gold proofs), `sentences.db`(retrieval 코퍼스 53387).
- **이미 생성 중**: `data/grpo_rollouts/tst1000tr5091_gold.jsonl`(298MB, per-step **state+tactic+premises+proofs**) — tst1000tr5091 파이프라인 산출. **rango-augmented 재료**(여기 각 step에 [TYPES]/[DECIDERS]/재랭킹만 추가).

## 2. 계획 합당성 평가 — 합당(통제 필요)
- ✅ **올바른 테스트**: base rango는 구조컨텍스트 없이 학습 → 못 씀(oracle +2pp = OOD 하한). 재학습이 "정말 쓰는지" 판정.
- ⚠️ **통제군 필수**: 같은 split·학습·**증강만 뺀** baseline. → **`tst1000tr5091-sft`(같은 split, 증강 없음)가 baseline.** rango-augmented도 같은 split로 → 깨끗한 A/B.
- ⚠️ **싸게**: from-scratch 말고 **base rango에서 continue-SFT**(기존 지식 유지 + 저비용).
- ⚠️ **천장**: 선택 개선돼도 다단계 도달성이 상한일 수 있음([[SUBGOAL_PAPER_ASSESSMENT]] §10). 실험이 판정.

### 평가 (a) gold lemma 매칭
teacher-forcing top-1(oracle류): 각 gold state에서 재학습 모델이 gold tactic을 top-1으로 뽑나. baseline(비증강) 대비 Δ. **+2pp(base rango, OOD)가 하한** — 증강학습 모델이 넘어야 함.
### 평가 (b) CompCert 성공률
rand200/test @300s. baseline(tst1000tr5091-sft) vs augmented. 순 성공률 Δ.

## 3. 프롬프트 예산 실측 (걱정: 대형 프로젝트서 폭증?)
현재: hard_seq_len 4096, 사용 ~3200(state1024+script512+proof1024+premise512+out128) → **헤드룸 ~900**.

| 주입 | goal당 토큰(실측) |
|---|---|
| [TYPES] 생성자 | 평균 **56**, 중앙 26, 최대 709 |
| [DECIDERS] | 타입당 ~10 × 소수 |
| [SIGNATURES] 증분(premise에 없는 stdlib만) | **70%가 0**, 필요시 lemma당 ~18 |
| **합** | **평균 ~80-120** |

- **핵심**: CompCert가 커도 **한 goal 등장 inductive 타입은 중앙 3개**(평균 4.2)뿐 → 생성자 주입 작음. 평균 헤드룸 안.
- **꼬리**: **상위 2% goal이 500+토큰(최대 709)** — 대형 문맥. 여기가 selective 필요 지점.

## 4. Selective 타입 주입 (사용자 직관 "진짜 필요한 것만" = 맞음)
전부 넣지 말고 **관련도 선별**(대형 goal 꼬리 + 낭비 방지):
1. **destruct 후보 타입만**: goal 결론 등장 or case-split 대상 변수의 타입(전체 가설맥락 아님).
2. **결정가능·소수 생성자 우선**: 큰 record 제외, eq_dec/소수 constructor 타입 우선.
3. **관련도 랭킹 + 예산캡**: 타입도 premise처럼 top-K, 총 ≤N토큰(예 200).
4. **재랭킹된 premise가 쓰는 타입** 우선(선택-구조 정렬).
→ 평균 56 더 축소 + 상위 2% 꼬리 제어.

## 4b. ★ CPU dry-run 검증 (2026-08-02, `scripts/test_augmented_dryrun.py`)

selective [TYPES]+[DECIDERS]를 실제 CompCert gold state **18,433개**에 적용(실제 deepseek 토크나이저):
| 검증 | 결과 |
|---|---|
| **에러율** | **0%** (18,433 state 파싱·주입 클린) |
| **프롬프트 토큰** | base 중앙 2098 → **augmented 2148 (+50)**, budget(4096) 초과 6.6%→7.0%(+0.4pp) |
| **selective vs naive** | selective 평균 21토큰 vs naive 86 = **76% 절감** (최대 144 vs 1193) |
| **필요타입 커버** | **100%** (gold destruct 타입이 selective에 100% 포함 = 신호손실 없음) |

**결론: (1) 에러 없이 동작, (2) 프롬프트 안 커짐(+50 중앙), (3) 성능저하 위험 없음(필요타입 100% 커버).**
- **함정 하나 잡음**: 첫 selective가 "변수가 결론 등장" 요구 → 커버 38%로 급락(가설 destruct 누락). **완화(가설 변수도 포함, 소수생성자+예산캡 유지)** → 100% 커버 + 21토큰 유지.
- **주의**: base가 이미 6.6% >4096(기존 truncation 대상, 병리적 대형 가설). augmented는 +0.4pp만 추가 — 무시가능. [TYPES]는 collator서 **독립 예산**(premise 안 뺏음)으로 붙임.
- **selective 규칙**(학습·추론 동일 적용): inductive-타입 변수(가설·결론) → 생성자 ≤8개 → 결론등장 우선 랭킹 → top-6, ≤200토큰 캡.

## 5. 파이프라인 (제안)
```
0. tst1000tr5091-sft 완료 대기 (= 비증강 baseline)
1. 증강 데이터 빌드: tst1000tr5091_gold.jsonl 각 step에 [TYPES](selective)+[DECIDERS]+재랭킹 premise 추가 → augmented.jsonl
   · collator에 [TYPES]/[DECIDERS] 섹션 추가(RERANK_PREMISES는 이미 배선)
2. continue-SFT: init=base rango(or tst1000tr5091-sft), augmented 데이터, 같은 hyperparam
3. 평가 (a) gold lemma top-1  (b) rand200/test 성공률  — vs tst1000tr5091-sft baseline
```

## 6. 리스크·주의
- **데이터-프롬프트 일치**: 학습·추론 프롬프트 포맷 동일해야(섹션 순서·토큰예산). 안 그러면 OOD.
- **selective 주입의 결정성**: 학습·추론서 같은 규칙으로 타입 선별(안 그러면 분포 불일치).
- **혼동 통제**: 증강 vs 비증강만 다르게(같은 데이터·split·hyperparam).
- **도달성 천장**: (b)가 안 올라도 (a)가 오르면 "선택은 개선, 경로는 별개" = 여전히 유의미 결과.

관련: [[SELECTION_REPRESENTATION_INDEX]] · [[STRUCTURED_CONTEXT]] · [[TYPED_RERANK_AND_COMPOSITION]] · [[REPRESENTATION_FOR_TRANSFER]]
