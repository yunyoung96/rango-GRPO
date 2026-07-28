#!/bin/bash
# ★ 사용자 요청: luffy-on-fix 끝나면 robust-for-fix(fix@180) 먼저.
#   priority 체인(=$WAIT_PID)이 luffy-on-fix 를 마치고 backward(2/4) 로 넘어가려는 순간 선점 →
#   재배치: fix@180 → backward-prm → retry-prm → revcurr.
set -u
WAIT_PID=${WAIT_PID:?"WAIT_PID 필요 (chain_luffy_priority.sh PID)"}
LOG=all_log/chain_tail.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF="$(dirname "$INIT")/training_conf.yaml"
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }

say "대기: priority 체인(${WAIT_PID}) 이 LUFFY-on-fix 마칠 때까지"
PREEMPTED=0
while kill -0 "$WAIT_PID" 2>/dev/null; do
  if grep -q "◀ LUFFY-on-fix 완료" all_log/chain_luffy_priority.log 2>/dev/null; then
    PREEMPTED=1
    say "LUFFY-on-fix 완료 감지 → 선점(재배치: fix@180 먼저)"
    kill "$WAIT_PID" 2>/dev/null
    # priority 체인이 막 띄웠을 수 있는 backward/retry eval 정리
    pkill -f "run_all.py --alias rango-grpo-backward" 2>/dev/null
    pkill -f "run_thm.py run rango-grpo-backward" 2>/dev/null
    pkill -f "tactic_gen_server.py decoder-local models/rango-grpo-backward" 2>/dev/null
    pkill -f "smart_eval.py --alias rango-grpo-backward" 2>/dev/null
    break
  fi
  sleep 60
done
[ "$PREEMPTED" = "1" ] || say "priority 체인 자연종료(선점 안 함) — 그대로 진행"
say "GPU 잔여 정리 대기(15s)"; sleep 15

say "▶ 1/4  fix @180 (robust for fix — 앞당김)"
python3 scripts/smart_eval.py --alias rango-grpo-fix --stages 180 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"
say "◀ fix@180 완료"

say "▶ 2/4  backward @20→@40 이어서 + backward-prm (캐시 resume)"
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

say "▶ 4/4  revcurr (전체 역행 curriculum)"
bash all_log/run_revcurr.sh

say "===== tail 전체 완료 (fix@180 우선 배치) ====="
grep -h "smart\] ■" "$LOG" all_log/revcurr.log 2>/dev/null | tail -10
