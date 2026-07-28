#!/bin/bash
# ★ Backward curriculum @40 — sparse reward 의 구조적 해법.
#
# 인간 gold 증명의 중간 상태(남은 tactic 4개)에서도 롤아웃 → 성공확률을 50% 근처로 조준.
#   현재(정리 처음부터, L≈14): 1회 성공률 5.8% → 8회 혼합그룹(신호O) 38% (실측 27%)
#   remaining=4 에서 시작    : 1회 성공률 44%  → 8회 혼합그룹 98.9%
#   → dead group 73% 가 구조적으로 사라진다.
#
# 정리마다 **그룹 2개**: s_0(처음) 8시도 + s_k(중간) 8시도. 절대 섞지 않는다 —
#   그룹 평균이 V(s) baseline 이라 같은 시작점에서 나와야 한다(test_prm_grpo.py §7 검증).
#
# 재샘플링(k=4)도 함께 켠다 → 두 처방이 곱해진다: p 0.816→0.994, L 14→4 ⇒ 완주율 5.8%→97.6%
set -u
LOG=all_log/backward.log
WORKERS=${WORKERS:-2}
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "===== Backward curriculum @40 시작 ====="
say "1) 커리큘럼 빌드 (학습셋 cc[200:240], 전역 idx 376~443)"
python3 scripts/build_backward_curriculum.py --remaining 4 >> "$LOG" 2>&1
[ -s data/curriculum/backward.json ] || { say "★ 커리큘럼 빌드 실패 — 중단"; exit 1; }

say "2) 롤아웃 수집 (정리당 그룹 2개: s_0 + s_k, 각 8시도, 재샘플링 k=4)"
rm -f data/grpo_rollouts/backward.jsonl
python3 scripts/run_all.py --alias grpo-rollout-backward --start 200 --num 40 \
  --timeout 900 --workers "$WORKERS" \
  --description "backward curriculum 롤아웃(s0+sk 별도그룹, retry k=4)" >> "$LOG" 2>&1

say "3) ★ 효과 측정 — dead group 이 실제로 줄었나"
python3 - <<'PY' 2>&1 | tee -a "$LOG"
import json, collections
try:
    g=[json.loads(l) for l in open('data/grpo_rollouts/backward.jsonl')]
except FileNotFoundError:
    print("  롤아웃 파일 없음"); raise SystemExit
by=collections.defaultdict(list)
for x in g: by[x.get('start','s0')].append(x)
print(f"\n  {'시작점':<12} {'그룹':>5} {'시도성공':>12} {'dead(전멸)':>12} {'혼합(신호O)':>14}")
for k in ['s0','curriculum']:
    gs=by.get(k,[])
    if not gs: continue
    att=[a for x in gs for a in x['attempts']]
    su=sum(1 for a in att if a['reward']>=1.0)
    dead=sum(1 for x in gs if all(a['reward']<1 for a in x['attempts']))
    allw=sum(1 for x in gs if all(a['reward']>=1 for a in x['attempts']))
    mixed=len(gs)-dead-allw
    lab = 's_0 (처음부터)' if k=='s0' else 's_k (중간부터)'
    print(f"  {lab:<12} {len(gs):>5} {su:>4}/{len(att):<3} ({su/len(att):4.0%}) "
          f"{dead:>4}/{len(gs):<3} ({dead/len(gs):4.0%}) {mixed:>5}/{len(gs):<3} ({mixed/len(gs):4.0%})")
print(f"\n  기존(round-1, 재샘플링·커리큘럼 없음): 혼합그룹 11/41 = 27%")
PY

say "4) 학습 (backward 롤아웃, base=instruct)"
python3 -m tactic_gen.grpo_train \
  --rollouts data/grpo_rollouts/backward.jsonl \
  --model_name deepseek-ai/deepseek-coder-1.3b-instruct \
  --init_adapter models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500 \
  --collator_conf models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml --max_len 3072 \
  --save_dir models/rango-grpo-backward/adapter \
  --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-backward/ 2>/dev/null

say "5) + PRM (같은 롤아웃, --process 만 추가 → 깨끗한 ablation)"
python3 -m tactic_gen.grpo_train \
  --rollouts data/grpo_rollouts/backward.jsonl \
  --model_name deepseek-ai/deepseek-coder-1.3b-instruct \
  --init_adapter models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500 \
  --collator_conf models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml --max_len 3072 \
  --save_dir models/rango-grpo-backward-prm/adapter \
  --process --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-backward-prm/ 2>/dev/null

# ★ 평가: smart_eval @20→@40 에스컬레이션(20 먼저, 가능성 보이면 40). 기준=우리 rango(published 비교 안 함).
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }
[ -f models/rango-grpo-backward/adapter/adapter_model.safetensors ] && \
  seval rango-grpo-backward || say "★ backward 학습 실패"
[ -f models/rango-grpo-backward-prm/adapter/adapter_model.safetensors ] && \
  seval rango-grpo-backward-prm || say "★ backward-prm 학습 실패"

say "===== Backward curriculum @40 완료 ====="
grep '■' "$LOG"
