#!/bin/bash
# ★ DEFER 스텁 — bigscale 을 "맨 마지막"으로 미룸(사용자 요청 2026-07-17).
#   chain_B 가 이 파일을 부르면 아무것도 안 하고 즉시 반환한다.
#   실제 bigscale 은 run_bigscale_real.sh 이며, 전체 큐(deepres 개선) 맨 끝에서 실행된다.
echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] bigscale DEFER — 맨 마지막으로 미룸(run_bigscale_real.sh 가 큐 끝에서 실행)" | tee -a all_log/bigscale.log
exit 0
