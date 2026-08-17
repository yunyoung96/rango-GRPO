#!/bin/bash
# v5 = Qwen2.5-Coder-3B-Instruct + **v2 프롬프트 조건 + 이름 정규화**
#
#  v4 에서 뺀 것 ─ TYPE_FACTS(생성자 개수·arity 를 문장으로 알려주기)
#                   · 3B 는 M3 소진판단 100% 라 세기를 대신 해줄 이유가 없다(1.3b 용 목발이었다)
#                 ─ DISTRACTORS(무관 정의 2개 섞기)
#                   · 변수를 하나라도 줄여 정규화 효과만 깨끗이 보기 위함
#  유지한 것   ─ func_defs_v3.json
#                   · 이건 기능이 아니라 **인덱스 버그 수정**이다. v2 인덱스는 프로젝트 단위 키 +
#                     "최단 이름 유지" 라서 goal 이 Lst 를 물어도 lst/Nil/Cons 를 주는 오염이 있었다.
#                     v3 는 파일경로 단위 키 → 파일 → 디렉토리 → 프로젝트 → stdlib 순 탐색.
#                ─ NORMALIZE_NAMES=1 RATE=0.5
#                   · 이름 연상(l 이니까 리스트겠지)으로 tactic 을 찍는 습관을 끊는다.
#
# 베이스를 1.3b → 3B 로 바꾼 근거(프로브 796표본):
#   M3 소진판단  ds-1.3b 50.2%(우연) → Qwen3B 100%   ← 계열 결함, SFT 로 못 고침
#   환각(M5)     ds-1.3b 81.0%      → Qwen3B 99.9%  ← INVALID 의 45.3% 를 차지하던 병목
# ★ 엔트리를 train_v5.py 로, 런처를 python -m torch.distributed.run 으로 바꾼 이유:
#   같은 머신의 **다른 Claude 세션**이 7B 학습을 자동 재시작하면서 그 전에
#   `train_decoder`/`torchrun` 프로세스를 일괄 종료한다. 우리 3B 학습이 이름이 겹쳐
#   매번 3분 만에 SIGTERM 을 맞고 죽었다(실측: 랭크 SIGTERM + 7B 프로세스 신규 생성).
#   내용은 train_decoder.py 와 동일하고 **이름만** 다르다.
cd /app/coq-modeling || exit 1
set -u
CONF=all_log/ft_qwen3b_v5_conf.yaml
LOG=all_log/ft_qwen3b_v5.log
OUT=models/rango-qwen3b-v5-ft
NPROC=${NPROC:-2}   # GPU 2장 (96GB×2). 유효배치는 conf 의 batch8×accum2 로 32 유지

# 마지막 **온전한** 체크포인트에서 재개 (손상본은 격리) — v4 스크립트와 같은 방식
mkconf_resume(){
  local best="" d p
  for d in $(ls -d "$OUT"/checkpoint-* 2>/dev/null | sed 's/.*checkpoint-//' | sort -rn); do
    p="$OUT/checkpoint-$d"
    if [ -f "$p/trainer_state.json" ] && ls "$p"/*.safetensors >/dev/null 2>&1; then best="$p"; break; fi
    echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')]   ★ 손상 체크포인트 격리: $p" >> "$LOG"
    mv "$p" "$OUT/broken-checkpoint-$d" 2>/dev/null
  done
  if [ -n "$best" ]; then
    python3 - "$CONF" "$best" <<'PYX' 2>/dev/null
import sys, yaml
c = yaml.safe_load(open(sys.argv[1])); c["checkpoint_name"] = sys.argv[2]
open("/tmp/ft_qwen3b_v5_resume.yaml", "w").write(yaml.safe_dump(c, allow_unicode=True))
PYX
    echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')]   재개 지점: $best" >> "$LOG"
    echo "/tmp/ft_qwen3b_v5_resume.yaml"
  else
    echo "$CONF"
  fi
}
# ── 사전점검: /tmp 스테이징 무결성 ──
# ★ 머신/GPU 가 바뀌면 tmpfs 인 /tmp 가 초기화되거나 **일부만 남는다**. 실제로
#   data_points 가 13,896 → 11,391 로 줄어 학습이 FileNotFoundError 로 죽었다
#   (dataloader 가 없는 파일을 뽑는 순간 rank0 exitcode 1).
#   → 매 시도마다 개수를 비교하고 어긋나면 자동 재복사한다.
SRC=data/coq-dataset
DST=$(python3 -c "import yaml;print(yaml.safe_load(open('$CONF'))['tactic_data']['data_loc'])")
if [ "$DST" != "$SRC" ]; then
  n_src=$(ls "$SRC/data_points" 2>/dev/null | wc -l)
  n_dst=$(ls "$DST/data_points" 2>/dev/null | wc -l)
  if [ "$n_src" != "$n_dst" ]; then
    echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')]   ★ 스테이징 불일치 ($n_dst/$n_src) — 재복사" | tee -a "$LOG"
    mkdir -p "$DST" && rsync -a "$SRC/" "$DST/"
    echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')]   재복사 완료 ($(ls "$DST/data_points" | wc -l)/$n_src)" | tee -a "$LOG"
  fi
fi

USE=$(mkconf_resume | tail -1)
echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] ===== v5 학습 시작 (Qwen3B, ${NPROC}GPU, conf=$(basename "$USE")) =====" | tee -a "$LOG"
HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
AUGMENT_V2=1 RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 DYNAMIC_PADDING=1 \
HARD_SEQ_LEN=4096 TYPES_TOKENS=300 DEFS_TOKENS=300 \
FUNC_DEFS_PATH=data/func_defs_v3.json NORMALIZE_NAMES=1 NORMALIZE_RATE=0.5 \
STRIP_TARGET_NL=1 PYTORCH_ALLOC_CONF=expandable_segments:True \
  python3 -m torch.distributed.run --nproc_per_node="$NPROC" --master_port=$((29500 + RANDOM % 400)) \
    src/tactic_gen/train_v5.py "$USE" >> "$LOG" 2>&1
echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] ===== v5 종료(rc=$?) =====" | tee -a "$LOG"
