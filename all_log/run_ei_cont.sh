#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# EI 연속 (라운드 → held-out eval → 라운드).  사용자 지정: R3 이후 라운드마다 rand200 측정.
#   R(START)부터: rollout(g1w8) → 성공 RFT(--sft) → GRPO → rand200 w2 600s(GPU1) eval.
#   기본 R4 하나만 하고 멈춤(R3·R4 held-out 곡선 보고 R5 결정). MAXR=5로 재실행하면 R5 이어감.
#   전부 GPU1. R(START-1)의 모델+eval이 끝날 때까지 대기(GPU1 충돌 방지).
# ══════════════════════════════════════════════════════════════════════════════
set -u
LOG=all_log/ei.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
TRAIN=data/compcert_bs2_train_idx.txt
RAND=data/compcert_bs2_rand200_idx.txt
GPUS="1"; ROLLW=8; EVALW=2
export SUBGOAL_GS=8 SUBGOAL_MAXSTEPS=20
START=${START:-4}; MAXR=${MAXR:-4}
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }
gtrain(){ local ro="$1" init="$2" sd="$3"; shift 3
  CUDA_VISIBLE_DEVICES=1 python3 -m tactic_gen.grpo_train --rollouts "$ro" --model_name "$BASE" --init_adapter "$init" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$sd/adapter" \
    --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 "$@" >> "$LOG" 2>&1; cpconf "$sd"; }

# ── R(START-1) 완료 대기: 모델 + rand200 eval summary 존재 + GPU1에 우리 학습/eval 프로세스 없음 ──
PREVM=models/rango-grpo-ei-r$((START-1))/adapter
PREVEVAL=all_results/rand200_ei_r$((START-1))_w2/summary.json
say "════ EI-cont 대기: R$((START-1)) 모델+eval 완료까지 (GPU1 충돌 방지) ════"
while true; do
  running=$(ps -eo args | awk '/[g]rpo_train --rollouts/{n++} /[r]un_all\.py/{n++} END{print n+0}')
  [ -f "$PREVM/adapter_model.safetensors" ] && [ -s "$PREVEVAL" ] && [ "$running" -eq 0 ] && break
  sleep 120
done
say "════ EI-cont 시작 (R${START}..R${MAXR}, 라운드마다 rand200 w2 eval, GPU1) ════"

INIT="$PREVM"
for k in $(seq "$START" "$MAXR"); do
  say "──── Round $k (init=$INIT) ────"
  RO=data/grpo_rollouts/ei-r${k}.jsonl; SUCC=data/grpo_rollouts/ei-r${k}-succ.jsonl
  SFTM=models/rango-grpo-ei-r${k}sft; FINM=models/rango-grpo-ei-r${k}

  export SUBGOAL_CURRICULUM=data/curriculum/empty.json SUBGOAL_OUT="$RO" SUBGOAL_POLICY="$INIT" \
         SUBGOAL_SKIP_S0=0 SUBGOAL_REWARD=0 SUBGOAL_HYBRID=0
  [ -s "$RO" ] || python3 scripts/run_all.py --alias grpo-rollout-subgoal --idx-file "$TRAIN" \
      --timeout 600 --gpus "$GPUS" --workers $ROLLW >> "$LOG" 2>&1
  COV=$(python3 -c "import json;r=[json.loads(l) for l in open('$RO') if l.strip()];print(sum(1 for g in r if any(a['reward']>=1 for a in g['attempts'])),len(r))" 2>/dev/null||echo '? ?')
  say "  R$k rollout coverage(성공정리/총) = $COV"

  [ -s "$SUCC" ] || python3 scripts/extract_successes.py "$RO" "$SUCC" >> "$LOG" 2>&1
  [ -f "$SFTM/adapter/adapter_model.safetensors" ] || gtrain "$SUCC" "$INIT" "$SFTM" --sft
  [ -f "$FINM/adapter/adapter_model.safetensors" ] || gtrain "$RO" "$SFTM/adapter" "$FINM"
  INIT="$FINM/adapter"

  # ── 라운드마다 held-out eval (rand200 w2 GPU1) ──
  RD=all_results/rand200_ei_r${k}_w2
  say "  R$k held-out eval 시작: rand200 w2 600s (GPU1)"
  [ -s "$RD/summary.json" ] || python3 scripts/run_all.py --alias rango-grpo-ei-r${k} --idx-file "$RAND" \
      --timeout 600 --gpus 1 --workers $EVALW --out "$RD" --description "EI R$k rand200 w2" >> "$LOG" 2>&1
  SR=$(python3 -c "import json;r=json.load(open('$RD/summary.json'))['results'];su=sorted(x['elapsed_sec'] for x in r if x['success']);p=su[int(0.9*len(su))] if su else 0;print(f\"{sum(1 for x in r if x['success'])}/{len(r)} (p90 {p:.0f}s)\")" 2>/dev/null||echo '?')
  say "  ★ R$k held-out rand200 w2 = $SR   (π_0 SFT→GRPO=75/200 37.5%, R3=측정중)"
done
say "════ [EI-cont R${START}..R${MAXR} 완료] ════"
