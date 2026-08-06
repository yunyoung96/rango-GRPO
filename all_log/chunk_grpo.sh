#!/bin/bash
# tst1000tr5091 chunked GRPO (모델 B) — 5091을 200개×26 batch로 rollout→GRPO 반복.
#   각 batch: theorem 200개 × G=16 rollout → mixed(~60) → batch 전체 loss 1번 → update 1번(full_batch).
#   GPU 동적(모델A가 GPU0 점유중이면 GPU1만, 끝나면 양쪽). batch마다 저장(재개가능).
#   관심사: batch 진행하며 mixed 오르는지/dead 내리는지(flywheel). lr 1e-5, epochs 1.
cd /app/coq-modeling || exit 1
TAG=tst1000tr5091
LOG=all_log/${TAG}_chunk.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
SFTM=models/rango-${TAG}-sft
FINM=models/rango-${TAG}-sftgrpo             # 모델A (비교용)
TRAIN=data/compcert_${TAG}_train_idx.txt
CKDIR=data/chunks_${TAG}
MROOT=models/rango-${TAG}-chunk
RAND=data/compcert_bs2_rand200_idx.txt
CHUNK_TO=300
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
wait_gpu(){ local need=${1:-24000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ] && { echo 0;return; }
  [ "$f1" -ge "$need" ] && { echo 1;return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 30;w=$((w+30)); done; }
wait_gpus(){ local need=${1:-13000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  local g=""; [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ]&&g="0"; [ "$f1" -ge "$need" ]&&g="${g:+$g,}1"
  [ -n "$g" ]&&{ echo "$g";return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 30;w=$((w+30)); done; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }
rollf(){ pkill -9 -f 'tactic_gen_server.py.*rango-tst1000tr5091-\(sft/\|chunk\)' 2>/dev/null; }
sumline(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success'),'/',d.get('done'))" 2>/dev/null; }

say "=== 모델B chunked (동적GPU, 재개가능, 일시정지 없음) ==="

# chunk 분할 (seed 고정, 멱등)
mkdir -p "$CKDIR"
rm -f "$CKDIR"/chunk_*.txt     # 재분할 전 옛 chunk(다른 크기) 정리
NCH=$(python3 -c "
import random
idx=[x.strip() for x in open('$TRAIN') if x.strip()]
random.seed(0); random.shuffle(idx)
n=0
for i in range(0,len(idx),200):
    open(f'$CKDIR/chunk_{n:03d}.txt','w').write('\n'.join(idx[i:i+200])+'\n'); n+=1
print(n)
")

# 재개: 완료된 마지막 라운드
PREV="$SFTM/adapter"; START=0
for r in $(seq 0 $((NCH-1))); do
  ri=$(printf "%03d" $r)
  [ -f "$MROOT/r${ri}/adapter/adapter_model.safetensors" ] && { PREV="$MROOT/r${ri}/adapter"; START=$((r+1)); }
done
say "chunk ${NCH}개 · 라운드 $START 부터 (prev=$(basename $(dirname $PREV)))"

# 라운드 루프 (일시정지 없음 — 끝까지)
for r in $(seq $START $((NCH-1))); do
  ri=$(printf "%03d" $r)
  CHUNK="$CKDIR/chunk_${ri}.txt"
  ROLL="data/grpo_rollouts/${TAG}_chunk_${ri}_roll.jsonl"
  MIXED="data/grpo_rollouts/${TAG}_chunk_${ri}_mixed.jsonl"
  NEW="$MROOT/r${ri}/adapter"
  rm -f "$ROLL"
  GPUS=$(wait_gpus 13000)
  say "R$ri 롤아웃: $(wc -l < $CHUNK)개 × G=16 @${CHUNK_TO}s (정책=$(basename $(dirname $PREV)), GPU $GPUS)"
  EXEC_ADAPTER=$PREV ROLLOUT_OUT=$ROLL ROLLOUT_RETRY=1 GROUP_SIZE=16 HF_HUB_OFFLINE=1 \
    python3 scripts/run_all.py --alias grpo-rollout-pf --idx-file "$CHUNK" --timeout "$CHUNK_TO" --gpus "$GPUS" --workers 4 >> "$LOG" 2>&1
  rollf; sleep 3
  python3 -c "
import json
n=mx=dd=al=big=0; CAP=50000
def giant(g):
    for a in g['attempts']:
        for st in a.get('steps',[]):
            ex=st.get('example',{})
            if isinstance(ex,str):
                if len(ex)>CAP: return True
                try: ex=json.loads(ex)
                except: continue
            if isinstance(ex,dict) and any(len(v if isinstance(v,str) else json.dumps(v))>CAP for v in ex.values()): return True
    return False
try:
 with open('$MIXED','w') as o:
  for l in open('$ROLL'):
    n+=1
    try: g=json.loads(l)
    except: continue
    on=[a for a in g['attempts'] if a.get('steps') and not a.get('off_policy')]
    if not on: continue
    sv=sum(1 for a in on if a['reward']>=1)
    if sv==0: dd+=1
    elif sv<len(on):
        if giant(g): big+=1; continue   # ★ 초대형 예제(>50KB) 자동 제외
        mx+=1; o.write(l)
    else: al+=1
except FileNotFoundError: pass
print(f'R$ri flywheel: rollout {n} | mixed {mx} dead {dd} ({100*dd/max(n,1):.1f}%) all {al} | 초대형제외 {big}')
" | tee -a "$LOG"
  MX=$(wc -l < "$MIXED" 2>/dev/null || echo 0)
  if [ "${MX:-0}" -lt 1 ]; then say "  R$ri mixed 0 → GRPO 스킵(정책 유지)"; continue; fi
  G=$(wait_gpu 24000)
  rm -rf "$NEW"
  # ★ 의사코드식: chunk 전체 loss → gradient 누적 → 1 update (--full_batch_update, epochs 1).
  #   chunk rollout당 1 gradient step = 가장 on-policy. ratio≈1(첫 update 전)이라 clip 무의미.
  HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$G \
    python3 -m tactic_gen.grpo_train --rollouts "$MIXED" --model_name "$BASE" \
      --init_adapter "$PREV" --ref_adapter "$SFTM/adapter" \
      --collator_conf "$CONF" --max_len 3072 --save_dir "$NEW" \
      --kl_beta 0.04 --epochs 1 --lr 1e-5 --micro_bsz 2 --full_batch_update >> "$LOG" 2>&1
  if [ -f "$NEW/adapter_model.safetensors" ]; then
    cpconf "$MROOT/r${ri}"; PREV="$NEW"; say "  R$ri GRPO OK (mixed $MX) → 저장 r${ri}"
  else say "  R$ri GRPO 실패 → 이전 정책 유지"; fi
done
say "=== 모델B 전체 ${NCH}라운드 완료 (최종=$PREV) ==="

# ── mixed 추세 요약 (flywheel 판정) ──
say "── flywheel 추세 (라운드별 dead%) ──"
grep -oE 'R[0-9]+ flywheel: rollout [0-9]+ \| mixed [0-9]+ dead [0-9]+ \([0-9.]+%\)' "$LOG" | tee -a "$LOG" >/dev/null
python3 -c "
import re
xs=[]
for l in open('$LOG'):
    m=re.search(r'R(\d+) flywheel: rollout (\d+) \| mixed (\d+) dead (\d+) \(([\d.]+)%\)', l)
    if m: xs.append((int(m.group(1)),int(m.group(3)),float(m.group(5))))
if xs:
    k=max(1,len(xs)//3)
    early=xs[:k]; late=xs[-k:]
    em=sum(x[1] for x in early)/len(early); lm=sum(x[1] for x in late)/len(late)
    ed=sum(x[2] for x in early)/len(early); ld=sum(x[2] for x in late)/len(late)
    print(f'  초반{k}R 평균: mixed {em:.1f} dead {ed:.1f}%  →  후반{k}R 평균: mixed {lm:.1f} dead {ld:.1f}%')
    print(f'  flywheel: {\"작동(mixed↑ dead↓)\" if lm>em+2 and ld<ed-2 else \"약함/없음(변화 미미)\"}')
" | tee -a "$LOG"

# ── 비교 rand200 (양쪽 GPU) — 모델B 최종 + 모델A(single) ──
BLAST="$PREV"
say "▶ 비교 rand200 @600s (모델B 최종 + 모델A single, 양쪽GPU)"
for M in "chunk:$BLAST:all_results/${TAG}_chunk_rand200_600" "single:$FINM/adapter:all_results/${TAG}_sftgrpo_rand200_600"; do
  nm=${M%%:*}; rest=${M#*:}; ad=${rest%%:*}; out=${rest#*:}
  [ -f "$ad/adapter_model.safetensors" ] || { say "  $nm 모델없음 → 생략"; continue; }
  GPUS=$(wait_gpus 13000); rm -rf "$out"
  EXEC_ADAPTER=$ad HF_HUB_OFFLINE=1 \
    python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" --timeout 600 --gpus "$GPUS" --workers 2 \
    --out "$out" --description "$nm rand200" >> "$LOG" 2>&1
  pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; sleep 3
  say "  ★ $nm rand200 full-200: $(sumline $out)"
done
python3 -c "
import json,os
train=set(int(x) for x in open('$TRAIN').read().split())
for nm,p in [('single','all_results/${TAG}_sftgrpo_rand200_600/summary.json'),('chunk','all_results/${TAG}_chunk_rand200_600/summary.json')]:
    if not os.path.exists(p): print(f'  {nm}: 결과없음'); continue
    d=json.load(open(p)); res=d.get('results',[])
    held=[r for r in res if r['idx'] not in train]; hs=sum(1 for r in held if r.get('success'))
    print(f'  {nm}: full-200 {d.get(\"success\")}/{d.get(\"done\")} | held-out-169 {hs}/{len(held)} ({100*hs/max(len(held),1):.1f}%)')
print('  비교기준: base rango 67/200 · bs2 SFT→GRPO 75/200')
" | tee -a "$LOG"
say "=== ${TAG}_CHUNK_DONE ==="
