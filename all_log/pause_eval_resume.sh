#!/bin/bash
# 학습 일시정지 → rand200(워커 최대) → 학습 자동 재개.
#   · 정지 시점의 최신 체크포인트에서 재개하므로 손실은 마지막 저장 이후 step 뿐이다.
#   · ★ 워커 수 주의: rand200 성공률은 워커수에 confound 가 있다(CPU 경합으로 300초 안에 도는 탐색량이
#     달라짐). 기존 w2 결과와 직접 비교하려면 같은 워커수로 재측정해야 한다 — 여기 결과는 '빠른 중간확인'용.
cd /app/coq-modeling || exit 1
set -u
CKPT=${CKPT:-models/rango-1.3b-augmented-ft/checkpoint-21000}
RAND=data/compcert_bs2_rand200_idx.txt
WPG=${WPG:-8}                       # GPU 당 워커 (총 = WPG × 2)
TIMEOUT=${TIMEOUT:-300}
RESULT=all_results/rango_aug_$(basename $CKPT)_rand200_t${TIMEOUT}_w$((WPG*2))   # 체크포인트별로 분리
LOG=all_log/pause_eval_resume.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "===== 학습 정지 → rand200(워커 $((WPG*2))) → 재개 ====="
say "평가 대상: $CKPT"

# ── 1) 학습 정지 ──
STEP=$(tr '\r' '\n' < all_log/ft_rango_augmented.log | grep -aoE "[0-9]+/60000" | tail -1)
say "정지 직전 step: $STEP (최신 체크포인트에서 재개 예정)"
pkill -9 -f ft_rango_augmented 2>/dev/null
pkill -9 -f train_decoder.py 2>/dev/null
sleep 20
say "학습 정지 완료 — GPU 반납: $(nvidia-smi --query-gpu=memory.used --format=csv,noheader | tr '\n' ' ')"

# ── 2) rand200 ──
say "rand200 시작 (200정리, timeout ${TIMEOUT}s, GPU 2개 × 워커 ${WPG})"
HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
EXEC_ADAPTER="$CKPT" RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 \
IND_INDEX_PATH=data/ind_constructors_clean.json TYPES_TOKENS=200 \
FUNC_DEFS_PATH=data/func_defs.json DEFS_TOKENS=200 DEFS_MAX=5 DEFS_MAX_BODY=80 DEFS_MAX_SIG=40 \
  python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" \
    --timeout "$TIMEOUT" --gpus 0,1 --workers "$WPG" --out "$RESULT" \
    --description "rango-augmented $(basename $CKPT) rand200 w$((WPG*2))" >> "$LOG" 2>&1
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
sleep 5

python3 - <<PY 2>&1 | tee -a "$LOG"
import json, pathlib
p = pathlib.Path("$RESULT/summary.json")
if p.exists():
    r = json.load(p.open())["results"]
    ok = sum(1 for x in r if x.get("success"))
    print(f"\n■ rand200 @ $(basename $CKPT) (timeout ${TIMEOUT}s, 워커 $((WPG*2))): 성공 {ok}/{len(r)} = {ok/max(len(r),1)*100:.1f}%")
else:
    print("결과 파일 없음")
PY

# ── 3) 학습 재개 ──
say "학습 재개(최신 정상 체크포인트에서 이어서)"
setsid nohup bash all_log/ft_rango_augmented_v2.sh > /dev/null 2>&1 < /dev/null &
sleep 120
say "재개 확인: $(tr '\r' '\n' < all_log/ft_rango_augmented.log | grep -aoE '[0-9]+/60000 \[[0-9:]+<[0-9:]+' | tail -1)"
say "===== 완료 ====="
