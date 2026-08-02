#!/bin/bash
# once-v2 GRPO executor를 @600s·executor단독으로 rand200 eval (=@600s 리그와 동등 비교).
#   비교대상: SFT→GRPO 37.5% / leaf-subgoal 37.0% / plain @600 33.5% (전부 executor단독 @600).
cd /app/coq-modeling || exit 1
LOG=all_log/once_v2_600.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
FINAL=models/rango-opener-once-v2-grpo/adapter
RAND=data/compcert_bs2_rand200_idx.txt
OUT=all_results/once_v2_600
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'),'(',round(100*d.get('success',0)/max(d.get('done',1),1),1),'%)')" 2>/dev/null; }
# test=w2. gpu 2개 쓰되 gpu0_foreign이면 gpu1만.
wait_gpus(){ local need=${1:-14000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  local g=""; [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ]&&g="0"; [ "$f1" -ge "$need" ]&&g="${g:+$g,}1"
  [ -n "$g" ]&&{ echo "$g";return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 20;w=$((w+20)); done; }

GPUS=$(wait_gpus 14000); say "rand200 @600s w2 executor단독 (GPU $GPUS) — once-v2 GRPO executor"
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$FINAL python3 scripts/run_all.py --alias rango-grpo \
  --idx-file "$RAND" --timeout 600 --gpus "$GPUS" --workers 2 \
  --out "$OUT" --description "once-v2 @600s executor-only (fair vs 37.5%)" >> "$LOG" 2>&1
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
say "once-v2 @600s 최종: $(sumline $OUT)  (비교: SFT→GRPO 37.5% / leaf-subgoal 37.0% / plain@600 33.5%)"
say "=== ONCEV2_600_DONE ==="
