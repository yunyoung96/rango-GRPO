#!/bin/bash
# v5(Qwen3B) 평가 — **학습과 동일한 프롬프트 env** + Qwen 전용 보정 2가지.
#
#  ★ TACTIC_LEADING_NL=1 (필수)
#    v5 는 STRIP_TARGET_NL=1 로 학습해 tactic 을 **선행 개행 없이** 뱉는다.
#    탐색기는 cur_proof_script + tactic 으로 이어붙이므로, 개행이 없으면
#    "...end.Proof." 가 되어 Coq 이 한정이름(qualified name)으로 파싱한다 → 전부 INVALID.
#    이 변수를 빼면 평가가 통째로 0 이 된다.
#
#  ★ NORMALIZE_NAMES 는 켜지 않는다
#    정규화는 **학습 시 증강**(rate 0.5)이다. 추론에서는 실제 이름을 그대로 써야 한다.
#
#  ★ FUNC_DEFS_PATH 는 v3 (학습과 동일). v2 인덱스를 쓰면 다른 정의가 들어가 train/infer 불일치.
#
# 사용: bash all_log/eval_v5.sh <체크포인트> [출력디렉토리이름]
cd /app/coq-modeling || exit 1
set -u
CKPT=$1
NAME=${2:-v5-$(basename "$CKPT")}
RAND=data/compcert_bs2_rand200_idx.txt
OUT=all_results/${NAME}_rand200_t600_g2xw6
LOG=all_log/eval_${NAME}.log
echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] v5 평가: $CKPT" | tee "$LOG"
EXEC_ADAPTER="$CKPT" TACTIC_LEADING_NL=1 \
AUGMENT_V2=1 RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 \
HARD_SEQ_LEN=4096 TYPES_TOKENS=300 DEFS_TOKENS=300 FUNC_DEFS_PATH=data/func_defs_v3.json \
HF_HUB_OFFLINE=1 \
  python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" \
    --timeout 600 --gpus 0,1 --workers 6 --out "$OUT" \
    --description "v5 Qwen3B $(basename "$CKPT") rand200 (600s g2xw6)" >> "$LOG" 2>&1
python3 -c "
import json;d=json.load(open('$OUT/summary.json'))
print(f\"v5 {d['success']}/{d['done']} = {d['success']/max(d['done'],1)*100:.1f}%\")" | tee -a "$LOG"
