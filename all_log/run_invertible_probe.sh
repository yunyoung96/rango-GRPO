#!/bin/bash
# invertible 분해 검증 — invertible 스크립트로 분해 → cascade-s0 모델이 각 subgoal 닫나. train 40정리, GPU0만.
set -u
LOG=all_log/invprobe.log
export SUBGOAL_CURRICULUM=data/curriculum/invertible_probe.json
export SUBGOAL_OUT=data/grpo_rollouts/invprobe.jsonl
export SUBGOAL_POLICY=models/rango-grpo-cascade-s0/adapter
export SUBGOAL_SKIP_S0=1      # curriculum(=invertible) 그룹만
export SUBGOAL_REWARD=1       # subgoal 진전(goal수↓)시 reward=1
export SUBGOAL_GS=4 SUBGOAL_MAXSTEPS=12
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
say "════ invertible 분해 검증 (40정리×3변형, cascade-s0, GPU0) ════"
python3 scripts/run_all.py --alias grpo-rollout-subgoal \
  --idx-file data/compcert_bs2_invprobe_idx.txt --timeout 180 --gpus 0 --workers 2 >> "$LOG" 2>&1
say "════ 롤아웃 완료 → $SUBGOAL_OUT ════"
