#!/bin/bash
# v2 step50000 → **전이(transfer) 평가**: hoare-tut(25) + dblib(138).
#   rand200(CompCert) 이 끝난 뒤 이어서 돈다. 학습 재개보다 먼저 실행되도록 rand200 종료를 직접 감시.
#
# 왜 이 두 프로젝트인가:
#   · CompCert 는 test 정리의 59%(6,091/10,396)를 차지하고 train 에도 인접 코드가 많다.
#   · hoare-tut(호어 논리)·dblib(de Bruijn 인덱스 라이브러리)는 **도메인이 다르고 규모가 작다**
#     → 명세가 강조한 "전이율(train 에 없던 타입/함수가 test 에 나올 때 적용되나)" 측정에 적합.
#   · 정리 수가 작아(합 163) 600초 timeout 에서도 1시간 안쪽이면 끝난다.
#
# ★ 평가 env 는 학습과 동일해야 한다(AUGMENT_V2 포함). 다르면 train/infer 불일치(OOD).
cd /app/coq-modeling || exit 1
set -u
OUTM=models/rango-1.3b-augmented-v2-ft
CKPT=${CKPT:-$OUTM/checkpoint-50000}
TIMEOUT=${TIMEOUT:-600}
WPG=${WPG:-8}
LOG=all_log/eval_v2_transfer.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "===== 전이평가 대기 (rand200 종료 후) ====="
# rand200 이 도는 동안 대기
while pgrep -f "run_all.py .*rand200|run_all.py .*compcert_bs2_rand200" >/dev/null; do sleep 60; done
sleep 30
say "rand200 종료 감지 — 전이평가 시작"

# 학습이 재개됐으면 잠시 멈춘다(평가 중 GPU 경합 방지)
if pgrep -f train_decoder.py >/dev/null; then
  say "학습 일시정지(전이평가용)"
  pkill -9 -f v2_watchdog.sh 2>/dev/null
  pkill -9 -f run_augmented_v2 2>/dev/null
  sleep 3
  ps -eo pid,cmd | grep "[t]rain_decoder.py" | awk '{print $1}' | xargs -r kill -9 2>/dev/null
  sleep 20
fi
say "GPU: $(nvidia-smi --query-gpu=memory.used --format=csv,noheader | tr '\n' ' ')"

run_one(){    # $1 = 프로젝트명
  local proj=$1
  local idxf=data/${proj}_all_idx.txt
  local out=all_results/rango_v2_step50000_${proj}_t${TIMEOUT}_w$((WPG*2))
  local n=$(wc -l < "$idxf")
  say "  [$proj] $n 정리 평가 시작"
  HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
  EXEC_ADAPTER="$CKPT" \
  AUGMENT_V2=1 RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 \
  HARD_SEQ_LEN=4096 TYPES_TOKENS=300 DEFS_TOKENS=300 FUNC_DEFS_PATH=data/func_defs.json \
    python3 scripts/run_all.py --alias rango-grpo --idx-file "$idxf" \
      --timeout "$TIMEOUT" --gpus 0,1 --workers "$WPG" --out "$out" \
      --description "v2 step50000 transfer $proj" >> "$LOG" 2>&1
  ps -eo pid,cmd | grep "[t]actic_gen_server" | awk '{print $1}' | xargs -r kill -9 2>/dev/null
  sleep 5
  local S=$(grep -al "CURRENT RESULT: SUCCESS" $out/logs/*.txt 2>/dev/null | wc -l)
  local F=$(grep -al "^failed" $out/logs/*.txt 2>/dev/null | wc -l)
  say "  [$proj] 성공 $S / 완료 $((S+F)) (전체 $n)"
}

run_one hoare-tut
run_one dblib

python3 - <<'PY' 2>&1 | tee -a "$LOG"
import glob, os
print("\n■ v2 step50000 전이 평가 (600s, 워커 16)")
print(f"   {'프로젝트':14s} {'성공':>6} {'완료':>6} {'성공률':>8}")
print("   " + "-"*38)
tot_ok = tot_n = 0
for p in ("hoare-tut", "dblib"):
    d = f"all_results/rango_v2_step50000_{p}_t600_w16/logs"
    ok = n = 0
    for f in glob.glob(d + "/*.txt"):
        t = open(f, errors="ignore").read()
        if "CURRENT RESULT: SUCCESS" in t: ok += 1; n += 1
        elif "\nfailed" in t: n += 1
    tot_ok += ok; tot_n += n
    print(f"   {p:14s} {ok:>6} {n:>6} {ok/max(n,1)*100:>7.1f}%")
print("   " + "-"*38)
print(f"   {'★ 합계(프로젝트 아님)':14s} {tot_ok:>6} {tot_n:>6} {tot_ok/max(tot_n,1)*100:>7.1f}%")
print("\n   참고: CompCert rand200 은 별도(같은 체크포인트, 600s/w16)")
PY

say "학습 재개"
nohup setsid bash all_log/run_augmented_v2_ddp.sh </dev/null >/dev/null 2>&1 &
disown -a 2>/dev/null || true
sleep 5
pgrep -f v2_watchdog.sh >/dev/null || { nohup setsid bash all_log/v2_watchdog.sh </dev/null >/dev/null 2>&1 & disown -a 2>/dev/null || true; }
sleep 120
say "재개 확인: $(tr '\r' '\n' < all_log/ft_rango_augmented_v2.log | grep -aoE '[0-9]+/60000 \[[0-9:]+<[0-9:]+' | tail -1)"
say "===== 전이평가 종료 ====="
