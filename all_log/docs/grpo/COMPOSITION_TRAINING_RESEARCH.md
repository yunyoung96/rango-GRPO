# 조립(composition)을 decoder에서 학습 — 아이디어 + 논문조사 (2026-08-03)

질문: "materials(가설+premise)는 있는데 조립(apply THIS lemma to THESE hyps)을 못 함(oracle +2pp). decoder 단계에서 조립을 잘하게 학습하는 방법 + 논문."

## ★★ 메타-발견 (조사 결론)
**소형 텍스트 decoder를 "이 lemma를 이 가설에 apply"라는 전용 dense objective로 학습시킨 논문은 없다.** 조각들(verifier step-reward·검색측 hard-negative·인자바인딩 분해·thought-before-tactic)은 따로 존재하나, **조립특화 decoder objective = 미개척 니치(novelty 있음).**

## 내 4 아이디어 × 학계 대응 × 판정
| 아이디어 | 학계 대응 | 판정 |
|---|---|---|
| **2. 조립 dense reward**(step-level, coq-lsp가 productive 판정) | **arXiv:2606.20068**(Process-Verified RL via Lean checker) + arXiv:2605.11905(segment-level credit) | ⭐**1순위 실행가능** |
| **1. sub-step 분해**(select→bind→emit / rationale) | **Lean-STaR arXiv:2407.10040**(thought-before-tactic) + 고전 TacticZero(select→args) | ⭐**2순위 값쌈** |
| **3. 하드-네거티브 조립**(decoder측 대조) | arXiv:2506.07477(검색측 InfoNCE, hard-neg) + arXiv:2402.14328(CREME) | ⭐**가장 novel**(decoder측 아무도 안함) |
| **4. 재료정렬 입력**(구조주입) | Graph2Tac 2401.02949 / Passport 2204.10370 | =지금 [TYPES] 방향 |

## 결정적 논문 3
1. **arXiv:2606.20068** (Process-Verified RL, 2026) — **가장 on-point.** Lean elaborator를 process 오라클로: 생성 증명을 step 파싱→locally-sound step·최초 실패 step 표시→first-error-propagation+first-token credit→GRPO. **verifier-grounded 공짜 라벨(human PRM/MC rollout 불필요).** Coq `coqc`/serapi가 같은 신호(어느 tactic 첫 실패/어느 subgoal 닫힘) 제공. critic-free=1.3B single-GPU 적합. (단 Lean·whole-proof라 per-step Coq에 credit-assignment 포팅 필요.)
2. **arXiv:2402.14328** (CREME, ACL2024) — **"조립 실패는 국소화된 학습가능 회로"**(중간층 MHA에 causal intervention으로 국소화·패치). → **"gold 줘도 +2pp=정보 아님" 내 결론을 기계적 뒷받침.** 타겟 학습/조립층 LoRA로 조립 이동 가능 시사.
3. **arXiv:2502.18532** (CuDIP, DPO for ATP) — **내 plain-DPO unique-solve 0 원인 설명**: 평범 DPO는 하드네거티브·커리큘럼 없어 gradient 무의미. 재시도 시 **타입호환 오답 hard-neg + 커리큘럼(easy→hard) + on-policy 쌍** 필수. (그래도 process-reward GRPO가 더 나은 베팅.)

## 각도별 핵심 (조사 요약)
- **Angle1 step-reward**: 2606.20068·2605.11905(segment)·Math-Shepherd 2312.08935(rollout consensus, 우린 verifier로 대체 가능=더나음)·LeanProgress 2502.17925(progress value)·PRM800K 2305.20050(human, 불필요).
- **Angle2 contrastive**: LeanHammer 2506.07477(**검색측** InfoNCE hard-neg, +21%)·CuDIP·MASS-DPO 2605.10784(multi-neg). **decoder측 조립 대조는 없음=novel.**
- **Angle3 compose retrieved**: Rango 2412.14063(**조립을 search에 위임, generator는 조립 objective 학습 안함=우리 갭**)·RocqStar 2505.22846(agent retrieval)·LEGO-Prover 2310.00656(**2504.03048이 library-learning 환상이라 반증**)·ReProver 2306.15626(우리가 안하는 것).
- **Angle4 structure**: Graph2Tac 2401.02949(GNN, [TYPES]의 GNN원형)·Passport 2204.10370(identifier구조 도움, RNN기).
- **Angle5 sub-task**: Lean-STaR 2407.10040(⭐ rationale→tactic)·DeepSeek-Prover-V2 2504.21801(subgoal, 7B/큰granularity)·고전 select→bind(pre-LLM, 부활 안됨=갭).
- **Angle6 현상**: Compositionality Gap 2210.03350(현상 명명, scale로 안줄음)·CREME 2402.14328·Local-Success-Not-Compose 2509.23061(**formal verification서 우리현상**)·STaD 2604.18177(scaffold 커리큘럼=training fix 제안).

## 추천 실행 순서 (1.3B Coq)
1. **조립 dense reward** (2606.20068): coq-lsp를 per-step "productive?" 오라클로 → GRPO segment-level advantage. "valid but not productive" 정면공략. critic-free. **이미 있는 인프라**(`--process`)를 조립-credit(선택맞음 vs 인자만틀림 분리)으로 강화.
2. **Lean-STaR rationale** (2407.10040): gold step에 "왜 lemma L을 가설 h에" 근거 합성 → rationale→tactic SFT → 경량 expert-iter. **가장 값쌈.**
3. **decoder 하드-네거티브** (novel): 타입호환 오답 lemma를 coq-lsp 검증된 hard-neg로 대조. 단 커리큘럼+hard-neg 필수(2502.18532).

## 정직한 회의 (이미 밝혀진 벽)
- 조립 개선이 **test 성능 전이**는 별개(DPO unique-0, process도 outcome 못넘음, EI≤37%). **벽이 조립 위 도달성(§10)**일 수 있음.
- 단 CREME(2402.14328)이 "조립은 학습가능 국소회로"라 하고, 우리 아직 **조립특화 dense objective를 안 해봄** → 시도가치.
- **novelty는 확실**: 조립특화 decoder objective 논문 없음.

## rango-augmented와의 연결
- [TYPES]/[DEFINITIONS] = 재료 완전성(수평) = Graph2Tac decoder판.
- **조립 학습(수직) = 위 3방법** = [[rango_augmented/COMPOSITION_IS_THE_WALL]]의 실행형.
- 둘 다 필요: 완전한 재료 + 조립 objective.

관련: [[rango_augmented/COMPOSITION_IS_THE_WALL]] · [[SUBGOAL_PAPER_ASSESSMENT]] §10 · [[IDEAS]] · [[rango_augmented/STRUCTURAL_INFO_MAP]] · [[LITERATURE]]
