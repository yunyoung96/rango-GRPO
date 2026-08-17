#!/bin/bash
# SFT 없는 베이스 모델의 rand200 **뒤 50개** 증명 생성 능력 비교.
#
#  · 대상: data/compcert_bs2_rand200_idx.txt 의 151~200번째 (--start 150 --num 50)
#  · 프롬프트 env 는 v2 평가(all_log/eval_v2_final.sh)와 **동일** — 프롬프트 차이로 인한
#    교란을 없애고 '모델만' 바꾼 비교가 되도록.
#  · ZEROSHOT_CLEAN=1 : SFT 안 한 모델은 tactic 한 줄이 아니라 설명문·마크다운을 뱉는다.
#    (실측: 3B 가 "```coq\nauto\n```\nThis script defines the theorem ..." → 전부 구문오류)
#    첫 tactic 한 줄만 잘라내야 비교가 성립한다.
#  · 워커는 **모든 모델 동일하게 GPU당 4** — 성공률이 워커수에 confound 되므로 고정.
#    (7B 4개 동시 = 60GB 로 한 장에 들어가는 최대치)
#
# 사용: bash all_log/eval_zeroshot_last50.sh <GPU> <이름> [어댑터경로] [CLEAN]
#   어댑터경로 생략 시 models/<이름>/base (SFT 없는 베이스 모델)
#   CLEAN=0 이면 정제기를 끈다 — **SFT 모델(v2 등)은 반드시 0**. tactic 한 줄을 이미 잘 뱉으므로
#   정제기를 걸면 오히려 멀쩡한 출력을 건드린다.
cd /app/coq-modeling || exit 1
set -u
G=$1; M=$2
ADAPTER=${3:-models/${M}/base}
CLEAN=${4:-1}
W=${W:-4}
RAND=data/compcert_bs2_rand200_idx.txt
OUT=all_results/zeroshot_last50_${M}_t600_g1xw${W}
LOG=all_log/eval_zeroshot_${M}.log
echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] === $M (GPU$G, w$W, adapter=$ADAPTER, clean=$CLEAN) 시작 ===" | tee "$LOG"
EXEC_ADAPTER="$ADAPTER" ZEROSHOT_CLEAN="$CLEAN" \
AUGMENT_V2=1 RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 \
HARD_SEQ_LEN=4096 TYPES_TOKENS=300 DEFS_TOKENS=300 FUNC_DEFS_PATH=data/func_defs.json \
HF_HUB_OFFLINE=1 \
  python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" \
    --start 150 --num 50 --timeout 600 --gpus "$G" --workers "$W" --out "$OUT" \
    --description "${M} rand200 뒤50 (600s g1xw${W}, clean=${CLEAN})" >> "$LOG" 2>&1
echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] === $M 완료 ===" | tee -a "$LOG"
python3 -c "
import json;d=json.load(open('$OUT/summary.json'))
print(f\"  {'$M'}: 성공 {d['success']}/{d['done']} = {d['success']/max(d['done'],1)*100:.1f}%\")
" 2>/dev/null | tee -a "$LOG"
