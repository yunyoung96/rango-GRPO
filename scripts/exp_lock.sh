#!/bin/bash
# 실험 직렬화 — **flock 으로**. 절대 pgrep 패턴으로 하지 않는다.
#
# ★ 왜: `pgrep -f '<명령줄 패턴>'` 은 그 문자열을 cmdline 에 담은 **모든** 프로세스를
#   잡는다. 감시 셸도, 스크립트를 만든 heredoc 셸도, 심지어 그 pgrep 자신도.
#   이 함정에 오늘만 세 번 빠졌다(감시자 데드락 → 체인 데드락 → 생성자 데드락).
#   커널 파일 잠금은 **누가 실행 중인지**를 명령줄 문자열이 아니라 fd 로 판단한다.
#
# 사용: bash scripts/exp_lock.sh <명령...>
exec 9> /tmp/coq-modeling-exp.lock
flock 9                       # 앞 실험이 끝날 때까지 블록
exec "$@"
