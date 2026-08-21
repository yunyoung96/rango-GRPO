# v9 프롬프트 vs 기존 rango 프롬프트

같은 스텝(0개)에서 두 파이프라인이 만드는 프롬프트를 그대로 나란히 뽑았다.

## 무엇이 다른가

| 설정 | rango 원본 | v9 |
|---|---|---|
| premise_tokens | 512 | 896 |
| proof_tokens | 1024 | 256 |
| hard_seq_len | 4096 | 2048 |
| num_premises | 50 | 100 |
| num_proofs | 20 | 12 |
| 검색 | tfidf 만 | tfidf + 구조 재랭킹 |
| [TYPES]/[DEFINITIONS] | 없음 | 주입 |
| 이름 정규화 | 없음 | 전부(rate 1.0) |
| cut | 없음 | gold 가 없으면 assert 치환 |

토크나이저는 **둘 다 Qwen** 으로 맞췄다 — 예산 차이만 남기고 나머지 변수를 없애야 비교가 의미 있다.

## 자동 점검 요약

- 이상 없음

## 예제 목록

| # | 인덱스 | rango tok | v9 tok | cut | TYPES | DEFS | 점검 |
|---|---|---|---|---|---|---|---|
