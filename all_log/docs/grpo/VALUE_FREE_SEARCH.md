# Value-free structural search — 완전 설계

작성 2026-07-29. 관련: [[BOTTLENECK_ANALYSIS]](진단 근거·문헌). **#1 최우선 레버 + 논문 positive-number 후보.**
근거 요약: 실패의 root = **초반 분해 오예측**(divergence 61%, ~3 step). 정책이 **정답 분해를 아예 생성 못 함(coverage 22%)** = generation 문제라 학습으로 안 뚫림(모두 37.5% 수렴). → **test-time에 분해를 강제 탐색.**

---

## 0. 한 줄 요약
분해 노드에서 **가능한 분해를 전부 열거**하고, 각 후보의 좋음을 **policy 롤아웃 성공률(=value를 net 없이 몬테카를로로 추정)**로 판단하며, **막히면 되돌아간다(backtrack)**. **critic 학습 없이** capacity 천장을 넘는다.

---

## 1. "value-free"가 정확히 무슨 뜻인가 (핵심)

- **value/critic** = "이 proof state에서 QED까지 갈 확률"을 예측하는 **학습된 스칼라 네트워크**. 우리 PPO critic은 sparse reward로 **학습 실패**(explained_var≈0).
- **value-free**: value를 **학습하지 않고**, 검색 중 **몬테카를로로 직접 추정**한다.
  - state `s`의 점수 `V(s) ≈ (policy로 s에서 짧은 롤아웃 K개 돌렸을 때 QED 도달 비율)`.
  - 이게 정확히 **Math-Shepherd(2312.08935)의 step-label 신호** — 단 그들은 이 라벨로 **PRM net을 학습**하고, 우리는 **검색 중 온라인으로 값 자체를 씀**(net 없음).
- **왜 되나**: Coq(verifier)이 ground-truth("이 롤아웃이 QED 냈나")를 공짜로 준다. 학습 불안정성 0.
- **대가**: 롤아웃 compute(§5에서 관리).

---

## 2. 알고리즘 (best-first + 분해 enumeration + MC scoring + backtrack)

```
frontier = priority queue of (score, proof_state)
push(root, score=0)
while frontier not empty and elapsed < per_thm_budget:
    s = pop_best(frontier)                      # backtrack = 자동(다음 best로 되돌아감)
    if s == QED: return proof

    if is_decomposition_point(s):               # goal에 분해 가능한 hyp/inductive var 존재
        cands = enumerate_structural(s) + policy_topk(s, k)   # 강제 열거 + 정책 후보
    else:
        cands = policy_topk(s, k)               # 일반 노드는 정책 샘플만 (싸게)

    for a in cands:
        s' = coq_apply(a, s)
        if s' == COMPLETE: return proof
        if s' == INVALID:  continue
        # ★ value-free 점수
        if is_decomposition_point(s):  score(s') = mc_value(s')       # 비싼 MC (분해 노드만)
        else:                          score(s') = cum_logprob(s')/L^α # 싼 policy score
        push(s', score(s'))
```

- **is_decomposition_point(s)**: 첫 subgoal 파싱 → (a) inductive 타입 변수 존재, (b) 분해 가능한 가설(∧/∨/∃/inductive-hyp) 존재 → 분해 결정 지점. (구현: 기존 `grpo_rollout._targeted_cands`/`_goals_str` 재사용.)
- **enumerate_structural(s)**: 각 가설 `H_i` → `destruct H_i` (+`inversion H_i`); 각 변수 `x_j`(inductive) → `induction x_j`. 분기수 = #hyp + #var, **보통 3~15**(작음 → tractable).
- **mc_value(s')**: policy로 `s'`에서 **K개 롤아웃, 깊이 D**(기존 `rollout_attempt` 재사용) → `#(QED 도달)/K`. QED가 하나도 없으면 **progress proxy**(goal 수 감소 / closed-subgoal 수)로 fallback.
- **backtrack**: best-first frontier가 **자동 제공** — stuck(모든 후보 INVALID/무진전)이면 그 노드는 점수 낮아 다시 안 뽑히고, frontier의 다른 노드로 되돌아감. (선형 rollout이 못 하던 것.)

---

## 3. 왜 우리 병목에 정확히 맞나 (진단 매핑)

| 진단 사실 | 이 알고리즘이 해결하는 방식 |
|---|---|
| **coverage 22%** — 정답 분해를 정책이 안 생성 | **enumerate_structural이 정답 분해를 후보에 강제 주입**(정책이 안 뽑아도) |
| **오류 49% "종류 맞음·대상 틀림"** (destruct H2 대신 H1) | **모든 대상 열거 + MC로 정답 선택** |
| **stuck 74%** — 유효 tactic 못 냄 | **backtrack** — 막힌 가지 버리고 다른 후보로 |
| 대상 공간 작음(#hyp+#var) | 열거가 **tractable** (lemma top-K보다 분기 적음) |
| retrieval OK·built-in OK | 여기 안 건드림 (병목 아님) |

---

## 4. 하이퍼파라미터 & 예산

| 항목 | 값(시작) | 비고 |
|---|---|---|
| 분기폭(분해 노드) | #hyp+#var + policy top-k (k=3) | 열거 + 정책 |
| 분기폭(일반 노드) | policy top-k (k=2~4) | 싸게 |
| MC 롤아웃 K | 4~8 | 분해 노드에서만 |
| MC 깊이 D | 6~10 step | 짧게(빨리 QED나는지만) |
| length-norm α | 0.5 | 일반 노드 logprob 정렬(BFS-Prover식) |
| per-theorem budget | **600s** | ★평가 공정성(baseline w2 600s와 동일) |

**score 결합**: 분해 노드 자식은 `mc_value`, 일반 노드 자식은 `cum_logprob/L^α`. 두 스케일이 다르니 **분해 노드 자식엔 mc_value 우선순위 bonus**(예 +큰 상수)로 먼저 확장.

---

## 5. Compute 관리 (핵심 리스크)

MC 롤아웃 × 분기 = **compute 폭발** 위험. 완화:
- **MC는 분해 노드에서만**(전체 노드 X). 일반 노드는 logprob score(무료).
- K·D 작게(4/8). QED "빨리 나나"만 보면 됨.
- **MC 캐싱**: 같은 state 재방문 시 재사용.
- **progress 조기 가지치기**: K 롤아웃 중 goal 수가 안 줄면 조기 중단.
- 600s 예산 안에서 **MC로 평가하는 분해 노드 수를 bound**(예: 상위 N개 분해 노드만 MC, 나머진 logprob).

→ 이 튜닝(어디에 MC compute를 쓸지)이 **성패의 핵심**.

---

## 6. 문헌 위치 & novelty

| 논문 | 관계 |
|---|---|
| Proverbot9001 (1907.07794) | value-free Coq best-first search — **우리 baseline search 참조**(value 없이 CompCert 27.5% = 전례) |
| Math-Shepherd (2312.08935) | MC-rollout으로 step value 라벨 → **우리는 net 학습 없이 검색 중 온라인으로 값 사용** (차이) |
| QEDCartographer (2408.09237) | reward-free Coq search — **단 state-value를 학습**(우리는 안 함; value-free 여부 원문 확인 필요) |
| RMaxTS / DS-Prover-V1.5 (2408.08152) | intrinsic-reward MCTS로 다양 증명 — 유사하나 **우리는 structural 분해 enumeration이 핵심** |
| kSubS/AdaSubS (2108.11204/2206.00702) | subgoal 생성+검색 — 우리는 subgoal net 없이 **Coq-native 분해 tactic 열거** |

**우리 novelty**: **"structural 분해 대상 강제 열거 + value-free MC scoring + backtrack"을, 측정된 병목(coverage 22%·divergence 61%)에 맞춰 1.3B Coq에** 특화. = "왜 학습이 실패하나(진단) → test-time 분해 search로 넘는다"는 **진단-driven method 스토리**.

---

## 7. 구현 가이드 (다른 서버에서 바로 구현·실행)

> **좋은 소식: 필요한 부품이 전부 이미 있음.** `enumerate_structural`은 `grpo_rollout._targeted_cands`가 **이미 그거**고, MC 롤아웃은 `rollout_attempt`, goal 파싱은 `_goals_str`, best-first 트리는 `bfs_prover_searcher`가 제공. **새로 짤 건 3개 helper + search 루프 한 곳 수정뿐.**

### 7.1 재사용할 정확한 API (인터페이스)

```python
# src/tactic_gen/grpo_rollout.py
def rollout_attempt(tactic_client, proof_manager, theorem, initial_proof: str,
                    max_steps: int, temperature_seed=None, value_fn=None,
                    shaping_coef=0.3, max_retries=0, subgoal_reward=False) -> dict
    # 반환 {"steps":[{example,tactic,result,state_key}], "reward": float}
    # reward: subgoal_reward=False → COMPLETE=1 else 0 ;  =True → focused subgoal 닫히면(goal수↓) 1
    # ★ MC value용: initial_proof=그 state의 proof-prefix 문자열, max_steps=D(짧게), 여러 seed로 K회.

def _targeted_cands(goals: list) -> list[str]
    # 첫 goal의 가설 파싱 → ['\ndestruct v.', '\ninduction v.', '\ninversion H.', ...]  = enumerate_structural 그 자체
def _goals_str(check) -> list[str]     # check.current_goals → [repr(goal), ...]

# src/model_deployment/proof_manager.py
proof_manager.check_proof(script: str, theorem) -> res
    # res.tactic_result ∈ {VALID, INVALID, COMPLETE} ;  res.new_proof ;  res.current_goals
proof_manager.build_dset_file(new_proof) -> dset ;  proof = dset.proofs[-1]
proof.proof_prefix_to_string(proof.steps[-1], include_theorem=False) -> str  # 그 state까지의 proof 스크립트

# src/model_deployment/bfs_prover_searcher.py  (search() 안)
client.get_recs(step_idx, proof, dset, E, beam=False, file_prefix=...) -> recs
    # recs.next_tactic_list: list[str] ,  recs.score_list: list[float](logprob)
# frontier: heapq of _QNode(neg_score, seq, check_result, cum_logprob, depth, node_id)
```

### 7.2 새 helper 3개 (bfs_prover_searcher.py에 추가)

```python
from tactic_gen.grpo_rollout import rollout_attempt, _targeted_cands, _goals_str
import statistics

def is_decomposition_point(check) -> bool:
    # 현재 goal에 destruct/induction 가능한 hyp/inductive var가 있으면 분해 결정 지점
    return len(_targeted_cands(_goals_str(check))) > 0

def enumerate_structural(check) -> list[str]:
    return _targeted_cands(_goals_str(check))     # 각 hyp destruct / 각 var induction / inversion

def mc_value(self, check, K: int, D: int) -> float:
    """value-free 점수: 이 state에서 policy로 K개 짧은(깊이 D) 롤아웃 → QED 도달률.
    QED가 하나도 없으면 subgoal-close 비율(goal수↓)로 진전 근사."""
    new_proof = check.new_proof
    if new_proof is None:
        return 0.0
    dset = self.proof_manager.build_dset_file(new_proof)
    script = dset.proofs[-1].proof_prefix_to_string(
        dset.proofs[-1].steps[-1], include_theorem=False)
    qed = 0; prog = 0
    for i in range(K):
        r = rollout_attempt(self.tactic_clients[0], self.proof_manager,
                            new_proof.theorem, script, max_steps=D,
                            temperature_seed=i, max_retries=1)          # 전체 QED
        if r["reward"] >= 1.0: qed += 1
        rp = rollout_attempt(self.tactic_clients[0], self.proof_manager,
                            new_proof.theorem, script, max_steps=D,
                            temperature_seed=i, max_retries=1, subgoal_reward=True)  # subgoal 닫힘
        if rp["reward"] >= 1.0: prog += 1
    # QED 우선, 없으면 진전 신호를 작은 가중으로 (전부 0인 랭킹 붕괴 방지)
    return qed / K + 0.1 * (prog / K)
    # 최적화: qed 롤아웃 재사용해 rp를 따로 안 돌리고 steps에서 goal수 감소 판정해도 됨(compute 절반).
```

### 7.3 search() 루프 수정 (한 곳)

`bfs_prover_searcher.search()`의 **노드 확장 부분**만 바꾼다. 현재는 `get_recs`로 E개 뽑아 전부 push. 수정:

```python
# 노드 s 팝 후, 후보 tactic 생성
if self.use_vfsearch and is_decomposition_point(node.check_result):
    struct = enumerate_structural(node.check_result)                  # 강제 분해 후보
    recs = client.get_recs(step_idx, proof, dset, self.expand_width,  # + 정책 top-k
                           beam=False, file_prefix=...)
    cand_tactics = struct + list(recs.next_tactic_list)
    decomp_node = True
else:
    recs = client.get_recs(step_idx, proof, dset, self.expand_width, beam=False, file_prefix=...)
    cand_tactics = list(recs.next_tactic_list)
    decomp_node = False

for tactic in cand_tactics:
    res = self.proof_manager.check_proof(script + tactic, new_proof.theorem)
    if res.tactic_result == TacticResult.COMPLETE:
        return success(...)                       # QED
    if res.tactic_result != TacticResult.VALID:
        continue                                  # INVALID 버림 (stuck→backtrack은 frontier가 자동)
    # ★ value-free 우선순위
    if decomp_node:
        score = mc_value(self, res, self.mc_K, self.mc_D)   # 비싼 MC (분해 노드만)
        priority = -(1000.0 + score)                        # 분해 자식은 큰 bonus로 먼저 확장
    else:
        cum = node.cum_logprob + tac_logprob
        score = cum / max(1, node.depth+1) ** self.alpha    # 싼 logprob (기존)
        priority = -score
    heapq.heappush(frontier, _QNode(priority, seq, res, cum_if_any, node.depth+1, child_id))
```

- **backtrack**: 명시 코드 불필요 — best-first frontier가 stuck 노드(자식 다 INVALID)를 자연히 버리고 다음 best로 되돌아감.
- **INVALID 후보 무시**로 stuck 자동 처리.

### 7.4 config / alias / eval

```python
# BFSProverSearchConf 에 필드 추가
use_vfsearch: bool = False
mc_K: int = 4          # MC 롤아웃 수
mc_D: int = 8          # MC 깊이(step)
# ALIAS = "vfsearch"
```
```python
# scripts/run_thm.py  (get_searcher_conf에)
case "rango-vfsearch":
    return BFSProverSearchConf(timeout=timeout, alpha=0.5, expand_width=4,
                               use_vfsearch=True, mc_K=4, mc_D=8, print_proofs=True)
# 그리고 모델 case(rango-grpo-* 계열)에 rango-vfsearch 정책=models/rango-grpo/adapter 연결
```
```bash
# 평가 (다른 서버: GPU 지정 자유, eval은 공정성 위해 w2)
python3 scripts/run_all.py --alias rango-vfsearch --idx-file data/compcert_bs2_rand200_idx.txt \
    --timeout 600 --gpus 0 --workers 2 --out all_results/rand200_vfsearch_w2
```

### 7.5 튜닝 순서 & 디버깅 (다른 서버)

1. **먼저 소규모 스모크**: `--idx-file` 앞 10개, `--timeout 120`으로 크래시·API 매칭 확인.
2. **compute 감 잡기**: 한 정리에서 분해 노드 수 × mc_K × mc_D × (check_proof 왕복 ~수초) 로그 찍어 600s 예산 안 드는지. 넘치면:
   - `mc_K 4→2`, `mc_D 8→6`, 분해 노드 중 **상위 N개만 MC**(나머진 logprob).
   - `mc_value`에서 rp(subgoal) 롤아웃 빼고 qed 롤아웃 steps에서 goal수 감소로 progress 판정(compute 절반).
3. **MC-sparsity 체크**: 분해 노드들 mc_value가 전부 0이면(1.3B가 D step 안에 QED 못 냄) → `0.1*prog` 항이 랭킹 담당하는지 확인, 안 되면 progress 가중↑ 또는 mc_D↑.
4. **ablation 실행**(논문 figure): use_vfsearch=False(정책 BFS만) / struct만(mc 끔, score=logprob) / +mc / (backtrack은 항상 on) 각각 rand200.

### 7.6 요약 체크리스트
- [ ] `bfs_prover_searcher.py`: `is_decomposition_point`·`enumerate_structural`·`mc_value` 추가 + search 확장부 수정.
- [ ] `BFSProverSearchConf`: `use_vfsearch/mc_K/mc_D` 필드.
- [ ] `run_thm.py`: `rango-vfsearch` alias(searcher conf + 정책 모델).
- [ ] 스모크(10정리/120s) → compute 튜닝 → rand200 w2 600s.
- [ ] ablation 4종 + 적용 후 §divergence/coverage/stuck 재측정.

---

## 8. 평가 & ablation (논문용)

- **기준**: rand200 **w2 600s** vs SFT→GRPO **37.5%**.
- **기대**: search compute를 쓰니 **천장 위 가능**(Proverbot value-free만으로 27.5% 전례; 분해 강제로 coverage 22%↑이면 성공률↑). 단 §9 위험 참조.
- **ablation(핵심 figure)**: (a) 정책 BFS만 → (b) +structural enumeration → (c) +MC scoring → (d) +backtrack. 각 단계 기여 분해 = "무엇이 얼마나 도왔나" 실증.
- **진단 재측정**: 적용 후 §divergence 61%·coverage 22%·stuck 74%가 얼마나 개선되는지 → 진단↔개선 인과 연결(강한 논문 클레임).

---

## 9. 위험 / 한계 (정직)

1. **MC 신호 sparse**: 1.3B가 롤아웃(깊이 D)에서 QED를 잘 못 내면 분해 후보들 성공률이 다 0 → 랭킹 무의미. → **progress proxy(goal 수 감소·closed subgoal)로 보완** 필수.
2. **compute**: 600s 예산 안 MC가 비쌈 → §5 튜닝 안 되면 오히려 정리당 탐색량 줄어 성능↓ 가능.
3. **분해 후 lemma 적용(51% INVALID)은 여전**: search가 그 지점도 탐색으로 우회해야(premise 열거 병행 = divergence-DPO/top-K와 결합).
4. **분기 폭발**: hyp/var 많은 goal에선 enumerate가 큼 → cap(상위 몇 개만) 필요.

→ 한 줄: **"분해를 강제 열거해 coverage를 뚫고, value를 net 없이 MC로 사서 랭킹, 막히면 backtrack"** — 진단에 가장 맞고 critic 불요지만, **compute 튜닝과 MC-sparsity가 성패**.

---

## 10. divergence-DPO와의 관계
- **상보적**: divergence-DPO(학습측)는 정책의 분해 생성확률을 gold쪽으로 미세조정 → **enumerate 없이도 정답을 더 자주 생성**하게. value-free search(추론측)는 **지금 당장** 정답을 강제 탐색.
- **결합**: DPO로 향상된 정책 위에 search를 올리면 시너지(정책이 정답을 더 자주 top-k에 → search 분기·MC 효율↑).
