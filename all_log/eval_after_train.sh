#!/bin/bash
# v2 완주 대기 → ① rand200(CompCert) ② 다른 test 프로젝트 전체 — **v2 와 rango 를 나란히** 평가.
#
# ★ 왜 rango 도 같이 도는가:
#   이 저장소에는 CompCert 외 프로젝트로 rango 를 평가한 결과가 **하나도 없다**(확인함).
#   기준선 없이 v2 만 재면 숫자가 나와도 해석이 안 된다. 같은 정리·같은 조건으로 둘 다 돌려야
#   비교가 성립한다. (rand200 은 기존 기준선 rand200_rango_blackwell_g1w6 이 있으나, 조건을
#   완전히 맞추기 위해 여기서도 같이 돌린다.)
#
# ★ 조건: 600초 · g2×w6=12 · 학습과 동일 프롬프트 env(AUGMENT_V2 포함, v2 에만).
#   rango 는 원본이므로 증강 env 를 끈다(원래 학습된 프롬프트 형식).
cd /app/coq-modeling || exit 1
set -u

exec 9>/tmp/.rango_eval.lock
if ! flock -n 9; then echo "다른 평가 실행 중 — 취소"; exit 1; fi

OUTM=models/rango-1.3b-augmented-v2-ft
TIMEOUT=${TIMEOUT:-600}
WPG=${WPG:-6}
TOTW=$((WPG*2))
TAG="g2xw${WPG}_tot${TOTW}"
LOG=all_log/eval_after_train.log
GRACE=${GRACE:-60}
RANGO_CKPT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "===== 학습 완주 대기 → 전체 평가 (${TIMEOUT}s, ${TAG}) ====="

# ── 1) 완주 대기 (AUGMENT.json = rc=0 정상 종료 표식) ──
gone=0
while [ ! -f "$OUTM/AUGMENT.json" ]; do
  sleep 60
  if pgrep -f "train_decoder.py|run_augmented_v2|v2_watchdog" >/dev/null; then gone=0
  else
    gone=$((gone+1)); say "  학습 프로세스 안 보임 ($gone/$GRACE)"
    [ "$gone" -ge "$GRACE" ] && { say "★ 학습 실패로 판단 — 평가 중단"; exit 1; }
  fi
done
say "완주 감지"

# 최신 정상 체크포인트
CKPT=""
for d in $(ls -d "$OUTM"/checkpoint-* 2>/dev/null | sed 's/.*checkpoint-//' | sort -rn); do
  [ -f "$OUTM/checkpoint-$d/adapter_model.safetensors" ] && { CKPT="$OUTM/checkpoint-$d"; break; }
done
[ -n "$CKPT" ] || { say "★ 체크포인트 없음"; exit 1; }
STEP=$(basename "$CKPT" | sed 's/checkpoint-//')
say "평가 대상: $CKPT (v2)  /  $RANGO_CKPT (rango 원본)"

pkill -9 -f v2_watchdog.sh 2>/dev/null
sleep 5

run_eval(){   # $1=모델(v2|rango)  $2=평가셋이름  $3=인덱스파일
  local model=$1 name=$2 idxf=$3
  local out="all_results/${model}_step${STEP}_${name}_t${TIMEOUT}_${TAG}"
  [ "$model" = "rango" ] && out="all_results/rango54500_${name}_t${TIMEOUT}_${TAG}"
  if [ -s "$out/summary.json" ]; then say "  [$model/$name] 이미 완료 — 건너뜀"; return; fi
  local n=$(wc -l < "$idxf")
  say "  [$model/$name] $n 정리 시작"
  if [ "$model" = "v2" ]; then
    HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
    EXEC_ADAPTER="$CKPT" AUGMENT_V2=1 RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 \
    HARD_SEQ_LEN=4096 TYPES_TOKENS=300 DEFS_TOKENS=300 FUNC_DEFS_PATH=data/func_defs.json \
      python3 scripts/run_all.py --alias rango-grpo --idx-file "$idxf" \
        --timeout "$TIMEOUT" --gpus 0,1 --workers "$WPG" --out "$out" \
        --description "augmented-v2 step${STEP} $name (${TIMEOUT}s ${TAG})" >> "$LOG" 2>&1
  else
    HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
      python3 scripts/run_all.py --alias rango --idx-file "$idxf" \
        --timeout "$TIMEOUT" --gpus 0,1 --workers "$WPG" --out "$out" \
        --description "rango checkpoint-54500 $name (${TIMEOUT}s ${TAG})" >> "$LOG" 2>&1
  fi
  ps -eo pid,cmd | grep "[t]actic_gen_server" | awk '{print $1}' | xargs -r kill -9 2>/dev/null
  sleep 5
  local S=$(grep -al "CURRENT RESULT: SUCCESS" $out/logs/*.txt 2>/dev/null | wc -l)
  local F=$(grep -al "^failed" $out/logs/*.txt 2>/dev/null | wc -l)
  say "  [$model/$name] 성공 $S / 완료 $((S+F)) / 전체 $n"
}

# ── 2) rand200 (CompCert) — v2 만(rango 기준선은 기존 결과 사용) ──
run_eval v2 rand200 data/compcert_bs2_rand200_idx.txt

# ── 3) 다른 test 프로젝트 — 작은 것부터(빨리 결과가 나오게), v2 와 rango 둘 다 ──
for p in hoare-tut dblib ext-lib zorns-lemma zfc huffman poltac reglang buchberger math-classes fourcolor; do
  f="data/test_${p}_idx.txt"
  [ -s "$f" ] || continue
  run_eval v2    "$p" "$f"
  run_eval rango "$p" "$f"
  STEP=$STEP TIMEOUT=$TIMEOUT TAG=$TAG python3 scripts/report_transfer.py 2>&1 | tee -a "$LOG"
done

say "===== 전체 평가 종료 ====="
