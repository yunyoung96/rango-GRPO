#!/bin/bash
# v2 가 checkpoint-20000 에 도달하면 → 학습 정지 → rand200 → 학습 재개.
#   ★ v1 의 step 21,000 평가와 **같은 조건**(600초, GPU2×워커8=16)으로 맞춰 직접 비교한다.
#     v1 step21000 = 27.5%,  v1 step40000 = 31.9%,  기준선 rango = 33.5%(600s/w2)
#   ★ 평가 env 에 AUGMENT_V2=1 필수 — 학습과 프롬프트가 다르면(OOD) 성능이 실제보다 낮게 나온다.
cd /app/coq-modeling || exit 1
set -u
OUTM=models/rango-1.3b-augmented-v2-ft
STEP=${STEP:-20000}
CKPT=$OUTM/checkpoint-$STEP
RAND=data/compcert_bs2_rand200_idx.txt
WPG=${WPG:-8}
TIMEOUT=${TIMEOUT:-600}
RESULT=all_results/rango_v2_step${STEP}_rand200_t${TIMEOUT}_w$((WPG*2))
LOG=all_log/eval_v2_step${STEP}.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "===== v2 checkpoint-$STEP 대기 ====="
# ★ 대기 중 "학습 없음" 판정 주의:
#   · 다른 STEP 의 평가가 도는 동안에는 학습이 **의도적으로** 멈춰 있다(그 평가가 끝나면 재개).
#     그때 죽었다고 오판하면 이 예약이 취소된다 → run_all/tactic_gen_server/감시견도 '살아있음'으로 본다.
#   · 재시작 공백도 있으므로 연속 GRACE 회(기본 30회=30분) 비어 있을 때만 실패로 본다.
GRACE=${GRACE:-30}
gone=0
while [ ! -f "$CKPT/trainer_state.json" ] || [ ! -f "$CKPT/adapter_model.safetensors" ]; do
  sleep 60
  if pgrep -f "train_decoder.py|run_augmented_v2|run_all.py|tactic_gen_server|v2_watchdog" >/dev/null; then
    gone=0
  else
    gone=$((gone + 1))
    say "  학습/평가 프로세스 안 보임 ($gone/$GRACE)"
    [ "$gone" -ge "$GRACE" ] && { say "★ $GRACE 분 연속 부재 — 평가 취소"; exit 1; }
  fi
done
sleep 30
say "checkpoint-$STEP 확보 → 학습 정지 후 rand200"

pkill -9 -f run_augmented_v2 2>/dev/null
sleep 3
ps -eo pid,cmd | grep "[t]rain_decoder.py" | awk '{print $1}' | xargs -r kill -9 2>/dev/null
sleep 20
say "GPU 반납: $(nvidia-smi --query-gpu=memory.used --format=csv,noheader | tr '\n' ' ')"

say "rand200 시작 (200정리, ${TIMEOUT}s, GPU2 × 워커 $WPG)"
HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
EXEC_ADAPTER="$CKPT" \
AUGMENT_V2=1 RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 \
HARD_SEQ_LEN=4096 TYPES_TOKENS=300 DEFS_TOKENS=300 FUNC_DEFS_PATH=data/func_defs.json \
  python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" \
    --timeout "$TIMEOUT" --gpus 0,1 --workers "$WPG" --out "$RESULT" \
    --description "rango-augmented v2 step${STEP} rand200" >> "$LOG" 2>&1
ps -eo pid,cmd | grep "[t]actic_gen_server" | awk '{print $1}' | xargs -r kill -9 2>/dev/null
sleep 5

python3 - <<PY 2>&1 | tee -a "$LOG"
import glob, json, os
D="$RESULT/logs"
ok=fail=0
for f in glob.glob(D+"/*.txt"):
    t=open(f,errors="ignore").read()
    if "CURRENT RESULT: SUCCESS" in t: ok+=1
    elif "\nfailed" in t: fail+=1
print(f"\n■ v2 rand200 @ step $STEP (${TIMEOUT}s, 워커 $((WPG*2))): 성공 {ok}/{ok+fail} = {ok/max(ok+fail,1)*100:.1f}%")
print("   비교: v1 step21000 27.5% | v1 step40000 31.9% | 기준선 rango 33.5%(600s/w2)")
PY

say "v2 학습 재개"
# ★ PPID 1 로 완전 분리 — 이 방식이 아니면 부모 종료 시 함께 죽는다(v2 가 687 step 에서 그렇게 죽음)
nohup setsid bash all_log/run_augmented_v2_ddp.sh </dev/null >/dev/null 2>&1 &
disown -a 2>/dev/null || true
# 감시견도 평가 중 정지시켰으면 되살린다
pgrep -f v2_watchdog.sh >/dev/null || { nohup setsid bash all_log/v2_watchdog.sh </dev/null >/dev/null 2>&1 & disown -a 2>/dev/null || true; }
sleep 150
say "재개 확인: $(tr '\r' '\n' < all_log/ft_rango_augmented_v2.log | grep -aoE '[0-9]+/60000 \[[0-9:]+<[0-9:]+' | tail -1)"
say "===== 종료 ====="
