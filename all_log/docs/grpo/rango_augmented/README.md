# rango-augmented — 색인

우리가 개선한 기술(타입-지향 재랭킹 + [TYPES]/[DECIDERS] 구조컨텍스트)을 **프롬프트에 넣어 1.3B decoder를 재학습**하는 실험. 목표: (a) gold lemma 매칭↑ (b) CompCert 성공률↑.

## 문서
| 파일 | 내용 |
|---|---|
| [INDEX_VS_PROMPT.md](INDEX_VS_PROMPT.md) | **★ 개념정리** — 인덱스(사전) vs 프롬프트(모델이 읽는 것) 구분, 현재 구현상태 표 |
| [PLAN.md](PLAN.md) | 전체 계획 — training set 위치, 합당성, 프롬프트예산 실측, selective 설계, 파이프라인 |
| [REVIEW.md](REVIEW.md) | **★ 사전검토** — 렌더링으로 잡은 버그3(수정), 배선검증, 누수분석, 남은리스크, 사전비행 체크리스트 |
| [NOTATION_AND_COVERAGE.md](NOTATION_AND_COVERAGE.md) | notation 3방법 검증, decider 커버 2→79% 개선(조회base매칭 최대레버), 100% 상한 |
| [DECIDER_DEEP_DIVE.md](DECIDER_DEEP_DIVE.md) | **★ decider 심층분석** — compound 완전분해(A:goal스캔 62%/B1:decider조회 12%/B2:도메인lemma 26%), 프로젝트독립성, 인덱스+랭킹이 과설계인 이유 |
| [PHASE2_DECIDER_GUIDE.md](PHASE2_DECIDER_GUIDE.md) | 2차 구현 가이드(개정) — decider 주력=goal 스캔(`_targeted_cands` 재사용), 프롬프트 섹션은 낮은 우선순위 |
| [PROMPT_EXAMPLES.md](PROMPT_EXAMPLES.md) | 실제 렌더된 프롬프트 예시(train split) |

## 현재 상태 (2026-08-02)
- **핵심 배선 완료**: `RERANK_PREMISES=1`(src/tactic_gen/tactic_data.py) — premise 결론매칭 재정렬. 검증됨(+14pp selection, reverse+truncation 올바름).
- **인덱스 준비**: `data/ind_constructors_clean.json`(626타입), `data/ddr_index.json`(505 decider).
- **dry-run 통과**: 18,433 CompCert state 에러0%, 프롬프트 +50토큰, 필요타입 100% 커버.
- **미구현**: [TYPES]/[DECIDERS] collator 섹션(독립예산). continue-SFT 파이프라인.
- **대기**: tst1000tr5091-sft 완료(=비증강 baseline).

## 핵심 결정
- **1차 = 재랭킹 premise + [TYPES] selective 생성자**(고신뢰 2종). [DECIDERS]/[SIGNATURES]는 2차.
- **통제**: tst1000tr5091-sft(비증강)와 A/B.
- **AU(anti-unification)**: premise 선택엔 내 재랭킹이 우월 → 안 씀([[../TYPED_RERANK_AND_COMPOSITION]]).

## 코드
`scripts/`: `build_decider_index.py`, `test_ddr_coverage.py`, `rerank_premises_typed.py`, `test_augmented_dryrun.py`, `render_augmented_examples.py`.

관련: [[../SELECTION_REPRESENTATION_INDEX]] · [[../STRUCTURED_CONTEXT]] · [[../REPRESENTATION_FOR_TRANSFER]]
