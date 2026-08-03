#!/bin/bash
# Stage C 가속판 (eval w2→w4, resume). A/B 완료(rango-opener-sub-grpo 저장됨)라 C만 다시.
cd /app/coq-modeling || exit 1
LOG=all_log/stageC.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
# 0) 기존 파이프라인/느린 eval/서버 정리(고아 tactic_gen_server 포함)
pkill -9 -f 'full_pipeline.sh' 2>/dev/null
pkill -9 -f 'run_all.py' 2>/dev/null
pkill -9 -f 'run_thm.py' 2>/dev/null
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
pkill -9 -f 'planner_server.py' 2>/dev/null
sleep 8
say "기존 정리 완료. GPU=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader -i 1)"
QWEN=Qwen/Qwen2.5-Coder-7B-Instruct
OPENER=models/opener-7b-sub/adapter
FINAL=models/rango-opener-sub-grpo/adapter
GOLD=models/rango-grpo-bs2-sft/adapter
RAND=data/compcert_bs2_rand200_idx.txt
PORT=8130; URL=http://127.0.0.1:$PORT
SRVLOG=all_log/opener_server_fp.log
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'),'/',d.get('total'))" 2>/dev/null; }

# ── C1: 최종+opener rand200 (w4, resume — 기존 18개 유지) ── headline
say "=== C1: 최종+opener rand200 (w4, resume) ==="
: > "$SRVLOG"
HF_HUB_OFFLINE=1 PLANNER_ADAPTER=$OPENER PLANNER_OPENER=1 CUDA_VISIBLE_DEVICES=1 \
  python3 src/model_deployment/planner_server.py "$QWEN" "$PORT" >> "$SRVLOG" 2>&1 &
SRV=$!; for i in $(seq 1 90); do grep -q READY "$SRVLOG" 2>/dev/null && break; sleep 5; done
say "opener 서버 READY=$(grep -q READY $SRVLOG && echo Y || echo N)"
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$FINAL PLANNER_URL=$URL CUDA_VISIBLE_DEVICES=1 \
  python3 scripts/run_all.py --alias rango-planner --idx-file "$RAND" --timeout 300 --gpus 1 --workers 4 \
  --out all_results/osg_final_opener >> "$LOG" 2>&1
kill -9 "$SRV" 2>/dev/null; pkill -9 -f 'planner_server.py' 2>/dev/null; pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 5
say "C1 최종+opener rand200: $(sumline all_results/osg_final_opener)"

# ── C2: gold-SFT anchor rand200 (w8, opener 없이) ──
say "=== C2: gold-SFT anchor rand200 (w8) ==="
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$GOLD CUDA_VISIBLE_DEVICES=1 \
  python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" --timeout 300 --gpus 1 --workers 8 \
  --out all_results/osg_goldsft >> "$LOG" 2>&1
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
say "C2 gold-SFT anchor rand200: $(sumline all_results/osg_goldsft)"

say "=== Stage C 완료 STAGEC_DONE ==="
python3 - >> "$LOG" 2>&1 <<'PY'
import json,os
def g(p):
    p=f'all_results/{p}/summary.json'
    if os.path.exists(p): d=json.load(open(p));return f"{d.get('success')}/{d.get('done')}/{d.get('total')}"
    return "(없음)"
print("\n===== 최종 (rand200@300s, success/done/total) =====")
print("  최종 gold-SFT→opener-sub-GRPO +opener :",g('osg_final_opener'))
print("  gold-SFT (anchor, opener없이)         :",g('osg_goldsft'))
PY
