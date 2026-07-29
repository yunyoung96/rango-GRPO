# GRPO / RL-for-Coq 문서 인덱스

Coq 증명 자동생성(Rango: DeepSeek-Coder-1.3B + LoRA + BM25/TF-IDF retrieval)에 대한 GRPO/RL 실험·분석·아이디어 모음. 갱신 2026-07-27.

## 🎯 핵심 결과 & 진단 (먼저 읽을 것)
- **[MIXED_GROUP_SUMMARY.md](MIXED_GROUP_SUMMARY.md)** — 전 28실험 mixed% 완전체 + **핵심 역설: mixed%(신호량)와 held-out 무상관** (gold 86%인데 회귀, SFT→GRPO 25%인데 최고).
- **[SUBGOAL_PAPER_ASSESSMENT.md](SUBGOAL_PAPER_ASSESSMENT.md)** — subgoal 방법 종합 평가. **§10 도달성 진단**(gold subgoal 16.7%만 도달, 레벨 0% 중첩 → cascade 실패 정량 근본원인), §9 로그메트릭·GRPO개선.
- **[GOLD_PROOF_METHODS.md](GOLD_PROOF_METHODS.md)** — gold 주입 6종(LUFFY·KL-LUFFY·backward·revcurr·DAPG·RFT-gold) **전멸 + covariate-shift 분석**. "왜 gold가 구조적으로 안 되나".

## 💡 아이디어 & 계획
- **[IDEAS.md](IDEAS.md)** — SFT→GRPO(37.5%) 이후 후보 우선순위표(11+EI) + **§4 dead-group 3분류**(부분진행/탐색가능/하드코어) + 부록 A~K(각 아이디어 상세). PPO=파일럿 critic 실패로 접음.
- **[DECOMPOSITION_IDEAS.md](DECOMPOSITION_IDEAS.md)** — **invertible-rule 분해로 도달성 보존 커리큘럼** + CompCert 실측 전술분포 + **LLM에 "쪼개는 법" 가르치기(process-GRPO)**. IDEAS⑩ 구체화.
- **[INTERLEAVED_SFT_RL.md](INTERLEAVED_SFT_RL.md)** — SFT↔GRPO 교대 문헌(ReLIFT/BRIDGE/Goedel/STP) + Coq 공백 + **우리 실측 비판**(그들 gold-SFT 데이터원은 §10 함정 → reachable로 교체) + 종합 파이프라인.
- **[MODEL_CANDIDATES.md](MODEL_CANDIDATES.md)** — 더 큰/teacher 모델 + 로컬(2×48GB) 실행성. DeepSeek(-Prover는 Lean) vs **Qwen 비교**(§7·§8), naive base 비교.

## 📊 실험 상세 (원판 기록)
- **[GRPO_ROLLOUT_ANALYSIS.md](GRPO_ROLLOUT_ANALYSIS.md)** — 롤아웃 분석(dead 73%, 길이편향, MDP 층위).
- **[GRPO_RESULT.md](GRPO_RESULT.md)** — GRPO 결과.
- **[LEAF_SUBGOAL_METHOD.md](LEAF_SUBGOAL_METHOD.md)** — leaf subgoal 방법.
- **[HARVEST_ROUND.md](HARVEST_ROUND.md)** — 실패 롤아웃서 닫힌 subgoal harvest(RFT).
- **[BFS_PROVER_IMPL.md](BFS_PROVER_IMPL.md)** — BFS-Prover(2502.03438) 우리 구현 정리(탐색 충실 재현+ablation, DPO/validity-DPO, 실측·충실도).
- **[EI_PROGRESS.md](EI_PROGRESS.md)** — Expert Iteration 진행·mixed 변화율·R3 분해.
- **[EI_OVERFIT_MITIGATIONS.md](EI_OVERFIT_MITIGATIONS.md)** — EI overfitting 완화책 정확 구현(early-stop/KL→π₀/entropy·clip-higher/lr↓) + 문헌.
- **[BOTTLENECK_ANALYSIS.md](BOTTLENECK_ANALYSIS.md)** — ★병목 실측 진단(retrieval OK·built-in OK·**초반 분해 divergence 61%·coverage 22%**) + 문헌기반 알고리즘 제안 + 다른서버 handoff.
- **[VALUE_FREE_SEARCH.md](VALUE_FREE_SEARCH.md)** — ★#1 레버 완전 설계+구현가이드(분해 강제열거+MC value-free scoring+backtrack, critic 불요).
- **[SUBGOAL_EXPERIMENT_PLAN.md](SUBGOAL_EXPERIMENT_PLAN.md)** — subgoal 실험 계획.
- **[PASSK_ANALYSIS.md](PASSK_ANALYSIS.md)** — pass@k 분석.

## 📚 리서치 / 문헌
- **[SUBGOAL_RL_RESEARCH_ALL.md](SUBGOAL_RL_RESEARCH_ALL.md)** — subgoal 재활용 RL 리서치 종합.
- **[RESEARCH_GOLD_CURRICULUM.md](RESEARCH_GOLD_CURRICULUM.md)** — gold 커리큘럼 리서치.

---

## 한 줄 스토리 (2026-07-27 현재)
**SFT→GRPO 37.5%가 최고. subgoal(leaf/cascade)·harvest·gold 6종·PPO 다 못 넘음.** 근본원인 = **도달성**(§10: "닫기"는 배우나 "도달"을 못 배움) + **희소보상**(dead 62%) + **테스트 compute-bound**. 진행중 = cascade-s0r2(harvest) 공정 w2 재측정(≈37% 수렴, SFT→GRPO 못 넘음 예상). 다음 유망 = **invertible-분해로 도달성 보존 커리큘럼 + variance-스케줄 interleaved SFT-GRPO + lemma flywheel**.
