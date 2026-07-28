#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# SFT→CASCADE-subgoal-GRPO — subgoal 방법의 on-policy 정정판.
#
# 기존 subgoal(run_subgoal_bigscale.sh)과의 차이 = ★ 롤아웃 정책을 스테이지 init 에 맞춤(cascade).
#   기존: s1/s2/s3 롤아웃을 전부 SFT 모델로 뽑음(데이터-정책 불일치, off-policy).
#   여기: 각 스테이지 롤아웃 정책 = 그 스테이지 init 모델(SFT→s1→s2→s3 로 "폭포처럼" 이어짐).
#     s1 롤아웃=SFT / s2 롤아웃=s1 / s3 롤아웃=s2 / s0 롤아웃=s3  (전부 on-policy).
#   → 각 GRPO 라운드가 진짜 on-policy(π_old=init)라 신호가 덜 흐릿할 것으로 기대.
#
# 병렬: 멀티-GPU(g=2). 각 워커를 CUDA_VISIBLE_DEVICES 로 물리 GPU 에 핀(정리 단위 독립).
#   롤아웃·평가 모두 g2×w4(=8 병렬, ROLLW=EVALW=4). group_size(G)=8. 옵션명 g2w4.
#   자원 감시(보고 전용): 별도 nvidia-smi 감시자(all_log/gpu_watch.sh)가 GPU util·mem 을 md(all_log/gpu_monitor.md)에 연속 기록.
#     빡빡하면 감시자가 md 에 표시 → 사용자에 보고. 자동정지 없음.
# 흐름: leaf 커리큘럼 재사용 → s1→s2→s3→s0 (각 라운드 collect(g2w4)→GRPO) → rand200@600s g2w4600s → 1191@120s g2w4.
# ══════════════════════════════════════════════════════════════════════════════
set -u
LOG=all_log/cascade.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
SFTM=models/rango-grpo-bs2-sft/adapter        # ★ SFT(gold) = s1 라운드의 init·롤아웃 정책
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
TEST=data/compcert_bs2_test_idx.txt
RAND=data/compcert_bs2_rand200_idx.txt
TRAIN=data/compcert_bs2_train_idx.txt
NTEST=$(wc -l < "$TEST")
GPUS="0,1"                                     # ★ 사용 물리 GPU (2개, RTX 6000 Ada 48GB×2)
ROLLW=4                                         # ★ rollout: GPU당 워커 → g2×w4 = 8 병렬
EVALW=4                                         # ★ eval:    GPU당 워커 → g2×w4 = 8 병렬 (옵션명 g2w4)
export SUBGOAL_GS=8                             # ★ rollout 개수(group_size) 6→8 = SFT→GRPO와 매칭
export SUBGOAL_MAXSTEPS=20                      # ★ max_steps 16→20 = SFT→GRPO와 공정 매칭
HARVEST_ROUND=${HARVEST_ROUND:-0}              # ★ s0 후 harvest 라운드 (0=안함[기본], 1=함). env 로 켬: HARVEST_ROUND=1 bash ...
# 자원 감시: 별도 nvidia-smi 감시자(all_log/gpu_watch.sh)가 GPU util·mem 을 md 에 연속 기록(보고 전용).
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }
gtrain(){ python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$2" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$3/adapter" \
    --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1; cpconf "$3"; }
idxof(){ python3 -c "import json;print('\n'.join(str(v['idx']) for v in json.load(open('$1')).values()))"; }
teval(){ local d="all_results/bs2_$2_g2w4120s/summary.json"; local n
  n=$([ -s "$d" ] && python3 -c "import json;print(len(json.load(open('$d'))['results']))" 2>/dev/null || echo 0)
  [ "$n" -ge "$NTEST" ] && { say "   $2 이미 완료($n)"; return 0; }
  python3 scripts/run_all.py --alias "$1" --idx-file "$TEST" --timeout 120 --gpus "$GPUS" --workers $EVALW \
    --out "all_results/bs2_$2_g2w4120s" --description "cascade $2 g2w4" >> "$LOG" 2>&1; }
# cascade 스테이지: $1=stage $2=커리큘럼접두 $3=idx $4=init($=롤아웃 정책!) $5=save $6=RT
lstage(){ local ST=$1 PFX=$2 IDXF=$3 INIT=$4 SAVE=$5 RT=$6
  local CUR="${PFX}_${ST}.json" ROLL="data/grpo_rollouts/${SAVE##*/}_${ST}.jsonl"
  say "  ▶ [$SAVE] cascade-$ST rollout(정책=$(basename $(dirname $INIT)))+GRPO(init=동일)"
  [ -s "$CUR" ] || { say "    ✗ $CUR 없음 — 스킵"; return 0; }
  # ★ on-policy: 롤아웃 정책 = 이 스테이지 init 모델
  export SUBGOAL_CURRICULUM="$CUR" SUBGOAL_OUT="$ROLL" SUBGOAL_SKIP_S0=1 SUBGOAL_REWARD=1 SUBGOAL_POLICY="$INIT"
  [ -s "$ROLL" ] || python3 scripts/run_all.py --alias grpo-rollout-subgoal --idx-file "$IDXF" --timeout $RT --gpus "$GPUS" --workers $ROLLW >> "$LOG" 2>&1
  [ -f "$SAVE/adapter/adapter_model.safetensors" ] || gtrain "$ROLL" "$INIT" "$SAVE"; }

say "════════ SFT→CASCADE-subgoal-GRPO (on-policy, gpus=$GPUS roll×w$ROLLW eval×w$EVALW, G=$SUBGOAL_GS steps=$SUBGOAL_MAXSTEPS retries=${SUBGOAL_RETRIES:-2}) ════════"
[ -f "$SFTM/adapter_model.safetensors" ] || { say "✗ SFT 모델($SFTM) 없음 — 중단"; exit 1; }

# ─────────────── leaf 커리큘럼 재사용(이미 빌드됨) ───────────────
say "▶ leaf 커리큘럼 재사용(data/curriculum/leaf_bs2_s{1,2,3}.json)"
[ -s data/curriculum/leaf_bs2_s1.json ] || python3 scripts/build_leaf_subgoal_curriculum.py --idx-file "$TRAIN" --max-per-thm 2 --out data/curriculum/leaf_bs2.json >> "$LOG" 2>&1
idxof data/curriculum/leaf_bs2_s1.json > data/leaf_bs2_idx.txt
BI=data/leaf_bs2_idx.txt
say "  leaf 대상 정리: $(wc -l < "$BI")개"

# ─────────────── cascade 스테이지 (롤아웃 정책 = 각 init) ───────────────
lstage s1 data/curriculum/leaf_bs2 "$BI" "$SFTM"                              models/rango-grpo-cascade-s1 600
lstage s2 data/curriculum/leaf_bs2 "$BI" models/rango-grpo-cascade-s1/adapter models/rango-grpo-cascade-s2 600
lstage s3 data/curriculum/leaf_bs2 "$BI" models/rango-grpo-cascade-s2/adapter models/rango-grpo-cascade-s3 600

# ─────────────── s0: 완전체 root GRPO (롤아웃 정책=s3, on-policy) ───────────────
S3M=models/rango-grpo-cascade-s3/adapter
[ -f "$S3M/adapter_model.safetensors" ] || S3M=models/rango-grpo-cascade-s2/adapter
[ -f "$S3M/adapter_model.safetensors" ] || S3M=models/rango-grpo-cascade-s1/adapter
say "  ▶ [s0] root(완전체) rollout(정책=$(basename $(dirname $S3M)), Qed 보상)+GRPO(init=동일)"
export SUBGOAL_CURRICULUM=data/curriculum/empty.json SUBGOAL_OUT=data/grpo_rollouts/rango-grpo-cascade-s0.jsonl SUBGOAL_SKIP_S0=0 SUBGOAL_REWARD=0 SUBGOAL_POLICY="$S3M"
[ -s "$SUBGOAL_OUT" ] || python3 scripts/run_all.py --alias grpo-rollout-subgoal --idx-file "$TRAIN" --timeout 600 --gpus "$GPUS" --workers $ROLLW >> "$LOG" 2>&1
[ -f models/rango-grpo-cascade-s0/adapter/adapter_model.safetensors ] || gtrain "$SUBGOAL_OUT" "$S3M" models/rango-grpo-cascade-s0

# ─────────────── (옵션) HARVEST 라운드 — HARVEST_ROUND=1 일 때만 (기본 안 함) ───────────────
#   s0 실패(dead) 롤아웃에서 **모델 자신이 닫은 subgoal**을 추출(harvest) → 그걸 학습 → s0 한 번 더.
#   ★ on-policy(모델이 방문/생성/Coq가 닫음) = covariate-shift 없음(§3-B self-harvest / §6 OSR).
#   흐름: harvest(닫힌 subgoal 추출, reward=1) → RFT(--sft, reward=1이라 GRPO 아닌 순수 MLE) → s0 재롤아웃 → s0 GRPO.
if [ "$HARVEST_ROUND" = "1" ]; then
  say "════════ HARVEST 라운드 (s0 실패 롤아웃 → 닫힌 subgoal RFT → s0 재실행) ════════"
  S0M=models/rango-grpo-cascade-s0/adapter
  if [ ! -f "$S0M/adapter_model.safetensors" ]; then
    say "  ✗ s0 모델 없음 — harvest 라운드 스킵"
  else
    HARV=data/grpo_rollouts/rango-grpo-cascade-harvest.jsonl
    [ -s "$HARV" ] || python3 scripts/harvest_subgoals.py --rollouts data/grpo_rollouts/rango-grpo-cascade-s0.jsonl --dead_only --out "$HARV" >> "$LOG" 2>&1
    NH=$([ -s "$HARV" ] && wc -l < "$HARV" || echo 0)
    say "  harvest: 닫힌 subgoal $NH 그룹 (dead 그룹 출신)"
    if [ "$NH" -gt 0 ]; then
      # (1) gradient update = RFT: reward=1 트레이스 순수 MLE (--sft), init=s0 모델
      [ -f models/rango-grpo-cascade-harvest/adapter/adapter_model.safetensors ] || \
        python3 -m tactic_gen.grpo_train --rollouts "$HARV" --model_name "$BASE" --init_adapter "$S0M" \
          --collator_conf "$CONF" --max_len 3072 --save_dir models/rango-grpo-cascade-harvest/adapter \
          --sft --kl_beta 0.0 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1
      cpconf models/rango-grpo-cascade-harvest
      HM=models/rango-grpo-cascade-harvest/adapter
      # (2) s0 재롤아웃 (정책=harvest 모델, Qed 보상) → (3) s0 GRPO
      say "  ▶ [s0-r2] root 재롤아웃(정책=harvest 모델) + GRPO(init=동일)"
      export SUBGOAL_CURRICULUM=data/curriculum/empty.json SUBGOAL_OUT=data/grpo_rollouts/rango-grpo-cascade-s0r2.jsonl SUBGOAL_SKIP_S0=0 SUBGOAL_REWARD=0 SUBGOAL_POLICY="$HM"
      [ -s "$SUBGOAL_OUT" ] || python3 scripts/run_all.py --alias grpo-rollout-subgoal --idx-file "$TRAIN" --timeout 600 --gpus "$GPUS" --workers $ROLLW >> "$LOG" 2>&1
      [ -f models/rango-grpo-cascade-s0r2/adapter/adapter_model.safetensors ] || gtrain "$SUBGOAL_OUT" "$HM" models/rango-grpo-cascade-s0r2
      say "  harvest 라운드 완료 — 최종 = models/rango-grpo-cascade-s0r2"
    else
      say "  harvest 0개 — 라운드 스킵 (s0 모델 유지)"
    fi
  fi
fi

# 최종 모델 (harvest 라운드 결과 s0r2 우선, 없으면 s0 → …)
FINAL=models/rango-grpo-cascade-s0r2
[ -f "$FINAL/adapter/adapter_model.safetensors" ] || FINAL=models/rango-grpo-cascade-s0
[ -f "$FINAL/adapter/adapter_model.safetensors" ] || FINAL=models/rango-grpo-cascade-s3
[ -f "$FINAL/adapter/adapter_model.safetensors" ] || FINAL=models/rango-grpo-cascade-s2
[ -f "$FINAL/adapter/adapter_model.safetensors" ] || FINAL=models/rango-grpo-cascade-s1
FA=rango-grpo-${FINAL##*/rango-grpo-}
say "  최종 모델 = $FINAL (alias $FA)"

# ★ 평가 순서(사용자 지정): rand200@600s g2w4(=g2w4600s) 먼저 → 1191@120s g2w4
say "▶ [평가1/2] rand200 @600s g2w4 (옵션명 g2w4600s)"
NRAND=$(wc -l < "$RAND")
RD=all_results/rand200_cascade_g2w4600s
if [ ! -s "$RD/summary.json" ] || [ "$(python3 -c "import json;print(len(json.load(open('$RD/summary.json'))['results']))" 2>/dev/null||echo 0)" -lt "$NRAND" ]; then
  python3 scripts/run_all.py --alias "$FA" --idx-file "$RAND" --timeout 600 --gpus "$GPUS" --workers $EVALW \
    --out "$RD" --description "rand200 cascade g2w4600s" >> "$LOG" 2>&1
fi
SR=$(python3 -c "import json;r=json.load(open('$RD/summary.json'))['results'];print(f\"{sum(1 for x in r if x['success'])}/{len(r)}\")" 2>/dev/null || echo '?')
say "  [rand200 g2w4600s] cascade = $SR (참조 baseline 33.5% / SFT→GRPO 37.5% / subgoal ~40%)"

say "▶ [평가2/2] 1191 @120s g2w4"
teval "$FA" cascade
SG=$(python3 -c "import json;r=json.load(open('all_results/bs2_cascade_g2w4120s/summary.json'))['results'];print(sum(1 for x in r if x['success']))" 2>/dev/null || echo 0)
say "════════ CASCADE 결과 ════════"
say "  rand200@600s g2w4600s: $SR  (참조 baseline 33.5% / SFT→GRPO 37.5% / subgoal ~40%)"
say "  1191@120s g2w4: $SG/$NTEST  (참조 baseline 322 / GRPO 328 / SFT→GRPO 338)"
say "════════ 완료 ════════"
