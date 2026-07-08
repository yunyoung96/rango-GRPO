#!/bin/bash
cd /app/coq-modeling
log(){ echo "[$(date -u +%H:%M:%S)] $*" >> all_log/oracle_both.log; }
log "=== 깨끗한 A/B both 비교: 앞 실험 대기 ==="
while ps -eo args | grep -qE "[o]racle_ablation|[r]un_all.py --alias|[r]un_bigger.sh"; do sleep 120; done
for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
log "▶ rango 동일스텝 A/B (40파일)"
python3 scripts/oracle_ablation.py --alias rango --num-files 40 --max-proofs-per-file 8 \
  --max-steps-per-proof 30 --cond both --out all_log/oracle_rango_AB.md >> all_log/oracle_both.log 2>&1
log "■ rango A/B 완료: $(grep 'gold-lemma..\? top-1' all_log/oracle_rango_AB.md 2>/dev/null | head -1)"
log "=== 종료 ==="
