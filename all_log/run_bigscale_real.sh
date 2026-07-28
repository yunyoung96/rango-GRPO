#!/bin/bash
# ★ 대규모 scale — CompCert 뒤 1000개로 GRPO 학습 → 앞 5091개 평가(disjoint 일반화 테스트).
#   원본 rango 초기화(scale 효과 격리). eval 이 5091개라 매우 오래 걸림(timeout 300s).
set -u
LOG=all_log/bigscale.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF="$(dirname "$INIT")/training_conf.yaml"
TRAIN=data/compcert_bigscale_train_idx.txt
EVAL=data/compcert_bigscale_eval_idx.txt
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
say "===== bigscale 시작 (뒤 $(wc -l<$TRAIN) 학습 / 앞 $(wc -l<$EVAL) 평가) ====="

say "1) 롤아웃 수집 (뒤 1000개, 오래 걸림)"
if [ ! -s data/grpo_rollouts/bigscale.jsonl ]; then
  rm -f data/grpo_rollouts/bigscale.jsonl
  python3 scripts/run_all.py --alias grpo-rollout-bigscale --idx-file "$TRAIN" --timeout 600 --workers 1 \
    --description "bigscale rollout 1000" >> "$LOG" 2>&1
fi
[ -s data/grpo_rollouts/bigscale.jsonl ] || { say "★ 롤아웃 실패"; exit 1; }
say "  롤아웃 $(wc -l < data/grpo_rollouts/bigscale.jsonl)그룹"

say "2) 학습 (원본 rango 초기화)"
[ ! -f models/rango-grpo-bigscale/adapter/adapter_model.safetensors ] && \
  python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/bigscale.jsonl \
    --model_name "$BASE" --init_adapter "$INIT" --collator_conf "$CONF" --max_len 3072 \
    --save_dir models/rango-grpo-bigscale/adapter --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1
cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-bigscale/ 2>/dev/null

say "3) 평가 (앞 5091개, timeout 300s — 매우 오래)"
[ -f models/rango-grpo-bigscale/adapter/adapter_model.safetensors ] && \
  python3 scripts/run_all.py --alias rango-grpo-bigscale --idx-file "$EVAL" --timeout 300 --workers 1 \
    --out all_results/bigscale_eval --description "bigscale eval 5091" >> "$LOG" 2>&1 || say "★ 학습 실패"

say "===== bigscale 완료 ====="
d=all_results/bigscale_eval; [ -f "$d/summary.json" ] && python3 -c "
import json;r=json.load(open('$d/summary.json'))['results'];print('  bigscale eval:',sum(1 for x in r if x.get('success')),'/',len(r))" 2>&1 | tee -a "$LOG"
