# 학습·평가 실행 Runbook (구현 완료분 — 실제 구동은 마지막에)

> 사용자 지시: **실험(평가 실행)은 맨 마지막에**. 아래는 전부 구현·단위테스트 완료.
> 실제 GPU/Coq 구동 시 이 순서대로. ★OCaml/opam 버전 변경 금지.

## 0. 공통 전제
- 모델 서버(rango tactic_gen)와 coq-lsp가 떠 있어야 함(run_thm 경로).
- base 모델: `deepseek-ai/deepseek-coder-1.3b-base`, rango adapter = 기존 LoRA.

## 1. Quarry (Planning to Hammer) — 평가
```
# 난이도 학습(선택; 없으면 heuristic 자동): trace 수집 후
python3 scripts/run_all.py --alias quarry-trace --num 40 --start 200 --timeout 600 --workers 1
python3 scripts/train_quarry_difficulty.py \
    --traces data/quarry_traces/traces.jsonl --out models/quarry_difficulty/difficulty.json
# 평가(학습 θ / heuristic θ)
python3 scripts/run_all.py --alias quarry      --num 40 --timeout 600 --workers 1
python3 scripts/run_all.py --alias quarry-heur --num 40 --timeout 600 --workers 1
```
컴포넌트: 분해생성(A)/검증(B)/28차원 난이도(C)/재귀 SolveGoal(D)/CoqHammer(E)/오프라인학습(F).

## 2. GRPO (DeepSeek-Prover-V1.5) — 학습→평가
```
# (1) rollout 수집: train셋에서 정리당 G개 시도 생성+Coq검증 → 그룹 jsonl
#     grpo_rollout.collect_group()을 run_thm 서버/proof_manager 셋업에서 호출하는 드라이버 필요.
#     출력: data/grpo_rollouts/rollouts.jsonl
# (2) GRPO 업데이트
python3 src/tactic_gen/grpo_train.py \
    --rollouts data/grpo_rollouts/rollouts.jsonl \
    --model_name deepseek-ai/deepseek-coder-1.3b-base \
    --init_adapter <rango-adapter> --collator_conf <rango training_conf.yaml> \
    --save_dir models/rango-grpo/adapter --epochs 1 --lr 1e-6 --kl_beta 0.04
# (3) 새 adapter로 평가(rango 경로에 adapter 교체 후 run_all)
```
코어: 그룹상대 advantage + 클립목적 −β·KL (grpo.py, 단위테스트 완료).

## 3. BFS-Prover full (expert-iteration + DPO) — 학습→평가
```
# (1) 트리 덤프 수집(성공경로 backprop 포함)
python3 scripts/run_all.py --alias bfs-prover-trace --num 40 --start 200 --timeout 300 --workers 1
# (2) 라운드 오케스트레이션(탐색→SFT/DPO 추출→DPO 학습→반복)
python3 src/tactic_gen/bfs_expert_iter.py \
    --rounds 2 --model_name deepseek-ai/deepseek-coder-1.3b-base \
    --init_adapter <rango-adapter> --collator_conf <rango training_conf.yaml>
# (3) 최종 adapter로 bfs-prover 평가
```
DPO 코어(dpo.py)·추출(bfs_dpo_data.py)·학습(dpo_train.py) 단위테스트 완료.

## 4. QEDCartographer full (value iteration) + ablation
```
# (1) 트리 덤프(AND-OR 엣지 포함) 수집
python3 scripts/run_all.py --alias rango-vlog --num 60 --start 200 --timeout 600 --workers 1
# (2) value 학습: closed-form / bootstrap × backup ablation
python3 scripts/train_qed_value.py --mode closed-form --gamma 0.9 --out models/qed_value/qed.pt
python3 scripts/train_qed_value.py --mode bootstrap  --gamma 0.9 --backup product
# (3) 검색시 backup ablation 평가
python3 scripts/run_all.py --alias rango-qed      --num 40 --timeout 600 --workers 1  # product(논문)
python3 scripts/run_all.py --alias rango-qed-sum  --num 40 --timeout 600 --workers 1  # ablation
python3 scripts/run_all.py --alias rango-qed-min  --num 40 --timeout 600 --workers 1  # ablation
```

## 5. 최종 종합 표
```
python3 scripts/ablation_compare.py         # 탐색 ablation 20 vs 40 + baseline 대비
python3 scripts/unique_solves.py            # baseline 못 푸는 것 unique solve
```
전 기법 baseline(published Rango) 대비 net/unique/regress로 보고.
