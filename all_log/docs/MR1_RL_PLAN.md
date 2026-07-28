# MR1: QEDCartographer-영감 value-guided best-first (RL) — 실행 계획

> 사용자 우선순위: **4→1→3→2** (RL 먼저). 이 문서 = 4번(RL) 구현 계획.

## 목표
QEDCartographer의 실제 이득 원천(value 순서화 + product-over-subgoals backup)을 Rango의 ClassicalSearcher에 이식.
policy(DeepSeek 생성)는 supervised 유지, **critic(value head)만** 학습해 frontier 우선순위를 블렌드.

## 구현 플랫폼/프레임워크 (사용자 질문 답)
**외부 RL 플랫폼을 쓰지 않는다. 전부 PyTorch로 직접 구현한 커스텀 파이프라인이다.**
- **탐색 하네스**: Rango 자체의 `ClassicalSearcher`(best-first, heapq). gym/environment 없음.
- **value 모델**: 순수 `torch.nn` MLP — `src/model_deployment/value_head.py`(특징 v1: hand feats + goal 토큰 해시 BoW → MLP[520→128→1] sigmoid).
- **학습**: `scripts/train_value.py`, **지도학습 BCE**(자기 탐색 트리에서 뽑은 (state→solvable) 라벨). Adam, pos_weight 불균형 보정.
- **의존성**: `torch`만. stable-baselines/RLlib/gym/Ray 등 **RL 프레임워크 미사용**.
- **QEDCartographer 원본 코드 미사용**: 그건 Proverbot9001(Coq 8.10.2 + coq2vec LSTM + polyarg + MPI)로 Rango(DeepSeek/LoRA/Coq8.18)와 통합 불가(→ RL_LITERATURE.md). **아이디어(value 순서화 + subgoal product backup)만 이식.**

### 정직한 명명: 이건 "full RL"이 아니라 **지도학습 critic(value-guided search)**이다
- policy gradient 없음, reward 최대화 루프 없음, environment stepping 없음.
- 하는 일 = **V(state)=P(solvable)를 self-play 탐색 결과로 학습**(라벨=실제 탐색에서 그 state가 QED로 이어졌나) → best-first 우선순위 블렌드.
- QEDCartographer는 "reward-free value iteration"(Bellman 부트스트랩). 우리 v1은 그 **단순화판(1-pass 지도학습, 부트스트랩 없이 실측 라벨)**. expert iteration(자기증명 재학습)까지 가면 online RL에 근접하나 현재 v1은 아님.
- 즉 "강화학습"이라기보다 **학습된 탐색 휴리스틱(critic)**. 보고 시 이 구분을 유지한다.

## 파이프라인
- **A. 데이터 로깅 (완료)**: ClassicalSearcher가 탐색 트리의 각 VALID 노드에 도달 goal 상태 저장,
  탐색 종료 시 `_dump_tree()`로 (goal, label, dist, depth, cum_score, tactic_score, tactic) JSONL 덤프.
  label=1: 이 state에서 예산 내 증명완료 가능(성공경로/조상), label=0: subtree 전멸.
  alias `rango-vlog` (classical+memo+log_tree).
- **B. 라벨 트리 생성 (다음)**: `rango-vlog`를 100~200 정리에 실행 → `data/vguided_trees/*.jsonl`.
  solved 정리에서 positive, 실패 정리에서 negative 확보. hprobe/GPU 여유 후 실행.
- **C. value head 학습**: goal → 특징 → MLP → sigmoid, BCE(=P(solvable)).
  특징 v1(경량, 모델 불필요): #hyps, goal 길이, depth, cum_score, tactic_score, 토큰 해시 BoW.
  특징 v2(무거움, 추후): 동결 DeepSeek encoder mean-pool 임베딩. 스크립트 `scripts/train_value.py`.
- **D. frontier 블렌드**: `score = cum_score + value_weight·log(V+eps)`. alias `rango-vguided`(value_ckpt/value_weight).
  다중 subgoal은 product backup(∏V) — QED와 동일 AND 구조.
- **E. 평가**: rango-vguided vs baseline(공정 @600), value_weight sweep(0/0.5/1/2).

## 정직한 리스크 (선반영)
- **classical best-first 자체가 straight-line baseline에 −3**(rango-mem). value 유도는 이 적자를 *넘어야* 순증.
  QEDCartographer 이득은 CoqGym의 *약한* best-first 대비였지 강한 diverse sampling 대비가 아님.
- 우리 전체 발견: verifier 있으면 diverse full-budget sampling이 지배, search-order tweak은 진다.
  → MR1은 **학습된** search-order라 더 나을 여지는 있으나, baseline 초과는 불확실. 그래도 사용자 요청이라 제대로 빌드+정직 보고.
- label 잡음: label=0이 "진짜 불가능"이 아니라 "예산 내 미완". HTPS도 동일 처리(unproven=0). 예산 크게 주면 완화.

## 상태
- [x] A 데이터 로깅 (classical_searcher.py `_dump_tree`, rango-vlog/vguided alias)
- [ ] B 라벨 트리 생성 (rango-vlog @ 150 정리)
- [ ] C value head 학습 (scripts/train_value.py)
- [ ] D frontier 블렌드 (_value_model 로드 + 블렌드)
- [ ] E 평가

출처: QEDCartographer 2408.09237 · HTPS 2205.11491 · GPT-f 2009.03393 · ExIt 2202.01344.

## ★실측 리스크 (2026-07-07 08:5x): positive 데이터 부족
- Part B 재생성(수정 후) 초반 10정리 전부 classical 실패 → **positive 0, negative 884**. classical이 CompCert(idx30~)를 거의 못 풀어 성공경로(=positive) 상태가 안 나옴.
- value 모델은 pos/neg 둘 다 필요(train_value: pos==0이면 학습 불가). 100정리 완주 후 positive 총량 재확인 필요.
- positive 부족 시 대응: (a) 더 큰 data-gen 세트, (b) straight-line 성공증명을 pseudo-tree(성공경로=positive)로 변환해 positive 보강, (c) 더 쉬운(그러나 eval과 분리된) 정리 포함.
- 이 자체가 시사점: classical이 약해 positive 자체가 희소 → value-guided classical의 baseline 초과 가능성을 더 낮춤(정직 반영).
