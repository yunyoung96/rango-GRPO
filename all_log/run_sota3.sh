#!/bin/bash
# SOTA 3종 @40 평가. robustness @180 + 오염수습이 전부 끝난 뒤 GPU 독점 상태에서 실행.
#
#  #2 PGTS         (2604.24354) — 학습 불필요. 바로 평가.
#  #1 progress critic (2502.17925) — critic 학습 → α sweep 평가.
#  #3 PRM-GRPO     (2606.20068) — rollout 재수집(result 기록) → 학습 → 평가.
#
# 비교 기준(@40): published baseline 12 · rango-grpo 16 · bfs-a1 16 · portfolio 15
set -u
LOG=all_log/sota3.log
NUM=${NUM:-40}
WORKERS=${WORKERS:-2}
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
evalr(){  # evalr <alias> <설명>
  say "----- eval: $1 @${NUM} -----"
  python3 scripts/run_all.py --alias "$1" --num "$NUM" --timeout 600 --workers "$WORKERS" \
    --description "$2" >> "$LOG" 2>&1
  d=$(ls -dt all_results/*_"$(echo "$1" | sed 's/[^A-Za-z0-9._-]/-/g')" 2>/dev/null | head -1)
  s=$(python3 -c "
import json;dd=json.load(open('$d/summary.json'));r=dd['results']
su=sum(1 for x in r if x.get('success'));ob=sum(1 for x in r if x.get('original_success'))
g=[x['idx'] for x in r if x.get('success') and not x.get('original_success')]
c=[x['idx'] for x in r if x.get('original_success') and not x.get('success')]
print(f\"{su}/{len(r)} | published {ob} | net {su-ob:+d} | gain {len(g)} 회귀 {len(c)} {c}\")" 2>/dev/null)
  say "■ $1: ${s}  -> ${d}"
}

say "===== SOTA 3종 @${NUM} 시작 ====="

# ── #2 PGTS: 학습 불필요 ────────────────────────────────────────────────
say "### #2 PGTS (패턴 재랭킹 + 기호적 가지치기)"
evalr pgts     "PGTS full: bfs-a1 + tactic-pattern 재랭킹 + failure dict + no-progress"
evalr pgts-sym "PGTS ablation: 기호적 가지치기만(β=0)"
evalr pgts-pat "PGTS ablation: 패턴 재랭킹만"

# ── #1 progress critic: 학습 → α sweep ─────────────────────────────────
say "### #1 progress critic 학습 (LeanProgress)"
python3 scripts/train_progress_critic.py \
  --data data/progress/train.jsonl \
  --save_dir models/progress_critic \
  --max_samples 200000 --epochs 1 --bsz 8 >> "$LOG" 2>&1
if [ -f models/progress_critic/head.pt ]; then
  say "critic 학습 완료"
  evalr rango-progress-a0  "progress α=0 (sanity: bfs-a1과 순위 동일해야 함)"
  evalr rango-progress     "progress α=0.2 (논문 최적값)"
  evalr rango-progress-a05 "progress α=0.5"
  evalr rango-progress-a10 "progress α=1.0 (순수 value — 논문은 붕괴한다고 보고)"
else
  say "★ critic 학습 실패 — progress 평가 건너뜀"
fi

# ── 롤아웃 재수집 (#3 과 base정정 재학습이 공유) ────────────────────────
# 옛 rollouts.jsonl 은 (a) step["result"] 가 없어 PRM 불가, (b) E3 가 덮어써서 round-1 원본도 아님.
# 경로도 alias 별로 분리한다 — 안 그러면 다음 실험이 또 지운다.
say "### 롤아웃 재수집 (step['result'] 기록, 경로 분리)"
python3 scripts/run_all.py --alias grpo-rollout --start 200 --num 40 \
  --timeout 600 --workers "$WORKERS" \
  --description "rollout 재수집(result 기록, base 정정 이후)" >> "$LOG" 2>&1
cp data/grpo_rollouts/rollouts.jsonl data/grpo_rollouts/round1-fixed.jsonl 2>/dev/null
say "rollout 수집 완료 → data/grpo_rollouts/round1-fixed.jsonl"

# ── base 정정 GRPO 재학습 (알고리즘 동일, 베이스만 instruct) ────────────
# 기존 rango-grpo: 롤아웃=instruct정책 / 학습=base / 배포=instruct → 셋이 다름.
# 이번: 셋 다 instruct. rango-grpo(16/40) 대비 **유일한 변인이 베이스 모델**이다.
say "### base 정정 GRPO 재학습 (rango-grpo-fix)"
python3 -m tactic_gen.grpo_train \
  --rollouts data/grpo_rollouts/round1-fixed.jsonl \
  --model_name deepseek-ai/deepseek-coder-1.3b-instruct \
  --init_adapter models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500 \
  --save_dir models/rango-grpo-fix/adapter \
  --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
if [ -f models/rango-grpo-fix/adapter/adapter_model.safetensors ]; then
  say "base 정정 GRPO 학습 완료"
  evalr rango-grpo-fix "GRPO(base 정정: instruct 통일). rango-grpo 대비 유일한 변인 = 베이스 모델"
else
  say "★ base 정정 GRPO 학습 실패 — 평가 건너뜀"
fi

# ── #3 PRM-GRPO: 같은 롤아웃 + process reward ───────────────────────────
say "### #3 PRM-GRPO (같은 롤아웃, --process 만 추가)"
python3 -m tactic_gen.grpo_train \
  --rollouts data/grpo_rollouts/round1-fixed.jsonl \
  --model_name deepseek-ai/deepseek-coder-1.3b-instruct \
  --init_adapter models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500 \
  --save_dir models/rango-grpo-prm/adapter \
  --process --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
if [ -f models/rango-grpo-prm/adapter/adapter_model.safetensors ]; then
  say "PRM-GRPO 학습 완료"
  # rango-grpo-fix 와 롤아웃·베이스·하이퍼가 전부 같고 --process 만 다르다 → 깨끗한 ablation
  evalr rango-grpo-prm "PRM-GRPO: coq-lsp 검증 기반 per-tactic process reward(첫 토큰 credit)"
else
  say "★ PRM-GRPO 학습 실패 — 평가 건너뜀"
fi

# ── #4 재샘플링 롤아웃 (§7 P1) ─────────────────────────────────────────
# 2×2 factorial:  (재샘플링 유/무) × (process reward 유/무)
#   rango-grpo-fix       : 재샘플링 ✗  process ✗   ← 기준
#   rango-grpo-prm       : 재샘플링 ✗  process ✓
#   rango-grpo-retry     : 재샘플링 ✓  process ✗
#   rango-grpo-retry-prm : 재샘플링 ✓  process ✓   ← 풀스택
say "### #4 재샘플링 롤아웃 수집 (max_retries=4)"
python3 scripts/run_all.py --alias grpo-rollout-retry --start 200 --num 40 \
  --timeout 900 --workers "$WORKERS" \
  --description "재샘플링 롤아웃(k=4): INVALID 시 같은 state 재샘플" >> "$LOG" 2>&1

if [ -s data/grpo_rollouts/retry.jsonl ]; then
  say "재샘플링 롤아웃 수집 완료 — 효과 측정:"
  python3 - <<'PY' 2>&1 | tee -a "$LOG"
import json
for f in ['round1-fixed','retry']:
    try:
        g=[json.loads(l) for l in open(f'data/grpo_rollouts/{f}.jsonl')]
    except FileNotFoundError:
        continue
    att=[a for x in g for a in x['attempts']]
    su=sum(1 for a in att if a['reward']>=1.0)
    dead=sum(1 for x in g if all(a['reward']<1 for a in x['attempts']))
    allw=sum(1 for x in g if all(a['reward']>=1 for a in x['attempts']))
    print(f"  {f:14} 그룹{len(g):3} 시도성공 {su:3}/{len(att):3} ({su/len(att):5.1%}) "
          f"dead {dead:2} 버려지는그룹 {dead+allw}/{len(g)}")
PY

  say "### 재샘플링 GRPO 학습 (outcome only)"
  python3 -m tactic_gen.grpo_train \
    --rollouts data/grpo_rollouts/retry.jsonl \
    --model_name deepseek-ai/deepseek-coder-1.3b-instruct \
    --init_adapter models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500 \
    --save_dir models/rango-grpo-retry/adapter \
    --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
  [ -f models/rango-grpo-retry/adapter/adapter_model.safetensors ] && \
    evalr rango-grpo-retry "재샘플링 롤아웃(k=4) + outcome reward" || \
    say "★ retry 학습 실패"

  say "### 재샘플링 + PRM (풀스택)"
  python3 -m tactic_gen.grpo_train \
    --rollouts data/grpo_rollouts/retry.jsonl \
    --model_name deepseek-ai/deepseek-coder-1.3b-instruct \
    --init_adapter models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500 \
    --save_dir models/rango-grpo-retry-prm/adapter \
    --process --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
  [ -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && \
    evalr rango-grpo-retry-prm "재샘플링(k=4) × PRM 결합 — 풀스택" || \
    say "★ retry-prm 학습 실패"
else
  say "★ 재샘플링 롤아웃 수집 실패 — #4 건너뜀"
fi

say "===== SOTA 3종 + 재샘플링 완료 ====="
grep '■' "$LOG" | tee -a "$LOG"
