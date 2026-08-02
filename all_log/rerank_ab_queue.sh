#!/bin/bash
# 타입-지향 premise 재랭킹 A/B (inference-only, 학습 불필요).
#   같은 executor(subgoal)·같은 rand200·@300s w2. 유일차이 = RERANK_PREMISES 0(off) vs 1(on).
#   질문: 결론매칭 재랭킹(BM25 top-1 22%→36%)이 test 성공률로 전이되나(selection 개선).
#   tst1000tr5091 학습 완료 후 자동 실행(GPU 경합 방지).
cd /app/coq-modeling || exit 1
LOG=all_log/rerank_ab.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
EXEC=models/rango-grpo-subgoal-bs2/adapter
RAND=data/compcert_bs2_rand200_idx.txt
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'),'(',round(100*d.get('success',0)/max(d.get('done',1),1),1),'%)')" 2>/dev/null; }
wait_gpus(){ local need=${1:-14000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  local g=""; [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ]&&g="0"; [ "$f1" -ge "$need" ]&&g="${g:+$g,}1"
  [ -n "$g" ]&&{ echo "$g";return; }; [ $w -ge 7200 ]&&{ echo 1;return; }; sleep 30;w=$((w+30)); done; }

# ── 1) tst1000tr5091 학습 완료 대기 (GPU 경합 방지) ──
say "tst1000tr5091 학습 완료 대기 (TRAIN_DONE)..."
S=$SECONDS
while :; do
  grep -q 'tst1000tr5091_TRAIN_DONE' all_log/tst1000tr5091.log 2>/dev/null && break
  # 안전장치: 학습 프로세스 없고 최종모델 있으면 완료로 간주
  if ! pgrep -f 'grpo_train|run_all.py' >/dev/null && [ -f models/rango-tst1000tr5091-sftgrpo/adapter/adapter_model.safetensors ]; then break; fi
  sleep 120; [ $((SECONDS-S)) -ge 172800 ] && { say "대기 타임아웃(48h) — 그래도 진행"; break; }
done
say "→ 재랭킹 A/B 시작"
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 5

# ── 2) Arm A: baseline (RERANK off) ──
if [ ! -s all_results/rerank_base/summary.json ]; then
  GPUS=$(wait_gpus 14000); say "Arm A baseline (RERANK off, GPU $GPUS)"
  HF_HUB_OFFLINE=1 EXEC_ADAPTER=$EXEC RERANK_PREMISES=0 \
    python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" --timeout 300 --gpus "$GPUS" --workers 2 \
    --out all_results/rerank_base --description "rerank A/B baseline (off)" >> "$LOG" 2>&1
  pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 3
fi
say "  Arm A: $(sumline all_results/rerank_base)"

# ── 3) Arm B: treatment (RERANK on) ──
if [ ! -s all_results/rerank_on/summary.json ]; then
  GPUS=$(wait_gpus 14000); say "Arm B treatment (RERANK on, GPU $GPUS)"
  HF_HUB_OFFLINE=1 EXEC_ADAPTER=$EXEC RERANK_PREMISES=1 \
    python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" --timeout 300 --gpus "$GPUS" --workers 2 \
    --out all_results/rerank_on --description "rerank A/B treatment (on)" >> "$LOG" 2>&1
  pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 3
fi
say "  Arm B: $(sumline all_results/rerank_on)"

# ── 4) 비교(겹침) ──
python3 - >> "$LOG" 2>&1 <<'PY'
import json,os
def solved(p):
    f=p+'/summary.json'
    if not os.path.exists(f): return None
    d=json.load(open(f)); return set(r['idx'] for r in d['results'] if r.get('success'))
A=solved('all_results/rerank_base'); B=solved('all_results/rerank_on')
if A is not None and B is not None:
    print(f"[재랭킹 A/B] off {len(A)}/200 vs on {len(B)}/200 | on-only {len(B-A)} off-only {len(A-B)} 공통 {len(A&B)}")
    print(f"  순효과 {len(B)-len(A):+d}정리 ({100*(len(B)-len(A))/200:+.1f}pp)")
PY
say "=== RERANK_AB_DONE ==="
