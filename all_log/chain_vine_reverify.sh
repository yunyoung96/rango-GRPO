#!/bin/bash
set -u
say(){ echo "[$(date '+%m-%d %H:%M')] reverify: $*" | tee -a all_log/newtech.log; }
say "vine @20 완료 대기"
until [ "$(python3 -c "import json;print(len(json.load(open('all_results/smart_rango-grpo-vine/summary.json'))['results']))" 2>/dev/null||echo 0)" -ge 20 ]; do sleep 30; done
# 혹시 남은 vine 롤아웃/평가 프로세스 정리
sleep 10
say "vine @20 완료 → 타임아웃 실패분 단독 재검증"
python3 - <<'PY'
import json
p='all_results/smart_rango-grpo-vine/summary.json'
d=json.load(open(p));
# 타임아웃 실패(경합 의심) 만 제거 → 단독 재실행
bad=[x['idx'] for x in d['results'] if not x.get('success') and (x.get('exit_code')==-9 or x.get('elapsed_sec',0)>590)]
d['results']=[x for x in d['results'] if x['idx'] not in bad]
d['done']=len(d['results']); json.dump(d,open(p,'w'))
import os
for i in bad:
    f=f'all_results/smart_rango-grpo-vine/logs/{i}.txt'
    if os.path.exists(f): os.remove(f)
print(f'  재검증 대상(타임아웃 실패): {bad}')
PY
python3 scripts/run_all.py --alias rango-grpo-vine --num 20 --timeout 600 --workers 2 \
  --out all_results/smart_rango-grpo-vine --description "vine reverify" >> all_log/newtech.log 2>&1
say "vine 재검증 완료"
python3 - <<'PY' 2>&1 | tee -a all_log/newtech.log
import json,glob,sys; sys.path.insert(0,'src')
from coqstoq import Split, get_theorem_list; from pathlib import Path
cc=[i for i,t in enumerate(get_theorem_list(Split.TEST, Path('CoqStoq'))) if t.project.dir_name=='compcert'][:20]
r={x['idx']:x for x in json.load(open('all_results/smart_rango-grpo-vine/summary.json'))['results']}
fix={x['idx']:x for x in json.load(open('all_results/smart_rango-grpo-fix/summary.json'))['results']}
rd=sorted(glob.glob('all_results/2026071*_rango'))[-1]; rango={x['idx']:x for x in json.load(open(rd+'/summary.json'))['results']}
dn=[i for i in cc if i in r]; vs=sum(1 for i in dn if r[i].get('success'))
fs=sum(1 for i in dn if fix.get(i,{}).get('success')); rs=sum(1 for i in dn if rango.get(i,{}).get('success'))
print(f'  ★ vine @20 (재검증 후): {vs}/{len(dn)} | fix {fs} | rango {rs} → vs fix {vs-fs:+d}, vs rango {vs-rs:+d}')
PY
say "→ 마스터 재시작(KL-LUFFY 부터)"
nohup bash all_log/chain_all_remaining.sh >> all_log/chain_all_remaining.log 2>&1 &
say "마스터 재시작 PID=$!"
