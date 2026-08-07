#!/bin/bash
# 학습 완료 → rand200 평가 자동 실행.
#   · 완료 판정: ft_rango_augmented.sh 가 rc=0 일 때만 쓰는 AUGMENT.json 존재 (부분학습으로 평가 안 함)
#   · ★ 평가도 학습과 **같은 프롬프트 env**(RERANK_PREMISES=1 INJECT_TYPES=1) 로 — 안 그러면 train/infer
#     불일치(OOD)라 성능이 실제보다 낮게 나온다(REVIEW R1).
#   · 워커 2 고정: rand200 성공률은 워커수에 confound 가 있어 기존 결과와 비교하려면 w2 로 맞춰야 한다.
cd /app/coq-modeling || exit 1
set -u
OUTM=models/rango-1.3b-augmented-ft
RAND=data/compcert_bs2_rand200_idx.txt
TIMEOUT=${TIMEOUT:-600}
RESULT=all_results/rango_aug_final_rand200_t${TIMEOUT}_w2
LOG=all_log/chain_eval_rand200.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "===== rand200 평가 체인 시작 (학습 완료 대기) ====="

# ── 1) 학습 완료 대기 ──
#   ★ 재시작·전환 중에는 프로세스가 잠깐 사라진다(실측: 동적패딩 전환 시 15초 공백).
#     한 번 안 보인다고 중단하면 안 되므로, **연속 GRACE 회**(기본 10회=20분) 비어 있을 때만 실패로 본다.
GRACE=${GRACE:-180}   # 120초 × 180 = 6시간 — 중간평가로 학습이 오래 멈춰도 안 죽게
gone=0
while :; do
  [ -f "$OUTM/AUGMENT.json" ] && break
  if pgrep -f "ft_rango_augmented(_v2)?\.sh|chain_warm_then_train\.sh|train_decoder\.py|warm_example_cache|switch_to_dynpad" >/dev/null; then
    gone=0
  else
    gone=$((gone + 1))
    say "  학습 프로세스 안 보임 ($gone/$GRACE) — 재시작 중일 수 있어 대기"
    if [ "$gone" -ge "$GRACE" ]; then
      say "★ $GRACE 회 연속 학습 프로세스 없음 — 평가 중단(수동 확인: all_log/ft_rango_augmented.log)"
      exit 1
    fi
  fi
  sleep 120
done
say "학습 완료 감지"

# ── 2) 평가할 체크포인트 선택(최신 정상 checkpoint-N) ──
CKPT=""
for d in $(ls -d "$OUTM"/checkpoint-* 2>/dev/null | sed 's/.*checkpoint-//' | sort -rn); do
  p="$OUTM/checkpoint-$d"
  if [ -f "$p/adapter_model.safetensors" ]; then CKPT="$p"; break; fi
done
[ -n "$CKPT" ] || { say "★ 평가할 체크포인트 없음 — 중단"; exit 1; }
say "평가 대상: $CKPT"

# ── 3) rand200 (@${TIMEOUT}s, GPU 2개, 워커 2) ──
if [ -s "$RESULT/summary.json" ] && [ "$(python3 -c "import json;print(len(json.load(open('$RESULT/summary.json'))['results']))" 2>/dev/null || echo 0)" -ge 200 ]; then
  say "이미 완료된 결과 있음: $RESULT"
else
  say "rand200 실행 (200정리, timeout ${TIMEOUT}s, gpus 0,1, workers 2)"
  HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
  EXEC_ADAPTER="$CKPT" RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 \
  IND_INDEX_PATH=data/ind_constructors_clean.json TYPES_TOKENS=200 \
  FUNC_DEFS_PATH=data/func_defs.json DEFS_TOKENS=200 DEFS_MAX=5 DEFS_MAX_BODY=80 DEFS_MAX_SIG=40 \
    python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" \
      --timeout "$TIMEOUT" --gpus 0,1 --workers 2 --out "$RESULT" \
      --description "rango-1.3b-augmented-ft rand200 (rerank+TYPES)" >> "$LOG" 2>&1
  pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
fi

# ── 4) 결과 요약 ──
python3 - <<PY 2>&1 | tee -a "$LOG"
import json, pathlib
p = pathlib.Path("$RESULT/summary.json")
if p.exists():
    r = json.load(p.open())["results"]
    ok = sum(1 for x in r if x.get("success"))
    print(f"\n■ rand200 결과 (rango-1.3b-augmented-ft, @${TIMEOUT}s, w2)")
    print(f"   성공 {ok}/{len(r)} = {ok/max(len(r),1)*100:.1f}%")
else:
    print("결과 파일 없음: $RESULT/summary.json")
PY
say "===== rand200 평가 체인 종료 ====="
