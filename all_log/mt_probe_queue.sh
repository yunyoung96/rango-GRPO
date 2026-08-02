#!/bin/bash
# once-v2 @600s eval 완료 대기 → multi-turn 에러피드백 A/B 프로브 롤아웃 → 분석 리포트(MD).
#   프로브: executor=subgoal 1.3B, INVALID state에서 A0(에러없이)/A1(에러주석) 각 n샘플 재생성·coq검증.
#   MT_PROBE=1 (grpo_rollout.py). PLANNER 없음(opener 안 씀 — 순수 executor 능력 측정).
cd /app/coq-modeling || exit 1
LOG=all_log/mt_probe.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
EXECU=models/rango-grpo-subgoal-bs2/adapter
TRAIN=data/compcert_bs2_train_idx.txt
PROBE=/tmp/mt_probe.jsonl
ROLL=/tmp/mt_probe_roll.jsonl
REPORT=all_log/docs/grpo/MULTITURN_PROBE_RESULT.md
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
wait_gpus(){ local need=${1:-14000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  local g=""; [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ]&&g="0"; [ "$f1" -ge "$need" ]&&g="${g:+$g,}1"
  [ -n "$g" ]&&{ echo "$g";return; }; [ $w -ge 7200 ]&&{ echo 1;return; }; sleep 30;w=$((w+30)); done; }

# ── 1) once-v2 @600s eval 완료 대기 ──
say "once-v2 @600s eval 완료 대기 (ONCEV2_600_DONE)..."
S=$SECONDS
while :; do
  grep -q 'ONCEV2_600_DONE' all_log/once_v2_600.log 2>/dev/null && break
  # 안전장치: eval 프로세스도 없고 summary도 있으면 완료로 간주
  if ! pgrep -f 'run_all.py --alias rango-grpo' >/dev/null && [ -s all_results/once_v2_600/summary.json ]; then break; fi
  sleep 60
  [ $((SECONDS-S)) -ge 43200 ] && { say "대기 타임아웃(12h) — 그래도 진행"; break; }
done
say "600s eval 완료 감지 → 프로브 시작"
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 5

# ── 2) MT_PROBE 롤아웃 (80정리, executor=subgoal, opener 없음) ──
#   cap 250 = paired McNemar 검정력 확보(120은 순 3~4케이스 차가 노이즈라 판정불가).
head -80 "$TRAIN" > /tmp/mt_idx.txt
rm -f "$PROBE" "$ROLL"
GPUS=$(wait_gpus 14000); say "프로브 롤아웃 (GPU $GPUS, 80정리, MT_PROBE=1, n=8, cap=250)"
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$EXECU \
  MT_PROBE=1 MT_PROBE_OUT=$PROBE MT_PROBE_N=8 MT_PROBE_MAX=250 \
  ROLLOUT_OUT=$ROLL \
  python3 scripts/run_all.py --alias grpo-rollout-pf --idx-file /tmp/mt_idx.txt \
  --timeout 200 --gpus "$GPUS" --workers 2 >> "$LOG" 2>&1
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 3
NREC=$([ -f "$PROBE" ] && wc -l < "$PROBE" || echo 0)
say "프로브 완료: $NREC 케이스 기록"

# ── 3) 분석 → MD 리포트 ──
if [ "$NREC" -ge 1 ]; then
  python3 scripts/analyze_mt_probe.py "$PROBE" "$REPORT" >> "$LOG" 2>&1
  SUMM=$(grep '^SUMMARY' "$LOG" | tail -1)
  say "분석 완료 → $REPORT"
  say "$SUMM"
else
  say "프로브 기록 0 — INVALID를 못 만났거나 서버 실패. 로그 확인 필요."
fi
say "=== MT_PROBE_DONE ==="
