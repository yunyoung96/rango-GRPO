#!/bin/bash
# 이름필터 평가 종료 → 자가교정(ERROR_REPAIR) 평가 → v3(인용타깃) 학습, 순차 실행.
cd /app/coq-modeling || exit 1
LOG=all_log/queue_repair_then_v3.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }

say "이름필터 평가 종료 대기"
gone=0
while :; do
  sleep 120
  if pgrep -f "run_all.py" >/dev/null; then
    gone=0
  else
    gone=$((gone + 1))
    [ "$gone" -ge 3 ] && break
  fi
done

say "→ 자가교정(ERROR_REPAIR) 평가 시작"
bash all_log/eval_error_repair.sh
say "자가교정 평가 종료"

say "→ v3(인용타깃) 학습 시작"
for p in $(ps -eo pid,cmd | grep -E "[r]un_thm.py|[t]actic_gen_server" | awk '{print $1}'); do
  kill -9 "$p" 2>/dev/null
done
sleep 20
nohup setsid bash all_log/run_augmented_v3_ddp.sh </dev/null >/dev/null 2>&1 &
disown -a 2>/dev/null || true
sleep 180

# v3 감시견(죽으면 자동 재기동)
sed 's#run_augmented_v2_ddp.sh#run_augmented_v3_ddp.sh#; s#rango-1.3b-augmented-v2-ft#rango-1.3b-augmented-v3-ft#; s#all_log/v2_watchdog.log#all_log/v3_watchdog.log#' \
  all_log/v2_watchdog.sh > all_log/v3_watchdog.sh
chmod +x all_log/v3_watchdog.sh
nohup setsid bash all_log/v3_watchdog.sh </dev/null >/dev/null 2>&1 &
disown -a 2>/dev/null || true
say "v3 감시견 가동"
say "v3 진행: $(tr '\r' '\n' < all_log/ft_rango_augmented_v3.log 2>/dev/null | grep -aoE '[0-9]+/60000' | tail -1)"
