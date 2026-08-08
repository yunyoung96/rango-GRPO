#!/bin/bash
# v2 학습 감시견 — 죽으면 자동으로 되살린다.
#   run_augmented_v4_ddp.sh 자체에 재시도 루프가 있지만, **런처까지 함께 죽는 경우**(세션 종료,
#   프로세스 그룹 kill)는 그 루프가 못 돈다. 실제로 687 step 에서 그렇게 죽었다 → 이 감시견이 필요.
#   PPID 1 로 분리해 띄우고, 학습이 안 보이면 재기동한다(최신 정상 체크포인트에서 자동 재개).
cd /app/coq-modeling || exit 1
LOG=all_log/v4_watchdog.log
OUT=models/rango-1.3b-augmented-v4-ft
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }

say "===== v2 감시견 시작 ====="
miss=0
while :; do
  sleep 120
  # 완료됐으면 종료
  [ -f "$OUT/AUGMENT.json" ] && { say "v2 학습 완료 감지 — 감시 종료"; exit 0; }
  # ★ 평가(rand200)가 도는 동안에는 학습이 **의도적으로** 멈춰 있다. 여기서 되살리면 GPU 를 뺏어
  #   평가가 왜곡된다(탐색량이 줄어 성공률이 낮게 나옴) → 평가 중이면 감시를 쉰다.
  if pgrep -f "run_all.py|tactic_gen_server|eval_v2_at" >/dev/null; then
    miss=0
    continue
  fi
  if pgrep -f "train_decoder.py" >/dev/null; then
    miss=0
  else
    miss=$((miss + 1))
    say "학습 프로세스 안 보임 ($miss/2)"
    if [ "$miss" -ge 2 ]; then     # 4분 연속 부재 = 진짜 죽음(재시작 중 공백 아님)
      LAST=$(ls -d "$OUT"/checkpoint-* 2>/dev/null | sed 's/.*checkpoint-//' | sort -n | tail -1)
      say "★ 재기동 (최신 체크포인트: ${LAST:-없음})"
      nohup setsid bash all_log/run_augmented_v4_ddp.sh </dev/null >/dev/null 2>&1 &
      disown -a
      miss=0
      sleep 180
    fi
  fi
done
