#!/bin/bash
# Planner–Executor 스모크/실전 (PLANNER_EXECUTOR_DESIGN.md). ★GPU1 전용(GPU0 금지).
#   1) 배관 스모크: 로컬 6.7B planner로 앞 5정리/120s — planner 로드·plan 생성·후보 주입·coq-lsp 도는지.
#   2) 실전: 32B planner로 rand200 (또는 서브셋). ★w1(워커당 planner 1개 로드, 메모리). 공정성 §5 주의.
# 사용: bash all_log/run_planner_smoke.sh smoke   |   bash all_log/run_planner_smoke.sh eval
set -u
MODE="${1:-smoke}"
LOG=all_log/planner_run.log
RAND=data/compcert_bs2_rand200_idx.txt
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

if [ "$MODE" = "smoke" ]; then
  say "════ planner 배관 스모크: 6.7B planner, 앞 5정리, w1, 120s (GPU1) ════"
  # 앞 5개만
  head -5 "$RAND" > /tmp/planner_smoke_idx.txt
  CUDA_VISIBLE_DEVICES=1 python3 scripts/run_all.py --alias rango-planner-6b \
    --idx-file /tmp/planner_smoke_idx.txt --timeout 120 --gpus 1 --workers 1 \
    --out all_results/smoke_planner6b --description "planner-6b smoke" 2>&1 | tee -a "$LOG"
  say "  스모크 결과:"; python3 -c "import json;r=json.load(open('all_results/smoke_planner6b/summary.json'))['results'];print('   ', sum(1 for x in r if x['success']),'/',len(r),'솔브')" 2>/dev/null | tee -a "$LOG"
  say "  ↑ plan 품질은 로그에서 '[planner] 분해노드' 라인 육안 확인."

elif [ "$MODE" = "eval" ]; then
  # 32B 다운로드 완료 대기
  say "32B planner 다운로드 완료 대기..."
  until python3 -c "import os,glob; d=os.path.expanduser('~/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-32B-Instruct/snapshots'); import sys; sys.exit(0 if glob.glob(d+'/*/model-00017-of-*.safetensors') or (glob.glob(d+'/*/model.safetensors.index.json') and len(glob.glob(d+'/*/*.safetensors'))>=14) else 1)" 2>/dev/null; do sleep 60; done
  say "════ planner 실전: 32B planner, rand200, w1, 600s (GPU1) ════"
  CUDA_VISIBLE_DEVICES=1 python3 scripts/run_all.py --alias rango-planner \
    --idx-file "$RAND" --timeout 600 --gpus 1 --workers 1 \
    --out all_results/rand200_planner_w1 --description "planner-32b rand200 w1" 2>&1 | tee -a "$LOG"
  SR=$(python3 -c "import json;r=json.load(open('all_results/rand200_planner_w1/summary.json'))['results'];print(f\"{sum(1 for x in r if x['success'])}/{len(r)}\")" 2>/dev/null||echo '?')
  say "════ ★ planner-executor rand200 w1 = $SR (vs SFT→GRPO 37.5% [단 w2측정, §5 공정성 주의]) ════"
else
  echo "usage: $0 smoke|eval"; exit 1
fi
