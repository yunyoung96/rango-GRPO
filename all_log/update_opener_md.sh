#!/bin/bash
# opener-once-comp 300 파이프라인(OONCE_DONE) 완료 대기 → opener md들을 300 결과로 갱신.
cd /app/coq-modeling || exit 1
# 완료 대기 (최대 10h)
S=$SECONDS
while ! grep -q OONCE_DONE all_log/opener_once.log 2>/dev/null; do
  sleep 120; [ $((SECONDS-S)) -ge 36000 ] && break
done
sleep 5
python3 - <<'PY'
import json,os,re
# 300 롤아웃 통계
F='data/grpo_rollouts/opener_once_pipe2.jsonl'
rows=[json.loads(l) for l in open(F)] if os.path.exists(F) else []
a=m=d=0;ts=ta=0
for g in rows:
    ns=sum(1 for x in g['attempts'] if x.get('reward',0)>0);ta+=len(g['attempts']);ts+=ns
    if ns==0:d+=1
    elif ns==len(g['attempts']):a+=1
    else:m+=1
n=max(len(rows),1)
mixed=100*m/n; att=100*ts/max(ta,1); succ=100*(a+m)/n
# rand200 결과
def perf(p):
    p=f'all_results/{p}/summary.json'
    if os.path.exists(p):
        d=json.load(open(p));return f"{d.get('success')}/{d.get('done')} = {100*d.get('success',0)/max(d.get('done',1),1):.1f}%"
    return "(미완)"
final=perf('oonce_final')
stats={'n':len(rows),'mixed':mixed,'att':att,'succ':succ,'all':a,'m':m,'dead':d,'final':final}
json.dump(stats, open('/tmp/oonce_stats.json','w'))
print("300 결과:", stats)

# OPENER_ONCE_COMP.md 의 '결과(측정 중)' 절 갱신
p='all_log/docs/grpo/opener/OPENER_ONCE_COMP.md'
s=open(p).read()
newres=f"""## 결과 (300 train 롤아웃, 정식 규모)
- **Stage2 롤아웃 {len(rows)}그룹**: all-solved {a} / **mixed {m} ({mixed:.0f}%)** / dead {d} | attempt {att:.1f}%
- rand200 (w2, opener 없이): **{final}**
- 비교(정식 300): plain SFT→GRPO(bigscale2_sft) mixed 26% / leaf-subgoal 27% / opener-tac 28%(100) / opener-once 30%(100)
- 판정: mixed {mixed:.0f}% {'→ plain(26%) 대비 상승' if mixed>=30 else '→ plain과 유사(parity)'}. {'단 mixed↑≠test↑ 주의 — rand200으로 확인.' if mixed>=30 else ''}
"""
s=re.sub(r'## 결과 \(측정 중\).*?(?=\n## |\Z)', newres+'\n', s, flags=re.DOTALL)
if '## 결과' not in s: s+='\n'+newres
open(p,'w').write(s)
print("OPENER_ONCE_COMP.md 갱신")

# README.md 성공률 표에 opener-once-comp 행 추가/갱신
r='all_log/docs/grpo/opener/README.md'
rs=open(r).read()
row=f"| opener-once-comp (300, 전체opening) | {succ:.0f}% | {mixed:.0f}% | {att:.1f}% |"
if 'opener-once-comp' not in rs:
    # 성공률 표 끝에 삽입
    rs=rs.replace("| opener-every (매 분기) | 19% | 8% | 12.6% |",
                  "| opener-every (매 분기) | 19% | 8% | 12.6% |\n"+row)
open(r,'w').write(rs)
print("README.md 갱신")
PY
echo "=== opener md 갱신 완료 MD_UPDATED ===" >> all_log/update_opener_md.log
