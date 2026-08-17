#!/bin/bash
# 순차 큐: ① 진행중 zero-shot(w4) 5종 완주 대기 → ② 프로브 796 전항목(32B 포함)
#          → ③ A안: 32B + Qwen7B 를 **둘 다 w1** 으로 zero-shot (공정 대조)
#
# A안을 w1 으로 하는 이유: 32B bf16 은 워커당 ~65GB 라 한 장에 1개만 올라간다.
#   w1 은 CPU 경합이 없어 600초 안에 탐색이 더 들어가므로 w4 결과와 직접 비교하면 안 된다.
#   → 대조군 Qwen7B 도 같은 w1 으로 돌려 **w1 끼리** 비교한다.
cd /app/coq-modeling || exit 1
set -u
LOG=all_log/chain_after_zeroshot.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }
say "===== 큐 시작 ====="

# ── ① 진행중 실행 완주 대기 ──
say "① zero-shot(w4) 5종 완주 대기"
while pgrep -f "eval_zeroshot_last50.sh" > /dev/null; do sleep 60; done
sleep 30
for p in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader); do kill -9 "$p" 2>/dev/null; done
sleep 10
say "① 완료 — 결과:"
for m in nosft-qwen7b nosft-ds1.3b nosft-prover nosft-qwen3b v2-sft-step60000; do
  D=$(ls -d all_results/zeroshot_last50_${m}_* 2>/dev/null | head -1)
  [ -f "$D/summary.json" ] && python3 -c "
import json;d=json.load(open('$D/summary.json'))
print(f\"   {'$m':22s} {d['success']:2d}/{d['done']:2d} = {d['success']/max(d['done'],1)*100:5.1f}%\")" | tee -a "$LOG"
done

# ── ② 프로브 796 전항목 ──
say "② 프로브 재실행 (표본 796, Bonferroni 보정, 32B 포함)"
N=796 nohup bash all_log/probe_rerun.sh 0 all_log/probe796_g0.log \
  "Qwen/Qwen2.5-Coder-32B-Instruct" > /dev/null 2>&1 &
P0=$!
N=796 nohup bash all_log/probe_rerun.sh 1 all_log/probe796_g1.log \
  "deepseek-ai/deepseek-coder-1.3b-instruct" "Qwen/Qwen2.5-Coder-1.5B-Instruct" \
  "Qwen/Qwen2.5-Coder-3B-Instruct" "deepseek-ai/deepseek-coder-6.7b-instruct" \
  "Qwen/Qwen2.5-Coder-7B-Instruct" "deepseek-ai/DeepSeek-Prover-V1.5-RL" > /dev/null 2>&1 &
P1=$!
wait $P0 $P1
for p in $(nvidia-smi --query-compute-apps=pid --format=csv,noheader); do kill -9 "$p" 2>/dev/null; done
sleep 10
say "② 완료 (결과: all_log/probe796_g0.log, all_log/probe796_g1.log)"

# ── ③ A안: 32B + Qwen7B, 둘 다 w1 ──
say "③ A안 시작 — 32B(GPU0,w1) + Qwen7B(GPU1,w1). 정리당 600초 × 50개 = 최대 8.3시간"
W=1 nohup bash all_log/eval_zeroshot_last50.sh 0 nosft-qwen32b > /dev/null 2>&1 &
sleep 5
W=1 nohup bash all_log/eval_zeroshot_last50.sh 1 nosft-qwen7b-w1 models/nosft-qwen7b/base 1 > /dev/null 2>&1 &
while pgrep -f "eval_zeroshot_last50.sh" > /dev/null; do sleep 120; done
say "③ 완료 — A안 결과:"
for m in nosft-qwen32b nosft-qwen7b-w1; do
  D=$(ls -d all_results/zeroshot_last50_${m}_* 2>/dev/null | head -1)
  [ -f "$D/summary.json" ] && python3 -c "
import json;d=json.load(open('$D/summary.json'))
print(f\"   {'$m':22s} {d['success']:2d}/{d['done']:2d} = {d['success']/max(d['done'],1)*100:5.1f}%\")" | tee -a "$LOG"
done
say "===== 큐 전체 완료 ====="
