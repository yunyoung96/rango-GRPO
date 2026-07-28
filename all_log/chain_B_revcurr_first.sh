#!/bin/bash
# B안: KL-LUFFY 학습만 끝내고 평가는 미룸 → revcurr 먼저 → 그 다음 KL-LUFFY 평가 → 나머지.
# 순서: [KL-LUFFY 학습완료 대기] → revcurr → KL-LUFFY eval → adaptprefix → bread
#        → backward-prm(eval) → bigscale → retry-prm → fixdyn(refix, 버그수정판)
set -u
LOG=all_log/chain_B.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT_FIX=models/rango-grpo-fix/adapter
INIT_ORIG=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
TPID=1552094   # 진행 중인 KL-LUFFY 학습 python (평가는 이 스크립트가 뒤에서 담당)
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 --workers 2 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"; }
roll(){ [ -s "$2" ] && return 0; rm -f "$2"; python3 scripts/run_all.py --alias "$1" --start 200 --num 40 --timeout 900 --workers 2 --description "$1" >> "$LOG" 2>&1; [ -s "$2" ]; }
trainf(){ python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$INIT_FIX" --collator_conf "$CONF" --max_len 3072 --save_dir "$2" --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 "${@:3}" >> "$LOG" 2>&1; cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$(dirname "$2")/" 2>/dev/null; }

say "대기: KL-LUFFY 학습(PID $TPID) 완료까지 — 평가는 스킵하고 revcurr 먼저"
while kill -0 "$TPID" 2>/dev/null; do sleep 30; done
cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-luffy-kl/ 2>/dev/null
say "KL-LUFFY 학습 완료(adapter 저장 확인). 평가는 revcurr 뒤로 미룸."

say "▶ 1  revcurr (최우선)"; bash all_log/run_revcurr.sh

say "▶ 2  KL-LUFFY 평가 (미뤄둔 것)"
[ -f models/rango-grpo-luffy-kl/adapter/adapter_model.safetensors ] && seval rango-grpo-luffy-kl || say "★ KL-LUFFY adapter 없음 — 학습 실패?"

say "▶ 3  adaptprefix"
roll grpo-rollout-adaptprefix data/grpo_rollouts/adaptprefix.jsonl && { [ ! -f models/rango-grpo-adaptprefix/adapter/adapter_model.safetensors ] && trainf data/grpo_rollouts/adaptprefix.jsonl models/rango-grpo-adaptprefix/adapter; seval rango-grpo-adaptprefix; }
say "▶ 4  bread"
roll grpo-rollout-bread data/grpo_rollouts/bread.jsonl && { [ ! -f models/rango-grpo-bread/adapter/adapter_model.safetensors ] && trainf data/grpo_rollouts/bread.jsonl models/rango-grpo-bread/adapter --luffy; seval rango-grpo-bread; }
say "▶ 5  backward-prm (eval only)"; [ -f models/rango-grpo-backward-prm/adapter/adapter_model.safetensors ] && seval rango-grpo-backward-prm
say "▶ 6  bigscale (뒤1000 학습/앞5091 평가 — 매우 오래)"; bash all_log/run_bigscale.sh
say "▶ 7  retry-prm"
[ ! -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && [ -s data/grpo_rollouts/retry.jsonl ] && { python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/retry.jsonl --model_name "$BASE" --init_adapter "$INIT_ORIG" --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-grpo-retry-prm/adapter --process --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1; cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-retry-prm/ 2>/dev/null; }
[ -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && seval rango-grpo-retry-prm
say "▶ 8  fixdyn (버그수정판 재실행)"; bash all_log/run_fixdyn_refix.sh
say "===== 전체 완료 ====="
