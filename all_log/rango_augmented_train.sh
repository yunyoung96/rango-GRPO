#!/bin/bash
# rango-augmented 재학습 (docs/grpo/rango_augmented/{PLAN,REVIEW,EXPERIMENT_SETUP}.md 명세 1차 구성).
#   증강 = ① 재랭킹 premise(RERANK_PREMISES=1) + ② [TYPES] selective 생성자(INJECT_TYPES=1).
#   [DECIDERS]/[SIGNATURES] 는 2차(REVIEW R4: 노이즈) — 여기선 안 씀.
#
# ★ 통제(REVIEW R5): **같은 training set·같은 hyperparam·같은 init**, 증강만 다른 두 arm 을 동시 학습.
#     aug  : RERANK_PREMISES=1 INJECT_TYPES=1   → models/rango-augmented-sft      (GPU0)
#     ctrl : 증강 없음(base 프롬프트)            → models/rango-augmented-ctrl-sft (GPU1)
#   training set = data/grpo_rollouts/goldsft_bs2.jsonl (= 기존 rango-grpo-bs2-sft 를 만든 그 gold SFT 셋)
#   hyperparam   = run_bigscale2.sh ▶3 과 동일: --sft --kl_beta 0 --lr 1e-6 --epochs 2 --micro_bsz 2 --max_len 3072
#   init         = rango baseline checkpoint-54500
#
# ★ 중단복구: save_every 1000 step 체크포인트 + keep_every 5000 마일스톤 보존(그 사이 1000단위는 5000 도달 시 삭제).
#   GPU 가 끊기면 아래 재시도 루프가 --resume 으로 이어서 학습(adapter+optimizer+step 위치 복원).
cd /app/coq-modeling || exit 1
set -u
TAG=rango-augmented
LOG=all_log/${TAG}.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
DATA=data/grpo_rollouts/goldsft_bs2.jsonl
SAVE_EVERY=1000
KEEP_EVERY=5000
LOG_EVERY=25
WORKERS=12                 # arm 당 렌더 워커(32코어 / 2 arm)
MAX_RETRY=20               # GPU 끊김 대비 재시도 횟수

run_arm(){                 # $1=arm이름 $2=gpu $3=rerank $4=inject
  local arm=$1 gpu=$2 rr=$3 it=$4
  local out=models/${TAG}-${arm}
  local ck=$out/checkpoints
  local alog=all_log/${TAG}_${arm}.log
  for try in $(seq 1 $MAX_RETRY); do
    [ -f "$ck/DONE" ] && { say "  [$arm] 이미 완료(DONE)"; return 0; }
    say "  [$arm] 학습 시도 $try (GPU$gpu, RERANK=$rr INJECT=$it)"
    HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
    CUDA_VISIBLE_DEVICES=$gpu RERANK_PREMISES=$rr INJECT_TYPES=$it \
      python3 -m tactic_gen.grpo_train \
        --rollouts "$DATA" --model_name "$BASE" --init_adapter "$INIT" \
        --collator_conf "$CONF" --max_len 3072 --save_dir "$out/adapter" \
        --sft --kl_beta 0.0 --epochs 2 --lr 1e-6 --micro_bsz 2 \
        --save_every $SAVE_EVERY --keep_every $KEEP_EVERY --log_every $LOG_EVERY \
        --ckpt_dir "$ck" --loss_log "$ck/loss.jsonl" \
        --render_workers $WORKERS --resume >> "$alog" 2>&1
    if [ -f "$ck/DONE" ]; then
      # ★ R1(train/infer 포맷 일치): 이 어댑터를 평가·배포할 때 반드시 같은 env 를 켜야 한다.
      printf '{"RERANK_PREMISES": "%s", "INJECT_TYPES": "%s", "IND_INDEX_PATH": "data/ind_constructors_clean.json", "TYPES_TOKENS": "200", "note": "추론 시 동일 env 필수(안 그러면 OOD)"}\n' \
        "$rr" "$it" > "$out/AUGMENT.json"
      say "  [$arm] 완료 → $out/adapter (평가 env: RERANK_PREMISES=$rr INJECT_TYPES=$it)"
      return 0
    fi
    say "  [$arm] 중단됨(시도 $try) — 30s 후 --resume 재시도"
    sleep 30
  done
  say "  [$arm] ★ $MAX_RETRY 회 실패"; return 1
}

say "===== ${TAG} 재학습 시작 (aug=GPU0 / ctrl=GPU1 동시) ====="
say "  데이터: $DATA ($(wc -l < $DATA) 그룹) | init: $INIT"
: > all_log/${TAG}_aug.log; : > all_log/${TAG}_ctrl.log
run_arm aug  0 1 1 &
PID_A=$!
run_arm ctrl 1 0 0 &
PID_C=$!
wait $PID_A; RA=$?
wait $PID_C; RC=$?
say "===== 학습 종료 (aug=$RA ctrl=$RC) ====="
python3 scripts/report_loss.py models/${TAG}-aug/checkpoints/loss.jsonl models/${TAG}-ctrl/checkpoints/loss.jsonl 2>&1 | tee -a "$LOG"
