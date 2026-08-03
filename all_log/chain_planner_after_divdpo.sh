#!/bin/bash
# divdpo eval 완주 감지 → 최종 보고 → GPU1 확보 → planner 6.7B 배관 스모크.
#   사용자 결정(2026-07-30): "divdpo 완주 후 planner". ★GPU1 전용, GPU0 금지.
#   스모크(6.7B)까지만 자동 — 32B 실전은 plan 품질/plumbing 확인 후 별도 launch.
set -u
LOG=all_log/planner_run.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] [chain] $*" | tee -a "$LOG"; }

say "divdpo eval 200/200 완주 대기..."
while true; do
  d=$(python3 -c "import json;print(len(json.load(open('all_results/rand200_divdpo_w2/summary.json')).get('results',[])))" 2>/dev/null || echo 0)
  [ "${d:-0}" -ge 200 ] && break
  sleep 300
done
say "divdpo 완주. 최종:"
python3 -c "import json;r=json.load(open('all_results/rand200_divdpo_w2/summary.json'))['results'];s=sum(1 for x in r if x['success']);print(f'  ★ divdpo rand200 w2 = {s}/{len(r)} = {100*s/len(r):.1f}%  (vs SFT->GRPO 37.5%, 안전-EI 35.0%)')" | tee -a "$LOG"

say "GPU1 확보(divdpo run_all/server 정리)..."
for p in $(pgrep -f '[r]un_divdpo'); do kill "$p" 2>/dev/null; done
for p in $(pgrep -f '[r]un_all\.py'); do kill "$p" 2>/dev/null; done
sleep 3
for p in $(pgrep -f '[t]actic_gen_server'); do kill -9 "$p" 2>/dev/null; done
sleep 6
say "GPU: $(nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader | tr '\n' ' | ')"

say "planner 배관 스모크(6.7B, 앞5정리, w1, 120s) 시작..."
bash all_log/run_planner_smoke.sh smoke
say "스모크 완료 — plan 품질/plumbing 확인 후 32B 실전(rango-planner) launch 예정."
