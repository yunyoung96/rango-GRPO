#!/bin/bash
# 마스터 v2: CompCert 기반 GRPO 먼저, cross-repo 맨 뒤. 롤아웃 오염 제거.
# 비교기준 = 우리 rango (@20=11, @40=15). @20 < 10 이면 @40 확장 안 함(smart_eval).
# 모든 학습: instruct 베이스 + length 보정. 평가: smart_eval 에스컬레이션(재사용/덮어쓰기).
set -u
LOG=all_log/master.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }
CONF="$(dirname "$INIT")/training_conf.yaml"
# ★ 학습 후 training_conf/lm-example-conf 복사 필수 — 없으면 서버 로딩 hang.
train(){ python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 \
    --save_dir "$2" --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 "${@:3}" >> "$LOG" 2>&1
  local mdir; mdir="$(dirname "$2")"
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$mdir/" 2>/dev/null; }

say "===== MASTER v2 시작 (CompCert 먼저) ====="

# ── B/C. base 정정 + PRM (round1-fixed 는 이미 정제됨) ────────────────
say "▶ B. base 정정 GRPO (rango-grpo-fix)"
[ ! -f models/rango-grpo-fix/adapter/adapter_model.safetensors ] && \
  train data/grpo_rollouts/round1-fixed.jsonl models/rango-grpo-fix/adapter
seval rango-grpo-fix

say "▶ C. PRM-GRPO (rango-grpo-prm)"
[ ! -f models/rango-grpo-prm/adapter/adapter_model.safetensors ] && \
  train data/grpo_rollouts/round1-fixed.jsonl models/rango-grpo-prm/adapter --process
seval rango-grpo-prm

# ── D. 재샘플링 (retry) ──────────────────────────────────────────────
say "▶ D. 재샘플링 롤아웃 수집 (k=4, 깨끗한 시작)"
rm -f data/grpo_rollouts/retry.jsonl
python3 scripts/run_all.py --alias grpo-rollout-retry --start 200 --num 40 --timeout 900 --workers 2 \
  --description "재샘플링 롤아웃 k=4" >> "$LOG" 2>&1
if [ -s data/grpo_rollouts/retry.jsonl ]; then
  python3 - <<'PY' 2>&1 | tee -a "$LOG"
import json
g=[json.loads(l) for l in open('data/grpo_rollouts/retry.jsonl')]
att=[a for x in g for a in x['attempts']]
dead=sum(1 for x in g if all(a['reward']<1 for a in x['attempts']))
print(f"  retry 롤아웃: {len(g)}그룹 dead {dead} ({dead/max(len(g),1):.0%}) [기존 non-retry 는 dead 69%]")
PY
  train data/grpo_rollouts/retry.jsonl models/rango-grpo-retry/adapter
  train data/grpo_rollouts/retry.jsonl models/rango-grpo-retry-prm/adapter --process
  seval rango-grpo-retry
  seval rango-grpo-retry-prm
else say "  ★ retry 수집 실패"; fi

# ── E. progress critic (LeanProgress) ────────────────────────────────
say "▶ E. progress critic α sweep"
[ ! -f models/progress_critic/head.pt ] && \
  python3 scripts/train_progress_critic.py --data data/progress/train.jsonl \
    --save_dir models/progress_critic --max_samples 200000 --epochs 1 --bsz 8 >> "$LOG" 2>&1
if [ -f models/progress_critic/head.pt ]; then
  seval rango-progress-a0; seval rango-progress; seval rango-progress-a05; seval rango-progress-a10
else say "  ★ critic 학습 실패"; fi

# ── A. cross-repo (맨 뒤, 오래 걸림) ─────────────────────────────────
say "▶ A. cross-repo GRPO (non-CompCert 300개, 맨 뒤)"
rm -f data/grpo_rollouts/cross.jsonl
python3 scripts/run_all.py --alias grpo-rollout-cross --idx-file data/crossrepo/train_idx.txt \
  --timeout 600 --workers 2 --description "cross-repo rollout" >> "$LOG" 2>&1
if [ -s data/grpo_rollouts/cross.jsonl ]; then
  python3 - <<'PY' 2>&1 | tee -a "$LOG"
import json
g=[json.loads(l) for l in open('data/grpo_rollouts/cross.jsonl')]
att=[a for x in g for a in x['attempts']]; su=sum(1 for a in att if a['reward']>=1)
dead=sum(1 for x in g if all(a['reward']<1 for a in x['attempts']))
sig=len(g)-dead-sum(1 for x in g if all(a['reward']>=1 for a in x['attempts']))
print(f"  cross 롤아웃: {len(g)}그룹 시도성공 {su}/{len(att)}({su/max(len(att),1):.0%}) 신호그룹 {sig}({sig/max(len(g),1):.0%}) [CompCert 27%]")
PY
  train data/grpo_rollouts/cross.jsonl models/rango-grpo-cross/adapter
  train data/grpo_rollouts/cross.jsonl models/rango-grpo-cross-prm/adapter --process
  seval rango-grpo-cross
  seval rango-grpo-cross-prm
else say "  ★ cross 수집 실패"; fi

say "===== MASTER 완료 ====="
echo "=== 최종 요약 (우리rango @20=11 @40=15 기준) ===" | tee -a "$LOG"
grep -h "smart\] ■" "$LOG" | tail -30 | tee -a "$LOG"
