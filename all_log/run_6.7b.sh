#!/bin/bash
cd /app/coq-modeling
log(){ echo "[$(date -u +%H:%M:%S)] $*" >> all_log/run6.7b.log; }
log "=== 6.7B 러너: 다운로드 완료 대기 ==="
# 두 shard + tokenizer 모두 존재 + 다운로드 프로세스 종료까지 대기
while true; do
  s1=models_dl/deepseek-coder-6.7b-instruct/model-00001-of-00002.safetensors
  s2=models_dl/deepseek-coder-6.7b-instruct/model-00002-of-00002.safetensors
  if [ -f "$s1" ] && [ -f "$s2" ] && ! pgrep -f "snapshot_download" >/dev/null 2>&1; then break; fi
  grep -q "^DONE" all_log/dl_6.7b.log 2>/dev/null && [ -f "$s1" ] && [ -f "$s2" ] && break
  sleep 20
done
log "다운로드 완료 확인. 고아 서버 정리 후 스모크."
for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done
sleep 3
# 스모크: 6.7B 로드+생성 검증 (idx6, 180s)
log "▶ 스모크 rango-6.7b idx6 @180s"
timeout 600 python3 scripts/run_thm.py run rango-6.7b test 6 --timeout 180 > all_log/smoke_6.7b.log 2>&1
if grep -q "RANGO_JSON_SUCCESS" all_log/smoke_6.7b.log; then
  r=$(grep -oE "RANGO_JSON_SUCCESS: (True|False)" all_log/smoke_6.7b.log | tail -1)
  log "✓ 스모크 완료(로드+생성 정상): $r"
  for p in $(pgrep -f tactic_gen_server); do kill "$p" 2>/dev/null; done; sleep 3
  log "▶ 본실험 rango-6.7b first-20 @600"
  python3 scripts/run_all.py --alias rango-6.7b --num 20 --timeout 600 --workers 1 \
    --description "heavy lever 1: raw DeepSeek-Coder-6.7B-instruct + Rango prompt (untuned)" >> all_log/run6.7b.log 2>&1
  dir=$(ls -dt all_results/*/ | head -1)
  python3 scripts/make_report.py "$dir" >> all_log/run6.7b.log 2>&1
  s=$(python3 -c "import json;d=json.load(open('$dir/summary.json'));print(d['success'],'/',d['total'])" 2>/dev/null)
  log "■ rango-6.7b first-20 완료: $s → $dir"
else
  log "✗ 스모크 실패(로드/생성 오류) — 로그 확인 필요: all_log/smoke_6.7b.log"
  tail -20 all_log/smoke_6.7b.log >> all_log/run6.7b.log
fi
log "=== 6.7B 러너 종료 ==="
