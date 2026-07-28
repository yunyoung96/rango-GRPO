#!/bin/bash
# ★ fixdyn @40 완료 → 오염된 15·27·29 재평가(CPU 경합 없이) → fix@180(rango-grpo-fix robustness)
#   → 그 뒤 기존 큐(vine → KL-LUFFY → revcurr → adaptprefix → bread → backward-prm → retry-prm).
set -u
LOG=all_log/chain_reeval_master.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT_FIX=models/rango-grpo-fix/adapter
INIT_ORIG=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
say(){ echo "[$(date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
seval(){ python3 scripts/smart_eval.py --alias "$1" --stages 20,40 2>&1 | tee -a "$LOG" | grep -E "smart\] ■|smart\] ✗|smart\] ✓"; }
roll(){ [ -s "$2" ] && return 0; rm -f "$2"; python3 scripts/run_all.py --alias "$1" --start 200 --num 40 --timeout "$3" --workers 2 --description "$1" >> "$LOG" 2>&1; [ -s "$2" ]; }
trainf(){ python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$INIT_FIX" --collator_conf "$CONF" --max_len 3072 --save_dir "$2" --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 "${@:3}" >> "$LOG" 2>&1; cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$(dirname "$2")/" 2>/dev/null; }

say "대기: fixdyn @40 완료까지"
while ! grep -q "smart\] ■ rango-grpo-fixdyn @40" all_log/chain_onpolicy.log 2>/dev/null; do sleep 60; done
say "fixdyn @40 완료 감지 → 기존 체인 선점(vine/gold 뒤로 미룸)"
kill 946403 963056 2>/dev/null
pkill -f "run_all.py --alias grpo-rollout-vine" 2>/dev/null
pkill -f "run_thm.py run grpo-rollout-vine" 2>/dev/null
pkill -f "bash all_log/run_vine.sh" 2>/dev/null
sleep 12

# ── 1. 오염 3개 재평가 (summary 에서 제거 → run_all resume 이 그 3개만 다시) ──
say "▶ 1/9  오염 재평가: idx 15·27·29 (CPU 경합 없이 단독)"
python3 - <<'PY' 2>&1 | tee -a "$LOG"
import json
p="all_results/smart_rango-grpo-fixdyn/summary.json"
d=json.load(open(p)); before=len(d["results"])
d["results"]=[r for r in d["results"] if r["idx"] not in (15,27,29)]
d["done"]=len(d["results"])
json.dump(d,open(p,"w"))
import os
for i in (15,27,29):
    f=f"all_results/smart_rango-grpo-fixdyn/logs/{i}.txt"
    if os.path.exists(f): os.remove(f)
print(f"  summary 에서 3개 제거({before}→{len(d['results'])}), run_all resume 이 재실행")
PY
python3 scripts/run_all.py --alias rango-grpo-fixdyn --num 40 --timeout 600 --workers 2 \
  --out all_results/smart_rango-grpo-fixdyn --description "reeval 15/27/29" >> "$LOG" 2>&1
say "◀ 재평가 완료 — 15/27/29 결과:"
python3 - <<'PY' 2>&1 | tee -a "$LOG"
import json
r={x['idx']:x for x in json.load(open('all_results/smart_rango-grpo-fixdyn/summary.json'))['results']}
for i in (15,27,29):
    x=r.get(i,{}); print(f"    idx{i}: success={x.get('success')} {x.get('elapsed_sec','?')}s")
import sys; sys.path.insert(0,'src')
from coqstoq import Split, get_theorem_list; from pathlib import Path
cc=[i for i,t in enumerate(get_theorem_list(Split.TEST, Path('CoqStoq'))) if t.project.dir_name=='compcert']
for n,b in ((20,11),(40,15)):
    dn=[i for i in cc[:n] if i in r]; su=sum(1 for i in dn if r[i].get('success'))
    print(f"  ★ fixdyn @{n} (재평가 후): {su}/{len(dn)}  vs 우리rango{b} {su-b:+d}")
PY

# ── 2. fix@180 (rango-grpo-fix robustness) ──
say "▶ 2/9  fix@180 (rango-grpo-fix robustness, 우리rango 61 기준)"
python3 scripts/smart_eval.py --alias rango-grpo-fix --stages 180 2>&1 | tee -a "$LOG" | grep -E "smart\] ■"

# ── 3. 나머지 큐 ──
say "▶ 3/9  VinePPO"; bash all_log/run_vine.sh
say "▶ 4/9  KL-LUFFY"; bash all_log/run_luffy_kl.sh
say "▶ 5/9  revcurr"; bash all_log/run_revcurr.sh
say "▶ 6/9  adaptprefix"
if roll grpo-rollout-adaptprefix data/grpo_rollouts/adaptprefix.jsonl 900; then
  [ ! -f models/rango-grpo-adaptprefix/adapter/adapter_model.safetensors ] && trainf data/grpo_rollouts/adaptprefix.jsonl models/rango-grpo-adaptprefix/adapter
  seval rango-grpo-adaptprefix; fi
say "▶ 7/9  bread"
if roll grpo-rollout-bread data/grpo_rollouts/bread.jsonl 900; then
  [ ! -f models/rango-grpo-bread/adapter/adapter_model.safetensors ] && trainf data/grpo_rollouts/bread.jsonl models/rango-grpo-bread/adapter --luffy
  seval rango-grpo-bread; fi
say "▶ 8/9  backward-prm"; [ -f models/rango-grpo-backward-prm/adapter/adapter_model.safetensors ] && seval rango-grpo-backward-prm
say "▶ 9/9  retry-prm"
if [ ! -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && [ -s data/grpo_rollouts/retry.jsonl ]; then
  python3 -m tactic_gen.grpo_train --rollouts data/grpo_rollouts/retry.jsonl --model_name "$BASE" --init_adapter "$INIT_ORIG" --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-grpo-retry-prm/adapter --process --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> "$LOG" 2>&1
  cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml models/rango-grpo-retry-prm/ 2>/dev/null; fi
[ -f models/rango-grpo-retry-prm/adapter/adapter_model.safetensors ] && seval rango-grpo-retry-prm
say "===== 전체 완료 ====="
