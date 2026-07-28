#!/bin/bash
# bigscale 완전판 (6조건): compcert 앞1500 중 300-train(전역2102~2615) / test(statement-disjoint).
# 조건: baseline / SFT(gold) / GRPO / SFT→GRPO / PPO / SFT→PPO.
#   → GRPO계열 vs PPO계열 × SFT유무 완전대조. PPO=actor-critic(학습 V(s) baseline, dead group도 −V 신호).
# ★ train(롤아웃) w2/600s, test w2/timeout 120s (이름 test120_w2 명시 — 시간 명확화).
# 전부 checkpoint-54500 초기화 + instruct 베이스(fix). 버그수정판(NaN guard/dropout off/append flock/누출제거).
set -u
LOG=all_log/bigscale2.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
TEST=data/compcert_bs2_test_idx.txt
TRAIN=data/compcert_bs2_train_idx.txt
NTEST=$(wc -l < "$TEST")
T=120                                           # ★ test timeout(초)
ROLL=data/grpo_rollouts/bigscale2.jsonl         # GRPO/PPO (원본 rango 롤아웃)
GOLD=data/grpo_rollouts/goldsft_bs2.jsonl       # SFT (gold 참조증명)
SFTROLL=data/grpo_rollouts/bigscale2_sft.jsonl  # SFT→GRPO/PPO (SFT 모델 on-policy 롤아웃)
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }
# ★ 평가 out 이름에 _t${T}(=t120) → 로그·디렉토리에 timeout 명시. 완성도체크(부분→완성 오인 방지).
teval(){ local d="all_results/bs2_$2_test${T}_w2/summary.json"; local n
  n=$([ -s "$d" ] && python3 -c "import json;print(len(json.load(open('$d'))['results']))" 2>/dev/null || echo 0)
  [ "$n" -ge "$NTEST" ] && { say "   $2 이미 완료($n)"; return 0; }
  python3 scripts/run_all.py --alias "$1" --idx-file "$TEST" --timeout "$T" --workers 2 --out "all_results/bs2_$2_test${T}_w2" --description "bs2 test $2 test${T}_w2" >> "$LOG" 2>&1; }
gtrain(){ python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$2" --collator_conf "$CONF" --max_len 3072 --save_dir "$3/adapter" "${@:4}" --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1; cpconf "$3"; }

say "===== bigscale 완전판(6조건) — train(롤아웃)w2/600s / test w2/${T}s(test${T}_w2) / test $NTEST ====="

say "▶ 1 GRPO 롤아웃(원본 rango,300,w2,600s)"; [ -s "$ROLL" ] || python3 scripts/run_all.py --alias grpo-rollout-bigscale2 --idx-file "$TRAIN" --timeout 600 --workers 2 --description "bs2 GRPO rollout" >> "$LOG" 2>&1
say "▶ 2 gold-SFT 데이터(gold replay,300,w2,600s)"; [ -s "$GOLD" ] || python3 scripts/run_all.py --alias grpo-rollout-goldsft --idx-file "$TRAIN" --timeout 600 --workers 2 --description "bs2 gold-SFT" >> "$LOG" 2>&1

say "▶ 3 SFT 학습(gold, kl0)"
[ -f models/rango-grpo-bs2-sft/adapter/adapter_model.safetensors ] || gtrain "$GOLD" "$INIT" models/rango-grpo-bs2-sft --sft --kl_beta 0.0

say "▶ 4 SFT 모델 on-policy 재롤아웃(300,w2,600s)"; [ -s "$SFTROLL" ] || python3 scripts/run_all.py --alias grpo-rollout-bs2sft --idx-file "$TRAIN" --timeout 600 --workers 2 --description "bs2 SFT rollout" >> "$LOG" 2>&1

say "▶ 5 GRPO 학습(원본 롤아웃, kl0.04)"
[ -f models/rango-grpo-bigscale2/adapter/adapter_model.safetensors ] || gtrain "$ROLL" "$INIT" models/rango-grpo-bigscale2 --kl_beta 0.04
say "▶ 6 SFT→GRPO 학습(SFT 롤아웃, SFT 초기화, kl0.04)"
[ -f models/rango-grpo-bs2-sftgrpo/adapter/adapter_model.safetensors ] || { [ -s "$SFTROLL" ] && gtrain "$SFTROLL" models/rango-grpo-bs2-sft/adapter models/rango-grpo-bs2-sftgrpo --kl_beta 0.04; }
say "▶ 7 PPO 학습(원본 롤아웃, critic, checkpoint 초기화)"
[ -f models/rango-grpo-bs2-ppo/adapter/adapter_model.safetensors ] || gtrain "$ROLL" "$INIT" models/rango-grpo-bs2-ppo --ppo
say "▶ 8 SFT→PPO 학습(SFT 롤아웃, critic, SFT 초기화)"
[ -f models/rango-grpo-bs2-sftppo/adapter/adapter_model.safetensors ] || { [ -s "$SFTROLL" ] && gtrain "$SFTROLL" models/rango-grpo-bs2-sft/adapter models/rango-grpo-bs2-sftppo --ppo; }

say "▶ 9 평가 (test $NTEST, timeout ${T}s, w2)"
say "  baseline"; teval rango baseline
say "  SFT";      teval rango-grpo-bs2-sft sft
say "  GRPO";     teval rango-grpo-bigscale2 grpo
say "  SFT→GRPO"; teval rango-grpo-bs2-sftgrpo sftgrpo
# ★ SFT→PPO/PPO는 최후순위로 분리 → all_log/run_ppo_evals.sh (큐 맨 뒤)
# say "  SFT→PPO";  teval rango-grpo-bs2-sftppo sftppo
# say "  PPO";      teval rango-grpo-bs2-ppo ppo

say "===== bigscale 완전판 완료 — 결과 (test $NTEST, t${T}) ====="
python3 - <<PY 2>&1 | tee -a "$LOG"
import json
N=$NTEST; T=$T
print(f"  방법                 solved/{N} (timeout {T}s)")
for name,d in [('baseline(원본rango)','baseline'),('SFT(gold)','sft'),('GRPO','grpo'),('SFT→GRPO','sftgrpo'),('PPO','ppo'),('SFT→PPO','sftppo')]:
    try:
        r=json.load(open(f'all_results/bs2_{d}_test{T}_w2/summary.json'))['results']
        print(f'  {name:19s}: {sum(1 for x in r if x["success"])}/{len(r)}')
    except Exception: print(f'  {name:19s}: (미완)')
PY
