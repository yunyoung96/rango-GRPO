#!/bin/bash
# 강화 invertible(_targeted_cands v2: 타입-지향 결정절차 case-split) A/B 검증.
# plain cascade-s0 vs 강화-hybrid, 34정리(invauto), GPU0, 전체CPU. 개선되면 train-300 확장.
set -u
LOG=all_log/hybridab.log
IDX=data/compcert_bs2_invauto_idx.txt
GPU=0; W=12
runab(){  # $1=hybrid(0/1) $2=outname
  export SUBGOAL_CURRICULUM=data/curriculum/empty.json
  export SUBGOAL_OUT=data/grpo_rollouts/$2.jsonl
  export SUBGOAL_POLICY=models/rango-grpo-cascade-s0/adapter
  export SUBGOAL_SKIP_S0=0 SUBGOAL_REWARD=0 SUBGOAL_GS=6 SUBGOAL_MAXSTEPS=12 SUBGOAL_HYBRID=$1
  rm -f data/grpo_rollouts/$2.jsonl
  taskset -c 0-127 python3 scripts/run_all.py --alias grpo-rollout-subgoal --idx-file "$IDX" \
    --timeout 120 --gpus "$GPU" --workers "$W" >> "$LOG" 2>&1
}
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
say "════ A/B: plain vs 강화-hybrid cascade-s0 (34정리, G6 steps12, GPU$GPU w$W) ════"
say "▶ [1/2] plain (HYBRID=0)"; runab 0 ab_plain
say "▶ [2/2] 강화-hybrid (HYBRID=1)"; runab 1 ab_hybrid
say "════ 결과 ════"
python3 -c "
import json,collections
def cr(f):
    try: rows=[json.loads(l) for l in open(f) if l.strip()]
    except: return 0,0
    per=collections.defaultdict(int)
    for r in rows:
        per[r['theorem']] |= (1 if any(a['reward']>=1 for a in r['attempts']) else 0)
    return sum(per.values()), len(per)
for nm,f in [('plain cascade-s0','data/grpo_rollouts/ab_plain.jsonl'),('강화-hybrid','data/grpo_rollouts/ab_hybrid.jsonl')]:
    c,n=cr(f); print(f'  {nm:20s}: {c}/{n} 닫힘 ({100*c//max(n,1)}%)')
" 2>&1 | tee -a "$LOG"
say "════ [hybridab 완료] ════"
