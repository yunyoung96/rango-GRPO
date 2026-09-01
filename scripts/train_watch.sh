#!/bin/bash
# ★ v11 본학습 감시자 — 10분마다: 프로세스 생존·최근 loss·샘플 EM·GPU 메모리 확인, 죽었으면 최대 2회 체크포인트 재개.
cd /app/coq-modeling
L=all_log/au_research/v11_train.log; PIDF=models/ft_qwen3_4b_v11/train.pid; RETRY=0
until [ -f $PIDF ]; do sleep 300; done
echo "[$(date '+%m-%d %H:%M')] 감시 시작 pid $(cat $PIDF)"
while true; do
  sleep 600
  if grep -q 'SFT_TRAIN_DONE' $L 2>/dev/null; then echo "[$(date '+%m-%d %H:%M')] 학습 정상 종료"; echo "TRAIN_WATCH_DONE"; exit 0; fi
  if ! kill -0 $(cat $PIDF) 2>/dev/null; then
    echo "[$(date '+%m-%d %H:%M')] ★ 학습 프로세스 사망. 마지막 로그:"; grep -v 'it/s\|it\]' $L | tail -5 | cut -c1-200
    if [ $RETRY -ge 2 ]; then echo "재개 한도 초과 — 중단"; echo "TRAIN_WATCH_FAIL"; exit 1; fi
    RETRY=$((RETRY+1)); echo "재개 시도 $RETRY (체크포인트에서)"
    cp $L "$L.crash$RETRY"
    CUDA_VISIBLE_DEVICES=0,1 nohup torchrun --nproc_per_node 2 --master_port $((29573+RETRY)) scripts/sft_train.py all_log/ft_qwen3_4b_v11_conf.yaml --resume > $L 2>&1 < /dev/null &
    echo $! > $PIDF; sleep 120
  fi
  g=$(grep '\[guard\]' $L | tail -1 | cut -c1-120); s=$(grep '\[sample\]' $L | tail -1 | cut -c1-160)
  m=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader | tr '\n' ' ')
  echo "[$(date '+%m-%d %H:%M')] $g | $s | GPU $m"
done
