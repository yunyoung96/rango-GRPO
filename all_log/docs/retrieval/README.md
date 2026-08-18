# 검색(retrieval) 문서

| 파일 | 내용 |
|---|---|
| [diagnose.md](diagnose.md) | 진단부터 지금까지 전부 — 왜 gold lemma 가 프롬프트에 없나, 시도한 것과 실패한 것, assert 분할, 알고리즘 설명 |
| [gbdt.md](gbdt.md) | ★ 가장 성능이 좋은 방법(GBDT 재랭킹) 상세 — 초등학생용 설명 + 알고리즘 + 모의코드 + 코드 단위 설명 |

## 한 줄 요약

현재 rango 는 **토큰 TF-IDF** 로 premise 를 고른다 — 구조를 전혀 안 본다.
가장 좋은 개선은 **GBDT 재랭킹**으로 TEST R@50 **65.0% → 88.6%** (+23.6pp).
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
