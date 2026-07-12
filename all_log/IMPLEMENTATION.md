# 구현 상세 문서 (Implementation Details)

> 이 문서는 우리가 구현한 모든 알고리즘의 **코드 레벨 디테일**을 담는다.
> 대상: RMaxTS · BFS-Prover · QEDCartographer · Quarry · GRPO · DPO(BFS-full) · effectiveness study · transplant miner.
> 각 항목: 파일 위치 → 자료구조 → 핵심 수식/알고리즘 → **까다로운 구현 디테일(gotcha)** → 파라미터/alias → 한계.
> 베이스: rango = DeepSeek-Coder-1.3B-instruct + LoRA(BM25 proof + TF-IDF premise retrieval), Coq 8.18, coqpyt.

## 콜아웃 범례 (스캔용 색상 코딩)

> 🟦 **개념** — ML을 몰라도 이해되도록 풀어쓴 설명
> 🟨 **함정(gotcha)** — 실제로 부딪힌 버그·제약·우회
> 🟥 **결과** — @40 성능 (baseline = published Rango 12/40)

---

## 0. 공통 인프라 (모든 searcher가 쓰는 인터페이스)

> 🟦 **개념 · 이 시스템이 하는 일**
> Coq에서 정리를 증명한다 = **tactic(증명 명령)을 한 줄씩** 쳐서 목표(goal)를 없애는 것.
> 우리 모델은 "지금 goal에서 다음에 칠 tactic 한 줄"을 예측한다(**next-tactic 정책**).
> 그 줄을 Coq에 실제로 넣어보고(`check_proof`), 통과하면 다음으로 나아간다.

### 0.1 ProofManager (coqpyt 래퍼) — `src/model_deployment/proof_manager.py`
- `check_proof(partial_proof: str, theorem) -> ProofCheckResult`
  - 반환: `tactic_result ∈ {COMPLETE, VALID, INVALID}`, `current_goals: list[Goal]`, `new_proof: Proof`
  - `"Qed."`가 들어오면 스스로 detect(직접 붙이지 말 것).

> 🟨 **함정 · admit 금지 (매우 중요)**
> `check_proof`는 `partial_proof`에 `"Theorem"/"Lemma"/"Proposition"/"Remark"/"Corollary"/"Property"/"Admitted."/"admit."/"Abort."` 문자열이 있으면 **무조건 INVALID**로 막는다.
> → **admit 기반 트릭 불가, 새 Lemma 선언 불가.** Quarry(§4) 설계가 여기 정면으로 걸려서 assert+재귀로 우회했다.
- `build_dset_file(new_proof) -> DatasetFile` : 현재 proof 상태를 retrieval/formatter용 DatasetFile로.
- `get_initial_context() -> DatasetFile` : theorem 로드.

### 0.2 Goal 구조 — `coqpyt.coq.lsp.structs`
- `Goal(hyps: list[Hyp], ty: str)` — `ty`=현재 목표 명제 문자열, `hyps`=가설들
- `Hyp(names: list[str], ty: str, definition: Optional[str])`
- goal_key(상태 해시) = `"\n===\n".join(repr(g) for g in goals)` (RMaxTS/BFS 공통)

### 0.3 정책(모델) 클라이언트 — `src/model_deployment/tactic_gen_client.py`
- `LocalTacticGenClient.get_recs(step_idx, proof, dset, n, beam, file_prefix) -> ModelResult`
  - `ModelResult.next_tactic_list: list[str]`, `.score_list: list[float]`(= Σ token log-prob)
  - `beam=False` → temperature=1.0 샘플링, `beam=True` → beam.
  - 내부: `formatter.example_from_step(...)` → 서버 RPC → 모델 생성. **retrieval(BM25 proof + TF-IDF premise)이 이 example에 이미 포함됨.**
- **자유형 생성(신규 추가, Quarry/GRPO용)**: `generate_raw(prompt, n, max_new_tokens, temperature) -> list[str]`
  - 경로: `model_wrapper.DecoderLocalWrapper.generate_raw` → server RPC `generate_raw` → client. collator 우회, prompt 그대로 토크나이즈.

### 0.4 실행 하네스
- `scripts/run_thm.py` : `get_searcher_conf(alias)` + `get_tactic_confs(alias, split)` → 서버 기동 → `run_proof` → searcher.
- `scripts/run_all.py` : 여러 idx 배치. **하드 타임아웃 = timeout+300s**, `subprocess.Popen(start_new_session=True)` + `os.killpg(SIGKILL)` (hang 방지). 출력 dir = `all_results/<timestamp>_<alias>`. `--idx-file`로 명시 인덱스 리스트(커리큘럼).
- `src/model_deployment/searcher.py` : conf→searcher 디스패치(`searcher_from_conf`).

---

## 1. RMaxTS (DeepSeek-Prover-V1.5 탐색부) — `src/model_deployment/rmaxts_searcher.py`

> 🟦 **개념 · MCTS / UCB**
> 증명을 **나무(tree)**로 탐색한다. 노드=증명 상태, 가지=친 tactic. 어디를 더 파볼지 정할 때 **UCB** 공식을 쓴다:
> "지금까지 좋았던 가지(활용)" + "덜 가본 가지(탐험)"의 균형. 바둑 AI(AlphaGo)가 쓰던 방식.

### 자료구조
```python
class RMaxNode:
    check_result   # ProofCheckResult (도달 상태)
    goal_key       # state 병합 키
    children: dict[str, RMaxNode]   # tactic -> 자식(도달 state, 병합됨)
    N: dict[str, float]             # N_γ(discounted visit)
    W: dict[str, float]             # W_γ(discounted value)
    tactics: list[str]              # 시도한 action들
```
`self.nodes: dict[goal_key, RMaxNode]` = **state 병합 테이블**(동일 state는 한 노드).

### 알고리즘 (논문 그대로)
- **DUCB 선택**: `Q = W_γ/N_γ + sqrt(2 ln ΣN_γ / N_γ)`, `γ=GAMMA=0.99`
- **RMax intrinsic reward**: `R = 1[롤아웃에서 새 노드 추가됨]` (외부보상 없음, novelty 탐색)
- **truncate-and-resume**: 선택 leaf에서 whole-proof 롤아웃 → 첫 에러에서 자르고 유효 prefix만 트리에 삽입
- **backprop**: 궤적 (s,a)마다 `N←γN+1`, `W←γW+R`

> 🟨 **함정 · Proof. self-loop & 사이클**
> 1. **Proof.-self-loop**: `Proof.`/bullet은 goal을 안 바꿔 goal_key가 root와 같아짐 → self-merge → 무한 self-loop(같은 tactic 194회). **수정**: `_expand`에서 goal 불변 tactic은 트리 노드를 안 만들고 로컬 script만 전진(`cur_check` 별도), goal 변할 때만 노드 생성/병합.
> 2. **state-merge 사이클**: 병합이 그래프 사이클(A→B→A) 생성 → `_select`의 `while node.children` 무한. **수정**: `visited: set[int]` + `len(path) < 2*n_rollout_steps+50` 경계.
> 3. rollout 내 `get_recs(n=1, beam=False)` = temperature 샘플(다양성).

### ablation 플래그 & alias
- `use_reward`(RMax reward), `use_merge`(state merge), `use_ducb`(DUCB vs uniform random)
- alias: `rmaxts` / `rmaxts-noreward` / `rmaxts-nomerge` / `rmaxts-nomcts`
- 파라미터: `n_rollout_steps=8`, `timeout`(기본 600)

> 🟥 **결과 · @40 ablation**
> full 11 · **−reward 14** · −merge 13 · −DUCB 12 (baseline 12). **정교한 장치(reward/merge/DUCB)를 뗄수록 좋아진다** → 미학습 1.3B엔 MCTS 무효.

---

## 2. BFS-Prover (탐색부) — `src/model_deployment/bfs_prover_searcher.py`

> 🟦 **개념 · best-first + 길이 정규화**
> 지금까지 "가장 그럴듯한(확률 높은)" 부분증명부터 우선 확장한다(best-first). 단, 긴 증명은 확률 곱이 작아져 불리하므로 **길이로 나눠(÷L^α) 공정하게** 만든다. 깊은 증명 탐색을 장려.

### 알고리즘
- **length-normalized best-first**: 노드 우선순위
  `score(s_L) = (Σ_{t} log p(a_t|s_t)) / L^α`, `L`=경로 tactic 수, `α=0.5`(논문)
- heapq(min-heap) on `-score`. `_QNode(neg_score, seq, check_result, cum_logprob, depth, node_id)`
- **expansion**: pop → `get_recs(n=expand_width=2, beam=False)` → 각 tactic:
  COMPLETE→성공 / VALID→`cum += tac_logprob; depth+=1; push` / INVALID→버림
- **pure tree** (goal_key 병합/skip 안 함). `max_depth=50`으로 bound.

> 🟨 **함정 · seen-skip 제거 & 트리 덤프**
> 1. **goal_key seen-skip 제거**: 원래 seen-set으로 중복 state skip했으나 `Proof.`가 goal 불변이라 skip돼 진전 막힘 → 제거하고 pure tree로.
> 2. **트리 덤프(expert-iter/DPO용, 신규)**: `trace_out` 설정 시 각 노드에 `state_example`(LmExample json)+시도 tactic들 기록. COMPLETE 시 `_mark_success_path`로 root까지 부모 tactic을 `leads_to_success=True` backprop. alias `bfs-prover-trace`.

### alias & 결과
- `bfs-prover`(α=0.5) / `bfs-a0`(α=0) / `bfs-a1`(α=1.0)
> 🟥 **결과 · @40**
> α=0 → 12 · α=0.5 → 13 · **α=1.0 → 16**(최고 단일 탐색법). length-norm이 클수록 여기선 유리.

---

## 3. QEDCartographer (value iteration) — `qed_cartographer.py` + `qed_value_iter.py`

> 🟦 **개념 · value(가치) 함수**
> "이 상태에서 증명이 **얼마나 가까운가**"를 0~1로 매기는 신경망(value). 가까운 상태부터 파본다.
> value = γ^(QED까지 남은 스텝) 을 학습. 여러 subgoal이면 **곱(AND: 다 닫아야 함)**으로 합친다.

### 모델
- `Coq2Vec` : 토큰 임베딩 → LSTM → 마지막 hidden(상태벡터). `encode_ids(goal)` = `hash(tok)%vocab`.
  (🟨 함정: `padded = torch.zeros(..., device=self.emb.weight.device)` — CPU/CUDA 불일치 방지.)
- `QEDValue` : `sigmoid(MLP(z)) ∈ (0,1)` = γ^(QED까지 거리) 추정.
- `QEDValuePredictor.value_state(goals, backup)` : 다중 subgoal 상태값
  - `product`(논문/AND) = `∏ V(gᵢ)`, `sum`/`min`/`mean` = ablation

### value iteration — `qed_value_iter.py`
- **bootstrap**: `V(s) = γ · max_child V(child)`, solved leaf=1, dead=0. `γ=GAMMA=0.9`.
- **closed-form**: `V*(goal) = γ^dist` (성공경로 dist, 아니면 0).
- **★증명적 사실**: OR-트리에서 **closed-form == bootstrap 고정점** (단위테스트로 실증). 그래서 기존 closed-form 학습이 이미 충분.
- 학습데이터: `data/vguided_trees/*.jsonl` (classical_searcher `_dump_tree`가 `(goal,label,dist,node_id,children,solved)` 덤프. AND-OR 엣지는 하위호환 추가).

### 학습/평가
- `scripts/train_qed_value.py --mode {closed-form,bootstrap} --gamma --backup {product,sum,min}`
- 검색: `classical_searcher`의 `_value_of`가 product backup으로 frontier 정렬. `value_weight>0`로 활성.
- alias: `rango-qed`(product) / `rango-qed-sum` / `rango-qed-min`
> 🟥 **결과 · @40 backup ablation**
> product 11 · sum 10 · min 11 (baseline 12). value-guided 탐색은 이 세팅에서 효과 없음(product>sum는 논문과 일치).

---

## 4. Quarry (Planning to Hammer) — `quarry_searcher.py` + `quarry_features.py` + `quarry_difficulty.py`

> 🟦 **개념 · 분해(decomposition)**
> 어려운 정리를 **보조정리 여러 개로 쪼갠 뒤**, 각 조각을 자동증명기(CoqHammer의 sauto/hauto)로 닫고 다시 합친다.
> LLM이 "이렇게 쪼개라"를 제안(`[LEMMA]/[TARGET]` 블록), 난이도 모델이 쉬운 분해부터 시도.

### A. 분해 생성
- few-shot 프롬프트(`FEWSHOT`)로 `generate_raw(k=8)` → `[LEMMA]..[END]` 블록들 + `[TARGET]..[END]` 파싱(`parse_decomposition`).

### C. 28차원 난이도 특징 — `quarry_features.py`
- `N_FEATURES=28` = intros-state 19 + statement 9 (`FEATURE_NAMES`).
> 🟨 **함정 · intros-state 시뮬**: 실제 Coq `repeat intro` 대신 **텍스트 레벨 intro 시뮬**(`_split_intros`: `forall x.., body` 바인더 + `P -> Q` 전제를 hyp로, 남은 걸 goal로) — 무거운 Coq 왕복 회피.

### 난이도 모델 — `quarry_difficulty.py`
- `d_θ(ℓ) = θ^T z(φ(ℓ)) + β` (표준화 z). heuristic 초기화 또는 pairwise 학습.
- **pairwise margin ranking**: `loss = Σ max(0, μ−(d(s⁻)−d(s⁺)))² + λ‖θ‖²`, `μ=1.0, λ=1e-3`. 성공후보=낮은 난이도.

### D. 재귀 SolveGoal (Algorithm 1)
```
SolveGoal(prefix, goals, depth):
  1. hammer fast-path: HAMMER_TACTICS=[sauto,hauto,eauto,congruence,lia,easy,auto] 시도
  2. depth>=max_depth: return None
  3. decompose k=8 → 난이도 랭킹 → 상위 branch=1:
       각 서브레마 ℓ: "assert (ℓ) as HQ_n." → 서브골 생성 → 재귀로 실제 증명 → 스플라이스
       모든 ℓ 풀리면 target proof p(c) 적용 → goal 닫힘 확인
```
> 🟨 **함정 · admit 금지 우회**
> 논문은 "서브레마를 admit로 가정하고 type-check"하는데, `check_proof`가 `admit.`을 차단한다(§0).
> → **`assert (ℓ) as H.`가 만든 서브골을 재귀로 진짜 증명해 스플라이스** → 전체가 실제 Qed. admit 불필요.
> `_closes` 종료판정: `COMPLETE` 또는 `VALID and len(current_goals) < n_before`(focus goal 하나 닫힘, assert가 balanced해 건전).
- hyp 이름 `HQ{counter}` 전역 유일. target의 `H1,H2..` → 실제 이름 치환(`_rename_hyps`).

### alias & 결과 & 한계
- `quarry`(학습 θ) / `quarry-heur` / `quarry-trace`
> 🟥 **결과 · @40**
> **0/40**. 버그가 아니라 환경 불일치: ① rango 1.3B는 next-tactic 모델이라 `[LEMMA]/[TARGET]` 분해 형식을 못 만듦(tactic만 출력, generate_raw는 정상), ② CoqStoq 파일이 CoqHammer 미import → `sauto/hauto` "reference not found". Quarry 전제(대형 분해 LLM + CoqHammer) 미충족.

---

## 5. GRPO (RL 학습) — `grpo.py` + `grpo_rollout.py` + `grpo_train.py`

> 🟦 **개념 · SFT vs RL(강화학습)**
> **SFT**(지도학습)는 "정답 증명을 따라 쓰기"로 배운다. **RL**은 다르다: 모델이 **직접 여러 번 증명을 시도**하고,
> **성공한 시도의 행동은 확률↑, 실패는 확률↓**. 정답 대신 "결과(성공/실패)"로 배운다. GRPO는 그 RL 방법 중 하나.

> ⚠️ **논문과의 차이(정직)**: 논문 GRPO는 7B Lean **whole-proof** 정책. 우리는 **GRPO 알고리즘만** rango(1.3B Coq **next-tactic** + retrieval)에 이식. 알고리즘 충실, 대상 모델·설정 다름.

> 🟦 **개념 · advantage(그룹 상대)**
> 8번 시도 보상이 `[1,0,0,1,0,0,0,0]`이면, GRPO는 그룹 안에서 상대적으로 평가한다: 평균보다 잘한 시도=**양수(밀어올림)**,
> 못한 시도=**음수(눌러내림)**. 8개 다 실패면 우열 없어 신호 0 → 그 정리는 학습에 못 씀(이게 "성긴 신호" 문제).

> 🟦 **개념 · clip 과 KL 이 왜 있나**
> **clip**: 한 번에 확률을 너무 많이 바꾸면 학습이 폭주 → 비율을 0.8~1.2로 잘라 조금씩만. **KL**: 학습된 정책이 시작 정책에서
> 너무 멀어지지 않게 당기는 끈(β=0.04). 이 둘이 "안전하게 조금씩 개선"을 보장(PPO 계열 핵심).

### 코어 수식 — `grpo.py` (순수 텐서, 단위테스트 완료)
- `group_advantages(r)`: `Â = (r − mean)/(std + EPS_STD)`, `EPS_STD=1e-4`. std<eps면 0(신호 없음).
- `kl_unbiased(logp, logp_ref)`: `exp(Δ) − Δ − 1 ≥ 0` (DeepSeek unbiased estimator).
- `grpo_batch_loss`: `ratio = exp(logp_new − logp_old)`;
  `surrogate = min(ratio·Â, clip(ratio,1±ε)·Â)`; `loss = −mean(surrogate − β·KL)` over completion mask.
  `clip_eps=0.2, kl_beta=0.04`.

### rollout — `grpo_rollout.py` (searcher로 통합, run_thm 인프라 재사용)
```
정리당 G개 시도(다른 seed):
  for step in max_steps:
    example = formatter.example_from_step(...)      # retrieval 포함 입력
    tactic = get_recs(n=1, beam=False)              # temperature 샘플(한 줄)
    steps.append({example.to_json(), tactic})
    check = check_proof(prefix+tactic)
    COMPLETE→reward=1;break / INVALID→break
그룹 = {theorem, attempts:[{steps, reward}]}
```
- alias `grpo-rollout`(binary). 출력 `data/grpo_rollouts/rollouts.jsonl`.
- **dense reward(E2)**: 미완 시도에 `reward = shaping_coef · V(last_valid_goals)` (QED value), `coef=0.3`. alias `grpo-rollout-dense`.

### 학습 — `grpo_train.py`
- `build_completion_batch`: **prompt/completion 따로 토크나이즈 후 이어붙임**(subword 경계 보장, RLHF 표준). max_len 초과 시 prompt 앞을 자르고 completion 보존.
- `sequence_token_logprobs`: `logits[:, :-1]`로 shift → position t = `logp(token_t | <t)`, position 0 = 0.
- `flatten_group`: 그룹 → 시도별 advantage를 그 시도의 **모든 (state,tactic) step**에 부여.
- π_ref = base+LoRA 시작정책 **동결 복사**(deepcopy), π_old = π_ref (온폴리시 첫 라운드). 그룹 내 보상 균일이면 skip.
- 실제 실행: base=deepseek-coder-1.3b-instruct, init_adapter=rango checkpoint-54500, collator_conf=rango training_conf.yaml. lr=1e-6, epochs=2, micro_bsz=2.
> 🟨 **함정 · prompt 재현 & adapter 로드**
> rollout이 `example`(LmExample json) 저장 → 학습 때 `collator.collate_input`으로 서버와 **동일 prompt 재현**(collate_fn). 또 prompt/completion을 따로 토크나이즈해 이어붙여야 subword 경계 마스크가 안 깨짐.
> LoRA adapter 로드는 **부모 dir에 training_conf.yaml 필요**(get_training_conf가 `checkpoint.parent/training_conf.yaml` 읽음) → 학습 후 복사.

### 결과
- rollout 39그룹(신호 11) → 2epoch → adapter. 평가 alias `rango-grpo`(straight-line 탐색).
> 🟥 **결과 · @40**
> **16/40**. published Rango(12) 대비 +4, **우리 rango 재현 대비 +1**(idx 55 `agree_exten`만 진짜 유일). regress 0.
> idx 55 = "탐색으로 안 되던 마무리 수순을 RL이 완주" — rango는 매 궤적이 끝을 못 맺는데(valid-but-stuck), GRPO는 완주에 커밋.

---

## 6. BFS-full (expert-iteration + DPO) — `dpo.py` + `dpo_train.py` + `bfs_dpo_data.py` + `bfs_expert_iter.py`

> 🟦 **개념 · DPO(선호학습)**
> "같은 상황에서 **좋은 tactic(성공경로) vs 나쁜 tactic(실패)**"의 쌍을 주고, 좋은 쪽 확률을 상대적으로 올리게 학습.
> RL보다 단순(보상 함수 불필요). BFS 탐색 트리에서 쌍을 자동 추출.

### DPO 코어 — `dpo.py`
- `dpo_loss = −logσ( β·[ (logπ_w − logπ_l)_policy − (logπ_w − logπ_l)_ref ] )`, `β=0.1`.
- `w`=chosen(성공경로 tactic), `l`=rejected(실패 tactic).

### 데이터 추출 — `bfs_dpo_data.py` (BFS 트리 덤프에서)
- `extract_sft`: `leads_to_success` tactic의 (state, tactic) → SFT.
- `extract_dpo_pairs`: 같은 state에서 성공 tactic × 실패/INVALID tactic의 곱 쌍.

### 오케스트레이션 — `bfs_expert_iter.py`
- 라운드: 탐색(bfs-prover-trace) → 추출 → DPO 학습 → 반복.

### 결과 & 한계
- 트리 40정리 → SFT 129, **DPO쌍 35**(희소, expand_width=2 탓). DPO 3epoch, lr=5e-7.
> 🟥 **결과 · @40**
> **13/40** (baseline 12, +1). loss 0.69→0.68 · acc 0.53→0.58 = **학습 약함** — DPO 쌍이 35개로 너무 적어 신호 부족. untrained BFS와 동수.

---

## 7. Effectiveness study 인프라 (GRPO 변형)

각 실험 = rollout → 학습(→ `models/rango-grpo-e{N}/adapter`) → 평가(`rango-grpo-e{N}` alias, straight-line). 드라이버 `all_log/run_grpo_effstudy.sh`. baseline = GRPO round-1(16/40).

| 실험 | 조작 | rollout alias / 인자 | init_adapter |
|---|---|---|---|
| **E1 expert-iter** | round-1 정책으로 재-rollout | `grpo-rollout-r2` (models/rango-grpo/adapter) | rango-grpo/adapter |
| **E2 dense** | QED value 부분보상 | `grpo-rollout-dense` (qed_ckpt) | base rango |
| **E3 curriculum** | sibling-rich 정리 over-sample | `grpo-rollout --idx-file sibling_rich_train.txt`(353개) | base rango |
| **E4 scale** | G=16, 정리 60 | `grpo-rollout-g16` | base rango |

- 커리큘럼 인덱스: `data/grpo_curriculum/sibling_rich_train.txt` = statement-suffix 유사 sibling 보유(hs≥8/fm≥6, idx≥100) 353개.

---

## 8. suffix-transplant miner (방법 ②, negative result) — `scripts/mine_transplants.py`

### 파이프라인
1. 같은 파일 statement-유사(Jaccard≥0.55) 형제쌍.
2. `anti_unify_sigma(target_stmt, sib_stmt)`: SequenceMatcher로 위치별 토큰 diff → σ(sibling→target).
3. Phase1: 코퍼스 전체 σ aggregate → 전역 rename-family 사전(2회↑ 관측).
4. σ + family로 sibling proof 변환 → `compile_variant`로 **coqc 검증**.
5. **verify-repair**: 실패 시 "reference X not found" 파싱 → target 파일 vocab에서 최소 편집거리 analog 보정(`resolve_symbol`) → 재컴파일 반복.

### gotcha & negative result

> 🟨 **함정 · Section 닫기 필수**
> 대상 lemma가 `Section` 안이면 Qed 뒤에서 `End S.`로 닫아야 컴파일(안 하면 "section CMCONSTR needs to be closed"). `cov.open_sections_at` 사용.

> 🟥 **결과 · yield ~0.5% (negative result)**
> idx42류 `and→andl`은 **양쪽 다 정의된 의미적 rename** → "not found"가 아니라 **타입 에러** → name-repair 못 잡음. family 사전은 방향 노이즈(`al→a` 등).
> **함의**: rename family를 손으로 못 짬 → **학습 필요**(equivariance / neural transplant 동기).

### 관련 오프라인 분석
- `scripts/suffix_similarity_count.py` / `suffix_detail.py` : 전체 test에서 suffix-유사 sibling 보유 정리 수(§6 기준 hs≥4/fm≥3 → 953개). `poc_sigma_replay.py` : σ-replay coqc 검증 PoC(idx806/538 PASS).

---

## 9. 파라미터 요약표

| 알고리즘 | 핵심 상수 |
|---|---|
| RMaxTS | γ=0.99, n_rollout_steps=8 |
| BFS | α=0.5(0/1 ablation), expand_width=2, max_depth=50 |
| QED | γ=0.9, backup=product |
| Quarry | k=8, branch=1, max_depth=5, μ=1.0, λ=1e-3, φ=28dim |
| GRPO | clip_eps=0.2, kl_beta=0.04, lr=1e-6, G=8, epochs=2, EPS_STD=1e-4 |
| DPO | β=0.1, lr=5e-7, epochs=3 |
| dense reward | shaping_coef=0.3 (QED value) |

## 10. 핵심 gotcha 총정리 (재발 방지)
1. check_proof는 `admit./Lemma/Theorem` 문자열 차단 → 새 lemma/admit 불가.
2. `Proof.`/bullet은 goal 불변 → RMaxTS/BFS의 goal_key 병합/skip이 self-loop 유발 → 특수처리.
3. state-merge 그래프 사이클 → select 무한루프 → visited+경계.
4. run_all 하드 타임아웃(timeout+300, killpg SIGKILL) 없으면 거대 goal에 hang.
5. adapter 로드는 부모 dir에 training_conf.yaml 필요.
6. rollout prompt 재현은 collate_input(collator) — subword 경계 위해 prompt/completion 분리 토크나이즈.
7. transplant는 Section 닫기 필수.
8. `pkill -f "run..."`는 자기 자신 매치 → exit 144. `ps ... | grep [r]un` 브래킷 트릭 사용.
