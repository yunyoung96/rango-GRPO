#!/bin/bash
# "우리만 푼 4개"가 정말 [TYPES]/[DEFINITIONS] 덕분인지 가리는 ablation.
#
# 설계: 같은 체크포인트·같은 정리·같은 timeout 으로 두 조건만 비교한다.
#   A(full)    : [TYPES]/[DEFINITIONS] 내용 그대로            ← 대조군(재현성 확인 겸함)
#   B(ablated) : 섹션 **헤더는 유지**하고 내용만 '(none)'      ← 정보만 제거
#   ※ 헤더를 유지하는 이유: INJECT_*=0 으로 끄면 프롬프트 포맷이 학습과 달라져(OOD) 성능이 떨어져도
#     "정보가 필요했다"는 증거가 되지 못한다. 포맷 고정이 핵심.
#   ※ 탐색에 무작위성이 있으면 1회 실행으로는 단정 못 한다 → A 를 재실행해 재현되는지도 같이 본다.
cd /app/coq-modeling || exit 1
set -u
CKPT=${CKPT:-models/rango-1.3b-augmented-ft/checkpoint-21000}
IDXF=/tmp/ablation_idx.txt
# 우리만 푼 정리(rand200 진행 중 발견된 것 전부)
printf "360\n467\n700\n702\n1327\n1344\n" > "$IDXF"
TIMEOUT=${TIMEOUT:-600}
WPG=${WPG:-2}
LOG=all_log/ablation_only_ours.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

run_cond(){   # $1=이름  $2=ABLATE_TYPES  $3=ABLATE_DEFS
  # ※ local 한 줄에 몰아 쓰면 인자 확장 시점에 ${name} 이 아직 없어 set -u 에서 죽는다(실측) → 분리
  local name=$1
  local at=$2
  local ad=$3
  local out="all_results/ablation_${name}"
  say "  조건 $name (ABLATE_TYPES=$at ABLATE_DEFS=$ad) 시작"
  rm -rf "$out"
  HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
  EXEC_ADAPTER="$CKPT" RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 \
  ABLATE_TYPES=$at ABLATE_DEFS=$ad \
  IND_INDEX_PATH=data/ind_constructors_clean.json TYPES_TOKENS=200 \
  FUNC_DEFS_PATH=data/func_defs.json DEFS_TOKENS=200 DEFS_MAX=5 DEFS_MAX_BODY=80 DEFS_MAX_SIG=40 \
    python3 scripts/run_all.py --alias rango-grpo --idx-file "$IDXF" \
      --timeout "$TIMEOUT" --gpus 0,1 --workers "$WPG" --out "$out" \
      --description "ablation $name" >> "$LOG" 2>&1
  pkill -9 -f 'tactic_gen_server.py' 2>/dev/null
  sleep 5
}

say "===== ablation: 우리만 푼 6개(360,467,700,702,1327,1344) ====="
say "대상: $CKPT   timeout ${TIMEOUT}s"

# rand200 이 아직 돌면 끝날 때까지 대기(GPU 경합 방지)
while pgrep -f "run_all.py .*rand200" >/dev/null || pgrep -f pause_eval_resume >/dev/null; do sleep 60; done
say "rand200 종료 확인 — ablation 시작"

run_cond full     0 0
run_cond ablated  1 1

python3 - <<'PY' 2>&1 | tee -a "$LOG"
import json, glob, os
def res(d):
    out={}
    for f in glob.glob(f'all_results/{d}/logs/*.txt'):
        i=int(os.path.basename(f)[:-4]); t=open(f,errors='ignore').read()
        out[i] = 'CURRENT RESULT: SUCCESS' in t
    return out
a, b = res('ablation_full'), res('ablation_ablated')
print("\n■ ablation 결과 (같은 체크포인트·같은 정리·timeout 600s)")
print(f"{'정리':>6} {'full(주입O)':>12} {'ablated(내용비움)':>18}")
for i in sorted(set(a) | set(b)):
    f = '성공' if a.get(i) else ('실패' if i in a else '-')
    g = '성공' if b.get(i) else ('실패' if i in b else '-')
    print(f"{i:>6} {f:>12} {g:>18}")
print(f"\n  full {sum(a.values())}/{len(a)}   ablated {sum(b.values())}/{len(b)}")
print("  해석: full 에서 재현되고 ablated 에서 실패 → 주입 정보가 실제로 기여했다는 직접 증거.")
print("        둘 다 성공 → 그 정리는 주입 없이도 풀린다(= 증강 공로 아님).")
print("        full 에서도 실패 → 탐색 무작위성 → 이 정리로는 판정 불가.")
PY
say "===== ablation 종료 ====="
