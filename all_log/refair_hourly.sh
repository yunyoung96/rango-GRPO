#!/bin/bash
# refair 시간별 성공률 — cascade-s0r2(harvest) 진행중(부분,편향) + 대조군(최종값). 매시간(첫 회 즉시), s0r2 200 완료시 종료.
# ※ cascade-s0 는 사용자 요청으로 중단(동결) → 보고에서 제외. 부분값은 완료순 편향(빠른 정리 먼저) → 하강수렴.
first=1
while true; do
  [ "$first" = 1 ] || sleep 3600
  first=0
  ts=$(TZ=Asia/Seoul date '+%m-%d %H:%M')
  out=$(python3 -c "
import json
def rd(n):
    try:
        r=json.load(open(f'all_results/{n}/summary.json'))['results']
        return len(r), sum(1 for x in r if x['success'])
    except Exception:
        return 0,0
d,s=rd('rand200_cascade_s0r2_w2'); fin = 1 if d>=200 else 0
bd,bs=rd('rand200_baseline_test600_w2'); gd,gs=rd('rand200_sftgrpo_test600_w2'); ld,ls=rd('rand200_leafsubgoal_test600_w2')
print(f'  진행중(부분,편향): cascade-s0r2(harvest)={s}/{d}({100*s/max(d,1):.0f}%)')
print(f'  대조(최종200): baseline(=SFT) {bs}/{bd}({100*bs/max(bd,1):.1f}%) · SFT→GRPO {gs}/{gd}({100*gs/max(gd,1):.1f}%) · leaf-subgoal {ls}/{ld}({100*ls/max(ld,1):.1f}%)')
print('DONE' if fin else 'GO')
")
  body=$(printf '%s\n' "$out" | head -2)
  flag=$(printf '%s\n' "$out" | tail -1)
  if [ "$flag" = "DONE" ]; then
    printf '[시간별 %s] ✅ cascade-s0r2 200/200 완료 — 시간별 보고 종료 (cascade-s0는 중단됨)\n%s\n' "$ts" "$body"
    break
  fi
  printf '[시간별 %s]  (cascade-s0는 중단됨)\n%s\n' "$ts" "$body"
done
