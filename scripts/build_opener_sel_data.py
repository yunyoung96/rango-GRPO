#!/usr/bin/env python3
"""하이브리드 선택형 opener 데이터: {goal, candidates(열거), gold}. 후보에 gold 있으면 선택, 없으면 생성.
학습: input=goal+열거후보, output=gold tactic. ★OCaml 무관."""
import json, re, sys
sys.path.insert(0,'src')
from tactic_gen.grpo_rollout import _targeted_cands
def kw(t):
    m=re.match(r'\s*([A-Za-z_]+)',t or '');return m.group(1) if m else ''
def norm(t):
    t=(t or '').split(';')[0].strip().rstrip('.'); t=re.sub(r'\s+as\s+\[.*$','',t);t=re.sub(r'\s+eqn:\S+','',t);return t.strip()
STRUCT={'induction','destruct','inversion','case','inv'}
rows=[]; inc_n=0
for l in open('data/grpo_rollouts/goldsft_bs2.jsonl'):
    g=json.loads(l)
    for a in g['attempts']:
        s=a['steps']
        if not s: continue
        si=next((i for i,x in enumerate(s) if kw(x.get('tactic',''))in STRUCT),None)
        if si is None: continue
        gd=(s[si]['tactic']).strip()
        goal=s[si]['example'].get('proof_state','') or ''
        cands=[c.strip() for c in _targeted_cands([goal])]
        gold_in=any(norm(c)==norm(gd) for c in cands); inc_n+=gold_in
        rows.append({'goal':goal,'candidates':cands,'gold':gd,'gold_in':gold_in})
        break
open('data/grpo_rollouts/opener_sel2.jsonl','w').write('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows))
print(f"하이브리드 선택 데이터 {len(rows)}개 → opener_sel2.jsonl (gold 열거포함 {100*inc_n/max(len(rows),1):.0f}%)")
