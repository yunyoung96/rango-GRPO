#!/bin/bash
# v2 평가 (워커 6) — 이 서버(Blackwell)에서 측정된 rango 기준선과 **조건 일치**.
#
# 왜 w6 인가:
#   기준선 all_results/rand200_rango_blackwell_g1w6 = rango(checkpoint-54500) · 이 서버(RTX PRO 6000
#   Blackwell) · 600s · **워커 6** · 74/200 = 37.0%.
#   워커 수는 confound 다 — CPU 경합으로 600초 안의 탐색량이 달라진다. w16 으로 재보니 load 39(32코어
#   초과)에 GPU 63~88% 로 떨어져 성능이 과소측정됐다. 기준선과 같은 w6 으로 맞춰야 비교가 성립한다.
#
# ★ 평가 env 는 학습과 동일(AUGMENT_V2 포함). 다르면 train/infer 불일치(OOD).
cd /app/coq-modeling || exit 1
set -u

# ★ 중복 실행 방지 — 평가가 겹치면 워커가 배로 늘어 CPU 경합이 터진다(실제로 w6 요청에 22개가 떴다:
#   이전 transfer 예약이 살아남아 rand200 과 동시에 hoare-tut 를 띄웠음).
exec 9>/tmp/.rango_eval.lock
if ! flock -n 9; then
  echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] ★ 다른 평가가 이미 실행 중 — 중복 실행 취소" >&2
  exit 1
fi
# 잔여 평가 프로세스 청소(이전 실행의 유령 방지)
for pid in $(ps -eo pid,cmd | grep -E "[r]un_all.py|[r]un_thm.py|[t]actic_gen_server" | awk "{print \$1}"); do
  kill -9 "$pid" 2>/dev/null
done
sleep 5
OUTM=models/rango-1.3b-augmented-v2-ft
CKPT=${CKPT:-$OUTM/checkpoint-50000}
STEP=$(basename "$CKPT" | sed 's/checkpoint-//')
TIMEOUT=${TIMEOUT:-600}
WPG=${WPG:-6}                       # GPU당 워커. 총 워커 = WPG × 2GPU
#   표기 규칙: g<GPU수>×w<GPU당>=<총합>  예) g2×w6=12 / 기준선 rango 는 g1×w6=6
TOTW=$((WPG*2))
RAND=data/compcert_bs2_rand200_idx.txt
TAG="g2xw${WPG}_tot${TOTW}"          # 결과 경로에 GPU수·GPU당·총합을 모두 남긴다
RESULT=all_results/rango_v2_step${STEP}_rand200_t${TIMEOUT}_${TAG}
LOG=all_log/eval_v2_${TAG}.log
DO_TRANSFER=${DO_TRANSFER:-1}       # rand200 후 hoare-tut/dblib 전이평가도 할지
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

# 학습이 돌고 있으면 정지(평가 중 GPU/CPU 경합 방지)
if pgrep -f train_decoder.py >/dev/null; then
  say "학습 일시정지"
  pkill -9 -f v2_watchdog.sh 2>/dev/null
  pkill -9 -f run_augmented_v2 2>/dev/null
  sleep 3
  ps -eo pid,cmd | grep "[t]rain_decoder.py" | awk '{print $1}' | xargs -r kill -9 2>/dev/null
  sleep 20
fi

say "===== v2 step${STEP} 평가 (${TIMEOUT}s, g2×w${WPG}=${TOTW}) ====="
say "  대상: $CKPT"
say "  GPU: $(nvidia-smi --query-gpu=memory.used --format=csv,noheader | tr '\n' ' ')  load: $(uptime | sed 's/.*average: //')"

run_set(){    # $1=이름  $2=인덱스파일  $3=결과경로
  local nm=$1 idxf=$2 out=$3
  local n=$(wc -l < "$idxf")
  say "  [$nm] $n 정리 시작"
  rm -rf "$out"
  HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
  EXEC_ADAPTER="$CKPT" \
  AUGMENT_V2=1 RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 \
  HARD_SEQ_LEN=4096 TYPES_TOKENS=300 DEFS_TOKENS=300 FUNC_DEFS_PATH=data/func_defs.json \
    python3 scripts/run_all.py --alias rango-grpo --idx-file "$idxf" \
      --timeout "$TIMEOUT" --gpus 0,1 --workers "$WPG" --out "$out" \
      --description "rango-1.3b-augmented-v2 step${STEP} $nm (${TIMEOUT}s g2xw${WPG}=${TOTW})" >> "$LOG" 2>&1
  ps -eo pid,cmd | grep "[t]actic_gen_server" | awk '{print $1}' | xargs -r kill -9 2>/dev/null
  sleep 5
  local S=$(grep -al "CURRENT RESULT: SUCCESS" $out/logs/*.txt 2>/dev/null | wc -l)
  local F=$(grep -al "^failed" $out/logs/*.txt 2>/dev/null | wc -l)
  say "  [$nm] 성공 $S / 완료 $((S+F)) / 전체 $n"
}

run_set rand200 "$RAND" "$RESULT"

if [ "$DO_TRANSFER" = "1" ]; then
  run_set hoare-tut data/hoare-tut_all_idx.txt "all_results/rango_v2_step${STEP}_hoare-tut_t${TIMEOUT}_${TAG}"
  run_set dblib     data/dblib_all_idx.txt     "all_results/rango_v2_step${STEP}_dblib_t${TIMEOUT}_${TAG}"
fi

STEP=$STEP TOTW=$TOTW WPG=$WPG NGPU=2 TIMEOUT=$TIMEOUT TAG=$TAG python3 scripts/report_eval.py 2>&1 | tee -a "$LOG"

say "학습 재개"
nohup setsid bash all_log/run_augmented_v2_ddp.sh </dev/null >/dev/null 2>&1 &
disown -a 2>/dev/null || true
sleep 5
pgrep -f v2_watchdog.sh >/dev/null || { nohup setsid bash all_log/v2_watchdog.sh </dev/null >/dev/null 2>&1 & disown -a 2>/dev/null || true; }
sleep 120
say "재개 확인: $(tr '\r' '\n' < all_log/ft_rango_augmented_v2.log | grep -aoE '[0-9]+/60000 \[[0-9:]+<[0-9:]+' | tail -1)"
say "===== 종료 ====="
