#!/bin/bash
# ★ cross-repo GRPO (§10 P6) — 지금까지 짚어온 가장 큰 레버.
#
# 문제: rango-grpo 는 CompCert 40개(cc[200:240])로만 학습 → 73%가 dead group(신호 0).
#   게다가 평가도 CompCert라 39%가 같은 파일(sibling confound).
# 해결: non-CompCert repo(fourcolor/math-classes/buchberger/reglang/poltac/huffman)로 학습.
#   신호량↑ + 평가(CompCert)와 파일 겹침 0.
#
# 모든 버그 수정 반영: instruct 베이스 + 재샘플링(k=4) + PRM + length 보정.
# 비교축: published rango 53 · 우리 rango 61 · rango-grpo 60(same-project).
#   → cross 가 61 을 넘거나, 최소한 union 기여가 same-project 보다 큰지가 시험.
set -u
LOG=all_log/crossrepo_grpo.log
WORKERS=${WORKERS:-2}
IDX=data/crossrepo/train_idx.txt
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
evalr(){
  say "----- eval: $1 @40 -----"
  python3 scripts/run_all.py --alias "$1" --num 40 --timeout 600 --workers "$WORKERS" \
    --description "$2" >> "$LOG" 2>&1
  d=$(ls -dt all_results/*_"$1" 2>/dev/null | head -1)
  python3 - "$1" "$d" <<'PY' 2>&1 | tee -a "$LOG"
import json,sys,math
a,d=sys.argv[1],sys.argv[2]
r=json.load(open(f"{d}/summary.json"))["results"]
s=sum(1 for x in r if x.get("success")); o=sum(1 for x in r if x.get("original_success"))
g=[x['idx'] for x in r if x.get('success') and not x.get('original_success')]
c=[x['idx'] for x in r if x.get('original_success') and not x.get('success')]
b,cc=len(g),len(c);n=b+cc
p=min(2*sum(math.comb(n,k) for k in range(0,min(b,cc)+1))/2**n,1.0) if n else 1.0
print(f"■ {a}: {s}/40 | published {o} | net {s-o:+d} | gain {b} 회귀 {cc} {c} | McNemar p={p:.4f}")
PY
}

say "===== cross-repo GRPO 시작 ====="
[ -s "$IDX" ] || { say "★ $IDX 없음 — build_crossrepo_idx.py 먼저 실행"; exit 1; }
say "학습 대상: $(wc -l < $IDX)개 정리 (non-CompCert)"

# ── 1. cross-repo 롤아웃 수집 ────────────────────────────────────────
say "▶ 1/3  cross-repo 롤아웃 수집 (재샘플링 k=4)"
rm -f data/grpo_rollouts/cross.jsonl
python3 scripts/run_all.py --alias grpo-rollout-cross --idx-file "$IDX" \
  --timeout 600 --workers "$WORKERS" \
  --description "cross-repo rollout (non-CompCert, k=4 재샘플링)" >> "$LOG" 2>&1
if [ -s data/grpo_rollouts/cross.jsonl ]; then
  python3 - <<'PY' 2>&1 | tee -a "$LOG"
import json
g=[json.loads(l) for l in open('data/grpo_rollouts/cross.jsonl')]
att=[a for x in g for a in x['attempts']]
su=sum(1 for a in att if a['reward']>=1.0)
dead=sum(1 for x in g if all(a['reward']<1 for a in x['attempts']))
allw=sum(1 for x in g if all(a['reward']>=1 for a in x['attempts']))
print(f"  롤아웃: 그룹 {len(g)} | 시도성공 {su}/{len(att)} ({su/len(att):.1%})")
print(f"          dead {dead} 전부성공 {allw} → 신호있는 그룹 {len(g)-dead-allw} ({(len(g)-dead-allw)/len(g):.0%})")
print(f"  ※ CompCert same-project 는 신호그룹 27%뿐이었다. 이보다 높으면 cross 가 유리.")
PY
else
  say "★ cross 롤아웃 수집 실패 — 종료"; exit 1
fi

# ── 2. 학습 (outcome only / +PRM) ────────────────────────────────────
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
say "▶ 2/3  cross-repo GRPO 학습"
python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/cross.jsonl \
  --model_name "$BASE" --init_adapter "$INIT" \
  --save_dir models/rango-grpo-cross/adapter \
  --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
say "▶ 2b  cross-repo GRPO + PRM 학습"
python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/cross.jsonl \
  --model_name "$BASE" --init_adapter "$INIT" \
  --save_dir models/rango-grpo-cross-prm/adapter \
  --process --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1

# ── 3. 평가 (CompCert @40) ───────────────────────────────────────────
say "▶ 3/3  평가 (CompCert @40, sibling 누출 0)"
[ -f models/rango-grpo-cross/adapter/adapter_model.safetensors ] && \
  evalr rango-grpo-cross "cross-repo GRPO (다른 repo 학습, CompCert 평가)" || say "★ cross 학습 실패"
[ -f models/rango-grpo-cross-prm/adapter/adapter_model.safetensors ] && \
  evalr rango-grpo-cross-prm "cross-repo GRPO + PRM" || say "★ cross-prm 학습 실패"

say "===== cross-repo GRPO 완료 ====="
grep '■' "$LOG"
