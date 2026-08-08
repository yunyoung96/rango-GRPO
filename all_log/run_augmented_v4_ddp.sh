#!/bin/bash
# rango-augmented **v2** 학습 — GPU 1장(기본 GPU1). v1 과 동시 실행 가능.
#   v2 = [TYPES] 정의문(생성자 시그니처)+재귀 / [DEFINITIONS] 우리 시드+재귀 / 두 섹션 **맨 뒤** + 길이보장.
#   v1 과 같은 것: 코퍼스·셔플순서·LoRA·LR·max_steps(60000)·유효배치 32. 다른 것은 프롬프트 구성뿐.
#   중단복구: save_steps 1000 저장, 5000 배수만 보존, 죽으면 최신 정상 체크포인트에서 자동 재개.
cd /app/coq-modeling || exit 1
set -u
CONF=${CONF:-all_log/ft_rango_augmented_v4_conf.yaml}
NPROC=${NPROC:-2}
OUT=$(python3 -c "import yaml;print(yaml.safe_load(open('$CONF'))['output_dir'])")
LOG=all_log/ft_rango_augmented_v4.log
MAX_RETRY=${MAX_RETRY:-50}
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

# 최신 **정상** 체크포인트에서 재개할 conf 생성(손상본은 격리 — v1 에서 겪은 함정)
mkconf_resume(){
  local best="" d p
  for d in $(ls -d "$OUT"/checkpoint-* 2>/dev/null | sed 's/.*checkpoint-//' | sort -rn); do
    p="$OUT/checkpoint-$d"
    if [ -f "$p/trainer_state.json" ] && ls "$p"/*.safetensors >/dev/null 2>&1; then best="$p"; break; fi
    echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')]   ★ 손상 체크포인트 격리: $p" >> "$LOG"
    mv "$p" "$OUT/broken-checkpoint-$d" 2>/dev/null
  done
  if [ -n "$best" ]; then
    python3 - "$CONF" "$best" <<'PY' 2>/dev/null
import sys, yaml
c = yaml.safe_load(open(sys.argv[1])); c["checkpoint_name"] = sys.argv[2]
open("/tmp/ft_rango_aug_v4_resume.yaml", "w").write(yaml.safe_dump(c, allow_unicode=True))
PY
    echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')]   재개 지점: $best" >> "$LOG"
    echo "/tmp/ft_rango_aug_v4_resume.yaml"
  else
    echo "$CONF"
  fi
}

say "===== rango-augmented v4 학습(인용+정규화+에러조건) (GPU ${NPROC}장 DDP) ====="
say "  conf=$CONF  out=$OUT"

# 코퍼스 스테이징 확인(tmpfs 는 재부팅 시 비워짐)
SRC_DS=data/coq-dataset
DST_DS=$(python3 -c "import yaml;print(yaml.safe_load(open('$CONF'))['tactic_data']['data_loc'])")
if [ "$DST_DS" != "$SRC_DS" ] && [ "$(ls "$DST_DS/data_points" 2>/dev/null | wc -l)" -lt "$(ls "$SRC_DS/data_points" | wc -l)" ]; then
  say "  코퍼스 스테이징: $SRC_DS → $DST_DS"
  mkdir -p "$DST_DS" && cp -r "$SRC_DS"/. "$DST_DS"/
fi

# 빈 output_dir 은 제거(make_output_dir 가 막지 않도록). 내용 있으면 손대지 않음.
[ -d "$OUT" ] && [ -z "$(ls -A "$OUT" 2>/dev/null)" ] && rmdir "$OUT"

for try in $(seq 1 $MAX_RETRY); do
  USE=$(mkconf_resume | tail -1)
  say "  시도 $try (conf=$(basename "$USE"))"
  HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
  \
  AUGMENT_V2=1 RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 DYNAMIC_PADDING=1 \
  HARD_SEQ_LEN=4096 TYPES_TOKENS=300 DEFS_TOKENS=300 \
  FUNC_DEFS_PATH=data/func_defs_v3.json CITE_TARGET=1 NORMALIZE_NAMES=1 NORMALIZE_RATE=0.5 \
  ERROR_COND=1 SYNTH_ERROR_RATE=0.8 TYPE_FACTS=1 DISTRACTORS=2 \
    torchrun --nproc_per_node="$NPROC" --master_port=$((29500 + RANDOM % 400)) src/tactic_gen/train_decoder.py "$USE" >> "$LOG" 2>&1
  rc=$?
  if [ $rc -eq 0 ]; then
    say "  학습 정상 종료(rc=0)"
    printf '{"AUGMENT_V2":"1","RERANK_PREMISES":"1","INJECT_TYPES":"1","INJECT_DEFS":"1","HARD_SEQ_LEN":"4096","TYPES_TOKENS":"300","DEFS_TOKENS":"300","FUNC_DEFS_PATH":"data/func_defs_v3.json","CITE_TARGET":"1","NORMALIZE_NAMES":"1","NORMALIZE_RATE":"0.5","ERROR_COND":"1","SYNTH_ERROR_RATE":"0.8","TYPE_FACTS":"1","DISTRACTORS":"2","note":"추론·평가 시 동일 env 필수"}\n' > "$OUT/AUGMENT.json"
    break
  fi
  say "  ★ 중단(rc=$rc) — 60s 후 최신 체크포인트에서 재개"
  sleep 60
done
say "===== v2 종료 — 체크포인트: $(ls -d $OUT/checkpoint-* 2>/dev/null | tr '\n' ' ') ====="
