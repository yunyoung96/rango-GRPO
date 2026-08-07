#!/bin/bash
# checkpoint-40000 저장되면 → 학습 정지 → rand200(600s, 워커16) → 학습 재개.
#   ★ step 21000 평가와 **같은 조건**(600초, GPU2×워커8=16)으로 맞춤 — 학습 진행에 따른 변화를 직접 비교하기 위함.
cd /app/coq-modeling || exit 1
CK=models/rango-1.3b-augmented-ft/checkpoint-40000
LOG=all_log/wait_ckpt40000.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "===== checkpoint-40000 대기 ====="
while [ ! -f "$CK/trainer_state.json" ] || [ ! -f "$CK/adapter_model.safetensors" ]; do
  sleep 30
  if ! pgrep -f "train_decoder.py|ft_rango_augmented" >/dev/null; then
    say "★ 학습이 멈춤 — 40000 도달 전. 평가 취소"; exit 1
  fi
done
sleep 30    # 저장 flush 여유
say "checkpoint-40000 확보 → 학습 정지 후 rand200"
CKPT=$CK WPG=8 TIMEOUT=600 bash all_log/pause_eval_resume.sh >> "$LOG" 2>&1
say "===== 종료 ====="
