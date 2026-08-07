#!/bin/bash
# checkpoint-1000 이 저장되면 → 학습을 **동적 패딩**(v2)으로 갈아탄다. 진행분 손실 0(그 체크포인트에서 재개).
#
# 왜: LmDataset 이 모든 예제를 hard_seq_len(4096)까지 패딩하는데 실제 프롬프트 중앙은 ~1700 토큰이라
#     연산의 절반 이상이 패딩이다. pad 는 attention_mask/label(-100) 로 제외되므로 **수학적으로 동일**,
#     속도만 개선된다. 실측 6.4 s/step(=60000 step 4.4일) → 개선 기대.
# 안전장치: 전환 후 속도가 나아지지 않으면 사람이 v1(all_log/ft_rango_augmented.sh)로 되돌리면 된다.
cd /app/coq-modeling || exit 1
OUT=models/rango-1.3b-augmented-ft
LOG=all_log/switch_dynpad.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "===== checkpoint-1000 대기(동적 패딩 전환) ====="
while [ ! -f "$OUT/checkpoint-1000/trainer_state.json" ]; do
  sleep 60
  if ! pgrep -f "train_decoder.py|ft_rango_augmented" >/dev/null; then
    say "★ 학습이 멈춰 있음 — 전환 취소(수동 확인 필요)"; exit 1
  fi
done
say "checkpoint-1000 확보"

# 전환 전 속도 기록(비교용)
BEFORE=$(tr '\r' '\n' < all_log/ft_rango_augmented.log | grep -aoE "[0-9]+/60000 \[[0-9:]+<[0-9:]+" | tail -1)
say "전환 전 진행: $BEFORE"

pkill -9 -f ft_rango_augmented.sh 2>/dev/null
pkill -9 -f train_decoder.py 2>/dev/null
sleep 15
say "동적 패딩(v2)으로 재개 — checkpoint-1000 에서 이어서"
setsid nohup bash all_log/ft_rango_augmented_v2.sh > /dev/null 2>&1 < /dev/null &
sleep 600
AFTER=$(tr '\r' '\n' < all_log/ft_rango_augmented.log | grep -aoE "[0-9]+/60000 \[[0-9:]+<[0-9:]+" | tail -1)
say "전환 후 진행: $AFTER  (ETA 가 줄었으면 성공)"
say "===== 전환 완료 ====="
