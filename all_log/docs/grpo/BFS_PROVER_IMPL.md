# BFS-Prover (arXiv:2502.03438) — 우리 구현 정리

작성 2026-07-28. 원논문 [BFS-Prover 2502.03438](https://arxiv.org/abs/2502.03438) (ByteDance, 2025, Lean4, 7B).
관련: [[SUBGOAL_RL_RESEARCH_ALL]], `METHODS.md`(§bfs-prover), `IMPLEMENTATION.md`(§DPO·§Expert-Iteration).
목적: "이 논문을 정확히 어떻게 구현했나"의 파일별 대조.

---

## 1. 논문 BFS-Prover 요약 (3요소)

1. **length-normalized best-first search (BFS)**: 노드 우선순위
   `score(s_L) = ( Σ_{t=0}^{L-1} log p(a_t|s_t) ) / L^α` — 경로 tactic log-prob 합을 길이 `L^α`로 나눔.
   누적 log-prob의 "짧은 증명 편향"을 완화해 **깊은 증명 탐색을 장려**. 논문 평가값 **α=0.5**.
2. **expert iteration + strategic data filtering**: 라운드마다 정책으로 탐색 → 성공 trace를 학습 데이터화. 각 라운드에서 **beam expansion으로 이미 풀리는 문제는 제외**하고 어려운 문제에 집중.
3. **DPO (compiler-feedback 선호쌍)**: `(state, tactic)` 쌍을 컴파일러 피드백으로 자동 라벨 → **VALID/성공 tactic = chosen, 에러 tactic = rejected**로 DPO 선호학습.

base = 7B, Lean4, verifier=Lean 컴파일러.

---

## 2. 우리 구현 (파일별 매핑)

### A. 탐색 — `src/model_deployment/bfs_prover_searcher.py` ★충실 재구현·실행됨
논문의 length-normalized best-first를 그대로:
- `_score(cum_logprob, depth) = cum_logprob / max(1,depth)**alpha` (L.113) — 논문 식 그대로.
- priority queue = `heapq`에 `-score` push(min-heap→최고 score pop, L.166).
- **확장**: pop한 노드에서 정책 LLM이 `expand_width=E` tactic 샘플(`get_recs(..., beam=False)` = temperature 샘플링, 주석상 temp 1.1). 각 tactic을 Coq로 check:
  - `COMPLETE` → 성공 반환(+성공경로 표시).
  - `VALID` → `cum += tac_logprob`, `depth+1`, score 재계산 후 큐 push (L.159-166).
  - `INVALID` → terminal, 버림 (L.167).
- `alpha=0.5`, `expand_width=2`, `max_depth=50` (논문 평가값, L.34-36).
- `seen` graph 가드 있으나 주석대로 **순수 tree**로 운용(goal 병합 안 함, `Proof.` 같은 불변 tactic이 스킵돼 진전 막히는 것 방지, max_depth로 bound — L.133).
- `trace_out` 켜면 **탐색 트리를 jsonl로 덤프**(노드=state_example + 시도 tactic들 + 결과 + leads_to_success) → 학습 데이터 소스 (`_record_state/_record_tactic/_mark_success_path/_dump_trace`).

**별칭**(`run_thm.py`): `bfs-prover`(α0.5), `bfs-a0`(α0.0=정규화 없음), `bfs-a1`(α1.0=완전 평균), `bfs-prover-trace`(트리 덤프 on). → **α ablation을 위해 3버전** 준비.

**논문과의 차이(명시)**: Lean→**Coq**, 정책=**우리 DeepSeek-Coder-1.3B**(논문 7B BFS-Prover 학습모델 없음), rango 탐색과 **안 섞은 순수 BFS**. → "탐색 알고리즘만 충실 재현, 학습모델은 우리 것".

### B. 학습 파이프라인(expert-iteration) — `src/tactic_gen/bfs_expert_iter.py`
라운드 루프 오케스트레이션(L.85-94):
1. `run_search` → `bfs-prover-trace`로 train 정리 탐색, `trees.jsonl` 덤프.
2. `extract_round` → SFT + DPO쌍 추출.
3. `run_dpo` → `dpo_train.py`로 DPO 학습 → 새 adapter → 다음 라운드 init.

⚠ **한계**: SFT 단계는 "데모로 미완, DPO 위주"라 주석(L.92) — 완전한 expert-iter(성공 trace SFT + 데이터 필터링)는 **스캐폴딩만** 되고 풀 재현은 안 됨.

### C. 데이터 추출 — `src/tactic_gen/bfs_dpo_data.py`
- `extract_sft`: 트리에서 `leads_to_success`인 `(state, tactic)` → SFT 예제.
- `extract_dpo_pairs`: **같은 state**에서 `chosen`=성공경로 tactic × `rejected`=(`INVALID` 또는 비성공) tactic의 곱 쌍. (한 state에 성공·실패 둘 다 있어야 쌍 생성) — 논문의 compiler-feedback 선호쌍과 동형.

### D. DPO 코어 — `src/tactic_gen/dpo.py` (+ `dpo_train.py` 진입점)
Rafailov et al. DPO 손실 그대로(L.19-32):
`L = −log σ( β·[ (logπθ(y_w)−logπref(y_w)) − (logπθ(y_l)−logπref(y_l)) ] )`, **β=0.1**.
시퀀스 logprob은 `grpo_train.sequence_token_logprobs` 재사용, completion mask로 합산.

### E. validity-DPO 변형(★우리가 실제로 돌린 것) — `grpo_train.py --dpo` + `all_log/run_vdpo.sh`
논문 DPO를 **on-policy·dead-group 친화**로 단순화해 GRPO 학습기에 통합(`grpo_train.py` L.174-212):
- 같은 `state_key`에서 **chosen=VALID tactic / rejected=INVALID(Coq 에러) tactic** 인접쌍. 두 row prompt 동일 보장(DPO 전제).
- **핵심 동기**: dead group(증명 못 찾은 78%)에서도 "에러 tactic" 사실은 남으므로 **쌍이 나옴** → GRPO가 신호 0인 구간에서도 학습. (배우는 축: "증명을 찾아라"가 아니라 "깨진 tactic을 내지 마라" → 탐색예산 낭비↓)
- `run_vdpo.sh`: init=`rango-grpo-fix`, 데이터=`luffy.jsonl` 재사용(INVALID step 포함), β=0.1, micro_bsz=2(쌍 정렬). @20 게이트(우리 rango 11 이상)→@40, 미달 시 접음.
- 별칭 `bfs-dpo` = `models/bfs-dpo/adapter`(DPO 학습) + BFS 탐색 / `rango-grpo-vdpo` = validity-DPO adapter.

---

## 3. 충실도 요약

| 논문 요소 | 우리 구현 | 상태 |
|---|---|---|
| length-normalized best-first (α=0.5) | `bfs_prover_searcher.py` 식 그대로 | **충실·실행됨** (+α ablation) |
| expert iteration 라운드 | `bfs_expert_iter.py` 오케스트레이션 | 스캐폴딩(SFT 단계 미완) |
| 데이터 필터링(쉬운 문제 제외) | 미구현 | ✗ |
| DPO 선호학습 | `dpo.py`(Rafailov, β0.1) + validity 변형 | **코어 충실**, validity로 단순화해 실행 |
| base 7B Lean | 우리 Coq-1.3B | 대체(모델 없음) |

→ **"탐색 알고리즘은 논문 충실 재현·ablation까지, 전체 self-improvement(expert-iter+DPO) 학습은 부분 구현/validity-DPO로 대체 실행."**

---

## 4. 실측 결과 (우리 Coq-1.3B 정책 기준)

⚠ `@N`은 서로 다른 정리 부분집합(@20·@40·@180 직접 비교 불가), 표본 작음(노이즈). [[no-published-baseline]]에 따라 **우리 rango끼리만** 비교.

| alias | 정책 | 탐색 | 결과 |
|---|---|---|---|
| `bfs-prover` (α0.5) | Coq-1.3B | BFS α0.5 | @20 **10/20 50%**, @40 13/40 32.5% |
| `bfs-a0` (α0.0) | Coq-1.3B | BFS α0(정규화 없음) | @20 7/20 35%, @40 12/40 30% |
| `bfs-a1` (α1.0) | Coq-1.3B | BFS α1(완전 평균) | @20 9/20 45%, @40 **16/40 40%**, @180 49/180 27.2% |
| `bfs-dpo` | DPO 학습 | BFS α0.5 | @40 13/40 32.5% |
| `rango-grpo-bfs` | **GRPO 학습** | BFS α0.5 | @40 **15/40 37.5%** |
| `rango-grpo-vdpo` | validity-DPO | (평가) | 게이트 기반, 명확한 held-out 수치 미기록 |

**해석**:
- **α 정규화는 효과 있음**(α0 최하). 단 논문값 α0.5가 우리 Coq에서 항상 최고는 아님 — @40/@180에선 **α1.0이 더 나음**(작은 표본 주의).
- **DPO 이득 없음**: `bfs-dpo`(32.5%) = plain `bfs-prover`(32.5%)@40 동일 → DPO 학습이 BFS 탐색 성능을 못 올림.
- **정책 품질 > 탐색 튜닝**: `rango-grpo-bfs`(GRPO 정책+BFS) 37.5% 가 BFS 계열 중 @40 최고 → 탐색 α보다 **정책이 지배적**.

---

## 5. 결론 / 한계
- BFS-Prover의 **탐색(length-normalized best-first)은 충실히 재현·ablation**했고, DPO **코어도 재현**했으나, **전체 expert-iteration 자기개선 루프는 부분 구현**(SFT/데이터필터링 미완)이라 "논문 full 재현"은 아님.
- 우리 세팅(Coq-1.3B)에서 **DPO/validity-DPO는 뚜렷한 이득 없음**, 성능은 **정책 품질(GRPO)**이 좌우. → BFS-Prover식 DPO는 우리 규모에서 우선순위 낮음(접힘 계열).
- 참고: validity-DPO의 "dead group에서도 쌍 생성" 동기는 [[research-direction-2026-07]]의 dead-group 병목 문제의식과 같은 계열이나, 실측 이득은 확인 안 됨.
