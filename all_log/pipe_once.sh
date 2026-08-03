#!/bin/bash
# opener-ONCE 파이프라인: opener는 '맨 처음 goal 열 때만'(pre-loop 1회) + hedge(홀수 seed 순수 rango).
#   PLANNER_EVERY 제거 → 첫 분해만 opener가, 이후는 모델이 auto/lia로 닫음.
#   Stage A 롤아웃(100,gold-SFT) → mixed 분석 → Stage B GRPO → Stage C test(opener 없이) + gold-SFT baseline.
cd /app/coq-modeling || exit 1
LOG=all_log/pipe_once.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
# 기존 eval/서버 정리
pkill -9 -f 'eval_noopener.sh' 2>/dev/null
pkill -9 -f 'run_all.py' 2>/dev/null
pkill -9 -f 'run_thm.py' 2>/dev/null
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
pkill -9 -f 'planner_server.py' 2>/dev/null
sleep 8
say "기존 정리. GPU=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader -i 1)"
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
QWEN=Qwen/Qwen2.5-Coder-7B-Instruct
GOLD=models/rango-grpo-bs2-sft/adapter
OPENER=models/opener-7b-sub/adapter
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
FINAL=models/rango-opener-once-grpo
ROLL_IDX=/tmp/roll100_idx.txt
RAND=data/compcert_bs2_rand200_idx.txt
ROLL=data/grpo_rollouts/opener_once_pipe.jsonl
PORT=8130; URL=http://127.0.0.1:$PORT
SRVLOG=all_log/opener_server_fp.log
start_srv(){ pkill -9 -f 'planner_server.py' 2>/dev/null; sleep 3; : > "$SRVLOG"
  HF_HUB_OFFLINE=1 PLANNER_ADAPTER=$OPENER PLANNER_OPENER=1 CUDA_VISIBLE_DEVICES=1 \
    python3 src/model_deployment/planner_server.py "$QWEN" "$PORT" >> "$SRVLOG" 2>&1 &
  SRV=$!; for i in $(seq 1 90); do grep -q READY "$SRVLOG" 2>/dev/null && break; sleep 5; done
  grep -q READY "$SRVLOG" 2>/dev/null && say "  opener 서버 READY" || say "  ✗ opener 서버 실패"; }
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'),'/',d.get('total'),'(',round(100*d.get('success',0)/max(d.get('done',1),1),1),'%)')" 2>/dev/null; }

# ── Stage A: opener-once(hedge) 롤아웃 ──
rm -f "$ROLL"
say "=== Stage A: opener-once 롤아웃 (100 theorem, pre-loop 1회+hedge, executor=gold-SFT, w4) ==="
start_srv
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$GOLD PLANNER_FIRST_URL=$URL PLANNER_HEDGE=1 ROLLOUT_OUT=$ROLL ROLLOUT_RETRY=1 \
  CUDA_VISIBLE_DEVICES=1 python3 scripts/run_all.py --alias grpo-rollout-pf --idx-file "$ROLL_IDX" --timeout 400 --gpus 1 --workers 8 >> "$LOG" 2>&1
kill -9 "$SRV" 2>/dev/null; pkill -9 -f 'planner_server.py' 2>/dev/null; pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 5
python3 - >> "$LOG" 2>&1 <<'PY'
import json
try: rows=[json.loads(l) for l in open('data/grpo_rollouts/opener_once_pipe.jsonl')]
except: rows=[]
a=m=d=0; ts=ta=0
for g in rows:
    ns=sum(1 for x in g['attempts'] if x.get('reward',0)>0); ta+=len(g['attempts']); ts+=ns
    if ns==0:d+=1
    elif ns==len(g['attempts']):a+=1
    else:m+=1
n=max(len(rows),1)
print(f"[★opener-once mixed] {len(rows)}그룹: all {a}, mixed {m}, dead {d} → mixed {100*m/n:.0f}% (opener-every는 10%였음), attempt성공 {100*ts/max(ta,1):.1f}%")
PY
say "Stage A 완료 — mixed 분석 로그 위 참조"

# ── Stage B: GRPO(init=gold-SFT) ──
if [ -s "$ROLL" ]; then
  say "=== Stage B: GRPO (init=gold-SFT → $FINAL) ==="
  HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=1 python3 -m tactic_gen.grpo_train \
    --rollouts "$ROLL" --model_name "$BASE" --init_adapter "$GOLD" --collator_conf "$CONF" \
    --max_len 3072 --save_dir "$FINAL/adapter" --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$FINAL/" 2>/dev/null
  say "Stage B 완료: $([ -f "$FINAL/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)"
fi

# ── Stage C: test (opener 없이) — 최종 vs gold-SFT ──
if [ -f "$FINAL/adapter/adapter_model.safetensors" ]; then
  say "=== Stage C: rand200@300s (opener 없이) ==="
  HF_HUB_OFFLINE=1 EXEC_ADAPTER=$FINAL/adapter CUDA_VISIBLE_DEVICES=1 \
    python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" --timeout 300 --gpus 1 --workers 12 \
    --out all_results/once_final --description "opener-once final no-opener" >> "$LOG" 2>&1
  pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 3
  say "  once_final(opener없이) rand200: $(sumline all_results/once_final)"
  HF_HUB_OFFLINE=1 EXEC_ADAPTER=$GOLD CUDA_VISIBLE_DEVICES=1 \
    python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" --timeout 300 --gpus 1 --workers 12 \
    --out all_results/osg_goldsft --description "gold-SFT baseline" >> "$LOG" 2>&1
  pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
  say "  gold-SFT baseline rand200: $(sumline all_results/osg_goldsft)"
fi
say "=== 완료 ONCE_DONE ==="
