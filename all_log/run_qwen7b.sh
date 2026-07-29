#!/bin/bash
# Qwen2.5-Coder-7B QLoRA 재학습 (rango 레시피, base만 교체). 재개용 드라이버.
#   smoke(30step, GPU0) → 통과 시 전체 학습(2-GPU DDP) → models/rango-qwen7b-ft.
# 사전조건: raw-data/coq-dataset, sentences.db, data/ft6.7b-shuffled-index.json (재사용).
# 파이프라인 수정 반영됨: eval_strategy/processing_class(transformers 4.46+), 4-bit device_map(LOCAL_RANK), make_output_dir 가드 완화.
set -u
cd /app/coq-modeling
export PYTHONPATH=src
CONF=all_log/ft_qwen7b_conf.yaml
SMOKE=all_log/ft_qwen7b_smoke.yaml
LOG=all_log/qwen7b.log
say(){ echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }

# 잔여 서버 정리(PID로 — 패턴 pkill 자기매칭 회피)
for p in $(pgrep -f tactic_gen_server 2>/dev/null); do kill -9 "$p" 2>/dev/null; done
sleep 3

# smoke config 생성(30 step)
sed 's/max_steps: 20000/max_steps: 30/; s|models/rango-qwen7b-ft|models/rango-qwen7b-ft-smoke|g' "$CONF" > "$SMOKE"
rm -rf models/rango-qwen7b-ft-smoke
say "▶ smoke (GPU0, 30step)"
CUDA_VISIBLE_DEVICES=0 python3 -u src/tactic_gen/train_decoder.py "$SMOKE" >> "$LOG" 2>&1
if grep -qiE 'train_runtime' "$LOG"; then
  say "✓ smoke 통과 → 전체 학습(2-GPU DDP)"
  if torchrun --nproc_per_node=2 --master_port=29517 src/tactic_gen/train_decoder.py "$CONF" >> "$LOG" 2>&1; then
    say "■ 완료(2-GPU) → models/rango-qwen7b-ft"
  else
    say "⚠ 2-GPU 실패 → 단일 GPU 재시도"
    CUDA_VISIBLE_DEVICES=0 python3 -u src/tactic_gen/train_decoder.py "$CONF" >> "$LOG" 2>&1 && say "■ 완료(단일 GPU)"
  fi
else
  say "✗ smoke 실패 — $LOG 확인"; tail -25 "$LOG"
fi
