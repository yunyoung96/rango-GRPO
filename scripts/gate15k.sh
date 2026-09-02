#!/bin/bash
# ★ 15k 평가 게이트 — global step ≥ 15000 이 되면: 감시자(자동재개) 정지 → 학습 정지(checkpoint-15000 보존)
#   → 마커 출력. 이후 rand200 평가·계속/종료 결정은 상위(Claude/사용자)가 한다.
cd /app/coq-modeling
L=models/ft_qwen3_4b_v11/trainlog.jsonl
until [ -f "$L" ]; do sleep 600; done
echo "[$(date '+%m-%d %H:%M')] 게이트 감시 시작"
while :; do
  sleep 600
  st=$(tail -1 "$L" 2>/dev/null | python3 -c "import sys,json;print(json.loads(sys.stdin.read() or '{}').get('step',0))" 2>/dev/null)
  [ -z "$st" ] && st=0
  if [ "$st" -ge 15000 ]; then
    echo "[$(date '+%m-%d %H:%M')] step $st ≥ 15000 — 게이트 발동"
    for p in $(pgrep -f 'train_watch.s[h]'); do kill $p; done; sleep 2
    for p in $(pgrep -f 'torchrun.*2957[0-9]'); do pkill -P $p; kill $p; done; sleep 5
    for p in $(pgrep -f 'sft_train.py.*ft_qwen3_4b_v11_con[f]'); do kill $p; done
    ls -d models/ft_qwen3_4b_v11/checkpoint-* 2>/dev/null | tail -3
    echo "GATE15K_REACHED"
    exit 0
  fi
done
