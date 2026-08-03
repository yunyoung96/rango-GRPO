#!/bin/bash
# pre-loop 수정 검증(5정리) → opener가 Proof.만 안 내면(정상) → 300 롤아웃→GRPO→rand200 자동 재실행.
cd /app/coq-modeling || exit 1
LOG=all_log/verify_then_full.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" >> "$LOG"; }
: > "$LOG"

# ── 검증(5정리) 완료 대기 (vp_roll.jsonl 5그룹 or 롤아웃 프로세스 종료) ──
say "검증(5정리) 완료 대기..."
S=$SECONDS
while :; do
  n=$([ -f /tmp/vp_roll.jsonl ] && wc -l < /tmp/vp_roll.jsonl || echo 0)
  # 롤아웃 프로세스 없고 데이터 있으면 완료
  if ! pgrep -f 'run_thm.py run grpo-rollout-pf' >/dev/null && [ "$n" -ge 1 ]; then break; fi
  [ "$n" -ge 5 ] && break
  sleep 20; [ $((SECONDS-S)) -ge 900 ] && { say "검증 대기 타임아웃"; break; }
done
sleep 5
# 검증 판정: Proof.만 낸 attempt가 0이고 intros/destruct가 나오면 통과
PASS=$(python3 - <<'PY'
import json,re,os
try:
    rows=[json.loads(l) for l in open('/tmp/vp_roll.jsonl')]
except: print("FAIL"); raise SystemExit
def kw(t):
    m=re.match(r'\s*([a-z_]+)',(t or '').strip().lstrip('\n'));return m.group(1) if m else ''
proof_only=0; opener_att=0; has_real=0
for g in rows:
    for a in g['attempts']:
        ops=[s for s in a['steps'] if s.get('planner_opening')]
        if not ops: continue
        opener_att+=1
        if all((s.get('tactic') or '').strip().lstrip('\n')=='Proof.' for s in ops): proof_only+=1
        if any(kw(s.get('tactic','')) in ('intros','intro','destruct','induction','inv','unfold','simpl') for s in ops): has_real+=1
# 통과 = opener가 실제 opening(intros/destruct 등) 냄 & Proof-only 비율 낮음
print("PASS" if (opener_att>0 and has_real>0 and proof_only < opener_att*0.5) else "FAIL")
PY
)
say "검증 판정: $PASS"
if [ "$PASS" != "PASS" ]; then say "검증 실패 — 자동 재실행 중단(수동 확인 필요)"; exit 1; fi

# ── 통과 → 기존 100/300 산출물 제거 후 300 전체 재실행 ──
rm -f data/grpo_rollouts/opener_once_pipe2.jsonl
rm -rf models/rango-opener-once-comp-grpo
say "검증 통과 → opener_once_pipeline.sh (300 롤아웃→GRPO→rand200) 재실행"
exec bash all_log/opener_once_pipeline.sh
