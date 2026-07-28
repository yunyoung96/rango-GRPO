#!/bin/bash
# 작은 scale PPO (bigscale PPO 전 검증) — 다양한 critic 아키텍처 비교.
#   다른 기법(luffy/vine/backward 등)은 다 @20 게이트를 거쳤는데 PPO만 안 거치고 bigscale 직행했음 → 보정.
#   critic 4종: linear(현행) / mlp / mlp2 / tanh. 전부 on-fix(luffy.jsonl, gold 제외 on-policy).
#   흐름: 각 critic 학습 → @20 평가. @20 ≥ 11(우리 rango) 이면 @40 확장, 미달이면 접음.
set -u
LOG=all_log/small_ppo.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/rango-grpo-fix/adapter
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
ROLL=data/grpo_rollouts/luffy.jsonl     # on-fix 롤아웃(PPO는 off_policy=gold 자동 제외)
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

say "===== 작은 PPO — critic 아키텍처 4종 비교 (@20 게이트) 시작 ====="
[ -s "$ROLL" ] || { say "✗ $ROLL 없음"; exit 1; }

for ARCH in linear mlp mlp2 tanh sigmoid; do
  M="rango-grpo-ppo-$ARCH"
  say "▶ [$ARCH] PPO 학습 (fix 초기화, value_arch=$ARCH)"
  [ -f "models/$M/adapter/adapter_model.safetensors" ] || {
    python3 -m tactic_gen.grpo_train --rollouts "$ROLL" --model_name "$BASE" --init_adapter "$INIT" \
      --collator_conf "$CONF" --max_len 3072 --save_dir "models/$M/adapter" \
      --ppo --value_arch "$ARCH" --value_coef 0.5 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
    cpconf "models/$M"; }
  [ -f "models/$M/adapter/adapter_model.safetensors" ] || { say "  ✗ [$ARCH] 학습 실패, 스킵"; continue; }
  grep "value_loss\|\[ppo\] epoch\|\[grpo\] epoch" "$LOG" | tail -2 | sed 's/^/    /'

  # deploy alias 등록 필요 — run_thm.py 가 rango-grpo-ppo-* 를 fix 어댑터 서빙하도록 별칭 사용
  say "▶ [$ARCH] @20 평가 (게이트: 우리 rango 11)"
  python3 scripts/smart_eval.py --alias "$M" --stages 20 --workers 1 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"
  G=$(s20 "$M")
  if [ "$G" -ge 11 ]; then
    say "  ✓ [$ARCH] @20=$G ≥ 11 → @40 확장"
    python3 scripts/smart_eval.py --alias "$M" --stages 40 --workers 1 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"
  else
    say "  ✗ [$ARCH] @20=$G < 11 → 접음(@40 스킵)"
  fi
done

say "===== 작은 PPO 완료 — critic 4종 @20/@40 요약 ====="
for ARCH in linear mlp mlp2 tanh sigmoid; do
  G=$(s20 "rango-grpo-ppo-$ARCH")
  say "  $ARCH: @20=$G"
done
say "  (참조: 우리 rango-fix @20=11)"
