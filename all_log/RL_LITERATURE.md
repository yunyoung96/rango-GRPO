# RL 조사 요약 (QEDCartographer 포함) — 2026-07-05

> 사용자 요청으로 RL 범위 추가. hammer는 계속 미사용.

## 결론
- **QEDCartographer 직접 실행 ✗**: Proverbot9001 브랜치(`UCSD-PL/proverbot9001` @ `qedcartographer`). Coq **8.10.2** + opam/OCaml + `coq2vec`(LSTM 상태 임베딩) + polyarg 예측기 + MPI 분산학습. Rango(DeepSeek/LoRA)와 통합 불가 — 재작성 수준.
- **권장: QEDCartographer-영감 value-guided best-first를 ClassicalSearcher에 이식.** 이득의 실제 원천(value 순서화 + product backup)만 ~1% 비용으로.

## QEDCartographer 핵심 (arXiv:2408.09237, ICSE2025)
- **reward-free** = 중간 보상 설계 없음. sparse "증명완료"를 **분기(AND) 구조 Bellman**에 직접 반영: `V'(s)=maxₐ γ·∏_{s'∈f(s,a)} V(s')`. subgoal 곱 → 모든 obligation이 닫혀야 좋은 tactic. γ가 짧은 증명 선호(26~34% 짧아짐).
- **value V(s)=γ^(남은 step수)** 학습(critic만, policy는 supervised 유지). best-first: 우선순위=V. A*: f=depth+log_γ V.
- 입력: 상태(hyps+goal) → coq2vec 임베딩 → MLP value head.

## 이식 가능한 코어 (우리 로그로 저비용)
- **GPT-f**(2009.03393): provability head — 성공경로 상태=1, 그 외=0 이진 라벨. 우선순위=누적 log-prob(우리 `score=parent+tactic_score`) ⊕ value.
- **HTPS**(2205.11491): critic c(g)→[0,1], MCTS leaf value, **product backup**(QED와 동일 구조). online expert iteration으로 critic 재학습(Metamath 65→82%).
- **데이터**: 우리가 이미 가짐 — ClassicalSearcher가 트리(root_candidate.children, 각 proof_str/tactic/depth, VALID/INVALID/COMPLETE) 생성. 라벨: 성공경로=1, subtree 전멸/INVALID=0, 거리=COMPLETE까지 path 길이. **단, 노드별 goal text를 로깅해야 함**(현재 미저장).
- **expert iteration**(2202.01344): 자기 성공증명으로 정책 재학습 → policy 개선(value는 순서 개선, 상보적).
- 기타: DT-Solver(동적 예산), TacticZero(policy-gradient, 무거움), LeanProgress(거리 회귀 확인).

## 구현 스케치 (MR1 value-guided)
1. **데이터 로깅**: ClassicalSearcher.search_step에 노드 `(goal_key, tactic, depth, cum_logprob, outcome)` JSONL 기록 훅. 탐색 종료 후 트리에서 성공경로/dead 라벨링.
2. **특징**: goal text → 동결 DeepSeek encoder mean-pool 임베딩(생성용 모델 재사용, goal_key로 캐시). 대안: 수제 특징(#hyps, 길이, depth, cum_logprob, retrieval-hit, top1-top2 margin).
3. **value head**: MLP[emb→256→1] sigmoid. 이진 BCE(=P(solved)) 또는 거리 MSE(γ^steps). 수 분 학습.
4. **frontier blend**: `score = cum_logprob + value_weight·log(V+eps)` (value_weight=0이면 현 baseline=A/B). 다중 subgoal이면 product backup(A3와 연결).
5. **wiring**: ClassicalSearchConf(value_guided, value_weight, value_ckpt), summary.json 기록.

출처: QEDCartographer 2408.09237 · GPT-f 2009.03393 · HTPS 2205.11491 · ExIt 2202.01344 · Proverbot9001(repo) · DT-Solver ACL2023 · LeanProgress 2502.17925.
