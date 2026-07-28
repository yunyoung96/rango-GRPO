#!/bin/bash
# ★ rango-grpo-scale — CompCert 내부 학습셋 확대 (40 → 200개, cc[200:400]).
#
# rango-grpo(40개) 대비 유일한 변인 = **학습셋 크기**. 재샘플링/PRM 없음(순수 크기 격리).
#   가설: 신호그룹 12개(dead 69%)가 부족한 게 병목 → 5배로 늘리면 신호 확보 → 정책 개선.
#   평가셋 cc[0:180]과 정리 겹침 0 (같은 프로젝트라 파일은 겹침 = sibling, 정직히 표기).
#
# 비교기준 = 우리 rango (@20=11, @40=15). smart_eval 에스컬레이션.
# ※ 학습 후 training_conf/lm-example-conf 복사 필수(없으면 서버 로딩 hang).
set -u
LOG=all_log/scale_grpo.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF="$(dirname "$INIT")/training_conf.yaml"
IDX=data/compcert_scale_idx.txt
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
train(){ python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$2" --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 "${@:3}" >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$(dirname "$2")/" 2>/dev/null; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }

say "===== rango-grpo-scale (CompCert 200개 학습) 시작 ====="

# ── 1. 롤아웃 수집 (200개, 재샘플링 없음) ────────────────────────────
say "▶ 1/3  롤아웃 수집 ($(wc -l < $IDX)개 정리, k=0)"
if [ ! -s data/grpo_rollouts/scale.jsonl ]; then
  rm -f data/grpo_rollouts/scale.jsonl
  python3 scripts/run_all.py --alias grpo-rollout-scale --idx-file "$IDX" \
    --timeout 600 --workers 2 --description "scale rollout cc[200:400]" >> "$LOG" 2>&1
fi
if [ -s data/grpo_rollouts/scale.jsonl ]; then
  python3 - <<'PY' 2>&1 | tee -a "$LOG"
import json
g=[json.loads(l) for l in open('data/grpo_rollouts/scale.jsonl')]
att=[a for x in g for a in x['attempts']]; su=sum(1 for a in att if a['reward']>=1)
dead=sum(1 for x in g if all(a['reward']<1 for a in x['attempts']))
sig=len(g)-dead-sum(1 for x in g if all(a['reward']>=1 for a in x['attempts']))
print(f"  scale 롤아웃: {len(g)}그룹 시도성공 {su}/{len(att)}({su/max(len(att),1):.0%}) 신호그룹 {sig}({sig/max(len(g),1):.0%})")
print(f"    [기존 40개는 신호그룹 12(31%). 크기 5배 → 신호 절대량 {sig}개]")
PY
else say "  ★ 롤아웃 수집 실패"; exit 1; fi

# ── 2. 학습 (outcome / +PRM) ─────────────────────────────────────────
say "▶ 2/3  학습"
[ ! -f models/rango-grpo-scale/adapter/adapter_model.safetensors ] && \
  train data/grpo_rollouts/scale.jsonl models/rango-grpo-scale/adapter
[ ! -f models/rango-grpo-scale-prm/adapter/adapter_model.safetensors ] && \
  train data/grpo_rollouts/scale.jsonl models/rango-grpo-scale-prm/adapter --process

# ── 3. 평가 ──────────────────────────────────────────────────────────
say "▶ 3/3  평가 (smart_eval @20→@40)"
[ -f models/rango-grpo-scale/adapter/adapter_model.safetensors ] && seval rango-grpo-scale || say "  ★ scale 학습 실패"
[ -f models/rango-grpo-scale-prm/adapter/adapter_model.safetensors ] && seval rango-grpo-scale-prm || say "  ★ scale-prm 학습 실패"

say "===== rango-grpo-scale 완료 ====="
grep -h "smart\] ■" "$LOG" | tail -6
