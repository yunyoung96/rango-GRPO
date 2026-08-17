#!/bin/bash
# 감사에서 고친 프로브를 **확장 표본**으로 전 항목 재실행.
#   수정: ① 단어경계 검색(부분문자열 오매칭) ② X1 이중계산 제거
#         ③ Bonferroni 보정(54검정) ④ truncation_side=left
#   표본: goldsft 단일(226) → 성공 롤아웃 8종 통합 796 (중복제거)
cd /app/coq-modeling || exit 1
set -u
G=$1; OUT=$2; shift 2
N=${N:-796}
: > "$OUT"
for M in "$@"; do
  echo "[$(TZ=Asia/Seoul date '+%H:%M')] === $M ===" | tee -a "$OUT"
  timeout 7200 env CUDA_VISIBLE_DEVICES="$G" HF_HUB_OFFLINE=1 \
    python3 scripts/probe_type_match.py --model "$M" --n "$N" 2>>"${OUT%.log}.err" \
    | grep -a --line-buffered -E "^   [✅❌△▽·]|표본:" | tee -a "$OUT"
  # 크래시를 숨기지 않는다 — 예전에 2>/dev/null 때문에 OverflowError 가 조용히 묻혔다
  if grep -aqE "Traceback|Error" "${OUT%.log}.err" 2>/dev/null; then
    echo "   ⚠ 오류 발생 — ${OUT%.log}.err 확인" | tee -a "$OUT"
  fi
  echo "" | tee -a "$OUT"
done
echo "[$(TZ=Asia/Seoul date '+%H:%M')] 완료" | tee -a "$OUT"
