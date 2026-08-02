# architecture.md — 개발한 알고리즘 전체 목록 (rango RL for Coq)

작성 2026-07-31. DeepSeek-Coder-1.3B + LoRA + BM25/TF-IDF retrieval, CompCert(coq-lsp) next-tactic.
각 알고리즘: rango alias + 별칭 / 코드위치 / 학습종류 / mixed(GRPO) / rand200 / 판정.

---

## 실험 로그·결과 디렉토리 (링크)
루트: `/app/coq-modeling/`
| 종류 | 위치 |
|---|---|
| **실험 로그(학습/평가 stdout)** | [`all_log/`](../../all_log/) — 알고리즘별 `*.log` (§1 표의 로그열) |
| **평가 결과(성능 summary.json)** | [`all_results/`](../../all_results/) — `rand200_*`, `smart_*`, `bs2_*test120*` |
| **롤아웃 데이터(GRPO 학습입력)** | [`data/grpo_rollouts/`](../../data/grpo_rollouts/) — `*.jsonl` (그룹·attempt·step) |
| **커리큘럼(subgoal/backward/revcurr)** | [`data/curriculum/`](../../data/curriculum/) — `*.json` |
| **학습된 어댑터(LoRA)** | [`models/`](../../models/) — `<alias>/adapter/` |
| **문서** | [`all_log/docs/grpo/`](grpo/) · [`all_log/docs/grpo/opener/`](grpo/opener/) |

각 결과 성능은 `all_results/<dir>/summary.json`(success/done/total), 로그는 `all_log/<name>.log`.
아래 §1 표의 "로그"·"결과" 열이 각 알고리즘의 정확한 파일을 가리킴.

---

## 0. 공통 스펙 (모든 GRPO 변형 공유 — 자세히는 `grpo/EXPERIMENT_SPEC.md`)
- **데이터/split**: CompCert. **train_idx=300** 정리(롤아웃), **eval=rand200(200)** 또는 test 1191. (1200/300 아님. Base SFT는 CompCert train 전체.)
- **Base SFT** (executor 출발점): supervised MLE, **epoch 2, lr 1e-3**, LoRA **r64/α16/drop0.1**, max_steps 60000, batch4. 입력=(state1024+script512+검색proof1024+premise512)→tactic. 코드: rango `tactic_gen` 학습, config `models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml`.
- **GRPO** (RL): critic-free, 그룹상대 advantage (rᵢ−mean)/std + PPO-clip(ε=0.2) + KL(β=0.04, k3). **epoch 2, lr 1e-6, micro_bsz 2, max_len 3072**. init=SFT adapter. 롤아웃 G=8, max_steps20, retries1, 단일궤도(backtrack 없음). 코드: `src/tactic_gen/grpo_train.py`(학습) + `grpo_rollout.py`(데이터생성).
- **가중치 저장**: 전부 **LoRA adapter** (`<model>/adapter/adapter_model.safetensors` + `adapter_config.json`). 풀모델 X. 추론=base+PeftModel.
- **mixed 정의**: 그룹(정리1개 G=8궤도) 중 mixed(1~7성공)만 gradient. all-solved·dead는 advantage=0.
- **test 탐색**: `bfs_prover_searcher.py` = length-normalized **best-first search**(backtrack O). rand200@600s w2 기준.

---

## 1. 핵심 요약표
로그=`all_log/<name>.log`, 결과=`all_results/<dir>/summary.json`, 롤아웃=`data/grpo_rollouts/<name>.jsonl`.

| # | alias | 별칭 | 종류 | mixed | rand200 | 판정 | 로그 | 결과 dir |
|---|---|---|---|---|---|---|---|---|
| 1 | `rango` | 원조 SFT (baseline) | SFT | — | 33.5% | baseline | [core](../../all_log/core.log) | [rand200_baseline_test600_w2](../../all_results/rand200_baseline_test600_w2/) (arch=`rango`) |
| 1b | `rango-grpo-bs2-sft` | gold-SFT (executor init) | SFT | — | (test1191 27.2%) | init용 | [bigscale2](../../all_log/bigscale2.log) | [bs2_sft_test120_w2](../../all_results/bs2_sft_test120_w2/) |
| 2a | `rango-grpo-bigscale2` | **그냥 GRPO** (base→GRPO, SFT 없음) | GRPO | — | (test1191 27.5%) | — | [bigscale2](../../all_log/bigscale2.log) | [bs2_grpo_test120_w2](../../all_results/bs2_grpo_test120_w2/) |
| 2b | `rango-grpo-bs2-sftgrpo` | **SFT→GRPO** (π₀, SFT 위 GRPO) | SFT→GRPO | 26% | **37.5%** | ★최고 | [bigscale2](../../all_log/bigscale2.log) | [rand200_sftgrpo_test600_w2](../../all_results/rand200_sftgrpo_test600_w2/) · [bs2_sftgrpo_test120_w2](../../all_results/bs2_sftgrpo_test120_w2/) |
| 2c | `rango-grpo` / `rango-grpo-fix` | 구 π₀ / base정합 정정판 | SFT→GRPO | — | (초기라인) | fix=올바름 | — | [smart_rango-grpo-fix](../../all_results/smart_rango-grpo-fix/) |
| 3 | `grpo-rollout-luffy`→`rango-grpo-luffy` | LUFFY | gold주입 GRPO | 86%* | 부분 | 실패(shift) | [luffy](../../all_log/luffy.log) | [smart_rango-grpo-luffy](../../all_results/smart_rango-grpo-luffy/) |
| 4 | `-luffy`+KL | KL-LUFFY | gold+KL | 35%(부분) | 부분 | 실패 | [luffy](../../all_log/luffy.log) | [smart_rango-grpo-luffy-kl](../../all_results/smart_rango-grpo-luffy-kl/) |
| 5 | `grpo-rollout-backward`→`rango-grpo-backward` | backward curriculum | gold중간상태 GRPO | 31% | 부분 | 실패(회귀) | [backward](../../all_log/backward.log) | [smart_rango-grpo-backward](../../all_results/smart_rango-grpo-backward/) |
| 6 | `grpo-rollout-revcurr`→`rango-grpo-revcurr` | reverse curriculum | gold전역행 GRPO | 30% | 37.5%(부분40) | 실패(회귀) | [revcurr](../../all_log/revcurr.log) | [smart_rango-grpo-revcurr](../../all_results/smart_rango-grpo-revcurr/) |
| 7 | (dapg) | DAPG | demo-augmented PG | — | 40%(부분40) | 실패 | [dapg](../../all_log/dapg.log) | [smart_rango-grpo-dapg](../../all_results/smart_rango-grpo-dapg/) |
| 8 | (rft-gold) | RFT-gold | gold SFT주입 | — | 부분 | 실패(shift) | — | [smart_rango-grpo-rft-gold](../../all_results/smart_rango-grpo-rft-gold/) |
| 9 | `grpo-rollout-subgoal`→`rango-grpo-subgoal` | leaf-first subgoal-GRPO | subgoal 커리큘럼 | s1 37% | **37.0%** | parity | [subgoal](../../all_log/subgoal.log) | [rand200_leafsubgoal_test600_w2](../../all_results/rand200_leafsubgoal_test600_w2/) · [smart_rango-grpo-subgoal](../../all_results/smart_rango-grpo-subgoal/) |
| 10 | `rango-grpo-cascade-*` | cascade subgoal | on-policy 정정 subgoal | s1 43% | 33.5~37.5% | parity | [cascade](../../all_log/cascade.log) | [rand200_cascade_s0r2_w2](../../all_results/rand200_cascade_s0r2_w2/) |
| 11 | `grpo-rollout-vine`→`rango-grpo-vine` | VinePPO | step MC advantage | 18% | 40%(부분40) | 실패 | [vine](../../all_log/vine.log) | [smart_rango-grpo-vine](../../all_results/smart_rango-grpo-vine/) |
| 12 | `rango-grpo-prm` | process reward(PRM) | per-tactic checker advantage | — | 40%(부분40) | 실패 | — | [smart_rango-grpo-prm](../../all_results/smart_rango-grpo-prm/) |
| 13 | `grpo-rollout-dense`/`-dapo` | dense/DAPO | shaped reward | — | — | 미결 | — | — |
| 14 | `smart_...-ppo-*` | PPO(critic) | PPO linear/mlp critic | — | 부분(작음) | 실패(explained_var≈0) | — | [smart_rango-grpo-ppo-mlp](../../all_results/smart_rango-grpo-ppo-mlp/) · [ppo-linear](../../all_results/smart_rango-grpo-ppo-linear/) |
| 15 | `bfs-dpo` / divergence | divergence-DPO | selection DPO | — | 33.6% | 실패(unique0) | [divdpo](../../all_log/divdpo.log) | [rand200_divdpo_w2](../../all_results/rand200_divdpo_w2/) |
| 16 | `rango-grpo-ei-r1..3` | EI / STaR | self-success SFT 반복 | 28~32% | 28.3%(r3) | 실패(dead 못살림) | — | [rand200_ei_r3_w2](../../all_results/rand200_ei_r3_w2/) |
| 17 | `eisafe-*` | 안전-EI | overfit-hardened EI | 32% | **35.0%** | 차선 | — | [rand200_eisafe_best_w2](../../all_results/rand200_eisafe_best_w2/) |
| 18 | `rmaxts`(-nomcts/merge/reward) | RMaxTS | MCTS 검색 | — | — | 탐색축(별도) | — | — |
| 19 | `bfs-prover`(-a0/a1/trace) | BFS-Prover | best-first 탐색 | — | — | 탐색기 | [bfs](../../all_log/bfs.log) | — |
| 20 | `pgts`(-sym/-pat) | PGTS | policy-guided tree search | — | — | 탐색축 | — | — |
| 21 | `quarry`(-heur/-trace) | Quarry | lemma 채굴 | — | — | 별도 | — | — |
| 22 | `rango-planner`(-6b) | 32B/7B planner(추론) | opener 추론 | — | 16.7%(부분6) | 실패 | [chain_planner_boot](../../all_log/chain_planner_boot.log) | [rand200_planner_w2](../../all_results/rand200_planner_w2/) |
| 23 | opener-**every** (`grpo-rollout-pf`+PLANNER_EVERY) | opener 매분기 | opener+GRPO | **10%** | 29.6%(부분108) | 실패(과분해) | [full_pipeline](../../all_log/full_pipeline.log) | [osg_final_opener](../../all_results/osg_final_opener/) |
| 24 | opener-**once** (`grpo-rollout-pf`+PLANNER_FIRST) | opener 처음1번 | opener+GRPO | **30%** | 미완 | parity | [pipe_once](../../all_log/pipe_once.log) | (미완) |
| 25 | combo (`grpo-rollout-pf`+subgoal executor) | subgoal+opener 조합 | 두 벽 동시 | **27%** | 미완 | parity | [combo_rollout](../../all_log/combo_rollout.log) | (롤아웃 [combo](../../data/grpo_rollouts/combo_subgoal_opener.jsonl)) |
| 26 | `no-retrieval`/`no-proof`/`no-lemma` | retrieval ablation | 검색 제거 | — | — | ablation | [ablation](../../all_log/ablation.log) | — |

*LUFFY mixed 86%는 gold 궤도(r=1)를 그룹에 주입해 인위적으로 높인 것(신호↑≠성능↑의 증거).
※ `smart_*` rand200은 **부분표본(done 5~40)**이라 %가 부풀 수 있음 — 신뢰값은 rand200@600s(done 200)만.
※ 로그 열의 일부 알고리즘은 여러 `chain_*.log`에 섞여 실행됨(정확한 실행은 `all_log/chain_*.log` grep). "—"=단독 로그 파일 특정 안 됨.

---

## 2. 신뢰 가능한 rand200 성능 (done=200 @600s w2)
| 방법 | rand200 | 코드결과 |
|---|---|---|
| baseline(SFT) | **33.5%** | rand200_baseline_test600_w2 (67/200) |
| **SFT→GRPO(π₀)** | **37.5%** | rand200_sftgrpo_test600_w2 (75/200) |
| leaf-subgoal | 37.0% | rand200_leafsubgoal_test600_w2 (74/200) |
| cascade s0r2 | 37.5% | rand200_cascade_s0r2_w2 (75/200) |
| safe-EI | 35.0% | rand200_eisafe_best_w2 (70/200) |
| divergence-DPO | 33.6% | rand200_divdpo_w2 (49/146) |
| cascade g2w4 | 33.5% | rand200_cascade_g2w4600s |
- **전체 ~33.5-37.5% 수렴. SFT→GRPO 37.5%가 최고.** 어떤 개입도 유의미 초과 없음.
- **full test 1191@120s (3라인 명확 구분)**: SFT만(`bs2-sft`) 27.2% / **그냥 GRPO**(`bigscale2`, base→GRPO) 27.5% / **SFT→GRPO**(`bs2-sftgrpo`) 28.4%.
  → 그냥 GRPO는 SFT 대비 +0.3%p뿐(거의 무의미), **SFT→GRPO만 +1.2%p**. **SFT 단계가 필수**.
- ※ rand200 성능 라인의 실제 모델: baseline=arch`rango`, SFT→GRPO=arch`rango-grpo-bs2-sftgrpo`. **`rango-grpo-fix` 아님**(fix는 초기 core 라인). 300train/1191test는 전부 **bs2 계열**.

---

## 3. 알고리즘별 상세

### A. Base 계열 — SFT / 그냥GRPO / SFT→GRPO는 **서로 다른 3라인** (구분 중요)
- **rango** (원조 SFT, baseline): §0 Base SFT. rand200 **33.5%**. arch=`rango`.
- **rango-grpo-bs2-sft** (gold-SFT): 300 train용 SFT. executor **init**으로 씀. test1191 27.2%.
- **rango-grpo-bigscale2** (**그냥 GRPO**): base rango 위에 **바로 GRPO**(SFT 단계 없음). test1191 27.5% = SFT와 거의 동일 → **SFT 없이 GRPO만은 효과 미미**.
- **rango-grpo-bs2-sftgrpo** (**SFT→GRPO = π₀**): SFT 위에 GRPO. mixed 26%, **rand200 37.5% / test1191 28.4%**. `grpo-rollout-pf` 등 이번 세션 executor의 π₀. → **최고, 모든 비교 기준.**
- **rango-grpo / rango-grpo-fix** (초기 core 라인): `rango-grpo`=구버전(GRPO를 base 위에서 학습했는데 config·배포는 instruct라 데이터생성/최적화/배포 3정책 불일치 버그). `rango-grpo-fix`=셋 다 instruct로 통일 재학습(**차이는 base 모델뿐, 알고리즘·데이터·하이퍼 동일**). **bs2 계열(300/1191)과는 별도 라인** — rand200/test1191 성능은 fix가 아니라 `bs2-sftgrpo`가 낸 것.
- **정리**: "SFT→GRPO"와 "그냥 GRPO"는 다른 알고리즘(전자만 +1.2%p). "fix"는 SFT→GRPO의 base정합 정정판이지 별개 알고리즘 아님.

### B. Gold-injection 계열 (전부 실패 — covariate shift)
- **LUFFY**(`grpo-rollout-luffy`→`rango-grpo-luffy`): dead group에 인간 gold 궤도 1개 주입(clip 없이 shaping f(π_θ)). mixed 86%(인위적). 학습 후 회귀. `luffy.jsonl`.
- **KL-LUFFY**: LUFFY + π_ref KL. 실패.
- **backward**(`-backward`): gold의 remaining=4 한 중간상태서 롤아웃+GRPO. mixed 31%. 회귀. `backward.jsonl`.
- **revcurr**(`-revcurr`): gold **모든 중간상태**(remaining 2~8)서 롤아웃. mixed 30%. 회귀. `revcurr.json` 커리큘럼.
- **DAPG**: demonstration-augmented PG. 실패.
- **RFT-gold**: gold를 SFT로 주입. shift. `rft-gold`.
- 공통 실패 원인: **d^gold ≠ d^π** (도달 16.7%), dead group 86% 부활시켜도 test 0상승 = 신호↑≠성능↑.

### C. Subgoal 계열 (parity)
- **leaf-first subgoal-GRPO**(`grpo-rollout-subgoal`→`rango-grpo-subgoal`): gold 트리를 goal-수로 복원, subgoal 경계서 seed, **per-subgoal 보상**(goal수 하락=닫힘=reward1, Qed불필요), leaf(size≤2)→위로 스테이지 s1→s2→s3. env `SUBGOAL_CURRICULUM/REWARD/SKIP_S0`. G=6, max_steps16, retries2. mixed s1 37%/s2 48%/s3 30%. rand200 **37.0%**. 데이터 `rango-grpo-subgoal-bs2-s0/s1/s2.jsonl`. 코드 `build_leaf_subgoal_curriculum.py`. 문서 `grpo/opener/`엔 없음→ `LEAF_SUBGOAL_METHOD.md`.
- **cascade**(`rango-grpo-cascade-*`): 위와 같으나 롤아웃 정책을 각 스테이지 init에 맞춤(on-policy 정정), w4/G8. mixed s1 43%. rand200 33.5~37.5%.

### D. Value / process
- **VinePPO**(`grpo-rollout-vine`→`rango-grpo-vine`): 각 step서 K회 MC 롤아웃→value, step-level advantage V(s')−V(s). mixed 18%. `vine.jsonl`.
- **PRM/process**(`rango-grpo-prm`): coq-lsp per-tactic 결과를 process reward로(2606.20068). rand200 부분 40%.
- **value-free MC search**: net 없이 MC value로 랭킹 → 32.5→17% 붕괴(1.3B가 QED 못 내 신호0).

### E. Search (탐색축 — 별도)
- **RMaxTS**(`rmaxts`, `-nomcts/-nomerge/-noreward`): MCTS 탐색. ablation 포함.
- **BFS-Prover**(`bfs-prover`, `-a0/-a1/-trace`): best-first, value-free MC 채점.
- **PGTS**(`pgts`, `-sym/-pat`): policy-guided tree search.
- **Quarry**(`quarry`, `-heur/-trace`): 실패 롤아웃서 lemma 채굴.

### F. PPO / DPO
- **PPO**(`smart_...-ppo-linear/mlp/mlp2`): critic(linear/MLP) 학습 PPO. **critic explained_var≈0**(희소보상)로 실패 → GRPO가 critic-free인 이유 실증. 부분표본.
- **divergence-DPO**(`bfs-dpo`): 정책이 gold를 gold 아닌 것보다 선호하게 selection DPO. rand200 33.6%, margin↑(acc0.54→0.65)지만 **unique solve 0**(생성확률·solve 불변).

### G. Expert Iteration
- **EI/STaR**(`rango-grpo-ei-r1..r3`): s0 롤아웃 → **성공 완전체만 SFT** → 재롤아웃 반복. mixed 28~32%. rand200 r3 28.3%(부분46). dead group(신호0) 못 살림.
- **safe-EI**(`eisafe-*`): overfit-hardened EI(early-stop/정규화). rand200 **35.0%**. 차선.

### H. Planner / Opener (이번 세션 주력 — 상세는 `grpo/opener/`)
- **rango-planner**(-6b): 범용 32B/7B planner를 **추론만**(학습X)으로 opener 후보 제공. target일치 14%. rand200 16.7%(부분6). 실패.
- **opener-7b/-sub** SFT(`train_opener_sft.py`): Qwen-7B를 gold opening 학습. **epoch4, lr1e-4, LoRA r16/α32**, max_len2048. opener-sub=정리147+subgoal130 opening. gold일치 52%(train).
- **opener-every**(`grpo-rollout-pf`+`PLANNER_EVERY=1`): 매 분기 opener. mixed **10%**(과분해). GRPO 완료(`rango-opener-sub-grpo`). rand200 29.6%(부분108, baseline미달).
- **opener-once**(`grpo-rollout-pf`+`PLANNER_FIRST_URL`+hedge): 처음 1번만 opener. mixed **30%**(회복). GRPO 미완, rand200 미실행.
- **combo**(위 + executor=subgoal모델): mixed **27%**. GRPO/test 미실행.
- 판정: opener 90% VALID로 잘 열지만 **닫기가 벽** → parity. 상세 `grpo/opener/OPENER_RANGO_ANALYSIS.md`.

### I. Retrieval ablation
- `no-retrieval`/`no-proof`/`no-lemma`(+`-inter-file`): retrieval 요소 제거. gold lemma recall 88.5%(top50) → retrieval은 병목 아님 확인용.

---

## 4. dead group 유형 (combo, dead attempt 512개)
| 유형 | 비율 |
|---|---|
| lemma 오적용 (닫기) | 30% |
| opening 실패 | 27% |
| 기타 | 24% |
| 과분해 | 15% |
| automation 실패 | 3% |
| timeout | 0% |
→ 닫기 관련 ≈48%, 열기 27%. 핵심=**lemma 오적용(도메인 지식 부족=capacity)**.

---

## 5. 종합 판정
- **모든 알고리즘 rand200 ~33.5-37.5% 수렴. SFT→GRPO 37.5%가 천장.** gold주입(전부 실패), subgoal/opener/조합(parity), PPO(critic실패), DPO(unique0), value-free(붕괴).
- 병목 = retrieval(88.5%)·선택(열기)이 아니라 **닫기(도메인 lemma 적용 = 1.3B capacity)**.
- 남은 레버 = **더 큰 executor(7B)**.

관련 문서: `grpo/EXPERIMENT_SPEC.md`(train 상세) · `grpo/PAPER_FINDINGS.md` · `grpo/GOLD_PROOF_METHODS.md` · `grpo/LEAF_SUBGOAL_METHOD.md` · `grpo/opener/`
