# Invertible 분해 기반 Expert Iteration — 알고리즘 설계

작성 2026-07-27. 관련: `DECOMPOSITION_IDEAS.md`(아이디어·CompCert 실측), `SUBGOAL_PAPER_ASSESSMENT.md` §10(도달성 진단), `INTERLEAVED_SFT_RL.md`(교대 문헌), `IDEAS.md` ⑩·부록A.

---

## 0. 동기 (§10 한 줄)

기존 subgoal(leaf/cascade)은 **gold 분해**에 모델을 갖다 놓고 "닫기"만 학습 → 완전체 풀이서 **83% 미도달**(covariate shift). 병목 = "닫기"가 아니라 **"거기까지 가기(분해·도달)"**.
→ **모델이 스스로 도달 가능한 분해를 생성**하도록 학습. 분해를 **invertible(안전) 전술**로 만들면 도달성·on-policy 안전성이 구조적으로 보장(canonical·결정적, 자기 생성).

---

## 1. 전체 알고리즘 (한눈)

```
INPUT: 정리 집합 T, 초기 정책 π_0 (=SFT→GRPO, retrieval-augmented Rango)
반복 라운드 k = 0,1,2,...:
  # ── 수집 (invertible 분해 + 모델 닫기) ──
  successes = []
  for thm in T:
    s := state_after("Proof. intros.", thm)              # goal-reading
    cands := gen_invertible_candidates(s)                 # §2.1 (destruct/induction/inversion)
    for c in cands:                                       # §3 탐색(다양한 분해)
      s' := check_proof("Proof.\n"+c, thm)
      if s'.invalid: continue                             # Coq이 무효 분해 필터
      # 분해된 subgoal들을 π_k(+retrieval)로 닫기 시도 (G개, step 제한)
      leaves_closed := rollout_close(π_k, thm, prefix=c)  # §2.3
      if all_leaves_closed:
        successes += full_proof(c + closing_tactics)      # 도달가능·검증된 full 증명
  # ── 학습 (§4) ──
  π_{k+1} := train(π_k, successes)                        # RFT(full) + 분해-집중 process-GRPO
  # ── 평가 ──
  eval(π_{k+1}, held_out); if plateau: stop
OUTPUT: π_K
```

핵심: **분해(invertible, 로컬)는 lemma 불필요**, **닫기(apply/rewrite)는 π_k + retrieval**가 담당(§2.3). 성공한 분해가 다음 라운드 학습데이터(도달가능·on-policy).

---

## 2. 구성요소 상세

### 2.1 Invertible 분해 후보 생성 (type-directed 열거)

intros-후 상태의 각 가설 `name: type` 을 파싱 → 타입으로 후보 생성:

| 후보 | 조건 | 성격 |
|---|---|---|
| `destruct X` | X 타입이 유도형 데이터(nat/positive/Z/list/option/bool + CompCert AST), 함수·sort·R 제외 | 케이스 분기(IH 없음) |
| `induction X` | 위와 같되 **재귀 유도형**일 때 유의미(IH) | 케이스+IH |
| `inversion H` | H가 명제(등식 `=` / `In` / `<=` / H-가설) | 유도형 가설 역분석(CompCert step/typing에 핵심) |
| (자동) `intros`·`split`·`subst` | 항상 안전 | strict-invertible 포화 |

**"고르지 않고 다 열거 → 필터가 선택"**: 어느 변수를 destruct/induction하나를 미리 안 정하고, **유도형마다 후보를 다 만들고 (a)Coq 유효성 + (b)모델이 닫나로 필터.** 인자 = **탐색 차원**. 다양성 = {타깃}×{destruct/induction/inversion}×깊이.

### 2.2 Induction 인자 결정 — 미묘함 (v1 한계 → v2)

- **재귀형 vs 비재귀형**: `induction`은 재귀 유도형(nat/positive/list/tree)에서만 IH 제공. bool/option은 induction=destruct(중복). → **v2: 재귀형만 induction, 나머지 destruct.**
- **약한 IH (제일 중요)**: 다른 가설이 X에 의존하면 plain `induction X`는 IH가 약해 유효해도 못 풂. → **v2: `revert <deps>; induction X` / `induction X in *` 로 일반화 후 귀납(강한 IH).**
- **cap/순서**: 유도형-우선 정렬 후 앞 N개(연산량 bound). v2에서 gold-induction-타깃을 프라이어로.
- **v1(현재 실험)**: plain `induction X`(유도형 첫 3변수) = baseline. 먼저 "generic(≈0)보다 쪼개고 닫나" 확인 후 v2.

### 2.3 분업 — invertible(로컬) vs model+retrieval(lemma)

- **invertible 분해**는 **로컬 context(변수·가설)만** 씀 → **lemma 열거 불필요**(후보 = 가설 수로 bound). 폭발 없음.
- lemma가 필요한 **apply/rewrite(비-invertible, CompCert 78%)**는 **각 subgoal 내부 추론** → **π_k + Rango retrieval(BM25 proof + TF-IDF premise)**이 담당. 모든 lemma가 아니라 **retrieval이 관련만 선택.**
- → "쪼개기=invertible(local), 닫기=model+retrieval(lemma)". 사용자 직관과 일치.

---

## 3. 탐색 & 수집 (분해트리 → full proof)

- 한 정리에서 **여러 invertible 분해**(다른 destruct/induction 타깃) 시도 = 탐색. Coq이 무효 분해 즉시 필터.
- 유효 분해의 각 leaf를 π_k로 닫기(G개 롤아웃, step 제한). **모든 leaf 닫히면** = 성공한 full 증명(분해 prefix + 닫기 tactics).
- 이 full 증명은 **도달가능**(invertible+모델 자기 tactic) + **Coq 검증** → 학습데이터로 안전.
- 폭발 제어: goal-관련 타깃 우선·재귀형 우선·깊이 제한·결과 state 중복제거(state_key).

---

## 4. 학습 (성공 분해 → π_{k+1})

두 신호를 결합:
1. **RFT (full 증명 MLE)**: 성공한 (state, next-tactic) 궤적 전체를 SFT — **분해 스텝(destruct/induction/inversion)을 포함**. → 모델이 "어디서 어떻게 쪼개나"를 next-tactic으로 학습. (기존 subgoal은 닫기만 있었음.)
2. **분해-집중 process-GRPO**: 분해 지점에서 여러 후보 분해를 샘플 → 각각 나머지 롤아웃 → **모든 subgoal 닫히면 reward=1** → group-relative advantage로 **"어느 split이 통하나(useful)" 학습**. invertible이라 모두 valid → 학습 대상 = "닫기 쉬운 분해". (Tree-GRPO/VinePPO 계열.)

⚠ RFT 데이터는 전부 reward=1 → GRPO advantage 0 → **RFT는 `--sft`로, process-GRPO는 mixed 분해에**.

---

## 5. Expert Iteration 루프 (SFT ↔ invertible+GRPO)

```
π_{k+1} = π_k
        + RFT(성공 full 증명)                    # 도달+닫기 imitate
        + process-GRPO(mixed 분해 결정)           # 어느 분해가 통하나
반복 → held-out plateau까지 (ReST-EM 패턴: 몇 라운드 후 정체)
```
- **variance 스케줄(INTERLEAVED_SFT_RL ①)**: mixed 분해=GRPO / all-zero=(다른 분해 or hammer)로 SFT큐 / all-one=드롭.
- **다양성 붕괴 방지**: model soup / LoRA α 스케줄 / pass@k 곡선 보고.

---

## 6. 도달성 안전성 (why §10 fixed)

- 학습데이터 = **invertible(canonical·결정적) 분해 + 모델 자기 닫기** on **reachable state** = **자기 탐색(on-policy)** → **covariate shift 0, 도달성 갭 0.**
- 모델이 **"거기까지 가는 법(분해)"을 처음 학습** — 기존이 못 하던 절반. gold 분해(§10, 도달 16.7%)와 정반대로 안전.

---

## 7. 실험 프로토콜 (우리가 돌린 것)

```
Phase 0 (정적, §4.5): 300 train gold 증명 분류 → 순수 invertible+closer 21%(78% apply/rewrite 필요).
Phase 1 (generic 동적): intros/split/destruct-hyps → CompCert 거의 안 쪼갬(≈0), closure 0. → generic은 약함(§2.1 targeted 필요) 실증.
Phase 2 (goal-reading): intros-후 상태 40개 수집(invgr.jsonl).
Phase 3 (targeted build): 상태→가설 파싱→destruct/induction/inversion 후보(17정리×~5). 함수/sort 제외.
Phase 4 (targeted 롤아웃): cascade-s0+retrieval이 각 invertible-subgoal 닫나. [완료 ↓]
Phase 5 (되면): 성공 분해로 RFT → invertible+GRPO EI.
```

**Phase 4 실측 (2026-07-27, 78후보·17정리):**
| 지표 | 값 |
|---|---|
| **Coq 유효분해(실제 쪼개짐)** | **62/78 = 79%** (generic ≈0 대비 확실) |
| 정리 ≥1 유효분해 | 15/17 = 88% |
| **cascade+retrieval closure(reward>0)** | **3/78 = 3%** ⚠ |
| 정리 ≥1 subgoal 닫힘 | 2/17 = 11% (원판 leaf gold분해 mixed 36%보다 낮음) |

**결론**: ✅ **targeted invertible은 CompCert를 잘 쪼갬(79%)** — Ask3 동적 답. ⚠ **근데 모델이 그 subgoal을 거의 못 닫음(3%)** — 분해된 subgoal도 apply/rewrite 도메인추론 필요, cascade-s0(약함)가 못 함. **분해는 은탄환 아님, closing이 병목.**
**원인/다음**: (a) **built-in `auto`/`lia` 닫기 안 씀** — 분해 subgoal 상당수(base case·산술)는 auto/lia로 싸게 닫힐 것 → **다음: invertible + auto;lia;intuition.** (b) v1 plain induction = **약한 IH**(§2.2) → v2 일반화. (c) 더 강한 모델.

---

## 8. 연산량/스케일

- 분해 후보 = 정리당 가설 수(≤~8) → 폭발 없음(lemma 열거 안 하므로).
- 유효 분해만 모델 롤아웃(Coq이 무효 즉시 필터) → 비용 = 유효분해 × G × step.
- 소규모 파일럿(17정리)은 GPU0 여유로 ~30~40분. 전체 300은 라운드당 반나절급.

---

## 9. v2 개선 & open questions

- **v2 분해기**: 재귀형만 induction / 일반화 후 귀납(강한 IH) / gold-induction 프라이어 / inversion 확대.
- **하이브리드 닫기**: leaf에 π_k 실패 시 built-in `auto`/`lia`/`intuition`(hammer는 opam 리스크로 제외) 시도 → reachable SFT 데이터 추가(INTERLEAVED_SFT_RL 3.2).
- **open**: (a) targeted invertible이 CompCert를 실제로 얼마나 쪼개나(Phase 4 결과). (b) 분해가 dead 정리(모델이 flat으론 못 푸는)를 살리나 = 진짜 가치. (c) process-GRPO가 분해 정책을 실제로 개선하나.
