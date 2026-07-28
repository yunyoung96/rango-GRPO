#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# HARVEST 라운드 (A/RFT) — cascade-s0 위에 self-harvested subgoal RFT → s0 재실행 → 평가.
#   cascade가 held-out에서 baseline로 회귀(33.5%) → 실패 s0 롤아웃의 닫힌 subgoal을 강화해 재시도.
#   흐름: harvest(닫힌 subgoal) → RFT(--sft, reward=1 MLE, init=cascade-s0) → s0 재롤아웃(정책=harvest)
#         → s0 GRPO → rand200@600s g2w4 평가.  (§3-B self-harvest / HARVEST_ROUND.md 참고.)
# ══════════════════════════════════════════════════════════════════════════════
set -u
LOG=all_log/harvest.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
TRAIN=data/compcert_bs2_train_idx.txt
RAND=data/compcert_bs2_rand200_idx.txt
GPUS="0,1"; ROLLW=4; EVALW=4
export SUBGOAL_GS=8 SUBGOAL_MAXSTEPS=20
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }
gtrain(){ python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$2" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$3/adapter" \
    --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1; cpconf "$3"; }

S0M=models/rango-grpo-cascade-s0/adapter
S0ROLL=data/grpo_rollouts/rango-grpo-cascade-s0.jsonl
say "════════ HARVEST 라운드 (cascade-s0 → harvest RFT → s0 재실행) ════════"
[ -f "$S0M/adapter_model.safetensors" ] || { say "✗ cascade-s0 모델 없음 — 중단"; exit 1; }
[ -s "$S0ROLL" ] || { say "✗ s0 롤아웃 없음 — 중단"; exit 1; }

# ── 1) harvest: s0 실패(dead) 롤아웃에서 닫힌 subgoal 추출 (reward=1) ──
HARV=data/grpo_rollouts/rango-grpo-cascade-harvest.jsonl
[ -s "$HARV" ] || python3 scripts/harvest_subgoals.py --rollouts "$S0ROLL" --dead_only --out "$HARV" >> "$LOG" 2>&1
NH=$([ -s "$HARV" ] && wc -l < "$HARV" || echo 0)
say "  harvest: 닫힌 subgoal $NH 그룹 (dead 그룹 출신)"
[ "$NH" -gt 0 ] || { say "  harvest 0 — 중단"; exit 1; }

# ── 2) RFT (--sft): reward=1 트레이스 순수 MLE (init=cascade-s0) ──
[ -f models/rango-grpo-cascade-harvest/adapter/adapter_model.safetensors ] || \
  python3 -m tactic_gen.grpo_train --rollouts "$HARV" --model_name "$BASE" --init_adapter "$S0M" \
    --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-grpo-cascade-harvest/adapter \
    --sft --kl_beta 0.0 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
cpconf models/rango-grpo-cascade-harvest
HM=models/rango-grpo-cascade-harvest/adapter
[ -f "$HM/adapter_model.safetensors" ] || { say "✗ RFT 실패"; exit 1; }
say "  RFT(--sft) 완료 → cascade-harvest"

# ── 3) s0 재롤아웃 (정책=harvest 모델, Qed 보상) ──
export SUBGOAL_CURRICULUM=data/curriculum/empty.json SUBGOAL_OUT=data/grpo_rollouts/rango-grpo-cascade-s0r2.jsonl SUBGOAL_SKIP_S0=0 SUBGOAL_REWARD=0 SUBGOAL_POLICY="$HM"
say "  ▶ s0 재롤아웃(정책=harvest, 300정리, g2w$ROLLW)"
[ -s "$SUBGOAL_OUT" ] || python3 scripts/run_all.py --alias grpo-rollout-subgoal --idx-file "$TRAIN" --timeout 600 --gpus "$GPUS" --workers $ROLLW >> "$LOG" 2>&1

# ── 4) s0 GRPO (init=harvest 모델) ──
[ -f models/rango-grpo-cascade-s0r2/adapter/adapter_model.safetensors ] || gtrain "$SUBGOAL_OUT" "$HM" models/rango-grpo-cascade-s0r2
say "  s0r2 학습 완료 → cascade-s0r2 (최종)"

# ── 5) rand200@600s g2w4 평가 ──
say "▶ [평가] rand200@600s g2w4 (cascade-s0r2)"
RD=all_results/rand200_cascade_s0r2_g2w4600s
NRAND=$(wc -l < "$RAND")
if [ ! -s "$RD/summary.json" ] || [ "$(python3 -c "import json;print(len(json.load(open('$RD/summary.json'))['results']))" 2>/dev/null||echo 0)" -lt "$NRAND" ]; then
  python3 scripts/run_all.py --alias rango-grpo-cascade-s0r2 --idx-file "$RAND" --timeout 600 --gpus "$GPUS" --workers $EVALW --out "$RD" --description "harvest s0r2 rand200" >> "$LOG" 2>&1
fi
SR=$(python3 -c "import json;r=json.load(open('$RD/summary.json'))['results'];print(f\"{sum(1 for x in r if x['success'])}/{len(r)}\")" 2>/dev/null||echo '?')
say "════════ HARVEST 라운드 결과 ════════"
say "  [rand200 cascade-s0r2] = $SR   (cascade-s0=67/200=33.5% · SFT→GRPO=75/200=37.5% · baseline=33.5%)"
say "════════ 완료 ════════"
