#!/bin/bash
# 후보 모델을 같은 프로브로 비교 — "어느 모델이 rango 병목을 뚫을 능력이 있나".
# 사용: bash all_log/probe_sweep.sh <GPU> <출력파일> <모델...>
#
# 프로브 축 (앞 4개=타입 읽기 / 뒤 5개=병목: 환각·조합)
#   M1 생성자 소속   M2 남은분기 추적   M3 소진판단(세기)   M4 생성자 인자수
#     → 전부 코퍼스에 없는 **합성 타입**. 외운 게 아니라 정의를 읽는지만 잰다.
#   M5 실재 premise vs 환각      ← INVALID 의 45.3%가 '이름 못 찾음', 그 78%가 지어낸 이름
#   M6 premise 안 이름 vs 완전가짜
#   X1 lemma 선택   ← apply 실패의 90%가 '잘못된 lemma 선택' (BOTTLENECK_ANALYSIS.md)
#   X2 인자 배치    ← 재료(가설)는 79% 이미 프롬프트에 있음
#   X3 oracle 힌트  ← gold lemma를 쥐여줘도 8→10%(+2pp)뿐이었다 (COMPOSITION_IS_THE_WALL.md)
cd /app/coq-modeling || exit 1
set -u
G=$1; OUT=$2; shift 2
N=${N:-200}
: > "$OUT"
for M in "$@"; do
  echo "[$(TZ=Asia/Seoul date '+%H:%M')] === $M ===" | tee -a "$OUT"
  timeout 5400 env CUDA_VISIBLE_DEVICES="$G" HF_HUB_OFFLINE=1 \
    python3 scripts/probe_type_match.py --model "$M" --n "$N" 2>/dev/null \
    | grep -aE "^   [✅❌·]" | tee -a "$OUT"
  echo "" | tee -a "$OUT"
done
echo "[$(TZ=Asia/Seoul date '+%H:%M')] 완료" | tee -a "$OUT"
