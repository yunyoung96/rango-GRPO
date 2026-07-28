#!/usr/bin/env python3
"""goal-reader(invgr.jsonl)의 intros-후 상태에서 가설을 파싱 → targeted invertible 후보
(destruct/induction 각 변수, inversion 각 prop-가설)를 생성 → targeted_probe.json 커리큘럼.
Coq이 유효한 것만 통과시키므로 blind 열거해도 됨."""
import json, re, sys

curr = json.load(open('data/curriculum/invgr.json'))          # statement -> {starts,idx,path}
jl = [json.loads(l) for l in open('data/grpo_rollouts/invgr.jsonl') if l.strip()]

groups = []
for r in jl:
    steps = r['attempts'][0]['steps'] if r['attempts'] else []
    if not steps: continue
    ex = steps[0]['example']
    groups.append({'file': ex.get('file_name',''), 'state': ex.get('proof_state','')})

def parse_hyps(state):
    hyps = []
    for ln in state.split('\n'):
        if ln.strip() == '':
            break                          # 빈 줄 → 이후는 goal
        m = re.match(r"^([\w' ]+?)\s*:\s*(.+)$", ln)
        if not m:
            break
        names, typ = m.group(1).split(), m.group(2).strip()
        for nm in names:
            hyps.append((nm, typ))
    return hyps

def goal_of(state):
    p = state.split('\n\n', 1)
    return (p[1] if len(p) > 1 else state).strip()

IND_TYPES = {'nat', 'positive', 'Z', 'N', 'bool', 'list', 'option', 'comparison',
             'prod', 'sum', 'sumbool', 'ident', 'block', 'val', 'memval', 'instruction'}
def candidates(hyps):
    dvars, props = [], []
    for nm, typ in hyps:
        head = typ.split()[0] if typ.split() else typ
        # destruct/induction: 유도형 데이터. 함수(->)·sort·R/Q/radix 제외.
        if '->' not in typ:
            if head in IND_TYPES:
                dvars.append((0, nm))
            elif head[:1].isupper() and head not in ('Type', 'Set', 'Prop', 'R', 'Q', 'radix'):
                dvars.append((1, nm))
        # inversion: 등식 / In / <= / H-가설(명제)
        if '=' in typ or typ.startswith('In ') or '<=' in typ or (nm[0] == 'H' and '->' not in typ):
            props.append(nm)
    dvars = [nm for _, nm in sorted(dvars, key=lambda x: x[0])]
    c = []
    for v in dvars[:3]:
        c += [f'\nProof.\nintros. destruct {v}.', f'\nProof.\nintros. induction {v}.']
    for h in props[:2]:
        c.append(f'\nProof.\nintros. inversion {h}.')
    return list(dict.fromkeys(c))[:8]

out, matched = {}, 0
for stmt, e in curr.items():
    path = e['path']
    cg = [g for g in groups if g['file'].endswith(path)]
    best = None
    for g in cg:
        goal = goal_of(g['state'])
        if goal and goal[:35] in stmt.replace('\n', ' '):
            best = g; break
    if best is None and len(cg) == 1:
        best = cg[0]
    if best is None:
        continue
    matched += 1
    cands = candidates(parse_hyps(best['state']))
    if not cands:
        continue
    out[stmt] = {**e, 'starts': [{'initial_proof': c, 'remaining': 1} for c in cands]}

json.dump(out, open('data/curriculum/targeted_probe.json', 'w'))
idxs = [v['idx'] for v in out.values()]
open('data/compcert_bs2_targeted_idx.txt', 'w').write('\n'.join(map(str, idxs)) + '\n')
print(f'matched {matched}/{len(curr)} · targeted 커리큘럼 {len(out)}정리 · '
      f'평균 후보 {sum(len(v["starts"]) for v in out.values())/max(len(out),1):.1f}개')
if out:
    ex = list(out.values())[0]
    print('예 후보:', [s['initial_proof'].strip().replace(chr(10),' ') for s in ex['starts'][:4]])
