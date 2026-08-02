# Planner–Executor for Coq — 구현 설계 (2026-07-29)

관련: [[BREAK_BOTTLENECK_LITERATURE]](근거·문헌), [[BOTTLENECK_ANALYSIS]](병목), [[MODEL_CANDIDATES]](로컬 모델), [[VALUE_FREE_SEARCH]](재사용할 search 뼈대).

**목표**: 병목(1.3B가 초반 분해를 **생성** 못 함, coverage 22%)을 **분해를 1.3B 밖 강한 로컬 planner에 맡겨** 우회. 1.3B는 subgoal별 tactic 실행만(강점). **1.3B 재학습 0.**

---

## 1. 아키텍처

```
정리 T ──► [Planner: 강한 로컬 LLM]  "이 goal을 어떻게 분해?"
              │  (few-shot Coq 프롬프트, 학습 안 함, 추론만)
              ▼
      고수준 계획 = 순서있는 구조적 move들:
        예) ["induction n", "destruct l", "apply Nat.add_comm", ...]
              │
              ▼
   [Executor: 우리 1.3B + coq-lsp]  각 move를 실제 tactic으로 실행·검증
        · move가 구조 tactic이면 그대로 적용(induction/destruct)
        · move가 "lemma L 적용"이면 1.3B가 정확한 apply/rewrite 구문 생성(retrieval 결합)
        · 생성된 각 subgoal은 1.3B의 best-first BFS로 닫음(기존 강점)
              │
              ▼
   [Search 프레임: bfs_prover_searcher + vfsearch 훅]  planner move를 강제 후보로,
     dense decomposition-score로 랭킹(§4), 막히면 backtrack(best-first 자동)
```

**핵심 차이 vs 우리가 실패한 것들**:
- gold-injection/distill: 분해를 **1.3B가 학습·생성**해야 함 → covariate-shift/capacity 벽. **여기선 분해를 추론시 외부가 줌 → 벽 자체가 없음.**
- value-free MC: 분해 후보를 **QED-롤아웃(sparse=0)**으로 채점 → 붕괴. **여기선 planner가 후보를 좁혀주고(적은 수), dense score로 채점(§4).**

---

## 1.5 알고리즘 (핵심 — 의사코드)

**구성 요소**
- **Planner** = 강한 LLM(Qwen-7B). 현재 goal에 "이렇게 분해해봐" **후보 tactic 제안**.
- **Executor** = 우리 1.3B. 일반 노드 다음 tactic 생성 + planner 후보 실행.
- **Verifier** = coq-lsp. 모든 tactic을 **VALID / INVALID / QED**로 판정 — **유일한 정답 기준**.
- **Frontier** = best-first 우선순위 큐. 유망 state 먼저 꺼냄(막히면 다음 best = 자동 backtrack).

```
INPUT: 정리 T, 예산 600초
frontier ← { 시작상태 s0 (우선순위 0) }

while frontier 비어있지 않고 시간 남음:
    s ← frontier에서 우선순위 최고 pop            # 막히면 다음 best로 = 자동 backtrack

    # 1) 후보 tactic 모으기
    if depth(s) ≤ 6:                              # 초반 = 분해 결정 지점(병목)
        planner_cands ← Planner.plan(goal(s))     # 강한 LLM에 분해 후보 요청(HTTP)
    else:                                         #   예: [induction l, destruct H, apply foo]
        planner_cands ← []
    policy_cands ← Executor.next_tactics(s, k=4)  # 1.3B 자기 후보
    candidates ← planner_cands + policy_cands

    # 2) 각 후보를 verifier로 시도
    for a in candidates:
        s' ← coq_lsp.apply(a, s)                  # ★ 판정
        if s' == QED:     return 성공             # ← 유일한 "정답"
        if s' == INVALID: continue                # ← 환각/안맞는 tactic 버림
        # s' == VALID (진행됨)
        if a ∈ planner_cands:
            score ← BIG_BONUS − 0.1·(남은 goal 수) # dense 채점(MC 아님): 분해 우선 + goal 감소
        else:
            score ← cum_logprob(s') / depth^0.5   # 1.3B logprob(기존 BFS-Prover)
        frontier.push(s', score)

return 실패(시간초과)
```

**핵심 3줄**
1. 탐색 트리를 넓히며, **초반 노드에서 planner가 분해 후보를 강제 주입**(1.3B이 못 내는 induction/destruct 공급 → coverage 22% 우회).
2. **모든 후보는 coq-lsp가 검증** — VALID만 트리에 남고 환각은 버려짐.
3. **QED = 성공(정답)**. planner "맞음"의 기준 = 그 후보가 **verifier 통과해 QED로 이어짐**. gold 비교 없음 → covariate shift 없음, 틀린 증명 불가능.

**구체 예시 (한 스텝)**
```
goal:  n: nat, l: list nat  ⊢  length (rev l) = length l
Planner.plan → ["induction l.", "simpl.", "rewrite app_length.", ...]   # 6개
Executor     → ["unfold length.", "auto.", ...]                         # 4개
coq_lsp 시도:
   "induction l."        → VALID   → push (BONUS 우선)   ★핵심 분해
   "rewrite app_length." → VALID   → push
   "auto."               → INVALID → 버림
   "simplify."(환각)      → INVALID → 버림
다음 루프: "induction l." 상태 먼저 꺼내 계속 → … → QED
```

**왜 병목을 깨나**: 1.3B은 `induction l`을 22%만 생성 → 혼자선 못 뚫음. planner가 후보에 넣어주니 1.3B은 **그 다음(subgoal별 tactic)만** 하면 됨(강점). 틀린 제안은 verifier가 걸러 해 없음.

**B(학습 planner)와의 관계**: 위 탐색을 **GRPO 롤아웃 중**에 돌려, planner 덕에 QED 낸 궤적을 **positive 학습데이터**로 씀(dead group 살림). 같은 부품, 쓰는 시점만 다름(추론 vs 학습).

---

## 1.6 실제 코드 대조 (`bfs_prover_searcher.py` `search()`)

의사코드의 각 줄이 실제 코드 어디인지 (2026-07-30 기준 라인). 파일: `src/model_deployment/bfs_prover_searcher.py`.

| 의사코드 | 실제 코드 | 라인 |
|---|---|---|
| `frontier ← {s0}` | `heapq.heappush(frontier, _QNode(-0.0, seq, self.init_check, 0.0, 0, 0))` | 239 |
| `while 큐 & 시간` | `while frontier and time.time() - start < self.timeout:` | 242 |
| `s ← pop best` (backtrack) | `node = heapq.heappop(frontier)` | 243 |
| `policy_cands ← Executor.next(s)` | `recs = client.get_recs(...)` → `cand = list(zip(recs.next_tactic_list, recs.score_list))` | 256, 266 |
| `if depth(s) ≤ 6` (게이팅) | `if self.use_planner: is_dp = (node.depth <= self.plan_max_depth) and (self.n_decomp_nodes < self.plan_budget)` | 269–270 |
| `planner_cands ← Planner.plan(goal(s))` | `struct = self.planner.plan("\n".join(self._goals_list(node.check_result)))` | 279 |
| `candidates ← planner + policy` | `cand = [(t, None) for t in struct] + cand` | 285 |
| `s' ← coq_lsp.apply(a, s)` | `res = self.proof_manager.check_proof(script + tactic, new_proof.theorem)` | 291 |
| `if QED: return 성공` | `if res.tactic_result == TacticResult.COMPLETE: … return StraightLineSuccess(...)` | 295–302 |
| `if INVALID: continue` (버림) | (VALID만 아래서 push, INVALID는 그냥 다음 for로 = 자동 버림) | 303, 323 |
| dense 채점(planner 자식) | `bonus = self.plan_bonus + (10.0 if tactic in planner_set else 0.0); score = bonus - 0.1*ng` | 308–313 |
| logprob 채점(policy 자식) | `score = self._score(cum, depth)`  (=`cum_logprob / depth^α`) | 318 |
| `frontier.push(s', score)` | `heapq.heappush(frontier, _QNode(-score, seq, res, cum, depth, child_id))` | 322 |
| `return 실패` | `return StraightLineFailure(...)` | 325 |

### 의사코드엔 없는 실제 디테일 (주의)
1. **`plan_budget` 상한** (270행): 의사코드는 "depth≤6"만인데, 실제는 **정리당 planner 호출 ≤ 20**(`self.n_decomp_nodes < self.plan_budget`)도 걸어 compute를 bound. planner HTTP가 비싸서.
2. **`BIG_BONUS` = `plan_bonus`(기본 500)** (312행). planner 후보를 `-(500+…)`로 push → heap 최상단 → **먼저 확장**. `+10`은 planner가 실제로 준 후보(`planner_set`)를 열거 fallback보다 살짝 우선.
3. **best-first heap = 자동 backtrack** (243행): 막힌 노드(자식 다 INVALID)는 자식이 안 생겨 다시 안 뽑히고, 큐의 다음 best로 되돌아감. 명시적 backtrack 코드 없음.
4. **`_QNode(-score, seq, …)`**: heapq는 min-heap → `-score`로 최대 우선. 동점이면 `seq`(생성순)로 tie-break → planner 후보가 먼저 들어가 먼저 확장.
5. **분해 후보엔 logprob 없음** (`tac_logprob=None`, 285행) → `cum`에 0으로 더해짐(중립, 305행). 그 자식의 **또 다음** 자식(일반 노드)부터 logprob 누적.
6. **`is_struct_child = is_dp and tac_logprob is None`** (307행): "이 자식이 planner 후보에서 나왔나" 판정 → dense 채점 여부 결정.

### Planner 호출 경로 (`self.planner.plan()` → 서버)
`planner_client.py`:
```
PlannerClient.plan(goal) 
  ├─ 캐시 hit? → 반환 (같은 goal 재질의 방지)
  ├─ server_url 있음 → _plan_http(goal)  → planner_server(HTTP POST /plan)  ← A 실전(공유 서버)
  └─ server_url 없음 → _plan_local(goal) → in-process 생성                  ← 단독 테스트
       generate → _parse_moves(JSON/줄 파싱) → 각 tactic 앞 '\n' 부착(검색 규약)
```
`planner_server.py`: Qwen-7B 한 번 로드 → `/plan`에서 `pc.plan(goal)` (lock으로 w2 직렬화) → `{"plan": [...]}`.

### 채점이 의사코드 "dense"인 이유 (MC 아님)
312–313행 `score = plan_bonus - 0.1*ng` 는 **QED 롤아웃(MC)을 안 씀** — `ng`=적용 후 남은 goal 수. goal이 줄면(=분해가 진전) 점수↑. value-free MC(§[[VALUE_FREE_SEARCH]])가 1.3B 롤아웃 sparse로 17% 붕괴한 걸 피하려고, **verifier가 즉시 주는 goal 수**만 씀.

---

## 2. Planner 모델 (로컬)

**planner는 Coq 전용 prover일 필요 없음** — 강한 범용 코드/추론 모델이 few-shot으로 "고수준 분해 전략"만 내면 됨(정확한 Coq 구문은 executor가 책임).

| 후보 | 로컬 | 역할 적합성 | 조달 |
|---|---|---|---|
| **Qwen2.5-Coder-32B-Instruct** ★ | ✓ 4bit(~18GB) 한 장 / fp16 TP | 오픈 코드 SOTA, Apache2.0. **실제 run용 1순위** | **다운로드 필요**(~65GB fp16 / ~18GB AWQ) |
| Qwen3-30B-A3B (MoE) | ✓ | active 3B라 빠름, 추론 강함 | 다운로드 필요 |
| **DeepSeek-Coder-6.7B-instruct** | ✓ **이미 로컬** | 약함(구형)이나 **배관 스모크용 즉시 가능** | 있음 |

### ★ 현재 확정 구현 (2026-07-30)
- **planner = `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ` (AWQ 4bit, ~19GB)**, persistent 서버로 로드.
  - (초기엔 7B로 배관 검증 → 32B로 교체. 7B도 로드 가능하나 plan이 노이즈 많음. 32B는 `induction l; simpl; rewrite IHl` 등 더 깔끔.)
- **★ 로딩 함정 (중요, 재현 방지)**:
  1. **fp16 32B(65GB)는 로드 불가** — transformers 5.1의 bnb 4bit 로더가 **양자화 전 full bf16을 GPU에 올려 48GB OOM**(`GLOBAL_WORKERS`·`max_memory`·`device_map=auto` 다 안 됨). → **AWQ(사전 4bit) 사용.**
  2. **AWQ를 `AutoModelForCausalLM.from_pretrained`로 로드하면 `gptqmodel` 요구**(=transformers 5.14 업그레이드 유발, 파이프라인 위험). → **`autoawq`의 `AutoAWQForCausalLM.from_quantized`로 직접 로드**(transformers 안 건드림). `pip install autoawq`만.
  3. 코드 수정 후 **`__pycache__` 삭제 필수**(`.cpython-311.pyc` 스테일이면 옛 로더 경로 탐).
- **다른 모델 시**: bf16로 48GB에 들어가면(≤~14B) `load_4bit=False`가 가장 간단(bnb 회피). 32B급은 AWQ 필수.

**프롬프트(planner)**: 현재 proof state(goal/hyps) + few-shot(A∨B destruct, S n=S m inversion 등) → 출력 = **JSON tactic 리스트**(`["induction l.", ...]`). 파싱: JSON 우선, 실패 시 줄단위 fallback(`_parse_moves`).

---

## 3. 코드 접합점 (재사용 최대화)

이미 `bfs_prover_searcher.py`에 vfsearch 훅(분해노드 감지 + 강제후보 주입 + 확장부)이 있음(2026-07-29 추가). **`enumerate_structural`(맹목 열거)을 `planner_moves`(planner 제안)로 교체**만 하면 대부분 재사용.

| 파일 | 변경 |
|---|---|
| **`src/model_deployment/planner_client.py`** (신규) | `PlannerClient`: 로컬 LLM(vLLM/transformers) 로드, `plan(goal_str, theorem) -> list[move]`. 캐시(state_key→plan). 4bit 로드. |
| **`bfs_prover_searcher.py`** | `use_planner` 플래그 추가. 분해노드에서 `_enumerate_structural` 대신(또는 앞에) `planner.plan(...)` 결과를 강제 후보로. move→tactic 문자열 변환(`_move_to_tactic`). MC 대신 §4 dense score. |
| `BFSProverSearchConf` | `use_planner`, `planner_model`, `planner_4bit`, `plan_score` 필드. |
| `scripts/run_thm.py` | `rango-planner` alias → BFSProverSearchConf(use_planner=True, planner_model=..., use_vfsearch=False). |
| 서버/리소스 | planner 서버(32B-4bit ~18GB) + executor(1.3B ~3GB) **GPU1 한 장 공존**. 메모리 빡빡하면 eval **w1**로. |

**move→tactic 변환**(`_move_to_tactic`):
- `induction x` / `destruct x` / `inversion H` → 그대로 tactic 문자열.
- `apply L` → executor(1.3B)에게 "이 state에서 L을 쓰는 정확한 tactic"을 get_recs로 생성(retrieval 프롬프트에 L 힌트) → 정확 구문·인자.
- `auto`류 → built-in(우리 automation VALID 57–61% 강점).

---

## 4. 채점 — dense decomposition-score (MC 금지)

value-free 붕괴 교훈: **QED-롤아웃 채점 금지.** planner move 후보를 **dense 구조 신호**로 랭킹(Goedel-Code-Prover식):
- **structural effectiveness**: 적용 후 goal 수 / 각 subgoal의 term-size·hyp 수 **감소량**.
- **immediate dischargeability**: 각 subgoal에 built-in `auto/lia/congruence/eauto` 즉시 닫힘 개수(우리 강점을 dense 신호로).
- **planner confidence**: planner logprob / 순위(있으면).
- QED 롤아웃 **불요** → sparse 회피 + 저비용. (분해노드당 planner 1콜 + 각 후보 coq-lsp 몇 왕복.)

---

## 5. 리소스 / 실행 계획 (★확정)

- **GPU0 절대 금지**(외부 유저). **GPU1 단독.**
- **★ 메모리 함정 해결됨 → persistent 서버**: searcher는 정리별 subprocess라 in-process planner면 정리마다 재로드(치명적). → **`planner_server.py`(HTTP)로 32B AWQ를 한 번만 로드**, run_all이 공유. **워커별 중복 로드 없어 w2 가능**(공유 서버 1개).
- **★ 실측 메모리(w2)**: **GPU1 25.8GB / 48GB** (32B AWQ 서버 19GB + executor w2 ~6-7GB + KV) → **w2 넉넉(22GB 여유), w3-4도 메모리로는 가능.** (w1로 낮출 필요 없음.)
- **★ 진짜 병목 = planner 속도**(메모리 아님): 서버가 generate를 lock으로 직렬화 + 32B plan ~3-6s → 워커 늘려도 planner에 줄 섬. **w2 유지**(executor·coq-lsp 병렬은 이득 + baseline과 공정 w2). 느리면 `plan_budget` 20→8.
- 실행: `PLANNER_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct-AWQ bash all_log/run_planner_srv.sh eval` (서버 자동 시작 + rand200 w2).

## 6. 실행 순서
1. **[GPU 불요, 지금]** Qwen2.5-Coder-32B(-AWQ) 다운로드 + `PlannerClient` 작성 + few-shot 프롬프트.
2. **[배관 스모크]** 6.7B planner로 rand200 앞 5개/120s — planner→executor→coq-lsp 도는지, plan 파싱, 후보 주입 확인.
3. **[divdpo 후 ~14:30, GPU1]** 32B planner로 스모크(10개) → compute·메모리 튜닝(w, plan 캐시, 후보 cap).
4. **rand200 w2(가능하면) 600s** → 37.5% 대비. ablation: (a) executor만(현 BFS 32.5%) / (b) +planner move / (c) +dense score.
5. 적용 후 §coverage 22%·divergence 61%·stuck 74% 재측정 → 진단↔개선 인과.

## 7. 논문 프레이밍
"진단: 작은 prover의 천장은 **분해 generation**(coverage 22%). 학습형 개입 7종 실패(distill도 capacity 벽). → **분해를 추론시 강한 planner로 분리(big-plans/small-executes)** 해 돌파." **Coq/CompCert planner-executor는 문헌 공백** + 진단-driven. positive-number 후보.

## 8. 위험 (정직)
1. **planner가 Coq 분해를 잘 낼까**: 범용 32B가 CompCert 특유 분해(어느 변수/lemma)를 few-shot으로 얼마나? → 스모크서 plan 품질 육안 검증 필수. 안 되면 few-shot↑ 또는 planner도 소량 SFT.
2. **32B+1.3B 한 장 공존 메모리**: 4bit로 완화, 안 되면 w1 / planner를 분해노드에만 호출(콜 수 최소).
3. **novelty 방어**: BFS-Prover-V2/Goedel가 유사(Lean) → 우리는 **Coq + 진단-driven + 1.3B executor**로 차별.
4. move→apply 구문 정확도: executor가 lemma 인자 못 맞추면 → retrieval 힌트 결합(우리 retrieval recall 88.5% 강점).
