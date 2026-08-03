#!/bin/bash
# augmented SFT 완료 후 → rand200 @600s w2 평가 (test1191@120s 대신). 이어받기.
#   원 aug_bs2.sh가 test1191@120s로 평가하는데, 사용자 요청 rand200@600s로 교체.
#   SFT모델 완성 감지 → 원 스크립트 평가(▶2) 죽이고 → rand200@600s로.
cd /app/coq-modeling || exit 1
LOG=all_log/aug_bs2.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
AUGM=models/rango-aug-bs2-sft
RAND=data/compcert_bs2_rand200_idx.txt
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'),'(',round(100*d.get('success',0)/max(d.get('done',1),1),1),'%)')" 2>/dev/null; }
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
wait_gpus(){ local need=${1:-13000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  local g=""; [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ]&&g="0"; [ "$f1" -ge "$need" ]&&g="${g:+$g,}1"
  [ -n "$g" ]&&{ echo "$g";return; }; [ $w -ge 7200 ]&&{ echo 1;return; }; sleep 30;w=$((w+30)); done; }

# 1) SFT 완성 대기
say "[rand200@600s] SFT 완성 대기..."
S=$SECONDS
while :; do
  [ -f "$AUGM/adapter/adapter_model.safetensors" ] && break
  sleep 30; [ $((SECONDS-S)) -ge 7200 ] && { say "[rand200] SFT대기 타임아웃"; break; }
done
[ -f "$AUGM/adapter/adapter_model.safetensors" ] || { say "[rand200] SFT 없음 — 중단"; exit 1; }
say "[rand200] SFT 완성 → 원 스크립트 test1191@120s 평가 대신 rand200@600s로 교체"

# 2) 원 스크립트의 test1191 평가 죽이기 (rand200으로 교체)
sleep 8
pkill -9 -f 'run_all.py --alias rango-grpo' 2>/dev/null
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 5
rm -rf all_results/aug_bs2_sft   # test1191 부분결과 제거

# 3) rand200 @600s w2 (augmented env)
GPUS=$(wait_gpus 13000)
say "[rand200] ▶ augmented SFT rand200 @600s w2 (GPU $GPUS, INJECT env)"
HF_HUB_OFFLINE=1 EXEC_ADAPTER=$AUGM/adapter INJECT_TYPES=1 INJECT_DEFS=1 RERANK_PREMISES=1 \
  python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" --timeout 600 --gpus "$GPUS" --workers 2 \
  --out all_results/aug_bs2_rand200_600 --description "augmented SFT rand200 @600s" >> "$LOG" 2>&1
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
say "  ★★ augmented SFT rand200@600s: $(sumline all_results/aug_bs2_rand200_600)"
say "     비교: baseline 67/200(33.5%) / SFT→GRPO 75/200(37.5%) @600s"
say "=== AUG_RAND200_DONE ==="
