#!/bin/bash
# 안전-EI 재개 체인: 남은(미시작) 66개만 GPU1로 롤아웃(진행분 219에 append) → 오케스트레이터 재시작.
#   재시작 시 run_ei_safe.sh는 ei-safe-r1.jsonl이 차 있어 R1 rollout을 스킵 → RFT/GRPO/val(전부 GPU1).
set -u
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] [chain] $*" | tee -a all_log/ei_safe.log; }
export SUBGOAL_CURRICULUM=data/curriculum/empty.json \
       SUBGOAL_OUT=data/grpo_rollouts/ei-safe-r1.jsonl \
       SUBGOAL_POLICY=models/rango-grpo/adapter \
       SUBGOAL_SKIP_S0=0 SUBGOAL_REWARD=0 SUBGOAL_HYBRID=0 \
       SUBGOAL_GS=8 SUBGOAL_MAXSTEPS=20
say "남은 66개 GPU1(w4) 롤아웃 시작 (append, 시작 전 $(wc -l < data/grpo_rollouts/ei-safe-r1.jsonl)그룹)"
python3 scripts/run_all.py --alias grpo-rollout-subgoal \
   --idx-file data/compcert_bs2_train_remaining.txt \
   --timeout 600 --gpus 1 --workers 4 >> all_log/ei_safe.log 2>&1
say "남은 롤아웃 완료 → ei-safe-r1.jsonl 총 $(wc -l < data/grpo_rollouts/ei-safe-r1.jsonl)그룹"
# 안전: 혹시 append 아니고 truncate였으면 백업 복구
n=$(wc -l < data/grpo_rollouts/ei-safe-r1.jsonl)
if [ "$n" -lt 219 ]; then
  say "⚠ 그룹수 $n < 219 (truncate 의심) → 백업 복구 후 병합"
  cat data/grpo_rollouts/ei-safe-r1.jsonl.bak >> data/grpo_rollouts/ei-safe-r1.jsonl
  say "복구 후 $(wc -l < data/grpo_rollouts/ei-safe-r1.jsonl)그룹"
fi
say "오케스트레이터 재시작(rollout 스킵 → RFT/GRPO/val, GPU1-only)"
bash all_log/run_ei_safe.sh >> all_log/ei_safe_boot.log 2>&1
say "체인 종료"
