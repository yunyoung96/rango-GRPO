#!/bin/bash
# ★ LUFFY (2504.14945) @20→@40 — off-policy gold 주입으로 dead group 부활.
#
# 핵심: 정리마다 s_0 그룹(8개 π_old 샘플)에 **인간 gold 증명 궤적 1개**(재생·검증, r=1)를 섞는다.
#   dead group(전부 실패)이라도 gold 덕에 group mean≠0 → advantage 신호 생성.
#   학습(--luffy): gold 토큰은 clip 없이 shaping f(π_θ)=π_θ/(π_θ+γ) 로(낮은확률 정답토큰 증폭),
#                  on-policy row 는 표준 clipped GRPO. gold advantage 는 std-floor(폭발 방지).
#   재샘플링(k=4)도 함께: precision 실패를 줄이면서 gold 로 정답 방향을 준다.
#
# 비교기준 = 우리 rango(@20=11, @40=15) — published 비교 안 함. smart_eval 에스컬레이션(20 먼저).
# ※ 학습 후 training_conf/lm-example-conf 복사 필수(없으면 서버 로딩 hang).
set -u
LOG=all_log/luffy.log
WORKERS=${WORKERS:-2}
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
# ★ fix 위에서 이어 학습(expert-iteration): 초기화 = fix 어댑터(원본 rango 아님).
#   ref 모델도 init_adapter(=fix)라 KL 이 fix 로 당긴다. 롤아웃 정책도 fix(run_thm alias).
INIT=models/rango-grpo-fix/adapter
# collator_conf 는 SFT 포맷 고정값(어느 어댑터든 동일한 rango training_conf 사용).
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }

say "===== LUFFY @20→@40 시작 ====="

# ── 1. gold 궤적 빌드 (학습셋 cc[200:240], 전역 idx 376~443) ──────────
say "1) gold 궤적 빌드"
python3 scripts/build_gold_trajectories.py --project compcert --start 200 --num 40 >> "$LOG" 2>&1
[ -s data/curriculum/gold.json ] || { say "★ gold 빌드 실패 — 중단"; exit 1; }
say "   gold: $(python3 -c "import json;print(len(json.load(open('data/curriculum/gold.json'))))")개 정리"

# ── 2. 롤아웃 수집 (s_0 그룹 8시도 + gold 1개 주입, 재샘플링 k=4) ─────
say "2) 롤아웃 수집 (gold 주입, retry k=4)"
if [ ! -s data/grpo_rollouts/luffy.jsonl ]; then
  rm -f data/grpo_rollouts/luffy.jsonl
  python3 scripts/run_all.py --alias grpo-rollout-luffy --start 200 --num 40 \
    --timeout 900 --workers "$WORKERS" \
    --description "LUFFY 롤아웃(s0 + gold 주입, retry k=4)" >> "$LOG" 2>&1
fi
[ -s data/grpo_rollouts/luffy.jsonl ] || { say "★ 롤아웃 수집 실패 — 중단"; exit 1; }

say "3) ★ 효과 측정 — gold 가 dead group 을 얼마나 살렸나"
python3 - <<'PY' 2>&1 | tee -a "$LOG"
import json
g=[json.loads(l) for l in open('data/grpo_rollouts/luffy.jsonl')]
# gold 는 off_policy attempt. gold 제외한 on-policy 만으로 dead 판정 → gold 로 부활한 그룹 수.
n=len(g); goldok=0; dead_wo=0; revived=0
for x in g:
    on=[a for a in x['attempts'] if not a.get('off_policy')]
    gold=[a for a in x['attempts'] if a.get('off_policy')]
    has_gold = any(a['reward']>=1 for a in gold)
    dead = on and all(a['reward']<1 for a in on)
    goldok += 1 if has_gold else 0
    if dead: dead_wo += 1
    if dead and has_gold: revived += 1
print(f"  그룹 {n}개 | gold 주입성공 {goldok} | on-policy dead {dead_wo} | "
      f"★ gold 로 부활한 dead group {revived}/{dead_wo}")
print(f"  [기존 round-1: 혼합그룹(신호O) 11/41=27%. LUFFY 는 dead {dead_wo}개에 정답신호 주입]")
PY

# ── 4. 학습 (--luffy: gold=shaping, on-policy=표준 GRPO) ──────────────
say "4) 학습 (--luffy)"
[ ! -f models/rango-grpo-luffy/adapter/adapter_model.safetensors ] && \
  python3 -m tactic_gen.grpo_train \
    --rollouts data/grpo_rollouts/luffy.jsonl \
    --model_name "$BASE" --init_adapter "$INIT" \
    --collator_conf "$CONF" --max_len 3072 \
    --save_dir models/rango-grpo-luffy/adapter \
    --luffy --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-luffy/ 2>/dev/null

# ── 5. 평가 (smart_eval @20→@40, 우리 rango 대비) ────────────────────
say "5) 평가 (smart_eval @20→@40)"
[ -f models/rango-grpo-luffy/adapter/adapter_model.safetensors ] && seval rango-grpo-luffy || say "★ LUFFY 학습 실패"

say "===== LUFFY @20→@40 완료 ====="
grep -h "smart\] ■" "$LOG" | tail -4
