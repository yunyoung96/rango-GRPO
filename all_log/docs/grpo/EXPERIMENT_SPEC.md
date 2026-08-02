# 학습 실험 상세 스펙 (rango SFT / GRPO / opener)

작성 2026-07-31. 대상: DeepSeek-Coder-1.3B + LoRA + BM25/TF-IDF retrieval, CompCert(Coq/coq-lsp) next-tactic.

---

## 1. 구현된 코드 위치
| 역할 | 파일 |
|---|---|
| **Base SFT** (rango) 학습 config | `models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml` (Rango tactic_gen 학습) |
| **GRPO 학습** (RL fine-tune) | `src/tactic_gen/grpo_train.py` |
| **GRPO 롤아웃** (학습데이터 생성) | `src/tactic_gen/grpo_rollout.py` (`rollout_attempt`, `collect_group`) |
| **Opener SFT** | `scripts/train_opener_sft.py` · 데이터 `scripts/build_opener_data.py`, `build_opener_sub_data.py` |
| **test 탐색기** (배포) | `src/model_deployment/bfs_prover_searcher.py` (best-first search) |
| Opener 서빙 | `src/model_deployment/planner_client.py`, `planner_server.py` |
| 실행 러너 | `scripts/run_all.py` (배치), `scripts/run_thm.py` (정리별 + alias) |
| 파이프라인 | `all_log/full_pipeline.sh`(opener-every), `pipe_once.sh`(opener-once), `combo_rollout.sh`(subgoal+opener) |

---

## 2. 데이터셋 / train-test split
- **데이터**: CompCert (CoqStoq). 입력=(proof state + 검색된 유사증명 20 + 검색된 premise 50), 출력=다음 tactic.
- **Base SFT 학습셋**: CompCert train split 전체 (`data/bm25-proof-tfidf-proj-thm-prem-final-clean`, 정리 수천 개의 (state→tactic) step). splits: `final-split.json`, `random-split.json`.
- **GRPO 실험 train**: `data/compcert_bs2_train_idx.txt` = **300 CompCert 정리**. (이번 세션 롤아웃은 시간상 그중 **head-100**만 사용.)
- **평가(eval) set**:
  - `compcert_bs2_test_idx.txt` = **1191** (전체 CompCert test)
  - `compcert_bs2_rand200_idx.txt` = **200** (무작위 부분집합) ← 이번 세션 평가는 이걸로
- **split 방식**: CompCert test 정리 리스트에 대한 idx. GRPO train_idx(300)와 eval(rand200/1191)은 분리. (단 Base SFT는 CompCert train 전체를 봤고 eval도 CompCert라 **same-project 전이 confound** 있음 — 코드 주석에 명시.)
- **규모 요약**: 학습 300(실사용 100), 평가 200(rand) / 1191(full). **1200/300이 아니라 train 300 / eval rand200**.

---

## 3. 알고리즘별 학습 파이프라인

### 3.1 Base SFT (rango) — supervised
- **알고리즘**: 표준 causal-LM MLE. (state+script+retrieval 프롬프트) → 다음 tactic 토큰 예측. LoRA fine-tune.
- 이건 이번 세션 이전에 학습된 것(재활용). executor의 출발점.

### 3.2 GRPO — on-policy RL (`grpo_train.py`)
- **알고리즘**: Group Relative Policy Optimization (critic-free).
  - 정리당 G개 궤도 롤아웃 → outcome reward(Qed=1, 아니면 0).
  - **그룹 상대 advantage** Âᵢ = (rᵢ − mean)/std (같은 정리 시도끼리). all-solved·dead는 std/편차 0 → advantage 0 → gradient 0.
  - **surrogate**: PPO-clip `min(ρÂ, clip(ρ,1±ε)Â)`, ρ=π_new/π_old. `clip_eps=0.2`.
  - **KL 정규화**: π_ref(RL 시작 스냅샷)에 KL, `kl_beta=0.04` (Schulman k3 추정 `exp(Δ)−Δ−1`).
  - γ=1, RLOO/std-normalize baseline. (코드에 process/luffy/vine/DAPO 변형도 있으나 본 실험은 표준 GRPO.)
- **롤아웃 설정** (grpo-rollout-pf): group_size **G=8**, max_steps **20**, max_retries **1**(ROLLOUT_RETRY), 단일궤도 forward(backtrack 없음).

### 3.3 Opener SFT (`train_opener_sft.py`) — supervised
- **알고리즘**: causal-LM MLE, 프롬프트 마스킹(labels=−100), goal → opening tactic(JSON). Qwen2.5-Coder-7B + LoRA.

---

## 4. 학습 하이퍼파라미터 상세

| | **Base SFT (rango)** | **GRPO** | **Opener SFT** |
|---|---|---|---|
| 종류 | supervised MLE | on-policy RL(GRPO) | supervised MLE |
| 모델 | deepseek-coder-1.3b-instruct | 동(base)+SFT adapter init | Qwen2.5-Coder-7B-Instruct |
| **epoch** | **2** | **2** (기본1) | **4** |
| **learning rate** | **1e-3** | **1e-6** | **1e-4** |
| max_steps | 60000 | (데이터×2ep) | (276예시×4ep) |
| batch | per_device 4 | micro_bsz **2** (기본4) | 1 (예시 순차) |
| max_len | hard_seq_len 4096 | **3072** | **2048**(sub)/1024 |
| **LoRA r / α / dropout** | **64 / 16 / 0.1** | (SFT adapter 위 학습) | **16 / 32 / 0.05** |
| LoRA target | q,k,v,o,gate,up,down_proj | 동 | all-linear |
| clip_eps | — | 0.2 | — |
| kl_beta | — | 0.04 | — |
| 입력 토큰 배분 | state1024·script512·proof1024·premise512·out128 | (롤아웃 궤적) | goal + JSON opening |
| grad clip | — | 1.0 | 1.0 |

- **GRPO 실행 커맨드**(예): `python3 -m tactic_gen.grpo_train --rollouts <roll.jsonl> --model_name deepseek-...-1.3b-instruct --init_adapter <SFT>/adapter --collator_conf <conf> --max_len 3072 --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 --save_dir <out>/adapter`

---

## 5. 가중치 저장 방식 (fine-tuning = LoRA)
- **전부 LoRA adapter만 저장.** 풀 모델 X.
- 저장 파일: `<model>/adapter/adapter_model.safetensors` (LoRA 가중치) + `adapter_config.json` (r/α/target/base).
- 추론 시: base 모델(deepseek-1.3b 또는 Qwen-7B) 로드 후 `PeftModel.from_pretrained(base, adapter)`로 얹음.
- GRPO는 SFT adapter를 **init**으로 얹고 그 위에서 업데이트 → 새 adapter 저장 (`training_conf.yaml`·`lm-example-conf.yaml` 복사해 eval 로드 가능하게).

---

## 6. GRPO mixed 비율 (그룹 성공 분포)
그룹(=정리 1개의 G=8 궤도)을 성공 수로 분류: **all-solved**(8/8, advantage=0), **mixed**(1~7/8, ★유일 학습신호), **dead**(0/8, advantage=0).

| 롤아웃 (train 100) | all-solved | **mixed(신호)** | dead | attempt성공 |
|---|---|---|---|---|
| plain SFT (baseline) | 7% | **27%** | 66% | 18.9% |
| opener-every (매분기) | 10% | **10%** | 80% | 12.6% |
| opener-once (처음1번) | 5% | **30%** | 65% | 17.4% |
| combo (subgoal모델+opener) | 5% | **27%** | 68% | 17.0% |

- mixed만 gradient. opener-every는 과분해로 mixed 붕괴(10%). opener-once/combo는 회복했으나 plain과 **parity(27~30%)** — baseline 초과 X.

---

## 7. dead group 유형 (combo, dead attempt 512개 분류)
| 유형 | 비율 | 설명 |
|---|---|---|
| **lemma 오적용** | **30%** | 닫기서 `apply/rewrite/unfold`에 안 맞는 lemma 골라 INVALID (예 `apply f_equal`, `rewrite PTree.gsspec`) |
| **opening 실패** | 27% | 첫 분해 step서 INVALID (compound destruct 인자 틀림 등) |
| 기타 | 24% | intros/기타 tactic INVALID |
| **과분해** | 15% | 닫는 대신 또 destruct/induction |
| automation 실패 | 3% | auto/lia가 이 goal엔 안 먹음 |
| timeout(예산소진) | 0% | INVALID 없이 max_steps 도달(드묾) |

→ 닫기 관련(lemma오적용+과분해+automation) ≈ 48%, 열기 27%. **핵심 = lemma 오적용(도메인 지식 부족)**.

---

## 8. rand200 성능 (이번 세션)
| 모델 / 조건 | rand200 | 상태 |
|---|---|---|
| `rango-opener-sub-grpo` (opener-**every** 학습) + test때 opener | **29.6%** (32/108) | **부분(108/200)**, 중단 |
| 동, opener 없이 | 30% (6/20) | 부분(20/200), 표본 작아 신뢰 낮음 |
| `rango-opener-once-grpo` (mixed 30% 모델) | — | **미학습(GRPO 미완)** |
| gold-SFT baseline / once_final | — | **미실행** |
| **(참고) 기존 known** SFT / π₀(SFT→GRPO) | **33.5% / 37.5%** | 이전 세션(rand200) |

**정직한 상태**: 이번 세션 opener 계열은 rand200을 **깨끗이 완주 못 함**(파이프 중단). 유일 부분값 29.6%(opener-every+opener at test)는 **baseline(33.5%) 미달**. mixed 회복(30%)된 opener-once 모델은 **학습·평가 미완**이라 rand200 숫자 없음.

---

## 핵심 결론
- 모든 개입(opener/subgoal/조합)의 **롤아웃 성공률 ~32-34% = plain과 parity**. rand200(search)도 baseline(~33-37%) 초과 근거 없음.
- 벽 = **닫기(lemma 오적용, 도메인 증명경로 = 1.3B capacity)**, 열기 아님.
- 상세: `opener/OPENER_RANGO_ANALYSIS.md`, `opener/README.md`.
