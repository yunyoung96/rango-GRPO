#!/bin/bash
# 올바른 eval: test는 opener 없이(opener는 학습 탐색 도구). rand200 처음부터.
#   E1: 최종모델(rango-opener-sub-grpo) 단독  vs  E2: gold-SFT 단독. 둘 다 w8, opener 없음.
cd /app/coq-modeling || exit 1
LOG=all_log/eval_noopener.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
# 기존 opener eval/서버 정리
pkill -9 -f 'stageC_fast.sh' 2>/dev/null
pkill -9 -f 'run_all.py' 2>/dev/null
pkill -9 -f 'run_thm.py' 2>/dev/null
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
pkill -9 -f 'planner_server.py' 2>/dev/null
sleep 8
say "기존 opener eval 정리. GPU=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader -i 1)"
# 잘못된 opener eval 결과 제거(처음부터 다시)
rm -rf all_results/osg_final_noopener all_results/osg_goldsft
FINAL=models/rango-opener-sub-grpo/adapter
GOLD=models/rango-grpo-bs2-sft/adapter
RAND=data/compcert_bs2_rand200_idx.txt
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'),'/',d.get('total'))" 2>/dev/null; }

# E1: 최종모델 단독 (opener 없이)
say "=== E1: 최종모델(opener없이) rand200 @300s w8 ==="
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$FINAL CUDA_VISIBLE_DEVICES=1 \
  python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" --timeout 300 --gpus 1 --workers 8 \
  --out all_results/osg_final_noopener --description "final no-opener" >> "$LOG" 2>&1
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 3
say "E1 최종(opener없이) rand200: $(sumline all_results/osg_final_noopener)"

# E2: gold-SFT 단독 (opener 없이) = baseline
say "=== E2: gold-SFT(opener없이) rand200 @300s w8 ==="
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$GOLD CUDA_VISIBLE_DEVICES=1 \
  python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" --timeout 300 --gpus 1 --workers 8 \
  --out all_results/osg_goldsft --description "gold-SFT baseline" >> "$LOG" 2>&1
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
say "E2 gold-SFT rand200: $(sumline all_results/osg_goldsft)"

say "=== EVAL 완료 EVAL_DONE ==="
python3 - >> "$LOG" 2>&1 <<'PY'
import json,os
def g(p):
    p=f'all_results/{p}/summary.json'
    if os.path.exists(p): d=json.load(open(p));return f"{d.get('success')}/{d.get('done')}/{d.get('total')} ({100*d.get('success',0)/max(d.get('done',1),1):.1f}%)"
    return "(없음)"
print("\n===== 최종 (rand200@300s, opener 없이, success/done/total) =====")
print("  최종 gold-SFT→opener-sub-GRPO :",g('osg_final_noopener'))
print("  gold-SFT (baseline)          :",g('osg_goldsft'))
PY
