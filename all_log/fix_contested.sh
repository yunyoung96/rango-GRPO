#!/bin/bash
# GPU 경합으로 오염된 rango-grpo @180 결과를 재실행해 교체한다.
#
# 배경: 2026-07-13 13:00~14:10 UTC 사이에 PGTS 스모크 테스트가 같은 GPU를 썼다.
#   평가 타임아웃이 600초 **벽시계** 기준이라, GPU 경합은 실행을 느리게 만드는 게 아니라
#   그 600초 안에 시도 가능한 tactic 수를 줄여 **성공률을 떨어뜨린다** = 결과를 바꾼다.
#   그 구간에 '실패'로 기록된 정리들은 신뢰할 수 없다.
#   (같은 구간의 '성공'은 유효하다 — 경합은 성공률을 낮출 뿐 높이지 못한다.)
#
# 동작: robustness 드라이버가 전부 끝나기를 기다린 뒤(GPU 독점 확보),
#   오염 구간에 실패한 idx 만 summary 에서 제거하고 --out resume 으로 재실행한다.
set -u
LOG=all_log/fix_contested.log
DRIVER_PID=${DRIVER_PID:-1605702}
START_EPOCH=${START_EPOCH:?오염 시작 epoch 필요}
END_EPOCH=${END_EPOCH:?오염 종료 epoch 필요}
say(){ echo "[$(date '+%H:%M')] $*" | tee -a "$LOG"; }

say "===== 오염 결과 수습 대기 시작 (드라이버 PID ${DRIVER_PID} 종료 대기) ====="
while kill -0 "$DRIVER_PID" 2>/dev/null; do sleep 60; done
say "드라이버 종료 확인 → GPU 독점. 수습 시작."

D=$(ls -dt all_results/*_rango-grpo | head -1)
say "대상 디렉토리: $D"

CONTESTED=$(python3 - "$D" "$START_EPOCH" "$END_EPOCH" <<'PY'
import json, os, sys
d, s, e = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
summ = json.load(open(f"{d}/summary.json"))
bad = []
for r in summ["results"]:
    if r.get("success"):          # 경합 중 성공은 유효 → 건드리지 않는다
        continue
    f = f"{d}/logs/{r['idx']}.txt"
    if os.path.exists(f) and s <= os.path.getmtime(f) <= e:
        bad.append(r["idx"])
print(" ".join(map(str, sorted(bad))))
PY
)
say "오염된 실패 idx: ${CONTESTED:-없음}"
[ -z "$CONTESTED" ] && { say "수습할 것 없음. 종료."; exit 0; }

# 백업 후 해당 항목 제거(로그도 지워야 run_thm 이 새로 씀)
cp "$D/summary.json" "$D/summary.pre_fix.json"
python3 - "$D" "$CONTESTED" <<'PY'
import json, os, sys
d = sys.argv[1]
bad = set(int(x) for x in sys.argv[2].split())
p = f"{d}/summary.json"
summ = json.load(open(p))
kept = [r for r in summ["results"] if r["idx"] not in bad]
summ["results"] = kept
summ["done"] = len(kept)
summ["success"] = sum(1 for r in kept if r.get("success"))
summ["fail"] = summ["done"] - summ["success"]
json.dump(summ, open(p, "w"), indent=2, ensure_ascii=False)
for i in bad:
    f = f"{d}/logs/{i}.txt"
    if os.path.exists(f):
        os.remove(f)
print(f"제거 {len(bad)}개, 잔존 {len(kept)}개")
PY

say "재실행 시작 (workers=2, GPU 독점)"
python3 scripts/run_all.py --alias rango-grpo --num 180 --timeout 600 --workers 2 \
  --out "$D" --description "robustness @180 (contested idx re-run, GPU 독점)" >> "$LOG" 2>&1

python3 - "$D" <<'PY'
import json, sys
d = sys.argv[1]
new = json.load(open(f"{d}/summary.json"))
old = json.load(open(f"{d}/summary.pre_fix.json"))
def stat(s):
    r = s["results"]
    su = sum(1 for x in r if x.get("success"))
    ob = sum(1 for x in r if x.get("original_success"))
    return len(r), su, ob
print("수습 전:", "%d개 · succ %d · published %d · net %+d" % (*stat(old), stat(old)[1]-stat(old)[2]))
print("수습 후:", "%d개 · succ %d · published %d · net %+d" % (*stat(new), stat(new)[1]-stat(new)[2]))
PY
say "===== 수습 완료 ====="
