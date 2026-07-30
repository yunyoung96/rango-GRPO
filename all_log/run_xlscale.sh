#!/bin/bash
# XL-scale (bigscale보다 큼) baseline vs SFT→GRPO 비교.
#   split: 3000 = test 2000(clean 1191 held-out + 809) / train 1000 (disjoint).
#   P1 롤아웃(xl_train 1000, on-policy SFT, 2-GPU max workers)
#   P2 GRPO 학습(init=SFT) → models/rango-grpo-xlscale
#   P3 평가(xl_test 2000, w6): baseline=GPU0 / SFT→GRPO=GPU1 (각 모델이 GPU 하나 선점, 병렬)
set -u
cd /app/coq-modeling
export PYTHONPATH=src
LOG=all_log/xlscale.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF="$(dirname "$INIT")/training_conf.yaml"
TRAIN=data/compcert_xl_train_idx.txt
TEST=data/compcert_xl_test_idx.txt
ROLL=data/grpo_rollouts/xlscale.jsonl
ADP=models/rango-grpo-xlscale/adapter
CAPS="OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2"
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }
ndone(){ python3 -c "import json;print(len(json.load(open('$1/summary.json'))['results']))" 2>/dev/null||echo 0; }

# ── P1: 롤아웃 수집 (xl_train 1000, on-policy SFT, 2-GPU max workers) ──
say "▶ P1 롤아웃 수집 (xl_train 1000, gpus 0,1 w8, on-policy SFT)"
if [ ! -s "$ROLL" ]; then
  env $CAPS taskset -c 0-127 python3 scripts/run_all.py --alias grpo-rollout-xlscale \
    --idx-file "$TRAIN" --timeout 600 --gpus 0,1 --workers 8 \
    --out all_results/xlscale_rollout --description "xlscale rollout 1000 g2w8" >> "$LOG" 2>&1
fi
NG=$(wc -l < "$ROLL" 2>/dev/null || echo 0)
say "  롤아웃 완료: $NG 그룹"
[ "$NG" -lt 100 ] && { say "  ★ 롤아웃 부족($NG) — 중단"; exit 1; }

# ── P2: GRPO 학습 (init=SFT) ──
say "▶ P2 GRPO 학습 → $ADP"
if [ ! -f "$ADP/adapter_model.safetensors" ]; then
  python3 -m tactic_gen.grpo_train --rollouts "$ROLL" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$ADP" \
    --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml \
     models/rango-grpo-xlscale/ 2>/dev/null
fi
[ ! -f "$ADP/adapter_model.safetensors" ] && { say "  ★ GRPO 학습 실패 — 중단"; exit 1; }
say "  학습 완료 (adapter 생성됨)"

# ── P3: 평가 (xl_test 2000, w6): baseline=GPU0 / SFT→GRPO=GPU1, 병렬 ──
say "▶ P3 평가 (xl_test 2000, w6). baseline=GPU0 | SFT→GRPO=GPU1 (병렬)"
if [ "$(ndone all_results/xltest_baseline_w6)" -lt 2000 ]; then
  env $CAPS taskset -c 0-127 python3 scripts/run_all.py --alias rango \
    --idx-file "$TEST" --timeout 600 --gpus 0 --workers 6 \
    --out all_results/xltest_baseline_w6 --description "xl baseline(SFT) 2000 w6 GPU0" >> "$LOG" 2>&1 &
fi
if [ "$(ndone all_results/xltest_sftgrpo_w6)" -lt 2000 ]; then
  env $CAPS taskset -c 0-127 python3 scripts/run_all.py --alias rango-grpo-xlscale \
    --idx-file "$TEST" --timeout 600 --gpus 1 --workers 6 \
    --out all_results/xltest_sftgrpo_w6 --description "xl SFT->GRPO 2000 w6 GPU1" >> "$LOG" 2>&1 &
fi
wait
b=$(ndone all_results/xltest_baseline_w6); g=$(ndone all_results/xltest_sftgrpo_w6)
say "■ xlscale 완료 — baseline $b/2000, SFT→GRPO $g/2000"
