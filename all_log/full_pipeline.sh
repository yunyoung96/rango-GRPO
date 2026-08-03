#!/bin/bash
# FULL PIPELINE (사용자 확정: gold-SFT 시작, opener 매 분기).
#   executor/init(1.3B) = gold-SFT(rango-grpo-bs2-sft). opener = opener-7b-sub(정리+subgoal 여는).
#   Stage A: 300 theorem s0 롤아웃 + opener 매 분기(PLANNER_EVERY) → GRPO 데이터
#   Stage B: GRPO(init=gold-SFT) → models/rango-opener-sub-grpo
#   Stage C: rand200@300s — 최종+opener vs π₀(anchor)
# GPU1 전용. 각 단계 resumable.
cd /app/coq-modeling || exit 1
LOG=all_log/full_pipeline.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
QWEN=Qwen/Qwen2.5-Coder-7B-Instruct
GOLD=models/rango-grpo-bs2-sft/adapter
OPENER=models/opener-7b-sub/adapter
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
FINAL=models/rango-opener-sub-grpo
TRAIN=data/compcert_bs2_train_idx.txt
RAND=data/compcert_bs2_rand200_idx.txt
ROLL=data/grpo_rollouts/opener_sub_pipe.jsonl
PORT=8130; URL=http://127.0.0.1:$PORT
SRVLOG=all_log/opener_server_fp.log
start_srv(){ pkill -9 -f 'planner_server.py' 2>/dev/null; sleep 3; : > "$SRVLOG"
  HF_HUB_OFFLINE=1 PLANNER_ADAPTER=$OPENER PLANNER_OPENER=1 \
    CUDA_VISIBLE_DEVICES=1 python3 src/model_deployment/planner_server.py "$QWEN" "$PORT" >> "$SRVLOG" 2>&1 &
  SRV=$!; for i in $(seq 1 90); do grep -q READY "$SRVLOG" 2>/dev/null && break; sleep 5; done
  grep -q READY "$SRVLOG" 2>/dev/null && say "  opener 서버 READY(pid $SRV)" || say "  ✗ opener 서버 기동 실패"; }
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'),'/',d.get('total'))" 2>/dev/null; }

say "=== FULL PIPELINE 시작 (gold-SFT 시작, opener-7b-sub 매 분기) ==="

# ── Stage A: 100 theorem s0 롤아웃 + opener 매 분기 (밤새 완주 위해 300→100 축소; 분당 0.6그룹) ──
ROLL_IDX=/tmp/roll100_idx.txt
if [ ! -s "$ROLL" ]; then
  say "=== Stage A: 롤아웃 (100 theorem s0, opener 매 분기=PLANNER_EVERY, executor=gold-SFT, w4) ==="
  start_srv
  HF_HUB_OFFLINE=1 EXEC_ADAPTER=$GOLD PLANNER_FIRST_URL=$URL PLANNER_EVERY=1 ROLLOUT_OUT=$ROLL ROLLOUT_RETRY=1 \
    CUDA_VISIBLE_DEVICES=1 python3 scripts/run_all.py --alias grpo-rollout-pf --idx-file "$ROLL_IDX" --timeout 400 --gpus 1 --workers 4 >> "$LOG" 2>&1
  kill -9 "$SRV" 2>/dev/null; pkill -9 -f 'planner_server.py' 2>/dev/null; sleep 5
  say "Stage A 완료. 롤아웃 그룹수: $(python3 -c "print(sum(1 for _ in open('$ROLL')))" 2>/dev/null || echo 0)"
else say "=== Stage A: $ROLL 이미 있음 — 스킵 ==="; fi

# ── Stage B: GRPO 학습(init=gold-SFT) ──
if [ ! -f "$FINAL/adapter/adapter_model.safetensors" ]; then
  if [ -s "$ROLL" ]; then
    say "=== Stage B: GRPO 학습 (init=gold-SFT → $FINAL) ==="
    HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=1 python3 -m tactic_gen.grpo_train \
      --rollouts "$ROLL" --model_name "$BASE" --init_adapter "$GOLD" --collator_conf "$CONF" \
      --max_len 3072 --save_dir "$FINAL/adapter" --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
    cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$FINAL/" 2>/dev/null
    say "Stage B 완료: $([ -f "$FINAL/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)"
  else say "=== Stage B 스킵: 롤아웃 데이터 없음 ==="; fi
else say "=== Stage B: $FINAL 이미 있음 — 스킵 ==="; fi

# ── Stage C: rand200@300s test (최종+opener 먼저=headline, 그다음 gold-SFT anchor) ──
if [ -f "$FINAL/adapter/adapter_model.safetensors" ]; then
  say "=== Stage C: rand200@300s test ==="
  # C1: 최종+opener (headline — 먼저 완주 보장)
  if [ ! -s all_results/osg_final_opener/summary.json ]; then
    start_srv
    HF_HUB_OFFLINE=1 EXEC_ADAPTER=$FINAL/adapter PLANNER_URL=$URL CUDA_VISIBLE_DEVICES=1 \
      python3 scripts/run_all.py --alias rango-planner --idx-file "$RAND" --timeout 300 --gpus 1 --workers 2 \
      --out all_results/osg_final_opener --description "osg final + opener-sub" >> "$LOG" 2>&1
    kill -9 "$SRV" 2>/dev/null; pkill -9 -f 'planner_server.py' 2>/dev/null; sleep 5
  fi
  say "  최종+opener rand200: $(sumline all_results/osg_final_opener)"
  # C2: gold-SFT anchor (init baseline, opener 없이) — best-effort
  [ -s all_results/osg_goldsft/summary.json ] || HF_HUB_OFFLINE=1 EXEC_ADAPTER=$GOLD CUDA_VISIBLE_DEVICES=1 \
    python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" --timeout 300 --gpus 1 --workers 8 \
    --out all_results/osg_goldsft --description "osg gold-SFT anchor" >> "$LOG" 2>&1
  say "  gold-SFT anchor rand200: $(sumline all_results/osg_goldsft)"
else say "=== Stage C 스킵: 최종 모델 없음 ==="; fi

say "=== FULL PIPELINE 완료 FP_DONE ==="
python3 - >> "$LOG" 2>&1 <<'PY'
import json,os
def g(p):
    p=f'all_results/{p}/summary.json'
    if os.path.exists(p): d=json.load(open(p));return f"{d.get('success')}/{d.get('done')}/{d.get('total')}"
    return "(없음)"
print("\n===== 최종 (rand200@300s, success/done/total) =====")
print("  최종 gold-SFT→opener-sub-GRPO +opener :",g('osg_final_opener'))
print("  gold-SFT (init anchor, opener없이)   :",g('osg_goldsft'))
print("  (참고 known: SFT 33.5%, π₀ SFT→GRPO 37.5% @rand200)")
PY
