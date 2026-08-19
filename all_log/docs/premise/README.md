# 검색(retrieval) 문서

| 파일 | 내용 |
|---|---|
| [diagnose.md](diagnose.md) | 진단부터 지금까지 전부 — 왜 gold lemma 가 프롬프트에 없나, 시도한 것과 실패한 것, assert 분할, 알고리즘 설명 |
| [gbdt.md](gbdt.md) | ★ 가장 성능이 좋은 방법(GBDT 재랭킹) 상세 — 초등학생용 설명 + 알고리즘 + 모의코드 + 코드 단위 설명 |
| [problem_of_gbdt.md](problem_of_gbdt.md) | ★ GBDT 의 **문제** — 학습/추론 후보집합 불일치, 한계, assert 하위목표에서 구조우선이 +39pp 인 이유 |

## 지표 정의 (모든 문서 공통)

분모는 **gold lemma 를 쓰고 그 lemma 가 후보 풀에 실제로 있는 스텝** 이다.

| 지표 | 뜻 |
|---|---|
| **R@k** | 필요한 gold 중 **하나라도** 상위 k 안에 든 스텝의 비율 |
| **ALL@k** | 필요한 gold 를 **전부** 상위 k 안에 넣은 스텝의 비율 |

프롬프트에는 상위 N 개만 들어간다. tactic 이 lemma 를 2개 쓰는데 하나만 들어가면 모델은
나머지를 **지어내야** 하므로 불가능하다 → **실제로 중요한 것은 ALL@k**. TEST 에서 lemma 를
2개 이상 쓰는 스텝이 **24%** 라 차이가 크다.

(예: gold 가 `add_comm` 3위, `mul_comm` 41위면 → R@20 ✓, ALL@20 ✗, ALL@50 ✓)

## 한 줄 요약

현재 rango 는 **토큰 TF-IDF** 로 premise 를 고른다 — 구조를 전혀 안 본다.
오프라인 최고는 **GBDT 재랭킹** TEST R@50 **65.0% → 88.6%** (+23.6pp) 인데,
실제 파이프라인 경로에서는 **학습/추론 후보집합 불일치**로 R@1 이 무너진다(problem_of_gbdt.md).
아직 `SparseClient` 에 통합하지 않았다.

## 코드 위치

**실제 파이프라인** — 고치면 학습·추론에 반영된다

| 파일 | 역할 |
|---|---|
| `src/premise_selection/premise_client.py:343` `SparseClient` | 랭킹 진입점 |
| `src/data_management/dataset_file.py:27` `ID_FORM` | 토큰 자르는 정규식 |
| `src/proof_retrieval/tfidf.py` | TF-IDF |
| `src/tactic_gen/tactic_data.py` | 프롬프트 조립 |

**연구용** — 아직 파이프라인 밖

| 파일 | 역할 |
|---|---|
| `src/tactic_gen/tier_rank.py` | RRF/계층 랭커 |
| `src/tactic_gen/applicable.py` | Coq 항 파서 + 단방향 유니피케이션 |
| `scripts/dump_retrieval_features.py` | 특징 12개 추출 → jsonl |
| `scripts/train_ranker_gbdt.py` | GBDT 학습·평가 |
| `scripts/eval_retrieval.py` | R@k / ALL@k 성능 검사 |
| `scripts/research_structural.py` | 신호 A~K 실험대 |
