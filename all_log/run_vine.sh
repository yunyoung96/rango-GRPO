#!/bin/bash
# ★ VinePPO(2410.01679) @20→@40 — on-fix. 우리 실패진단(gold-state 전이실패)의 직교 처방.
#   backbone G개 + 각 on-policy state 에서 MC value(k분기) → step별 advantage=V(s')−V(s).
#   gold state 안 씀 → 분포 불일치 회피. sparse binary → step별 dense credit.
#   ※ 비쌈: state당 k_mc 롤아웃. group_size 4, k_mc 3, max_steps 12 로 절제. @20 먼저 보고 판단.
# 비교기준 = 우리 rango(11/15) + fix(13/19). published 비교 안 함.
set -u
LOG=all_log/vine.log
WORKERS=${WORKERS:-2}
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/rango-grpo-fix/adapter        # fix 위에서 이어 학습
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }

say "===== VinePPO @20→@40 (on-fix) 시작 ====="

say "1) 롤아웃 수집 (fix 정책, backbone 4 + state별 MC k=3) — ★ 오래 걸림"
if [ ! -s data/grpo_rollouts/vine.jsonl ]; then
  rm -f data/grpo_rollouts/vine.jsonl
  python3 scripts/run_all.py --alias grpo-rollout-vine --start 200 --num 40 \
    --timeout 1200 --workers "$WORKERS" \
    --description "VinePPO 롤아웃(MC value, on-fix)" >> "$LOG" 2>&1
fi
[ -s data/grpo_rollouts/vine.jsonl ] || { say "★ 롤아웃 수집 실패 — 중단"; exit 1; }

say "2) ★ 효과 측정 — adv_vine 분포"
python3 - <<'PY' 2>&1 | tee -a "$LOG"
import json
g=[json.loads(l) for l in open('data/grpo_rollouts/vine.jsonl')]
advs=[s['adv_vine'] for x in g for a in x['attempts'] for s in a['steps'] if 'adv_vine' in s]
nz=[a for a in advs if abs(a)>1e-6]
import statistics as st
print(f"  그룹 {len(g)} | step {len(advs)} | 비영 advantage {len(nz)}/{len(advs)} ({len(nz)/max(len(advs),1):.0%})")
if nz: print(f"  adv_vine: 평균 {st.mean(nz):+.3f}  범위 [{min(nz):+.2f},{max(nz):+.2f}]  양수 {sum(1 for a in nz if a>0)}/{len(nz)}")
print("  (VinePPO 는 dead group 스킵 대신 step별 MC credit — 대부분 step 에 신호)")
PY

say "3) 학습 (fix 초기화, --vine)"
[ ! -f models/rango-grpo-vine/adapter/adapter_model.safetensors ] && \
  python3 -m tactic_gen.grpo_train \
    --rollouts data/grpo_rollouts/vine.jsonl \
    --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 \
    --save_dir models/rango-grpo-vine/adapter \
    --vine --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1
cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-vine/ 2>/dev/null

say "4) 평가 (smart_eval @20→@40)"
[ -f models/rango-grpo-vine/adapter/adapter_model.safetensors ] && seval rango-grpo-vine || say "★ vine 학습 실패"

say "===== VinePPO 완료 ====="
grep -h "smart\] ■" "$LOG" 2>/dev/null | tail -4
