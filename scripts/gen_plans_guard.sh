#!/bin/bash
# ★ 중복 실행 방지. 재시작할 때마다 인스턴스가 쌓여 프로세스 72개 · 부하 100 이 됐다
#   (의도한 12개의 6배). kill 루프가 자기매칭으로 계속 실패한 것이 원인이다.
#   flock 으로 **한 번에 하나만** 돌게 한다.
exec 9> /tmp/coq-modeling-genplans.lock
flock -n 9 || { echo "이미 실행 중 — 아무것도 하지 않는다"; exit 0; }
exec bash scripts/gen_plans_both.sh
