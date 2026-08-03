#!/bin/bash
# 수정판: gold-subgoal 닫기율 진단(올바르게=skip_s0 curriculum-only) + 2x2 ablation.
#   {π₀=rango-grpo, leaf-subgoal=rango-grpo-subgoal-bs2} × {opener 없음, 생성형 opener}
# GPU1 전용(CUDA_VISIBLE_DEVICES=1). GPU0 절대 금지(외부 유저).
cd /app/coq-modeling || exit 1
LOG=all_log/overnight_2x2.log
say(){ echo "[$(TZ=Asia/Seoul date +%m-%d\ %H:%M)] $*" >> "$LOG"; }
: > "$LOG"

IDX=/tmp/abl60_idx.txt
head -60 data/compcert_bs2_rand200_idx.txt > "$IDX"
TRAIN=data/compcert_bs2_train_idx.txt
TMO=240

# ── ① gold-subgoal 닫기율 진단 (revcurr, skip_s0 → curriculum 그룹만; 매칭 안 된 정리는 빠르게 skip) ──
say "=== ① 진단: gold subgoal 닫기율 (revcurr, skip_s0, train 300, w8) ==="
rm -f data/grpo_rollouts/revcurr.jsonl
HF_HUB_OFFLINE=1 SUBGOAL_SKIP_S0=1 CUDA_VISIBLE_DEVICES=1 python3 scripts/run_all.py \
  --alias grpo-rollout-revcurr --idx-file "$TRAIN" --timeout 400 --gpus 1 --workers 8 \
  --out all_results/revcurr_diag >> "$LOG" 2>&1
python3 - >> "$LOG" 2>&1 <<'PY'
import json
from collections import defaultdict
try: rows=[json.loads(l) for l in open('data/grpo_rollouts/revcurr.jsonl')]
except FileNotFoundError: rows=[]
cur=[g for g in rows if g.get('start')!='s0']
def solved(g): return sum(1 for x in g.get('attempts',[]) if x.get('reward',0)>0)
ng=len(cur); gs=sum(1 for g in cur if solved(g)>0)
print(f"[진단] gold subgoal 그룹 {ng} | ≥1닫음 {gs}/{ng} = {100*gs/max(ng,1):.0f}%  (닫기율 = 도달 벽 vs capacity 벽)")
# remaining 깊이별
byr=defaultdict(lambda:[0,0])
for g in cur:
    r=(g.get('attempts',[{}])[0].get('steps',[{}]) or [{}])
    rem=g.get('remaining','?')
    byr[rem][0]+=1; byr[rem][1]+=(1 if solved(g)>0 else 0)
PY
say "① 진단 완료(닫기율은 로그 참조)."

run_cond(){ # $1=label $2=alias $3=workers $4=out ; env는 호출측
  say ">>> $1 시작 (alias=$2 w=$3)"
  HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=1 python3 scripts/run_all.py \
    --alias "$2" --idx-file "$IDX" --timeout "$TMO" --gpus 1 --workers "$3" --out "$4" >> "$LOG" 2>&1
  local s; s=$(python3 -c "import json;d=json.load(open('$4/summary.json'));print(d.get('success'),'/',d.get('done'),'/',d.get('total'))" 2>/dev/null)
  say "<<< $1 종료. success/done/total = $s"
}

# ── ② opener 없는 2조건(w8) ──
run_cond "COND1 π₀ 단독"          rango-grpo 8 all_results/abl_pi0
EXEC_ADAPTER=models/rango-grpo-subgoal-bs2/adapter \
run_cond "COND2 leaf-subgoal 단독" rango-grpo 8 all_results/abl_subgoal

# ── ③ 생성형 opener 서버 기동 + opener 2조건(w2) ──
say "opener 서버(생성형) 기동..."; : > all_log/opener_server.log
HF_HUB_OFFLINE=1 PLANNER_ADAPTER=models/opener-7b/adapter PLANNER_OPENER=1 \
  CUDA_VISIBLE_DEVICES=1 python3 src/model_deployment/planner_server.py \
  Qwen/Qwen2.5-Coder-7B-Instruct 8130 >> all_log/opener_server.log 2>&1 &
SRV=$!
for i in $(seq 1 90); do grep -q 'READY' all_log/opener_server.log 2>/dev/null && break; sleep 5; done
if grep -q 'READY' all_log/opener_server.log 2>/dev/null; then
  say "opener 서버 READY (pid $SRV)"
  PLANNER_URL=http://127.0.0.1:8130 \
  run_cond "COND3 π₀+opener"          rango-planner 2 all_results/abl_pi0_opener
  PLANNER_URL=http://127.0.0.1:8130 EXEC_ADAPTER=models/rango-grpo-subgoal-bs2/adapter \
  run_cond "COND4 leaf-subgoal+opener" rango-planner 2 all_results/abl_subgoal_opener
  kill -9 "$SRV" 2>/dev/null
else
  say "opener 서버 기동 실패 → COND3/4 건너뜀"; kill -9 "$SRV" 2>/dev/null
fi

say "=== 2x2 완료 ==="
python3 - >> "$LOG" 2>&1 <<'PY'
import json,os
rows=[("π₀ 단독","abl_pi0"),("leaf-subgoal 단독","abl_subgoal"),
      ("π₀+opener","abl_pi0_opener"),("leaf-subgoal+opener","abl_subgoal_opener")]
print("\n=== 2x2 요약 (success/done/total) ===")
for name,d in rows:
    p=f"all_results/{d}/summary.json"
    print(f"  {name:24s}: "+ (f"{json.load(open(p)).get('success')}/{json.load(open(p)).get('done')}/{json.load(open(p)).get('total')}" if os.path.exists(p) else "(없음)"))
PY
say "DONE_MARKER"
