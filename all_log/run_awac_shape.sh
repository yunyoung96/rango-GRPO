#!/bin/bash
# 이론보장 2종 (작은 scale: luffy.jsonl 37그룹 재사용, on-fix):
#   awac      = AWAC/AWR exp(A/λ) 가중 BC — KL-제약 정책개선 닫힌 해(OOD 차단 보장)
#   goldshape = potential-based shaping — 최적정책 불변 보장, gold=Φ만, 순수 on-policy
# 흐름: 학습 → @20 게이트(우리 rango 11 이상이면) → @40 확장. 게이트 탈락 시 접음(가망없음 원칙).
set -u
LOG=all_log/awac_shape.log
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

say "===== AWAC + goldshape (small scale, @20게이트→@40) 시작 ====="
[ -s "$ROLL" ] || { say "✗ luffy.jsonl 없음"; exit 1; }

say "▶ 1a AWAC 학습 (luffy.jsonl, fix 초기화, λ=1.0)"
[ -f models/rango-grpo-awac/adapter/adapter_model.safetensors ] || {
  python3 -m tactic_gen.grpo_train --rollouts "$ROLL" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-grpo-awac/adapter \
    --awac --awac_lam 1.0 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1; cpconf models/rango-grpo-awac; }

say "▶ 1b goldshape 학습 (luffy.jsonl, fix 초기화, coef=0.3, kl0.04)"
[ -f models/rango-grpo-goldshape/adapter/adapter_model.safetensors ] || {
  python3 -m tactic_gen.grpo_train --rollouts "$ROLL" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-grpo-goldshape/adapter \
    --shape_gold --shape_coef 0.3 --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1; cpconf models/rango-grpo-goldshape; }

for A in awac goldshape; do
  M="rango-grpo-$A"
  [ -f "models/$M/adapter/adapter_model.safetensors" ] || { say "✗ $A 학습실패 스킵"; continue; }
  say "▶ 2 $A @20 평가 (게이트: 우리 rango 11)"
  python3 scripts/smart_eval.py --alias "$M" --stages 20 --workers 1 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"
  G=$(s20 "$M")
  if [ "$G" -ge 11 ]; then
    say "  ✓ $A @20=$G ≥ 11 → @40 확장"
    python3 scripts/smart_eval.py --alias "$M" --stages 40 --workers 1 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"
  else
    say "  ✗ $A @20=$G < 11 → 가망없음, 접음(@40 스킵)"
  fi
done
say "===== AWAC + goldshape 완료 ====="
grep -h "smart\] ■" "$LOG" | tail -4
