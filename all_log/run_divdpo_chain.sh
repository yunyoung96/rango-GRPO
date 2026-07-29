#!/bin/bash
# safe-EI 최종 eval 완료 감지 → GPU1 확보(orchestrator/R3 정지) → divergence-DPO 학습+평가.
#   ★GPU1 전용. R3 재개는 보류(부분결과 rand200_ei_r3_w2 보존). 사용자 지정: "테스트 끝나면 바로 학습".
set -u
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] [chain] $*" | tee -a all_log/divdpo.log; }

say "safe-EI 최종 eval(200/200) 완료 대기..."
while true; do
  d=$(python3 -c "import json;print(len(json.load(open('all_results/rand200_eisafe_best_w2/summary.json')).get('results',[])))" 2>/dev/null || echo 0)
  [ "${d:-0}" -ge 200 ] && break
  sleep 300
done
say "safe-EI eval 완료 → orchestrator/R3 정지(GPU1 확보). R3 재개 보류."
for p in $(pgrep -f '[r]un_ei_safe'); do kill "$p" 2>/dev/null; done
sleep 3
for p in $(pgrep -f '[r]un_all\.py'); do kill "$p" 2>/dev/null; done
sleep 3
for p in $(pgrep -f '[t]actic_gen_server\.py'); do kill -9 "$p" 2>/dev/null; done
sleep 4
say "GPU 상태: $(nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader | tr '\n' ' | ')"
say "→ divergence-DPO 학습 시작 (GPU1 전용)"
bash all_log/run_divdpo.sh
say "완료"
