#!/bin/bash
# opener-once Stage A 완료 후: 같은 roll100에 plain-SFT(opener 없이) 롤아웃 → 매칭 mixed 비교 → GRPO/test.
cd /app/coq-modeling || exit 1
LOG=all_log/after_stageA.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
GOLD=models/rango-grpo-bs2-sft/adapter
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
FINAL=models/rango-opener-once-grpo
ROLL_IDX=/tmp/roll100_idx.txt
RAND=data/compcert_bs2_rand200_idx.txt
ONCE=data/grpo_rollouts/opener_once_pipe.jsonl
PLAIN=data/grpo_rollouts/plain_sft_pipe.jsonl
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'),'(',round(100*d.get('success',0)/max(d.get('done',1),1),1),'%)')" 2>/dev/null; }

say "opener-once Stage A 완료 대기중..."
while ! grep -q "Stage A 완료" all_log/pipe_once.log 2>/dev/null; do sleep 20; done
say "Stage A 감지 → pipe_once 후속(auto-GRPO/test) 중단, plain-SFT 비교 먼저."
pkill -9 -f 'pipe_once.sh' 2>/dev/null; pkill -9 -f 'grpo_train' 2>/dev/null
pkill -9 -f 'run_all.py' 2>/dev/null; pkill -9 -f 'run_thm.py' 2>/dev/null
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; pkill -9 -f 'planner_server.py' 2>/dev/null
sleep 8

# 1) plain-SFT 롤아웃 (같은 roll100, opener 없이, w12)
rm -f "$PLAIN"
say "=== plain-SFT 롤아웃 (roll100, opener 없이, gold-SFT, w12) ==="
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$GOLD ROLLOUT_OUT=$PLAIN ROLLOUT_RETRY=1 CUDA_VISIBLE_DEVICES=1 \
  python3 scripts/run_all.py --alias grpo-rollout-pf --idx-file "$ROLL_IDX" --timeout 400 --gpus 1 --workers 12 >> "$LOG" 2>&1
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 5

# 2) 매칭 비교 (정리 statement=proof_script 로 매칭 — theorem_id는 프로세스별 hash라 불가)
python3 - >> "$LOG" 2>&1 <<'PY'
import json,os
def load(f): return [json.loads(l) for l in open(f)] if os.path.exists(f) else []
def stats(rows):
    byt={}; a=m=d=0; ts=ta=0
    for g in rows:
        atts=g.get('attempts',[])
        ns=sum(1 for x in atts if x.get('reward',0)>0); ta+=len(atts); ts+=ns
        try: stmt=atts[0]['steps'][0]['example'].get('proof_script','')
        except: stmt=str(g.get('theorem'))
        cat='all' if ns==len(atts) and atts else ('dead' if ns==0 else 'mixed')
        byt[stmt]=cat
        if ns==0:d+=1
        elif atts and ns==len(atts):a+=1
        else:m+=1
    return dict(n=len(rows),a=a,m=m,d=d,ts=ts,ta=ta,byt=byt)
once=stats(load('data/grpo_rollouts/opener_once_pipe.jsonl'))
plain=stats(load('data/grpo_rollouts/plain_sft_pipe.jsonl'))
common=set(once['byt'])&set(plain['byt'])
def mr(s,keys): mm=sum(1 for k in keys if s['byt'][k]=='mixed'); return mm
om=mr(once,common); pm=mr(plain,common)
print("===== plain-SFT vs opener-once (같은 100 theorem) =====")
print(f"  [전체] opener-once: mixed {once['m']}/{once['n']}={100*once['m']/max(once['n'],1):.0f}%, attempt {100*once['ts']/max(once['ta'],1):.1f}%")
print(f"  [전체] plain-SFT  : mixed {plain['m']}/{plain['n']}={100*plain['m']/max(plain['n'],1):.0f}%, attempt {100*plain['ts']/max(plain['ta'],1):.1f}%")
print(f"  [★매칭 {len(common)}개] opener-once mixed {100*om/max(len(common),1):.0f}% vs plain-SFT mixed {100*pm/max(len(common),1):.0f}%")
print(f"  → opener-once가 plain 대비 mixed {'▲' if om>pm else '▼'} ({om-pm:+d}개)")
PY
say "=== ★비교 완료 COMPARE_DONE (로그 위 참조) ==="

# 3) 이어서 opener-once GRPO + test
if [ ! -f "$FINAL/adapter/adapter_model.safetensors" ]; then
  say "=== GRPO (opener-once, init=gold-SFT) ==="
  HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=1 python3 -m tactic_gen.grpo_train \
    --rollouts "$ONCE" --model_name "$BASE" --init_adapter "$GOLD" --collator_conf "$CONF" \
    --max_len 3072 --save_dir "$FINAL/adapter" --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$FINAL/" 2>/dev/null
  say "GRPO 완료: $([ -f "$FINAL/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)"
fi
if [ -f "$FINAL/adapter/adapter_model.safetensors" ]; then
  say "=== test rand200 (opener 없이) ==="
  HF_HUB_OFFLINE=1 EXEC_ADAPTER=$FINAL/adapter CUDA_VISIBLE_DEVICES=1 python3 scripts/run_all.py \
    --alias rango-grpo --idx-file "$RAND" --timeout 300 --gpus 1 --workers 12 --out all_results/once_final >> "$LOG" 2>&1
  pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 3
  say "  once_final rand200: $(sumline all_results/once_final)"
  HF_HUB_OFFLINE=1 EXEC_ADAPTER=$GOLD CUDA_VISIBLE_DEVICES=1 python3 scripts/run_all.py \
    --alias rango-grpo --idx-file "$RAND" --timeout 300 --gpus 1 --workers 12 --out all_results/osg_goldsft >> "$LOG" 2>&1
  pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
  say "  gold-SFT rand200: $(sumline all_results/osg_goldsft)"
fi
say "=== 전체 완료 AFTER_DONE ==="
