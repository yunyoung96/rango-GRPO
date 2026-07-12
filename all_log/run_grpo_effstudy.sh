#!/bin/bash
# GRPO effectiveness study: E1 expert-iter / E2 dense / E3 curriculum / E4 scale.
# 각 실험 = rollout(train셋) → GRPO 학습 → 평가(eval 0-40). baseline=GRPO round-1(16/40).
cd /app/coq-modeling
export PYTHONPATH=src
CK="models/deepseek-bm25-proof-tfidf-proj-thm-prem-final"
BASE="deepseek-ai/deepseek-coder-1.3b-instruct"
CONF="$CK/training_conf.yaml"
LOG=all_log/grpo_effstudy.log
RO=data/grpo_rollouts/rollouts.jsonl
mkdir -p data/grpo_rollouts models
say(){ echo "[$(date -u '+%H:%M')] $*" >> $LOG; }

run_exp () {  # $1=이름 $2=rollout_alias $3=extra_rollout_args $4=init_adapter $5=eval_alias
  local name="$1" ralias="$2" rargs="$3" init="$4" ealias="$5"
  say "===== $name: rollout ($ralias $rargs) ====="
  rm -f $RO
  python3 scripts/run_all.py --alias "$ralias" --timeout 400 --workers 1 $rargs      --description "$name rollout" >> $LOG 2>&1
  local nsig=$(python3 -c "import json,torch;g=[json.loads(l) for l in open('$RO')];print(sum(1 for x in g if torch.tensor([a['reward'] for a in x['attempts']]).std()>1e-4))" 2>/dev/null)
  say "$name: 그룹 $(wc -l < $RO), 신호그룹 $nsig"
  cp "$RO" data/grpo_rollouts/${name}.jsonl
  say "===== $name: GRPO 학습 → models/$ealias/adapter ====="
  local initarg=""; [ -n "$init" ] && initarg="--init_adapter $init"
  python3 src/tactic_gen/grpo_train.py --rollouts $RO --model_name $BASE $initarg      --collator_conf $CONF --save_dir models/$ealias/adapter      --max_len 3072 --epochs 2 --lr 1e-6 --kl_beta 0.04 --micro_bsz 2 >> $LOG 2>&1
  cp $CK/training_conf.yaml models/$ealias/training_conf.yaml
  cp $CK/lm-example-conf.yaml models/$ealias/ 2>/dev/null
  say "===== $name: 평가 ($ealias @40) ====="
  python3 scripts/run_all.py --alias "$ealias" --num 40 --timeout 600 --workers 1      --description "$name eval" >> $LOG 2>&1
  local d=$(ls -dt all_results/*_$ealias 2>/dev/null | head -1)
  [ -z "$d" ] && d=$(ls -dt all_results/2026071*/ | head -1)
  local s=$(python3 -c "import json;dd=json.load(open('$d/summary.json'));print(dd.get('success'),'/',dd.get('total'))" 2>/dev/null)
  say "■ $name ($ealias): $s  -> $d"
}

say "########## GRPO effectiveness study 시작 ##########"
# E2 dense (base rango에서)
run_exp E2-dense      grpo-rollout-dense "--start 200 --num 40" "$CK/checkpoint-54500" rango-grpo-e2
# E3 curriculum (sibling-rich)
run_exp E3-curriculum grpo-rollout       "--idx-file data/grpo_curriculum/sibling_rich_train.txt --num 40" "$CK/checkpoint-54500" rango-grpo-e3
# E4 scale (G=16, 정리 60)
run_exp E4-scale      grpo-rollout-g16   "--start 200 --num 60" "$CK/checkpoint-54500" rango-grpo-e4
# E1 expert-iter (round-1 adapter에서 rollout + 이어서 학습)
run_exp E1-expiter    grpo-rollout-r2    "--start 200 --num 40" "models/rango-grpo/adapter" rango-grpo-e1
say "########## effectiveness study 완료 ##########"
