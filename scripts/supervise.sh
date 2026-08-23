#!/bin/bash
# ★ 실험 감시자 — 죽으면 되살리고, 같은 원인으로 반복 실패하면 멈춘다.
#
#  오늘 실험이 죽은 원인 셋:
#    ① 캐시 스탬프 불일치 (rc=3 / rc=1)   → 설정 해시 디렉터리로 구조적 해결
#    ② 체인 스크립트를 실행 중에 수정      → bash 가 오프셋으로 읽어 중복/오작동
#    ③ `pkill -f` 자기매칭으로 셸이 죽음   → 명시 PID 트리로만 정리
#
#  그래도 남는 것(OOM·타임아웃·일시적 오류)을 위해 감시한다.
#  ★ 무한 재시작은 하지 않는다 — 같은 작업이 3번 실패하면 포기하고 기록한다.
set -u
cd /app/coq-modeling || exit 1
exec 9>/tmp/supervise.lock
flock -n 9 || { echo "이미 감시 중"; exit 0; }

L=all_log/au_research/supervise.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$L"; }

alive(){ # $1 = cmdline 조각. **명시 PID 로만** 본다 (comm 은 전부 python3 라 args 를 쓰되 자기 제외)
  local me=$$ n=0 p a
  for p in $(ps -eo pid= 2>/dev/null); do
    [ "$p" = "$me" ] && continue
    a=$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null) || continue
    case "$a" in *supervise.sh*) continue;; esac      # 감시자 자신 제외
    case "$a" in *"$1"*) n=1; break;; esac
  done
  [ $n -eq 1 ]
}

declare -A FAIL
MAX_FAIL=3

restart_rank(){
  [ -f /tmp/rank_done ] && return 0
  # ★★ **체인 스크립트**가 살아 있으면 정상이다. exp_abcd 만 보면
  #   스텝 사이의 빈 순간(한 스플릿이 끝나고 다음이 뜨기 전)을 '죽음' 으로 오인해
  #   체인을 **중복 실행**한다(실제로 uni test 가 두 번 돌았다).
  alive "rank.sh" && return 0
  local k=rank
  FAIL[$k]=$(( ${FAIL[$k]:-0} + 1 ))
  if [ "${FAIL[$k]}" -gt $MAX_FAIL ]; then
    say "★ 랭커 체인 ${MAX_FAIL}회 실패 — 포기. 마지막 로그:"
    tail -5 all_log/au_research/hyb_test.log 2>/dev/null | tr -d '\000' | tee -a "$L"
    touch /tmp/rank_done
    return 1
  fi
  say "★ 랭커 체인이 죽었다 (${FAIL[$k]}/${MAX_FAIL}회) — 재시작"
  # ★ **잠금 파일을 지우면 안 된다** — 지우면 새 프로세스가 새 파일에 새 잠금을 얻어
  #   flock 이 무력화되고 체인이 중복 실행된다(실제로 3개가 동시에 돌았다).
  #   flock 은 이미 죽은 프로세스의 잠금을 자동으로 놓아 준다.
  nohup bash /tmp/rank.sh > /dev/null 2>&1 &
}

restart_halluc(){
  grep -q "SSReflect 환각 스텝만 제외" all_log/au_research/extref_ssr.log 2>/dev/null && return 0
  alive "probe_extref_halluc" && return 0
  return 0    # ★ 이미 끝났다 — 재시작하지 않는다 (결과 파일로 판정)
  local k=halluc
  FAIL[$k]=$(( ${FAIL[$k]:-0} + 1 ))
  if [ "${FAIL[$k]}" -gt $MAX_FAIL ]; then
    say "★ 환각률 측정 ${MAX_FAIL}회 실패 — 포기. 마지막 로그:"
    tail -5 all_log/au_research/extref_ssr.log 2>/dev/null | tee -a "$L"
    return 1
  fi
  say "★ 환각률 측정이 죽었다 (${FAIL[$k]}/${MAX_FAIL}회) — 재시작"
  nohup env PYTHONPATH=src nice -n 12 timeout 21600 python3 -u scripts/probe_extref_halluc.py 12000 \
      >> all_log/au_research/extref_ssr.log 2>&1 &
}

say "===== 감시 시작 (60초 주기 · 최대 ${MAX_FAIL}회 재시도) ====="
while true; do
  restart_rank
  restart_halluc
  if [ -f /tmp/rank_done ] && grep -q "SSReflect 환각 스텝만 제외" \
       all_log/au_research/extref_ssr.log 2>/dev/null; then
    say "===== 전부 완료 — 감시 종료 ====="
    break
  fi
  sleep 60
done
