#!/bin/bash
cd /app/coq-modeling
log(){ echo "[$(date -u +%H:%M:%S)] $*" >> all_log/oracle_drv.log; }
log "=== oracle 후속 드라이버: GPU 대기 ==="
while ps -eo args | grep -qE "[r]un_all.py --alias rango-hybrid"; do sleep 60; done
for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
# 조건 B: rango 1.3b + gold lemma 주입 (retrieval 병목 테스트)
log "▶ 조건B rango gold-lemma (40파일)"
python3 scripts/oracle_ablation.py --alias rango --num-files 40 --max-proofs-per-file 8 \
  --max-steps-per-proof 30 --cond B --detail --out all_log/oracle_rango_B.md >> all_log/oracle_drv.log 2>&1
log "■ 조건B 완료"
for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
# 조건 A: 6.7b (capacity 테스트)
log "▶ 조건A 6.7b (40파일)"
python3 scripts/oracle_ablation.py --alias rango-6.7b --num-files 40 --max-proofs-per-file 8 \
  --max-steps-per-proof 30 --cond A --detail --out all_log/oracle_6.7b_A.md >> all_log/oracle_drv.log 2>&1
log "■ 조건A 6.7b 완료"
log "=== oracle 후속 드라이버 종료 ==="
