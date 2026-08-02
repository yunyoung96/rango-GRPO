#!/usr/bin/env python3
"""opener 학습 데이터 생성(2변형) — 300 train gold(goldsft_bs2)에서:
(a) 생성형 opener_gen.jsonl: {goal, opening:[tactics]}  — goal → gold opening(첫 분해까지)
(b) 선택형 opener_sel.jsonl: {goal, candidates:[...], gold} — goal+열거후보 → gold 선택
★OCaml 무관."""
import json, re, sys
sys.path.insert(0, 'src')
from tactic_gen.grpo_rollout import _targeted_cands

STRUCT = {'induction','destruct','inversion','case','inv'}
INTRO = {'intro','intros'}
def kw(t):
    m=re.match(r'\s*([A-Za-z_]+)', t or ''); return m.group(1) if m else ''

gen=[]; sel=[]; nostruct=0; goldnotin=0
for line in open('data/grpo_rollouts/goldsft_bs2.jsonl'):
    g=json.loads(line)
    for a in g['attempts']:
        steps=a['steps']
        if not steps: continue
        # 첫 structural step 찾기
        si=next((i for i,s in enumerate(steps) if kw(s.get('tactic',''))in STRUCT), None)
        if si is None: nostruct+=1; continue
        init_goal = steps[0]['example'].get('proof_state','') or ''
        opening = [ (steps[i].get('tactic') or '').strip() for i in range(si+1) ]  # 시작~첫분해
        gold_tac = (steps[si].get('tactic') or '').strip()
        decision_goal = steps[si]['example'].get('proof_state','') or ''
        cands = _targeted_cands([decision_goal])
        cands = [c.strip() for c in cands]
        # gold가 열거에 있나(정규화: kw+대상)
        def norm(t): return re.sub(r'\s+eqn:\S+','',(t or '').split(';')[0].strip().rstrip('.'))
        gold_in = any(norm(c)==norm(gold_tac) for c in cands)
        if not gold_in:
            goldnotin+=1
            cands = cands + [gold_tac]   # gold를 후보에 추가(항상 정답 존재)
        gen.append({'goal':init_goal, 'opening':opening})
        sel.append({'goal':decision_goal, 'candidates':cands, 'gold':gold_tac})
        break  # 정리당 gold 1개

with open('data/grpo_rollouts/opener_gen.jsonl','w') as f:
    for r in gen: f.write(json.dumps(r,ensure_ascii=False)+'\n')
with open('data/grpo_rollouts/opener_sel.jsonl','w') as f:
    for r in sel: f.write(json.dumps(r,ensure_ascii=False)+'\n')
print(f"생성형 {len(gen)}개 → opener_gen.jsonl")
print(f"선택형 {len(sel)}개 → opener_sel.jsonl (열거에 gold 있던 비율 {100*(len(sel)-goldnotin)/max(len(sel),1):.0f}%)")
print(f"  (structural 없는 gold {nostruct}개 제외)")
# 샘플
print("\n=== 샘플 ===")
for r in sel[:2]:
    print('goal:', ' '.join(r['goal'].split())[:100])
    print('  후보:', r['candidates'][:6])
    print('  gold:', r['gold'])
