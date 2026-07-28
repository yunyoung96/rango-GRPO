#!/bin/bash
# ══════════════════════════════════════════════════════════════════════════════
# SFT→subgoal-GRPO (leaf-first subgoal 단위) — 사용자 최종 설계.
#   SFT(gold, rango-grpo-bs2-sft) 한 번 → **트리 leaf subgoal부터** rollout → GRPO → 위로.
#
# 핵심(remaining-거리·decompose-node 실패 교훈):
#   - subgoal 트리를 goal-수 궤적으로 복원, **각 subgoal 경계에서 seed**(중간 안 자름).
#   - **per-subgoal 보상**: focused subgoal 하나만 닫으면 reward=1(Qed 불필요, grpo_rollout subgoal_reward).
#     → decompose-node(subtree 전체 요구=dead)와 달리 첫 자식(쉬운 base case)만 풀어도 신호.
#   - **leaf-first 스테이징**: subgoal 크기로 s1(leaf,size≤2)→s2(≤5)→s3(나머지). remaining 숫자 불필요.
#   - SFT 초기화·롤아웃 정책 = rango-grpo-bs2-sft(on-policy, 이긴 SFT→GRPO 대응).
#
# 흐름: [bigscale] 300-train w1, leaf s1→s2→s3 rollout+GRPO → 1191@120s w2 → 좋으면 rand200 600s.
# ══════════════════════════════════════════════════════════════════════════════
set -u
LOG=all_log/subgoal.log
BASE=deepseek-ai/deepseek-coder-1.3b-instruct
SFTM=models/rango-grpo-bs2-sft/adapter        # ★ SFT(gold) 모델 = init·롤아웃 정책
CONF=models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/training_conf.yaml
TEST=data/compcert_bs2_test_idx.txt
RAND=data/compcert_bs2_rand200_idx.txt
TRAIN=data/compcert_bs2_train_idx.txt
NTEST=$(wc -l < "$TEST")
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
cpconf(){ cp models/rango-grpo/training_conf.yaml models/rango-grpo/lm-example-conf.yaml "$1/" 2>/dev/null; }
gtrain(){ python3 -m tactic_gen.grpo_train --rollouts "$1" --model_name "$BASE" --init_adapter "$2" \
    --collator_conf "$CONF" --max_len 3072 --save_dir "$3/adapter" \
    --kl_beta 0.04 --epochs 2 --lr 1e-6 --micro_bsz 2 >> "$LOG" 2>&1; cpconf "$3"; }
idxof(){ python3 -c "import json;print('\n'.join(str(v['idx']) for v in json.load(open('$1')).values()))"; }
teval(){ local d="all_results/bs2_$2_test120_w2/summary.json"; local n
  n=$([ -s "$d" ] && python3 -c "import json;print(len(json.load(open('$d'))['results']))" 2>/dev/null || echo 0)
  [ "$n" -ge "$NTEST" ] && { say "   $2 이미 완료($n)"; return 0; }
  python3 scripts/run_all.py --alias "$1" --idx-file "$TEST" --timeout 120 --workers 2 \
    --out "all_results/bs2_$2_test120_w2" --description "bs2 leafsubgoal $2" >> "$LOG" 2>&1; }
# leaf 스테이지: $1=stage(s1/s2/s3) $2=커리큘럼접두 $3=idx $4=init $5=save $6=RT
lstage(){ local ST=$1 PFX=$2 IDXF=$3 INIT=$4 SAVE=$5 RT=$6
  local CUR="${PFX}_${ST}.json" ROLL="data/grpo_rollouts/${SAVE##*/}_${ST}.jsonl"
  say "  ▶ [$SAVE] leaf-$ST rollout(per-subgoal 보상)+GRPO(init=$(basename $(dirname $INIT) 2>/dev/null || echo $INIT))"
  [ -s "$CUR" ] || { say "    ✗ $CUR 없음 — 스킵"; return 0; }
  export SUBGOAL_CURRICULUM="$CUR" SUBGOAL_OUT="$ROLL" SUBGOAL_SKIP_S0=1 SUBGOAL_REWARD=1
  [ -s "$ROLL" ] || python3 scripts/run_all.py --alias grpo-rollout-subgoal --idx-file "$IDXF" --timeout $RT --workers 2 >> "$LOG" 2>&1
  [ -f "$SAVE/adapter/adapter_model.safetensors" ] || gtrain "$ROLL" "$INIT" "$SAVE"; }

say "════════ SFT→subgoal-GRPO (leaf-first subgoal 단위, per-subgoal 보상) ════════"
[ -f "$SFTM/adapter_model.safetensors" ] || { say "✗ SFT 모델($SFTM) 없음 — 중단"; exit 1; }

# ─────────────── leaf 커리큘럼 빌드(300-train) ───────────────
say "▶ leaf 커리큘럼 빌드(300-train, 트리 subgoal 추출)"
[ -s data/curriculum/leaf_bs2_s1.json ] || python3 scripts/build_leaf_subgoal_curriculum.py --idx-file "$TRAIN" --max-per-thm 2 --out data/curriculum/leaf_bs2.json >> "$LOG" 2>&1
idxof data/curriculum/leaf_bs2_s1.json > data/leaf_bs2_idx.txt
say "  leaf-s1(가장 많은 정리) 대상: $(wc -l < data/leaf_bs2_idx.txt)개"
export SUBGOAL_POLICY="$SFTM"   # 롤아웃 정책 = SFT 모델(on-policy)
BI=data/leaf_bs2_idx.txt

# ─────────────── leaf-first 스테이지 (deep leaf → 위로), SFT 초기화 ───────────────
lstage s1 data/curriculum/leaf_bs2 "$BI" "$SFTM"                          models/rango-grpo-subgoal-bs2-s1 600
lstage s2 data/curriculum/leaf_bs2 "$BI" models/rango-grpo-subgoal-bs2-s1/adapter models/rango-grpo-subgoal-bs2-s2 600
lstage s3 data/curriculum/leaf_bs2 "$BI" models/rango-grpo-subgoal-bs2-s2/adapter models/rango-grpo-subgoal-bs2    600

# ─────────────── s0 스테이지: prefix 없는 완전체 정리 GRPO (root, SFT→GRPO와 동일 학습) ───────────────
#   subgoal(s1~s3) 부트스트랩 위에서, 이제 s0(정리 statement만, gold prefix 없음, Qed 보상)로 완전체를 풀게.
#   → SFT→GRPO 처럼 root 를 직접 학습. 커리큘럼 없음(empty)→s0 그룹만, skip_s0=0, subgoal_reward=0(Qed).
S3M=models/rango-grpo-subgoal-bs2/adapter
[ -f "$S3M/adapter_model.safetensors" ] || S3M=models/rango-grpo-subgoal-bs2-s2/adapter
[ -f "$S3M/adapter_model.safetensors" ] || S3M=models/rango-grpo-subgoal-bs2-s1/adapter
say "  ▶ [s0] root(prefix 없는 완전체 정리) rollout(Qed 보상) + GRPO(init=$(basename $(dirname $S3M)))"
export SUBGOAL_CURRICULUM=data/curriculum/empty.json SUBGOAL_OUT=data/grpo_rollouts/rango-grpo-subgoal-bs2-s0.jsonl SUBGOAL_SKIP_S0=0 SUBGOAL_REWARD=0 SUBGOAL_POLICY="$S3M"
[ -s "$SUBGOAL_OUT" ] || python3 scripts/run_all.py --alias grpo-rollout-subgoal --idx-file "$TRAIN" --timeout 600 --workers 2 >> "$LOG" 2>&1
[ -f models/rango-grpo-subgoal-bs2-s0/adapter/adapter_model.safetensors ] || gtrain "$SUBGOAL_OUT" "$S3M" models/rango-grpo-subgoal-bs2-s0

# 최종 모델: s0(root 학습) 우선, 없으면 s3→s2→s1
FINAL=models/rango-grpo-subgoal-bs2-s0
[ -f "$FINAL/adapter/adapter_model.safetensors" ] || FINAL=models/rango-grpo-subgoal-bs2
[ -f "$FINAL/adapter/adapter_model.safetensors" ] || FINAL=models/rango-grpo-subgoal-bs2-s2
[ -f "$FINAL/adapter/adapter_model.safetensors" ] || FINAL=models/rango-grpo-subgoal-bs2-s1
FA=rango-grpo-${FINAL##*/rango-grpo-}   # 서빙 alias 이름
say "  최종 모델 = $FINAL (alias $FA)"

# ★ 평가 순서 (사용자 지정, 뒤집음): 먼저 rand200@600s → 그 다음 1191@120s.
say "▶ [평가1/2] rand200 @600s w2 (먼저)"
NRAND=$(wc -l < "$RAND")
RD=all_results/rand200_leafsubgoal_test600_w2
if [ ! -s "$RD/summary.json" ] || [ "$(python3 -c "import json;print(len(json.load(open('$RD/summary.json'))['results']))" 2>/dev/null||echo 0)" -lt "$NRAND" ]; then
  python3 scripts/run_all.py --alias "$FA" --idx-file "$RAND" --timeout 600 --workers 2 \
    --out "$RD" --description "rand200 leafsubgoal 600s" >> "$LOG" 2>&1
fi
SR=$(python3 -c "import json;r=json.load(open('$RD/summary.json'))['results'];print(f\"{sum(1 for x in r if x['success'])}/{len(r)}\")" 2>/dev/null || echo '?')
say "  [rand200 600s] leaf-subgoal = $SR (참조 baseline 33.5% / SFT→GRPO 37.5%)"

say "▶ [평가2/2] 1191 @120s w2"
teval "$FA" leafsubgoal
SG=$(python3 -c "import json;r=json.load(open('all_results/bs2_leafsubgoal_test120_w2/summary.json'))['results'];print(sum(1 for x in r if x['success']))" 2>/dev/null || echo 0)
say "════════ SFT→subgoal-GRPO(leaf) bigscale 결과 ════════"
say "  rand200@600s: $SR  (참조 baseline 33.5% / SFT→GRPO 37.5%)"
say "  1191@120s: $SG/$NTEST  (참조 baseline 322 / GRPO 328 / SFT→GRPO 338)"
say "════════ 완료 ════════"
