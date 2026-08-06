#!/bin/bash
# tst1000tr5091 batch-chunk GRPO (최종 세팅) — 사용자 지정 설계.
#   데이터: train pool 4560 / valid 500(조기종료) / test=rand200(최종). 상호 배타.
#   batch B=100(46 batch/epoch), G=8 rollout, batch 전체 loss 1번→update 1번(full_batch), lr 1e-5, kl 0.015, clip 0.2.
#   epoch max 3, epoch끝 valid pass율 평가 → 증가 없으면(patience 1) 중단 → best로 test 평가.
#   GPU 0,1 각 workers 10(20병렬), rollout timeout 120. 초대형 자동제외. 재개 가능(progress 파일).
cd /app/coq-modeling || exit 1
TAG=tst1000tr5091
LOG=all_log/${TAG}_bc.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
SFTM=models/rango-${TAG}-sft/adapter          # π0 = init & KL 앵커
TRAINPOOL=data/${TAG}_trainpool_idx.txt        # 4560
VALID=data/${TAG}_valid500_idx.txt             # 500
TEST=data/compcert_${TAG}_test_idx.txt          # 1000 (아래 B= 블록에서 재확인)
B=100; G=8; KL=0.015; CLIP=0.2; MAXEP=3; ROLLTO=300; WK=12
GPUS="1"    # 외부가 GPU0 점유 시 "1"로. gpu0_foreign 플래그로도 GRPO 회피
LR_HI=3e-4; LR_LO=3e-5      # ★ cosine decay: 3e-4 → 3e-5 (현재 실험)
# ★ hyperparameter별 저장: 실험태그를 모델·결과 경로에 붙여 서로 안 덮어씀
EXP="lr${LR_HI}_kl${KL}_B${B}_G${G}"
MROOT=models/rango-${TAG}-bc_${EXP}
CUR=$MROOT/cur/adapter                          # 현재 정책(batch마다 덮어씀)
NEW=$MROOT/new/adapter                          # 임시 저장
BEST=$MROOT/best/adapter                        # valid best
PROG=$MROOT/progress.txt                        # 재개용: 마지막 완료 global batch id
BESTF=$MROOT/best_score.txt
BASEF=$MROOT/baseline_probe.txt                 # SFT baseline probe (성능 리포트용, 고정)
PREVF=$MROOT/prev_probe.txt                     # ★ 직전 probe (정체 판정 기준, 매 probe 갱신)
STALL_THRESH=4   # ★ strict 정체 기준: probe − 직전probe < 4 이면 정체(개선 멈춤) → ref_snapshot←cur
TMAX=138                    # cosine 총 update 기준(46 batch × 3 epoch). 조기종료 시 중간 lr에서 멈춤
MAXSTEPS=60                 # rollout 시도당 최대 tactic
TEST=data/compcert_${TAG}_test_idx.txt      # 최종 test = test1000 @600s
PROBE=data/${TAG}_probe100_idx.txt          # ★ 고정 probe 100 (valid에서 추출) — flywheel 측정용
PROBE_EVERY=10              # 매 10 batch마다 probe 성공률 측정
#  세팅: G=8, workers 6/gpu(12병렬), full_batch(batch당 1 update), cosine lr 1e-4→1e-5, kl 0.015.
#  flywheel 측정: 고정 probe100 성공률을 매 10 batch마다 (같은 정리라 chunk 노이즈 제거).
mkdir -p "$MROOT"
freemem(){ nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i "$1" 2>/dev/null; }
wait_gpu(){ local need=${1:-24000} w=0; while :; do local f0=$(freemem 0) f1=$(freemem 1);f0=${f0:-0};f1=${f1:-0}
  [ ! -f /tmp/gpu0_foreign ] && [ "$f0" -ge "$need" ] && { echo 0;return; }
  [ "$f1" -ge "$need" ] && { echo 1;return; }; [ $w -ge 5400 ]&&{ echo 1;return; }; sleep 30;w=$((w+30)); done; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1" 2>/dev/null; }
rollf(){ pkill -9 -f 'tactic_gen_server.py' 2>/dev/null; }
succ(){ python3 -c "import json,os;p='$1/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success',0))" 2>/dev/null; }

[ -f "$SFTM/adapter_model.safetensors" ] || { say "SFT 모델 없음 — 중단"; exit 1; }

# 재개 상태
DONE_GB=$(cat "$PROG" 2>/dev/null || echo -1)
BEST_SCORE=$(cat "$BESTF" 2>/dev/null || echo -1)
PATIENCE=0
# 현재 정책: 재개면 cur, 아니면 SFT
if [ -f "$CUR/adapter_model.safetensors" ] && [ "$DONE_GB" -ge 0 ]; then PREV="$CUR"; else PREV="$SFTM"; fi
say "=== batch-chunk GRPO 시작 (B=$B G=$G kl=$KL cosine-lr ${LR_HI}→${LR_LO} ep_max=$MAXEP) ==="
say "  train pool $(wc -l < $TRAINPOOL) / valid $(wc -l < $VALID) / test $(wc -l < $TEST) | probe $(wc -l < $PROBE) | 재개 DONE_GB=$DONE_GB best=$BEST_SCORE"

# ★ baseline probe (학습 전 SFT) — 새 시작일 때만. flywheel 비교 기준점.
if [ "$DONE_GB" -lt 0 ]; then
  PRES=all_results/${TAG}_bc_${EXP}_probe_baseline; rm -rf "$PRES"
  EXEC_ADAPTER=$SFTM HF_HUB_OFFLINE=1 \
    python3 scripts/run_all.py --alias rango-grpo --idx-file "$PROBE" --timeout 120 --gpus "$GPUS" --workers $WK \
    --out "$PRES" --description "probe baseline(SFT)" >> "$LOG" 2>&1
  rollf
  BSC=$(python3 -c "import json,os;p='$PRES/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success',0))" 2>/dev/null)
  echo "${BSC:-0}" > "$BASEF"    # SFT baseline (리포트 고정)
  echo "${BSC:-0}" > "$PREVF"    # 직전 probe 초기값 = baseline
  say "  ★probe baseline(SFT, 학습전): $BSC/100 (정체판정=직전probe 대비 +${STALL_THRESH} 미만)"
fi
[ -f "$PREVF" ] || cat "$BASEF" > "$PREVF" 2>/dev/null || echo 0 > "$PREVF"  # 재개 시 prev_probe 없으면 baseline으로

for EP in $(seq 0 $((MAXEP-1))); do
  # epoch별 shuffle → batch 파일 (seed=epoch, 재현/재개 일관)
  CKDIR=data/bc_chunks_${TAG}/ep${EP}; mkdir -p "$CKDIR"; rm -f "$CKDIR"/b_*.txt
  NB=$(python3 -c "
import random
idx=[x.strip() for x in open('$TRAINPOOL') if x.strip()]
random.seed(100+$EP); random.shuffle(idx)
n=0
for i in range(0,len(idx),$B):
    open(f'$CKDIR/b_{n:03d}.txt','w').write('\n'.join(idx[i:i+$B])+'\n'); n+=1
print(n)
")
  say "── epoch $EP: $NB batch (shuffle seed=$((100+EP))) ──"
  for BI in $(seq 0 $((NB-1))); do
    GBID=$((EP*1000+BI))
    if [ "$GBID" -le "$DONE_GB" ]; then continue; fi   # 재개 skip
    bi=$(printf "%03d" $BI)
    CHUNK="$CKDIR/b_${bi}.txt"
    ROLL="data/grpo_rollouts/${TAG}_bc_ep${EP}_b${bi}_roll.jsonl"
    MIXED="data/grpo_rollouts/${TAG}_bc_ep${EP}_b${bi}_mixed.jsonl"
    rm -f "$ROLL"
    # rollout (현재정책 PREV, G=16, gpu 0,1 w8)
    say "  ep$EP b$bi 롤아웃: $(wc -l < $CHUNK)×G$G @${ROLLTO}s (정책=$([ "$PREV" = "$SFTM" ] && echo SFT || echo cur))"
    EXEC_ADAPTER=$PREV ROLLOUT_OUT=$ROLL ROLLOUT_RETRY=1 GROUP_SIZE=$G MAX_STEPS=$MAXSTEPS HF_HUB_OFFLINE=1 \
      python3 scripts/run_all.py --alias grpo-rollout-pf --idx-file "$CHUNK" --timeout "$ROLLTO" --gpus "$GPUS" --workers $WK >> "$LOG" 2>&1
    rollf; sleep 3
    # mixed 필터 (std>0 + 초대형 자동제외)
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
        if giant(g): big+=1; continue
        mx+=1; o.write(l)
    else: al+=1
except FileNotFoundError: pass
print(f'  ep$EP b$bi flywheel: rollout {n} | mixed {mx} dead {dd} ({100*dd/max(n,1):.1f}%) all {al} | 초대형제외 {big}')
" | tee -a "$LOG"
    MX=$(wc -l < "$MIXED" 2>/dev/null || echo 0)
    if [ "${MX:-0}" -lt 1 ]; then say "    mixed 0 → update skip"; echo "$GBID" > "$PROG"; continue; fi
    # ★ cosine lr: t=현재 global update 순번(epoch*46+BI), T=TMAX. lr = LO + (HI-LO)*0.5*(1+cos(π t/T))
    GT=$((EP*NB+BI))
    LR=$(python3 -c "import math; t=min($GT,$TMAX); print(f'{$LR_LO + ($LR_HI-$LR_LO)*0.5*(1+math.cos(math.pi*t/$TMAX)):.3e}')")
    # ★ ref anchor = ref_snapshot (평소 고정, 정체 시에만 cur로 갱신 — batch마다 갱신 아님).
    #   초기 snapshot=SFT. 정체 감지(probe−baseline<STALL) 때마다 snapshot←현재 cur 로 리셋.
    if [ -f "$MROOT/ref_snap/adapter/adapter_model.safetensors" ]; then REFA="$MROOT/ref_snap/adapter"; else REFA="$SFTM"; fi
    # GRPO: batch 전체 loss → 1 update (full_batch), init=PREV, cosine lr
    G0=$(wait_gpu 24000); rm -rf "$NEW"
    say "    ep$EP b$bi GRPO (mixed $MX, lr=$LR, ref=$([ "$REFA" = "$SFTM" ] && echo SFT || echo snap))"
    HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True CUDA_VISIBLE_DEVICES=$G0 \
      python3 -m tactic_gen.grpo_train --rollouts "$MIXED" --model_name "$BASE" \
        --init_adapter "$PREV" --ref_adapter "$REFA" \
        --collator_conf "$CONF" --max_len 3072 --save_dir "$NEW" \
        --kl_beta $KL --clip_eps $CLIP --epochs 1 --lr $LR --micro_bsz 2 --full_batch_update >> "$LOG" 2>&1
    if [ -f "$NEW/adapter_model.safetensors" ]; then
      rm -rf "$MROOT/cur"; mkdir -p "$MROOT/cur"; mv "$NEW" "$CUR"; cpconf "$MROOT/cur/"
      PREV="$CUR"; echo "$GBID" > "$PROG"
      say "    ep$EP b$bi update OK (mixed $MX)"
    else
      say "    ep$EP b$bi GRPO 실패 → 정책 유지"; echo "$GBID" > "$PROG"
    fi
    # ★ harvesting 대비: 롤아웃 원본(dead 포함 전체) 보존. gzip으로 압축 보관.
    #   dead group의 실패 rollout에서 닫힌 subgoal 수확용(step에 example/result/state_key 기록됨).
    gzip -f "$ROLL" 2>/dev/null && say "    원본 보존(harvest용): ${ROLL}.gz" || say "    원본 보존: $ROLL"

    # ★ 매 PROBE_EVERY batch: 모델 가중치 스냅샷 저장(_{batch}) + probe 성공률 측정
    if [ $(( (GT+1) % PROBE_EVERY )) -eq 0 ]; then
      # 모델 스냅샷 (요청: 10 batch마다 학습결과 저장, step_{batch} 이름)
      rm -rf "$MROOT/step_${GT}"; mkdir -p "$MROOT/step_${GT}"; cp -r "$CUR" "$MROOT/step_${GT}/adapter"; cpconf "$MROOT/step_${GT}/"
      say "    → 모델 저장: $MROOT/step_${GT} (batch $GT)"
      # 고정 probe 성공률 — flywheel 측정(같은 정리라 chunk 노이즈 없음)
      PRES=all_results/${TAG}_bc_${EXP}_probe_gt$(printf %03d $GT)
      rm -rf "$PRES"
      EXEC_ADAPTER=$PREV HF_HUB_OFFLINE=1 \
        python3 scripts/run_all.py --alias rango-grpo --idx-file "$PROBE" --timeout 120 --gpus "$GPUS" --workers $WK \
        --out "$PRES" --description "probe gt$GT" >> "$LOG" 2>&1
      rollf
      PSC=$(python3 -c "import json,os;p='$PRES/summary.json';d=json.load(open(p)) if os.path.exists(p) else {};print(d.get('success',0))" 2>/dev/null)
      RTAG=$([ -f "$MROOT/ref_snap/adapter/adapter_model.safetensors" ] && echo snap || echo SFT)
      BASE_SC=$(cat "$BASEF" 2>/dev/null || echo 0)   # SFT baseline (리포트: 총 개선)
      PREV_SC=$(cat "$PREVF" 2>/dev/null || echo "$BASE_SC")  # 직전 probe (정체 판정)
      say "    ★probe(gt=$GT, lr=$LR, ref=$RTAG): $PSC/100  (SFT대비 총 $(( ${PSC:-0}-${BASE_SC:-0} ))/100 · 직전 $PREV_SC 대비 $(( ${PSC:-0}-${PREV_SC:-0} )))"
      # ★ 정체 판정 = "직전 probe" 대비 개선 < STALL_THRESH (SFT 고정 아님 — 한번 오르면 기준도 따라 오름).
      #   정체면 ref_snapshot ← 현재 cur 로 리셋(anchor 계단식 이동, drift 통제).
      if [ $(( ${PSC:-0} - ${PREV_SC:-0} )) -lt "$STALL_THRESH" ]; then
        rm -rf "$MROOT/ref_snap"; mkdir -p "$MROOT/ref_snap"; cp -r "$CUR" "$MROOT/ref_snap/adapter"
        say "    ⚠️ 정체 (probe $PSC − 직전 $PREV_SC < $STALL_THRESH) → ref_snapshot ← cur 리셋"
      else
        say "    → 개선 (probe $PSC − 직전 $PREV_SC ≥ $STALL_THRESH) → ref_snapshot 유지"
      fi
      echo "${PSC:-0}" > "$PREVF"   # ★ 직전 probe 갱신 (다음 판정 기준)
    fi
  done

  # ── epoch 끝: valid pass율 평가 (조기종료) ──
  VRES=all_results/${TAG}_bc_${EXP}_valid_ep${EP}
  say "  ep$EP valid 평가 (500 @120s w$WK)"
  rm -rf "$VRES"
  EXEC_ADAPTER=$PREV HF_HUB_OFFLINE=1 \
    python3 scripts/run_all.py --alias rango-grpo --idx-file "$VALID" --timeout 120 --gpus "$GPUS" --workers $WK \
    --out "$VRES" --description "bc valid ep$EP" >> "$LOG" 2>&1
  rollf
  SC=$(succ "$VRES")
  say "  ★ epoch $EP valid: $SC/500 (best=$BEST_SCORE)"
  # ★ epoch별 가중치 스냅샷 저장 (요청: 모든 batch 끝나면 epoch 모델 다 보존)
  rm -rf "$MROOT/epoch${EP}"; mkdir -p "$MROOT/epoch${EP}"; cp -r "$CUR" "$MROOT/epoch${EP}/adapter"; cpconf "$MROOT/epoch${EP}/"
  say "    → epoch $EP 가중치 저장: $MROOT/epoch${EP} (valid $SC/500)"
  if [ "${SC:-0}" -gt "${BEST_SCORE%.*}" ]; then
    BEST_SCORE=$SC; echo "$SC" > "$BESTF"
    rm -rf "$MROOT/best"; mkdir -p "$MROOT/best"; cp -r "$CUR" "$BEST"; cpconf "$MROOT/best/"
    PATIENCE=0; say "    → best 갱신, 저장"
  else
    PATIENCE=$((PATIENCE+1)); say "    → valid 증가 없음 (patience $PATIENCE)"
    if [ "$PATIENCE" -ge 1 ]; then say "  ⏹ 조기종료 (valid 감소) — epoch $EP 에서 중단"; break; fi
  fi
done

# ── 최종 test (best 모델, test1000 @600s w2) — test1000은 train과 완전 분리(순수 held-out) ──
FINAL="$BEST"; [ -f "$FINAL/adapter_model.safetensors" ] || FINAL="$CUR"
NT=$(wc -l < "$TEST")
say "▶ 최종 test: best 모델로 test1000($NT개) @600s w2"
RES=all_results/${TAG}_bc_${EXP}_test1000
rm -rf "$RES"
EXEC_ADAPTER=$FINAL HF_HUB_OFFLINE=1 \
  python3 scripts/run_all.py --alias rango-grpo --idx-file "$TEST" --timeout 600 --gpus "$GPUS" --workers 2 \
  --out "$RES" --description "bc final test1000" >> "$LOG" 2>&1
rollf
say "  ★★ batch-chunk 최종 test1000: $(succ $RES)/$NT (best valid=$BEST_SCORE/500)"
say "=== ${TAG}_BC_DONE ==="
