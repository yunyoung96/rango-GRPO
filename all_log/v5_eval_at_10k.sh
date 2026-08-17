#!/bin/bash
# step 10000 체크포인트가 나오면 → 학습 일시정지 → rand200 평가 → 학습 재개.
#
# 왜 일시정지하나: 평가도 GPU 를 쓴다. 같이 돌리면 600초 타임아웃 안에 들어가는
#   탐색량이 줄어 성공률이 과소평가된다(워커-타임아웃 confound).
# 재개 손실: 감독이 마지막 체크포인트(=10000)에서 이어받으므로 0.
cd /app/coq-modeling || exit 1
set -u
CKPT=models/rango-qwen3b-v5-ft/checkpoint-10000
LOG=all_log/v5_eval_at_10k.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
say "===== step 10000 대기 시작 ====="
while [ ! -f "$CKPT/adapter_model.safetensors" ]; do
  sleep 300
  [ -f /tmp/v5_diverged ] && { say "발산 플래그 — 대기 중단"; exit 1; }
done
say "checkpoint-10000 감지 — 학습 일시정지"
pgrep -af supervisor | grep -v "bin/bash -c" | awk '{print $1}' | xargs -r kill -9
sleep 5
pkill -9 -f train_decoder; sleep 15
for p in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader); do kill -9 "$p" 2>/dev/null; done
sleep 10
say "rand200 평가 시작 (600s, g2xw6=12병렬)"
bash all_log/eval_v5.sh "$CKPT" v5-step10000 >> "$LOG" 2>&1
say "평가 종료 — 결과:"
D=$(ls -d all_results/v5-step10000_rand200_t600_g2xw6 2>/dev/null)
[ -f "$D/summary.json" ] && python3 -c "
import json;d=json.load(open('$D/summary.json'))
print(f\"   v5 step10000: {d['success']}/{d['done']} = {d['success']/max(d['done'],1)*100:.1f}%\")" | tee -a "$LOG"
say "학습 재개"
nohup bash all_log/v5_supervisor.sh > /dev/null 2>&1 &
say "===== 완료 ====="
