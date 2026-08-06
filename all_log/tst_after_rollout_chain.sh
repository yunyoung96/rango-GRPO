#!/bin/bash
# 롤아웃 완료 대기 → mixed 필터 → GRPO(단일GPU) → rand200 @600s 평가.
#   rand200 200개 중 31개가 train유출(test1000엔 169) → full-200 + held-out-169 둘 다 리포트.
cd /app/coq-modeling || exit 1
TAG=tst1000tr5091
LOG=all_log/${TAG}_after_rollout.log
: > "$LOG"
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
SFTM=models/rango-${TAG}-sft
SFTROLL=data/grpo_rollouts/${TAG}_sftroll.jsonl
MIXED=data/grpo_rollouts/${TAG}_sftroll_mixed.jsonl
FINM=models/rango-${TAG}-sftgrpo
RAND=data/compcert_bs2_rand200_idx.txt
RES=all_results/${TAG}_sftgrpo_rand200_600
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
wait_gpu(){ local need=${1:-24000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ] && { echo 0;return; }
  [ "$f1" -ge "$need" ] && { echo 1;return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 30;w=$((w+30)); done; }
wait_gpus(){ local need=${1:-13000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  local g=""; [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ]&&g="0"; [ "$f1" -ge "$need" ]&&g="${g:+$g,}1"
  [ -n "$g" ]&&{ echo "$g";return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 30;w=$((w+30)); done; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'))" 2>/dev/null; }

# ── 0) 롤아웃 완료 대기 (DONE 마커 or 프로세스 종료 + sftroll 안정) ──
say "롤아웃 완료 대기 중..."
while :; do
  grep -q 'ROLLOUT_RESUME_DONE' all_log/${TAG}_rollout_resume.log 2>/dev/null && break
  if ! pgrep -f 'tst_rollout_resume.sh' >/dev/null && ! pgrep -f 'run_all.py --alias grpo-rollout-pf' >/dev/null; then
    say "  롤아웃 프로세스 종료 감지 (마커 없이) → 진행"; break
  fi
  sleep 120
done
pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 5
say "롤아웃 종료. sftroll = $(wc -l < $SFTROLL) 그룹"

# ── 1) mixed 필터 (dead/all-solved 제외 = 학습결과 동일, ~4x 빠름) ──
python3 -c "
import json
n=k=0
with open('$MIXED','w') as o:
    for l in open('$SFTROLL'):
        n+=1
        try: g=json.loads(l)
        except: continue
        on=[a for a in g['attempts'] if a.get('steps') and not a.get('off_policy')]
        if not on: continue
        sv=sum(1 for a in on if a['reward']>=1)
        if 0<sv<len(on): o.write(l); k+=1
print(f'mixed {k}/{n}')
" | tee -a "$LOG"
say "▶ GRPO 단일-GPU (mixed $(wc -l < $MIXED)그룹, kl0.04 ep2)"

# ── 2) GRPO 단일-GPU ──
G=$(wait_gpu 24000)
rm -rf "$FINM/adapter"
HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$G \
  python3 -m tactic_gen.grpo_train --rollouts "$MIXED" --model_name "$BASE" --init_adapter "$SFTM/adapter" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$FINM/adapter" \
    --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
cpconf "$FINM"
say "  GRPO: $([ -f "$FINM/adapter/adapter_model.safetensors" ] && echo OK || echo 실패)"
[ -f "$FINM/adapter/adapter_model.safetensors" ] || { say "GRPO 실패 — 중단"; exit 1; }

# ── 3) 모델A GRPO 완료 → GPU0 해제(모델B가 양쪽 GPU 사용). rand200 비교는 모델B 완료 후 일괄 ──
rm -f /tmp/gpu0_foreign
say "모델A GRPO 완료 → /tmp/gpu0_foreign 제거 = GPU0 해제. 이제 모델B가 양쪽 GPU 사용."
say "  (rand200 비교는 모델B 51라운드 완료 후 chunk_grpo.sh가 모델A+모델B 일괄 실행)"
say "=== ${TAG}_AFTER_ROLLOUT_DONE (모델A GRPO 완료, GPU0 해제) ==="
