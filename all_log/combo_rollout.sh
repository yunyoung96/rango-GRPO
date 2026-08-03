#!/bin/bash
# ★조합 검증: subgoal-학습 모델(rango-grpo-subgoal-bs2, 닫기 개선) + opener-once(열기 개선).
#   두 벽 동시. 100 theorem 롤아웃 → mixed + closing 실패위치 분석(닫기가 나아지나?).
cd /app/coq-modeling || exit 1
LOG=all_log/combo_rollout.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
pkill -9 -f 'run_all.py' 2>/dev/null; pkill -9 -f 'run_thm.py' 2>/dev/null
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; pkill -9 -f 'planner_server.py' 2>/dev/null
sleep 8
QWEN=Qwen/Qwen2.5-Coder-7B-Instruct
SUBGOAL=models/rango-grpo-subgoal-bs2/adapter
OPENER=models/opener-7b-sub/adapter
ROLL=data/grpo_rollouts/combo_subgoal_opener.jsonl
ROLL_IDX=/tmp/roll100_idx.txt
PORT=8130; URL=http://127.0.0.1:$PORT; SRVLOG=all_log/opener_server_fp.log
say "opener 서버 기동(opener-7b-sub)"
: > "$SRVLOG"
HF_HUB_OFFLINE=1 PLANNER_ADAPTER=$OPENER PLANNER_OPENER=1 CUDA_VISIBLE_DEVICES=1 \
  python3 src/model_deployment/planner_server.py "$QWEN" "$PORT" >> "$SRVLOG" 2>&1 &
SRV=$!; for i in $(seq 1 90); do grep -q READY "$SRVLOG" 2>/dev/null && break; sleep 5; done
say "opener READY=$(grep -q READY $SRVLOG && echo Y || echo N)"
rm -f "$ROLL"
say "=== 조합 롤아웃: executor=subgoal-학습모델, opener-once(hedge), 100 theorem, w8 ==="
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$SUBGOAL PLANNER_FIRST_URL=$URL PLANNER_HEDGE=1 ROLLOUT_OUT=$ROLL ROLLOUT_RETRY=1 \
  CUDA_VISIBLE_DEVICES=1 python3 scripts/run_all.py --alias grpo-rollout-pf --idx-file "$ROLL_IDX" --timeout 400 --gpus 1 --workers 8 >> "$LOG" 2>&1
kill -9 "$SRV" 2>/dev/null; pkill -9 -f 'planner_server.py' 2>/dev/null; pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 5
say "롤아웃 완료. 분석:"
python3 - >> "$LOG" 2>&1 <<'PY'
import json,os,re,statistics
from collections import defaultdict
def load(f): return [json.loads(l) for l in open(f)] if os.path.exists(f) else []
combo=load('data/grpo_rollouts/combo_subgoal_opener.jsonl')
def kw(t):
    m=re.match(r'\s*([A-Za-z_.]+)',t or ''); return m.group(1) if m else ''
a=m=d=0;ts=ta=0
for g in combo:
    atts=g.get('attempts',[]); ns=sum(1 for x in atts if x.get('reward',0)>0); ta+=len(atts); ts+=ns
    if ns==0:d+=1
    elif atts and ns==len(atts):a+=1
    else:m+=1
n=max(len(combo),1)
print(f"★[조합: subgoal모델+opener-once] {len(combo)}그룹")
print(f"   attempt 성공 {ts}/{ta}={100*ts/max(ta,1):.1f}% | 정리≥1 {a+m}/{len(combo)}={100*(a+m)/n:.0f}% | mixed {m}({100*m/n:.0f}%) dead {d}")
print(f"   비교: gold-SFT+opener-once=17.4%/33%/mixed29%, plain=19.5%/34%, opener-every=12.6%/19%")
# closing 실패위치
fp=[];clo=opn=0
for g in combo:
    for at in g.get('attempts',[]):
        if sum(1 for x in [at] if x.get('reward',0)>0): pass
        st=at.get('steps',[])
        fi=None
        for i,s in enumerate(st):
            if 'INVALID' in str(s.get('result','')): fi=i;break
        if fi is not None:
            fp.append(fi); (clo:=clo+1) if fi>1 else (opn:=opn+1)
if fp:
    print(f"   INVALID 첫위치 중앙값 {statistics.median(fp):.0f} | opening(≤1) {opn} vs closing(≥2) {clo} → {'closing 여전' if clo>opn else 'opening'}")
PY
say "=== COMBO_DONE ==="
