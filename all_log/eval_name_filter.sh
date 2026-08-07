#!/bin/bash
# 우선순위 14 (제약 디코딩)의 **경량 1단계** — 환각 lemma 이름 후보를 Coq 전에 버린다.
#   MGD 처럼 토큰 마스킹까지 가지 않고, 생성된 후보를 문자열로 판정해 버리는 방식.
#   학습 불필요·즉시 적용 가능하고, 효과가 확인되면 그때 토큰 마스킹으로 승급한다.
#
# 근거(rand200, v2 step60000 실측):
#   INVALID 7,981건 중 '이름 못 찾음' 3,613(45.3%), 그중 코퍼스에 아예 없는 이름 2,810(77.8%).
#   필터 오프라인 검증: INVALID 의 23.4% 선제 차단, 유효후보 손실 0.32%(allow=∅ 최악값).
#
# 비교: 같은 모델(v2 step60000)·같은 정리·같은 조건에서 필터 ON/OFF 만 다르게.
#   OFF 는 이미 있음 → all_results/v2_step60000_rand200_t600_g2xw6_tot12 (69/200)
cd /app/coq-modeling || exit 1
set -u
exec 9>/tmp/.rango_eval.lock
flock -n 9 || { echo "다른 평가 실행 중 — 취소"; exit 1; }

CKPT=models/rango-1.3b-augmented-v2-ft/checkpoint-60000
RAND=data/compcert_bs2_rand200_idx.txt
TIMEOUT=${TIMEOUT:-600}
WPG=${WPG:-6}; TOTW=$((WPG*2)); TAG="g2xw${WPG}_tot${TOTW}"
OUT="all_results/v2_step60000_rand200_namefilter_t${TIMEOUT}_${TAG}"
LOG=all_log/eval_name_filter.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "===== 이름필터 ON 평가 (${TIMEOUT}s, ${TAG}) ====="
[ -s "$OUT/summary.json" ] && { say "이미 완료 — 종료"; exit 0; }

HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
EXEC_ADAPTER="$CKPT" AUGMENT_V2=1 RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 \
HARD_SEQ_LEN=4096 TYPES_TOKENS=300 DEFS_TOKENS=300 FUNC_DEFS_PATH=data/func_defs.json \
FILTER_UNKNOWN_NAMES=1 KNOWN_NAMES_PATH=data/known_names.json \
  python3 scripts/run_all.py --alias rango-grpo --idx-file "$RAND" \
    --timeout "$TIMEOUT" --gpus 0,1 --workers "$WPG" --out "$OUT" \
    --description "v2 step60000 + name-filter (${TIMEOUT}s ${TAG})" >> "$LOG" 2>&1
ps -eo pid,cmd | grep "[t]actic_gen_server" | awk '{print $1}' | xargs -r kill -9 2>/dev/null
sleep 5

python3 - <<'PY' 2>&1 | tee -a "$LOG"
import glob, os
def load(d):
    out={}
    for f in glob.glob(os.path.join(d,"logs","*.txt")):
        try: i=int(os.path.basename(f)[:-4])
        except ValueError: continue
        t=open(f,errors="ignore").read()
        if "CURRENT RESULT: SUCCESS" in t: out[i]=True
        elif "\nfailed" in t: out[i]=False
    return out
on=load("all_results/v2_step60000_rand200_namefilter_t600_g2xw6_tot12")
off=load("all_results/v2_step60000_rand200_t600_g2xw6_tot12")
c=sorted(set(on)&set(off))
print(f"\n■ 이름필터 ON vs OFF  (v2 step60000, 600s, g2×w6=12, 같은 정리 {len(c)}개)")
if c:
    a=sum(1 for i in c if on[i]); b=sum(1 for i in c if off[i])
    ao=sum(1 for i in c if on[i] and not off[i]); bo=sum(1 for i in c if off[i] and not on[i])
    from math import comb
    n=ao+bo; k=min(ao,bo)
    p=(sum(comb(n,i) for i in range(k+1))*2/2**n) if n else 1.0
    print(f"   ON  {a} ({a/len(c)*100:.1f}%)   OFF {b} ({b/len(c)*100:.1f}%)   차이 {a-b:+d} ({(a-b)/len(c)*100:+.1f}%p)")
    print(f"   ON만 {ao} | OFF만 {bo} | McNemar p ≈ {min(p,1):.3f}")
PY
say "===== 종료 ====="
