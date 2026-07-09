#!/bin/bash
cd /app/coq-modeling
log(){ echo "[$(date -u +%H:%M:%S)] $*" >> all_log/ablation40.log; }
log "=== 40-theorem 라운드: 20-ablation 및 앞 실험 대기 ==="
sleep 90
while ps -eo args | grep -qE "[o]racle_ablation|[r]un_all.py --alias|[r]un_qed.sh|[r]un_6.7b_lean.sh|[r]un_rmaxts.sh|[r]un_bfs.sh|[r]un_ablation.sh|[r]un rmaxts|[r]un bfs"; do sleep 120; done
# paper 2개 + ablation 5개, 전부 40정리 @600
for a in rmaxts bfs-prover rmaxts-noreward rmaxts-nomerge rmaxts-nomcts bfs-a0 bfs-a1; do
  for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
  log "▶ $a first-40 @600"
  python3 scripts/run_all.py --alias "$a" --num 40 --timeout 600 --workers 1 \
    --description "40-theorem 라운드(ablation 확장)" >> all_log/ablation40.log 2>&1
  dir=$(ls -dt all_results/*/ | head -1)
  s=$(python3 -c "import json;d=json.load(open('$dir/summary.json'));print(d['success'],'/',d['total'])" 2>/dev/null)
  log "■ $a @40: $s → $dir"
done
log "=== 40 effectiveness 비교 ==="
python3 - >> all_log/ablation40.log 2>&1 <<'PY'
import json, glob
want={"rmaxts":"full","rmaxts-noreward":"−RMax reward","rmaxts-nomerge":"−state merge",
      "rmaxts-nomcts":"−DUCB","bfs-prover":"BFS α=0.5","bfs-a0":"BFS α=0","bfs-a1":"BFS α=1"}
res={}
for s in glob.glob("all_results/*/summary.json"):
    try: d=json.load(open(s))
    except: continue
    a=d.get("architecture")
    if a in want and d.get("total")==40:
        if a not in res or d.get("success",0)>=res.get(a,0): res[a]=d.get("success")
print("\n## RMaxTS/BFS 컴포넌트 effectiveness (first-40)")
for a,lbl in want.items(): print(f"  {lbl:16s}: {res.get(a,'?')}/40")
PY
log "=== 40 라운드 종료 ==="
