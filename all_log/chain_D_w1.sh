#!/bin/bash
# pass@K 완료 대기 → 결과 md 기입 → RFT(추천) 실행 → 큐 재개(adaptprefix~bigscale). worker 1.
set -u
LOG=all_log/chain_D.log
say(){ echo "[$(TZ=Asia/Seoul date '+%m-%d %H:%M')] $*" | tee -a "$LOG"; }

say "대기: pass@K 롤아웃 완료(passk.jsonl 40줄 또는 프로세스 종료)"
while [ "$(wc -l < data/grpo_rollouts/passk.jsonl 2>/dev/null || echo 0)" -lt 40 ]; do
  pgrep -f "run_all.py --alias grpo-rollout-passk" >/dev/null 2>&1 || break
  sleep 60
done
say "pass@K 종료 감지 → pass@1~8 계산 + md 기입"
python3 - <<'PY' 2>&1 | tee -a "$LOG"
import json
from pathlib import Path
g=[json.loads(l) for l in open('data/grpo_rollouts/passk.jsonl').read().splitlines() if l.strip()]
K=8; N=len(g)
rows=[]
for k in range(1,K+1):
    s=sum(1 for x in g if any(a['reward']>=1 for a in x['attempts'][:k]))
    rows.append(f"| pass@{k} | {s}/{N} |")
tbl=f"| K | solved (첫 {N}정리) |\n|---|---|\n"+"\n".join(rows)
p=Path('all_log/docs/PASSK_ANALYSIS.md'); t=p.read_text()
old='<!-- PASSK_RESULT -->\n_(측정 중 — 완료 시 자동 기입)_'
new='<!-- PASSK_RESULT -->\n'+tbl+"\n\n(fix greedy pass@1=19/40 참고. 위 pass@1은 온도샘플이라 더 낮을 수 있음. "
new+="pass@8≫pass@1 이면 능력 있음=디코딩 병목, pass@8도 낮으면 능력 천장.)"
if old in t: p.write_text(t.replace(old,new)); print("md 기입 완료")
else: print("경고: placeholder 못 찾음");
print(tbl)
PY

say "▶ RFT (rft-gold=fail set 겨냥, rft-self=on-policy 대조)"; bash all_log/run_rft.sh
say "▶ 큐 재개 (adaptprefix→bread→backward-prm→retry-prm→fixdyn→deepres→bigscale)"; bash all_log/chain_C_w1.sh
say "===== chain_D 전체 완료 ====="
