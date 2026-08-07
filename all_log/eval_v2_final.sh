#!/bin/bash
# v2 학습 완주 → rand200 최종 평가 (기준선과 **동일 조건**: 600초 · 워커 2).
#   기준선 all_results/rand200_baseline_test600_w2 = 67/200 = 33.5% (600s, w2)
#   ★ 워커 수는 confound 다(CPU 경합으로 600초 안의 탐색량이 달라짐). 중간평가는 w16 이었으므로
#     기준선과 직접 비교하려면 반드시 w2 로 재야 한다 — 이 스크립트가 그 역할.
#   ★ 평가 env 는 학습과 동일해야 한다(AUGMENT_V2 포함). 다르면 train/infer 불일치(OOD)로
#     성능이 실제보다 낮게 나온다.
cd /app/coq-modeling || exit 1
set -u
OUTM=models/rango-1.3b-augmented-v2-ft
RAND=data/compcert_bs2_rand200_idx.txt
TIMEOUT=${TIMEOUT:-600}
WPG=${WPG:-1}                      # GPU 당 워커 1 × 2GPU = 2 (기준선과 동일)
RESULT=all_results/rango_v2_final_rand200_t${TIMEOUT}_w$((WPG*2))
LOG=all_log/eval_v2_final.log
GRACE=${GRACE:-60}                 # 60분 연속 부재 = 학습 실패로 간주
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "===== v2 완주 대기 → rand200 최종평가(${TIMEOUT}s, 워커 $((WPG*2))) ====="

# ── 1) 완주 대기 (AUGMENT.json = 학습 rc=0 일 때만 생성되는 완료 표식) ──
gone=0
while [ ! -f "$OUTM/AUGMENT.json" ]; do
  sleep 60
  if pgrep -f "train_decoder.py|run_augmented_v2|v2_watchdog" >/dev/null; then
    gone=0
  else
    gone=$((gone + 1))
    say "  학습 프로세스 안 보임 ($gone/$GRACE) — 재시작 중일 수 있어 대기"
    [ "$gone" -ge "$GRACE" ] && { say "★ $GRACE 분 연속 부재 — 평가 중단(수동 확인 필요)"; exit 1; }
  fi
done
say "v2 완주 감지"

# ── 2) 평가할 체크포인트 = 최신 정상본 ──
CKPT=""
for d in $(ls -d "$OUTM"/checkpoint-* 2>/dev/null | sed 's/.*checkpoint-//' | sort -rn); do
  p="$OUTM/checkpoint-$d"
  [ -f "$p/adapter_model.safetensors" ] && { CKPT="$p"; break; }
done
[ -n "$CKPT" ] || { say "★ 평가할 체크포인트 없음 — 중단"; exit 1; }
say "평가 대상: $CKPT"

# 감시견 정지(평가 중 학습을 되살려 GPU 를 뺏지 않도록)
pkill -9 -f v2_watchdog.sh 2>/dev/null
sleep 5

# ── 3) rand200 ──
say "rand200 시작 (200정리, ${TIMEOUT}s, GPU 0,1 × 워커 $WPG)"
HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
EXEC_ADAPTER="$CKPT" \
AUGMENT_V2=1 RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 \
HARD_SEQ_LEN=4096 TYPES_TOKENS=300 DEFS_TOKENS=300 FUNC_DEFS_PATH=data/func_defs.json \
  python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" \
    --timeout "$TIMEOUT" --gpus 0,1 --workers "$WPG" --out "$RESULT" \
    --description "rango-augmented v2 final rand200 (600s w$((WPG*2)))" >> "$LOG" 2>&1
ps -eo pid,cmd | grep "[t]actic_gen_server" | awk '{print $1}' | xargs -r kill -9 2>/dev/null
sleep 5

# ── 4) 결과 + 기준선 대비 ──
python3 - <<'PY' 2>&1 | tee -a "$LOG"
import glob, json, os
D = "all_results/rango_v2_final_rand200_t600_w2/logs"
cur = {}
for f in glob.glob(D + "/*.txt"):
    i = int(os.path.basename(f)[:-4]); t = open(f, errors="ignore").read()
    if "CURRENT RESULT: SUCCESS" in t: cur[i] = True
    elif "\nfailed" in t: cur[i] = False
base = {int(x["idx"]): bool(x["success"])
        for x in json.load(open("all_results/rand200_baseline_test600_w2/summary.json"))["results"]}
ok = sum(cur.values()); n = len(cur)
print(f"\n■ v2 최종 rand200 (600s, 워커 2 — 기준선과 동일 조건)")
print(f"   성공 {ok}/{n} = {ok/max(n,1)*100:.1f}%")
c = [i for i in cur if i in base]
if c:
    o = sum(1 for i in c if cur[i]); b = sum(1 for i in c if base[i])
    both = sum(1 for i in c if cur[i] and base[i])
    oo = sum(1 for i in c if cur[i] and not base[i])
    bo = sum(1 for i in c if base[i] and not cur[i])
    u = both + oo + bo
    print(f"\n■ 같은 정리 {len(c)}개 비교")
    print(f"   v2      {o} ({o/len(c)*100:.1f}%)")
    print(f"   기준선  {b} ({b/len(c)*100:.1f}%)")
    print(f"   v2만 {oo} | 기준선만 {bo} | 둘다 {both} | 합집합 {u} ({u/len(c)*100:.1f}%) | Jaccard {both/max(u,1)*100:.1f}%")
print(f"\n■ 참고: v1 step21k 25.2% | v1 step40k 31.7% (둘 다 w16) | 기준선 33.5% (w2)")
PY
say "===== v2 최종평가 종료 ====="
