#!/bin/bash
# ★ 사용자 요청: backward 잠깐 멈추고 LUFFY-on-fix 부터.
#   backward @20 부분결과(캐시)는 보존 → 나중에 seval 이 이어서 완료(재수집 안 함, run_backward.sh 안 씀).
#   순서: [정지] → LUFFY-on-fix → backward 이어서 → backward-prm → retry-prm → fix@180.
set -u
LOG=all_log/chain_luffy_priority.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF="$(dirname "$INIT")/training_conf.yaml"
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }

say "===== 정지: backward eval + 기존 체인 종료 (backward 캐시는 보존) ====="
kill 656002 758997 2>/dev/null
pkill -f "run_all.py --alias rango-grpo-backward" 2>/dev/null
pkill -f "run_thm.py run rango-grpo-backward" 2>/dev/null
pkill -f "tactic_gen_server.py decoder-local models/rango-grpo-backward" 2>/dev/null
sleep 12
say "GPU: $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader)"

say "▶ 1/4  LUFFY-on-fix @20→@40 (fix 어댑터 위, 앞당김)"
bash all_log/run_luffy.sh
say "◀ LUFFY-on-fix 완료"

say "▶ 2/4  backward 이어서 (캐시 resume, @20→@40) + backward-prm"
[ -f models/rango-grpo-backward/adapter/adapter_model.safetensors ] && seval rango-grpo-backward || say "  ★ backward 모델 없음"
[ -f models/rango-grpo-backward-prm/adapter/adapter_model.safetensors ] && seval rango-grpo-backward-prm || say "  ★ backward-prm 모델 없음"

say "▶ 3/4  retry-prm 재학습 + eval"
if [ ! -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && [ -s data/grpo_rollouts/retry.jsonl ]; then
  python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/retry.jsonl \
    --model_name "$BASE" --init_adapter "$INIT" --collator_conf "$CONF" --max_len 3072 \
    --save_dir models/rango-grpo-retry-prm/adapter \
    --process --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-retry-prm/ 2>/dev/null
fi
[ -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && seval rango-grpo-retry-prm || say "  ★ retry-prm 실패"

say "▶ 4/4  fix @180 (통계 확정)"
python3 scripts/smart_eval.py --alias rango-grpo-fix --stages 180 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"

say "===== 전체 완료 (LUFFY-on-fix 우선) ====="
grep -h "smart\] ■" all_log/luffy.log "$LOG" 2>/dev/null | tail -10
