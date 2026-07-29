#!/bin/bash
# invertible-BFS: cascade-s0 정책 + BFS 탐색기 + invertible 후보 주입(BFS_INVERT).
#   재귀적 invertible+cascade를 우선순위큐로 효율 탐색(무거운 auto-saturation 없음).
#   A/B: plain-BFS vs invert-BFS 커버리지. 좋으면 train-300 확장(닫힌 성공경로=분해 SFT 데이터).
set -u
LOG=all_log/invbfs.log
IDX="${IDX:-data/compcert_bs2_invauto_idx.txt}"
POL=models/rango-grpo-cascade-s0/adapter
GPU="${GPU:-0}"; W="${W:-20}"; T="${T:-120}"    # 워커 증설(자원 여유)
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
runbfs(){  # $1=invert(0/1) $2=name
  rm -f data/bfs_trees/inv_$2.jsonl.*
  BFS_ADAPTER="$POL" BFS_INVERT="$1" BFS_INVERT_K="${BFS_INVERT_K:-6}" \
  BFS_TRACE_OUT="data/bfs_trees/inv_$2.jsonl" \
    taskset -c 0-127 python3 scripts/run_all.py --alias bfs-prover-trace \
    --idx-file "$IDX" --timeout "$T" --gpus "$GPU" --workers "$W" \
    --out "all_results/invbfs_$2" --description "invbfs $2" >> "$LOG" 2>&1
}
say "════ invertible-BFS A/B: cascade-s0+BFS ($(wc -l <"$IDX")정리, GPU$GPU w$W t$T) ════"
say "▶ plain-BFS (INVERT=0)";  runbfs 0 plain
say "▶ invert-BFS (INVERT=1)"; runbfs 1 invert
say "════ 결과 ════"
python3 - <<'PY' | tee -a "$LOG"
import json
def cov(p):
    try:
        r=json.load(open(p))['results']; s=sum(1 for x in r if x['success'])
        return f"{s}/{len(r)} ({100*s/max(len(r),1):.0f}%)"
    except Exception as e: return f"?({e})"
print("  plain-BFS  :", cov("all_results/invbfs_plain/summary.json"))
print("  invert-BFS :", cov("all_results/invbfs_invert/summary.json"))
PY
say "════ [invbfs 완료] ════"
