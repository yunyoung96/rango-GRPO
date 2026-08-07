#!/bin/bash
# rango 1.3B fine-tuning 완전 재학습 (augment 세팅: 재랭킹 랭커 + [TYPES] 프롬프트), GPU 2개 DDP.
#   · conf: all_log/ft_rango_augmented_conf.yaml (rango parity — LoRA r64, LR 1e-3, 60000 step, eff_batch 32)
#   · 증강: RERANK_PREMISES=1 INJECT_TYPES=1 (ProofPremiseCollator 가 학습·추론 동일 규칙으로 적용)
#   · 중단복구: save_steps 1000 저장 → 5000 배수만 영구 보존(CheckpointRotationCallback).
#              죽으면 아래 루프가 최신 checkpoint-N 에서 자동 재개(--resume 상당: conf 의 checkpoint_name).
# 사용: bash all_log/ft_rango_augmented.sh            (전체 학습)
#       SMOKE=1 bash all_log/ft_rango_augmented.sh    (50 step 스모크 — 배선 확인용)
cd /app/coq-modeling || exit 1
set -u
CONF=${CONF:-all_log/ft_rango_augmented_conf.yaml}
OUT=$(python3 -c "import yaml,sys;print(yaml.safe_load(open('$CONF'))['output_dir'])")
LOG=all_log/ft_rango_augmented.log
MAX_RETRY=${MAX_RETRY:-50}
NPROC=${NPROC:-2}
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

# 최신 **정상** 체크포인트에서 재개할 conf 를 만든다(HF Trainer 는 checkpoint 경로를 train() 인자로 받음).
#   ★ 저장 도중 죽으면 checkpoint-N 이 불완전(trainer_state.json 없음)하게 남는다. 그걸 그대로 잡으면
#     재개가 매번 FileNotFoundError 로 실패 → 재시도 루프가 영원히 헛돈다(실측). 그래서
#     최신부터 내려가며 **완전한 것**을 찾고, 손상본은 broken-checkpoint-N 으로 격리한다.
#   stdout 은 conf 경로 한 줄만(호출부가 $() 로 받음). 진단은 로그파일로.
mkconf_resume(){
  local best="" d p
  for d in $(ls -d "$OUT"/checkpoint-* 2>/dev/null | sed 's/.*checkpoint-//' | sort -rn); do
    p="$OUT/checkpoint-$d"
    if [ -f "$p/trainer_state.json" ] && ls "$p"/*.safetensors >/dev/null 2>&1; then
      best="$p"; break
    fi
    echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')]   ★ 손상 체크포인트 격리(쓰다 만 것): $p" >> "$LOG"
    mv "$p" "$OUT/broken-checkpoint-$d" 2>/dev/null
  done
  if [ -n "$best" ]; then
    python3 - "$CONF" "$best" <<'PY' 2>/dev/null
import sys, yaml
conf_path, ckpt = sys.argv[1], sys.argv[2]
c = yaml.safe_load(open(conf_path))
c["checkpoint_name"] = ckpt
open("/tmp/ft_rango_aug_resume.yaml", "w").write(yaml.safe_dump(c, allow_unicode=True))
PY
    echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')]   재개 지점: $best" >> "$LOG"
    echo "/tmp/ft_rango_aug_resume.yaml"
  else
    echo "$CONF"
  fi
}

say "===== rango-1.3B augmented 완전 재학습 (GPU ${NPROC}개 DDP) ====="
say "  conf=$CONF  out=$OUT"

# ── 코퍼스 스테이징: NFS 직접 읽기는 예제당 수 초(데이터 병목) → tmpfs(/tmp, RAM)로 올린다. ──
#   재부팅하면 tmpfs 가 비므로 매 실행마다 확인 후 없으면 다시 스테이징(멱등).
SRC_DS=${SRC_DS:-data/coq-dataset}
DST_DS=$(python3 -c "import yaml;c=yaml.safe_load(open('$CONF'));print(c.get('tactic_data',{}).get('data_loc',''))")
if [ -n "$DST_DS" ] && [ "$DST_DS" != "$SRC_DS" ]; then
  n_src=$(ls "$SRC_DS/data_points" 2>/dev/null | wc -l)
  n_dst=$(ls "$DST_DS/data_points" 2>/dev/null | wc -l)
  if [ "$n_dst" -lt "$n_src" ] || [ ! -f "$DST_DS/sentences.db" ]; then
    say "  코퍼스 스테이징: $SRC_DS → $DST_DS (data_points $n_dst/$n_src)"
    mkdir -p "$DST_DS" && cp -r "$SRC_DS"/. "$DST_DS"/ && say "  스테이징 완료($(du -sh "$DST_DS" | cut -f1))"
  else
    say "  코퍼스 스테이징 확인: $DST_DS (data_points $n_dst)"
  fi
fi
# ★ make_output_dir 은 "30분 넘은 output_dir 이 이미 있으면" exit(1) 한다(덮어쓰기 방지).
#   비어 있는 디렉토리(이전 시도가 만들다 만 것)면 지워야 재시작이 가능하다. 내용이 있으면 절대 건드리지 않음.
if [ -d "$OUT" ] && [ -z "$(ls -A "$OUT" 2>/dev/null)" ]; then
  rmdir "$OUT" && say "  빈 output_dir 제거(재시작 가능하게): $OUT"
fi

for try in $(seq 1 $MAX_RETRY); do
  USE=$(mkconf_resume | tail -1)
  say "  시도 $try (conf=$(basename "$USE"))"
  HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
  RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 \
  IND_INDEX_PATH=data/ind_constructors_clean.json TYPES_TOKENS=200 \
  FUNC_DEFS_PATH=data/func_defs.json DEFS_TOKENS=200 DEFS_MAX=5 DEFS_MAX_BODY=80 DEFS_MAX_SIG=40 \
    torchrun --nproc_per_node="$NPROC" --master_port=$((29500 + RANDOM % 500)) \
      src/tactic_gen/train_decoder.py "$USE" >> "$LOG" 2>&1
  rc=$?
  if [ $rc -eq 0 ]; then
    say "  학습 정상 종료(rc=0)"
    printf '{"RERANK_PREMISES":"1","INJECT_TYPES":"1","INJECT_DEFS":"1","IND_INDEX_PATH":"data/ind_constructors_clean.json","TYPES_TOKENS":"200","FUNC_DEFS_PATH":"data/func_defs.json","DEFS_TOKENS":"200","DEFS_MAX":"5","DEFS_MAX_BODY":"80","DEFS_MAX_SIG":"40","note":"추론·평가 시 동일 env 필수(안 그러면 train/infer 불일치=OOD)"}\n' > "$OUT/AUGMENT.json"
    break
  fi
  say "  ★ 중단(rc=$rc) — 60s 후 최신 체크포인트에서 재개"
  sleep 60
done
say "===== 종료 — 체크포인트: $(ls -d $OUT/checkpoint-* 2>/dev/null | tr '\n' ' ') ====="
