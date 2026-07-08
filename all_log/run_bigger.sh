#!/bin/bash
cd /app/coq-modeling
log(){ echo "[$(date -u +%H:%M:%S)] $*" >> all_log/bigger.log; }
log "=== 큰 재실행 드라이버: 앞선 GPU 실험(oracle 등) 대기 ==="
while pgrep -f "[r]un_oracle.sh" >/dev/null 2>&1 || pgrep -f "[o]racle_ablation" >/dev/null 2>&1 || ps -eo args | grep -qE "[r]un_all.py --alias rango-hybrid"; do sleep 90; done
# distinct-capability 기법만(자동화/검색/백트랙) 60정리 @600. baseline은 baseline600 참조라 제외.
for a in rango-sauto rango-portfolio rango-mem rango-search rango-vguided; do
  for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
  log "▶ $a idx0-59 @600"
  python3 scripts/run_all.py --alias "$a" --num 60 --timeout 600 --workers 1 \
    --description "큰 재실행(unique-solve 강점 측정)" >> all_log/bigger.log 2>&1
  dir=$(ls -dt all_results/*/ | head -1)
  s=$(python3 -c "import json;d=json.load(open('$dir/summary.json'));print(d['success'],'/',d['total'])" 2>/dev/null)
  log "■ $a 완료: $s → $dir"
  python3 scripts/unique_solves.py >> all_log/bigger.log 2>&1  # 매번 갱신
done
log "=== 큰 재실행 종료 ==="
