#!/bin/bash
# opener-tac 최종모델 rand200 평가 (opener 없이, executor 단독) + subgoal baseline 대조. GPU1 전용.
cd /app/coq-modeling || exit 1
LOG=all_log/eval_otac.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
pkill -9 -f 'planner_server.py' 2>/dev/null; pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 5
FINAL=models/rango-opener-tac-grpo/adapter
SUBG=models/rango-grpo-subgoal-bs2/adapter
RAND=data/compcert_bs2_rand200_idx.txt
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'),'(',round(100*d.get('success',0)/max(d.get('done',1),1),1),'%)')" 2>/dev/null; }
wait_g1(){ local w=0; while :; do f=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i 1); f=${f:-0}; [ "$f" -ge 20000 ] && break; [ $w -ge 3600 ] && break; sleep 20; w=$((w+20)); done; }

# E1: opener-tac 최종모델 (opener 없이)
wait_g1
say "E1: opener-tac 최종모델 rand200 (opener 없이, GPU1 w8)"
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$FINAL CUDA_VISIBLE_DEVICES=1 python3 scripts/run_all.py \
  --alias rango-grpo --idx-file "$RAND" --timeout 300 --gpus 1 --workers 8 \
  --out all_results/otac_final --description "opener-tac final no-opener" >> "$LOG" 2>&1
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 3
say "E1 opener-tac 최종: $(sumline all_results/otac_final)"

# E2: subgoal 모델 baseline (init 대조, opener 없이)
say "E2: subgoal모델(init 대조) rand200"
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$SUBG CUDA_VISIBLE_DEVICES=1 python3 scripts/run_all.py \
  --alias rango-grpo --idx-file "$RAND" --timeout 300 --gpus 1 --workers 8 \
  --out all_results/otac_subgoal_base --description "subgoal base" >> "$LOG" 2>&1
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
say "E2 subgoal base: $(sumline all_results/otac_subgoal_base)"
say "=== EVAL 완료 EVALOTAC_DONE ==="
python3 - >> "$LOG" 2>&1 <<'PY'
import json,os
def g(p):
    p=f'all_results/{p}/summary.json'
    if os.path.exists(p): d=json.load(open(p));return f"{d.get('success')}/{d.get('done')} = {100*d.get('success',0)/max(d.get('done',1),1):.1f}%"
    return "(없음)"
print("\n===== opener-tac rand200@300s (opener 없이) =====")
print("  opener-tac 최종(SFT-opener→롤아웃→GRPO):", g('otac_final'))
print("  subgoal 모델 (init 대조)              :", g('otac_subgoal_base'))
print("  (참고: plain SFT→GRPO 37.5%, leaf-subgoal 37.0%)")
PY
