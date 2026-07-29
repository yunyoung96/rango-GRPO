# 병목 진단 (SFT / GRPO / SFT→GRPO / rango 공통) + 해결 방안

작성 2026-07-29. 방법: **추측 아닌 실측**(goldsft_bs2 gold 증명 + ei-safe-r1 롤아웃). 관련: [[research-direction-2026-07]], [[EI_PROGRESS]], [[HARVEST_ROUND]].
질문: 모든 방법이 rand200 ~37.5%에 수렴 — **가장 큰 병목이 retrieval 실패냐 / ranking 실패냐 / tactic 오예측이냐?**

---

## 결론 (3단계 소거)

1. **Retrieval — 병목 아님.** gold이 쓴 lemma의 **recall 88.5%**(top-50 안), **rank median 2~3위**(top-10 70%). 필요한 lemma는 대부분 잡히고 상위에 놓임.
2. **Built-in/환경 — 병목 아님.** automation(lia/auto/ring/congruence) tactic **VALID율 57~61%**(못 불러오면 ~0%여야 함) → **built-in 정상 로드·실행.** INVALID 중 automation은 12~16%뿐.
3. **★ 진짜 병목 = policy의 분해/navigation (+ 선택).** retrieval이 정답을 top-3에 놓아도 정책이 틀린 lemma를 66%(dead) 고르는데(=retrieval–generation gap), **그 오선택의 80%는 이미 앞서 분해/navigation을 틀려 gold 경로를 벗어난 뒤의 증상.** 순수 lemma 오선택은 8%뿐. → **root = navigation/분해, lemma-선택 = 2차.**

---

## 출처 / 측정 조건 (train인가 test인가, 어떤 정책인가)

| 결론 항목 | 데이터 파일 | train/test | 정책 / 알고리즘 |
|---|---|---|---|
| retrieval recall 88.5% · rank 2~3 | `goldsft_bs2.jsonl` (gold=사람 증명) | **train 300 (gold)** | **retrieval 시스템**(BM25+TF-IDF) — SFT/GRPO/SFT→GRPO/rango **전부 공유**, 알고리즘 무관 |
| 오선택 66% · INVALID 37% · dead/solved · 증명길이 · built-in | `ei-safe-r1.jsonl` 롤아웃(G=8) | **train 300 롤아웃** | **π₀ = SFT→GRPO** (`models/rango-grpo/adapter`) |
| ~37.5% 천장 | `all_results/rand200_*` | **test held-out 200** | SFT 33.5% / SFT→GRPO 37.5% 등 |

**train 문제냐 test 문제냐 → 둘 다 = capability 천장(generalization gap 아님):**
- 정책이 **train의 ~58%를 dead(8/8 실패)**, **test의 ~62% 실패**(=37.5% 성공) — 거의 같음.
- train coverage ~42% ≈ test 37.5% → **train도 test도 비슷하게 실패** = 과적합(train≫test)이 아니라 **정책 능력 자체의 벽.**
- → 진단은 **step 정보가 풍부한 train 롤아웃**에서 하고, 그 벽이 **test 성공률(~37.5%)로 표출.**

**왜 SFT→GRPO 하나로 진단해도 대표성 있나:** SFT/GRPO/SFT→GRPO/rango가 ① **같은 retrieval** ② 비슷한 **1.3B 정책** ③ 전부 **~37.5% 수렴**. SFT→GRPO는 그 중 **최고**라 하한도 아님. (retrieval 측정은 애초에 정책 무관 — 셋 다 같은 걸 씀.)

---

## 실측 데이터

### 정책 실패 양상 — 계층 구조 & 조건부 확률 (DEAD 정리, π₀=SFT→GRPO, train 롤아웃)

생성 tactic **18,127개**를 tactic 종류 → retrieval → rank → 정답여부 → 적용결과로 계층 분해:

```
DEAD 생성 tactic  18,127                              [즉각 결과: VALID=적용 / INVALID=Coq 거부]
├─ structural (분해: intro/destruct/induction/simpl..)  61%   VALID 60% / INVALID 40%   ← 최대 volume=navigation
├─ automation (auto/lia/ring/congruence..)              31%   VALID 76% / INVALID 24%   ← built-in 정상
└─ lemma 참조형 (apply/rewrite/eapply/exact..)            8%   VALID 32% / INVALID 68%   ← 실패 집중
       └─ project-lemma citation  (1,582건)
           ├─ P(retrieval에 있음 | 참조) = 88%
           │    ├─ rank top5 :  63%   → P(정답 선택) 24%   | VALID 34% / INVALID 66%
           │    ├─ rank 5–10 :  16%   → P(정답 선택) 26%   | VALID 23% / INVALID 77%
           │    └─ rank 10+  :  21%   → P(정답 선택) 20%   | VALID 34% / INVALID 66%
           │    ⇒ 정답 선택 23%  → VALID 49% / INVALID 51%   (정답 골라도 절반 거부=적용오류)
           │      오선택   77%  → VALID 27% / INVALID 73%
           └─ P(retrieval에 없음 | 참조) = 12% (헛참조)   → VALID 22% / INVALID 78%
```

**조건부 확률로 읽으면:**
- **P(lemma 참조형 | tactic) = 8%** — 대부분(92%)은 structural(61%)+automation(31%). → **volume은 분해/navigation이 압도.**
- **P(INVALID | lemma 참조형) = 68%** (automation 24% 대비) → lemma 적용이 **저-volume·고-실패** 집중점.
- **P(retrieval에 있음 | 참조) = 88%** → retrieval는 제 몫.
- **P(정답 선택 | retrieval됨) = 23%뿐** = **77% 오선택.**
- **★ rank가 정답을 예측 못 함**: P(정답|top5)=24% ≈ P(정답|10+)=20% → **상위 후보 중에서도 틀린 걸 고름** = **ranking 문제 아닌 selection 문제.**
- **P(INVALID | 정답 선택) = 51%** → 정답 골라도 절반은 오적용 → **selection + application 둘 다.**
- **rank가 INVALID율도 못 낮춤**: INVALID(top5)=66% ≈ INVALID(10+)=66% (5-10은 77%로 더 나쁨) → 상위여도 거부율 동일 = **ranking 문제 아님 재확인.**
- **structural도 INVALID 40%**(분해 tactic 자체가 자주 거부) + VALID여도 wrong-choice(off-path) 가능 → 분해가 실패 volume·원인의 핵심(§divergence 61%).
- **헛참조(retrieval 밖)가 최악 INVALID 78%** — 존재하지 않는/후보 밖 이름을 생성.

#### DEAD vs SOLVED 요약 (계층 leaf 대조)
| 지표 | SOLVED | **DEAD(실패)** |
|---|---|---|
| P(INVALID \| tactic) | 26% | **37%** |
| P(정답 선택 \| project-lemma 참조) | 61%* | **34%*** / 23%(citation) |
| P(INVALID \| 정답 선택) | 28% | 47% |
| automation VALID율 | 57% | 61% |
| attempt당 step(길이) median | 7 | **10** |
| 실패의 ~99% | = 600s 타임아웃(틀린 답 아님, 탐색이 못 찾음) | |

*정리단위(gold이 project-lemma 쓰는 정리) 기준. citation단위(위 트리)는 23%.

### gold 증명 step 구성 (빡센 재검증 — built-in 분리)
| 종류 | 비율 |
|---|---|
| structural/local (intro/destruct/induction = **분해/navigation**) | **65%** |
| automation (built-in: lia/auto/ring) | 14% |
| **project-lemma apply (retrievable=선택 대상)** | **13%** |
| stdlib/built-in lemma | 9% |

### 두 개의 "랭킹"은 다름 (혼동 주의)
- **retrieval rank** = retriever가 정답을 프롬프트 몇 번째에 놓나 → **높음(2~3위)**.
- **policy 생성확률** = LLM이 실제로 그 lemma를 쓸 확률 → **낮음(dead 66% 오답)**.
- 병목 = **이 둘 사이 gap**(정답이 눈앞 상위에 있는데 1.3B가 안 씀).

### ★★ 실패는 어디서 만들어지나 — divergence 지점 (가장 중요)
주의: 위 트리의 "18,127 tactic"은 **dead attempt의 모든 step 합**(전체 population)이지 실패-유발 tactic이 아님. **실패를 만든 시점** = 정책이 **gold 경로를 처음 벗어난 그 tactic**으로 별도 측정 (dead attempt 1,168개):

| gold 경로를 **벗어나게 한** tactic 종류 | 비율 |
|---|---|
| **structural (분해: destruct/induction/intro)** | **61%** ← 실패 원인 |
| automation | 14% |
| **gold 경로 끝까지 유지했으나 실패**(적용오류/길이로 못 끝냄) | 13% |
| other | 6% |
| **lemma-apply** | **5%** |

- **벗어나기 전 on-path 깊이 median = 3 step** → **아주 일찍(≈3번째 tactic) 경로 이탈.**
- 종료 양상: **stuck(유효 tactic 못 냄) 74%** / wander(max-step 미도달) 26%.

**→ 실패는 lemma가 아니라 "잘못된 분해(structural)"가 만든다 — 61%, ~3 step째 일찍.** 정책이 **어느 변수 induction / 어느 가설 destruct를 틀려** gold 경로를 벗어나고, 그 뒤 헤매다(74% stuck) 실패. lemma가 divergence 원인인 건 **5%뿐** = "**오선택의 80%가 offpath 증상**"의 원천. **root = 초반 분해 오예측**, lemma-선택은 하류.

### ★ 오선택 INVALID을 gold 경로와 대조 — "tactic 틀림 vs lemma만 틀림 vs 이미 offpath"

정책이 오선택+INVALID한 step을, **그 state를 gold이 지나는지 + gold이 거기서 뭘 하는지**로 분류 (dead, π₀ 롤아웃):

| 분류 | 비율 | 의미 |
|---|---|---|
| **tactic OK, lemma만 틀림** | **8%** | gold도 이 state서 lemma-apply, 다른 lemma를 씀 = **순수 selection 오류** |
| **tactic부터 틀림** | **12%** | gold은 이 state서 구조적/automation인데 정책이 lemma 적용 = **tactic kind 오류** |
| **★ 이미 앞서 navigation 어긋남** | **80%** | gold이 **안 지나는 state**에서 헤맴 = **"오선택"은 원인 아닌 증상** |

→ **"lemma 오선택 66~77%"의 80%는 사실 navigation 증상.** 정책이 **더 앞 step에서 분해/navigation을 틀려 gold 경로를 벗어난 뒤**, 엉뚱한 state에서 안 맞는 lemma를 던짐. **순수 "맞는 state·틀린 lemma"는 8%뿐.**

### 실제 예시 (rank = 그 state의 retrieval 순위)

| 정리 | 정책 tactic (rank) | gold 정답 (rank) | 분류 |
|---|---|---|---|
| **Round_pred.v#52** | `apply Rnd_N0_pt_unique` (**rank 0**) | Rnd_N0_pt_unique_prop (**rank 35**) | **lemma만 틀림** — 정답이 rank35에 묻히고 오답이 top1 |
| Digits.v#40 | `rewrite Zdigits_abs` (rank 1) | Zdigits_correct (rank 2) | lemma만 틀림 |
| Unusedglobproof.v#49 | `eapply eval_builtin_args_determ` (rank 0) | eval_builtin_arg_inject (rank 6) | offpath (navigation) |
| Digits.v#4 | `rewrite Zdigit_opp` (rank 0) | Zpower_gt_0 (rank 7) | offpath |
| ValueDomain.v#9 | `apply dec_eq_sym` (rank 6) | dec_eq_true (rank 12) | offpath |
| Events.v#54 | `apply known_builtin_ok` (rank 0) | extcall_free_ok (rank 2) 외 8개 | offpath |
| NeedDomain.v#38 | `apply iagree_shru` (rank 7) | iagree_mone (rank 2) | offpath |
| Constpropproof.v#6 | `... set_res_lessdef` (rank 3) | set_reg_lessdef (rank 2) | offpath |

**2가지 패턴:**
- 정책은 대개 **top-rank lemma를 뽑음**(rank 0~7) — 근데 그 state엔 틀림. **이름 비슷한 이웃 lemma 혼동**(determ↔inject, unique↔unique_prop, sym↔true, res↔reg, Zdigit↔Zpower).
- 소수(8% on-path lemma)에선 **정답이 rank 35에 묻히고 오답이 top1**(Round_pred) → 여기선 **ranking도 기여.**
- **정답도 retrieval엔 있었음**(대부분 상위) → **retrieval 실패 아님.**

---

## 정확한 문제 정의

**1차 병목 = 분해/navigation (retrieval·built-in 아님).** 오선택 대조로 재확인:
- **root = 구조적 분해/navigation** (step의 65%): 어느 변수 induction / 어느 가설 destruct / 언제 case-split. **오선택 INVALID의 80%가 "이미 gold 경로를 벗어난 state"**에서 발생 = 앞선 분해 오류의 증상. (subgoal/EI가 계속 부딪힌 벽 = 이것.)
- **2차 = lemma 선택/적용** (step의 13%): 맞는 state서도 **8%는 순수 오선택**(정답 top-rank인데 이웃 lemma 혼동, 또는 정답이 rank35에 묻힘), 정답 골라도 47% 오적용. 단 대부분(80%)이 navigation 증상이라 **선택만 고쳐도 상한 존재.**
- 둘 다 **긴 증명(dead median 10-step)**에서 누적 → 600s 타임아웃.

→ **1.3B 정책의 "올바른 분해로 gold 경로 유지 + 후보 중 정답 선택" 능력**이 공통 천장. retrieval·built-in은 제 몫. RL(GRPO) marginal도 이 때문.

---

## 심화 진단 (2026-07-29) — 분해는 selection이 아니라 **generation(coverage) 문제**

divergence(분해)가 root임을 확인한 뒤, "정답 분해를 못 고르나 vs 아예 못 만드나"를 측정:

**① Coverage (pass@8): 정책이 gold 분해를 8시도 안에 맞는 state서 생성 = 22%뿐.**
→ **78%는 정답 분해를 아예 생성 못 함** = ranking/selection이 아니라 **generation(coverage) 문제.** (lemma는 retrieval이 후보에 넣어주지만, **분해는 retrieval 대상이 아니라 순수 생성** — 그래서 더 어려움.)

**② Canonicality (전이 가능성):**
| gold 분해 종류 | 비중 | 정책 생성률(coverage) |
|---|---|---|
| bare/canonical (변수/가설에 직접 induction·destruct) | 47% | **37%** |
| other (unfold/assert/generalize 등) | 38% | 9% |
| compound/idiosyncratic (`destruct (Rle_or_lt 0 x)` 등 계산항) | 16% | 11% |
→ **canonical은 그나마 생성·전이 되고**, other/compound가 coverage 최악(9~11%).

**③ divergence 오류 유형 (1,007건):**
| 유형 | 비중 |
|---|---|
| **분해 종류 맞음·대상 틀림** (gold `destruct H1` → 정책 `destruct H2`) | **49%** |
| 다른 분해 tactic 선택 (gold induction → 정책 destruct 등) | 29% |
| gold=lemma에서 이탈 | 12% |
| 성급한 lemma/automation·기타 | ~10% |
→ **정책은 "분해해야 함"은 대체로 앎(78%가 분해-vs-분해), 근데 대상/형태를 틀림.**

**★ 알고리즘 함의 (방향 전환):**
- **selection-only DPO는 상한 낮음** — 정답 분해를 22%만 생성하니 rerank할 후보에 정답이 없음(78%).
- **structural branch-and-verify(대상 열거)가 핵심 레버**: 오류의 49%가 "대상 틀림"이고 대상 공간(각 가설 destruct / 각 변수 induction)은 **작고 열거 가능** → 정답 대상을 **후보에 강제 주입**(coverage 22%→↑) 후 verify+DPO. lemma top-K보다 이게 우선.
- coverage 근본 개선엔 **더 큰 base(생성력)** 또는 **명시적 분해-제안 학습**도 후보.

---

## 해결 방안  (진단 반영: **root = 분해 divergence 61%, lemma-선택은 하류**)

### 왜 바닐라 GRPO/RL로는 안 되나
outcome-GRPO: ① **credit 배정 coarse**(어느 step이 fatal인지 못 집음) ② **dead group 신호 0**(positive 없음) ③ **exploration**(낮은 생성확률→안 뽑음). critic(PPO)도 우리 환경선 학습 실패(explained_var≈0). → 이건 "**후보 중 정답 고르기**" = **판별(discrimination) 문제**라 **대조/DPO가 적합.**

### ★ 1차 레버 — 분해 divergence 교정 (실패의 61% 직격)
**divergence 지점** = 정책이 gold 경로를 처음 벗어난 그 **structural tactic**(median 3 step). 그 지점은 **아직 gold이 지나는 on-path state**라 정답이 명확:
- **positive** = gold의 그 state 분해 (예 `destruct H1` / `induction n1`)
- **negative** = 정책의 divergence 분해 (예 `destruct H2` / 다른 변수 induction / 성급한 apply)
→ **(state, gold분해, 오분해) DPO 쌍** — **on-path라 안전**(정책이 실제 도달) + **실패 61% 원천을 정면**으로.
- 데이터: **divergence 추출 로직(방금 만든 것)을 쌍 생성기로** 그대로 사용.

**+ structural branch-and-verify** (lemma top-K의 분해판): 분해 결정 노드에서 **후보 분해 열거**(각 가설 `destruct` / 각 변수 `induction` — lemma top-K보다 분기수 적어 저렴) → BFS로 QED 도달 확인 → verified positive. **dead 정리에도 on-policy positive 생성**(못 풀던 것 새로 풂 = search-rollout 효과).

### 2차 레버 — lemma-선택 DPO (top-K 강제분기)
on-path lemma 오선택(**8~20%만**, 상한 낮음)을 커버. premise-tactic 노드서 **retrieval top-8~10 강제분기 → correctness(QED 도달)-DPO**.
- **exploration 우회**: 정답 premise(retrieval 상위)를 강제 탐색 → under-generate하던 정답을 positive로(생성확률↔rank gap 메움).
- **validity-DPO(실패)와 다름**: correctness 기준(오선택 대부분 VALID-but-wrong이라 validity론 못 잡음).
- 적용오류(정답 골라도 **51% INVALID**)엔 `eapply`/`apply ... with` 형태도 열거.
- 한계: top-K 밖 정답(~30%), budget 안 QED 못 닿는 dead는 positive 0.

### DPO + GRPO 결합
- **순차(권장)**: 한 라운드 = 검색(structural+premise 분기 BFS) → **DPO(분해+선택) → GRPO(outcome)**. `grpo_train --dpo`/GRPO chain(코드변경 소).
- **한 BFS 트리로 다 수확**: divergence 노드→분해쌍, premise 노드→선택쌍, 성공 완주→RFT/GRPO.
- **π_ref는 고정 π₀ 앵커**(drift 차단). 결합손실 `L_GRPO+λL_DPO`도 가능하나 나중.

### 보조
- retrieval rank를 top-5로 더 끌면 top-K 분기 recall↑(시너지). validity penalty(INVALID 억제) 값쌈·부차.

### 선행 실패 실험(algo-dev-dpo)과의 차이 — 재실패 방지
`algo-dev-dpo` 브랜치가 이미 DPO를 시도했고 **약효과**(커밋 `BFS-full 13/40=32.5%, DPO 약효과` = bfs-dpo=plain). 그건 **BFS-Prover 논문(2502.03438) 충실 DPO**였고, 우리 진단이 실패 원인을 설명 + 이 설계가 그 구멍을 메움:

| | algo-dev-dpo (BFS-Prover DPO, 실패) | 이 설계 (divergence-DPO) |
|---|---|---|
| **negative** | **INVALID(컴파일에러)만** (논문 준수) | **VALID-but-wrong**(적용되나 경로 이탈) ← 우리 실패의 80%+ |
| **positive/탐색** | 정책 샘플 트리(정답 under-generate) | gold 분해(divergence) · (v2) top-K 강제 enumeration |
| **타깃** | 일반 state 아무데나 | **divergence(fatal 분해) 지점** |

→ **INVALID-only negative는 "그럴듯하게 적용되지만 틀린" 선택/분해를 못 잡음** = 약효과의 원인. divergence-DPO는 **그 VALID-but-wrong을 negative로 직접** 씀.

### 구현/실행 상태 (2026-07-29)
- **v1 구현 완료**: `scripts/build_divergence_dpo.py`(divergence 쌍 508개, chosen=gold분해 induction/destruct/unfold 중심) · `all_log/run_divdpo.sh`(dpo_train, **GPU1 전용**, init=π₀=ref, β0.1/lr5e-7/ep2 → rand200 w2 평가) · `run_divdpo_chain.sh`(safe-EI eval 끝나면 자동 착수).
- v2(top-K/structural branch-and-verify)는 `bfs_prover_searcher` expansion 추가 후.

---

## 기존 자산 매핑
| 필요 | 자산 |
|---|---|
| **divergence 쌍 추출** (state, gold분해, 오분해) | 신규 소규모 스크립트(방금 로직) |
| structural + premise 분기 BFS + 트리 덤프 | `bfs_prover_searcher.py` (expansion 확장) |
| 트리 → (chosen,rejected) 쌍 | `bfs_dpo_data.py` (`leads_to_success`) |
| DPO / GRPO 학습 | `dpo.py` · `grpo_train.py --dpo` / GRPO (KL→π₀ = `--ref_adapter`) |

---

## 정직한 기대치
- **root=분해(divergence 61%)이고 어렵다**: idiosyncratic + reachability = subgoal/EI가 반복해 부딪힌 벽. **divergence-DPO는 그 fatal tactic을 정확히 겨눈 첫 시도**지만 1.3B 천장·도달성 한계 남음.
- **lemma-선택 DPO는 하류 8~20%만** → 보조.
- 정답 골라도 **51% INVALID**(적용오류) · structural도 **40% INVALID** → 선택 넘어 **적용·분해 능력 자체**가 벽.
- → **홈런보다 마진**. 단 **divergence 대조 + correctness-DPO는 미시도 조합**이라 시도 가치 有.

## 다음 액션
1. **divergence 쌍 추출** 스크립트(방금 로직) → (state, gold분해, 오분해) DPO 데이터 생성.
2. `bfs_prover_searcher`에 **structural + premise 분기 BFS** expansion 추가(소규모).
3. 소정리셋: 트리 덤프 → DPO쌍(분해+선택) → `grpo_train --dpo`(π₀ 앵커) → GRPO → rand200.
4. EI eval 끝나 GPU 나면 GPU1에서 파일럿.

---

## 신규 알고리즘 제안 (심화 진단 + 문헌, 2026-07-29)

**메타 원칙 2개** (진단에서 도출):
- **capacity 천장(모두 37.5%)은 1.3B 재학습보다 test-time compute(search·repair)로 넘는 게 확실.** 학습측은 천장과 싸우고, 추론측은 천장을 넘음. (Proverbot9001은 **value 없이 search만으로 CompCert 27.5%** — 1907.07794.)
- **학습된 scalar critic 필요한 건 고위험**(우리 PPO critic 실패, explained_var≈0) → **value-free 신호**(policy logprob / MC-rollout 성공률 / verifier)만.

**제안 (우선순위, 전부 value-free):**

| # | 방법 | 우리 진단 근거 | 문헌 | 비용 |
|---|---|---|---|---|
| **1★** | **value-free structural search** (▶ **전체 설계·의사코드·구현계획: [[VALUE_FREE_SEARCH]]**): 분해 노드서 **후보 분해(각 가설 destruct/각 변수 induction) 열거 + MC-rollout 성공률로 랭킹 + stuck시 backtrack** | coverage 22%(정답 분해 안 생성)·오류 49% "대상 틀림"·stuck 74% 직격 | Proverbot 1907.07794 · **MC-rollout 스코어=Math-Shepherd 2312.08935를 network 없이 온라인 사용** | 추론compute(학습X) |
| **2** | **분해-rationale SFT** (Lean-STaR): structural tactic **앞에 "왜 이 변수 induction"** 한 줄 생성, gold 합리화로 부트스트랩 | coverage 22% = generation 문제를 학습으로 직격 | Lean-STaR 2407.10040 · (teacher distill) DS-Prover-V2 2504.21801 | 싼 SFT, critic X |
| **3** | **HER 재라벨**: 실패 롤아웃(62%)을 **"닫은 subgoal의 성공 증명"으로 재라벨** → 데이터 증강 | dead 58% 신호0을 데이터로 전환 | HER-for-provers 2112.10664 | 싼, value-free |
| **4** | **Baldur repair**: stuck 상태 + **Coq 에러 메시지**를 넣어 재시도 | **stuck 74%** 직격 | Baldur 2303.04910 | 싼 추론 |
| 5 | **divergence-DPO** (진행 중) | 오선택/분해 대조 | CuDIP 2502.18532(양성) | 싼 학습 |
| 보너스 | **decode-time logit-bias** — retrieved 이웃 증명의 tactic 쪽으로 상향 | retrieval–generation gap(정답 프롬프트엔 있음) | Rango 2412.14063(proof 검색 +47%) | 매우 싼 |

**★ divergence-DPO caveat — 문헌 2회 조사 reconciliation (정직)**: step-level DPO 평가가 **엇갈림**:
- **양성/최우선**: CuDIP(2502.18532, 첫 formal-ATP DPO, 양성) + Step-DPO(2406.18629, step-local 선호). 한 조사는 **divergence-DPO를 #1로 추천.**
- **절제**: LeanListener(2503.09730)는 step-DPO가 valid-tactic 못 올리고 length bias, **subgoal-count 보상 GRPO가 낫다**고 보고.
→ divergence-DPO는 **합리적 첫 베팅(진행 중)이되 기대 절제, fallback = subgoal-reward GRPO 또는 #1 value-free search.**
- (DS-Prover-V1.5 2408.08152: **binary verifier 보상 RL(RLPAF)+RMaxTS로 critic 없이** 됨 — value-free 방향 지지.)

**논문 관점 (급한 상황)**: 심화 진단(coverage 22% = generation·대상 열거가 답)은 **강한 analysis 컨트리뷰션**. positive number가 필요하면 **#1(value-free structural search)이 천장을 넘는 가장 확실한 길**(추론compute, critic 불요). #2(rationale-SFT)는 Coq structural에 novel.

**heavy/스킵**(deadline): HTPS 2205.11491(critic), Let's-Verify 2305.20050(사람 라벨 PRM800K), DS-Prover-V2 full(671B teacher — 단 분해-distill 레시피만 차용), kSubS/AdaSubS/POETRY/SubgoalXL(엔지니어링 큼). value 모델 꼭 필요하면 Coq-native **QEDCartographer 2408.09237**(reward-free지만 state-value 학습, sparse 안정화 레시피).

### References (검증됨, arXiv id)
Proverbot9001 1907.07794 · Math-Shepherd 2312.08935 · Lean-STaR 2407.10040 · DeepSeek-Prover-V2 2504.21801 · DS-Prover-V1.5 2408.08152 · HER-for-provers 2112.10664 · Baldur 2303.04910 · CuDIP 2502.18532 · Step-DPO 2406.18629 · LeanListener/Local-Look-Ahead 2503.09730 · Rango 2412.14063 · QEDCartographer 2408.09237 · HTPS 2205.11491 · DSP 2210.12283 · Let's-Verify 2305.20050 · Graph2Tac 2401.02949 · Magnushammer 2303.04488 · Curriculum-EI 2202.01344 · kSubS 2108.11204 · AdaSubS 2206.00702 · SubgoalXL 2408.11172 · POETRY 2405.14414.
> ⚠ 두 조사가 **QEDCartographer(2408.09237)의 value-free 여부**에서 엇갈림(하나는 state-value 학습한다, 다른 하나는 reward·value 둘 다 없다) → 채택 전 논문 원문 확인 필요.

---

## 다른 서버로 이전 — 실험 재현/이어하기 (handoff)

### 환경 (필수)
- base: `deepseek-ai/deepseek-coder-1.3b-instruct` + LoRA(r=64). coq-lsp + CoqStoq(CompCert). **⚠ OCaml/opam 버전 절대 변경 금지**(환경 깨짐).
- π₀ 기준선 모델: `models/rango-grpo/adapter` (=SFT→GRPO, rand200 w2 **37.5%** = 비교 기준). 결과 비교는 **우리 rango끼리만**(published 비교 금지).

### 핵심 파일
| 용도 | 파일 |
|---|---|
| DPO 데이터 생성(divergence) | `scripts/build_divergence_dpo.py` |
| DPO 학습 | `src/tactic_gen/dpo_train.py` (`{state,chosen,rejected}` 소비, ref=init 자동앵커) |
| GRPO 학습(+`--ref_adapter` KL→π₀) | `src/tactic_gen/grpo_train.py` |
| BFS 탐색(트리 덤프) | `src/model_deployment/bfs_prover_searcher.py` |
| 별칭 등록 | `scripts/run_thm.py` (`rango-grpo-div*`, `eisafe-r*`) |
| run 스크립트 | `all_log/run_divdpo.sh` · `run_ei_safe.sh` |

### 데이터
- `data/grpo_rollouts/ei-safe-r1.jsonl` (π₀ 롤아웃, G8, dead/solved 분석·divergence 추출 소스)
- `data/grpo_rollouts/goldsft_bs2.jsonl` (gold 증명 + retrieval)
- `data/grpo_rollouts/divergence_dpo.jsonl` (**생성된 DPO 쌍 508**: chosen=gold분해 / rejected=정책 이탈)
- idx: `data/compcert_bs2_{train(300),rand200(200),val(60)}_idx.txt` (train∩rand200∩val = 서로 disjoint 검증됨)

### 실험 큐 (우선순위)
1. **divergence-DPO (구현 완료)**: `bash all_log/run_divdpo.sh` → rand200 w2 vs 37.5%. (GPU 지정만 조정)
2. **★ value-free structural search (미구현, 최우선 next)** — 요약 스펙(**전체 설계·의사코드·하이퍼파라미터·compute관리·구현계획·ablation은 [[VALUE_FREE_SEARCH]] 참조**):
   - `bfs_prover_searcher` expansion에서 **분해 결정 노드**(현 goal에 case 가능한 hyp/inductive var 존재) 감지 시:
     - **후보 열거**: 각 가설 `destruct H_i` + 각 변수 `induction x_j` (+ 정책 top-k tactic) → 후보 tactic set.
     - **MC-rollout voting(value-free)**: 각 후보에서 짧은 rollout K개 → **성공/진전률로 랭킹**(Math-Shepherd 신호를 network 없이). 
     - **backtrack**: stuck(유효 tactic 없음/진전 없음) 감지 시 상위 노드로 되돌아가 다른 후보.
   - 목적: coverage 22%(정답 분해 안 생성) → **열거로 강제 주입**, stuck 74% → **backtrack**. critic 불요.
   - 평가: rand200 **w2 600s**(공정성).
3. rationale-SFT(Lean-STaR): structural tactic 앞 한 줄 rationale SFT. HER: 실패 롤아웃 재라벨. Baldur: stuck+Coq에러 재시도.

### GPU 주의
- **우리 서버는 GPU1 전용 제약**(GPU0에 host-namespace orphan). 새 서버에선 **GPU 지정 자유** — run 스크립트의 `CUDA_VISIBLE_DEVICES`(학습)·`--gpus`(run_all)만 조정.
- **평가(rand200)는 반드시 w2**(2 workers/GPU) — baseline들이 w2로 측정됨(밀도 다르면 오염, g2w4=477s p90로 성공률 하락한 전례 有).

### 현재 진행 중(이 서버)
- divergence-DPO: safe-EI eval 끝나면 자동 학습(GPU1) → rand200. 결과 나오면 여기 표에 기록.
- (unsafe) EI R3 rand200 재개는 보류(부분결과 `all_results/rand200_ei_r3_w2` 46/200 보존).
