# Leaf-first subgoal-단위 커리큘럼 (SFT→subgoal-GRPO)

**한 줄**: gold 증명 트리를 goal-수로 복원 → **각 subgoal 경계에서 seed** → **그 focused subgoal 하나만 닫으면 보상**(Qed 불필요) → **leaf(가장 깊은/작은 subgoal)부터** 스테이지로 위로. `remaining=4,6,8` 같은 평평한 tactic-거리 숫자 없이, **subgoal 트리 구조가 스테이지를 정의**.

작성 2026-07-25. 관련: [[sft-subgoal-grpo-naming]], `scripts/build_leaf_subgoal_curriculum.py`, `src/tactic_gen/grpo_rollout.py`(subgoal_reward), `all_log/run_subgoal_bigscale.sh`.

---

## 왜 이 설계인가 (앞선 두 실패의 교훈)

| 시도 | 방식 | 결과 | 왜 |
|---|---|---|---|
| **decompose-node** | subgoal 생성 지점(induction 직후)에서 seed, **Qed 보상** | 전부 **dead** | 그 아래 subtree 전체를 풀어야 reward → 사실상 s0급 난이도 |
| **remaining-거리** | Qed에서 N-tactic 앞(backward식), Qed 보상 | 신호는 남(52%→30%) but **회귀**(subgoal⊆fix, 2·15 손실) | subgoal 중간을 자름(비-canonical) + covariate shift |
| **leaf-first (이것)** | **subgoal 경계**에서 seed, **per-subgoal 보상** | (실행 중) | 첫 자식(쉬운 leaf)만 닫아도 신호 + subgoal 단위(canonical) |

핵심 전환: **보상을 "Qed"에서 "focused subgoal 닫힘"으로**. 그러면 decompose 직후에 seed해도 **첫 자식 하나만** 풀면 보상 → dead가 signal로.

---

## 트리 복원 (goal-수 궤적)

`c[i]` = step i **직전** 열린 goal 수.
- `c[s] > c[s-1]` = **분해**(decompose): 새 subgoal 생성, 첫 자식 focused → **subgoal-start**.
- `c[s] < c[s-1]` = **닫힘**: 다음 형제 focused → 또 다른 **subgoal-start**.
- subgoal-start `s`의 **size** = `c`가 `c[s]` 아래로 처음 떨어지기까지의 step 수 = 그 subgoal 증명 길이.
- **size 작음 = leaf**(더 분해 안 되는 말단) = 쉬움 = 스테이지 1.

---

## 돌아가는 예시 ① — `add_globals_match` (단순, 분해 1개)

gold 증명 (goal 수 c 표시):
```
step: 0      1                        2      3            4        5              6
tac:  Proof. induction 1;intros;simpl. auto.  destruct a1.. apply IH..  apply add_g..  Qed.
c:    1      1                        2      1            1        1              0
                └ 여기서 goal 1→2 (분해: base+귀납) ┘
```

**subgoal-start 추출**:
- s=2 (분해 직후, `initial_proof`="Proof. induction;intros;simpl."), level c[2]=**2**.
  - size: c가 2 아래로 → c[3]=1, 즉 **size=1** (step2 `auto.`가 base case 닫음). → **leaf, 스테이지 s1**.
- s=3 (base 닫힌 뒤, 귀납 케이스 focused), level c[3]=**1**.
  - size: c가 1 아래로 → c[6]=0(Qed), **size=3** (destruct·apply·apply). → **s2** (중간).

**per-subgoal 보상으로 롤아웃**:
```
[s1] seed = "Proof. induction 1;intros;simpl."   (2 goals: base, 귀납)
     모델이 tactic 생성 → goal 수 2→1 되면 = base case 닫힘 = reward=1  (Qed 안 가도 됨!)
     실측(fix 정책): 6/6 완결  ← base case(auto.)는 쉬워서 다 풂
     ⇒ decompose-node+Qed보상이었으면 0/6(dead)였을 게 6/6 로.

[s2] seed = "Proof. induction;intros;simpl. auto."   (1 goal: 귀납 케이스)
     goal 수 1→0 되면 = 귀납 케이스 닫힘 = reward=1  (여기선 = Qed)
     destruct+apply+apply 필요 → 더 어려움 → mixed(신호) 기대.
```

**부트스트랩**: s1(base case)를 먼저 마스터 → s2(귀납 케이스)를 SFT+s1 모델로 풀게 → 전체.

---

## 돌아가는 예시 ② — `Zdiv_interval_2` (중첩)

goal 수 궤적:
```
step: 0      1      2                      3                    4    5    6    7...      13
tac:  Proof. intros. assert(lo<=a/b<hi+1). apply Zdiv_interval_1. lia. lia. auto. ...     Qed.
c:    1      1      1                      2                    5    4    3    2         0
                    └ 분해① assert(1→2) ┘  └ 분해② apply(2→5, ①안에서 중첩) ┘
```

**subgoal-start / size / 스테이지**:
- 분해②(apply, s=4) 직후 focused subgoal들: `lia`로 닫히는 **말단들** → **size 1~2 = leaf = s1**.
- 분해①(assert, s=3) 로 생긴 보조목표 H(`lo<=a/b<hi+1`) 증명: 그 안에 분해②가 있어 **size 큼 = s2/s3**.
- 본목표(H 사용, step7~12): **size 큼 = s3**.

→ **트리 깊이 = 스테이지**: 가장 깊은 `lia` 말단(leaf)부터 s1, 그걸 감싸는 `apply`-보조목표가 s2, 최상위 본목표가 s3. **remaining 숫자 안 나옴** — 트리가 자연스럽게 순서를 정함.

---

## 메커니즘 (per-subgoal 보상)

`src/tactic_gen/grpo_rollout.py` `rollout_attempt`:
```python
seed_level = len(last_valid_goals)      # seed 시점 열린 goal 수
...
if res.tactic_result == VALID:
    ...
    if subgoal_reward and len(new_goals) < seed_level:   # focused subgoal 닫힘
        reward = 1.0                                     # Qed 불필요
```
- `subgoal_reward=True`면 goal 수가 seed 레벨 아래로 떨어지는 순간(=focused subgoal 완결) reward=1.
- COMPLETE(전체 Qed)도 여전히 reward=1 (최상위 subgoal일 때).

---

## 스테이징 (deep leaf → 위로)

`build_leaf_subgoal_curriculum.py`가 subgoal-start를 **size로** 3 스테이지 분류:
- **s1** = size ≤ 2 (leaf, 가장 깊음)
- **s2** = size 3~5 (중간)
- **s3** = size ≥ 6 (위쪽 subgoal/root)

학습: SFT 모델(rango-grpo-bs2-sft) init → **s1(leaf) rollout+GRPO → s2 → s3**. 각 스테이지는 이전 checkpoint에서 이어받아, 안쪽 leaf를 마스터한 발판 위에서 바깥 subgoal을 학습.

bigscale 실측(300-train): subgoal-start 총 **917개**, s1=174정리 대상.

---

## 실행

```bash
bash all_log/run_subgoal_bigscale.sh        # SFT→subgoal-GRPO(leaf), session-detached
# env(참고): SUBGOAL_REWARD=1(per-subgoal), SUBGOAL_SKIP_S0=1, SUBGOAL_POLICY=SFT모델
```
- init·롤아웃 정책 = **rango-grpo-bs2-sft**(SFT, on-policy).
- 평가: 1191@120s w2 → baseline 322 / GRPO 328 / **SFT→GRPO 338** 대비.
- 좋으면 rand200 600s.

**정직한 caveat**: 여전히 gold prefix로 subgoal 상태에 도달하므로 covariate shift 여지는 있음. 단 subgoal 경계는 remaining 중간-자르기보다 canonical하고, per-subgoal 보상이 leaf 신호를 살려 **decompose-node(dead)·remaining(회귀)의 두 실패를 동시에 회피**하려는 설계.
