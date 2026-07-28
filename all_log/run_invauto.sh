#!/bin/bash
set -u
LOG=all_log/invauto.log
export SUBGOAL_CURRICULUM=data/curriculum/invauto.json
export SUBGOAL_OUT=data/grpo_rollouts/invauto.jsonl
export SUBGOAL_POLICY=models/rango-grpo-cascade-s0/adapter
export SUBGOAL_SKIP_S0=1 SUBGOAL_REWARD=0 SUBGOAL_GS=1 SUBGOAL_MAXSTEPS=0
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
say "════ invertible+auto 순수 닫기 (34정리, max_steps=0=모델없음, GPU0) ════"
python3 scripts/run_all.py --alias grpo-rollout-subgoal --idx-file data/compcert_bs2_invauto_idx.txt --timeout 40 --gpus 0 --workers 2 >> "$LOG" 2>&1
say "════ [invauto 완료] → $SUBGOAL_OUT ════"
