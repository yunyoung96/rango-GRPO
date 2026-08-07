#!/bin/bash
# ★ Type-ablation — "모델이 [TYPES]/[DEFINITIONS] 를 실제로 읽는가"를 가르는 결정적 실험.
#
# 배경: v2(step60000)는 **오염된 인덱스**로 학습됐다. build_func_defs.py 가 이름 충돌을
#   프로젝트 단위로만 구분하고 "같은 이름이 여럿이면 짧은 쪽"을 남긴 탓에, goal 이
#   `forall x : Lst, append x nil = x` 인데 다른 파일의 `append (l1 : lst) ... | Nil | Cons`
#   를 주입했다. 학습 예제의 46%가 영향, [DEFINITIONS] 항목의 24.8%가 엉뚱한 파일 정의였다.
#   → 지금까지의 음성 결과는 "오염된 주입은 효과 없다"까지만 말한다.
#
# 세 조건을 **같은 모델·같은 정리·같은 조건**으로 비교한다(프롬프트 포맷은 고정, 내용만 변경):
#   (a) polluted : 학습 때 쓴 오염 인덱스(func_defs.json)        ← train-matched
#   (b) fixed    : 파일 단위로 고친 인덱스(func_defs_v3.json)
#   (c) empty    : 헤더 유지 + 내용 '(none)'  (ABLATE_TYPES/DEFS=1)
#
# 해석:
#   (a)≈(b)≈(c) → 모델이 섹션을 아예 안 읽음(신호 희석). 학습 레시피를 바꿔야 함.
#   (b) > (a)   → 읽고 있고 오염이 발목을 잡았음 → 깨끗한 데이터로 재학습할 가치 있음.
#   (a) > (c)   → 오염된 것이라도 없는 것보단 나음.
#
# ※ Qwen-7B FULL 학습이 GPU 를 함께 쓰는 중이라 워커를 줄여(g2×w3=6) 경합을 줄인다.
#   세 조건 모두 같은 부하에서 순차 실행되므로 **조건 간 비교는 유효**하다(절대값만 낮아짐).
cd /app/coq-modeling || exit 1
set -u
exec 9>/tmp/.rango_eval.lock
flock -n 9 || { echo "다른 평가 실행 중 — 취소"; exit 1; }

CKPT=models/rango-1.3b-augmented-v2-ft/checkpoint-60000
RAND=data/compcert_bs2_rand200_idx.txt
TIMEOUT=${TIMEOUT:-600}
WPG=${WPG:-3}; TOTW=$((WPG*2)); TAG="g2xw${WPG}_tot${TOTW}"
LOG=all_log/ablation_types.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "===== Type-ablation (${TIMEOUT}s, ${TAG}) ====="
say "  모델: $CKPT"

run_cond(){    # $1=조건명  $2=FUNC_DEFS_PATH  $3=ABLATE(0|1)
  local name=$1 idxpath=$2 ab=$3
  local out="all_results/ablation_v2_${name}_t${TIMEOUT}_${TAG}"
  if [ -s "$out/summary.json" ]; then say "  [$name] 이미 완료 — 건너뜀"; return; fi
  say "  [$name] 시작  (FUNC_DEFS_PATH=$idxpath, ABLATE=$ab)"
  HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
  EXEC_ADAPTER="$CKPT" AUGMENT_V2=1 RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 \
  HARD_SEQ_LEN=4096 TYPES_TOKENS=300 DEFS_TOKENS=300 \
  FUNC_DEFS_PATH="$idxpath" ABLATE_TYPES="$ab" ABLATE_DEFS="$ab" \
    python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" \
      --timeout "$TIMEOUT" --gpus 0,1 --workers "$WPG" --out "$out" \
      --description "ablation $name (v2 step60000, ${TIMEOUT}s ${TAG})" >> "$LOG" 2>&1
  ps -eo pid,cmd | grep "[t]actic_gen_server" | awk '{print $1}' | xargs -r kill -9 2>/dev/null
  sleep 5
  local S=$(grep -al "CURRENT RESULT: SUCCESS" $out/logs/*.txt 2>/dev/null | wc -l)
  local F=$(grep -al "^failed" $out/logs/*.txt 2>/dev/null | wc -l)
  say "  [$name] 성공 $S / 완료 $((S+F))"
  TAG=$TAG TIMEOUT=$TIMEOUT python3 scripts/report_ablation.py 2>&1 | tee -a "$LOG"
}

# 4조건. 모델은 (wrong) 으로 학습됐다 = train-matched.
#   모델이 섹션을 읽는다면:  clean ≥ wrong > corrupt ≈ empty  가 나와야 한다.
#   네 조건이 모두 비슷하면 → 안 읽는 것(신호 희석) → 학습 레시피를 바꿔야 함.
run_cond wrong   data/func_defs.json         0   # 다른 파일의 동명 정의(학습과 동일, 오염본)
run_cond clean   data/func_defs_v3.json      0   # 파일단위로 고친 올바른 정의
run_cond corrupt data/func_defs_corrupt.json 0   # 생성자 개수·이름 조작(형식·길이는 동일)
run_cond empty   data/func_defs_v3.json      1   # 헤더만, 내용 (none)

say "===== Type-ablation 종료 ====="
