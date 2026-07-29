#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# 안전-EI (overfitting-hardened Expert Iteration). π₀=SFT→GRPO에서 새로 시작.
#   각 라운드: rollout(iid) → 성공추출 → [누적+gold혼합] RFT → GRPO → val 조기중단.
#   안전장치(EI_OVERFIT_MITIGATIONS.md 근거):
#     · KL을 고정 π₀에 앵커(--ref_adapter) — 누적 drift 차단 (Gao 2210.10760)
#     · gold SFT(real) + 라운드 성공(synthetic) 누적 혼합 (Gerstgrasser 2404.01413)
#     · lr↓(5e-7) / epochs 1 (보수적 업데이트, ReST-EM)
#     · 라운드마다 val(60, disjoint) 조기중단 — best-val 채택 (ReST-EM 2312.06585)
#   GPU: 학습(rollout/gtrain)=GPU0 비면 g2w4, GPU0 돌아오면 그때부터 GPU1만. eval=항상 w2/GPU1(공정).
#   train 끝나면 → 안전-EI 최종 rand200 → 그 다음 일시정지했던 R3 rand200 재개.
# ══════════════════════════════════════════════════════════════════════════════
set -u
LOG=all_log/ei_safe.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
TRAIN=data/compcert_bs2_train_idx.txt
VAL=data/compcert_bs2_val_idx.txt
RAND=data/compcert_bs2_rand200_idx.txt
GOLD=data/grpo_rollouts/goldsft_bs2.jsonl     # real 앵커(gold SFT)
PI0=models/rango-grpo/adapter                  # π₀ = SFT→GRPO (KL 앵커 + 시작 정책)
export SUBGOAL_GS=8 SUBGOAL_MAXSTEPS=20
NROUNDS=${NROUNDS:-4}; PATIENCE=${PATIENCE:-1}; ROLLW=8; EVALW=2   # ROLLW=4=GPU당 워커 → g2w4(둘) / g1w4(GPU1만)
LR=5e-7; EPOCHS=1

say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }

# ── GPU 선택: GPU0가 비었으면(util<20% & mem<3GB) 롤아웃 g2w4, gtrain GPU0. 아니면 GPU1만. ──
gpu0_free(){
  [ -f .gpu1_only ] && return 1   # ★ GPU0 off-limits(사용자 지정): 항상 GPU1만
  local u m
  u=$(nvidia-smi -i 0 --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null|tr -d ' '||echo 100)
  m=$(nvidia-smi -i 0 --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null|tr -d ' '||echo 99999)
  [ "${u:-100}" -lt 20 ] && [ "${m:-99999}" -lt 3000 ]
}
roll_gpus(){ gpu0_free && echo "0,1" || echo "1"; }
train_gpu(){ gpu0_free && echo "0" || echo "1"; }

# gtrain: KL을 항상 π₀에 앵커, lr↓/epochs1
gtrain(){ local ro="$1" init="$2" sd="$3"; shift 3; local g; g=$(train_gpu)
  say "    gtrain on GPU$g (ref=π₀, lr=$LR, epochs=$EPOCHS) → $sd"
  CUDA_VISIBLE_DEVICES=$g python3 -m tactic_gen.grpo_train --rollouts "$ro" --model_name "$BASE" \
    --init_adapter "$init" --ref_adapter "$PI0" --collator_conf "$CONF" --max_len 3072 \
    --save_dir "$sd/adapter" --kl_beta 0.04 --epochs $EPOCHS --lr $LR --micro_bsz 2 "$@" >> "$LOG" 2>&1
  cpconf "$sd"; }

covof(){ python3 -c "import json;r=[json.loads(l) for l in open('$1') if l.strip()];print(sum(1 for g in r if any(a['reward']>=1 for a in g['attempts'])),len(r))" 2>/dev/null||echo '? ?'; }
srof(){ python3 -c "import json;r=json.load(open('$1'))['results'];print(sum(1 for x in r if x.get('success')),len(r))" 2>/dev/null||echo '? ?'; }

[ -f "$PI0/adapter_model.safetensors" ] || { say "✗ π₀ 없음"; exit 1; }
say "════════ 안전-EI 시작 (π₀=SFT→GRPO, NROUNDS≤$NROUNDS, patience=$PATIENCE) ════════"
say "  안전장치: KL→π₀ 앵커 · gold+누적 혼합 · lr$LR/ep$EPOCHS · val$VAL 조기중단"

INIT="$PI0"; BEST_VAL=-1; BEST_MODEL="$PI0"; BAD=0
for k in $(seq 1 "$NROUNDS"); do
  say "──── Round $k (init=$INIT) ────"
  RO=data/grpo_rollouts/ei-safe-r${k}.jsonl
  SUCC=data/grpo_rollouts/ei-safe-r${k}-succ.jsonl
  RFT=data/grpo_rollouts/ei-safe-r${k}-rft.jsonl
  SFTM=models/rango-grpo-eisafe-r${k}sft
  FINM=models/rango-grpo-eisafe-r${k}

  # 1) rollout (iid, GPU auto)
  RG=$(roll_gpus); say "  rollout GPUs=$RG workers=$ROLLW"
  export SUBGOAL_CURRICULUM=data/curriculum/empty.json SUBGOAL_OUT="$RO" SUBGOAL_POLICY="$INIT" \
         SUBGOAL_SKIP_S0=0 SUBGOAL_REWARD=0 SUBGOAL_HYBRID=0
  [ -s "$RO" ] || python3 scripts/run_all.py --alias grpo-rollout-subgoal --idx-file "$TRAIN" \
      --timeout 600 --gpus "$RG" --workers $ROLLW >> "$LOG" 2>&1
  say "  R$k rollout coverage = $(covof "$RO")"

  # 2) 성공추출 → 3) 누적+gold 혼합 (real+synthetic)
  [ -s "$SUCC" ] || python3 scripts/extract_successes.py "$RO" "$SUCC" >> "$LOG" 2>&1
  cat "$GOLD" $(for j in $(seq 1 $k); do echo data/grpo_rollouts/ei-safe-r${j}-succ.jsonl; done) > "$RFT" 2>/dev/null
  say "  R$k RFT 데이터(gold+누적 성공) = $(wc -l < "$RFT")줄"

  # 4) RFT(--sft) → 5) GRPO  (둘 다 KL→π₀)
  [ -f "$SFTM/adapter/adapter_model.safetensors" ] || gtrain "$RFT" "$INIT" "$SFTM" --sft
  [ -f "$FINM/adapter/adapter_model.safetensors" ] || gtrain "$RO" "$SFTM/adapter" "$FINM"
  INIT="$FINM/adapter"

  # 6) val 평가 (w2/GPU1, 조기중단 판단)
  VD=all_results/val_eisafe_r${k}_w2
  [ -s "$VD/summary.json" ] || python3 scripts/run_all.py --alias rango-grpo-eisafe-r${k} --idx-file "$VAL" \
      --timeout 600 --gpus 1 --workers $EVALW --out "$VD" --description "eisafe R$k val" >> "$LOG" 2>&1
  read vs vn < <(srof "$VD/summary.json")
  say "  ★ R$k val = $vs/$vn"
  if [ "${vs:-0}" -gt "$BEST_VAL" ]; then
    BEST_VAL=$vs; BEST_MODEL="$FINM/adapter"; BEST_ALIAS="rango-grpo-eisafe-r${k}"; BAD=0
    say "    ↑ best-val 갱신 (val=$vs, model=eisafe-r$k)"
  else
    BAD=$((BAD+1)); say "    ↓ 개선 없음 (BAD=$BAD/$PATIENCE, best=$BEST_VAL)"
    [ "$BAD" -ge "$PATIENCE" ] && { say "  ■ 조기중단: val plateau. best=eisafe(best_val=$BEST_VAL)"; break; }
  fi
done
say "════ 학습 종료. best-val 모델=${BEST_ALIAS:-π₀} (val=$BEST_VAL) ════"

# ── 최종 rand200 (w2/GPU1) : best-val 모델 ──
FRD=all_results/rand200_eisafe_best_w2
say "════ 안전-EI 최종 평가: rand200 w2 600s (GPU1) — ${BEST_ALIAS:-π₀} ════"
[ -s "$FRD/summary.json" ] || python3 scripts/run_all.py --alias "${BEST_ALIAS:-rango-grpo}" --idx-file "$RAND" \
    --timeout 600 --gpus 1 --workers $EVALW --out "$FRD" --description "eisafe best rand200 w2" >> "$LOG" 2>&1
say "════ ★ 안전-EI rand200 w2 = $(srof "$FRD/summary.json")  (vs SFT→GRPO 75/200=37.5%) ════"

# ── train 끝나면: 일시정지했던 R3 rand200 재개(진단) ──
R3D=all_results/rand200_ei_r3_w2
say "════ (요청) R3 rand200 재개 — 기존 부분결과 이어서 ════"
python3 scripts/run_all.py --alias rango-grpo-ei-r3 --idx-file "$RAND" \
    --timeout 600 --gpus 1 --workers $EVALW --out "$R3D" --description "EI R3 rand200 w2 (resume)" >> "$LOG" 2>&1
say "════ ★ R3 rand200 w2 = $(srof "$R3D/summary.json") ════"
say "════ [안전-EI 완료] ════"
