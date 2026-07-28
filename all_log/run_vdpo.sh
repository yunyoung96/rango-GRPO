#!/bin/bash
# validity DPO (BFS-Prover 2502.03438 식): 같은 proof state 에서
#   chosen = Coq 가 받아들인 VALID tactic / rejected = Coq 에러를 낸 INVALID tactic
# ★ GRPO 대비 핵심: dead group(증명 못 찾은 78%)에서도 쌍이 나온다 — 실측 luffy.jsonl 37그룹 중
#   dead 20그룹에서 쌍 생성, 총 1049쌍. GRPO 는 이 구간에서 신호 0.
# 배우는 축이 다름: "증명을 찾아라"가 아니라 "깨진 tactic 을 내지 마라" → 탐색예산 낭비 감소.
# 흐름: 학습 → @20 게이트(우리 rango 11 이상) → @40 확장. 미달 시 접음(가망없음 원칙).
set -u
LOG=all_log/vdpo.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/rango-grpo-fix/adapter
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
ROLL=data/grpo_rollouts/luffy.jsonl     # on-fix 롤아웃(INVALID step 포함) 재사용
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

say "===== validity DPO (small scale, @20게이트→@40) 시작 ====="
[ -s "$ROLL" ] || { say "✗ $ROLL 없음"; exit 1; }

say "▶ 1 vdpo 학습 (luffy.jsonl, fix 초기화, β=0.1, micro_bsz=2(짝수·쌍정렬))"
[ -f models/rango-grpo-vdpo/adapter/adapter_model.safetensors ] || {
  python3 -m tactic_gen.grpo_train --rollouts "$ROLL" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-grpo-vdpo/adapter \
    --dpo --dpo_beta 0.1 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1; cpconf models/rango-grpo-vdpo; }

[ -f models/rango-grpo-vdpo/adapter/adapter_model.safetensors ] || { say "✗ 학습 실패 — 중단"; exit 1; }
say "  학습 완료. dpo_margin 추이:"; grep "dpo_margin" "$LOG" | tail -2 | sed 's/^/    /' | tee -a "$LOG"

say "▶ 2 vdpo @20 평가 (게이트: 우리 rango 11)"
python3 scripts/smart_eval.py --alias rango-grpo-vdpo --stages 20 --workers 1 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"
G=$(s20 rango-grpo-vdpo)
if [ "$G" -ge 11 ]; then
  say "  ✓ vdpo @20=$G ≥ 11 → @40 확장"
  python3 scripts/smart_eval.py --alias rango-grpo-vdpo --stages 40 --workers 1 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"
else
  say "  ✗ vdpo @20=$G < 11 → 가망없음, 접음(@40 스킵)"
fi
say "===== validity DPO 완료 ====="
grep -h "smart\] ■" "$LOG" | tail -2
