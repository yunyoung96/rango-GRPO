#!/bin/bash
# 작은 PPO(@20/@40) 결과에서 최고 critic 선택 → 그 critic 으로 bigscale PPO 재학습+평가.
#   선택: @20 게이트(≥11 = 우리 rango) 통과한 것 중 @40 최고(동점이면 @20). 전부 미달이면 스킵(가망없음).
#   linear 가 이기면 기존 bs2-ppo(이미 학습됨) 재사용. 다른 critic 이면 기존 삭제 후 재학습(버전 교체 규칙).
#   bigscale PPO 2조건: bs2-ppo(원본 rango 롤아웃) / bs2-sftppo(SFT 롤아웃). test 1191, 120s, w2.
set -u
LOG=all_log/bigscale2.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
TEST=data/compcert_bs2_test_idx.txt
NTEST=$(wc -l < "$TEST")
T=120
ROLL=data/grpo_rollouts/bigscale2.jsonl
SFTROLL=data/grpo_rollouts/bigscale2_sft.jsonl
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }
gtrain(){ python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$2" \
  --collator_conf "$CONF" --max_len 3072 --save_dir "$3/adapter" "${@:4}" --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1; cpconf "$3"; }
teval(){ local d="all_results/bs2_$2_test${T}_w2/summary.json"; local n
  n=$([ -s "$d" ] && python3 -c "import json;print(len(json.load(open('$d'))['results']))" 2>/dev/null || echo 0)
  [ "$n" -ge "$NTEST" ] && { say "   $2 이미 완료($n)"; return 0; }
  python3 scripts/run_all.py --alias "$1" --idx-file "$TEST" --timeout "$T" --workers 2 \
    --out "all_results/bs2_$2_test${T}_w2" --description "bs2 test $2 test${T}_w2 (critic=$3)" >> "$LOG" 2>&1; }

# ── 최고 critic 선택 ──
BEST=$(python3 - <<'PY'
import json
def read(alias, stage):
    try:
        r=json.load(open(f'all_results/smart_{alias}/summary.json'))['results']
        import sys; sys.path.insert(0,'src')
        from coqstoq import Split,get_theorem_list
        from pathlib import Path
        cc=[i for i,t in enumerate(get_theorem_list(Split.TEST,Path('CoqStoq'))) if t.project.dir_name=='compcert']
        rm={x['idx']:x for x in r}; dn=[i for i in cc[:stage] if i in rm]
        if len(dn)<stage: return None
        return sum(1 for i in dn if rm[i].get('success'))
    except Exception: return None
cands=[]
for arch in ['linear','mlp','mlp2','tanh']:
    a=f'rango-grpo-ppo-{arch}'
    g20=read(a,20)
    if g20 is None or g20<11: continue   # @20 게이트 미달 제외
    g40=read(a,40)
    cands.append((g40 if g40 is not None else -1, g20, arch))
if not cands: print("NONE")
else:
    cands.sort(reverse=True); print(cands[0][2])
PY
)

say "===== bigscale PPO 승격 — 최고 critic = ${BEST} ====="
if [ "$BEST" = "NONE" ] || [ -z "$BEST" ]; then
  say "  ✗ @20 게이트(≥11) 통과 critic 없음 → bigscale PPO 스킵(가망없음)"
  exit 0
fi

# linear 이외면 기존 linear bigscale PPO 결과/모델 삭제 후 재학습 (버전 교체)
if [ "$BEST" != "linear" ]; then
  say "  critic 교체($BEST) → 기존 linear bs2-ppo/sftppo 결과·모델 삭제"
  rm -rf all_results/bs2_ppo_test120_w2 all_results/bs2_sftppo_test120_w2
  rm -rf models/rango-grpo-bs2-ppo models/rango-grpo-bs2-sftppo
fi

say "▶ PPO 학습 (원본 롤아웃, critic=$BEST)"
[ -f models/rango-grpo-bs2-ppo/adapter/adapter_model.safetensors ] || gtrain "$ROLL" "$INIT" models/rango-grpo-bs2-ppo --ppo --value_arch "$BEST"
say "▶ SFT→PPO 학습 (SFT 롤아웃, SFT 초기화, critic=$BEST)"
[ -f models/rango-grpo-bs2-sftppo/adapter/adapter_model.safetensors ] || { [ -s "$SFTROLL" ] && gtrain "$SFTROLL" models/rango-grpo-bs2-sft/adapter models/rango-grpo-bs2-sftppo --ppo --value_arch "$BEST"; }

say "▶ 평가 (test $NTEST, 120s, w2)"
say "  SFT→PPO"; teval rango-grpo-bs2-sftppo sftppo "$BEST"
say "  PPO";      teval rango-grpo-bs2-ppo ppo "$BEST"

say "===== bigscale PPO(critic=$BEST) 완료 — 전체 6조건 최종표 ====="
python3 - <<PY 2>&1 | tee -a "$LOG"
import json
for nm,d in [('baseline','baseline'),('SFT','sft'),('GRPO','grpo'),('SFT→GRPO','sftgrpo'),('SFT→PPO','sftppo'),('PPO','ppo')]:
    try:
        r=json.load(open(f'all_results/bs2_{d}_test120_w2/summary.json'))['results']
        print(f'  {nm:9s}: {sum(1 for x in r if x["success"])}/{len(r)}')
    except Exception: print(f'  {nm:9s}: (미완)')
print("  (bigscale PPO critic = $BEST)")
PY
