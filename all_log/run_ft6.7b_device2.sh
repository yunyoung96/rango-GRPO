#!/bin/bash
# ===== device2(GPU2) 전용: 6.7B 파인튜닝 자기완결 실행 =====
# 이 컨테이너 복사본에서 그냥 `bash all_log/run_ft6.7b_device2.sh` 하면 됨.
# (대기 없음 — device2엔 다른 실험이 없으므로 바로 시작)
cd /app/coq-modeling
export PYTHONPATH=src
log(){ echo "[$(date -u +%H:%M:%S)] $*" | tee -a all_log/ft6.7b_device2.log; }

log "=== 6.7B 파인튜닝 (device2) 시작 ==="
# 사전조건 확인
[ -f data/ft6.7b-shuffled-index.json ] || { log "✗ shuffled index 없음. 먼저 빌드 필요."; exit 1; }
[ -d models_dl/deepseek-coder-6.7b-instruct ] || { log "✗ 6.7B 모델 없음(models_dl). 복사 확인."; exit 1; }
for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 2

# 1) 스모크(30 step): 파이프라인+속도 검증
log "▶ 스모크(max_steps 30) — step당 속도 측정"
sed 's/max_steps: 20000/max_steps: 30/; s|models/rango-6.7b-ft|models/rango-6.7b-ft-smoke|g' \
    all_log/ft6.7b_conf.yaml > all_log/ft6.7b_smoke.yaml
timeout 3600 python3 src/tactic_gen/train_decoder.py all_log/ft6.7b_smoke.yaml 2>&1 | tee all_log/ft6.7b_smoke_d2.log
if grep -qiE "loss|it/s|train_runtime" all_log/ft6.7b_smoke_d2.log; then
  log "✓ 스모크 통과 → 전체 학습(20k step)"
  # 2) 전체 학습
  python3 src/tactic_gen/train_decoder.py all_log/ft6.7b_conf.yaml 2>&1 | tee -a all_log/ft6.7b_device2.log
  log "■ 파인튜닝 완료 → models/rango-6.7b-ft"
  # 3) fine-tuned 6.7B oracle (capacity 판정) — 최신 체크포인트 자동 탐색
  CKPT=$(ls -d models/rango-6.7b-ft/checkpoint-* 2>/dev/null | sort -t- -k2 -n | tail -1)
  ln -sfn "$(basename $CKPT)" models/rango-6.7b-ft/final   # rango-6.7b-ft alias가 가리킴
  log "▶ fine-tuned 6.7B oracle (ckpt=$CKPT → final)"
  # rango-6.7b-ft alias는 run_thm.py에 정의됨(아래 참고). 없으면 checkpoint 경로로 직접.
  python3 scripts/oracle_ablation.py --alias rango-6.7b-ft --num-files 40 --max-proofs-per-file 8 \
    --max-steps-per-proof 30 --cond both --out all_log/oracle_6.7b_ft_AB.md 2>&1 | tee -a all_log/ft6.7b_device2.log
  log "■ fine-tuned 6.7B oracle 완료 → all_log/oracle_6.7b_ft_AB.md"
else
  log "✗ 스모크 실패 — all_log/ft6.7b_smoke_d2.log 확인"
fi
log "=== device2 파인튜닝 드라이버 종료 ==="
