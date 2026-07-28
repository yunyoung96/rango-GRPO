#!/bin/bash
set -u
LOG=all_log/hybridab.log
IDX=data/compcert_bs2_invauto_idx.txt
runab(){  # $1=hybrid(0/1) $2=outname
  export SUBGOAL_CURRICULUM=data/curriculum/empty.json
  export SUBGOAL_OUT=data/grpo_rollouts/$2.jsonl
  export SUBGOAL_POLICY=models/rango-grpo-cascade-s0/adapter
  export SUBGOAL_SKIP_S0=0 SUBGOAL_REWARD=0 SUBGOAL_GS=6 SUBGOAL_MAXSTEPS=12 SUBGOAL_HYBRID=$1
  rm -f data/grpo_rollouts/$2.jsonl
  python3 scripts/run_all.py --alias grpo-rollout-subgoal --idx-file "$IDX" --timeout 80 --gpus 1 --workers 4 >> "$LOG" 2>&1
}
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
say "════ A/B: plain vs 하이브리드 cascade (34정리 완전체, G6 steps12) ════"
say "▶ [1/2] plain (HYBRID=0)"; runab 0 ab_plain
say "▶ [2/2] hybrid (HYBRID=1)"; runab 1 ab_hybrid
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
for nm,f in [('plain cascade','data/grpo_rollouts/ab_plain.jsonl'),('hybrid(inv+auto)','data/grpo_rollouts/ab_hybrid.jsonl')]:
    c,n=cr(f); print(f'  {nm:20s}: {c}/{n} 닫힘 ({100*c//max(n,1)}%)')
" 2>&1 | tee -a "$LOG"
say "════ [hybridab 완료] ════"
