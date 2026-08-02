# architecture_bigscale.md — 300 train / 1191 test (bs2·bigscale 라인)

작성 2026-07-31. **300 train 정리로 학습 → 1191 CompCert test 전체 평가**한 실험만 모음.
(rand200만·40 smoke만 한 것은 §3에 별도. 이 문서 핵심 = **full-test 1191** 라인.)

DeepSeek-Coder-1.3B + LoRA + BM25/TF-IDF retrieval, CompCert(coq-lsp) next-tactic.

---

## 0. 공통 스펙 (이 라인 전체가 공유)

### 0.1 데이터 / split
- **train set**: `data/compcert_bs2_train_idx.txt` — **300 CompCert 정리** (idx 2102~2615). GRPO 롤아웃·학습 대상.
- **test set (main)**: `data/compcert_bs2_test_idx.txt` — **1191 CompCert test 전체**, @120s, **w2**.
- **부분평가 (참고)**: rand200 = 무작위 200개, @600s. full-1191과 다른 파일·다른 시간예산.
- train ∩ test = ∅ (분리). 단 Base SFT는 CompCert train 전체를 봄 → same-project 전이 confound 있음(명시).

### 0.2 학습 파이프라인 (무엇을 학습 → 무엇을 더 학습, 순서)
```
  ① 사전학습 base LLM (deepseek-coder-1.3b-instruct)   ← 외부(그대로 사용, 우리가 학습 안 함)
        │  supervised SFT (retrieval 증강, gold tactic)
        ▼
  ② Base SFT (rango / rango-grpo-bs2-sft)              ← executor의 출발점
        │  GRPO (self-rollout, verifier 보상)  [SFT→GRPO 라인]
        ▼
  ③ SFT→GRPO (rango-grpo-bs2-sftgrpo = π₀)             ← 최고 성능
```
- **그냥 GRPO 라인**은 ②를 건너뛰고 base LLM 위에 바로 ③ GRPO (`rango-grpo-bigscale2`). → 비교로 "SFT warmup이 필요한가"를 봄.
- 각 화살표 = 한 번의 학습 단계. 뒤 단계는 앞 단계의 **LoRA adapter를 init으로 얹고** 이어 학습.

### 0.3 학습 종류별 스펙
| 단계 | 종류 | 알고리즘 | 데이터 |
|---|---|---|---|
| ② Base SFT | **supervised** | causal-LM MLE (프롬프트 마스킹) | CompCert train (state+retrieval→gold tactic) |
| ③ GRPO | **on-policy RL** | GRPO (critic-free) | 300 train 자기-롤아웃(G=8) + verifier(coq-lsp) 0/1 보상 |

### 0.4 하이퍼파라미터
| 항목 | Base SFT | GRPO |
|---|---|---|
| learning rate | 1e-3 | 1e-6 |
| **epoch** | 2 | 2 |
| batch (micro) | 4 | 2 |
| max_len | 4096 | 3072 |
| LoRA r / α / dropout | 64 / 16 / 0.1 | (SFT adapter 위) |
| LoRA target | q,k,v,o,gate,up,down_proj | 동 |
| clip_eps (ε) | — | 0.2 |
| kl_beta (β) | — | 0.04 |
| max_steps | 60000 | (데이터×2ep) |
| 롤아웃 | — | G=8, max_steps 20, retries 1, 단일궤도(backtrack X) |

**epoch의 의미**:
- **SFT epoch**: 학습 데이터(전체 (state→tactic) 예시) **전체를 몇 번 반복**해서 gradient step을 밟나. epoch 2 = 데이터를 2회 순회.
- **GRPO epoch**: **수집된 롤아웃 그룹 데이터**를 몇 번 재사용해 policy update하나(각 epoch 내 미니배치 순회). epoch 2 = 같은 롤아웃 배치로 2회 최적화. (on-policy라 많이 돌리면 π_old와 벌어져 clip이 자주 걸림 → 2로 제한.)
- ※ GRPO에서 "롤아웃 재수집(라운드)"과 "epoch(같은 데이터 재사용)"는 다름 — 여기 epoch는 후자.

#### 0.4.1 코드 스니펫으로 하이퍼 이해 (pseudo-code)

**SFT (supervised, causal-LM MLE)**
```python
model = load_base("deepseek-coder-1.3b-instruct")
model = apply_lora(model, r=64, alpha=16, dropout=0.1,   # LoRA: 원본 W 동결, ΔW=B@A만 학습
                   target=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"])
opt = AdamW(model.lora_parameters(), lr=1e-3)            # learning rate 1e-3
step = 0
for epoch in range(2):                                    # epoch=2: 데이터 전체를 2회 순회
    for batch in dataloader(dataset, batch_size=4):       # per_device_train_batch_size=4
        logits = model(batch.input_ids[:, :4096])         # hard_seq_len=4096 (초과분 자름)
        loss = cross_entropy(logits, batch.labels)        # labels: 프롬프트는 -100(무시), tactic만 학습
        loss.backward(); opt.step(); opt.zero_grad()
        step += 1
        if step >= 60000: break                           # max_steps=60000 (상한. epoch보다 먼저 걸리면 종료)
save_lora(model, "models/.../adapter")                    # LoRA adapter만 저장
```

**GRPO (on-policy RL)**
```python
policy = load_base + load_lora(sft_adapter)   # init = SFT adapter (SFT→GRPO). 그냥GRPO면 base만.
ref    = snapshot(policy)                      # π_ref: KL 기준 (학습 내내 고정)
opt = AdamW(policy.lora_parameters(), lr=1e-6) # lr=1e-6: SFT의 1/1000 (RL은 조금씩, 분포붕괴 방지)

# (A) 롤아웃: 300 정리마다 G=8 궤도 생성 (학습 전)
groups = []
for thm in train_300:
    attempts = [rollout(policy, thm, max_steps=20, retries=1) for _ in range(8)]  # G=8
    rewards  = [1.0 if qed else 0.0 for a in attempts]   # verifier(coq-lsp) 0/1 보상
    groups.append((thm, attempts, rewards))              # → bigscale2_sft.jsonl 로 저장

# (B) 학습: 저장된 롤아웃으로 update
for epoch in range(2):                          # GRPO epoch=2: 같은 롤아웃 데이터 2번 재사용
    for (thm, attempts, rewards) in groups:
        adv = (rewards - mean(rewards)) / std(rewards)   # 그룹 상대 advantage Â
        # all-solved(다1)·dead(다0) → std=0 → adv=0 → gradient 0 (mixed 그룹만 학습신호)
        for s in range(0, len(attempts), 2):             # micro_bsz=2 (메모리 한계)
            logp_new = policy.logprob(seqs)[:, :3072]     # max_len=3072
            logp_old = seqs.logp_at_rollout               # 롤아웃 시점 logp
            logp_ref = ref.logprob(seqs)
            ratio = exp(logp_new - logp_old)              # importance ratio ρ
            surr  = min(ratio*adv, clip(ratio, 1-0.2, 1+0.2)*adv)   # clip_eps=0.2 (PPO clip)
            kl    = exp(logp_ref-logp_new) - (logp_ref-logp_new) - 1  # k3 unbiased KL
            loss  = -mean(surr - 0.04 * kl)               # kl_beta=0.04 (π_ref에서 안 벗어나게)
            loss.backward(); clip_grad_norm(1.0); opt.step(); opt.zero_grad()
save_lora(policy, "models/rango-grpo-bs2-sftgrpo/adapter")
```
- `lr`: SFT 1e-3(크게) vs RL 1e-6(1000배 작게 — 롤아웃 분포가 policy 의존이라 크게 움직이면 붕괴).
- `LoRA r=64`: 원본 동결, 각 층에 저랭크 ΔW=B(d×64)·A(64×d)만 → 파라미터 ~1%만 업데이트.
- `micro_bsz=2`: 각 시퀀스 최대 3072토큰이라 GPU 메모리상 2개씩.

**clip_eps ε=0.2** — 한 스텝에 확률을 얼마나 바꾸나:
```
ρ = π_new/π_old.  adv>0이어도 ρ를 1.2에서 자름:
  0.8 ──── 1.0 ──── 1.2   (1±ε 밖은 gradient 0 → 한 번에 20%↑ 안 바뀜, off-policy 폭주 방지)
```
**kl_beta β=0.04** — 초기 정책에서 얼마나 멀어지게:
```
β=0    자유탐색(발산위험, DAPO) | β=0.04 약한고정(DeepSeek-Prover 관행, 우리) | β=0.5 거의 안움직임
```

#### 0.4.2 epoch vs max_steps 차이 (헷갈리기 쉬움)
둘은 **다른 단위**의 종료조건이고, **둘 중 먼저 도달하면 종료**.
- **1 step** = 배치 1개(batch_size=4 예시) 처리 = weight 1번 update.
- **1 epoch** = 데이터 전체 1바퀴 = `(데이터 예시 수 ÷ batch_size)` step.
- `epoch=2` = "최대 2바퀴", `max_steps=60000` = "최대 6만 update". 먼저 걸리는 게 stop.

| 데이터 예시 수 | 1 epoch(=N÷4) | 2 epoch | 종료 |
|---|---|---|---|
| 5만 | 12,500 step | 25,000 | **2 epoch**에서 (25k<60k) |
| 20만 | 50,000 step | 100,000 | **max_steps 60k**에서 (1.2 epoch만) |

비유: epoch=교과서 통독 횟수 / step=푼 문제 수(한 번에 4문제) / max_steps=6만문제 풀면 끝. **CompCert train은 커서 max_steps(60000)가 실질 상한** → "60000 step ≈ 1~2 epoch 학습".

#### 0.4.3 SFT 목적함수 (state 프롬프트 → LLM → 다음 tactic, 정확한 식)
맞음 — **(state+retrieval 프롬프트) → 다음 tactic** 을 next-token으로 학습. **completion-only**(프롬프트 토큰은 loss에서 제외).

**입력 x (프롬프트)** = `LmExample`(코드 `src/tactic_gen/lm_example.py`):
```
x = [ 검색 premises(50, TF-IDF) ] + [ 검색 proofs(20, BM25) ] + [ proof_script(지금까지 tactic들) ] + [ proof_state(현재 goal) ]
```
**타겟 y** = `next_steps` = 그 state에서 gold **다음 tactic** (예: `destruct (Loc.eq l l').`).

**손실** (causal-LM, prompt 마스킹 — 코드 `Trainer` + `DataCollatorForCompletionOnlyLM`, `train_decoder.py`):
```
                     |y|
  L_SFT(θ) = − Σ      Σ   log π_θ( y_t | x, y_<t )
                (x,y)  t=1
```
- x(프롬프트) 위치의 토큰은 **label=−100 (무시)**, `response_template` 이후 y(tactic) 토큰에만 gradient. (`data_collator_compat.py`: "Masks all labels before the response_template so loss is computed on completions only")
- 즉 **주어진 state 프롬프트 조건에서 다음 tactic의 토큰 확률을 최대화**(= 조건부 최대우도 MLE). autoregressive: 각 y_t는 x + 앞 토큰 y_<t 에 조건.

의사코드:
```python
prompt = format(premises, proofs, proof_script, proof_state)  # x
target = next_tactic                                          # y (예: "destruct (Loc.eq l l').")
ids    = tokenize(prompt + target)
labels = [-100]*len(tokenize(prompt)) + tokenize(target)      # 프롬프트 마스킹 = completion-only
loss   = cross_entropy(model(ids).logits[:-1], labels[1:])   # 다음-토큰 예측, tactic 토큰에만
```

#### 0.4.4 SFT가 rango와 같나? → **거의 동일 (같은 config 파일 재사용)**
우리 SFT = **rango 원본 decoder 학습 config 그대로** (`models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml`). **rango도 epoch=2**.

| 항목 | rango 원본 = 우리 SFT |
|---|---|
| model / lr / **epoch** | 1.3b-instruct / 1e-3 / **2** |
| max_steps / LoRA r,α / seq | 60000 / 64,16 / 4096 / batch4 |
| 입력 | premises512+proof1024+script512+state1024 → tactic128 (retrieval 증강) |

→ **SFT 단계는 rango 논문 세팅 그대로 재현** (epoch·목적함수 동일). 우리가 새로 한 건 그 위의 **GRPO(RL)**뿐.

#### 0.4.3 epoch가 적지 않나? → **적정 (둘 다 의도적, 늘리면 역효과)**
- **SFT epoch=2**: 실질 상한은 `max_steps=60000`. CompCert train은 수만 step이라 2 epoch 안에 60000 도달 → 사실상 "60000 step 학습". 늘리면 train 정리 **암기(over-fit) → held-out 하락**. rango가 튜닝한 값. (LLM instruction-tuning·formal-prover SFT 관행 1~3.)
- **GRPO epoch=2**: on-policy라 "같은 롤아웃 재사용 횟수". 늘리면 π가 π_old에서 멀어져 **clip 계속 걸림 → 신호 왜곡·붕괴**. PPO/GRPO 관행 1~4(DeepSeek-Prover·DAPO 대개 1~2). **표준 범위.**
- **부족했던 건 epoch가 아니라**: ① 롤아웃 규모(이번 세션 300중 100만), ② 신호(mixed 26%, dead 73%가 gradient 0). → 레버는 epoch↑가 아니라 **mixed↑(subgoal/search)** 또는 **capacity↑(7B)**. 롤아웃 라운드를 늘리는 건 EI(r1~r3)로 별도 실험함.

### 0.5 GRPO 손실 수식 (kl_beta β가 왜 붙나 — 전체 유도)
코드: `src/tactic_gen/grpo.py` `grpo_batch_loss`. 시퀀스 i(정리의 한 롤아웃)마다:

**① 그룹 상대 advantage** (critic 없이 baseline):
```
Âᵢ = (rᵢ − mean_j r_j) / std_j r_j        (같은 정리의 G=8 시도끼리)
```
rᵢ = outcome 보상(Qed=1, else 0). all-solved/dead는 편차 0 → Âᵢ=0 → gradient 0.

**② importance ratio** (π_old = 롤아웃 시점 정책):
```
ρᵢ,ₜ = exp( logπ_new(tokenₜ) − logπ_old(tokenₜ) )
```

**③ PPO-clip surrogate** (한 방향으로 과도update 방지):
```
Lˢᵘʳʳ = min( ρ·Â ,  clip(ρ, 1−ε, 1+ε)·Â )        ε = clip_eps = 0.2
```

**④ KL 정규화** (π_ref = RL 시작 스냅샷에서 안 벗어나게):
```
전체 토큰 목적:  per_tok = Lˢᵘʳʳ − β · KL(π_new ‖ π_ref)     β = kl_beta = 0.04
```
- **KL 추정 = Schulman k3 (unbiased)**: `kl_unbiased`. Δ = logπ_ref − logπ_new 일 때
  ```
  KL̂ = exp(Δ) − Δ − 1     ( ≥0 항상, E[·]=KL, 저분산 )
  ```
  (유도: KL = E_π_new[log(π_new/π_ref)] = E[−Δ]. 단순 −Δ는 분산 큼. exp(Δ)−Δ−1은 −Δ의 2차 보정으로 항상 ≥0이고 무편향.)

**⑤ 최종 loss** (시퀀스별 완성-토큰 평균 → 배치 평균, 부호 반전):
```
L = − mean_i [ Σₜ maskᵢ,ₜ (per_tokᵢ,ₜ) / Σₜ maskᵢ,ₜ ]
```
- **β(kl_beta)의 역할**: β↑ → π_ref(초기 정책)에 강하게 묶임(보수적, 붕괴 방지) / β↓ → 자유 탐색(발산 위험). 0.04 = DeepSeek-Prover 관행값.
- γ=1(할인 없음), baseline은 그룹 std-정규화(RLOO 변형). (DAPO 변형은 KL 제거 + clip 비대칭 — 본 라인은 표준.)

### 0.6 가중치 저장 (fine-tuning = LoRA)
- **전부 LoRA adapter만** 저장(풀모델 X). 파일:
  - `models/<alias>/adapter/adapter_model.safetensors` — LoRA 가중치(ΔW = BA, r=64)
  - `adapter_config.json` — r/α/target/base(=instruct)
  - `training_conf.yaml`·`lm-example-conf.yaml` — eval 로드용 복사
- 추론: base LLM 로드 → `PeftModel.from_pretrained(base, adapter)`. GRPO는 SFT adapter를 init으로 얹고 그 위 업데이트.

### 0.7 평가·로그·데이터 위치
- **평가 탐색**: [`bfs_prover_searcher.py`](../../src/model_deployment/bfs_prover_searcher.py) best-first search, @120s w2.
- **로그**: [`all_log/bigscale.log`](../../all_log/bigscale.log), [`bigscale2.log`](../../all_log/bigscale2.log)
- **롤아웃 데이터**: [`data/grpo_rollouts/`](../../data/grpo_rollouts/) `bigscale2*.jsonl`
- **결과**: [`all_results/`](../../all_results/) `bs2_*_test120_w2`

---

## 1. 결과 요약 (test 1191 @120s w2)
| 별칭 | arch / model | 종류 | mixed | **test 1191** | 결과 dir |
|---|---|---|---|---|---|
| **SFT** (baseline) | `rango` | SFT | — | **27.0%** (322) | [bs2_baseline](../../all_results/bs2_baseline_test120_w2/) |
| gold-SFT (init) | `rango-grpo-bs2-sft` | SFT | — | 27.2% (324) | [bs2_sft](../../all_results/bs2_sft_test120_w2/) |
| **그냥 GRPO** (base→GRPO) | `rango-grpo-bigscale2` | GRPO(SFT없음) | 22% | 27.5% (328) | [bs2_grpo](../../all_results/bs2_grpo_test120_w2/) |
| **SFT→GRPO** (π₀) ★ | `rango-grpo-bs2-sftgrpo` | SFT→GRPO | 26% | **28.4%** (338) | [bs2_sftgrpo](../../all_results/bs2_sftgrpo_test120_w2/) |
| PPO(critic) | `rango-grpo-bs2-ppo` | PPO | — | (36% *done50*) | [bs2_ppo](../../all_results/bs2_ppo_test120_w2/) |
| cascade subgoal | `rango-grpo-cascade-s0` | subgoal-GRPO | — | (29.1% *done175*) | [bs2_cascade](../../all_results/bs2_cascade_g2w4120s/) |

**신뢰값 = done 1191인 4개**(SFT/gold-SFT/그냥GRPO/SFT→GRPO). PPO·cascade는 부분(done 50/175) → 참고만.

> **opener·DPO는 이 full-1191 라인에 완주본이 없음** (§3 참조). opener 최대 완주 = rand200 부분(done 108), DPO = rand200(done 146). 즉 300/1191 스케일로는 **아직 안 돌림**.

---

## 2. 상세 (성능 라인별)

## 2-1. Full 1191 test (신뢰 라인)

### SFT (baseline, `rango`) — 27.0%
- 학습: supervised MLE(§0.3), CompCert train 전체. GRPO 없음.

### gold-SFT (`rango-grpo-bs2-sft`) — 27.2%
- 300 train gold로 SFT. executor **init**으로 사용. baseline과 사실상 동일.

### 그냥 GRPO (`rango-grpo-bigscale2`) — 27.5%
- **base LLM 위에 바로 GRPO**(②Base SFT 건너뜀). 300 train 자기-롤아웃.
- 롤아웃 `bigscale2.jsonl`: 300그룹, **mixed 66(22%)**, all 1, dead 233(78%).
- SFT 대비 **+0.5%p뿐** → **SFT warmup 없이 GRPO만은 효과 미미**.

### SFT→GRPO (π₀, `rango-grpo-bs2-sftgrpo`) — 28.4% ★
- ②gold-SFT init 위에 GRPO. 롤아웃 `bigscale2_sft.jsonl`: 293그룹, **mixed 76(26%)**, all 2, dead 215(73%).
- SFT 대비 **+1.2%p** (그냥GRPO의 2배 이상). → **SFT→GRPO만 유의미. SFT warmup 필수.**

### (부분) PPO / cascade
- **PPO** (`rango-grpo-bs2-ppo`): critic(linear/MLP) 학습 PPO. **critic explained_var≈0**(희소보상)로 학습 실패 → GRPO가 critic-free인 이유 실증. test1191 미완(done50).
- **cascade** (`rango-grpo-cascade-s0/s0r2`): leaf-first subgoal-GRPO on-policy 정정판. test1191 부분(done175, 29.1%).

## 2-2. rand200 (@600s, 부분평가 라인)
| 별칭 | arch | rand200 | dir |
|---|---|---|---|
| baseline | `rango` | 33.5% (67/200) | [rand200_baseline](../../all_results/rand200_baseline_test600_w2/) |
| **SFT→GRPO** ★ | `rango-grpo-bs2-sftgrpo` | **37.5%** (75/200) | [rand200_sftgrpo](../../all_results/rand200_sftgrpo_test600_w2/) |
| leaf-subgoal | `rango-grpo-subgoal-bs2-s0` | 37.0% (74/200) | [rand200_leafsubgoal](../../all_results/rand200_leafsubgoal_test600_w2/) |
| cascade s0r2 | `rango-grpo-cascade-s0r2` | 37.5% (75/200) | [rand200_cascade_s0r2](../../all_results/rand200_cascade_s0r2_w2/) |
| safe-EI | `rango-grpo-eisafe-r1` | 35.0% (70/200) | [rand200_eisafe_best](../../all_results/rand200_eisafe_best_w2/) |
| divergence-DPO | `rango-grpo-divdpo` | 33.6% (49/**146**) | [rand200_divdpo](../../all_results/rand200_divdpo_w2/) |
| planner(opener 추론) | `rango-planner` | 16.7% (1/**6**) | [rand200_planner](../../all_results/rand200_planner_w2/) |

- rand200(더 긴 600s)에선 격차 확대: baseline 33.5% → **SFT→GRPO 37.5%**.
- divdpo·planner는 done<200(부분) → 신뢰 낮음.

---

## 3. opener·DPO — 이 스케일에서의 위치
> 요청: "opener·DPO 실험도 있지 않았나" — **있으나 full-1191/300 스케일 완주본이 아님.** 정확한 상태:

### opener (planner-executor) — 여러 변형
- **개념**: opener가 분해 열기 → rango(1.3B)가 닫기. executor는 300 train으로 GRPO.
- **3개 축의 조합**: ① opener **종류**(추론 32B / 생성형 7B / 선택형 7B / sub) × ② **적용 방식**(처음1번 / 매분기 / hedge) × ③ **executor**(gold-SFT / subgoal모델).
- **이 라인 상태**: 전부 **1191 test 없음.** rand200도 부분(opener-every done108). 판정 이미 **parity**(opener는 90% VALID로 잘 열지만 닫기가 벽). 상세 [`grpo/opener/`](grpo/opener/).

#### (i) opener 종류 (모델 자체)
| opener 모델 | 방식 | 대상일치 | 어댑터 |
|---|---|---|---|
| 범용 32B (Qwen-Coder-32B) | 추론 only(few-shot) | 14% | — (학습X) |
| **7B 생성형** | SFT | 68% | `models/opener-7b` |
| **7B 선택형**(열거후보 입력) | SFT | 80% | `models/opener-sel-7b`, `opener-sel-ho` |
| **7B-sub**(정리+subgoal opening) | SFT | 52/73% | `models/opener-7b-sub` ← 최종 |

#### (ii) 적용 방식 × executor = 롤아웃 변형 (실측, train 100, G=8)
| 변형 | opener 적용 | executor | mixed | ≥1성공 | attempt | 롤아웃 데이터 |
|---|---|---|---|---|---|---|
| **plain**(대조, opener X) | — | gold-SFT | 27% | 34% | 18.9% | (bigscale2_sft / subgoal-s0) |
| **opener-every** | 매 분기(PLANNER_EVERY) | gold-SFT | **10%** | 19% | 12.6% | `opener_sub_pipe.jsonl` |
| **opener-once** | 처음 1번+hedge | gold-SFT | **30%** | 33% | 17.4% | `opener_once_pipe.jsonl` |
| **combo** | 처음 1번+hedge | **subgoal모델** | 27% | 32% | 17.0% | `combo_subgoal_opener.jsonl` |
| (초기) opener-train rollout | 학습rollout | gold-SFT | 32% | — | 16.0% | `opener_train.jsonl` |
| (초기) 선택형 rollout | 선택형 | gold-SFT | 26% | — | 15.5% | `opener_sel100.jsonl` |
| pf40 exp / plain(초기 파일럿) | opener / 대조 | — | 18% / 38% | — | 15.5 / 23.0% | `pf40_exp/plain.jsonl` |

- **opener-every 10%**: 매 분기 opener가 **과분해**(mid/deep도 강제 destruct 90%) → 모델이 auto로 닫을 걸 막아 mixed 붕괴(27→10%). GRPO 완료 모델=`rango-opener-sub-grpo`, rand200 29.6%(부분, baseline 미달).
- **opener-once 30%**: 처음만 열고 닫기는 모델에 맡김 → mixed 회복. 단 plain(27%)과 **parity**(매칭 비교 opener 27% vs plain 25%). GRPO 미완.
- **combo 27%**: opener-once + **subgoal 학습 executor**(닫기 개선) = "두 벽 동시". 그래도 parity. GRPO/test 미완.
- 결론: 어떤 opener 변형도 plain 초과 X. 닫기(capacity)가 벽.

#### opener 두 세대: 32B(추론) vs 7B(학습)
| opener | 방식 | gold 분해 **대상 일치** | 강제 opening 시 |
|---|---|---|---|
| **범용 32B** (Qwen2.5-Coder-32B, 학습 X, few-shot 추론) | inference-only | **14%** | **dead 59→78% 악화** (regress 8 / revive 1) |
| **7B 생성형** (fine-tune) | SFT | **68%** (train셋) | — |
| **7B 선택형** (열거후보 입력+SFT) | SFT | **80%** (train셋) | — |
| **7B-sub** (정리+subgoal opening) | SFT | 52%(인자까지)/73%(종류) | opener-once 채택 |

- **32B는 성능 나빴다**: 강한 범용 32B조차 CompCert gold 분해 대상을 **14%만 맞힘**(86% 못 맞힘). 강제로 opening 넣으면 valid하나 gold와 다른 대상 → **rango가 원래 풀던 것까지 죽여 dead 59→78% 악화**(regress 8, revive 1 = net-harm). → "선택이 벽(coverage 아님)"의 증거. (32B는 GPU 단독 학습 불가라 추론만.)
- 그래서 **7B를 CompCert opening에 fine-tune** → target 일치 14%→68%(생성)/80%(선택)로 올림. 하지만 §opener 판정대로 닫기 벽 때문에 최종 성능은 parity.

#### opener SFT 학습 스펙 (`scripts/train_opener_sft.py`)
| 항목 | 값 |
|---|---|
| 종류 | **supervised SFT** (goal → opening tactic, JSON), completion-only(프롬프트 마스킹) |
| base 모델 | **Qwen2.5-Coder-7B-Instruct** (bf16, LoRA) |
| LoRA r / α / dropout | **16 / 32 / 0.05**, target=all-linear, bias=none |
| optimizer / lr | AdamW / **1e-4**, grad-clip 1.0 |
| **epoch** | **4** |
| max_len | 2048 (opener-sub) / 1024 (초기) |
| 데이터 | 생성형 147개 / **opener-sub 276개**(정리 147 + subgoal opening ~130). `opener_gen_sub.jsonl` |
| 손실 | causal-LM MLE, `L=−Σ log π(opening_t | goal, opening_<t)`, 프롬프트 −100 마스킹 |
| loss 궤적 | 생성형 1.52→0.25 / opener-sub 1.17→0.21 (4ep) |
| 저장 | LoRA adapter `models/opener-7b/`, `models/opener-7b-sub/` |
| NaN fix | 긴 subgoal state가 max_len 초과→label 전부 −100→NaN. max_len 2048 + 전부-마스킹 예시 제외 + NaN배치 가드 |

### DPO 계열
- **divergence-DPO** (`bfs-dpo`→`rango-grpo-divdpo`): 정책이 gold를 non-gold보다 선호하게 selection DPO(dpo_beta 0.1, `grpo.py`에 통합). rand200 33.6%(done146), margin↑(acc 0.54→0.65)지만 **생성확률·solve 불변, unique 0**. **1191 test 없음.**
- 로그 [divdpo](../../all_log/divdpo.log), 결과 [rand200_divdpo](../../all_results/rand200_divdpo_w2/).

→ **둘 다 300/1191 스케일로는 안 돌렸고(부분/rand200만), 판정은 이미 "무효/parity".** 필요시 1191로 완주 가능.

### backward curriculum (역방향 커리큘럼) — gold-injection 계열, 실패
- **개념**: 정리를 s₀(처음)부터 풀게 하지 말고 **gold 증명의 중간 상태**에서 시작 → 남은 tactic만 닫게. sparse reward의 구조적 해법. 출처 Salimans&Chen 2018([1812.03381](https://arxiv.org/abs/1812.03381)), reverse curriculum(Florensa 2017).
- **왜**: GRPO는 그룹 8개 보상이 균일하면 advantage=0 → 버림(dead 73%). **남은 tactic 수(remaining)로 성공확률 조준** → mixed 보장:
  ```
  인간 gold: a₀→a₁→...→a₁₁→QED (12 tactic)
  s₀(처음):    12개 다 맞춰야 → p¹²=8.7% (거의 dead)
  backward:  a₀..a₇ 줌 → 남은 4개만 → p⁴=44% (mixed↑)
     remaining=4 → 성공 44% → 8회 혼합확률 98.9%
     remaining=14(s₀) → 5.8% → 38%
  ```
- **구현** (`scripts/build_backward_curriculum.py`, alias `grpo-rollout-backward`):
  - 정리당 **그룹 2개**: s₀에서 8개 + s_k(중간, remaining=4)에서 8개.
  - ⚠️ 두 그룹 **안 섞음** — 그룹 평균이 V(s) baseline이라 같은 상태끼리만.
  - 재샘플링 k=4 함께. 커리큘럼 `data/curriculum/backward.json` `{정리stmt: {initial_proof, remaining, total, idx}}`.
  - **혼합**: 절반 s₀ / 절반 s_k (`curriculum_frac`) — 끝내기만 잘하는 편향 방지.
- **결과**: **실패(회귀)**. mixed 31%로 신호는 늘었으나 test 하락. rand200 부분(smart_backward done12). 로그 [backward](../../all_log/backward.log).
- **왜 실패**: **covariate shift** — 평가는 s₀에서 시작인데 학습은 gold 중간상태(off-distribution) → 정책이 그 상태에 스스로 못 감. + 우리 dead는 오히려 **초반(깊이≤4에서 65.7%)**에 몰려 backward(끝 보강)와 어긋남. → 이걸 gold 모든 중간상태로 확장한 게 **revcurr**(역시 실패). 상세 [`grpo/GOLD_PROOF_METHODS.md`](grpo/GOLD_PROOF_METHODS.md).

---

## 3b. opener 새 아키텍처 제안 (닫기 벽을 겨냥, 미검증 아이디어)
> 지금까지 opener는 "여는 것"만 도왔고 벽은 닫기(도메인 lemma 적용)였다. 닫기를 겨냥한 대안들:

| # | 아이디어 | 메커니즘 | 닫기 벽 공략? |
|---|---|---|---|
| 1 | **opener가 lemma까지 제안** (opener→"어느 lemma로 닫아라") | 강 모델이 분해뿐 아니라 **닫기용 lemma 후보**(apply X/rewrite Y)를 제안 → executor는 적용만 | ★직접 (닫기 실패 45%=lemma 오적용) |
| 2 | **retrieval-guided opener** | opener가 BM25/premise 검색결과를 보고 **이 정리에 쓸 lemma 랭킹** → executor 프롬프트에 강제 주입 | ★ recall 88.5%인데 못 쓰는 걸 opener가 선별 |
| 3 | **opener = full-proof sketch** (DSP식) | 강 모델이 **전체 증명 골격**(sketch, admit 허용) 제안 → executor가 각 gap(sub-lemma) 채움 | 열기+닫기 동시(하지만 executor가 gap 못 채우면 동일) |
| 4 | **opener as verifier-in-loop** | executor가 닫기 실패(INVALID)할 때만 opener 호출해 **대안 tactic 제안**(hedge) | 매분기 과분해 회피 + 막힐 때만 개입 |
| 5 | **2-model distillation** | opener(강)가 gold 못 푼 정리를 풀어 **성공 궤적을 executor에 distill**(SFT) | on-policy-safe, 닫기 능력 직접 이식 |
| 6 | **opener = search controller** | opener가 best-first search의 **노드 우선순위/확장 tactic** 지도(정책은 그대로) | 탐색축, 단일궤도 한계 우회 |

- **가장 유망**: #1·#2 (닫기 실패의 45%가 lemma 오적용 = opener가 **닫기용 lemma 선택**을 도우면 직접 공략). #5(distillation)는 on-policy-safe라 covariate shift 없음.
- **주의**: #3(sketch)는 열기 opener와 같은 함정 — executor가 gap을 못 닫으면 무효(현 opener와 동형). #1~#2가 "닫기 신호"를 실제로 넣는다는 점에서 다름.
- 전부 **미검증 아이디어** — 검증하려면 "닫기용 lemma를 프롬프트에 넣었을 때 INVALID율이 실제로 주나"를 값싸게 먼저 재야 함(기존 롤아웃 재분석으로 가능).

---

## 4. GRPO mixed 비율 (300 train 롤아웃, G=8)
| 롤아웃 | 그룹 | all-solved | **mixed(신호)** | dead |
|---|---|---|---|---|
| 그냥 GRPO (`bigscale2`) | 300 | 1 (0%) | **66 (22%)** | 233 (78%) |
| SFT→GRPO (`bigscale2_sft`) | 293 | 2 (1%) | **76 (26%)** | 215 (73%) |
- mixed만 gradient(all-solved·dead는 Â=0). SFT init이 mixed 22→26%로 소폭↑(warmup이 탐색 support 확대).
- dead 73~78% = 300 train 대부분 신호0 = sparse-reward 핵심 난제.

## 5. dead group 유형 (같은 executor급 롤아웃 분석)
| 유형 | 비율 |
|---|---|
| lemma 오적용 (닫기) | 30% |
| opening 실패 | 27% |
| 기타 | 24% |
| 과분해 | 15% |
| automation 실패 | 3% |
→ 닫기 관련 ≈48% = 도메인 lemma 적용(1.3B capacity)이 주 실패.

---

## 6. 판정 (full-1191 라인)
- **SFT 27.0% → 그냥GRPO 27.5%(+0.5) → SFT→GRPO 28.4%(+1.2, 최고)**. SFT→GRPO만 유의미 = **SFT warmup 필수**.
- rand200(600s): baseline 33.5% → SFT→GRPO 37.5%.
- opener·DPO는 이 스케일 미완(부분/rand200만), 판정 무효/parity.
- 병목 = 닫기(capacity), dead 73~78%.

관련: [`architecture.md`](architecture.md)(전체 알고리즘·rand200) · [`grpo/EXPERIMENT_SPEC.md`](grpo/EXPERIMENT_SPEC.md) · [`grpo/opener/`](grpo/opener/)
