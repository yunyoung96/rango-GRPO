#!/bin/bash
# 계획 생성이 끝난 **뒤에** metric 랭커 실험을 돌린다.
#
# ★ 왜 뒤인가: 계획 생성이 12코어를 쓴다. 같이 돌리면 둘 다 느려지고, 실험 시간
#   측정이 오염된다(이 실험은 **시간도 재는 것**이 목적이다).
#
# ★ 무엇을 겨루나
#     eqx        현재 채택안                         RRF(tfidf) + RRF(C') + W·1[α-동치]
#     jac        C' 를 metric 으로 대체              RRF(tfidf) + RRF(1−d_J)
#     jac_eqx    거기에 지시자까지                    + W·1[d_J=0]
#     jac_pure   **구조 정보만**                      1−d_J 단독
#     structural 옛 프로덕션 · tfidf rango 원본
set -u
cd /app/coq-modeling || exit 1
OUT=all_log/au_research
L="$OUT/chain.log"
say(){ echo "[$(date '+%m-%d %H:%M')] $*" >> "$L"; }

# 계획 생성이 끝날 때까지 (파일 개수로 — 프로세스 패턴은 자기매칭한다)
while [ "$(ls data/cut_plan_chunks_train/p_*.jsonl 2>/dev/null | wc -l)" -lt 81 ]; do sleep 180; done
say "계획 생성 완료 확인 — metric 실험 시작"

source all_log/v9_env.sh
unset CUTS_PATH
R='tfidf,structural,eqx,jac,jac_eqx,jac_pure'

for SP in test val; do
  say "metric 실험 $SP n=3000 · C_RENAME=1 · $R"
  C_RENAME=1 nice -n 19 bash scripts/exp_lock.sh \
      python3 -u scripts/exp_abcd.py --split "$SP" --n 3000 --rankers "$R" \
      > "$OUT/metric_$SP.log" 2>&1
  grep -q '프롬프트 포함(P) 기준' "$OUT/metric_$SP.log" \
    && say "metric $SP 완료 → $OUT/metric_$SP.log" \
    || { say "★★ metric $SP 실패"; tail -6 "$OUT/metric_$SP.log" >> "$L"; }
done

# 인덱싱 벤치마크도 다시 (부하 없는 상태에서 재측정 — 시간이 목적이므로)
say "LSH 벤치마크 (부하 없는 상태)"
PYTHONPATH=src python3 -u scripts/bench_metric_index.py 20000 300 \
    > "$OUT/bench_metric.log" 2>&1
say "벤치마크 완료 → $OUT/bench_metric.log"
say "metric 실험 체인 종료"
