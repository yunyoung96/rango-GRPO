#!/bin/bash
# 자가 교정(ERROR_REPAIR=1) ON 평가 — 같은 모델·같은 정리로 OFF(기존 69/200)와 비교.
#   Coq 에러 `Expects a disjunctive pattern with N branches` 를 보고 `as [|..|]`(빈 분기 N개)로
#   고쳐 즉시 재검증한다. 빈 분기는 Coq 이 인자를 자동 명명하므로 arity 를 몰라도 맞는다.
#   근거: 후보 '제거'(이름필터)는 탐색량 0.93배로 무효였다 → '올바른 후보 추가'가 유일한 유효 개입.
cd /app/coq-modeling || exit 1
set -u
exec 9>/tmp/.rango_eval.lock
flock -n 9 || { echo "다른 평가 실행 중 — 취소"; exit 1; }
CKPT=models/rango-1.3b-augmented-v2-ft/checkpoint-60000
TIMEOUT=${TIMEOUT:-600}; WPG=${WPG:-6}; TOTW=$((WPG*2)); TAG="g2xw${WPG}_tot${TOTW}"
OUT="all_results/v2_step60000_rand200_repair_t${TIMEOUT}_${TAG}"
LOG=all_log/eval_error_repair.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
say "===== 자가교정 ON 평가 (${TIMEOUT}s, ${TAG}) ====="
[ -s "$OUT/summary.json" ] && { say "이미 완료"; exit 0; }
HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
EXEC_ADAPTER="$CKPT" AUGMENT_V2=1 RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 \
HARD_SEQ_LEN=4096 TYPES_TOKENS=300 DEFS_TOKENS=300 FUNC_DEFS_PATH=data/func_defs.json \
ERROR_REPAIR=1 \
  python3 scripts/run_all.py --alias rango-grpo --idx-file data/compcert_bs2_rand200_idx.txt \
    --timeout "$TIMEOUT" --gpus 0,1 --workers "$WPG" --out "$OUT" \
    --description "v2 step60000 + error-repair (${TIMEOUT}s ${TAG})" >> "$LOG" 2>&1
ps -eo pid,cmd | grep "[t]actic_gen_server" | awk '{print $1}' | xargs -r kill -9 2>/dev/null
sleep 5
python3 - <<'PY' 2>&1 | tee -a "$LOG"
import glob, os, re
from math import comb
def load(d):
    out={}
    for f in glob.glob(os.path.join(d,"logs","*.txt")):
        try: i=int(os.path.basename(f)[:-4])
        except ValueError: continue
        t=open(f,errors="ignore").read()
        if "CURRENT RESULT: SUCCESS" in t: out[i]=True
        elif "\nfailed" in t: out[i]=False
    return out
on=load("all_results/v2_step60000_rand200_repair_t600_g2xw6_tot12")
off=load("all_results/v2_step60000_rand200_t600_g2xw6_tot12")
c=sorted(set(on)&set(off))
print(f"\n■ 자가교정 ON vs OFF (v2 step60000, 600s, g2×w6=12, 같은 정리 {len(c)}개)")
if c:
    a=sum(1 for i in c if on[i]); b=sum(1 for i in c if off[i])
    ao=sum(1 for i in c if on[i] and not off[i]); bo=sum(1 for i in c if off[i] and not on[i])
    n=ao+bo; k=min(ao,bo)
    p=(sum(comb(n,i) for i in range(k+1))*2/2**n) if n else 1.0
    print(f"   ON {a} ({a/len(c)*100:.1f}%)  OFF {b} ({b/len(c)*100:.1f}%)  차이 {a-b:+d} ({(a-b)/len(c)*100:+.1f}%p)")
    print(f"   ON만 {ao} | OFF만 {bo} | McNemar p ≈ {min(p,1):.3f}")
# 교정이 실제로 몇 번 성공했나
n_rep=sum(len(re.findall(r'→ \[교정\]', open(f,errors='ignore').read()))
          for f in glob.glob("all_results/v2_step60000_rand200_repair_t600_g2xw6_tot12/logs/*.txt"))
print(f"   교정 성공 횟수: {n_rep}회")
PY
say "===== 종료 ====="
