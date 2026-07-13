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

# 논문별 "full 구현" 여부 & 결합 방법

> ❓ 질문: 논문들을 **full로** 구현했나? → **네, 4개 다 "탐색부 + 학습부"를 구현하고 하나로 결합해 실행했다.**
> 단, 정직한 캐비어트가 있다(모델 대체·학습 스케일). 아래에서 구분해서 보여준다.

## 요약 표 — 무엇이 full이고 무엇이 결합됐나

| 논문 | ① 탐색부 | ② 학습부 | full = ①+② 결합 | 실행 alias | @40 | 정직 캐비어트 |
|---|---|---|---|---|---|---|
| **DeepSeek-Prover-V1.5** | RMaxTS ✅ | **GRPO** ✅(실학습) | ✅ 결합·실행 | `rango-grpo-rmaxts` | 12 | 알고리즘 충실하나 **7B Lean→1.3B Coq 대체**, 학습 소규모(39그룹/2ep) |
| **BFS-Prover** | length-norm BFS ✅ | **DPO+expert-iter** ✅ | ✅ 결합·실행 | `bfs-dpo` | 13 | DPO 쌍 35개로 학습 약함 |
| **QEDCartographer** | value-guided 탐색 ✅ | **value iteration** ✅ | ✅ 결합·실행 | `rango-qed` | 11 | closed-form=bootstrap(OR-트리) |
| **Quarry** | 재귀 SolveGoal ✅ | 난이도 pairwise ✅ | ✅ 결합·실행 | `quarry` | 0 | **환경 미충족**(1.3B 분해불가+CoqHammer 부재) |

> 🟨 **"full의 정의"**: 이 논문들은 전부 **"탐색 알고리즘 + 그 정책을 학습시키는 방법"** 두 축으로 되어 있다.
> 처음엔 **탐색부만**(search-only) 재구현했고(→ ablation), 나중에 **학습부까지** 구현해 **둘을 결합**하면 논문의 full 파이프라인이 된다.
> "full = 학습된 정책을 탐색에 실제로 얹은 것." 아래가 그 결합 방법이다.

## 결합 방법 — "어떤 요소를 어떻게 묶으면 full이 되나"

<details open>
<summary><b>▶ DeepSeek-Prover-V1.5 = RMaxTS 탐색 + GRPO 학습 정책</b></summary>

**두 요소:**
- ① 탐색: `src/model_deployment/rmaxts_searcher.py` (DUCB MCTS + RMax reward + truncate-resume)
- ② 학습: `grpo.py`+`grpo_rollout.py`+`grpo_train.py` → **학습 산출물** `models/rango-grpo/adapter`

**결합(코드로):** `run_thm.py`에서 alias `rango-grpo-rmaxts`가 둘을 묶는다:
```python
# get_tactic_confs: 정책 = GRPO로 학습한 adapter
case "rango-grpo-rmaxts":
    return [DecoderTacticGenConf(Path("models/rango-grpo/adapter"), [formatter])]  # ← ② 학습정책

# get_searcher_conf: 탐색 = RMaxTS
case "rmaxts" | "rango-grpo-rmaxts":
    return RMaxTSSearchConf(timeout=timeout, n_rollout_steps=8, ...)                # ← ① 탐색
```
→ **GRPO로 다듬은 정책이 RMaxTS 롤아웃의 tactic을 생성**한다 = 논문의 정식 full 구성.

> 🟨 **논문 전체 파이프라인 vs 우리**: DeepSeek-Prover-V1.5 = ① pretrain → ② **SFT**(형식증명 지도학습) → ③ **GRPO**(RLPAF) + 추론 **RMaxTS**.
> **①② 는 rango가 이미 그 역할**(rango = DeepSeek-Coder-1.3B + LoRA로 Coq 증명 SFT된 모델) → 우리는 **③(GRPO+RMaxTS)만 얹음.** 즉 "SFT를 빠뜨린 게 아니라 rango가 SFT."
> 다만 rango SFT는 **next-tactic** 포맷(논문은 whole-proof), SFT↔RL 사이 **데이터 확장(expert-iter)** 루프는 GRPO엔 미적용.

> 🟥 실행: `rango-grpo-rmaxts` @40 = **12** (GRPO+straight-line 16 > GRPO+BFS 15 > GRPO+RMaxTS 12 → 학습 정책에도 RMaxTS는 해로움).
</details>

<details>
<summary><b>▶ BFS-Prover = length-norm BFS 탐색 + DPO/expert-iteration 학습</b></summary>

**두 요소:**
- ① 탐색: `bfs_prover_searcher.py` (score=Σlogp/L^α). 학습데이터용 **트리 덤프**(성공경로 backprop) 포함.
- ② 학습: 트리 덤프 → `bfs_dpo_data.py`(SFT/DPO쌍 추출) → `dpo_train.py`(선호학습) + `bfs_expert_iter.py`(라운드 반복) → `models/bfs-dpo/adapter`

**결합:** alias `bfs-dpo` = DPO adapter + BFS 탐색:
```python
case "bfs-dpo":  return [DecoderTacticGenConf(Path("models/bfs-dpo/adapter"), [formatter])]  # ② 학습정책
case "bfs-prover" | "bfs-dpo":  return BFSProverSearchConf(alpha=0.5, ...)                    # ① 탐색
```
> 🟥 실행: `bfs-dpo` @40 = **13** (untrained BFS와 동수 — DPO 쌍 35개로 학습이 약해서).
</details>

<details>
<summary><b>▶ QEDCartographer = value iteration 학습 + value-guided 탐색</b></summary>

**두 요소:**
- ② 학습: `qed_value_iter.py`+`train_qed_value.py` (coq2vec value를 γ^dist에 회귀, value iteration) → `models/qed_value/qed.pt`
- ① 탐색: `classical_searcher.py`의 `_value_of`가 **학습된 value로 frontier 정렬**(product-over-subgoals backup).

**결합:** alias `rango-qed` = classical 탐색 + value 체크포인트:
```python
case "rango-qed":
    return ClassicalSearchConf(..., value_weight=1.0,
                               qed_ckpt="models/qed_value/qed.pt")  # ① 탐색이 ② 학습 value를 사용
```
→ 학습된 value가 "어느 상태부터 팔지"를 정한다 = value iteration + value-guided search의 결합.
> 🟥 실행: `rango-qed` @40 = **11** (value guidance 이 세팅에선 효과 없음).
</details>

<details>
<summary><b>▶ Quarry = 재귀 분해+CoqHammer 탐색 + 난이도 pairwise 학습 (6컴포넌트 전부)</b></summary>

**요소(6개 A~F, 하나의 searcher 안에서 결합):**
- A 분해생성(`generate_raw`) · B 검증(assert+재귀) · C 28차원 난이도특징 · D 재귀 SolveGoal · E CoqHammer fast-path · F 오프라인 pairwise 학습(`train_quarry_difficulty.py` → `models/quarry_difficulty/difficulty.json`)

**결합:** alias `quarry` — SolveGoal이 A~F를 한 재귀 안에서 호출(하나의 알고리즘이라 별도 정책+탐색 분리 없음):
```python
case "quarry":
    return QuarrySearchConf(k=8, branch=1, max_depth=5,
                            difficulty_ckpt="models/quarry_difficulty/difficulty.json")  # F 학습난이도
```
> 🟥 실행: `quarry` @40 = **0** — 구현은 full(6컴포넌트 전부)이나 **환경이 전제를 안 충족**:
> ① rango 1.3B는 next-tactic 모델이라 `[LEMMA]/[TARGET]` 분해를 못 함, ② CoqStoq에 CoqHammer 미import.
</details>

## 정직한 결론 — "full 맞나?"

- **알고리즘 관점: 예, 4개 다 full.** 각 논문의 탐색부 + 학습부를 구현하고 **결합해 실제 실행**했다(위 alias들).
- **재현 관점: 아니오, 논문 그대로는 아니다.** ⓐ 모델 대체(특히 DeepSeek-Prover는 7B Lean whole-proof → 우리 1.3B Coq next-tactic),
  ⓑ 학습 스케일이 소규모(GRPO 39그룹/2ep, DPO 35쌍), ⓒ Quarry는 환경 미충족으로 0.
- 즉 **"논문의 알고리즘 구조를 full로 구현·결합했다"**가 정확한 표현이고, **"논문 결과를 재현했다"는 아니다.**

> 🟦 한 줄: **full = 학습부(GRPO/DPO/value-iter/difficulty) 산출물을 탐색부(RMaxTS/BFS/value-guided/SolveGoal)에 얹어 하나의 alias로 실행한 것.** 그 결합 코드가 위 4개 case 블록이다.

---

# 전체 variation 성과 요약 (full 여부 · baseline 대비 +/−)

> 구현한 **모든 변형**을 성과·full여부·baseline 대비(+개선 / −회귀)로 정리.
> baseline = published Rango (@40=12/40, @20=8/20). **−는 baseline보다 나쁨(regression)**. 대부분 최고 성능은 @40에서 측정.

## A. 논문 full 구현 (탐색부 + 학습부 결합)

| 논문 | 구성(결합) | full? | @40 | vs base |
|---|---|---|---|---|
| **DeepSeek-Prover-V1.5** | GRPO 정책 + RMaxTS 탐색 (`rango-grpo-rmaxts`) | ✅ full | 12 | **0** |
| ↳ (참고) GRPO 정책 + straight-line | `rango-grpo` | ✅ 학습부 | **16** | **+4** ⭐ |
| ↳ (참고) GRPO 정책 + BFS α=1.0 | `rango-grpo-bfs` | ✅ 결합 | 15 | +3 |
| **BFS-Prover** | DPO 정책 + BFS 탐색 (`bfs-dpo`) | ✅ full | 13 | +1 |
| **QEDCartographer** | value-iteration + value-guided 탐색 (`rango-qed`) | ✅ full | 11 | **−1** ⚠️ |
| **Quarry** | 분해+CoqHammer 재귀 (`quarry`) | ✅ full | 0 | **−12** ⚠️(환경 미충족) |

## B. 논문 탐색부만 (학습 없음 = NOT full)

| 방법 | full? | @40 | vs base |
|---|---|---|---|
| RMaxTS (`rmaxts`) | ❌ 탐색만 | 11 | **−1** ⚠️ |
| BFS-Prover (`bfs-prover`) | ❌ 탐색만 | 13 | +1 |

## C. 탐색 컴포넌트 ablation (NOT full · 컴포넌트 분석용)

| 세팅 | full? | @40 | vs base |
|---|---|---|---|
| RMaxTS −reward (`rmaxts-noreward`) | ❌ ablation | 14 | +2 |
| RMaxTS −merge (`rmaxts-nomerge`) | ❌ | 13 | +1 |
| RMaxTS −DUCB (`rmaxts-nomcts`) | ❌ | 12 | 0 |
| BFS α=0 (`bfs-a0`) | ❌ | 12 | 0 |
| **BFS α=1.0 (`bfs-a1`)** | ❌ | **16** | **+4** ⭐ |
| QED backup=sum (`rango-qed-sum`) | ❌ | 10 | **−2** ⚠️ |
| QED backup=min (`rango-qed-min`) | ❌ | 11 | −1 ⚠️ |

## D. 내가 만든 창작 variation (논문 아님 · NOT full)

> rango 위에 얹은 inference-time 기법들. 대부분 @20에서 탐색(baseline @20=8).

| 방법 | 아이디어 | @ | 성공 | vs base |
|---|---|---|---|---|
| **portfolio** (`rango-portfolio`) | straight-line ∪ classical-mem union | 40 | **15** | **+3** ⭐ (regress 0) |
| portfolio | 〃 | 20 | 12 | +4 |
| mem-wide (`rango-mem-wide`) | transposition table + branch16 | 20 | 10 | +2 |
| psauto (`rango-psauto`) | portfolio + sauto | 20 | 10 | +2 |
| divsample (`rango-divsample`) | retrieval on/off 토글 앙상블 | 20 | 10 | +2 |
| ensemble (`rango-ensemble`) | retrieval/no-retrieval 모델 교대 | 20 | 10 | +2 |
| sauto (`rango-sauto`) | retrieval premise → `sauto use:` | 20 | 9 | +1 |
| align/alignapply | AlphaGoal 정렬 비교 | 20 | 9 | +1 |
| apply-sl (`rango-apply-sl`) | straight-line + forced apply | 20 | 9 | +1 |
| vguided (`rango-vguided`) | 학습 value head로 frontier 블렌드 | 20 | 9 | +1 |
| mem (`rango-mem`) | best-first + memo | 20 | 8 | 0 |
| apply/best-beam/hprobe | 각종 M4/beam/probe | 20 | 8 | 0 |
| qed-hybrid (`rango-qed-hybrid`) | QED value + 확신스텝 greedy | 20 | 8 | 0 |
| search (`rango-search`) | 조합 탐색 | 20 | 7 | **−1** ⚠️ |
| **hybrid** (`rango-hybrid`) | retrieval 신뢰도 게이팅 | 20 | **2** | **−6** ⚠️⚠️ |
| **hybrid-v** (`rango-hybrid-v`) | hybrid + value | 20 | **2** | **−6** ⚠️⚠️ |

## 핵심 관찰 (성과 관점)

- **+ (개선)**: portfolio(+3, regress 0) · GRPO(+4) · BFS α=1.0(+4) — union·학습·length-norm만 확실히 개선.
- **0 (무효)**: 대부분의 탐색 정교화(RMaxTS full/−DUCB, mem, apply, beam)는 baseline과 동급.
- **− (regression)**: RMaxTS full(−1), QED(−1~−2), 특히 **hybrid(−6)·Quarry(−12)** 는 크게 나쁨.
  - hybrid: retrieval 신뢰도 게이팅이 오히려 탐색을 망침(2/20).
  - Quarry: 환경(1.3B 분해불가+CoqHammer 부재)으로 0.
- 정직: **우리 자체 rango(@20=10, @40 재현 강함) 대비로는 순이득이 대부분 작다.** 확실한 순증은 portfolio·GRPO 정도.

---

# 이론편 · GRPO를 밑바닥부터 (수식 → 코드 대응)

> 이 절은 ML/RL을 **전혀 모른다고 가정**하고, 필요한 개념·기호·수식을 하나씩 쌓아 GRPO까지 간다.
> 마지막에 **각 수식이 코드의 어느 줄인지** 표로 매핑한다. 수학 기호도 처음 나올 때 풀어 설명한다.

## 0. 먼저 알아야 할 5개 개념

<details open>
<summary><b>▶ 0-1. 정책(policy) π — "상태를 보고 행동의 확률을 뱉는 함수"</b></summary>

- **상태(state) s** = 지금 Coq goal(증명해야 할 명제 + 가설들).
- **행동(action) a** = 다음에 칠 tactic 한 줄 (예: `induction 1.`).
- **정책 π(a | s)** = "상태 s에서 행동 a를 낼 **확률**". 우리 모델(rango 1.3B)이 바로 이 π다.
  - 기호 `π(a|s)` 읽는 법: "s가 **주어졌을 때(|)** a의 확률". `|`는 조건(given).
- 정책은 파라미터 θ(theta, 모델 가중치)로 정해진다 → `π_θ`. **학습 = θ를 바꿔 π를 개선하는 것.**

> 🟦 tactic은 사실 여러 **토큰**(단어 조각)의 나열이다. `induction 1.` = [`ind`,`uction`,` 1`,`.`] 같은 식.
> 그래서 tactic 하나의 확률 = 그 토큰들 확률의 **곱**: `π(tactic|s) = ∏_t p(token_t | 앞토큰들, s)`.
</details>

<details>
<summary><b>▶ 0-2. 확률의 곱을 왜 log로 바꾸나 (log-prob)</b></summary>

- 토큰이 30개면 확률 30개를 곱한다 → `0.1 × 0.2 × ...` = 아주 작은 수(0에 가까움) → 컴퓨터에서 **언더플로우**(0으로 뭉개짐).
- 해결: **log(로그)**를 씌운다. 곱이 **합**으로 바뀐다: `log(ab) = log a + log b`.
  - `log(∏ p_t) = Σ log p_t` — 기호 `Σ`(시그마) = "다 더해라", `∏`(파이) = "다 곱해라".
- 그래서 코드는 항상 **log-probability(log-prob)**를 다룬다. `get_recs`의 `score` = `Σ log p(token)` = tactic 하나의 log 확률.
- log 확률은 항상 ≤ 0 (확률이 0~1이니 log는 음수). **0에 가까울수록(덜 음수) 확신이 큼.**
</details>

<details>
<summary><b>▶ 0-3. softmax — "점수를 확률로 바꾸는 마지막 층"</b></summary>

모델은 각 토큰 후보에 **점수(logit)** z를 매긴다. 이걸 확률로 바꾸는 게 softmax:
```
p(token_i) = exp(z_i) / Σ_j exp(z_j)      # 다 양수로 만들고(exp), 합이 1이 되게 나눔
```
- `exp(x)` = e^x, 항상 양수. 큰 점수는 더 크게 벌어진다.
- log를 씌우면 `log softmax`. 코드의 `torch.log_softmax(logits)`가 이것 = 각 토큰의 log 확률.
</details>

<details>
<summary><b>▶ 0-4. 기대값 E, argmax, gradient(경사) — 기호 3개</b></summary>

- **E[X]** (기대값, Expectation) = "평균적으로 X가 얼마". `E[reward]` = "평균 보상". 우리는 이걸 **크게** 하고 싶다.
- **argmax_a f(a)** = "f를 가장 크게 만드는 a". (max는 값, argmax는 그 값을 주는 입력.)
- **∇θ J** (그래디언트, gradient) = "J를 θ로 미분한 것" = **θ를 어느 방향으로 조금 옮기면 J가 커지는지 알려주는 화살표(벡터)**.
  - 기호 `∇`(나블라) = 미분(기울기). **학습 = 이 화살표 방향으로 θ를 조금씩 이동**(gradient ascent).
</details>

<details>
<summary><b>▶ 0-5. SFT vs RL — 무엇으로 배우나</b></summary>

- **SFT(지도학습)**: "정답 증명"을 주고 그대로 따라 쓰게 함. 정답이 필요.
- **RL(강화학습)**: 정답 없이, 모델이 **직접 시도**하고 **결과(성공/실패)**로 배움.
  성공한 행동의 확률을 올리고 실패는 내린다. GRPO는 RL 방법.

> 왜 RL이 필요? 어떤 정리는 정답 증명이 코퍼스에 없거나(idx 55), 있어도 모델이 그 스타일을 못 따라 한다.
> "직접 풀어보고 되는 방향으로 스스로 조정"하는 게 RL의 힘.
</details>

## 1. 목표를 수식으로 — 우리가 최대화하려는 것

우리는 "정책이 증명에 **성공할 확률**"을 높이고 싶다. 성공하면 보상 `R=1`, 실패면 `R=0`.
정책 π_θ가 만드는 증명 시도 τ(tau, trajectory=궤적)의 **평균 보상**을 목적함수 J로 둔다:

```
J(θ)  =  E_{τ ~ π_θ} [ R(τ) ]        # π_θ로 궤적을 뽑았을 때, 보상의 평균(기대값)
```
- 읽기: "θ의 정책으로 증명을 뽑으면(`τ ~ π_θ`), 그 보상 R의 평균."
- **우리가 할 일**: `θ ← θ + η·∇θ J` (η=학습률). 즉 **J를 키우는 방향(∇θ J)으로 θ를 조금씩 이동.**

## 1.5 reward R(τ)는 코드에서 정확히 어떻게 계산되나 (빠짐없이)

> 위 수식의 `R(τ)`가 **우리 코드에서 실제로 어떤 값**인지 — 정의·수식·코드·구현 디테일을 전부.

### (1) 무엇의 보상인가 — "시도(궤적) 단위, 증명 완결 여부"

**reward는 tactic 하나가 아니라 증명 시도 τ 전체에 대해 매겨진다.** τ = 한 번의 증명 시도(여러 tactic의 나열).

```
R(τ) = 1   (그 시도가 Coq으로 COMPLETE = Qed 가능)
     = 0   (그 외: INVALID로 죽거나, max_steps 안에 못 끝냄)
```
- 즉 **binary(0/1)**. "이 시도가 정리를 완전히 증명했나?" 딱 하나만 본다.
- **검증 주체 = Coq**(coqpyt `check_proof`). 모델이 판단하는 게 아니라 **Coq이 통과시켜야** 1.

<details><summary><b>▸ 기호 — 클릭</b></summary>

| 기호 | 뜻 |
|---|---|
| `τ` (tau) | 한 증명 시도(궤적) = 시작 goal → tactic들 → 끝 |
| `R(τ)` | 그 시도의 보상. 여기선 0 또는 1 |
| COMPLETE | Coq 결과: 남은 goal 0개, Qed 가능 |
| INVALID | Coq 결과: tactic이 에러 |
| max_steps | 한 시도의 tactic 최대 수(=20). 넘으면 미완=0 |
</details>

### (2) 실제 코드 — `grpo_rollout.py:30` `rollout_attempt`

```python
reward = 0.0                                    # ① 시작 0
last_valid_goals = _goals_str(check)            # (dense용) 마지막 valid 상태 기록
for _ in range(max_steps):                      # ② 최대 20 tactic
    tactic = get_recs(n=1, beam=False)          #    한 줄 샘플
    steps.append({example.to_json(), tactic})   #    (상태,tactic) 저장
    check = check_proof(prefix + tactic)        # ③ ← Coq 검증
    if check == VALID:                          #    유효 → 마지막 valid 상태 갱신
        last_valid_goals = _goals_str(check)
    if check == COMPLETE:                        # ④ ★ 완결 → 보상 1
        reward = 1.0; break
    if check == INVALID:                         # ⑤ 에러 → 루프 종료(reward 0 유지)
        break
# ⑥ (dense reward) 미완이고 value_fn 있으면 부분보상
if reward == 0.0 and value_fn is not None and steps:
    reward = shaping_coef * value_fn(last_valid_goals)
return {"steps": steps, "reward": reward}
```
- **④** COMPLETE에서만 `reward=1.0`. 그 전엔 계속 0.
- **⑤** INVALID면 그 시도는 실패로 확정(reward 0). max_steps 소진도 동일(0).
- **①~⑤** 이게 **binary reward**의 전부. (dense는 ⑥에서만 추가)

### (3) dense reward 변형 (E2 실험만) — QED value로 부분보상

binary는 "8개 다 실패면 신호 0"(성긴 신호) 문제가 있다. E2에서만 **미완 시도에 부분점수**:
```
R(τ) = 1.0                              (COMPLETE)
     = shaping_coef · V(마지막 valid goal)   (미완, 0 ≤ V ≤ 1)   # shaping_coef=0.3
```
- `V` = QEDCartographer value 모델(§3)이 매긴 "그 상태가 QED에 얼마나 가까운가"(0~1).
- `shaping_coef=0.3`으로 **눌러서**(최대 0.3) 완결(1.0)을 절대 못 넘게 → "완결이 항상 최고"라는 순서 보존.
- 목적: 8개 다 미완이어도 "덜 미완 vs 더 미완"의 **advantage 신호를 만든다.**

<details><summary><b>▸ 기호 — 클릭</b></summary>

| 기호 | 뜻 |
|---|---|
| `V(goals)` | QED value: 상태가 증명 완료에 가까운 정도(0~1). `value_state`(§3) |
| `shaping_coef` | 부분보상 스케일=0.3. 완결(1.0) 초과 방지 |
| `last_valid_goals` | 시도가 죽기 직전 마지막 VALID 상태의 goal들(= V 입력) |
</details>

### (4) reward → advantage 로 흐르는 방식 (credit assignment)

reward는 **시도 단위**인데 학습은 **(state,tactic) 스텝 단위**다. 어떻게 잇나:
1. 한 정리에 G=8 시도 → reward `r = [r_1..r_8]` (예: `[1,0,0,1,0,0,0,0]`).
2. 그룹상대 advantage `Â_i = (r_i − mean)/std` (§3).
3. **시도 i의 advantage `Â_i`를 그 시도의 모든 스텝에 똑같이 부여**(`flatten_group`, `grpo_train.py:94`):
```python
for i, a in enumerate(attempts):
    for st in a["steps"]:
        advs.append(float(adv[i]))   # 시도 i의 모든 tactic이 같은 Â_i
```
> 🟦 **개념 · credit assignment**: "성공한 시도에서 친 모든 tactic은 좋았다고 보고 +, 실패 시도는 −." 어느 tactic이 결정적이었는지는 모르지만, 8번 평균내면 신호가 잡힌다. (이게 tactic별 보상을 안 쓰는 이유 — Coq은 "완결/실패"만 알려주지 tactic별 점수를 안 준다.)

### (5) 구현 디테일 총정리 (빠짐없이)

- reward는 `float`(0.0/1.0, dense는 0~1). `group_advantages`가 float를 받는다.
- **성공 판정 = check_proof의 `COMPLETE`** (내부적으로 남은 goal 0 + Qed 재검증). 우리가 문자열로 판단 안 함.
- INVALID / max_steps 초과 / `get_recs`가 빈 결과 → 전부 reward 0.
- dense의 `value_fn`은 rollout searcher가 `qed_ckpt` 있으면 `QEDValuePredictor`로 만든다(`grpo_rollout.py` `GRPORolloutSearcher.__init__`).
- **8개 다 reward 같으면**(다 0 or 다 1) → `group_advantages`가 0 반환 → 그 그룹은 학습에서 skip(`train` 루프의 `if all(|a|<1e-8): continue`).
- 실제 수집: 39그룹 중 **binary로 신호(혼합) 있는 그룹 11개**. dense(E2)는 이 신호 그룹 수를 늘리려는 시도.

<details><summary><b>▸ 돌아가는 예시 — 클릭</b></summary>

```
정리 idx 779038374015, G=8:
  시도별 reward = [1, 0, 0, 1, 0, 0, 0, 0]     ← binary (4/8 완결은 아니고 예시)
  mean=0.25, std=0.43
  advantage Â = [+1.7, −0.58, −0.58, +1.7, −0.58, −0.58, −0.58, −0.58]
  → 성공 시도(1,4)의 모든 tactic 확률↑, 실패 시도의 모든 tactic 확률↓
dense였다면 실패 시도도: reward = 0.3 × V(마지막상태) 예: 0.3×0.4=0.12
  → [1, 0.12, 0.05, 1, 0.08, ...] → 미완끼리도 우열이 생겨 신호↑
```
</details>

## 2. ∇θ J 를 어떻게 구하나 — Policy Gradient (REINFORCE)

문제: R은 "Coq이 통과/실패"라는 **미분 불가능**한 결과다. θ로 직접 미분 못 한다.
해결(정책경사 정리): 로그 미분 트릭으로 아래가 성립한다.

```
∇θ J  =  E[ R(τ) · ∇θ log π_θ(τ) ]              # (REINFORCE)
```
- **직관**: `∇θ log π_θ(a)` = "a의 확률을 올리는 θ 방향". 거기에 **R을 곱한다**.
  - 성공(R=1) → 그 행동들의 확률을 **올리는** 방향으로 θ 이동.
  - 실패(R=0) → 곱이 0 → 안 건드림.
- 한 줄 요약: **"성공한 시도에서 한 행동들의 확률을 높여라."**

> 🟨 문제: R을 그냥 쓰면 **분산이 크다**(운으로 성공/실패한 것도 그대로 반영) → 학습이 불안정. (§3에서 해결)

## 3. baseline 빼기 → advantage, 그리고 GRPO의 핵심

분산을 줄이려고 **기준선(baseline) b**를 빼도 수학적으로 결과가 안 변한다:
```
∇θ J  =  E[ (R − b) · ∇θ log π_θ ]              # (R−b) = advantage A
```
- **advantage A = R − b** = "평균(b)보다 **얼마나 잘했나**". 평균보다 나으면 +, 못하면 −.
- b를 뭘로? 보통 **value network**(상태 가치 추정 신경망)를 따로 학습해서 씀 → 복잡·비쌈.

**GRPO의 아이디어(핵심):** value network 없이, **같은 정리를 여러 번 풀어 그 그룹의 평균을 baseline으로.**
정리 하나에 G번(=8) 시도 → 보상 `{r_1..r_G}` → 그룹 안에서 표준화:
```
Â_i  =  (r_i − mean(r)) / (std(r) + ε)          # group-relative advantage
```
- `mean(r)` = 그룹 평균(=baseline b), `std(r)` = 표준편차(스케일 정규화), `ε`(엡실론)=아주 작은 수(0 나눗셈 방지).
- 예: `r=[1,0,0,1,0,0,0,0]` → mean 0.25, std 0.43 → 성공 `Â=+1.7`, 실패 `Â=−0.58`.
- **8개 다 실패면 std≈0 → Â=0 → 학습 신호 없음** (성긴 신호 문제).

> 🟩 **여기가 "Group Relative"의 뜻**: advantage를 **그룹 내 상대 순위**로 정한다. value network가 필요 없어 가볍다.

## 4. 안정화 — PPO의 clip 과 KL (importance ratio)

RL은 한 번에 정책을 크게 바꾸면 망가진다(폭주). PPO가 도입한 두 장치:

**(a) importance ratio ρ** — "샘플은 옛 정책 π_old로 뽑았는데, 지금 정책 π_θ로 학습". 이 차이를 보정:
```
ρ_t  =  π_θ(a_t | s_t) / π_old(a_t | s_t)  =  exp( logπ_new − logπ_old )
```
- ρ>1 = 지금 정책이 그 행동을 옛날보다 더 잘 냄. (log 차이의 exp = 비율.)

**(b) clipped surrogate** — ρ가 너무 커지지 않게 **자른다(clip)**:
```
L_clip  =  min( ρ·Â ,  clip(ρ, 1−ε, 1+ε)·Â )    # ε=0.2 → ρ를 0.8~1.2로 제한
```
- `min(...)` = 둘 중 **보수적인(작은)** 쪽 선택 → "너무 많이 올리려 하면 그 지점에서 멈춤".

**(c) KL 페널티** — 정책이 시작점(레퍼런스 π_ref)에서 **너무 멀어지지 않게** 당김:
```
KL ≈ exp(logπ_ref − logπ) − (logπ_ref − logπ) − 1  ≥ 0    # DeepSeek unbiased estimator
```
- 항상 ≥0, 두 분포가 같으면 0. 이걸 손실에 β배(=0.04) 더해서 "원래 실력(retrieval 등)을 잃지 마" 규제.

## 4.5 수식 유도 — 각 수식이 어디서 왔나 (+ surrogate의 의미)

> "왜 이 수식이 이렇게 생겼는가"의 출처. 앞 수식들이 **어떻게 유도되는지** 순서대로.

### (가) "surrogate(대리 목적함수)"란 무엇인가 ★

- 우리가 **진짜 최대화하고 싶은 건** `J = E[R]` (평균 보상). 그런데 R은 **Coq이 주는 0/1**이라 θ로 **미분 불가**. → 직접 못 올린다.
- 그래서 **미분 가능한 대리(proxy) 목적함수**를 만들어 그걸 대신 올린다. 이게 **surrogate**(대리). 이름 그대로 "진짜 J의 대역".
- PPO surrogate `L = min(ρ·Â, clip(ρ,1±ε)·Â)`는 **진짜 개선량의 보수적 하한(lower bound)**이 되도록 설계됨 → **surrogate를 올리면 진짜 정책이 (안전하게) 개선**된다. clip이 "과장된 개선"을 막아 하한을 보장.
- 한 줄: **surrogate = "직접 못 올리는 진짜 목표(E[R]) 대신 올리는, 미분 가능·안전한 대리 목표."**

### (나) policy gradient `∇J = E[R·∇logπ]` — 로그미분 트릭
```
∇θ E[R] = ∇θ ∫ π_θ(τ) R dτ = ∫ ∇π_θ · R dτ
        = ∫ π_θ · (∇π_θ / π_θ) · R dτ            ← π_θ 곱하고 나눔
        = ∫ π_θ · ∇log π_θ · R dτ                 ← 핵심: ∇log π = ∇π/π
        = E[ R · ∇log π_θ ]
```
**핵심 항등식** `∇π = π·∇log π`(로그의 미분). 미분 불가능한 R을 안 건드리고 gradient를 log π로 옮김. (REINFORCE, Williams 1992)

### (다) baseline이 왜 "공짜"인가 (advantage의 근거)
```
E[ b·∇logπ ] = b·∫ π∇logπ dτ = b·∫ ∇π dτ = b·∇(∫π dτ) = b·∇(1) = 0
```
∫π=1이라 그 미분=0 → **b를 빼도 기대값 불변**(분산만↓). 그래서 `A = R − b`가 정당. GRPO는 `b=그룹평균`.

### (라) ρ = π_new/π_old 의 출처 — importance sampling
- 샘플은 **π_old**로 뽑았는데 학습은 **π_θ**로 한다(샘플 재사용 위해). "q로 뽑고 p 평가":
```
E_{x~p}[f] = E_{x~q}[ (p/q)·f ]        # importance sampling
```
`p=π_θ, q=π_old` → 보정계수 `ρ = π_θ/π_old`. 그래서 ②의 `∇logπ` 자리에 `ρ`가 들어가 surrogate `E[ρ·A]`가 됨.

### (마) ρ = exp(logπ_new − logπ_old) — 로그 대수
```
a/b = exp(ln a − ln b)   →   π_θ/π_old = exp(logπ_new − logπ_old)
```
확률 대신 **log 확률(log_softmax)**을 손에 쥐고 있고, 작은 확률 직접 나눔은 언더플로우 → **log 빼고 exp**가 안정. (코드 `torch.exp(logp_new - logp_old)`)

### (바) clip `min(ρA, clip(ρ,1±ε)A)` — 왜 min·clip
- ρ가 1.2를 넘어도(정책이 그 행동을 크게 키우려 해도) `clip`이 잘라 **한 번에 못 바꾸게**.
- `min(비클립, 클립)` = **보수적인 쪽** 선택 → surrogate가 진짜 개선의 **하한**이 되어 "과장된 개선"을 방지. (PPO, Schulman+ 2017)

### (사) KL estimator `exp(Δ)−Δ−1` 은 왜 이 형태인가 (Schulman k3)
`Δ = logπ_ref − logπ`, `r = π_ref/π = exp(Δ)`. 목표: `KL(π‖π_ref) = E_π[log(π/π_ref)]` 를 샘플로 추정.
- **순진한 추정** `−Δ = log(π/π_ref)`: 불편이나 **분산 크고 음수도 나옴**(KL은 ≥0인데) → 나쁨.
- **Schulman 트릭**: 기대값 0인 항 `(r−1)`을 더함 → `KL_est = (r−1) − log r = exp(Δ) − Δ − 1`.
```
① 불편: E_π[r−1] = ∫π·(π_ref/π) − 1 = ∫π_ref − 1 = 0   →  E[KL_est] = KL + 0 = KL ✓
② ≥0 : f(r)=r−1−log r ≥ 0 (∵ log r ≤ r−1, r=1서 등호)   →  매 샘플 음수 안 됨 ✓
③ 저분산: (r−1)이 −log r 과 상관 → control variate 로 분산↓ ✓
```
→ "순진한 `−Δ`에 기대값 0인 `(r−1)`을 더해 **불편 유지 + 항상 ≥0 + 저분산**"으로 만든 것. (Schulman "Approximating KL")

## 5. 최종 목적함수 (전부 합침)

```
J_GRPO(θ) = E[ (1/|o|) Σ_t  min(ρ_t·Â, clip(ρ_t,1±ε)·Â)  −  β·KL_t ]
            └──────────────────┬──────────────────┘     └──┬──┘
                  이득: 성공행동↑ 실패행동↓(안전하게)         원래서 안 멀어지게
```
- `(1/|o|) Σ_t` = 생성한 tactic 토큰들에 대해 평균(|o|=완성 토큰 수).
- **손실 = −J** (최대화를 최소화로 뒤집어 `loss.backward()`).

## 6. 알고리즘 → 코드 대응표

| 알고리즘 단계 (수식) | 코드 위치 | 코드 |
|---|---|---|
| ① 궤적 뽑기 `τ ~ π_θ` (rollout) | `grpo_rollout.py` · `rollout_attempt` | `tactic = get_recs(n=1, beam=False)` |
| ② 보상 `R` (성공=1) | 〃 | `if COMPLETE: reward = 1.0` |
| ③ 그룹상대 advantage `Â=(r−mean)/std` | `grpo.py` · `group_advantages` | `return (r - r.mean())/(r.std()+EPS_STD)` |
| ④ Â를 시도의 모든 스텝에 부여 | `grpo_train.py` · `flatten_group` | `advs.append(float(adv[i]))` |
| ⑤ logπ 계산 (softmax·log·gather) | `grpo_train.py` · `sequence_token_logprobs` | `logp = log_softmax(logits); logp.gather(-1, tgt)` |
| ⑥ 비율 `ρ = exp(logπ_new−logπ_old)` | `grpo.py` · `grpo_batch_loss` | `ratio = torch.exp(logp_new - logp_old)` |
| ⑦ clip `min(ρÂ, clip(ρ)Â)` | 〃 | `surrogate = minimum(ratio*adv, clamp(ratio,1±ε)*adv)` |
| ⑧ KL 페널티 | 〃 | `kl = exp(Δ)-Δ-1;  per_tok = surrogate - β*kl` |
| ⑨ 완성토큰 평균 → 손실 | 〃 | `(per_tok*mask).sum()/denom;  loss = −obj` |
| ⑩ θ 업데이트(LoRA만) | `grpo_train.py` train 루프 | `loss.backward(); opt.step()` |

<details>
<summary><b>▶ ⑥⑦⑧⑨가 한 함수에 다 있는 실제 코드 (grpo.py)</b></summary>

```python
def grpo_batch_loss(logp_new, logp_old, logp_ref, advantages, mask, clip_eps=0.2, kl_beta=0.04):
    ratio = torch.exp(logp_new - logp_old)              # ⑥ ρ = π_new/π_old
    adv = advantages.unsqueeze(1)                       #    Â (시퀀스별)
    unclipped = ratio * adv
    clipped = torch.clamp(ratio, 1-clip_eps, 1+clip_eps) * adv   # ⑦ ρ를 0.8~1.2로 자름
    surrogate = torch.minimum(unclipped, clipped)      # ⑦ 보수적인 쪽
    kl = kl_unbiased(logp_new, logp_ref)               # ⑧ KL = exp(Δ)-Δ-1
    per_tok = surrogate - kl_beta * kl                 # ⑧ 이득 − β·KL
    m = mask.float()
    denom = m.sum(dim=1).clamp(min=1.0)
    seq_obj = (per_tok * m).sum(dim=1) / denom         # ⑨ 완성토큰만 평균
    return -seq_obj.mean(), ...                        # ⑨ loss = −목적
```
수식 `J = E[ min(ρÂ, clip(ρ)Â) − β·KL ]` 와 **한 줄씩** 대응한다.
</details>

> 🟦 **한 문장 요약**: GRPO = "정리마다 8번 풀어보고(①②), 그룹 안에서 잘한 시도는 +·못한 건 −로 점수 매긴 뒤(③④), 그 점수 방향으로 tactic 확률을 **조금씩(clip)·원래 실력 유지하며(KL)** 옮긴다(⑤~⑩)."

## 7. (참고) search 쪽 이론 — best-first & UCB 한 줄씩

- **best-first(BFS-Prover)**: `score = (Σ log p) / L^α`. 분자=지금까지 확신(log-prob 합), `÷L^α`=길이 페널티 완화.
  → heap에서 score 큰 것부터 확장. `α`가 클수록 깊은(긴) 증명을 더 탐색.
- **UCB(RMaxTS)**: `Q = W/N + √(2 ln ΣN / N)`. 앞항=평균 가치(활용), 뒤항=덜 가본 곳 보너스(탐험). γ로 할인.
  → "좋았던 곳 + 안 가본 곳"을 균형 있게. (미학습 1.3B엔 이 정교함이 오히려 무효 → §2 결과.)

---

# 코드 단위 딥다이브 — search & 학습이 정확히 어떻게 도는가

> 실제 소스를 **줄 단위로** 따라간다. 각 `▶` 제목 클릭 시 펼쳐짐(GitHub/VSCode 토글). 코드는 **실제 소스 그대로**.

## PART A · SEARCH — 증명 하나를 어떻게 찾는가 (BFS 예시)

> 🟦 **개념 · 한 줄 요약**: "지금 goal → 모델에게 다음 tactic 후보 요청 → Coq에 넣어봄 → VALID면 계속, COMPLETE면 끝, INVALID면 버림"을 **우선순위 큐**로 반복.

<details>
<summary><b>▶ A-1. 준비: root 노드를 큐에 넣는다</b></summary>

```python
def search(self, **kwargs) -> StraightLineSuccess | StraightLineFailure:
    start = time.time()
    frontier: list[_QNode] = []           # ① 우선순위 큐(heap). 제일 유망한 노드부터 꺼냄
    seq = 0
    heapq.heappush(frontier, _QNode(-0.0, seq, self.init_check, 0.0, 0, 0))  # ② root(빈 증명) 삽입
    client = self.tactic_clients[0]       # ③ 정책 모델(retrieval 포함) 핸들
```
- **①** `frontier` = min-heap. `neg_score`가 작을수록 먼저 꺼내짐 → **score 큰(유망한) 노드 우선**.
- **②** `_QNode(neg_score=-0.0, seq, check_result=init_check, cum_logprob=0.0, depth=0, node_id=0)`. `init_check` = 빈 증명 check_proof 결과(= 정리 시작 goal).
- **③** `client.get_recs`가 실제 모델 호출. 입력엔 **BM25 이웃 증명 + TF-IDF premise가 이미 붙어있다**.
</details>

<details>
<summary><b>▶ A-2. 메인 루프: 가장 유망한 노드를 꺼내 tactic 후보를 받는다</b></summary>

```python
    while frontier and time.time() - start < self.timeout:
        node = heapq.heappop(frontier)              # ① 제일 유망한 노드 pop
        if node.depth >= self.max_depth: continue   # ② 너무 깊으면 버림(max_depth=50)
        new_proof = node.check_result.new_proof
        dset = self.proof_manager.build_dset_file(new_proof)   # ③ 현재상태 → retrieval용 DatasetFile
        proof = dset.proofs[-1]
        script = proof.proof_prefix_to_string(proof.steps[-1], include_theorem=False)  # ④ 여기까지 증명 텍스트
        recs = client.get_recs(                     # ⑤ 모델에게 tactic E=2개 요청(temperature 샘플)
            len(proof.steps) - 1, proof, dset, self.expand_width,
            beam=False, file_prefix=self.proof_manager.file_prefix,
        )
```
- **①** pop = 지금까지 score(길이정규화 누적 log-prob) 최고인 부분증명.
- **③** `build_dset_file`: 현재 상태를 모델 입력 포맷으로. **여기서 retrieval이 현재 goal에 맞는 이웃 증명을 붙인다.**
- **④** `script` = root부터 지금까지의 tactic 텍스트(다음 check_proof에 prefix).
- **⑤** `get_recs(n=2, beam=False)` → temperature 샘플로 다른 tactic 2개 + 각 `score`(=Σ token log-prob).
</details>

<details>
<summary><b>▶ A-3. 각 후보를 Coq에 실제로 넣어보고 분기한다</b></summary>

```python
        for tactic, tac_logprob in zip(recs.next_tactic_list, recs.score_list):
            res = self.proof_manager.check_proof(script + tactic, new_proof.theorem)  # ① Coq 검증!
            if res.tactic_result == TacticResult.COMPLETE:          # ② 증명 끝!
                return StraightLineSuccess(..., res.new_proof, [])
            if res.tactic_result == TacticResult.VALID:             # ③ 유효 → 자식으로 큐에 추가
                cum = node.cum_logprob + tac_logprob                #    누적 log-prob 갱신
                depth = node.depth + 1
                score = self._score(cum, depth)                     #    score = cum / depth^α
                heapq.heappush(frontier, _QNode(-score, seq, res, cum, depth, child_id))
            # INVALID → 그 가지 버림
```
- **①** `check_proof(script + tactic)` = 지금까지 증명 + 이 tactic을 **Coq이 실제 실행**해 판정: COMPLETE / VALID / INVALID.
- **③** `_score`:
  ```python
  def _score(self, cum_logprob, depth):
      L = max(1, depth)
      return cum_logprob / (L ** self.alpha)   # α=0.5. 긴 증명 페널티 완화(길이 정규화)
  ```
  이 score로 heap 우선순위 결정.

> 🟦 **개념 · 왜 길이로 나누나**: tactic을 곱해갈수록 log 합이 계속 작아진다. 안 나누면 짧은 증명만 유리 → 깊은 증명을 못 판다. `÷L^α`로 공정하게.
> 🟥 **결과**: α=0 → 12, α=0.5 → 13, **α=1.0 → 16** (@40, baseline 12).
</details>

<details>
<summary><b>▶ A-4. (참고) RMaxTS는 여기에 트리 선택(DUCB)이 추가된다</b></summary>

BFS는 "score 큰 것부터"가 전부지만, RMaxTS는 **어느 노드를 확장할지 DUCB로 선택**:
```python
def ducb(t):                                    # 노드에서 tactic t의 점수
    n = node.N.get(t, 0.0) + 1e-9
    q = node.W.get(t, 0.0) / n                  # 평균 가치(활용)
    return q + math.sqrt(2.0 * math.log(total) / n)   # + 탐험 보너스(덜 가본 것)
best_t = max(node.tactics, key=ducb)
```
롤아웃 후 `reward = 1[새 노드 생김]`을 backprop: `N←γN+1, W←γW+R` (γ=0.99).
> 🟥 결과: DUCB/reward/merge **다 뗄수록** 좋아짐(full 11 → −reward 14). 미학습 1.3B엔 이 정교함이 무효.
</details>

## PART B · 학습 (GRPO) — 정책을 어떻게 강화하는가

> 🟦 **개념 · 3단계**: ① **rollout**(정리마다 8번 시도, 성공/실패 기록) → ② **advantage**(그룹 안 성공+/실패−) → ③ **update**(성공 궤적 tactic 확률↑, 실패↓, 단 조금씩).

### B-1. rollout — 학습 데이터(성공/실패 궤적) 모으기

<details>
<summary><b>▶ 한 번의 증명 시도(attempt) — search와 거의 같지만 "기록"이 목적</b></summary>

```python
def rollout_attempt(tactic_client, proof_manager, theorem, initial_proof, max_steps,
                    temperature_seed=None, value_fn=None, shaping_coef=0.3):
    tactic_client.set_seed(temperature_seed)          # ① 시도마다 다른 seed → 다양한 궤적
    steps = []
    check = proof_manager.check_proof(initial_proof, theorem)
    reward = 0.0
    for _ in range(max_steps):                        # ② 최대 20스텝까지 tactic 이어감
        dset = proof_manager.build_dset_file(check.new_proof)
        proof = dset.proofs[-1]
        example = tactic_client.formatters[0].example_from_step(...)   # ③ 모델이 본 입력(retrieval 포함)
        prefix = proof.proof_prefix_to_string(proof.steps[-1], include_theorem=False)
        recs = tactic_client.get_recs(..., 1, beam=False, ...)         # ④ tactic 1개 샘플
        tactic = recs.next_tactic_list[0]
        steps.append({"example": example.to_json(), "tactic": tactic}) # ⑤ (상태, tactic) 기록!
        check = proof_manager.check_proof(prefix + tactic, ...)
        if check.tactic_result == COMPLETE: reward = 1.0; break         # ⑥ 성공 → 보상 1
        if check.tactic_result == INVALID:  break                      #    사망
    return {"steps": steps, "reward": reward}
```
- **①** `set_seed(g)` — 8번 시도(`g=1..8`)가 서로 다르게 샘플되도록.
- **③⑤** search와 결정적 차이: **매 스텝의 `example`(모델 입력)과 고른 `tactic`을 저장**. 나중에 이 (입력,출력)으로 확률을 재계산해 학습.
- **⑥** 보상 **binary**: 완결=1, 아니면 0. (E2 dense면 미완에 QED value 부분보상)
</details>

<details>
<summary><b>▶ 그룹 = 정리 하나에 8번 → 성공/실패 섞인 8개 (rollouts.jsonl 한 줄)</b></summary>

```python
def collect_group(..., group_size, ...):
    attempts = [rollout_attempt(..., temperature_seed=g+1, ...) for g in range(group_size)]  # G=8
    return {"theorem": theorem_id, "attempts": attempts}
```
```json
{"theorem": 779038374015,
 "attempts": [ {"steps":[{example,tactic}, ...], "reward": 1},   ← 성공
               {"steps":[...], "reward": 0},                     ← 실패
               ... 8개 ... ]}
```
> 🟨 **함정 · 성긴 신호**: 8개가 **다 실패(전부 0)**면 우열 없어 학습 신호 0 → 정리 버려짐. 실제 39그룹 중 **신호 있는 건 11개**뿐. (GRPO 최대 병목)
</details>

### B-2. advantage — 그룹 안에서 상대평가

<details>
<summary><b>▶ 실제 코드 (grpo.py) — 성공은 +, 실패는 −</b></summary>

```python
def group_advantages(rewards):                 # rewards = [1,0,0,1,0,0,0,0]
    r = rewards.float()
    mean = r.mean()                             # 0.25
    std = r.std(unbiased=False)                 # 0.43
    if std < EPS_STD:                           # 전부 같으면(다 0 or 다 1)
        return torch.zeros_like(r)              #   → advantage 0 (학습 안 함)
    return (r - mean) / (std + EPS_STD)         # 성공→+1.7, 실패→−0.58
```
그리고 시도의 advantage를 그 시도의 **모든 (state,tactic) 스텝**에 부여(`flatten_group`):
```python
for i, a in enumerate(attempts):
    for st in a["steps"]:
        prompts.append(collate(st["example"]))   # 모델 입력(prompt)
        comps.append(st["tactic"])               # 그때 고른 tactic(completion)
        advs.append(float(adv[i]))               # 이 시도의 advantage
```
> 🟦 **개념**: "성공 시도의 모든 tactic은 좋았다고 보고 +, 실패 시도는 −." 어느 tactic이 결정적인지는 몰라도 많은 시도를 평균내면 신호가 잡힌다(credit assignment).
</details>

### B-3. 확률 재계산 — logprob

<details>
<summary><b>▶ 모델 통과시켜 "지금 정책이 그 tactic을 낼 확률"을 구한다</b></summary>

```python
def sequence_token_logprobs(model, input_ids, attn):
    out = model(input_ids=input_ids, attention_mask=attn)
    logits = out.logits[:, :-1, :]                  # ① 위치 t의 출력은 토큰 t+1 예측
    logp = torch.log_softmax(logits.float(), dim=-1)
    tgt = input_ids[:, 1:]                           # ② 실제 다음 토큰들
    tok_logp = logp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)   # ③ 그 토큰의 log 확률
    pad = torch.zeros((input_ids.shape[0], 1), ...)
    return torch.cat([pad, tok_logp], dim=1)         # (B,T): 위치 t = logp(token_t)
```
이걸 **세 번** 계산: `logp_new`(현재 정책 π_θ, grad O) · `logp_ref`(시작정책 동결본, grad X) · `logp_old`(온폴리시 1라운드라 = logp_ref).
> 🟨 **함정 · 마스크**: prompt/completion을 따로 토크나이즈해 이어붙여야(`build_completion_batch`) 어느 토큰이 "생성한 tactic"(학습 대상)인지 마스크가 정확.
</details>

### B-4. 손실 & 업데이트 — 확률을 밀고 당긴다

<details>
<summary><b>▶ GRPO 손실 (grpo.py) — 실제 코드</b></summary>

```python
def grpo_batch_loss(logp_new, logp_old, logp_ref, advantages, mask, clip_eps=0.2, kl_beta=0.04):
    ratio = torch.exp(logp_new - logp_old)          # ① ρ = 새확률/옛확률
    adv = advantages.unsqueeze(1)
    unclipped = ratio * adv
    clipped = torch.clamp(ratio, 1-clip_eps, 1+clip_eps) * adv   # ② 0.8~1.2로 자름
    surrogate = torch.minimum(unclipped, clipped)   # ③ 더 보수적인 쪽(폭주 방지)
    kl = torch.exp(Δ) - Δ - 1                        # ④ 시작정책서 멀어진 정도(≥0)
    per_tok = surrogate - kl_beta * kl              # ⑤ 목적 = 이득 − β·KL
    ... loss = −(완성토큰 평균) ...
    return loss, kl
```
- **①** `ratio`>1 = 지금 정책이 그 tactic을 더 잘 냄. advantage(+)면 더 키우려는 방향.
- **②③ clip**: 한 번에 너무 키우면 위험 → 1.2배 이상 잘라 **조금씩만** 올림.
- **④⑤ KL**: 정책이 시작점에서 너무 벗어나면 페널티 → retrieval 등 원래 실력을 안 잃게 붙잡음.
</details>

<details>
<summary><b>▶ 학습 루프 (grpo_train.py) — 그룹마다 gradient step</b></summary>

```python
for group in groups:
    prompts, comps, advs = flatten_group(group, collate_fn)
    if all(abs(a) < 1e-8 for a in advs):
        continue                                   # ① 신호 없는 그룹(다 성공/다 실패) skip
    for s in range(0, len(prompts), micro_bsz):    # ② micro-batch
        ids, attn, cmask = build_completion_batch(tokenizer, bp, bc, max_len, device)
        with torch.no_grad():
            logp_ref = sequence_token_logprobs(ref_model, ids, attn)  # ③ 레퍼런스(동결)
            logp_old = logp_ref
        logp_new = sequence_token_logprobs(model, ids, attn)          # ④ 현재정책(grad O)
        loss, kl = grpo_batch_loss(logp_new, logp_old, logp_ref, ba, cmask, ...)
        opt.zero_grad(); loss.backward()           # ⑤ 역전파
        torch.nn.utils.clip_grad_norm_(..., 1.0)   # ⑥ gradient도 clip(안정)
        opt.step()                                 # ⑦ LoRA 가중치만 업데이트
```
- **⑦** `opt`는 **LoRA 파라미터만** 대상. base 1.3B 동결, 작은 adapter만 움직임 → 값싼 학습.
- 실제: 39그룹 × 2 epoch = **208 step**, lr=1e-6, KL≈0.01. adapter → `models/rango-grpo/adapter`.
</details>

### B-5. 결과 — 실제로 학습이 통했나

> 🟥 **결과 · @40**: GRPO **16/40** (published Rango 12 대비 +4, 우리 rango 대비 +1 = idx 55만 진짜 유일).

<details>
<summary><b>▶ idx 55 agree_exten — rango는 실패, GRPO는 완주 (실제 로그)</b></summary>

**rango(학습 전)** — 오프닝을 매번 바꾸며 2~3스텝 뒤 사망, 수십 번 리셋:
```
induction 1; simpl; intuition; eauto.   → VALID
  intro r.                              → INVALID  ✗
intros. inv H. split. auto. auto. intro r.        (6스텝! 거의 정답길)
  apply H0, (agree_mregs0 (preg_of r)). → INVALID  ✗ 마지막 한 수 실패
... valid-but-stuck, COMPLETE 미도달
```
**GRPO(학습 후)** — 한 궤적으로 완주(95초) → COMPLETE → Qed:
```
induction 1; intros; auto; try tauto.
constructor. elim agree_sp0. auto. auto.
intros. specialize (agree_mregs0 r). rewrite H. auto.
eapply preg_of_data.        ← 마지막 goal 닫힘 → Qed
```
> 🟦 **해석**: GRPO는 새 정리를 "찾은" 게 아니다. **성공 궤적의 마무리 수순(위 4줄)에 확률을 몰아줘서**, rango가 반복해 틀리던 마지막 수(`eapply preg_of_data` 계열)를 **고르게 만든 것**. B-1~B-4가 이 한 줄을 강화한 결과.
</details>

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
