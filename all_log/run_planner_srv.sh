#!/bin/bash
# Planner–Executor 실전 (persistent planner 서버). ★GPU1 전용, GPU0 금지.
#   planner_server(Qwen-7B bf16)를 한 번 로드 → run_all이 HTTP로 공유(정리 재로드 0, w2 가능).
#   사용: bash all_log/run_planner_srv.sh smoke   |   bash all_log/run_planner_srv.sh eval
set -u
MODE="${1:-smoke}"
PORT=8130
URL="http://127.0.0.1:$PORT"
PLANNER_MODEL="${PLANNER_MODEL:-Qwen/Qwen2.5-Coder-7B-Instruct}"   # 32B: Qwen/Qwen2.5-Coder-32B-Instruct-AWQ
LOG=all_log/planner_run.log
RAND=data/compcert_bs2_rand200_idx.txt
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

# ── planner 서버 시작(없으면) ──
if ! pgrep -f '[p]lanner_server.py' >/dev/null; then
  say "planner_server 시작 ($PLANNER_MODEL, GPU1, port $PORT)..."
  CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 nohup python3 src/model_deployment/planner_server.py \
    "$PLANNER_MODEL" $PORT > all_log/planner_server.log 2>&1 &
  # READY 대기(최대 ~5분)
  for i in $(seq 1 60); do
    grep -q 'READY' all_log/planner_server.log 2>/dev/null && break
    grep -qiE 'Traceback|Error' all_log/planner_server.log 2>/dev/null && { say "✗ planner_server 로드 실패"; tail -5 all_log/planner_server.log; exit 1; }
    sleep 5
  done
  grep -q 'READY' all_log/planner_server.log || { say "✗ planner_server READY 안됨"; exit 1; }
  say "planner_server READY."
else
  say "planner_server 이미 실행중."
fi

# ── eval ──
if [ "$MODE" = "smoke" ]; then
  head -8 "$RAND" > /tmp/planner_srv_smoke.txt
  say "════ smoke: 8정리, w2, 300s (planner 서버 공유) ════"
  PLANNER_URL=$URL CUDA_VISIBLE_DEVICES=1 python3 scripts/run_all.py --alias rango-planner \
    --idx-file /tmp/planner_srv_smoke.txt --timeout 300 --gpus 1 --workers 2 \
    --out all_results/smoke_planner_srv --description "planner-srv smoke" 2>&1 | tee -a "$LOG"
  say "  smoke 결과: $(python3 -c "import json;r=json.load(open('all_results/smoke_planner_srv/summary.json'))['results'];print(sum(1 for x in r if x['success']),'/',len(r),'솔브')" 2>/dev/null)"
  say "  planner 호출: $(grep -h '\[planner\]' all_results/smoke_planner_srv/logs/*.txt 2>/dev/null | wc -l)회 (>0이어야 정상)"
elif [ "$MODE" = "eval" ]; then
  say "════ eval: rand200, w2, 600s (planner 서버 공유) vs SFT→GRPO 37.5% ════"
  PLANNER_URL=$URL CUDA_VISIBLE_DEVICES=1 python3 scripts/run_all.py --alias rango-planner \
    --idx-file "$RAND" --timeout 600 --gpus 1 --workers 2 \
    --out all_results/rand200_planner_w2 --description "planner rand200 w2" 2>&1 | tee -a "$LOG"
  SR=$(python3 -c "import json;r=json.load(open('all_results/rand200_planner_w2/summary.json'))['results'];su=sorted(x['elapsed_sec'] for x in r if x['success']);p=su[int(0.9*len(su))] if su else 0;print(f\"{sum(1 for x in r if x['success'])}/{len(r)} (p90 {p:.0f}s)\")" 2>/dev/null||echo '?')
  say "════ ★ planner-executor rand200 w2 = $SR   (vs SFT→GRPO 75/200=37.5%) ════"
fi
