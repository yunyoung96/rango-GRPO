#!/bin/bash
set -u
export SUBGOAL_CURRICULUM=data/curriculum/empty.json
export SUBGOAL_OUT=data/grpo_rollouts/smoke_hybrid.jsonl
export SUBGOAL_POLICY=models/rango-grpo-cascade-s0/adapter
export SUBGOAL_SKIP_S0=0 SUBGOAL_REWARD=0 SUBGOAL_GS=2 SUBGOAL_MAXSTEPS=6 SUBGOAL_HYBRID=1
python3 scripts/run_all.py --alias grpo-rollout-subgoal --idx-file /tmp/claude-0/-app-coq-modeling/593ee1f6-f742-496d-b483-be0594031e23/scratchpad/smoke_idx.txt --timeout 60 --gpus 0 --workers 2 >> all_log/smoke.log 2>&1
echo "[smoke 완료]" >> all_log/smoke.log
