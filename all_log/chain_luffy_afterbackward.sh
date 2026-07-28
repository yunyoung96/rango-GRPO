#!/bin/bash
# ★ backward 끝나면 LUFFY-on-fix 먼저 — 사용자 요청.
#   현재 chain_luffy_now.sh(=$WAIT_PID) 는 backward→retry-prm→fix@180 순.
#   backward(평가 포함) 이 끝나 'retry-prm'(3/4) 에 진입하는 순간 선점 →
#   순서 재배치: LUFFY-on-fix → retry-prm → fix@180.
set -u
WAIT_PID=${WAIT_PID:?"WAIT_PID 필요 (chain_luffy_now.sh PID)"}
LOG=all_log/chain_luffy_afterbackward.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF="$(dirname "$INIT")/training_conf.yaml"
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }

say "대기: chain(${WAIT_PID}) 가 backward(평가 포함) 마치고 retry-prm(3/4) 진입할 때까지"
PREEMPTED=0
while kill -0 "$WAIT_PID" 2>/dev/null; do
  if grep -q "▶ 3/4  retry-prm" all_log/chain_luffy_now.log 2>/dev/null; then
    PREEMPTED=1
    say "retry-prm 진입 감지 → 선점(backward 결과 보존). LUFFY-on-fix 를 앞으로."
    kill "$WAIT_PID" 2>/dev/null
    pkill -f "grpo_train.*retry.jsonl" 2>/dev/null
    pkill -f "smart_eval.py --alias rango-grpo-retry-prm" 2>/dev/null
    pkill -f "run_all.py --alias rango-grpo-retry-prm" 2>/dev/null
    pkill -f "run_thm.py run rango-grpo-retry-prm" 2>/dev/null
    pkill -f "tactic_gen_server.py.*rango-grpo-retry-prm" 2>/dev/null
    break
  fi
  sleep 60
done
[ "$PREEMPTED" = "1" ] || say "chain 자연 종료(선점 안 함) — 그대로 진행"
say "GPU 잔여 정리 대기(15s)"; sleep 15

say "▶ 1/3  LUFFY-on-fix @20→@40 (fix 어댑터 위에서 재학습) — 앞당김"
bash all_log/run_luffy.sh
say "◀ LUFFY-on-fix 완료"

say "▶ 2/3  retry-prm 재학습 + eval (뒤로 미룸)"
if [ ! -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && [ -s data/grpo_rollouts/retry.jsonl ]; then
  python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/retry.jsonl \
    --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 \
    --save_dir models/rango-grpo-retry-prm/adapter \
    --process --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-retry-prm/ 2>/dev/null
fi
[ -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && seval rango-grpo-retry-prm || say "  ★ retry-prm 학습 실패"

say "▶ 3/3  fix @180 (통계 확정)"
python3 scripts/smart_eval.py --alias rango-grpo-fix --stages 180 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"

say "===== 전체 완료 (LUFFY-on-fix 우선) ====="
grep -h "smart\] ■" all_log/luffy.log "$LOG" 2>/dev/null | tail -8
