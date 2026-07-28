#!/bin/bash
# DAPO / VAPO 작은 scale 학습(@20 게이트). GRPO/PPO 계열과 같은 통합 로거([metrics])로 비교.
#   DAPO(2503.14476) = GRPO + clip-higher + token-level loss + KL제거(+ dynamic sampling은 롤아웃단).
#     → --dapo --clip_eps_high 0.28. critic 없음(그룹 baseline).
#   VAPO(2504.05118) = PPO + value-pretraining + clip-higher. critic 있음(우린 mlp head).
#     → --ppo --value_arch mlp --value_pretrain 2 --clip_eps_high 0.28.
#   전부 on-fix(luffy.jsonl, gold 제외 on-policy). 학습 로그의 [metrics] 로 문제셋 진단.
set -u
LOG=all_log/dapo_vapo.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/rango-grpo-fix/adapter
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
ROLL=data/grpo_rollouts/luffy.jsonl
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }
s20(){ python3 -c "
import json
try:
  r=json.load(open('all_results/smart_$1/summary.json'))['results']
  import sys; sys.path.insert(0,'src')
  from coqstoq import Split,get_theorem_list
  from pathlib import Path
  cc=[i for i,t in enumerate(get_theorem_list(Split.TEST,Path('CoqStoq'))) if t.project.dir_name=='compcert']
  rm={x['idx']:x for x in r}; dn=[i for i in cc[:20] if i in rm]
  print(sum(1 for i in dn if rm[i].get('success')))
except Exception: print(0)"; }
gate(){ local M="$1"; local G=$(s20 "$M")
  if [ "$G" -ge 11 ]; then say "  ✓ $M @20=$G ≥11 → @40"; python3 scripts/smart_eval.py --alias "$M" --stages 40 --workers 1 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"
  else say "  ✗ $M @20=$G <11 → 접음"; fi; }

say "===== DAPO / VAPO 작은 scale (@20 게이트) 시작 ====="
[ -s "$ROLL" ] || { say "✗ $ROLL 없음"; exit 1; }

# ── DAPO ──
M=rango-grpo-dapo-small
say "▶ DAPO 학습 (--dapo --clip_eps_high 0.28)"
[ -f models/$M/adapter/adapter_model.safetensors ] || {
  python3 -m tactic_gen.grpo_train --rollouts "$ROLL" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir models/$M/adapter \
    --dapo --clip_eps_high 0.28 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1; cpconf models/$M; }
grep "\[metrics\]" "$LOG" | tail -2 | sed 's/^/    /'
[ -f models/$M/adapter/adapter_model.safetensors ] && { say "▶ DAPO @20"; python3 scripts/smart_eval.py --alias $M --stages 20 --workers 1 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"; gate $M; }

# ── VAPO ──
M=rango-grpo-vapo
say "▶ VAPO 학습 (--ppo --value_arch mlp --value_pretrain 2 --clip_eps_high 0.28)"
[ -f models/$M/adapter/adapter_model.safetensors ] || {
  python3 -m tactic_gen.grpo_train --rollouts "$ROLL" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir models/$M/adapter \
    --ppo --value_arch mlp --value_pretrain 2 --clip_eps_high 0.28 --value_coef 0.5 \
    --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1; cpconf models/$M; }
grep "\[metrics\]\|value-pretrain" "$LOG" | tail -3 | sed 's/^/    /'
[ -f models/$M/adapter/adapter_model.safetensors ] && { say "▶ VAPO @20"; python3 scripts/smart_eval.py --alias $M --stages 20 --workers 1 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"; gate $M; }

say "===== DAPO/VAPO 완료 ====="
say "  DAPO @20=$(s20 rango-grpo-dapo-small) | VAPO @20=$(s20 rango-grpo-vapo) | (rango-fix @20=11)"
say "  [metrics] 진단 시계열: grep '\\[metrics\\]' all_log/dapo_vapo.log"
