#!/bin/bash
# tst1000tr5091 Stage3 롤아웃 재개 — 남은 1843개(stage3 완료 3248 제외)를 이어서.
#   기존 sftroll.jsonl(3148그룹)에 append. SFT모델 롤아웃, @300s, w4(2GPU×4=8병렬).
#   theorem_id가 프로세스-랜덤이라, 남은 idx는 원본 로그의 완료 idx로 계산함(remain_idx.txt).
cd /app/coq-modeling || exit 1
TAG=tst1000tr5091
LOG=all_log/${TAG}_rollout_resume.log
: > "$LOG"
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
SFTM=models/rango-${TAG}-sft
SFTROLL=data/grpo_rollouts/${TAG}_sftroll.jsonl
REMAIN=data/compcert_${TAG}_remain_idx.txt
ROLLTO=300
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
wait_gpus(){ local need=${1:-13000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  local g=""; [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ]&&g="0"; [ "$f1" -ge "$need" ]&&g="${g:+$g,}1"
  [ -n "$g" ]&&{ echo "$g";return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 30;w=$((w+30)); done; }

[ -f "$SFTM/adapter/adapter_model.safetensors" ] || { say "SFT 모델 없음 — 중단"; exit 1; }
[ -s "$REMAIN" ] || { say "남은 idx 없음 — 중단"; exit 1; }
BEFORE=$(wc -l < "$SFTROLL")
say "▶ 롤아웃 재개: 남은 $(wc -l < $REMAIN)개 → sftroll(현재 $BEFORE그룹)에 append (@${ROLLTO}s, w4)"
G=$(wait_gpus 13000)
say "  GPU:$G"
EXEC_ADAPTER=$SFTM/adapter ROLLOUT_OUT=$SFTROLL ROLLOUT_RETRY=1 HF_HUB_OFFLINE=1 \
  python3 scripts/run_all.py --alias grpo-rollout-pf --idx-file "$REMAIN" --timeout "$ROLLTO" --gpus "$G" --workers 4 >> "$LOG" 2>&1
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
AFTER=$(wc -l < "$SFTROLL")
say "  롤아웃 완료: sftroll $BEFORE → $AFTER 그룹 (+$((AFTER-BEFORE)))"
say "=== ${TAG}_ROLLOUT_RESUME_DONE (총 $AFTER / 목표 5091) ==="
