#!/bin/bash
# 중간 점검: checkpoint-20000 으로 rand200 평가. **학습은 계속 돌린 채** GPU0 만 빌려 쓴다.
#   · 학습(DDP)이 두 GPU 를 쓰므로 GPU0 경합 → 학습 속도가 그동안 느려진다(동기 DDP라 전체가 느려짐).
#   · 워커 2 고정: rand200 성공률은 워커수에 confound 가 있어 기존 결과와 비교하려면 w2 여야 한다.
#   · ★ 학습과 같은 프롬프트 env(재랭킹+[TYPES]+[DEFINITIONS]) — 안 그러면 train/infer 불일치로
#     성능이 실제보다 낮게 나온다.
cd /app/coq-modeling || exit 1
set -u
OUTM=models/rango-1.3b-augmented-ft
CKPT=$OUTM/checkpoint-20000
RAND=data/compcert_bs2_rand200_idx.txt
RESULT=all_results/rango_aug_step20000_rand200_t300_w2
LOG=all_log/eval_step20000.log
TIMEOUT=${TIMEOUT:-300}
GPUS=${GPUS:-0}
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "===== checkpoint-20000 rand200 중간평가 ====="

# 1) checkpoint-20000 완성 대기(저장 도중 잡지 않도록 trainer_state.json 까지 확인)
while [ ! -f "$CKPT/trainer_state.json" ] || [ ! -f "$CKPT/adapter_model.safetensors" ]; do
  sleep 60
  if ! pgrep -f "train_decoder.py|ft_rango_augmented" >/dev/null; then
    say "★ 학습이 멈춤 — 20000 도달 전. 평가 취소"; exit 1
  fi
done
sleep 30      # 저장 직후 파일 flush 여유
say "checkpoint-20000 확보 → 평가 시작 (GPU $GPUS, workers 2, timeout ${TIMEOUT}s)"

HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
EXEC_ADAPTER="$CKPT" RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 \
IND_INDEX_PATH=data/ind_constructors_clean.json TYPES_TOKENS=200 \
FUNC_DEFS_PATH=data/func_defs.json DEFS_TOKENS=200 DEFS_MAX=5 DEFS_MAX_BODY=80 DEFS_MAX_SIG=40 \
  python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" \
    --timeout "$TIMEOUT" --gpus "$GPUS" --workers 2 --out "$RESULT" \
    --description "rango-1.3b-augmented-ft step20000 rand200 (rerank+TYPES+DEFS)" >> "$LOG" 2>&1
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null

python3 - <<PY 2>&1 | tee -a "$LOG"
import json, pathlib
p = pathlib.Path("$RESULT/summary.json")
if p.exists():
    r = json.load(p.open())["results"]
    ok = sum(1 for x in r if x.get("success"))
    print(f"\n■ rand200 @ step20000 (@${TIMEOUT}s, w2): 성공 {ok}/{len(r)} = {ok/max(len(r),1)*100:.1f}%")
else:
    print("결과 파일 없음: $RESULT/summary.json")
PY
say "===== 중간평가 종료 ====="
