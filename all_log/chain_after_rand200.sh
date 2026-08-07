#!/bin/bash
# rand200 종료 → (학습 재개 차단) → ablation → 학습 재개.  순서 보장이 목적.
#   pause_eval_resume.sh 는 rand200 이 끝나면 곧바로 학습을 재개하는데, 그러면 ablation 이 학습과
#   GPU/CPU 를 나눠 쓰게 된다. ablation 은 600초 timeout 안의 탐색량이 결과를 좌우하므로 경합이 있으면
#   "full 조건인데 실패" 같은 잡음이 생긴다 → 그래서 ablation 이 끝난 뒤에 학습을 재개한다.
cd /app/coq-modeling || exit 1
LOG=all_log/chain_after_rand200.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "===== rand200 종료 대기 → ablation → 학습 재개 ====="

# 1) rand200 종료 대기
while pgrep -f "run_all.py .*rand200" >/dev/null; do sleep 30; done
say "rand200 종료 감지"
D=all_results/rango_aug_step21000_rand200_t600_w16
S=$(grep -al "CURRENT RESULT: SUCCESS" $D/logs/*.txt 2>/dev/null | wc -l)
T=$(ls $D/logs 2>/dev/null | wc -l)
say "rand200 최종: 성공 $S / 로그 $T"

# 2) 학습 재개 차단(아직 재개 전이면 그 단계를 막고, 이미 재개됐으면 중지)
pkill -9 -f pause_eval_resume 2>/dev/null
sleep 3
pkill -9 -f ft_rango_augmented 2>/dev/null
pkill -9 -f train_decoder.py 2>/dev/null
pkill -9 -f tactic_gen_server 2>/dev/null
sleep 15
say "GPU 정리 완료: $(nvidia-smi --query-gpu=memory.used --format=csv,noheader | tr '\n' ' ')"

# 3) ablation (GPU 독점)
say "ablation 시작"
bash all_log/ablation_only_ours.sh >> "$LOG" 2>&1
say "ablation 종료"

# 4) 학습 재개
say "학습 재개 (최신 정상 체크포인트에서)"
setsid nohup bash all_log/ft_rango_augmented_v2.sh > /dev/null 2>&1 < /dev/null &
sleep 180
say "재개 확인: $(tr '\r' '\n' < all_log/ft_rango_augmented.log | grep -aoE '[0-9]+/60000 \[[0-9:]+<[0-9:]+' | tail -1)"
say "===== 전체 종료 ====="
