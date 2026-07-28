#!/bin/bash
# ★ Conservative LUFFY (KL-LUFFY) @20→@40 — 회귀 진단 처방.
#   진단: LUFFY 가 gold 항 KL 을 빼서 fix 를 무제약으로 끌어내 회귀(covariate shift+무제약 업데이트).
#   처방: gold 항에 KL(π_θ‖fix) 복원(--luffy_kl) → fix 근처에 묶어 회귀 방지.
#   ★ 롤아웃 재사용: 기존 fix 기반 luffy.jsonl(gold 주입 완료). 롤아웃 안 함 → 빠름(학습+평가만).
#   LUFFY 와의 유일한 차이 = KL 뿐(깨끗한 ablation).
# 비교기준 = fix(@20=13,@40=19) + luffy-on-fix(회귀판) + 우리 rango(11/15).
set -u
LOG=all_log/luffy_kl.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/rango-grpo-fix/adapter        # fix 초기화(ref=fix → KL 이 fix 로 당김)
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }

say "===== KL-LUFFY @20→@40 (fix 기반 luffy.jsonl 재사용) 시작 ====="
[ -s data/grpo_rollouts/luffy.jsonl ] || { say "★ luffy.jsonl 없음 — 중단(fix 기반 롤아웃 필요)"; exit 1; }
say "  롤아웃 재사용: $(wc -l < data/grpo_rollouts/luffy.jsonl)그룹"

say "1) 학습 (--luffy --luffy_kl, fix 초기화)"
[ ! -f models/rango-grpo-luffy-kl/adapter/adapter_model.safetensors ] && \
  python3 -m tactic_gen.grpo_train \
    --rollouts data/grpo_rollouts/luffy.jsonl \
    --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 \
    --save_dir models/rango-grpo-luffy-kl/adapter \
    --luffy --luffy_kl --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1
cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-luffy-kl/ 2>/dev/null

say "2) 평가 (smart_eval @20→@40)"
[ -f models/rango-grpo-luffy-kl/adapter/adapter_model.safetensors ] && seval rango-grpo-luffy-kl || say "★ KL-LUFFY 학습 실패"

say "===== KL-LUFFY 완료 ====="
grep -h "smart\] ■" "$LOG" 2>/dev/null | tail -3
