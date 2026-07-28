#!/bin/bash
# ★ Reverse curriculum(전체 역행) @20→@40 — on-fix.
#   gold 의 모든 중간상태(remaining 2~8)에서 각각 롤아웃 → 정리당 s_0 + 여러 curriculum 그룹.
#   backward(remaining=4 한 점)의 완전형. 각 시작상태가 자기 baseline(GRPO 그룹 분리).
#   fix 정책으로 수집 + fix 초기화(expert-iteration). all-success/all-fail 그룹은 학습때 스킵.
# 비교기준 = 우리 rango(@20=11,@40=15) + fix(@20=13,@40=19). published 비교 안 함.
set -u
LOG=all_log/revcurr.log
WORKERS=${WORKERS:-2}
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/rango-grpo-fix/adapter        # fix 위에서 이어 학습
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }

say "===== Reverse curriculum @20→@40 (on-fix) 시작 ====="

say "1) revcurr 커리큘럼 빌드 (gold 모든 중간상태, remaining 2~8)"
python3 scripts/build_revcurr_curriculum.py >> "$LOG" 2>&1
[ -s data/curriculum/revcurr.json ] || { say "★ revcurr 빌드 실패 — 중단"; exit 1; }
say "   $(python3 -c "import json;d=json.load(open('data/curriculum/revcurr.json'));print(f'{len(d)}정리, 시작점 {sum(len(v[\"starts\"]) for v in d.values())}개')")"

say "2) 롤아웃 수집 (fix 정책, 정리당 s_0 + 다중 curriculum, retry k=4)"
if [ ! -s data/grpo_rollouts/revcurr.jsonl ]; then
  rm -f data/grpo_rollouts/revcurr.jsonl
  python3 scripts/run_all.py --alias grpo-rollout-revcurr --start 200 --num 40 \
    --timeout 900 --workers "$WORKERS" \
    --description "reverse curriculum 롤아웃(전체 역행, on-fix)" >> "$LOG" 2>&1
fi
[ -s data/grpo_rollouts/revcurr.jsonl ] || { say "★ 롤아웃 수집 실패 — 중단"; exit 1; }

say "3) ★ 효과 측정 — 시작점별 신호 그룹 분포"
python3 - <<'PY' 2>&1 | tee -a "$LOG"
import json, collections
g=[json.loads(l) for l in open('data/grpo_rollouts/revcurr.jsonl')]
by=collections.Counter(); sig=collections.Counter(); tot=collections.Counter()
for x in g:
    lab=x.get('start','s0'); band = 's0' if lab=='s0' else lab
    att=x['attempts']; su=sum(1 for a in att if a['reward']>=1)
    tot[band]+=1
    mixed = 0<su<len(att)
    if mixed: sig[band]+=1
print(f"  총 그룹 {len(g)}개")
for b in sorted(tot):
    print(f"    {b:14s}: {tot[b]:3d}그룹, 혼합(신호O) {sig[b]:3d} ({sig[b]/max(tot[b],1):3.0%})")
allmix=sum(sig.values())
print(f"  ★ 전체 혼합그룹(신호O) {allmix}/{len(g)} ({allmix/max(len(g),1):.0%})  [기존 backward s_k 참고: 매우 높음]")
PY

say "4) 학습 (fix 초기화, 순수 curriculum GRPO — gold 주입 없음)"
[ ! -f models/rango-grpo-revcurr/adapter/adapter_model.safetensors ] && \
  python3 -m tactic_gen.grpo_train \
    --rollouts data/grpo_rollouts/revcurr.jsonl \
    --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 \
    --save_dir models/rango-grpo-revcurr/adapter \
    --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1
cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-revcurr/ 2>/dev/null

say "5) 평가 (smart_eval @20→@40)"
[ -f models/rango-grpo-revcurr/adapter/adapter_model.safetensors ] && seval rango-grpo-revcurr || say "★ revcurr 학습 실패"

say "===== Reverse curriculum 완료 ====="
grep -h "smart\] ■" "$LOG" 2>/dev/null | tail -4
