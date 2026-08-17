#!/bin/bash
# 후보 모델 전체를 같은 프로브로 비교 — 어느 모델이 rango 병목을 뚫을 능력이 있나.
#
# 비교 대상(정확한 HF 이름):
#   deepseek-ai/deepseek-coder-1.3b-instruct   3.4G  ← 현재 rango 베이스
#   Qwen/Qwen2.5-Coder-1.5B-Instruct           3.9G
#   Qwen/Qwen2.5-Coder-3B-Instruct             7.7G
#   deepseek-ai/deepseek-coder-6.7b-instruct    17G  ← rango 원논문 크기
#   Qwen/Qwen2.5-Coder-7B-Instruct              19G
#   deepseek-ai/DeepSeek-Prover-V1.5-RL         11G  ← 정리증명 전용 학습
#   Qwen/Qwen2.5-Coder-32B-Instruct             94G  (bf16 ~64GB, 한 장에 적재)
#
# 프로브(전부 코퍼스에 없는 합성 타입 + 실제 gold premise):
#   M1 생성자 소속 / M2 남은분기 추적 / M3 소진판단(세기) / M4 인자수
#   M5 실재 premise vs 환각 이름  ← rango 최대 병목(INVALID 의 45.3%)
#   M6 premise 안 이름 vs 완전 가짜
cd /app/coq-modeling || exit 1
set -u
N=${N:-200}
OUT=all_log/probe_all_models.log
: > "$OUT"
MODELS=(
  "deepseek-ai/deepseek-coder-1.3b-instruct"
  "Qwen/Qwen2.5-Coder-1.5B-Instruct"
  "Qwen/Qwen2.5-Coder-3B-Instruct"
  "deepseek-ai/deepseek-coder-6.7b-instruct"
  "Qwen/Qwen2.5-Coder-7B-Instruct"
  "deepseek-ai/DeepSeek-Prover-V1.5-RL"
  "Qwen/Qwen2.5-Coder-32B-Instruct"
)
for M in "${MODELS[@]}"; do
  echo "[$(TZ=Asia/Seoul date '+%H:%M')] === $M ===" | tee -a "$OUT"
  # 매 모델마다 GPU 를 완전히 비운다(잔존 프로세스로 OOM 난 적 있음)
  for p in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader); do kill -9 "$p" 2>/dev/null; done
  sleep 8
  timeout 3600 env CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 \
    python3 scripts/probe_type_match.py --model "$M" --n "$N" 2>/dev/null \
    | grep -aE "^   [✅❌·]|프레임유효" | tee -a "$OUT"
  echo "" | tee -a "$OUT"
done
echo "[$(TZ=Asia/Seoul date '+%H:%M')] 전체 완료" | tee -a "$OUT"
