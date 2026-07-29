#!/bin/bash
# divergence-DPO 학습+평가 — ★GPU1 전용(GPU0 절대 안 씀).
#   init=π₀(SFT→GRPO), pairs=divergence_dpo.jsonl (chosen=gold분해 / rejected=정책 이탈 VALID tactic).
#   dpo_train은 ref=init 자동앵커(=π₀). 평가는 rand200 w2/GPU1(공정).
set -u
LOG=all_log/divdpo.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
PI0=models/rango-grpo/adapter
PAIRS=data/grpo_rollouts/divergence_dpo.jsonl
RAND=data/compcert_bs2_rand200_idx.txt
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }

[ -s "$PAIRS" ] || { say "✗ divergence pairs 없음 — build_divergence_dpo.py 먼저"; exit 1; }
say "════ divergence-DPO 학습 (init=π₀, GPU1, β=0.1, lr5e-7, ep2) · 쌍 $(wc -l < "$PAIRS")개 ════"
[ -f models/rango-grpo-divdpo/adapter/adapter_model.safetensors ] || \
  CUDA_VISIBLE_DEVICES=1 python3 src/tactic_gen/dpo_train.py \
    --pairs "$PAIRS" --model_name "$BASE" --init_adapter "$PI0" \
    --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-grpo-divdpo/adapter \
    --epochs 2 --lr 5e-7 --beta 0.1 --micro_bsz 2 >> "$LOG" 2>&1
cpconf models/rango-grpo-divdpo
say "  학습 완료. dpo loss/acc:"; grep '\[dpo\] epoch' "$LOG" | tail -3 | sed 's/^/    /' | tee -a "$LOG"

say "════ divergence-DPO 평가: rand200 w2 600s (GPU1) ════"
RD=all_results/rand200_divdpo_w2
[ -s "$RD/summary.json" ] || python3 scripts/run_all.py --alias rango-grpo-divdpo \
    --idx-file "$RAND" --timeout 600 --gpus 1 --workers 2 --out "$RD" --description "divergence-DPO rand200 w2" >> "$LOG" 2>&1
SR=$(python3 -c "import json;r=json.load(open('$RD/summary.json'))['results'];su=sorted(x['elapsed_sec'] for x in r if x['success']);p=su[int(0.9*len(su))] if su else 0;print(f\"{sum(1 for x in r if x['success'])}/{len(r)} (p90 {p:.0f}s)\")" 2>/dev/null||echo '?')
say "════ ★ divergence-DPO rand200 w2 = $SR   (vs SFT→GRPO 75/200=37.5%) ════"
say "════ [divdpo 완료] ════"
