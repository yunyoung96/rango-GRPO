#!/bin/bash
set -u
export SUBGOAL_CURRICULUM=data/curriculum/invgr.json
export SUBGOAL_OUT=data/grpo_rollouts/invgr.jsonl
export SUBGOAL_POLICY=models/rango-grpo-cascade-s0/adapter
export SUBGOAL_SKIP_S0=1 SUBGOAL_REWARD=1 SUBGOAL_GS=1 SUBGOAL_MAXSTEPS=1
python3 scripts/run_all.py --alias grpo-rollout-subgoal --idx-file data/compcert_bs2_invprobe_idx.txt --timeout 45 --gpus 0 --workers 2 >> all_log/invgr.log 2>&1
echo "[goal-reader 완료]" >> all_log/invgr.log
