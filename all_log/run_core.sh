#!/bin/bash
# 핵심 파이프라인: prm(평가만, 이미 학습됨) → retry → fix @180.
# 각 학습마다 CONF/conf복사 정상. 학습 실패해도 다음으로 넘어감(멈추지 않음).
# 비교기준 = 우리 rango (@20=11 @40=15 @180=61).
set -u
LOG=all_log/core.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF="$(dirname "$INIT")/training_conf.yaml"
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
train(){ python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$2" --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 "${@:3}" >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$(dirname "$2")/" 2>/dev/null
  [ -f "$2/adapter_model.safetensors" ]; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }

# prm 평가가 아직 돌고 있으면 끝날 때까지 대기 (동시 GPU 방지)
while pgrep -f "smart_eval.py --alias rango-grpo-prm" >/dev/null 2>&1; do sleep 60; done
say "===== CORE 파이프라인 시작 (prm 평가 종료 확인) ====="
grep -h "smart\] ■ rango-grpo-prm" all_log/prm_eval.log 2>/dev/null | tail -2 | tee -a "$LOG"

# ── D. 재샘플링 (retry) — 근본 원인 처방 ─────────────────────────────
say "▶ retry 롤아웃 수집 (k=4)"
rm -f data/grpo_rollouts/retry.jsonl
python3 scripts/run_all.py --alias grpo-rollout-retry --start 200 --num 40 --timeout 900 --workers 2 \
  --description "재샘플링 롤아웃 k=4" >> "$LOG" 2>&1
if [ -s data/grpo_rollouts/retry.jsonl ]; then
  python3 - <<'PY' 2>&1 | tee -a "$LOG"
import json
g=[json.loads(l) for l in open('data/grpo_rollouts/retry.jsonl')]
dead=sum(1 for x in g if all(a['reward']<1 for a in x['attempts']))
print(f"  retry 롤아웃: {len(g)}그룹 dead {dead}({dead/max(len(g),1):.0%}) [비교: non-retry dead 69%]")
PY
  say "▶ retry 학습 (outcome)"; train data/grpo_rollouts/retry.jsonl models/rango-grpo-retry/adapter && seval rango-grpo-retry || say "  ★ retry 학습 실패"
  say "▶ retry-prm 학습"; train data/grpo_rollouts/retry.jsonl models/rango-grpo-retry-prm/adapter --process && seval rango-grpo-retry-prm || say "  ★ retry-prm 실패"
else say "  ★ retry 롤아웃 실패"; fi

# ── fix @180 — +4 의 통계적 확정 ─────────────────────────────────────
say "▶ fix @180 (통계 확정, 우리rango 61 기준)"
python3 scripts/smart_eval.py --alias rango-grpo-fix --stages 180 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"

say "===== CORE 완료 ====="
grep -h "smart\] ■" "$LOG" | tail -10 | tee -a "$LOG"
