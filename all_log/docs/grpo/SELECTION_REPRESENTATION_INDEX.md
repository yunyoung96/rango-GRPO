# 선택·표현 조사 인덱스 (2026-08-02)

compound/lemma **선택**과 **표현(전이)** 라인 조사 전체 색인. "closing 벽 = 선택(what)"을 겨냥한 도구·측정·설계.

## 조사 흐름 (질문 → 발견)
1. **compound 커버리지** → [[opener/COMPOUND_CANDIDATES]] §커버리지: 기존 `_targeted_cands`가 gold compound **59% 커버**(초기 "20%"는 as절 측정버그, 정정).
2. **DDR(decidability retrieval)** → [[opener/DDR_COMPOUND_RETRIEVAL]] + [[opener/DDR_INVESTIGATION_SUMMARY]]: 부분식추출+decider인덱스로 **59→69%**, 개선재료(순서decider·notation·가설인자) 추가로 **80%**(+21pp). Mode2(타입인덱스)는 **notation이 연산 가려 15%로 약함**.
3. **표현 한계** → [[REPRESENTATION_FOR_TRANSFER]]: goal은 타입 **이름만** 줌 → cross-project 전이 실패(이름 표층연상만 학습). 타입컨텍스트(생성자)·시그니처·AST 필요.
4. **구조 컨텍스트 주입** → [[STRUCTURED_CONTEXT]]: [TYPES] 생성자 **76%** + [SIGNATURES] 시그니처 **79%**(현 retrieval 62% → +17pp) 재료 실재. **단 닫기실패는 형식(0%)이 아니라 선택(90% 오lemma)** → 구조주입은 "선택 informed·전이가능"에 유효.
5. **타입-지향 재랭킹** → [[TYPED_RERANK_AND_COMPOSITION]]: BM25 top-1 22%→**36%**. AU lgg(독립구현)는 선택엔 나쁨(25%) → **내 재랭킹 채택**. oracle +2pp는 **하한**(미학습). 조립학습법 6종.

## 핵심 결론
- **벽 = 선택(what to apply)**, 형식/조합(how)이 아님(apply 인자오류 0%, 90% 오lemma).
- **재료는 존재**(생성자 76%, 시그니처 79%, decider 505개) — CPU 사전색인.
- **재랭킹으로 선택 랭킹 즉시 개선**(22→36% top-1), 배선 완료(`RERANK_PREMISES=1`), A/B 진행중.
- **표현이 진짜 레버**: notation·타입정보 부재가 Mode2 약점·전이실패의 근원. 구조주입 후 학습이 유망.
- **AU/CLEAVE**(타인 미공개 논문): AU lgg는 이 선택문제엔 무관(다른 채널=증명시연 검색). 논문 기여 안 씀.

## 산출물
**코드(CPU)**: `scripts/build_decider_index.py`, `test_ddr_coverage.py`, `build_gold_trajectories.py`(재활용), `rerank_premises_typed.py`, `au_rank_probe.py`. `data/ddr_index.json`(505), `data/ind_constructors.json`(776).
**배선**: `src/tactic_gen/tactic_data.py` `RERANK_PREMISES` env.
**실험 큐**: `all_log/rerank_ab_queue.sh`(재랭킹 A/B, 학습 후 자동).
**문서**: 위 5개 + 본 인덱스.

## 다음 (검증 우선순위)
1. 재랭킹 A/B 결과(진행중) — 오르면 selection 개선이 test로 전이됨 확인.
2. [TYPES]+[SIGNATURES] 주입 후 **train에 없던 타입/lemma의 test 전이율** A/B.
3. 되면 SFT/GRPO에 재랭킹+구조 반영, 하드네거티브/PRM-selection.

관련 상위: [[SUBGOAL_PAPER_ASSESSMENT]] §10 도달성 · [[BOTTLENECK_ANALYSIS]] · [[README]]
