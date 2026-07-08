#!/bin/bash
cd /app/coq-modeling
export PYTHONPATH=src
log(){ echo "[$(date -u +%H:%M:%S)] $*" >> all_log/ft6.7b.log; }
log "=== 6.7B 파인튜닝 드라이버: 인덱스+GPU 대기 ==="
# 인덱스 완료 대기
while [ ! -f data/ft6.7b-shuffled-index.json ] || pgrep -f "shuffled_idx" >/dev/null 2>&1; do sleep 30; done
log "인덱스 완료. 앞선 모든 GPU 실험 대기."
while ps -eo args | grep -qE "[o]racle_ablation|[r]un_all.py --alias|[r]un_bigger.sh|[r]un_qed.sh|[r]un_oracle"; do sleep 120; done
for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
# 스모크: max_steps 30으로 파이프라인 검증(retrieval on-the-fly 첫 example들이 도는지)
log "▶ 스모크(max_steps 30)"
sed 's/max_steps: 20000/max_steps: 30/; s|output_dir: "models/rango-6.7b-ft"|output_dir: "models/rango-6.7b-ft-smoke"|; s|models/rango-6.7b-ft|models/rango-6.7b-ft-smoke|g' all_log/ft6.7b_conf.yaml > all_log/ft6.7b_smoke.yaml
timeout 3600 python3 src/tactic_gen/train_decoder.py all_log/ft6.7b_smoke.yaml > all_log/ft6.7b_smoke.log 2>&1
if grep -qiE "loss|train_runtime|it/s" all_log/ft6.7b_smoke.log; then
  log "✓ 스모크 통과(학습 진행 확인) → 전체 학습"
  python3 src/tactic_gen/train_decoder.py all_log/ft6.7b_conf.yaml >> all_log/ft6.7b.log 2>&1
  log "■ 6.7B 파인튜닝 완료 → models/rango-6.7b-ft"
else
  log "✗ 스모크 실패 — ft6.7b_smoke.log 확인"
  tail -25 all_log/ft6.7b_smoke.log >> all_log/ft6.7b.log
fi
log "=== 드라이버 종료 ==="
