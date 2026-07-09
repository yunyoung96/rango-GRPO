#!/bin/bash
cd /app/coq-modeling
log(){ echo "[$(date -u +%H:%M:%S)] $*" >> all_log/ablation.log; }
log "=== ablation 드라이버: full rmaxts/bfs 및 앞선 실험 대기 ==="
sleep 60
while ps -eo args | grep -qE "[o]racle_ablation|[r]un_all.py --alias|[r]un_qed.sh|[r]un_6.7b_lean.sh|[r]un_rmaxts.sh|[r]un_bfs.sh|[r]un rmaxts|[r]un bfs"; do sleep 120; done
# 5개 ablation 변형 (full은 rmaxts/bfs-prover가 이미 돌아 reference)
for a in rmaxts-noreward rmaxts-nomerge rmaxts-nomcts bfs-a0 bfs-a1; do
  for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
  log "▶ $a first-20 @600"
  python3 scripts/run_all.py --alias "$a" --num 20 --timeout 600 --workers 1 \
    --description "ablation: 컴포넌트 하나 off" >> all_log/ablation.log 2>&1
  dir=$(ls -dt all_results/*/ | head -1)
  s=$(python3 -c "import json;d=json.load(open('$dir/summary.json'));print(d['success'],'/',d['total'])" 2>/dev/null)
  log "■ $a: $s → $dir"
done
# 효과 비교표
log "=== ablation 효과 비교 ==="
python3 - >> all_log/ablation.log 2>&1 <<'PY'
import json, glob
want={"rmaxts":"full","rmaxts-noreward":"−RMax reward","rmaxts-nomerge":"−state merge",
      "rmaxts-nomcts":"−DUCB(random)","bfs-prover":"BFS α=0.5","bfs-a0":"BFS α=0","bfs-a1":"BFS α=1"}
res={}
for s in glob.glob("all_results/*/summary.json"):
    try: d=json.load(open(s))
    except: continue
    a=d.get("architecture")
    if a in want and d.get("total")==20:
        if a not in res or d.get("success",0)>=res[a]: res[a]=d.get("success")
print("\n## RMaxTS/BFS 컴포넌트 effectiveness (first-20)")
for a,lbl in want.items():
    print(f"  {lbl:16s} ({a}): {res.get(a,'?')}/20")
PY
log "=== ablation 종료 ==="
