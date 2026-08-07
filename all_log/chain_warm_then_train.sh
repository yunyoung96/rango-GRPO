#!/bin/bash
# ExampleCache 워밍 완료 → 사전점검 → rango-1.3B augmented 완전 재학습(60k step, GPU 2개) 자동 체인.
#   워밍이 2~3시간 걸리므로 사람이 지키고 있지 않아도 바로 이어지게 한다.
cd /app/coq-modeling || exit 1
LOG=all_log/chain_warm_then_train.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "===== 체인 시작: 워밍 대기 → 사전점검 → 학습 ====="

# ── 1) 워밍 완료 대기 ──
while pgrep -f warm_example_cache >/dev/null; do sleep 60; done
if ! grep -qa "완료:" all_log/warm_cache.log; then
  say "★ 워밍이 비정상 종료됨 — 재시도 1회"
  HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src PYTHONUNBUFFERED=1 \
    python3 scripts/warm_example_cache.py all_log/ft_rango_augmented_conf.yaml 30 >> all_log/warm_cache.log 2>&1
  grep -qa "완료:" all_log/warm_cache.log || { say "★ 워밍 재시도도 실패 — 중단"; exit 1; }
fi
say "워밍 완료: $(grep -a '완료:' all_log/warm_cache.log | tail -1)"

# ── 2) 사전점검(GO/NO-GO) ──
say "사전점검 실행"
HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONPATH=src PYTHONUNBUFFERED=1 N_SAMPLE=20 \
RERANK_PREMISES=1 INJECT_TYPES=1 INJECT_DEFS=1 IND_INDEX_PATH=data/ind_constructors_clean.json TYPES_TOKENS=200 \
FUNC_DEFS_PATH=data/func_defs.json DEFS_TOKENS=200 DEFS_MAX=5 DEFS_MAX_BODY=80 DEFS_MAX_SIG=40 \
  python3 scripts/preflight_ft_augmented.py all_log/ft_rango_augmented_conf.yaml > all_log/preflight.log 2>&1
if ! grep -qa "★ GO" all_log/preflight.log; then
  say "★ 사전점검 NO-GO — 학습 시작 안 함. all_log/preflight.log 확인"
  grep -a "✗" all_log/preflight.log | tee -a "$LOG"
  exit 1
fi
say "사전점검 GO: $(grep -aE '프롬프트 토큰|주입률' all_log/preflight.log | tr '\n' ' ')"

# ── 3) 학습 시작(60k step, GPU 2개 DDP, 1000 저장/5000 배수 보존, 죽으면 자동 재개) ──
say "학습 시작 → all_log/ft_rango_augmented.log"
bash all_log/ft_rango_augmented.sh
say "===== 체인 종료 ====="
