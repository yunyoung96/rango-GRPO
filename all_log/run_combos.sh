#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# D = DeepSeek-Prover-V2 스타일 (SFT+GRPO+DPO), **expert iteration 2회** — 논문 충실.
# U = SRFT/Unified (SFT+GRPO 단일스테이지), 1회.
#   GPU0에서 학습(B는 GPU1). 학습·저장 후 D→U 순으로 rand200 w2 평가.
#   D Round1: B의 R1 검색결과 재활용(동일 baseline·동일 beam/collect라 통계적 동치) → 7h 절약.
#     SFT=B round1/sft/adapter → GRPO(baseline rollout) → DPO(B round1 pairs) = D1
#   D Round2: D1로 새 beam→BFS수집 → 추출 → SFT(누적)→GRPO(D1 rollout)→DPO = D2 = D_final
#   U: SRFT(baseline + baseline rollout + R1 성공 SFT), 1회.
# ══════════════════════════════════════════════════════════════════════════════
set -u
LOG=all_log/combos.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500   # baseline π_0
TRAIN=data/compcert_bs2_train_idx.txt      # 300
RAND=data/compcert_bs2_rand200_idx.txt     # 200
B_R1_SFT=data/bfs_expert_iter/round1/sft/adapter      # D Round1 SFT 재사용(B R1)
CUMSFT_R1=data/combo/cum_sft_r1.jsonl                 # R1 성공 SFT 스냅샷(735)
PAIRS_R1=data/combo/pairs_r1.jsonl                    # R1 DPO 스냅샷(83)
GRPORO=data/grpo_rollouts/combo_grpo.jsonl            # baseline GRPO rollout(D1 GRPO + U)
WORK=data/combo
GPU="${GPU:-0}"; W="${W:-8}"; RT="${RT:-300}"; BEAMT="${BEAMT:-120}"; BFST="${BFST:-300}"; ET="${ET:-600}"
TS="taskset -c 0-127"
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
gtrain(){ CUDA_VISIBLE_DEVICES="$GPU" $TS python3 -m tactic_gen.grpo_train "$@" >> "$LOG" 2>&1; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }
mkdir -p "$WORK"
[ -f "$B_R1_SFT/adapter_model.safetensors" ] || { say "✗ B R1 SFT 없음: $B_R1_SFT"; exit 1; }
say "════ 조합: D=SFT+GRPO+DPO(EI 2회) + U=SRFT(1회) — GPU$GPU w$W, B와 병렬 ════"

# baseline GRPO rollout (D1 GRPO + U 공유). 완결성(300)까지 재개.
rollgen(){ local pol="$1" out="$2" odir="$3"
  local done=$(python3 -c "import json;print(len(json.load(open('$odir/summary.json'))['results']))" 2>/dev/null||echo 0)
  [ "$done" -ge 300 ] && return
  say "  rollout 생성/재개 ($odir): $done/300"
  SUBGOAL_CURRICULUM=data/curriculum/empty.json SUBGOAL_OUT="$out" SUBGOAL_POLICY="$pol" \
    SUBGOAL_SKIP_S0=0 SUBGOAL_REWARD=0 SUBGOAL_HYBRID=0 SUBGOAL_GS=8 SUBGOAL_MAXSTEPS=20 \
    $TS python3 scripts/run_all.py --alias grpo-rollout-subgoal --idx-file "$TRAIN" \
    --timeout "$RT" --gpus "$GPU" --workers "$W" --out "$odir" >> "$LOG" 2>&1
}

# ════════ D: expert iteration 2회 ════════
# ── D Round 1 (B R1 재사용): SFT(B) → GRPO(baseline rollout) → DPO(B pairs) ──
say "──── D Round 1 (SFT=B재사용 → GRPO → DPO) ────"
rollgen "$INIT" "$GRPORO" all_results/combo_grpo_rollout
if [ ! -f models/rango-combo-d1-grpo/adapter/adapter_model.safetensors ]; then
  gtrain --rollouts "$GRPORO" --model_name "$BASE" --init_adapter "$B_R1_SFT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-combo-d1-grpo/adapter \
    --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2
fi
cpconf models/rango-combo-d1-grpo
if [ ! -f models/rango-combo-d1/adapter/adapter_model.safetensors ] && [ -s "$PAIRS_R1" ]; then
  CUDA_VISIBLE_DEVICES="$GPU" $TS python3 src/tactic_gen/dpo_train.py \
    --pairs "$PAIRS_R1" --model_name "$BASE" --init_adapter models/rango-combo-d1-grpo/adapter \
    --save_dir models/rango-combo-d1/adapter --collator_conf "$CONF" --max_len 3072 \
    --epochs 1 --lr 5e-7 --beta 0.1 --micro_bsz 2 >> "$LOG" 2>&1
fi
cpconf models/rango-combo-d1
D1=models/rango-combo-d1/adapter
say "  D Round 1 완료 → $D1"

# ── D Round 2 (D1로 새 검색): beam→collect→추출→SFT(누적)→GRPO(D1 rollout)→DPO ──
say "──── D Round 2 (D1 새 검색 → SFT+GRPO+DPO) ────"
RD=$WORK/d_round2; mkdir -p "$RD"
# beam 필터
BFS_ADAPTER="$D1" $TS python3 scripts/run_all.py --alias bfs-prover-beam \
  --idx-file "$TRAIN" --timeout "$BEAMT" --gpus "$GPU" --workers "$W" \
  --out "$RD/beam" >> "$LOG" 2>&1
python3 -m tactic_gen.bfs_dpo_data hard "$RD/beam/summary.json" "$TRAIN" "$RD/hard.txt" | tee -a "$LOG"
# BFS 수집
[ -s "$RD/collect/summary.json" ] || rm -f "$RD"/trees.jsonl.* "$RD/trees_all.jsonl"
BFS_ADAPTER="$D1" BFS_TRACE_OUT="$RD/trees.jsonl" $TS python3 scripts/run_all.py --alias bfs-prover-trace \
  --idx-file "$RD/hard.txt" --timeout "$BFST" --gpus "$GPU" --workers "$W" \
  --out "$RD/collect" >> "$LOG" 2>&1
cat "$RD"/trees.jsonl.* > "$RD/trees_all.jsonl" 2>/dev/null
# 추출(R2 성공 → sft2/pairs2) + 누적 SFT = R1 + R2
if [ ! -f "$RD/.extracted" ]; then
  python3 -m tactic_gen.bfs_dpo_data extract "$RD/trees_all.jsonl" "$RD/sft2_only.jsonl" "$RD/pairs2.jsonl" | tee -a "$LOG"
  touch "$RD/.extracted"
fi
# extract는 2번째 인자에 append → sft2_only는 이 라운드만. 누적 = R1 스냅샷 + sft2
cat "$CUMSFT_R1" "$RD/sft2_only.jsonl" > "$RD/cum_sft2.jsonl" 2>/dev/null
say "  D R2 누적 SFT = $(wc -l <"$RD/cum_sft2.jsonl")그룹, pairs2=$(wc -l <"$RD/pairs2.jsonl" 2>/dev/null)쌍"
# D1로 새 GRPO rollout
rollgen "$D1" "$WORK/d2_grpo.jsonl" all_results/combo_d2_rollout
# SFT(누적) → GRPO(D1 rollout) → DPO(pairs2)
if [ ! -f "$RD/sft/adapter/adapter_model.safetensors" ]; then
  gtrain --sft --rollouts "$RD/cum_sft2.jsonl" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$RD/sft/adapter" --epochs 2 --lr 1e-5 --micro_bsz 4
fi
cpconf "$RD/sft"
if [ ! -f "$RD/grpo/adapter/adapter_model.safetensors" ]; then
  gtrain --rollouts "$WORK/d2_grpo.jsonl" --model_name "$BASE" --init_adapter "$RD/sft/adapter" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$RD/grpo/adapter" --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2
fi
cpconf "$RD/grpo"
if [ ! -f "$RD/dpo/adapter/adapter_model.safetensors" ] && [ -s "$RD/pairs2.jsonl" ]; then
  CUDA_VISIBLE_DEVICES="$GPU" $TS python3 src/tactic_gen/dpo_train.py \
    --pairs "$RD/pairs2.jsonl" --model_name "$BASE" --init_adapter "$RD/grpo/adapter" \
    --save_dir "$RD/dpo/adapter" --collator_conf "$CONF" --max_len 3072 \
    --epochs 1 --lr 5e-7 --beta 0.1 --micro_bsz 2 >> "$LOG" 2>&1
fi
cpconf "$RD/dpo"
if [ -f "$RD/dpo/adapter/adapter_model.safetensors" ]; then D_FINAL="$RD/dpo/adapter"; else D_FINAL="$RD/grpo/adapter"; fi
say "  D Round 2 완료 → D_FINAL=$D_FINAL"

# ════════ U: SRFT 1회 (baseline + baseline rollout + R1 성공 SFT) ════════
say "──── U SRFT (single-stage, 1회) ────"
if [ ! -f models/rango-combo-u/adapter/adapter_model.safetensors ]; then
  CUDA_VISIBLE_DEVICES="$GPU" $TS python3 src/tactic_gen/srft_train.py \
    --rollouts "$GRPORO" --sft_data "$CUMSFT_R1" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-combo-u/adapter \
    --kl_beta 0.04 --sft_coef 1.0 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
fi
cpconf models/rango-combo-u
U_FINAL=models/rango-combo-u/adapter
say "  U 완료 → $U_FINAL"

# ════════ 평가: D → U 순, rand200 w6 (GPU0 전용 w6 = B의 GPU1 w6와 밀도 동일 = 공정) ════════
EVALW="${EVALW:-6}"
evalw2(){ local ad="$1" name="$2" out="$3"
  local n=$(python3 -c "import json;print(len(json.load(open('$out/summary.json'))['results']))" 2>/dev/null || echo 0)
  [ "$n" -ge 200 ] && return
  say "  평가 $name (rand200 GPU$GPU w$EVALW, trace 남김)"
  rm -f "$out"/trace.jsonl.*
  BFS_ADAPTER="$ad" BFS_TRACE_OUT="$out/trace.jsonl" $TS python3 scripts/run_all.py --alias bfs-prover \
    --idx-file "$RAND" --timeout "$ET" --gpus "$GPU" --workers "$EVALW" \
    --out "$out" --description "$name rand200 w$EVALW" >> "$LOG" 2>&1
}
say "════ rand200 w$EVALW 평가: D → U 순 ════"
evalw2 "$D_FINAL" "combo-D(EI2)" all_results/rand200_combo_d
evalw2 "$U_FINAL" "combo-U(SRFT)" all_results/rand200_combo_u
python3 - <<PY | tee -a "$LOG"
import json
def sr(p):
    try:
        r=json.load(open(p))['results']; s=sum(1 for x in r if x['success'])
        su=sorted(x['elapsed_sec'] for x in r if x['success']); p90=su[int(0.9*len(su))] if su else 0
        flag="clean" if p90<430 else "⚠오염의심"
        return f"{s}/{len(r)} ({100*s/max(len(r),1):.1f}%)  p90={p90:.0f}s [{flag}]"
    except Exception as e: return f"?({e})"
print("  combo-D (SFT+GRPO+DPO, EI2회) rand200:", sr("all_results/rand200_combo_d/summary.json"))
print("  combo-U (SRFT 1회)          rand200:", sr("all_results/rand200_combo_u/summary.json"))
PY
say "════ [combos 완료] ════"
