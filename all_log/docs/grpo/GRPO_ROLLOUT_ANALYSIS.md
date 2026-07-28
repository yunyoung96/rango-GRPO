# GRPO 롤아웃 로그 분석 — sparse reward의 진짜 원인

> 작성 2026-07-14. 데이터: `data/grpo_rollouts/*.jsonl`, `all_results/*_grpo-rollout*/logs/`.
>
> **한 줄 요약**: "정리가 길어서 성공에 도달 못 한다"는 가설은 **틀렸다**. 롤아웃은 3~4스텝 만에
> 잘못된 tactic을 뱉고 **즉사**한다. sparse reward는 horizon 문제가 아니라 **per-step 정밀도 × 무재시도**
> 문제이며, 곱셈으로 정확히 설명된다.

## 목차
- [§1 GRPO가 이 문제에 어떻게 대응되나 (agent/state/action)](#1-grpo가-이-문제에-어떻게-대응되나)
- [§2 돌아가는 예시 (실제 데이터)](#2-돌아가는-예시--dead-group-하나를-통째로)
  - 2-A dead group 하나를 통째로 · 2-B advantage 계산 실물 · 2-C 성공한 증명 · 2-D 실패의 두 종류
- [§3 데이터 가용성 (원본 유실 사고)](#3-데이터-가용성)
- [§4 세 라운드 요약](#4-세-라운드-요약)
- [§5 ★ 실패의 종말 원인](#5--실패의-종말-원인)
- [§6 ★ sparse reward의 수식](#6--sparse-reward의-수식)
- [§7 무엇이 죽이는가](#7-무엇이-죽이는가)
- [§8 다양성](#8-다양성)
- [§9 문제 목록 P1~P9](#9-문제-목록)
- [§10 처방 + 구현](#10-처방--구현)
- [§11 ★★ 베이스 모델 불일치](#11--베이스-모델-불일치)
- [§12 실행 큐 (2×2 factorial)](#12-실행-큐)
- [§13 재현 스크립트](#13-재현-스크립트)
- [§14 ★ 학습/평가 대상 idx + sibling 겹침 검사](#14-학습평가-대상-정리-겹침-검사)
- [§15 ★ 문헌 대조 — G(그룹 크기), advantage collapse, 우리 위치](#15-문헌-대조--g그룹-크기와-dead-group)

---

## 1. GRPO가 이 문제에 어떻게 대응되나

무엇이 agent이고 state이고 action인지부터 못박아야 아래 분석이 읽힌다.

| RL 요소 | 이 시스템에서 | 코드 |
|---|---|---|
| **Agent (정책 π_θ)** | DeepSeek-Coder-1.3B + LoRA. **학습되는 건 LoRA 60M뿐**(전체의 4.5%) | `grpo_train.py:269` |
| **Environment** | **Coq (coq-lsp)**. 결정론적 | `proof_manager.check_proof()` |
| **State s_t** | 현재 goal + 검색된 유사증명 20개 + 전제 50개 + 지금까지의 스크립트 | `grpo_rollout.py:72` `example_from_step()` |
| **Action a_t** | **tactic 문자열** (토큰 2~12개) | `grpo_rollout.py:89` |
| **Transition** | Coq이 tactic 실행 → 새 goal (또는 거부) | `check_proof(prefix + tactic)` |
| **Reward** | **QED면 1, 아니면 0.** 중간 보상 없음 | `grpo_rollout.py:114` |
| **Episode** | 정리 하나에 대한 증명 시도 1회 (≤20 step) | `rollout_attempt()` |
| **Value function** | **없음** — GRPO는 critic-free, 그룹 평균이 baseline | — |

### 정책 π는 LM의 softmax 그 자체

별도의 정책망이 없다. 마지막 은닉상태 `h ∈ R^2048` → `lm_head` → logits ∈ R^32256 → softmax:

```
π_θ(token=k | 문맥) = softmax(W_U · h)[k]
```

tactic `a`는 토큰 시퀀스 `(a_1,…,a_m)`이므로:

```
log π_θ(a | s) = Σ_j log π_θ(a_j | s, a_<j)
```

`model_wrapper.py:198-207`이 정확히 이 합을 계산해 `score_list`로 돌려준다:

```python
transition_scores = self.model.compute_transition_scores(
    generated_seqs, outputs.scores, normalize_logits=True)
scores = transition_scores.sum(axis=1).tolist()   # = log π(tactic | state)
```

### ★ MDP가 두 층위로 겹쳐 있다 — 여기서 credit assignment 문제가 나온다

- **환경(Coq)이 보는 MDP는 tactic 단위.** 한 스텝 = tactic 하나 = **매크로 액션**.
- **손실이 도는 MDP는 토큰 단위.** 한 스텝 = 토큰 하나 = **마이크로 액션**.

gradient는 **토큰마다** 걸리는데(`grpo.py:62-83`, `mask`가 완성 토큰만 켬), **advantage는 시도 하나당 스칼라 하나**다:

```python
# grpo_train.py:118  (flatten_group)
rewards = torch.tensor([a["reward"] for a in attempts])   # (G,)  ∈{0,1}
adv = group_advantages(rewards)                            # (G,)
for i, a in enumerate(attempts):
    for st in a["steps"]:
        advs_out.append(float(adv[i]))    # ← 시도의 스칼라를 모든 step 에 broadcast
```

**즉 한 시도가 실패하면 그 안의 15개 tactic이 전부 똑같이 벌점을 받는다.**
3번째 tactic이 틀렸고 1·2번째는 멀쩡했어도 구분이 안 된다. → **PRM(§10)이 고치는 지점.**

### GRPO 수식 ↔ 코드

```
① Advantage   A_i = (r_i − mean(r)) / std(r)                    grpo.py:21
② ratio       ρ_t = exp( log π_θ(a_t) − log π_old(a_t) )        grpo.py:98
③ surrogate   L_t = min( ρ_t·A , clip(ρ_t, 1±ε)·A )   ε=0.2      grpo.py:99-101
④ KL(Schulman k3)  KL_t ≈ exp(Δ) − Δ − 1,  Δ = logπ_ref − logπ_θ  grpo.py:32
⑤ loss = − mean_seq[ mean_tok( L_t − β·KL_t ) ]        β=0.04    grpo.py:103-108
```

**①에서 모든 게 결정된다**: 그룹 8개가 전부 실패하면 `std(r)=0` → `A=0` → **그 그룹은 통째로 스킵**된다.

```python
# grpo_train.py:152  — 여기서 73%가 버려진다
if outcome_dead and process_dead:
    continue   # 신호 전무 → 스킵
```

---

## 2. 돌아가는 예시 (실제 데이터)

### 2-A. dead group 하나를 통째로

`data/grpo_rollouts/rollouts.jsonl`의 실제 그룹 (theorem `475994196441`, CompCert `Conventions1.v`).

### state s₀

```coq
forall (tyl : list typ) (ir fr ofs : Z) (p : rpair loc),
In p (loc_arguments_elf64 tyl ir fr ofs) ->
(2 | ofs) -> forall_rpair (loc_argument_elf64_charact ofs) p
```
프롬프트에는 여기에 **검색된 유사증명 20개 + 전제 50개**가 함께 들어간다 (총 ~2000 토큰).

### 8개 시도 — 보상이 전부 0 (dead group)

```
보상: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
```

**시도 0** — 3스텝에서 사망:
```coq
a_0: Proof.                                                    → VALID
a_1: induction tyl as [ | ty tyl]; simpl loc_arguments_elf64; intros
                                                               → VALID
a_2: intro H'; inversion H'.                                   → INVALID  ✗ 시도 종료
```

**시도 1** — ★ **tactic 14개를 연속으로 통과하고 15번째에서 사망**:
```coq
a_0:  Proof.                                → VALID
a_1:  induction tyl as [ | t tyl].          → VALID
a_2:  -                                     → VALID
a_3:  simpl; now intros.                    → VALID
a_4:  -                                     → VALID
a_5:  intro; simpl.                         → VALID
a_6:  case t.                               → VALID
a_7:  +                                     → VALID
a_8:  (* int3 *) intros; destruct (zeq ir 0). → VALID
a_9:  *                                     → VALID
a_10: simpl.                                → VALID
a_11: intuition.                            → VALID
a_12: destruct p; simpl; auto.              → VALID
a_13: **                                    → VALID
a_14: destruct H; eauto; simpl; lia.        → INVALID  ✗ 시도 종료
```

**이 한 예시가 문제 전부를 보여준다.**
- 증명이 "너무 길어서" 실패한 게 아니다 — **14스텝을 이미 갔다.**
- 마지막 한 번의 실수로 **14개의 올바른 tactic이 전부 버려진다.**
- 그리고 `reward=0`이므로 GRPO는 이 시도에서 **"전부 나빴다"**고 학습한다. `a_0`~`a_13`은 멀쩡했는데도.
- 8개 시도가 다 이러니 그룹 보상이 균일(전부 0) → `std=0` → **advantage=0** → **그룹 전체가 학습에서 제외.**

**만약 `a_14`에서 다시 뽑았다면?** state는 `a_13` 직후 그대로다(Coq이 거부했으니 변하지 않았다).
그 state에서 다시 샘플링하면 81% 확률로 유효한 tactic이 나온다. → **§10 P1 처방.**

---

### 2-B. 혼합 그룹 — advantage가 실제로 어떻게 계산되나

**신호가 있는** 그룹 (37개 중 4개뿐). `group_advantages()`를 실제 보상에 돌린 결과다.

**theorem `523789788107`** — 8시도 중 **2개 성공**:

```
보상       [ 0,     0,     1,     1,     0,     0,     0,     0   ]
스텝 수    [ 4,     8,    10,    10,     8,     4,     8,     7   ]
advantage  [-0.58, -0.58, +1.73, +1.73, -0.58, -0.58, -0.58, -0.58]
             ↑ mean=0.25, std=0.433 → A_i = (r_i − 0.25) / 0.433
```

**theorem `906615913767`** — 8시도 중 **4개 성공** (가장 균형 잡힌 그룹):

```
보상       [ 1,     1,     1,     0,     1,     0,     0,     0   ]
advantage  [+1.00, +1.00, +1.00, -1.00, +1.00, -1.00, -1.00, -1.00]
             ↑ mean=0.5, std=0.5 → 성공/실패가 정확히 ±1
```

**읽는 법**: 성공한 시도 안의 **모든 tactic**이 `+1.73`(또는 `+1.00`)을 받고, 실패한 시도 안의
**모든 tactic**이 `-0.58`(또는 `-1.00`)을 받는다. **tactic 개별 품질은 전혀 반영되지 않는다** —
이게 §1에서 말한 credit assignment 문제이고, PRM이 고치는 지점이다.

그리고 `std=0`이면(= 8개가 전부 같은 보상) `group_advantages`가 **0 벡터를 반환**한다:

```python
# grpo.py:21
if std < EPS_STD:          # EPS_STD = 1e-4
    return torch.zeros_like(r)     # ★ dead group
```

---

### 2-C. 성공한 증명 — GRPO가 `+advantage`로 강화하는 것

37그룹 296시도 중 **성공은 12건**뿐이다 (tactic 수: 10, 10, 12, 12, 12, 13, 14, 15, 16, 16, 16, 16).
그 중 **가장 짧은 것** (theorem `523789788107`, 10 tactic):

```coq
goal: forall (src dst : mreg) (rs : regset) (ls : locset) (e e' : eqs),
      subst_loc_part (R dst) (R src) High ...

a_0: Proof.
a_1: intros; red; intros.
a_2: exploit in_subst_loc_part; eauto.
a_3: intros [[A [B C]] | [A B]]; intros.
a_4: rewrite A, B.
a_5: apply H0 in C.
a_6: rewrite Locmap.gss.
a_7: apply Val.hiword_lessdef.
a_8: exact C.
a_9: rewrite Locmap.gso; auto.          → COMPLETE ✅
```

**10개를 한 번의 실수도 없이 연속으로 맞춰야 여기 도달한다.** p=0.816 이면 `0.816^10 = 13%`.
그리고 이런 성공이 **296시도 중 12건(4.1%)**뿐이라, GRPO가 "정답이 어떻게 생겼는지" 볼 기회가 극도로 적다.

---

### 2-D. 실패의 두 종류 — INVALID를 낸 마지막 tactic

§7의 분류를 실물로 본다. 인자를 받는 tactic이 죽인 139건을 두 부류로 나눈 것이다.

**① 없는 이름을 지어냄** (64건 — constrained decoding이 막을 수 있는 것)

```coq
depth 2: unfold loc_type_compat, loc_type; intros.
         ↳ 존재하지 않는 이름: ['loc_type']

depth 9: unfold select_loc_l in SL; rewriteSL in SL.
         ↳ 존재하지 않는 이름: ['rewriteSL']      ← ★ `rewrite SL` 을 띄어쓰기 없이 붙여 씀

depth 3: eapply m_trans; eauto.
         ↳ 존재하지 않는 이름: ['m_trans']        ← `Mem.mem_trans`? 를 잘못 줄임

depth 3: eapply Mem.range_split_2 with (c:=mid); eauto.
         ↳ 존재하지 않는 이름: ['range_split_2']
```

`rewriteSL`이 특히 인상적이다 — **토큰 경계가 어긋나 tactic 이름과 인자가 한 단어로 붙어버렸다.**
§1의 토큰화를 보면 왜 이런 일이 생기는지 보인다(`'e','apply',' loc','_','arguments',…`).
이런 건 **문법이 아니라 철자 수준의 실수**이고, 제약 디코딩이 물리적으로 막을 수 있다.

**② 실재하는 이름을 잘못 씀** (75건 — 제약 디코딩으로 **못 막음**)

```coq
depth 4: rewrite H in H0.              (H, H0 둘 다 프롬프트에 있음)
depth 3: rewrite (sep_swap4 P).        (sep_swap4 존재함)
depth 4: apply sep_swap5 with mid.     (sep_swap5 존재함)
depth 3: rewrite ! sep_assoc in H.     (sep_assoc 존재함)
```

**이름은 전부 실재한다.** 문제는 **타입이 안 맞거나, 그 시점 스코프에 없거나, 그 goal에 적용이 안 되는 것**이다.
이건 "무엇이 존재하는가"가 아니라 "**여기서 무엇이 통하는가**"의 문제라서, 제약 디코딩의 사정권 밖이다.
**이걸 고치려면 정책 자체가 더 똑똑해져야 한다 → RL의 몫이다.**

---

## 3. 데이터 가용성

| 파일 | 크기 | 시각 | 내용 |
|---|---|---|---|
| `data/grpo_rollouts/rollouts.jsonl` | 32.9MB | 07-13 10:57 | ⚠️ **E3-curriculum과 md5 동일** |
| `data/grpo_rollouts/E3-curriculum.jsonl` | 32.9MB | 07-13 10:57 | E3 (커리큘럼 ablation) |
| `data/grpo_rollouts/E2-dense.jsonl` | 22.4MB | 07-13 01:48 | E2 (dense reward ablation) |
| ~~round-1 원본~~ | — | — | ❌ **덮어써짐** |

### ⚠️ 데이터 위생 사고

`rango-grpo`(16/40, 우리 대표 결과)를 학습시킨 **round-1 원본 롤아웃이 사라졌다.**
`GRPORolloutSearchConf.out`이 모든 alias에서 `rollouts.jsonl`로 고정돼 있었다:

```bash
$ md5sum data/grpo_rollouts/*.jsonl
822e87508c15ae6fc9e2b642926c60cd  data/grpo_rollouts/E3-curriculum.jsonl
822e87508c15ae6fc9e2b642926c60cd  data/grpo_rollouts/rollouts.jsonl   # ← 같다
```

**지금 `rollouts.jsonl`로 재학습하면 round-1이 아니라 E3를 재학습한다.**
다행히 `all_results/20260711-*_grpo-rollout/logs/`의 그룹별 출력으로 **그룹 수준 통계는 복원**했다
(시도별 tactic 시퀀스는 복원 불가).

**조치 완료** — alias별 경로 분리 (`run_thm.py`):
```python
"grpo-rollout"        → data/grpo_rollouts/rollouts.jsonl
"grpo-rollout-dense"  → data/grpo_rollouts/E2-dense.jsonl
"grpo-rollout-g16"    → data/grpo_rollouts/E4-g16.jsonl
"grpo-rollout-r2"     → data/grpo_rollouts/E1-r2.jsonl
"grpo-rollout-retry"  → data/grpo_rollouts/retry.jsonl
```

---

## 4. 세 라운드 요약

| 라운드 | 그룹 | **총 시도**(=그룹×8) | 성공 시도 | dead(전멸) | 혼합(**신호O**) | 전부성공 | **버려지는 그룹** |
|---|---|---|---|---|---|---|---|
| **round-1 (naive)** ※로그 복원 | 41 | **328** | **30 / 328 = 9.1%** | 29 / 41 = 71% | **11 / 41 = 27%** | 1 / 41 | **30 / 41 = 73%** |
| **E2-dense** (QED shaping) | 40 | **320** | 31 / 320 = 9.7% | 28 / 40 = 70% | **11 / 40 = 28%** | 1 / 40 | 29 / 40 = 72% |
| **E3-curriculum** | 37 | **296** | 12 / 296 = 4.1% | 33 / 37 = 89% | **4 / 37 = 11%** | 0 / 37 | **33 / 37 = 89%** |

보상이 균일한 그룹(전멸 or 전부성공)은 advantage가 0이라 스킵된다.

> **학습 신호가 실제로 있는 그룹은 round-1 기준 41개 중 11개 (27%).**
> 나머지 **30개(73%)는 GPU를 태워 롤아웃을 8번씩 돌리고도 gradient에 한 번도 기여하지 못했다.**
> 시도 단위로 보면 **328번 중 298번(91%)이 버려진 계산**이다.

- **E2(dense reward)**: dead를 29→28로 줄였을 뿐. 평가 **12/40 = baseline 동률**. 이득 없음.
- **E3(커리큘럼)**: 오히려 신호를 **더 죽였다** (혼합 11 → 4).

---

## 5. ★ 실패의 종말 원인

`rollout_attempt()`가 INVALID에 **즉시 break**하므로, 스텝 수로 사인을 역추적할 수 있다.
스텝이 `max_steps`(20)면 소진, 그보다 적은데 실패면 마지막 tactic이 에러.

### 전체 회계 (모든 수치에 분모를 명시)

**E3 (`rollouts.jsonl`)**

| 항목 | 수 | 분모 | 비율 |
|---|---|---|---|
| 그룹(정리) | **37** | — | — |
| **총 시도** | **296** | = 그룹 37 × G=8 | 100% |
| ├ 성공 | 12 | / 296 시도 | **4.1%** |
| └ 실패 | 284 | / 296 시도 | **95.9%** |
| ⠀⠀├ **INVALID로 즉사** | **283** | / 296 시도 | **95.6%** (실패 중 **99.6%**) |
| ⠀⠀├ 스텝 소진(≥20) | **1** | / 296 시도 | **0.3%** (실패 중 0.4%) |
| ⠀⠀└ 빈 시도 | 0 | / 296 시도 | 0.0% |
| **총 tactic 스텝** | **1,539** | (성공시도 162 + 실패시도 1,377) | — |
| INVALID 스텝 | **283** | **/ 1,539 스텝** | **18.4%** ← per-step 에러율 |

**E2-dense**

| 항목 | 수 | 분모 | 비율 |
|---|---|---|---|
| 그룹(정리) | **40** | — | — |
| **총 시도** | **320** | = 그룹 40 × G=8 | 100% |
| ├ 성공 | 31 | / 320 시도 | **9.7%** |
| └ 실패 | 289 | / 320 시도 | **90.3%** |
| ⠀⠀├ **INVALID로 즉사** | **287** | / 320 시도 | **89.7%** (실패 중 **99.3%**) |
| ⠀⠀├ 스텝 소진(≥20) | **2** | / 320 시도 | **0.6%** (실패 중 0.7%) |
| **총 tactic 스텝** | **1,377** | (성공시도 134 + 실패시도 1,243) | — |
| INVALID 스텝 | **287** | **/ 1,377 스텝** | **20.8%** ← per-step 에러율 |

> **"증명이 너무 길어서 20스텝 안에 못 끝낸다"** = **3 / 616 총시도 = 0.5%**
> (E3 1/296 + E2 2/320). **가설 기각.**
> 반면 **"틀린 tactic으로 즉사"** = **570 / 616 총시도 = 92.5%**.

### 죽은 깊이 분포 (분모 = INVALID 즉사 건수)

**E3 — 분모 283건**

| 깊이 | 건수 / 283 | 비율 | 누적 |
|---|---|---|---|
| 1 | 3 / 283 | 1.1% | 1.1% |
| 2 | 41 / 283 | 14.5% | 15.5% |
| **3** | **93 / 283** | **32.9%** ← 최빈 | 48.4% |
| 4 | 49 / 283 | 17.3% | **65.7%** |
| 5 | 17 / 283 | 6.0% | 71.7% |
| 6 | 14 / 283 | 4.9% | 76.7% |
| 7 | 15 / 283 | 5.3% | 82.0% |
| 8 | 15 / 283 | 5.3% | 87.3% |
| 9–10 | 17 / 283 | 6.0% | 93.3% |
| 11+ | 19 / 283 | 6.7% | 100% |

**E2 — 분모 287건**

| 깊이 | 건수 / 287 | 비율 | 누적 |
|---|---|---|---|
| 1 | 4 / 287 | 1.4% | 1.4% |
| 2 | 58 / 287 | 20.2% | 21.6% |
| **3** | **86 / 287** | **30.0%** ← 최빈 | 51.6% |
| 4 | 48 / 287 | 16.7% | **68.3%** |
| 5 | 29 / 287 | 10.1% | 78.4% |
| 6 | 24 / 287 | 8.4% | 86.8% |
| 7–8 | 20 / 287 | 7.0% | 93.7% |
| 9+ | 18 / 287 | 6.3% | 100% |

**두 데이터 모두 깊이 4 이내에서 2/3가 죽는다** (E3 65.7%, E2 68.3%).
round-1 로그의 "평균 step 4.4"와도 일치한다.

---

## 6. ★ sparse reward의 수식

```
E3 : INVALID 283 / 총 tactic 스텝 1,539  →  per-step 에러율 18.4%  →  p(통과) = 0.816
E2 : INVALID 287 / 총 tactic 스텝 1,377  →  per-step 에러율 20.8%  →  p(통과) = 0.792
```
(분모 = **실제로 Coq에 제출된 tactic 스텝 전체**. 성공 시도의 스텝도 포함한다 —
E3는 성공시도 162 + 실패시도 1,377 = 1,539.)

롤아웃은 **단일 샘플 체인**이다 — `get_recs(..., 1, ...)`, n=1:

```python
# grpo_rollout.py:74  (수정 전)
recs = tactic_client.get_recs(len(proof.steps)-1, proof, dset, 1, beam=False, ...)
tactic = recs.next_tactic_list[0]
check = proof_manager.check_proof(prefix + tactic, new_proof.theorem)
if check.tactic_result == TacticResult.INVALID:
    break          # ← 한 번 틀리면 시도 전체가 끝
```

따라서 길이 L짜리 증명을 한 체인이 완주할 확률은 **p^L**:

| 증명 길이 L | p^L (한 체인) | G=8 중 최소 1회 성공 |
|---|---|---|
| 4 | 44.2% | **99.1%** |
| 8 | 19.6% | 82.5% |
| 12 | 8.7% | 51.5% |
| **14** (E3 성공증명 중앙값) | **5.8%** | **37.7%** |
| 16 | 3.8% | 26.8% |
| 20 | 1.6% | 12.1% |

**이게 dead group 73%의 정체다.** 12~16개 tactic을 **단 한 번의 실수도 없이** 연속으로 맞춰야 하는데
스텝당 실수 확률이 18~21%다. **지수적으로 죽는다.**

> **sparse reward는 보상 설계의 문제가 아니라 롤아웃 성공률의 문제다.**
> E2가 dense reward로 보상 *모양*을 바꿨는데도 dead가 28개로 남은 이유가 이것이다 —
> **보상을 촘촘하게 만드는 것**과 **성공 궤적을 더 많이 만드는 것**은 다른 일이다.

---

## 7. 무엇이 죽이는가

### tactic별 **거부율** — 이게 핵심 증거다

단순 건수보다 **"그 tactic을 쓸 때 Coq이 거부할 확률"**이 훨씬 많은 걸 말해준다.
분모를 둘 다 명시한다: **죽임**은 INVALID 283건 중, **통과**는 VALID 1,256스텝 중.

**E3 (`rollouts.jsonl`)**

| tactic | 죽임 / 283 | 통과 / 1,256 | **거부율** = 죽임/(죽임+통과) | 인자 |
|---|---|---|---|---|
| `eapply` | 20 (7.1%) | 11 (0.9%) | **64.5%** | ✅ 보조정리 이름 |
| `assert` | 20 (7.1%) | 13 (1.0%) | **60.6%** | ✅ 명제 |
| `induction` | 12 (4.2%) | 8 (0.6%) | **60.0%** | ✅ 항 |
| `apply` | 53 (18.7%) | 73 (5.8%) | **42.1%** | ✅ 보조정리 이름 |
| `rewrite` | 40 (14.1%) | 59 (4.7%) | **40.4%** | ✅ 등식 이름 |
| `destruct` | 38 (13.4%) | 129 (10.3%) | 22.8% | ✅ 항 |
| `unfold` | 24 (8.5%) | 116 (9.2%) | 17.1% | ✅ 정의 이름 |
| **`intros`** | 14 (4.9%) | **231 (18.4%)** | **5.7%** | ❌ **인자 없음** |

**E2-dense** (분모: INVALID 287건 / VALID 1,090스텝)

| tactic | 죽임 / 287 | 통과 / 1,090 | **거부율** | 인자 |
|---|---|---|---|---|
| `eapply` | 11 (3.8%) | 3 (0.3%) | **78.6%** | ✅ |
| `assert` | 10 (3.5%) | 5 (0.5%) | **66.7%** | ✅ |
| `apply` | 47 (16.4%) | 24 (2.2%) | **66.2%** | ✅ |
| `rewrite` | 46 (16.0%) | 34 (3.1%) | **57.5%** | ✅ |
| `induction` | 18 (6.3%) | 43 (3.9%) | 29.5% | ✅ |
| `destruct` | 25 (8.7%) | 89 (8.2%) | 21.9% | ✅ |
| `unfold` | 17 (5.9%) | 88 (8.1%) | 16.2% | ✅ |
| **`intros`** | 15 (5.2%) | **199 (18.3%)** | **7.0%** | ❌ |

### 읽는 법

**`intros`는 거부율 5.7%인데 `eapply`는 64.5%다. 11배 차이다.**

차이는 딱 하나 — **인자(보조정리/항의 이름)를 받느냐**다.
`intros.`는 이름을 안 대도 되니 거의 안 틀린다. `eapply loc_arguments_elf64_charact.`는
그 이름을 **정확히** 맞춰야 하고, 못 맞추면 Coq이 즉시 거부한다.

**인자를 받는 tactic이 죽인 비율:**
- E3: **209 / 283 = 73.9%**
- E2: **175 / 287 = 61.0%**

§2의 예시도 정확히 이렇다 — `destruct H; eauto; simpl; lia.` 에서 `H`가 그 시점에 존재하지 않는 이름이었다.
그리고 §1의 토큰화를 보면 왜 어려운지 보인다:

```
'eapply loc_arguments_elf64_charact.'
  → 13토큰 ['e','apply',' loc','_','arguments','_','elf','6','4','_','char','act','.']
```
**13조각을 순서대로 전부 맞춰야 한다. 하나만 어긋나도 존재하지 않는 이름이 된다.**

> 실패는 "**어떤 전략을 쓸지**"를 몰라서가 아니라 "**어떤 보조정리/항을 넣을지**"를 틀려서다.
> **정밀도(precision) 문제**이지 탐색 구조 문제가 아니다.

### 그렇다면 "이름을 지어내는 것"이 문제인가? — 아니다. 반만 맞다.

거부된 tactic을 **마지막(=INVALID를 낸) tactic 기준**으로 다시 분해했다. 분모 = INVALID 283건.

| 분류 | 건수 / 283 | 비율 |
|---|---|---|
| 인자를 받는 tactic | **139 / 283** | **49.1%** |
| ⠀⠀├ ★ **없는 이름을 지어냄** | **64 / 283** | **22.6%** |
| ⠀⠀└ **실재하는 이름을 잘못 씀** | **75 / 283** | **26.5%** |
| 인자 없는 tactic (`intuition.`, bullet 등) | 144 / 283 | 50.9% |

**두 가지가 드러난다:**

1. **거부된 tactic의 절반(50.9%)은 인자를 아예 안 받는다.** `now intros.` / `intuition.` / bullet 이
   문맥상 안 맞아 거부된 경우다. 이름 문제가 아니다.
2. **인자를 받는 139건 중에서도 절반 이상(75건)은 실재하는 이름을 쓴 것이다.**
   이름은 맞는데 **타입이 안 맞거나, 그 시점 스코프에 없거나, 그 goal에 적용이 안 된다.**

> ⚠️ **정정**: 앞선 표의 "인자형 tactic이 실패의 73.9%"는 *head가 인자형인 스텝*을 센 것이고,
> **실제로 죽인 tactic 기준으로는 49.1%**다. 그리고 그 중 "이름을 지어낸" 것은 **22.6%**뿐이다.

### 미탐색 축: constrained decoding (나중에)

생성 시점에 **실재하는 이름만 뽑도록 logit을 제약**하는 방법 (`prefix_allowed_tokens_fn`).
레포에 관련 코드는 **0줄**이다 (`LogitsProcessor` / `prefix_allowed_tokens_fn` grep 결과 없음).
(`TokenMask`는 프롬프트를 어텐션에서 가리는 ablation 도구로, 출력 제약이 **아니다**.
`try_candidates`는 뽑은 뒤 버리는 **사후 필터**이지 생성 제약이 아니다.)

**타당성 실측** — 후보집합 = 검색된 전제 50 + 검색된 증명 20 + 현재 goal + 스크립트의 식별자:

| | 인자가 후보집합 안에 있던 비율 |
|---|---|
| **통과한 tactic** (E3) | **467 / 467 = 100.0%** |
| 거부된 tactic (E3) | 312 / 391 = 79.8% |
| 통과한 tactic (E2) | 228 / 237 = 96.2% |

**→ 정답 금지 위험 0.0% (E3) / 3.8% (E2).** 통과한 tactic이 쓴 이름은 **하나도 빠짐없이**
우리가 이미 프롬프트에 갖고 있는 이름이었다. **제약을 걸어도 잃을 게 없다.**

| 기대 효과 | 값 |
|---|---|
| 막는 실패 | **64 / 283 = 22.6%** |
| per-step 에러율 | 18.4% → **14.2%** |
| L=14 완주율 | 5.8% → **11.6%** |

**우선순위: 낮음(나중에).** 재샘플링(§10 P1, 완주율 5.8% → 91.5%)이 훨씬 큰 레버이고, 그 위에
얹으면 추가 이득이 작아진다(이미 재시도가 나쁜 tactic을 걸러내므로). 회귀 위험 0%에 구현이
하루짜리라 언젠가는 넣을 만하다. **재샘플링 결과를 본 뒤 재평가한다.**

---

## 8. 다양성

분모 = 그룹 수.

| | 8시도의 tactic 시퀀스가 완전 동일 | **첫 tactic이 8개 전부 동일** | 그룹당 고유 시퀀스 수(중앙값) |
|---|---|---|---|
| **E3** | 0 / 37 그룹 = 0% | **27 / 37 그룹 = 73%** | **8 / 8** |
| **E2** | 0 / 40 그룹 = 0% | **34 / 40 그룹 = 85%** | **8 / 8** |

고유 시퀀스 수 중앙값이 **8/8** — 시퀀스 전체로는 완전히 다양하다.
**하지만 첫 tactic은 거의 항상 같다** (§2 예시도 8시도 전부 `Proof.`로 시작).
즉 8개 시도가 **같은 지점에서 출발해 뒤에서만 갈라진다.** 증명 초반의 갈림길은 전혀 탐색하지 않는다.

---

## 9. 문제 목록

| # | 문제 | 증거 | 심각도 | 상태 |
|---|---|---|---|---|
| **P1** | **롤아웃이 첫 실수에서 즉사.** `rollout_attempt`가 INVALID에 `break`. 재샘플링도 백트래킹도 없다. **탐색기(BFS)는 하는 일을 롤아웃은 안 한다.** | 실패의 **100%**가 INVALID | ★★★ | ✅ 수정 |
| **P2** | **성공률이 지수적으로 죽는다.** p=0.81, L=14 → 완주 5.8% → dead 73%. | §6 | ★★★ | ✅ (P1로 해소) |
| **P3** | **학습 신호가 있는 그룹이 41개 중 11개.** 나머지는 advantage=0으로 스킵. | §4 | ★★★ | ✅ PRM |
| **P4** | **실패 시도의 정보를 전부 버린다.** 어느 tactic이 에러였는지 coq-lsp가 알려주는데, 기록에 `result` 필드조차 없었다. | 옛 jsonl | ★★★ | ✅ 수정 |
| **P5** | **초반 탐색이 없다.** 첫 tactic이 73~85%의 그룹에서 8시도 모두 동일. | §8 | ★★ | ⏳ |
| **P6** | **학습셋이 39~41개 정리뿐.** CoqStoq에 안 쓰는 non-CompCert 정리 **4,305개**가 있다. | 별도 조사 | ★★★ | ⏳ |
| **P7** | dense reward(E2)가 이 문제를 못 고쳤다. 평가 12/40 = baseline 동률. | E2 | (교훈) | — |
| **P8** | 커리큘럼(E3)은 오히려 악화. 혼합 그룹 11→4. | §4 | (교훈) | — |
| **P9** | 롤아웃 경로 공유로 원본 유실. | §3 | ★★ | ✅ 수정 |
| **P10** | **학습/데이터/배포 정책이 셋 다 다름.** | §11 | ★★★ | ✅ 수정 |

---

## 10. 처방 + 구현

### [P1] 재샘플링 롤아웃 — 가장 큰 레버

**핵심 통찰: INVALID는 state를 바꾸지 않는다.** Coq이 거부했으니 goal이 그대로다.
그러니 **같은 state에서 다시 뽑으면 된다.** 시도를 버릴 이유가 없다.

```python
# grpo_rollout.py  (수정 후, max_retries=4)
for attempt_i in range(1 + max_retries):
    if attempt_i == 0:
        tactic = recs.next_tactic_list[0]
    else:
        # 같은 state 에서 π 로부터 다시 뽑는다 (온도 샘플링이라 매번 다름)
        r2 = tactic_client.get_recs(len(proof.steps)-1, proof, dset, 1, beam=False, ...)
        tactic = r2.next_tactic_list[0]

    res = proof_manager.check_proof(prefix + tactic, new_proof.theorem)
    steps.append({                       # ★ INVALID 도 전부 기록 — PRM 의 음수 신호다
        "example": example.to_json(), "tactic": tactic,
        "state_key": state_key,
        "result": res.tactic_result.name,   # VALID | INVALID | COMPLETE
        "retry": attempt_i,
    })
    if res.tactic_result in (COMPLETE, VALID):
        advanced = True
        break
    # INVALID → state 는 그대로. 재시도.
```

**효과 (실측 p=0.815 기준, 보수 가정 = 재시도가 상관돼 실효 독립 횟수를 절반으로 깎음):**

| k | 유효 통과확률 p_eff | L=14 완주율 | 8시도 중 성공 |
|---|---|---|---|
| **0 (기존)** | 0.815 | **5.7%** | 37.5% |
| 1 | 0.920 | 31.3% | 95.1% |
| 2 | 0.966 | 61.4% | 100% |
| **4 (채택)** | **0.994** | **91.5%** | 100% |

**비용은 25% 증가.** 스텝의 81%가 첫 샘플에 통과하므로 스텝당 기대 샘플 수 = `1/p ≈ 1.23`. 5배가 아니다.

**on-policy 성질은 유지된다** (중요): 재샘플링해도 **모든 tactic은 그 state에서 π로부터 샘플된 것**이고,
INVALID였던 것도 `(state, tactic, INVALID)`로 전부 기록한다. `flatten_group`이 (state,tactic) 쌍 단위로
학습하므로 **액션 수준에서 on-policy**다. 바뀌는 건 방문하는 state 분포뿐인데, 그건 기존 GRPO도 보정하지 않는다.

### [P3·P4] PRM-GRPO — dead group을 되살린다

coq-lsp의 검증 결과를 **per-tactic 보상**으로 쓴다 (Process-Verified RL, 2606.20068):

```python
# process_reward.py
PHI_SUCCESS          = +1.00   # 증명이 최종 검증됨
PHI_SOUND_BUT_FAILED = -0.05   # tactic 은 유효하나 증명은 실패
PHI_ERROR            = -0.10   # tactic 이 에러
```

credit은 **각 tactic의 첫 토큰**에만 건다 (논문 검증: first-token 59.2 > all-tokens 57.8 > last-token 57.5.
첫 토큰이 `apply`/`induction` 같은 **전략을 고르는 키워드**이기 때문):

```python
# grpo_train.py:176-186
m = cmask.float()
first = torch.zeros_like(m)
idx = m.argmax(dim=1)                        # 행별 첫 완성토큰 위치
first[rows, idx] = m[rows, idx]              # 완성토큰 없는 행은 0 유지
adv_tokens = ba.unsqueeze(1) * m  +  bap.unsqueeze(1) * first
#            ^ A_outcome(완성토큰 전체)      ^ A_process(첫 토큰만)
loss, kl = grpo_batch_loss_perstep(logp_new, logp_old, logp_ref, adv_tokens, cmask, ...)
```

**왜 dead group이 살아나는가** (단위테스트 `scripts/test_prm_grpo.py` 실측):

```
dead group (8시도 전멸, 예: §2의 그 그룹):
  adv_outcome = [ 0.000,  0.000,  0.000]   ← 기존 GRPO: std=0 → 스킵
  adv_process = [-1.414,  0.707,  0.707]   ← PRM: 에러 tactic 벌점, 유효 tactic 상대 보상
```

기존 GRPO는 *"8번 다 실패했으니 배울 게 없다"*고 버렸다. 하지만 **8번의 실패 안에도 정보가 있다** —
어떤 tactic은 Coq이 문법 에러로 뱉었고, 어떤 tactic은 유효했지만 끝까지 못 갔다.

**우리가 논문보다 유리한 지점**: 논문 저자들은 whole-proof 텍스트에서 tactic 경계를 역추적해야 하지만,
**우리는 tactic을 하나씩 생성하고 coq-lsp가 어느 것이 틀렸는지 직접 알려준다.**

### ⚠️ 재샘플링을 켜면 PRM 규칙을 두 군데 고쳐야 한다

안 고치면 조용히 잘못 학습한다.

**(1) 성공한 시도 안의 INVALID에 +1을 주면 안 된다.**
재샘플링을 켜면 한 시도가 *"틀린 tactic → 다시 뽑아서 → 맞는 tactic"* 을 거쳐 성공할 수 있다.
기존 규칙("성공한 시도의 모든 tactic에 +1")을 그대로 두면 **에러를 강화학습하게 된다.**

**(2) first-error propagation을 꺼야 한다.**
논문이 "첫 에러 이후 전부 −0.10"을 쓰는 이유는 whole-proof 생성에서 **에러 이후 텍스트가 망가진 state
위에 쌓이기** 때문이다. 우리는 에러가 state를 안 바꾸고 **같은 state에서 다시 뽑으므로** 그 뒤 tactic들은
멀쩡하다. 전파하면 **정상 tactic을 처벌한다.**

```python
# process_reward.py:checker_process_rewards  (수정 후)
for st in steps:
    is_err = st.get("result") == "INVALID"
    if is_err or (propagate_first_error and seen_error):
        out.append(PHI_ERROR)              # -0.10  (성공한 시도 안에 있어도 마찬가지)
    elif solved:
        out.append(PHI_SUCCESS)            # +1.00
    else:
        out.append(PHI_SOUND_BUT_FAILED)   # -0.05
```
`propagate_first_error` 기본값 **False**. whole-proof 롤아웃을 쓰게 되면 True로 켠다.

### 아직 안 한 것

- **[P6] 학습셋 확대** — non-CompCert **4,305개**. 평가는 CompCert라 **sibling 누출 0**.
  BFS-Prover-V2/STP의 "**barely provable**" 밴드(`0 < pass@k < 0.5`)로 필터링하면 advantage가 0이 아닌
  정리만 고를 수 있다. **지금은 40개라 그 밴드를 찾을 수조차 없다.**
- **[P5] 첫 tactic 다양성 강제** — 첫 스텝만 temperature를 올리거나 top-k 강제 분기.

### 하면 안 되는 것

- **dense reward 재시도** — E2가 이미 했고 baseline 동률(12/40). 보상 모양을 바꿔도 **성공 궤적 수**가
  안 늘면 소용없다는 걸 실측했다.
- **커리큘럼 재시도** — E3가 신호를 오히려 줄였다(혼합 11→4).

---

## 11. ★★ 베이스 모델 불일치

롤아웃을 분석하다 발견. **GRPO는 처음부터 잘못된 모델 위에서 학습되고 있었다.**

### 증거

체크포인트에 **`config.json`이 없다** — 순수 PEFT adapter 디렉토리다:

```bash
$ python3 -c "from transformers import AutoConfig
AutoConfig.from_pretrained('models/deepseek-bm25-.../checkpoint-54500')"
ValueError: Unrecognized model ... Should have a `model_type`

$ grep base models/deepseek-bm25-.../checkpoint-54500/adapter_config.json
  "base_model_name_or_path": "deepseek-ai/deepseek-coder-1.3b-instruct"
```

그래서 `get_model()`(`train_decoder.py:92`)이 이 디렉토리를 로드하면 **adapter_config를 따라 instruct**를
가져온다. 반면 `TRAINING_RUNBOOK.md:30`과 `grpo_train.py --model_name`은 **`1.3b-base`**를 넘긴다.
**두 모델 모두 HF 캐시에 있어 에러 없이 조용히 갈린다.**

### 결과: 세 정책이 전부 다르다

| 단계 | 실제 정책 | 코드 |
|---|---|---|
| **롤아웃 수집** | **instruct** + LoRA = 진짜 rango ✅ | 서버가 `get_model(checkpoint)` |
| **GRPO 학습** | **base** + LoRA = 존재하지 않는 하이브리드 ❌ | `grpo_train.py:265` |
| **평가/배포** | **instruct** + LoRA ✅ | 저장된 adapter_config가 instruct를 물려받음 |

**함의:**
- `log π_old`가 **롤아웃을 실제로 생성한 정책의 확률이 아니다** → importance ratio ρ가 의미를 잃는다.
- `ref_model`(KL 기준)도 실제 rango가 아니다 → KL이 엉뚱한 점을 붙잡는다.
- 최적화한 함수(base+LoRA)와 배포한 함수(instruct+LoRA)가 다르다.

`rango-grpo`가 16/40이 나온 건 base와 instruct가 충분히 가까워 LoRA delta가 전이된 것으로 보인다.
즉 **결과가 틀린 게 아니라, RL이 의도한 일을 하고 있지 않았다.**

### 평가는 오염되지 않았다 (중요)

저장된 어댑터들의 `adapter_config`가 **전부 instruct**를 가리킨다 (`rango-grpo`, `-e2`, `-e3`, `bfs-dpo` 확인).
→ **평가는 전부 같은 베이스 위에서 이뤄졌다.** `rango` vs `rango-grpo` 비교는 공정하며,
진행 중인 **robustness @180도 유효하다** (중단 불필요).

### 조치

- 앞으로의 모든 학습을 **instruct**로 통일 (`run_sota3.sh`, `train_progress_critic.py`,
  `progress_critic.py`, `progress_searcher.py` 수정 완료).
- **`rango-grpo-fix`** alias 추가 — 베이스만 정정한 재학습. `rango-grpo`(16/40) 대비
  **유일한 변인이 베이스 모델**이므로 이 버그의 실제 영향을 수치로 잰다.
- ⏳ `TRAINING_RUNBOOK.md`의 `--model_name`을 고칠 것 (아직 base로 적혀 있음).

---

## 12. 실행 큐

```
robustness @180
 └→ 오염 결과 수습 (fix_contested)
     └→ run_sota3.sh
         ① PGTS ×3                     (pgts / pgts-sym / pgts-pat)   학습 불필요
         ② progress critic 학습 → α sweep ×4                          LeanProgress
         ③ 롤아웃 재수집 (result 기록, 경로 분리)
         ④ rango-grpo-fix         base 정정만
         ⑤ rango-grpo-prm         + process reward
         ⑥ 재샘플링 롤아웃 수집 (k=4)
         ⑦ rango-grpo-retry       재샘플링만
         ⑧ rango-grpo-retry-prm   재샘플링 × PRM = 풀스택
```

### ④~⑧ 은 2×2 factorial

| | process ✗ | process ✓ |
|---|---|---|
| **재샘플링 ✗** | `rango-grpo-fix` (기준) | `rango-grpo-prm` |
| **재샘플링 ✓** | `rango-grpo-retry` | `rango-grpo-retry-prm` |

네 수치를 나란히 놓으면 **재샘플링의 효과**, **PRM의 효과**, **둘의 상호작용**이 각각 분리된다.
롤아웃 수집 단계에서 **dead group 비율이 73%에서 얼마나 떨어지는지 로그에 바로 찍히므로,
§6의 이론이 맞았는지 학습 전에 확인된다.**

비교 기준(@40): published baseline **12** · rango-grpo **16** · bfs-a1 **16** · portfolio **15**

---

## 13. 재현 스크립트

```bash
# ── 라운드별 요약 ────────────────────────────────────────────────
python3 - <<'PY'
import json
for f in ['rollouts','E2-dense','E3-curriculum']:
    g=[json.loads(l) for l in open(f'data/grpo_rollouts/{f}.jsonl')]
    att=[a for x in g for a in x['attempts']]
    dead=sum(1 for x in g if all(a['reward']<1 for a in x['attempts']))
    inv=sum(1 for a in att if a['reward']<1 and 0<len(a['steps'])<20)
    steps=sum(len(a['steps']) for a in att)
    p = 1-inv/steps
    print(f"{f:16} 그룹{len(g):3} dead{dead:3} per-step에러율 {inv/steps:5.1%} "
          f"p={p:.3f} → L=14 완주율 {p**14:5.1%}")
PY

# ── 죽인 tactic head 분포 ────────────────────────────────────────
python3 - <<'PY'
import json, sys; sys.path.insert(0,'src')
from collections import Counter
from model_deployment.pgts_searcher import tactic_head
g=[json.loads(l) for l in open('data/grpo_rollouts/rollouts.jsonl')]
k=Counter(tactic_head(a['steps'][-1]['tactic'])
          for x in g for a in x['attempts'] if a['reward']<1 and a['steps'])
print(k.most_common(8))
PY

# ── round-1(naive) 복원 — jsonl 은 유실, 로그에서 ────────────────
grep -h "\[rollout\] thm" all_results/20260711-*_grpo-rollout/logs/*.txt

# ── 단위테스트 (CPU, GPU 불필요) ─────────────────────────────────
PYTHONPATH=src python3 scripts/test_prm_grpo.py        # 16/16
PYTHONPATH=src python3 scripts/test_progress_critic.py # 11/11
```

---

## 14. 학습/평가 대상 정리 (겹침 검사)

CompCert는 CoqStoq TEST split 안에 **6,091개** 정리가 있다. `cc = [전역 idx of CompCert 정리]`.

| 용도 | 슬라이스 | 개수 | 전역 idx 범위 | 명령 |
|---|---|---|---|---|
| **평가 @40** | `cc[0:40]` | 40 | **0 ~ 68** | `run_all --num 40` |
| **평가 @180** (robustness) | `cc[0:180]` | 180 | **0 ~ 344** | `run_all --num 180` |
| **GRPO 학습(롤아웃)** | `cc[200:240]` | 40 | **376 ~ 443** | `run_all --start 200 --num 40` |

### ✅ 정리 인덱스는 겹치지 않는다

```
학습 ∩ 평가@40  = ∅
학습 ∩ 평가@180 = ∅
```
평가@180의 마지막은 `cc[179]`(전역 344), 학습 시작은 `cc[200]`(전역 376). **위치 기준 20개 여유.**
⚠️ **평가를 @200 이상으로 넓히면 충돌한다.** 그때는 학습 슬라이스를 뒤로 밀어야 한다.

**GRPO 학습 대상 40개 전역 idx** (round-1 수집 로그와 대조 완료, 일치):
```
376, 377, 380, 381, 382, 383, 384, 385, 388, 390, 393, 395, 399, 400, 401,
404, 405, 406, 407, 409, 411, 412, 414, 417, 419, 420, 421, 422, 424, 426,
428, 430, 431, 433, 435, 437, 438, 439, 440, 443
```

### ⚠️ 하지만 **파일**은 겹친다 — sibling confound

정리는 다르지만 **같은 `.v` 파일**에서 나온 것이 많다.

| | 겹침 |
|---|---|
| GRPO 학습 정리 40개 중, **평가@40 과 같은 파일**에서 온 것 | **16 / 40 = 40%** |
| GRPO 학습 정리 40개 중, **평가@180 과 같은 파일**에서 온 것 | **30 / 40 = 75%** |
| 평가@40 정리 40개 중, 학습과 같은 파일 | 14 / 40 = 35% |
| 평가@180 정리 180개 중, 학습과 같은 파일 | 71 / 180 = 39% |

겹치는 주요 파일 (평가@180 개수 / 학습 개수):
`lib/Integers.v` 12/3 · `common/Memory.v` 10/4 · `backend/ValueDomain.v` 7/1 ·
`flocq/Core/Raux.v` 6/2 · `backend/Asmgenproof0.v` 5/1 · `common/Values.v` 5/2 ·
`lib/Coqlib.v` 4/3 · `backend/Allocproof.v` 3/2 · `flocq/Prop/Double_rounding.v` 3/1 …

**왜 문제인가:** BM25 proof retrieval이 **같은 파일의 증명을 프롬프트에 통째로** 넣는다.
GRPO가 그 파일의 증명 스타일·보조정리를 익히면 **같은 파일의 평가 정리에 전이**될 수 있다.
→ 이득이 "**일반적 개선**"인지 "**같은 파일 익숙함**"인지 구분이 안 된다.

이게 문서들이 말하는 *sibling 전이 confound*이고, `rango-grpo-self`라는 alias 이름이 붙은 이유다
(same-project RL). **정답은 `rango-grpo-cross`** — 학습을 non-CompCert 프로젝트
(fourcolor 1,341 / math-classes 763 / buchberger 658 …, 총 **4,305개**)로 옮기면
**파일 겹침이 구조적으로 0**이 된다. 미구현. §10 [P6]과 같은 처방이다.

**정직한 서술:** 지금의 `rango-grpo` 결과(@40 16/40, @180 60/180)는 **sibling confound가
제거되지 않은 수치**다. SFT 누출은 아니다(정답 증명을 본 적 없고 탐색 rollout 기반). 하지만
"같은 프로젝트, 39%는 같은 파일"이라는 조건은 명시되어야 한다.

---

---

## 15. 문헌 대조 — G(그룹 크기)와 dead group

> 2026-07-14 조사. 각 논문 직접 fetch 검증. 미검증 수치는 배제했다.

### G는 얼마가 표준인가 — **8은 프론티어 표준값이다**

| 논문 | 도메인 | **G** |
|---|---|---|
| **DeepSeekMath** (GRPO 원논문) | 수학 | **64** |
| **DeepSeek-Prover-V1.5** | Lean whole-proof | **32** |
| **DeepSeek-Prover-V2** | Lean whole-proof | **32** |
| Goedel-Prover | Lean | 16 |
| DeepSeek-R1 / DAPO | 추론/수학 | 16 |
| **Goedel-Prover-V2** (최신) | Lean | **8** |
| Dr. GRPO | 수학 | 8 |
| **Process-Verified RL** (2606.20068) | **Lean, tactic 보상** | **4** |
| Kimina-Prover | Lean | 8 (GRPO 아님) |
| **BFS-Prover V1/V2, STP** | **Lean, tactic 단위** | **없음 — group RL 안 씀** |
| **TRL 기본값** | — | **8** |

**결론: G를 8에서 키우지 않는다.** 두 독립 논문이 같은 말을 한다:

- **Advantage Collapse (2605.21125)** 원문: *"Increasing group size **G ∈ [6,8] provides the best trade-off**
  between gradient effectiveness and computational cost"*
- **2-GRPO (2510.00977)** 원문: *"2-GRPO retains **97.6% of the performance of 16-GRPO**,
  while requiring only **12.5% of the rollouts**"*

### 우리 문제에는 이름이 있다: **advantage collapse**

**Advantage Collapse (2605.21125)** 원문:
> *"GRPO is prone to **advantage collapse**, a failure mode where homogeneous rewards within a group
> (e.g., all correct or all incorrect answers) yield near-zero advantages and vanishing gradients."*

문헌의 degenerate 그룹 비율:

| 출처 | 비율 |
|---|---|
| GRESO (2506.02177) | ~80% |
| SPO (2509.13232) | 60% → 80% (학습이 진행되며 증가) |
| Advantage Collapse (2605.21125) | 배치의 28~45% (지표명 **ACR**) |
| **우리 (round-1)** | **73%** |

**우리 73%는 이상치가 아니다. 다만 성격이 정반대다:**
- 남들: **전부 정답** → "문제가 너무 쉬워짐"(saturation)
- **우리: 전부 실패** → "모델이 못 품"

**고치는 방법이 다르다.**

### ★ 모든 prover 논문이 정리를 pass-rate로 거른다

| 논문 | 필터 |
|---|---|
| DeepSeek-Prover-V1.5 | *"moderate success rate"* — GRPO의 group-relative 성질에 맞추려 **의도적으로** |
| Goedel-Prover | pass-rate ∈ **(0, ½]** |
| Goedel-Prover-V2 | pass-rate ∈ **(0, 0.75]**, 배치마다 온라인 |

**dead group에 대한 문헌의 답은 "G를 키워라"가 아니라 "적당히 어려운 정리만 골라라"다.**

**그런데 우리는 정리가 40개뿐이라 고를 게 없다:**

| | 학습 정리 수 |
|---|---|
| DeepSeek-Prover-V1.5 | **4,500** |
| Goedel-Prover | **80,000** |
| Kimina-Prover | **200,000** |
| **우리** | **40** ← 2~3 자릿수 아래 |

**→ backward curriculum(§10)은 이 필터를 "없으면 만든다"로 뒤집은 것이다.**
`remaining=4` 로 잡으면 pass-rate가 **44%** 가 되는데, 이는 Goedel-V2의 필터 구간 `(0, 0.75]` 한가운데다.
**고를 정리가 없으니 원하는 난이도의 문제를 제조한다.**

### 미구현 대안 두 가지

- **DAPO dynamic sampling** (2503.14476). 원문: *"학습 전에, 배치가 정확도 0도 1도 아닌 샘플로
  가득 찰 때까지 계속 샘플링한다."* 제약: `0 < |{정답}| < G`. 3× 오버샘플, 10회 상한.
  DAPO의 5개 트릭 중 **기여가 가장 큼**(AIME 42→50). **비용: degenerate 80%면 롤아웃 5배**(GRESO 측정).
- **AVSPO** (2605.21125). 원문: *"ACR을 실시간 모니터링하며 가상 보상 샘플을 주입해,
  **추가 롤아웃 없이** homogeneous 그룹에서도 학습 가능하게 한다."* collapse 58~63% 감소, 4~6점 상승.
  **방법론 본문 미독해 — 채택 전 직접 읽을 것.**

**판단: backward curriculum 이 dead group 을 1% 로 만들면 둘 다 불필요하다.** 결과를 보고 결정한다.

### ⚠️ 기대치 보정 — 우리와 가장 비슷한 논문의 결과

**Process-Verified RL (2606.20068)** — tactic 단위 보상 + TRL + LoRA(r=64) + DeepSeek-Prover-V1.5-SFT.
**우리 세팅과 가장 가깝다.**

```
SFT baseline        55.9 ± 0.2
outcome-only GRPO   55.7 ± 1.0    ← SFT 를 못 이김
+ tactic 보상(PRM)  57.1 ± 0.8    ← +1.4pp
```

**"GRPO만으로는 SFT를 못 이겼고, PRM을 얹어야 +1.4pp였다."**
우리 `rango-grpo`가 published 대비 +4로 보이지만 **자체 rango 대비 +1**이었던 것과 일치한다(§11 참조).

**Goedel-Prover의 경고** — GRPO 이득이 예산을 늘리면 사라진다:
```
Pass@32:    SFT 57.5  →  GRPO 60.5    (+3.0)
Pass@3200:  SFT 62.7  →  GRPO 63.1    (+0.4)   ← 거의 소멸
```
그리고 GRPO 후 **증명 길이가 폭증하고 `try`/`all_goals` 남발이 늘었다**(`try` 평균 1.50 → 5.16).
**"더 잘 증명하는 법"이 아니라 "더 많이 찔러보는 법"을 배웠을 수 있다.**

### ★★ 가장 중요한 사실: 우리는 아무도 안 간 길에 있다

> **이 문헌에서 tactic 단위 정책에 GRPO를 돌리는 논문은 하나도 없다.**
> tactic 단위 prover 두 개(BFS-Prover V1/V2)는 **의도적으로 expert iteration + DPO를 선택**했다.
> group-relative RL 은 거의 전적으로 **whole-proof 생성기**에서만 쓰인다 —
> 거기선 한 롤아웃 = 증명 하나 = 자연스러운 pass/fail 이기 때문이다.

**이건 우리의 기여이거나, 경고다.** 우리가 마주친 문제들(dead group 73%, 길이 편향, MDP 두 층위,
credit assignment)이 **전부 이 지점에서 나온다** — 한 정리에 tactic 이 14개씩 달려 있는데
보상은 맨 끝에 하나뿐이라서다.

---
