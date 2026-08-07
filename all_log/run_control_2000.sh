#!/bin/bash
# 통제군 2000 step → 끝나면 본 학습 자동 재개.
#   증강(재랭킹/[TYPES]/[DEFINITIONS])만 끄고 나머지는 본 학습과 동일 — 같은 코퍼스·같은 셔플 순서·
#   같은 초기값(base + 새 LoRA)·같은 하이퍼파라미터. 그래야 첫 2000 step loss 를 직접 비교할 수 있다.
cd /app/coq-modeling || exit 1
set -u
LOG=all_log/control_2000.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "===== 통제군(증강 OFF) 2000 step ====="
STEP=$(tr '\r' '\n' < all_log/ft_rango_augmented.log | grep -aoE "[0-9]+/60000" | tail -1)
say "본 학습 정지 (현재 $STEP, 최신 체크포인트에서 재개 예정)"
pkill -9 -f ft_rango_augmented 2>/dev/null
pkill -9 -f train_decoder.py 2>/dev/null
sleep 20
rm -rf models/rango-1.3b-control-ft
say "GPU 정리: $(nvidia-smi --query-gpu=memory.used --format=csv,noheader | tr '\n' ' ')"

say "통제군 학습 시작 (RERANK=0 INJECT_TYPES=0 INJECT_DEFS=0)"
HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src \
RERANK_PREMISES=0 INJECT_TYPES=0 INJECT_DEFS=0 DYNAMIC_PADDING=1 \
  torchrun --nproc_per_node=2 --master_port=$((29500 + RANDOM % 400)) \
    src/tactic_gen/train_decoder.py all_log/ft_rango_control_conf.yaml >> "$LOG" 2>&1
say "통제군 종료(rc=$?)"

python3 - <<'PY' 2>&1 | tee -a "$LOG"
import re, statistics, json
def load(path, pat=r"'loss': '([0-9.e-]+)'"):
    t=open(path,errors='ignore').read().replace('\r','\n')
    return [float(x) for x in re.findall(pat, t)]
ctl=load('all_log/control_2000.log')
aug=load('all_log/ft_rango_augmented.log')
st=json.load(open('models/deepseek-bm25-proof-tfidf-proj-thm-prem-final/checkpoint-60000/trainer_state.json'))
rango=[x['loss'] for x in st['log_history'] if 'loss' in x and x['step']<=2000]
n=min(len(ctl), 100)   # 2000 step = 로그 100개(logging_steps 20)
print("\n■ 첫 2000 step 평균 loss 비교 (같은 데이터·같은 순서)")
print(f"   증강 ON  (우리 본학습) : {statistics.mean(aug[:n]):.4f}")
print(f"   증강 OFF (통제군)      : {statistics.mean(ctl[:n]):.4f}")
print(f"   원본 rango(전처리 DB)  : {statistics.mean(rango):.4f}")
d=statistics.mean(aug[:n])-statistics.mean(ctl[:n])
print(f"\n   증강의 순효과(ON-OFF): {d:+.4f}")
print("   · OFF 가 원본(0.80)에 가까우면 → 격차 원인은 **증강**")
print("   · OFF 도 ON 과 비슷하면    → 원인은 **파이프라인**(검색 등), 증강 무죄")
PY

say "본 학습 재개"
setsid nohup bash all_log/ft_rango_augmented_v2.sh > /dev/null 2>&1 < /dev/null &
sleep 150
say "재개 확인: $(tr '\r' '\n' < all_log/ft_rango_augmented.log | grep -aoE '[0-9]+/60000 \[[0-9:]+<[0-9:]+' | tail -1)"
say "===== 완료 ====="
