# 문헌 조사 요약 (Rango 개선용) — 2026-07-05

> 목적: RL·hammer 없이 **inference-time**(search/backtracking/retrieval-aware/selective-RAG)으로 개선. 각 아이디어를 실패 유형(§analysis.md §3)과 실제 코드 콜사이트에 매핑.

## 코드 현황 (조사로 확인)
- `straight_line_searcher.py` = 38% baseline. INVALID 시 step0부터 재시작, frontier/메모리 없음 → **SEARCH_THRASH 생성기**.
- `classical_searcher.py` = **이미 best-first 존재**(heapq frontier, `score=parent+tactic_score`=GPT-f, depth_limit, `is_redundant`→`seen_goals` alpha 비교). **없는 것**: 실패-tactic 메모, dead-node 전파, cycle guard, AND-node product backup, 에러 repair. dedup이 O(n) 선형 스캔(→해시로).
- `proof_retriever.py` = BM25/TFIDF 쿼리를 `Goal.get_ids()`(식별자만)로 생성 → 불투명 축약이면 빈 쿼리(**NO_RETRIEVAL 원인**). 어느 중간 상태가 매칭됐고 그 다음 tactic이 뭔지 **버림**(STRATEGY_DIVERGE 최고 신호 손실).
- `lm_example.py` = 프롬프트에 retrieved proof/premise 주입. `ModelResult`에 `score_list`(log-prob) 있음 → confidence/entropy 계산 가능.

**최고 레버리지**: `ClassicalSearcher`를 기본으로 + **transposition table + 실패-tactic 메모 + dead-node 마킹** → SEARCH_THRASH 47% 대부분 해체.

## Track A — Search/backtracking (inference-only)
- **A1 GPT-f** (Polu&Sutskever 2020, 2009.03393): 누적 log-prob 우선큐, e≈32 tactic 샘플→dedup→check→push. 이미 ClassicalSearcher에 구현. 액션: 기본값 전환 + max_branch↑ + check 전 dedup. → SEARCH_THRASH, DIVERGE.
- **A2 HTPS status / DT-Solver** (Lample 2022, 2205.11491; Wang 2023): 정규화 goal 해시로 `dict[hash]→{solved,dead,rejected_tactics}` 전역 유지. 확장 전 dead skip, rejected를 Coq 치기 전에 제안에서 차감, 전부 거부면 dead 전파. cycle guard(조상 해시). → **SEARCH_THRASH(47%)**, AUTO_LOOP, LONG_PROOF. `is_redundant`를 해시맵+`rejected_tactics`+`dead`로 확장.
- **A3 HTPS AND/OR + product backup + PUCT** (2205.11491): tactic=여러 subgoal로 가는 hyperedge, `v(g,t)=∏ v(child)`(모든 subgoal 닫혀야). PUCT 선택. RL 없이 search만 채택 가능(prior=1.3B log-prob, leaf value=상수 0.5 또는 `GoalScorer`). → LONG_PROOF, 다중 subgoal(split/induction). 큰 작업, A1/A2 먼저.
- **A4 Baldur repair** (First 2023, 2303.04910): repair 입력에 **Coq 에러 메시지** 포함이 핵심(ablation 시 이득 사라짐). → LLM_INVALID, DIVERGE. check_proof가 거부한 tactic+에러를 다음 확장 프롬프트에 주입(1~2회 한정).
- **A5 COPRA** (Thakur 2023, 2310.04353): 스택 DFS, 프롬프트에 goal+retrieved+history+직전 에러 → 실패 tactic 재제안 회피. **CompCert에서 검증됨**. = A2+A4 조합.

## Track B — retrieval 정규화 (inference-only)
- **B1 정규화 파이프라인** (Kaliszyk&Urban 2014, 1402.3578): ① hyp/conclusion **필드 분리**+결론 가중, ② 로컬명 **alpha 정규화**(타입+도입순서로 리네임; `goal_comparer.py`에 기계 있음), ③ head 심볼/전역 상수 고가중·로컬 저가중 2-스트림, ④ 코퍼스·쿼리 동일 정규화. → DIVERGE, NO_RETRIEVAL.
- **B2 δ-unfold** (Graph2Tac, 2401.02949): 이름 대신 **정의 본문**으로 표현. "unfold하면 매칭 0→6"의 원리적 버전. retrieval-miss(top score<τ 또는 빈 ids)일 때 head 심볼 1단계 `unfold f`/`red` 후 재쿼리(lazy). → NO_RETRIEVAL. 새 search action으로도.
- **B3 accessible scoping** (LeanDojo/ReProver, 2306.15626): 같은 파일 premise 우세 → 동일파일 score 배수(재가중, 학습불요).

## Track C — retrieval-aware & selective RAG (inference-only)
- **C1 정렬된 next-tactic 복원** (Rango ICSE2025, 2412.14063): Rango가 매칭된 중간상태 `argmax_i`와 그 다음 tactic을 **버림**. 복원해 ① 프롬프트에 힌트 주입, ② **강제 decode 후보**로 frontier에 추가(step당 check 1회). → **DIVERGE(36%) 최고 레버리지**. `get_similar_proof_steps`가 `ref_step_idx` 이미 추적.
- **C2 confidence-gated re-retrieve** (FLARE 2305.06983; TARG 2511.09803): 초안 tactic의 저확률 토큰/엔트로피/top1-top2 margin으로 트리거, 저확률 토큰 마스킹 후 재검색. `score_list`로 계산. → NO_RETRIEVAL, 선택적 RAG 게이트.
- **C3 Self-RAG 관련성 비평** (Asai 2023, 2310.11511): ISREL(관련?)·ISSUP(근거?) 토큰으로 게이트. 1.3B에 "이 참조증명 관련? yes/no" 물어 P(yes)로 주입 게이트. → DIVERGE(엉뚱한 유사증명 차단), LLM_INVALID.
- **C4 Magnushammer rerank** (Mikuła 2024, 2303.04488): BM25=SELECT + **1.3B 자체를 zero-shot cross-encoder**로 RERANK(참조증명 next tactic의 length-norm likelihood). 파라미터 추가 없음.
- **C5 retrieval-confidence 탐색순서**: frontier 점수 = LM 누적 log-prob ⊕ top rerank retrieval score. 저신뢰 노드에선 `intros/unfold` 우선 → 검색 가능한 영역으로 복귀. `Candidate.score`/heapq key 수정.
- **C6 DSP follow-skeleton** (Jiang 2023, 2210.12283): 고신뢰 sibling `[t1..tk]`를 verbatim 우선 시도(가설명 repair 후), 실패 지점만 free 생성. Coq이 checker(ATP 불요).

## Track D — fine-tuning (보류, RL/hammer 아님)
- provability critic/value head(GPT-f/HTPS) · `<normalize>` 학습 토큰(Thor 2205.10893) · dense bi-encoder(ReProver) · cross-encoder reranker(Magnushammer) · PACT co-training(2102.06203, type-incorrect tactic↓).

## 근거 기반 우선순위
1. ClassicalSearcher 기본화 + 샘플 dedup (A1, XS) — thrash/diverge
2. transposition table+실패메모+dead+cycle (A2, M) — **SEARCH_THRASH 47%**, AUTO_LOOP
3. 정렬 next-tactic→프롬프트+강제후보 (C1, S) — **DIVERGE 36%**
4. 에러 조건부 repair 프롬프트 (A4/A5, S) — LLM_INVALID
5. retrieval-miss→δ-unfold 재검색 (B2/C2, S~M) — NO_RETRIEVAL
6. BM25 전 정규화(필드분리·alpha명·구조토큰가중) (B1, M) — DIVERGE, NO_RETRIEVAL
7. zero-shot cross-encoder rerank + 관련성 게이트 (C3/C4, M) — DIVERGE
8. FLARE/TARG 신뢰 게이트 + retrieval-confidence 순서 (C2/C5, M)
9. HTPS AND/OR + product backup (A3, L) — LONG_PROOF, 다중 subgoal
10. DSP follow-skeleton (C6, M) — DIVERGE

1~4가 실패의 ~87%(47+36+4) 공략하는 1차 스프린트.
