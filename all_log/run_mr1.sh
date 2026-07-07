#!/bin/bash
cd /app/coq-modeling
log(){ echo "[$(date -u +%H:%M:%S)] $*" >> all_log/mr1.log; }
log "=== MR1 러너 시작: hprobe 완료 대기 ==="
while ps -eo args | grep -q "[r]un_all.py --alias rango-hprobe"; do sleep 60; done
log "hprobe 완료. 고아 서버 정리."
for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done
sleep 3
# Part B: 라벨 트리 생성 (idx 30~129, eval first-20과 분리). timeout 240.
log "▶ Part B: rango-vlog 데이터 생성 (start=30 num=100 @240s)"
python3 scripts/run_all.py --alias rango-vlog --start 30 --num 100 --timeout 240 --workers 1 \
  --description "MR1 value-model 학습데이터 생성(트리 덤프)" >> all_log/mr1.log 2>&1
ntrees=$(ls data/vguided_trees/*.jsonl 2>/dev/null | wc -l)
npos=$(cat data/vguided_trees/*.jsonl 2>/dev/null | grep -c '"label": 1')
log "■ Part B 완료: 트리파일 $ntrees, positive 레코드 $npos"
# Part C: value head 학습
log "▶ Part C: value head 학습"
python3 scripts/train_value.py --epochs 200 >> all_log/mr1.log 2>&1
# Part E: rango-vguided vs baseline (first-20)
if [ -f models/value_head/value.pt ]; then
  for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
  log "▶ Part E: rango-vguided first-20 평가"
  python3 scripts/run_all.py --alias rango-vguided --num 20 --timeout 600 --workers 1 \
    --description "MR1 value-guided best-first (learned critic frontier blend)" >> all_log/mr1.log 2>&1
  dir=$(ls -dt all_results/*/ | head -1)
  python3 scripts/make_report.py "$dir" >> all_log/mr1.log 2>&1
  s=$(python3 -c "import json;d=json.load(open('$dir/summary.json'));print(d['success'],'/',d['total'])" 2>/dev/null)
  log "■ Part E 완료: rango-vguided $s → $dir"
else
  log "✗ value.pt 없음 → Part E 스킵 (데이터 부족?)"
fi
log "=== MR1 러너 종료 ==="
