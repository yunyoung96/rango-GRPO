#!/bin/bash
cd /app/coq-modeling
log(){ echo "[$(date -u +%H:%M:%S)] $*" >> all_log/oracle_6.7b.log; }
log "=== lean raw-6.7b oracle: bigger+both 대기 ==="
sleep 60
while ps -eo args | grep -qE "[r]un_bigger.sh|[r]un_oracle_both.sh|[r]un_all.py --alias|[o]racle_ablation"; do sleep 120; done
for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
log "▶ lean 6.7b oracle (15파일, no detail)"
python3 scripts/oracle_ablation.py --alias rango-6.7b --num-files 15 --max-proofs-per-file 6 \
  --max-steps-per-proof 25 --cond A --out all_log/oracle_6.7b_A.md >> all_log/oracle_6.7b.log 2>&1
log "■ 완료: $(grep 'top-1 exact' all_log/oracle_6.7b_A.md 2>/dev/null | head -1)"
