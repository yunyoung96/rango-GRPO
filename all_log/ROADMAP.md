# 방법론 로드맵 (순차 개발)

각 방법은 `run_thm.py`의 새 alias + `run_all --description`으로 실험한다. 근거는 `all_results/20260701-061839/analysis.md` §3 실패 유형(전체 1000건 기준):
STRATEGY_DIVERGE 36.2% · SEARCH_THRASH 47.0% · NO_RETRIEVAL 5.6% · LLM_INVALID 3.9% · AUTO_LOOP 2.3% · LONG_PROOF 4.3%.

> **순서 재정렬(논문 반영, `LITERATURE.md`)**: 실패 지분·구현 난이도 기준. M1(=ClassicalSearcher)이 최대 지분(SEARCH_THRASH 47%)을 이미 겨냥하므로, 그 위에 A2(검색 메모리)→C1(정렬 tactic)→A4(에러 repair)를 쌓는 게 1차 스프린트(실패 ~87% 공략). 이후 사용자 아이디어(retrieval-aware/normalize/selective-RAG)는 M6~로.

| 방법 | alias | 핵심 아이디어 | 겨냥 | 근거 | 상태 |
|------|-------|--------------|------|------|------|
| **M0 baseline** | `rango` | StraightLine, 재시작만 | (기준) | — | 존재 |
| **M1 backtracking** | `rango-best-beam` | best-first + `seen_goals` 중복제거 → 유효 prefix 보존 | SEARCH_THRASH(47%) | A1 GPT-f | **실행 중** |
| **M2 search-memory** | `rango-mem`(신규) | transposition table(goal repr 해시, O(1) dedup) + 실패-tactic 메모(check 전 차감) + cycle guard(무진전 tactic 제거) | SEARCH_THRASH, AUTO_LOOP | A2 HTPS/DT-Solver | **구현완료**(commit 9feeebd), GPU 비면 테스트 |
| **M3 aligned-tactic** | `rango-align`(신규) | 매칭된 sibling 중간상태의 **다음 tactic 복원** → 프롬프트 힌트 + 강제 decode 후보 | STRATEGY_DIVERGE(36%) | C1 Rango/Graph2Tac | 예정 |
| **M4 error-repair** | `rango-repair`(신규) | 거부된 tactic+Coq 에러를 다음 확장 프롬프트에 주입 | LLM_INVALID | A4 Baldur / A5 COPRA | 예정 |
| **M5 unfold-gate** | `rango-unfold`(신규) | retrieval-miss 시 head 심볼 δ-unfold 후 재검색 (idx444 매칭 0→6) | NO_RETRIEVAL | B2 Graph2Tac / C2 FLARE | 예정 |
| **M6+ (사용자 아이디어)** | `rango-raware`/`rango-norm`/`rango-selrag` | retrieval-confidence 탐색순서 · BM25 전 정규화 · 후보별 selective-RAG · cross-encoder rerank | DIVERGE/NO_RETR | C5/B1/C4 | 예정 |

> **범위 확정**: hammer 미설치·미사용. RL 미사용. inference-time만.

## M3 상세 설계 (aligned next-tactic, C1) — 구현 대기
- **교훈 반영**: M1에서 classical(best-first)이 straight-line보다 하락(-3). 따라서 M3는 **straight-line 기반**으로 붙인다(강한 baseline에 retrieval 개선을 얹음). searcher 무관한 프롬프트-포매터 변경이 핵심.
- 재료: `proof_retriever.py::get_similar_proof_steps`가 이미 매칭된 `ref_step_idx` 계산·반환 → 그 sibling 증명의 다음 tactic = `ref_proof.steps[ref_step_idx].step.text`.
- 구현: (1) retriever/formatter가 top-1 sibling의 aligned 다음 tactic을 추출, (2) `lm_example.example_from_step` 프롬프트에 `(* 유사 goal에서 다음 tactic: X *)` 힌트 라인 주입. (선택) classical이면 강제 decode 후보로도.
- alias `rango-align` = straight-line + 힌트. 스모크→600/20.

## M2 상세 설계 (retrieval-aware search) — 구현 대기
- 위치: `classical_searcher.py`의 `search_step` — 후보 생성 루프(recs.next_tactic_list) 지점. 새 candidate를 frontier에 push할 때 점수를 조정.
- 신호: 각 candidate의 결과 goal에 대한 proof-retrieval top1 매칭 overlap 비율 `r ∈ [0,1]` (지금도 lm_example에서 top5·매칭수를 계산하므로 재사용).
- 점수: `score' = tactic_score + α·r` (α는 alias 파라미터, 초기 α=0.5). r 높은 상태를 우선 확장 → STRATEGY_DIVERGE 겨냥.
- 주의: retrieval 호출 비용. 매 candidate마다 재검색은 비싸므로, 이미 formatter가 뽑아둔 retrieval 결과를 노드에 캐싱해 재사용.
- alias: `rango-raware`. get_searcher_conf/get_tactic_confs에 분기 추가.

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

## M4 상세 설계 (error-repair, A4) — 구현 대기
- Coq 에러: `proof_manager.py:220-222` diagnostic.message(severity 1)로 존재하나 ProofCheckResult에 미저장.
- 간이형(우선): straight-line에서 실패한 tactic 텍스트를 다음 프롬프트에 '피해야 할 것'으로 주입(COPRA-lite, 에러문 없이도 재제안 회피). formatter align_hint처럼 flag+주입.
- 정식형: ProofCheckResult에 error_msg 캡처→searcher→formatter 전달→프롬프트 주입.

## [범위 변경 2026-07-05] 강화학습(RL) 트랙 추가 — 사용자 요청
- 기존 "RL 미사용" 제약 해제. **RL 옵션 추가 실험**(QEDCartographer 포함). hammer는 여전히 미사용.
- 기존 루프 원칙 유지: 새 alias + --description, 순차 실행, 완료마다 analysis.md, 한 번에 GPU 하나.
- RL 후보 (조사 서브에이전트 결과 대기 중 → LITERATURE에 반영 예정):
  - **MR1 value-guided search**: 축적된 로그(state, 최종 solved?)로 경량 value head V(state)→P(provable) 학습 → best-first(ClassicalSearcher) heuristic으로. GPT-f/HTPS critic, QEDCartographer의 value-guidance 이식형. **우리 로그 재사용 = 저비용 첫 RL.**
  - **MR2 expert iteration**: 모델이 찾은 성공 증명으로 재학습(reward-free self-training).
  - **QEDCartographer 직접 실행 가능성**: 별도 repo(Proverbot9001 기반)라 통합 난이도 조사 필요 → 서브에이전트 판단 반영.
- 주의: RL은 학습(fine-tune) 필요 → GPU 학습 job은 M3~M5 inference 실험과 순차로(동시 금지).

## RL 트랙 구체화 (조사 반영, RL_LITERATURE.md)
- **QEDCartographer 직접 실행 배제** → **MR1 value-guided best-first**(QED-영감)로 대체.
- **MR1 (value-guided search)** — alias `rango-value`. 단계:
  1. ClassicalSearcher에 노드-상태 로깅(JSONL) + 탐색후 성공경로/dead 라벨링 훅.
  2. 로깅 켠 채 classical 탐색 데이터 수집 run(GPU).
  3. value head(MLP on 동결 DeepSeek 임베딩 or 수제특징) BCE/MSE 학습(수 분).
  4. `ClassicalSearchConf(value_guided, value_weight, value_ckpt)` — frontier 우선순위=cum_logprob+value_weight·log V. value_weight=0이면 baseline classical(A/B).
  5. 600/20 실험 → analysis.md.
- **MR2 (expert iteration)** — 자기 성공증명으로 LoRA 재학습(train_decoder.py 재사용). policy 개선. MR1 다음.
- 주의: classical 계열은 M1/M2에서 straight-line 미달이었음 → value-guiding으로 순서 개선이 그 격차를 메우는지가 관건. 안 되면 value 신호를 straight-line 후보 재랭킹에 쓰는 변형 고려.
- GPU 학습 job은 inference 실험과 순차(동시 금지).

## [사용자 피드백 2026-07-06] 신규 방향 4개 + 참조 케이스
### 새 실패 케이스 (분석용)
- **or_and_distrib** (bit_solve; apply orb_andb_distrib_r): built-in premise `orb_andb_distrib_r`를 못 찾음/증명 못함. reference `and_or_distrib`는 `demorgan1` 사용. → **built-in(Coq stdlib) lemma 검색 부재**.
- **idx 971 lt_le_trans** (ref idx 9335 le_lt_trans): reference는 거의 동일하게 잘 찾았으나, `elim (@E.lt_not_eq x1 x2)`의 **명시적 인자(x1 x2 vs x2 x3)** 적응이 약함. premise가 아니라 **explicit proposition/argument 추론** 문제. → proof-adaptation 강화 필요.

### 방향
1. **built-in premise 검색**: Coq stdlib lemma를 retrieval 대상에 포함(orb_andb_distrib_r 등). 인프라 큼(stdlib lemma DB). 보류/조사.
2. **proof-adaptation(explicit arg 적응)**: aligned sibling tactic의 명시적 인자를 goal에 맞게 순열/치환한 변형을 강제후보로. idx971류 겨냥. 파싱 필요.
3. **retrieval 약할 때 non-fine-tuned/일반 모델 사용** ← **실현가능(base=deepseek-coder-1.3b-instruct HF캐시, no-retrieval fine-tune=deepseek-basic-ablation 로컬)**. fine-tuning이 retrieval에 과적합됐을 수 있음. **→ 앙상블(straight-line이 tactic_clients 회전) or gated 전환.**
4. **multi-agent LLM**: 여러 에이전트(생성/비평/적응) 협업. 설계 단계.

### 우선순위: 3(앙상블, 지금 구현) → 2(arg 적응) → 1(stdlib) → 4(multi-agent)

## rango-sauto 설계 (coq-hammer-tactics, idle시 설치·구현) — 창의적
### 핵심 아이디어: retrieval-guided sauto (retrieval을 hammer에 먹임)
- 단순 `sauto.`가 아니라, **우리가 잘 찾는 top premise를 sauto에 use로 넣음**: `sauto use: p1, p2, p3.`
- 근거: idx840(load_rule)·or_and_distrib(orb_andb_distrib_r)처럼 **retrieval은 정답 lemma를 Top1로 찾는데 모델이 apply를 못함** → sauto가 그 lemma를 받아 자동으로 올바르게 적용/재구성. ATP 없이도 sauto-tactics만으로 강력.
- 강제후보(get_recs append, apply_hint 확장 sauto_hint flag): `sauto.`, `sauto use: <top3 premise>.`, `hauto use: <top3>.`, `best.`. classical+memo가 시도.
### 구현 단계 (idle=GPU free일 때)
1. `opam install -y coq-hammer-tactics.1.3.2+8.18` (Coq 8.18 정확히 매칭, Coq 안 건드림). 실험 idle 확인 후.
2. Hammer import 주입: proof_manager.check_proof의 `contents = file_prefix+partial_proof` 앞에 flag시 `From Hammer Require Import Tactics.\n` 프리펜드(위치어긋남/assert 주의 → 스모크로 검증). 안 되면 coqpyt 워크스페이스 프리로드 대안.
3. lm_example에 sauto_hint flag → self.forced_premises 기반 sauto use 후보를 get_recs가 주입(_append_forced_apply에 sauto 변형 추가).
4. alias rango-sauto = classical+memo + sauto_hint + hammer preamble. 스모크(test 6/840) → 큐.
### 주의
- 실행 중 opam install 금지(락/재빌드로 실험 깨짐). 반드시 idle.
- ATP 미설치 → 완전 hammer 아님, sauto/hauto/best만. 충분히 강력.

## [사용자 아이디어 2026-07-06] rango-search: Coq `Search`로 built-in premise 찾기 (방향1 구현안)
- **문제**: BM25 retrieval은 프로젝트 증명만 검색 → stdlib built-in lemma(orb_andb_distrib_r, demorgan1 등) 못 찾음. or_and_distrib 실패 원인.
- **해결**: Coq `Search <pattern>` = 로드된 모든 라이브러리(stdlib 포함)에서 매칭 lemma 반환. coqpyt 지원 확인(proof_file.py `__get_queries`/`get_diagnostics`가 query 결과 메시지 캡처).
- **설계**: 초기 goal(step<=1, sparse)에서 goal의 head 심볼/패턴으로 `Search (f _ _)` 실행→출력에서 lemma 이름 파싱→강제후보 `rewrite <l>`/`apply <l>`/`sauto use: <l>` 주입. sauto와 결합(Search로 찾은 stdlib lemma를 sauto use로).
- **구현 난이도**: 중. (a)패턴 도출(equality goal은 `Search (lhs_head _)`), (b)proof_manager/client로 Search 실행+메시지 파싱(check_proof 유사, add_step `Search ...` 후 diagnostic 읽기), (c)파싱. GPU-free 창에서 라이브 Coq client로 테스트 필요.
- alias rango-search. sauto처럼 sparse(초기goal). 우선순위: sparse-sauto 결과 본 뒤.

## MR2 expert iteration 계획 (사용자 승인, 추천안A: sauto/Search 후 착수)
- **실현 가능 확인**: 성공 증명이 로그에 `CURRENT PROOF:`로 남음. 대실행(20260701-061839)에 379개 성공 증명 존재 → 데이터 확보. train_decoder.py(get_datasets, LmDataset)로 재학습.
- **단계**:
  1. 모든 all_results 로그 + rango.json에서 (theorem, 성공proof) 수집·중복제거 → scripts/collect_successes.py.
  2. LmDataset 포맷(state→tactic)으로 변환, 기존 학습셋에 추가.
  3. LoRA 재학습(train_decoder.py) → 새 checkpoint → alias rango-exit.
  4. 재평가(20개@600, baseline600 대비). 개선되면 curriculum 반복.
- **정직한 한계**: 성공 증명 대부분이 이미 fine-tune 분포 내(쉬운 것) → 자기성공 재학습 효과 불확실. 진짜 이득은 **sauto/Search가 새로 딴 어려운 증명**을 학습셋에 넣을 때. 그래서 추천안A(sauto/Search 먼저 → 늘어난 성공셋으로 ExIt).
- GPU 학습이라 inference 실험 일시정지 필요.

## MR2 스코핑 결과 (2026-07-06) — 큰 작업, 낮은 payoff
- 학습 데이터는 (proof_state→next_tactic) 예제 포맷(LmProcessedDataset, tactic_data.py). raw proof를 넣는 게 아님.
- 찾은 증명→학습예제 변환 = **각 증명을 단계별 재실행(Coq)해 상태 추출 + retrieval 포맷팅** = 데이터빌드 파이프라인 재구동. 상당한 엔지니어링.
- payoff 불확실: 찾은 성공증명 대부분이 이미 fine-tune 분포 내(쉬운 test정리) → 자기재학습 이득 제한적. 진짜 이득은 sauto/Search가 딴 '새로운' 증명인데 그건 0개였음(sauto 하드코어 0).
- **정직한 판단**: MR2를 지금 셋업에서 제대로 하려면 큰 투자인데 개선 기대 낮음. 사용자에게 go/no-go 제시 필요.
- 대안(더 유망): (a) 학습 데이터를 TEST가 아니라 더 어려운/많은 정리로, (b) 더 큰 base 모델, (c) curriculum(쉬운→어려운).

## [대기] BFS-Prover 기법 이식 (사용자 요청, 헤비레버 4→1→3→2 이후)
- **주의**: BFS-Prover(ByteDance 2025)는 **Lean/miniF2F** 기반 — 그 모델/체크포인트를 Coq에 직접 못 씀. 우리 실험 = **기법 이식**.
- 핵심 기법:
  1. **length-normalized best-first**: tactic score를 길이/토큰수로 정규화해 짧은 증명 편향 제거(우리 ClassicalSearcher score에 적용 가능).
  2. **expert iteration + DPO**: 성공 tactic을 chosen, 실패를 rejected로 preference 학습(item 3 expert-iter의 강화판).
  3. **BFS 스케일링**: 컴퓨트↑에 best-first가 잘 scale(우리 baseline은 straight-line이라 비교 의미).
- 우리 맥락 실험안: (a) ClassicalSearcher에 length-norm 스코어 옵션(`rango-lnbfs`), (b) MR1 value + length-norm 결합, (c) expert-iter를 DPO로.
- 정직한 리스크: 우리 발견상 best-first(classical)가 straight-line baseline에 이미 -3. length-norm이 그걸 뒤집을지는 실측 필요. BFS-Prover 이득은 Lean/miniF2F에서였음.

## [학습(training) 로드맵] full 재현 — ablation study 방식 (2026-07-10 사용자 지시)
현재까지: 논문들의 **탐색 알고리즘만** 구현(rmaxts/bfs-prover/rango-qed). 학습부는 전부 미구현.
ablation study가 확인: 탐색 컴포넌트는 성능 상한 8~10/20, **논문 SOTA는 학습된 모델에서 나옴** → 학습이 진짜 레버.

### 순서 (전부 "테크닉 하나씩 켜며" ablation)
1. **GRPO (DeepSeek-Prover-V1.5 full)** ← 최종 목표 1순위
   - Coq 증명 성공/실패 → reward. 우리 정책 모델 GRPO 재학습. ablation: reward설계/KL/group size.
2. **BFS-Prover full** = 탐색(done) + **expert-iteration + DPO**
   - 성공 tactic=chosen, 실패=rejected preference. ablation: expert-iter만 vs +DPO, 데이터필터.
3. **QEDCartographer full (후순위)** = 탐색(done) + **value iteration(reward-free RL) + coq2vec 사전학습**
   - 현재 rango-qed는 1-pass γ^dist 회귀(단순화). full=반복 Bellman value iteration + online expert-iter. ablation: iteration 수, coq2vec 유무.

### 핵심: 1·2는 "성공증명으로 정책 재학습"이라 대부분 겹침
공통 인프라(성공증명 수집→preference/reward→재학습)를 GRPO로 먼저 구축 → BFS-full/QED-full은 그 변형.
데이터: collect_successes.py(수정필요) + 우리 실험들의 성공 증명 재활용.
