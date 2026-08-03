#!/bin/bash
# stage3(SFT 롤아웃)를 w8로 병렬 실행 — SFT 완료 감지 후 이어받기.
#   이유: tst1000tr5091_train.sh를 실행중 편집하면 bash 오프셋 깨질 위험 → stage3만 별도로 안전하게.
#   SFT모델 완성 대기 → 기존 스크립트의 stage3 진입 전에 롤아웃을 w8로 선점 실행(같은 출력파일).
#   이후 stage4 GRPO도 이어서.
cd /app/coq-modeling || exit 1
TAG=tst1000tr5091
LOG=all_log/tst1000tr5091.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
INIT=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-54500
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
TRAIN=data/compcert_${TAG}_train_idx.txt
SFTM=models/rango-${TAG}-sft
FINM=models/rango-${TAG}-sftgrpo
SFTROLL=data/grpo_rollouts/${TAG}_sftroll.jsonl
ROLLTO=300
ROLLW=8
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
wait_gpus(){ local need=${1:-13000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  local g=""; [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ]&&g="0"; [ "$f1" -ge "$need" ]&&g="${g:+$g,}1"
  [ -n "$g" ]&&{ echo "$g";return; }; [ $w -ge 7200 ]&&{ echo 1;return; }; sleep 30;w=$((w+30)); done; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }

# ── 1) SFT 완료 대기 (stage2 끝나면 stage3 선점) ──
say "[w8이어받기] SFT 완료 대기 → stage3 롤아웃 w8 선점"
S=$SECONDS
while :; do
  [ -f "$SFTM/adapter/adapter_model.safetensors" ] && break
  sleep 60; [ $((SECONDS-S)) -ge 21600 ] && { say "[w8] SFT대기 타임아웃6h"; break; }
done
[ -f "$SFTM/adapter/adapter_model.safetensors" ] || { say "[w8] SFT 없음 — 중단"; exit 1; }
say "[w8] SFT 완성 감지 → 원 스크립트 stage3(w4) 진입 막고 w8로."

# ── 2) 원 스크립트가 stage3 롤아웃을 이미 띄웠으면 죽이고 w8로 재시작 ──
sleep 10   # 원 스크립트가 stage3 시작할 틈
if pgrep -f 'run_all.py --alias grpo-rollout-pf' >/dev/null; then
  say "[w8] 원 스크립트 stage3(w4) 감지 → 중단하고 w8로 교체"
  pkill -9 -f 'run_all.py --alias grpo-rollout-pf' 2>/dev/null
  pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 5
  rm -f "$SFTROLL"   # 부분 결과 제거(깨끗이 w8로)
fi

# ── 3) stage3 롤아웃 w8 ──
if [ ! -s "$SFTROLL" ]; then
  G=$(wait_gpus 13000)
  NP=$(echo "$G" | awk -F, '{print NF}')
  say "[w8] ▶3 SFT 롤아웃 (5091, @${ROLLTO}s, GPU$G ×w${ROLLW} = $((NP*ROLLW))병렬)"
  EXEC_ADAPTER=$SFTM/adapter ROLLOUT_OUT=$SFTROLL ROLLOUT_RETRY=1 \
    python3 scripts/run_all.py --alias grpo-rollout-pf --idx-file "$TRAIN" --timeout "$ROLLTO" --gpus "$G" --workers "$ROLLW" >> "$LOG" 2>&1
  pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 3
fi
say "[w8] SFT 롤아웃 완료: $([ -s "$SFTROLL" ] && wc -l < "$SFTROLL" || echo 0) 그룹"
[ -s "$SFTROLL" ] || { say "[w8] 롤아웃 실패"; exit 1; }

# ── 4) stage4 GRPO (원 스크립트가 이미 했으면 건너뜀) ──
if [ ! -f "$FINM/adapter/adapter_model.safetensors" ]; then
  G=$(wait_gpus 24000); say "[w8] ▶4 SFT→GRPO (init=SFT, kl0.04, GPU$G)"
  python3 -m tactic_gen.grpo_train --rollouts "$SFTROLL" --model_name "$BASE" --init_adapter "$SFTM/adapter" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$FINM/adapter" --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
  cpconf "$FINM"
fi
say "[w8] SFT→GRPO: $([ -f "$FINM/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)"
say "=== ${TAG}_TRAIN_DONE (w8 이어받기) ==="
