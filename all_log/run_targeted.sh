#!/bin/bash
set -u
LOG=all_log/targeted.log
export SUBGOAL_CURRICULUM=data/curriculum/targeted_probe.json
export SUBGOAL_OUT=data/grpo_rollouts/targeted.jsonl
export SUBGOAL_POLICY=models/rango-grpo-cascade-s0/adapter
export SUBGOAL_SKIP_S0=1 SUBGOAL_REWARD=1 SUBGOAL_GS=2 SUBGOAL_MAXSTEPS=8
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
say "════ targeted invertible 롤아웃 (17정리, cascade-s0+retrieval, GPU0) ════"
python3 scripts/run_all.py --alias grpo-rollout-subgoal --idx-file data/compcert_bs2_targeted_idx.txt --timeout 60 --gpus 0 --workers 2 >> "$LOG" 2>&1
say "════ [targeted 완료] → $SUBGOAL_OUT ════"
