# 방법론 로드맵 (순차 개발)

각 방법은 `run_thm.py`의 새 alias + `run_all --description`으로 실험한다. 근거는 `all_results/20260701-061839/analysis.md` §3 실패 유형(전체 1000건 기준):
STRATEGY_DIVERGE 36.2% · SEARCH_THRASH 47.0% · NO_RETRIEVAL 5.6% · LLM_INVALID 3.9% · AUTO_LOOP 2.3% · LONG_PROOF 4.3%.

| 방법 | alias | 핵심 아이디어 | 겨냥 실패유형 | 코드 상태 |
|------|-------|--------------|--------------|-----------|
| **M0 baseline** | `rango` | StraightLine, 재시작만 | (기준) | 존재 |
| **M1 backtracking** | `rango-best-beam` | best-first + `seen_goals` 중복제거 → 유효 prefix 보존, 실패 step만 교체 | SEARCH_THRASH(47%) | **이미 존재**(ClassicalSearch) |
| **M2 retrieval-aware search** | `rango-raware`(신규) | 노드 점수에 retrieval 신뢰도(top-k 매칭 overlap) 가산 → 신뢰도 높은 상태를 우선 확장(exploit) | STRATEGY_DIVERGE(36%) | 개발 예정 |
| **M3 normalize-to-retrievable** | `rango-norm`(신규) | 신뢰도 낮으면 `intros/unfold head/simpl`로 goal 노출 후 재검색 | NO_RETRIEVAL(5.6%) | 개발 예정 |
| **M4 selective-RAG candidates** | `rango-selrag`(신규) | 여러 candidate 생성 → 각 결과 상태의 retrieval 신뢰도 평가 → 의미 있는 것만 RAG 확장 | NO_RETRIEVAL+DIVERGE | 개발 예정 |
| **M5 hammer fallback** | `rango-hammer`(신규) | 저신뢰·원자 goal leaf에서 CoqHammer 폴백 | NO_RETRIEVAL + 산술/결정가능 | **CoqHammer 설치 선행 필요** |

## 실험 프로토콜
1. **1차(스크리닝)**: timeout 300s(5분), 데이터 20개. baseline `rango`와 성공 개수 비교.
2. **가망 판정**: baseline 대비 성공 +1 이상(무회귀 우선). 애매하면 실패 회복/신규 회귀를 개별 확인.
3. **2차(확대)**: 가망 있으면 timeout 600s(10분), 데이터 40개 재실험.
4. 결과가 baseline 이상이면 `master`로 merge. 끔찍하면 branch에 보류.
5. 새 log(all_results/<ts>) → 다시 분석 → 다음 방법. 아이디어 고갈돼도 파라미터 스윕/조합으로 계속.

## 근거 데이터 (analysis.md에서)
- backtracking 유효성: SEARCH_THRASH 47% = "한 step 틀려 전부 버림". best-first면 구조적 회복.
- normalize 유효성: idx 444에서 `unfold DN_UP_parity_prop` 직후 retrieval 매칭 0→6 관측.
- selective-RAG: retrieval 신뢰도가 상태 의존적 → 신뢰도 낮은 가지에 비싼 RAG 낭비 대신 신뢰 높은 가지 집중.
