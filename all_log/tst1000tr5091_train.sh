#!/bin/bash
# tst1000tr5091 실험 (train만, eval 없음). CompCert 6091 → test 앞1000 / train 나머지5091.
#   방법 = bigscale2와 동일(rango baseline → gold SFT → SFT 롤아웃 → GRPO = 4b SFT→GRPO). split만 tst1000tr5091.
#   산출: models/rango-tst1000tr5091-sft, models/rango-tst1000tr5091-sftgrpo.
cd /app/coq-modeling || exit 1
TAG=tst1000tr5091
LOG=all_log/${TAG}.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500   # ★ rango baseline
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
TRAIN=data/compcert_${TAG}_train_idx.txt        # 5091 (gold SFT 대상)
GOLDCUR=data/curriculum/gold_${TAG}.json        # gold 커리큘럼 4298정리
GOLD=data/grpo_rollouts/${TAG}_gold.jsonl       # SFT 데이터
SFTROLL=data/grpo_rollouts/${TAG}_sftroll.jsonl # SFT→GRPO 롤아웃
SFTM=models/rango-${TAG}-sft
FINM=models/rango-${TAG}-sftgrpo
ROLLTO=300                                     # GRPO 롤아웃 정리당 timeout(초). 전체 5091 → @300s.
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
wait_gpus(){ local need=${1:-13000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  local g=""; [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ]&&g="0"; [ "$f1" -ge "$need" ]&&g="${g:+$g,}1"
  [ -n "$g" ]&&{ echo "$g";return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 30;w=$((w+30)); done; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }
gtrain(){ python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$2" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$3/adapter" "${@:4}" --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1; cpconf "$3"; }
rollf(){ pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; }

# ── ★ smoke: gold replay 20정리 (새 커리큘럼·env override 검증) ──
say "smoke: gold replay 20정리 (gold_${TAG} 커리큘럼 동작?)"
head -20 "$TRAIN" > /tmp/${TAG}_smoke_idx.txt
G=$(wait_gpus 13000)
GOLD_FILE=$GOLDCUR ROLLOUT_OUT=/tmp/${TAG}_gold_smoke.jsonl \
  python3 scripts/run_all.py --alias grpo-rollout-goldsft --idx-file /tmp/${TAG}_smoke_idx.txt --timeout 300 --gpus "$G" --workers 2 >> "$LOG" 2>&1
rollf; sleep 3
SMOKE=$([ -s /tmp/${TAG}_gold_smoke.jsonl ] && wc -l < /tmp/${TAG}_gold_smoke.jsonl || echo 0)
say "smoke gold 그룹: $SMOKE"
if [ "$SMOKE" -lt 1 ]; then say "★smoke 실패 — gold replay 0. 중단(수동확인)."; exit 1; fi

# ── 1) gold-SFT 데이터 (rango로 gold replay, 5091 train / gold 4298) ──
say "▶1 gold-SFT 데이터 (gold replay, w4)"
if [ ! -s "$GOLD" ]; then
  G=$(wait_gpus 13000); say "  gold replay GPU:$G"
  GOLD_FILE=$GOLDCUR ROLLOUT_OUT=$GOLD \
    python3 scripts/run_all.py --alias grpo-rollout-goldsft --idx-file "$TRAIN" --timeout 600 --gpus "$G" --workers 4 >> "$LOG" 2>&1
  rollf; sleep 3
fi
say "  gold 데이터: $([ -s "$GOLD" ] && wc -l < "$GOLD" || echo 0) 그룹"
[ -s "$GOLD" ] || { say "gold 데이터 없음 — 중단"; exit 1; }

# ── 2) SFT 학습 (rango baseline 위 + gold, kl0, lr1e-6 ep2) ──
say "▶2 SFT 학습 (init=rango baseline, --sft kl0)"
[ -f "$SFTM/adapter/adapter_model.safetensors" ] || gtrain "$GOLD" "$INIT" "$SFTM" --sft --kl_beta 0.0
say "  SFT: $([ -f "$SFTM/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)"
[ -f "$SFTM/adapter/adapter_model.safetensors" ] || { say "SFT 실패 — 중단"; exit 1; }

# ── 3) SFT 모델 on-policy 롤아웃 (GRPO 데이터, 전체 5091 @300s) ──
say "▶3 SFT 롤아웃 (5091 전부, @${ROLLTO}s, w4, opener 없음)"
if [ ! -s "$SFTROLL" ]; then
  G=$(wait_gpus 13000); say "  롤아웃 GPU:$G"
  EXEC_ADAPTER=$SFTM/adapter ROLLOUT_OUT=$SFTROLL ROLLOUT_RETRY=1 \
    python3 scripts/run_all.py --alias grpo-rollout-pf --idx-file "$TRAIN" --timeout "$ROLLTO" --gpus "$G" --workers 4 >> "$LOG" 2>&1
  rollf; sleep 3
fi
say "  SFT 롤아웃: $([ -s "$SFTROLL" ] && wc -l < "$SFTROLL" || echo 0) 그룹"
[ -s "$SFTROLL" ] || { say "롤아웃 없음 — 중단"; exit 1; }

# ── 4) SFT→GRPO 학습 (init=SFT, kl0.04, lr1e-6 ep2) ──
say "▶4 SFT→GRPO 학습 (init=SFT, kl0.04)"
[ -f "$FINM/adapter/adapter_model.safetensors" ] || gtrain "$SFTROLL" "$SFTM/adapter" "$FINM" --kl_beta 0.04
say "  SFT→GRPO: $([ -f "$FINM/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)"

say "=== ${TAG}_TRAIN_DONE (eval 없음. 모델: $SFTM, $FINM) ==="
