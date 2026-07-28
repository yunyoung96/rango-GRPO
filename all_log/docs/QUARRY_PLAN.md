# Quarry (Planning to Hammer, 2606.17981) — FULL 구현 계획 (최종 작업)

> **[구현 완료 2026-07-10 KST]** 아래 6개 컴포넌트 전부 코드화. 평가(실험)만 마지막에 실행 예정.
> 구현 파일:
> - `src/model_deployment/quarry_features.py` — φ 28차원 (C, 텍스트 레벨 intro 시뮬)
> - `src/model_deployment/quarry_difficulty.py` — 선형 난이도 모델 + pairwise 학습 (C, F)
> - `src/model_deployment/quarry_searcher.py` — 분해생성/파서/검증/hammer/재귀 SolveGoal (A,B,D,E)
> - `scripts/train_quarry_difficulty.py` — Algorithm 2 오프라인 학습 (F)
> - raw 생성 경로: `model_wrapper.generate_raw` → server `generate_raw` RPC → client `generate_raw`
> - alias: `quarry`(학습 θ), `quarry-heur`(heuristic θ), `quarry-trace`(trace 수집)
> **핵심 환경 대체**: check_proof가 "admit."/"Lemma" 문자열을 차단 → admit 기반 type-check 불가.
> 대신 `assert (ℓ) as H.` 서브골을 **재귀로 실제 증명**해 스플라이스(admit 없이 동등 검증, Qed 확인).
> 순수-로직(특징/난이도/파서) 단위테스트 통과. OCaml/opam 불변.


> 사용자 지시: **맨 마지막에 ablation 없이 full 구현, 하나도 빠뜨리지 말 것.**
> ★우리 환경에 이상적: **Rocq(Coq) 네이티브** + CoqHammer(설치됨) + LLM(rango 1.3B) + coqpyt(=SerAPI 역할).
> Lean 논문들(rmaxts/bfs)과 달리 모델 핸디캡 적음 — 제대로 성능 날 여지.

## 프레임워크 = Planning(LLM 분해) + Execution(CoqHammer 실행), 난이도 모델로 랭킹

## 구현 컴포넌트 (전부 필수 — 하나도 안 빠뜨림)

### A. 분해 생성 (LLM)
- goal에서 **k=8개 후보** 생성. 각 후보 c = 서브레마 L(c)={ℓ₁..ℓₘ} + target 증명 p(c)(서브레마 가정하고 goal 닫는 tactic script).
- 출력 포맷: `[LEMMA]...[END]` 블록들 + `[TARGET]...[END]` 하나.
- 프롬프트: 논문은 artifact에만 있음 → **직접 설계**(few-shot로 [LEMMA]/[TARGET] 포맷 유도).

### B. 분해 검증 (Coq/coqpyt)
- 서브레마들을 `Admitted`로 등록 → target 증명 p(c)가 그 context에서 goal을 **type-check로 닫는지** 확인.
- 유효 후보 V = type-check 통과한 것들만.

### C. 난이도 모델 (선형)
- `d_θ(ℓ) = θ^T φ(ℓ) + β`, **φ=28차원**:
  - **intros-state 19개**(`repeat intro` 후): num_goals, goal_len, goal_tok_count, forall_left, goal_arrow, goal_logic_ops, cmp_ops, is_contra_goal, num_hyps, hyp_total_len, hyp_len_avg, hyp_len_max, hyp_tok_count_total, hyp_tok_count_max, hyp_logic_ops_total, match_fix_let, mapset_tokens (+2 더)
  - **statement 9개**: stmt_len, stmt_tok_count, stmt_forall, stmt_exists, stmt_arrow, stmt_logic_ops, stmt_cmp_ops, stmt_match_fix_let, stmt_is_eq_goal
- **학습**: pairwise margin ranking. `θ ← argmin Σ_{(s+,s-)} max(0, μ−(s−−s+))² + λ‖θ‖²`. 성공 후보=낮은 난이도.
  - label = 재귀 CoqHammer 성공 여부(binary). 학습셋=CoqGym 200 goals(테스트와 project 분리).
  - 미명시: μ(margin), λ → 기본값 μ=1.0, λ=1e-3 사용. feature 표준화 적용.

### D. 재귀 실행 (Algorithm 1)
```
SolveGoal(G, budget):
  if CoqHammer(G): return true          # Phase1 fast path
  if budget ≤ 0: return false
  C ← LLM_Generate(G, k=8)               # Phase2
  V ← {c | RocqVerify(G,c)}
  V_ranked ← sort V by max_{ℓ∈L(c)} d_θ(ℓ) ascending
  for c in V_ranked[:B=1]:               # Phase3
    if all(SolveGoal(ℓ, budget−1) for ℓ in L(c)):
      ExecuteProof(p(c), G); return true
  return false
```
- 파라미터: k=8, B=1, max depth=5, LLM 60req/theorem, CoqHammer 30s/goal, LLM 90s/req, 벽시계 10분/theorem.

### E. CoqHammer 통합
- fast-path(분해 전) + leaf에서. 30s timeout. 우리는 `sauto`/`hauto`(+premise). 
- 표준 premise-selection+ATP는 우리에 외부 ATP 없음 → sauto/hauto/qauto 조합으로 대체(우리 환경 최대치).

### F. 오프라인 학습 (Algorithm 2)
- trace 수집: nodes.jsonl(goal, depth, intros-snapshot), candidates.jsonl(후보, 검증에러, 난이도, 재귀결과).
- θ 학습(pairwise). → 난이도 모델 저장.

## 구현 순서 (full, 최종 작업)
1. 특징 추출기 φ(ℓ) 28차원 (coqpyt로 intros-state + statement 파싱)
2. LLM 분해 생성 + 포맷 파서 ([LEMMA]/[TARGET])
3. Coq 검증(admit 서브레마 + target type-check)
4. CoqHammer fast-path (sauto/hauto)
5. 재귀 SolveGoal (Algorithm 1)
6. 난이도 모델: 먼저 heuristic(φ 가중합) → trace 수집 → pairwise 학습 → 교체
7. alias `quarry`, 평가 first-20/40

## 미명시 → 기본값
μ=1.0, λ=1e-3, feature 표준화 O, CoqHammer=sauto(30s)+hauto fallback, 프롬프트=few-shot 직접설계.

## 순위: 로드맵 최종 (40-round → GRPO → BFS-full → QED-full → **Quarry full**)
단, Quarry는 Coq-native라 성능 기대 높음 — 필요시 우선순위 조정 가능(사용자 확인).

## ★제약 (사용자): OCaml 버전 변경 금지
opam switch(coqstoq: Coq8.18/coq-hammer-tactics1.3.2/OCaml4.14) 절대 안 건드림.
→ SerAPI(X) → coqpyt(O), full-hammer+외부ATP(X) → 기존 sauto/hauto(O). 신규는 전부 Python 레벨.
