#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# Expert Iteration (full-theorem) — subgoal 폐기 후 정공법.
#   π_0 = SFT→GRPO. 각 라운드: rollout(성공수집,g2w4) → 성공으로 RFT(--sft) → GRPO → 다음 π.
#   라운드는 학습만(coverage로 수렴 판단), 최종만 rand200 w2 600s(GPU1) 평가. (사용자 지정)
# ══════════════════════════════════════════════════════════════════════════════
set -u
LOG=all_log/ei.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
TRAIN=data/compcert_bs2_train_idx.txt
RAND=data/compcert_bs2_rand200_idx.txt
GPUS="1"; ROLLW=8; EVALW=2   # 전부 GPU1: 학습 rollout=g1w8, 최종 test=g1w2 (OOM시 ROLLW 낮춤)
export SUBGOAL_GS=8 SUBGOAL_MAXSTEPS=20
NROUNDS=${NROUNDS:-3}
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }
gtrain(){ local ro="$1" init="$2" sd="$3"; shift 3
  CUDA_VISIBLE_DEVICES=1 python3 -m tactic_gen.grpo_train --rollouts "$ro" --model_name "$BASE" --init_adapter "$init" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$sd/adapter" \
    --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 "$@" >> "$LOG" 2>&1; cpconf "$sd"; }

INIT=models/rango-grpo/adapter    # π_0 = SFT→GRPO
[ -f "$INIT/adapter_model.safetensors" ] || { say "✗ SFT→GRPO 모델 없음"; exit 1; }
say "════════ Expert Iteration (full-theorem, π_0=SFT→GRPO, $NROUNDS 라운드) ════════"

for k in $(seq 1 "$NROUNDS"); do
  say "──── Round $k (init=$INIT) ────"
  RO=data/grpo_rollouts/ei-r${k}.jsonl
  SUCC=data/grpo_rollouts/ei-r${k}-succ.jsonl
  SFTM=models/rango-grpo-ei-r${k}sft
  FINM=models/rango-grpo-ei-r${k}

  # 1) rollout (완전체, g2w4)
  export SUBGOAL_CURRICULUM=data/curriculum/empty.json SUBGOAL_OUT="$RO" SUBGOAL_POLICY="$INIT" \
         SUBGOAL_SKIP_S0=0 SUBGOAL_REWARD=0 SUBGOAL_HYBRID=0
  [ -s "$RO" ] || python3 scripts/run_all.py --alias grpo-rollout-subgoal --idx-file "$TRAIN" \
      --timeout 600 --gpus "$GPUS" --workers $ROLLW >> "$LOG" 2>&1
  COV=$(python3 -c "import json;r=[json.loads(l) for l in open('$RO') if l.strip()];print(sum(1 for g in r if any(a['reward']>=1 for a in g['attempts'])),len(r))" 2>/dev/null||echo '? ?')
  say "  rollout coverage(성공정리/총) = $COV"

  # 2) 성공 추출 → RFT
  [ -s "$SUCC" ] || python3 scripts/extract_successes.py "$RO" "$SUCC" >> "$LOG" 2>&1
  # 3) RFT (--sft on 성공)
  [ -f "$SFTM/adapter/adapter_model.safetensors" ] || gtrain "$SUCC" "$INIT" "$SFTM" --sft
  # 4) GRPO (전체 rollout)
  [ -f "$FINM/adapter/adapter_model.safetensors" ] || gtrain "$RO" "$SFTM/adapter" "$FINM"
  INIT="$FINM/adapter"
  say "  Round $k 완료 → rango-grpo-ei-r${k}"
done

# 최종 평가 (rand200 w2 600s, GPU1)
FINAL=rango-grpo-ei-r${NROUNDS}
RD=all_results/rand200_ei_r${NROUNDS}_w2
say "════ 최종 평가: rand200 w2 600s (GPU1) — $FINAL ════"
[ -s "$RD/summary.json" ] || python3 scripts/run_all.py --alias "$FINAL" --idx-file "$RAND" \
    --timeout 600 --gpus 1 --workers $EVALW --out "$RD" --description "EI final rand200 w2" >> "$LOG" 2>&1
SR=$(python3 -c "import json;r=json.load(open('$RD/summary.json'))['results'];su=sorted(x['elapsed_sec'] for x in r if x['success']);p=su[int(0.9*len(su))] if su else 0;print(f\"{sum(1 for x in r if x['success'])}/{len(r)} (p90 {p:.0f}s)\")" 2>/dev/null||echo '?')
say "════ EI 최종 rand200 w2 = $SR   (vs SFT→GRPO 75/200=37.5% p90 399s) ════"
say "════ [EI 완료] ════"
