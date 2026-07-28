#!/usr/bin/env python3
"""invertible 분해(t1;t2 조합 포함) + auto-closer 후보 생성 → invauto.json.
각 후보 = 완결 시도 'Proof. intros; <분해조합>; solve[auto|...].' → check_proof COMPLETE면 순수-Coq로 닫힘.
gold 없이 모델 없이 '분해+auto'만으로 train 정리를 얼마나 닫나 측정(version A)."""
import json, re

curr = json.load(open('data/curriculum/invgr.json'))
jl = [json.loads(l) for l in open('data/grpo_rollouts/invgr.jsonl') if l.strip()]
groups = []
for r in jl:
    steps = r['attempts'][0]['steps'] if r['attempts'] else []
    if steps:
        ex = steps[0]['example']
        groups.append({'file': ex.get('file_name', ''), 'state': ex.get('proof_state', '')})

CLOSE = 'solve [ auto | eauto | lia | congruence | intuition | now eauto ]'
IND_TYPES = {'nat', 'positive', 'Z', 'N', 'bool', 'list', 'option', 'comparison',
             'prod', 'sum', 'sumbool', 'ident', 'block', 'val', 'memval', 'instruction'}

def parse_hyps(state):
    hyps = []
    for ln in state.split('\n'):
        if ln.strip() == '': break
        m = re.match(r"^([\w' ]+?)\s*:\s*(.+)$", ln)
        if not m: break
        for nm in m.group(1).split():
            hyps.append((nm, m.group(2).strip()))
    return hyps

def goal_of(s):
    p = s.split('\n\n', 1)
    return (p[1] if len(p) > 1 else s).strip()

def cands(hyps):
    dvars, props = [], []
    for nm, typ in hyps:
        head = typ.split()[0] if typ.split() else typ
        if '->' not in typ:
            if head in IND_TYPES: dvars.append((0, nm))
            elif head[:1].isupper() and head not in ('Type','Set','Prop','R','Q','radix'): dvars.append((1, nm))
        if '=' in typ or typ.startswith('In ') or '<=' in typ or (nm[0] == 'H' and '->' not in typ):
            props.append(nm)
    dv = [nm for _, nm in sorted(dvars, key=lambda x: x[0])]
    P = f'\nProof.\nintros; '
    out = [P + f'{CLOSE}.', P + f'simpl; {CLOSE}.']            # 분해없이 auto (baseline)
    for v in dv[:4]:
        out += [P + f'destruct {v}; {CLOSE}.',
                P + f'induction {v}; {CLOSE}.',
                P + f'destruct {v}; simpl; {CLOSE}.']
    for h in props[:2]:
        out += [P + f'inversion {h}; {CLOSE}.']
    # t1;t2 조합 (앞 2변수 쌍)
    if len(dv) >= 2:
        out += [P + f'destruct {dv[0]}; destruct {dv[1]}; {CLOSE}.',
                P + f'induction {dv[0]}; destruct {dv[1]}; {CLOSE}.']
    return list(dict.fromkeys(out))[:14]

out, matched = {}, 0
for stmt, e in curr.items():
    cg = [g for g in groups if g['file'].endswith(e['path'])]
    best = next((g for g in cg if goal_of(g['state'])[:35] in stmt.replace('\n', ' ')), None)
    if best is None and len(cg) == 1: best = cg[0]
    if best is None: continue
    matched += 1
    c = cands(parse_hyps(best['state']))
    if c:
        out[stmt] = {**e, 'starts': [{'initial_proof': s, 'remaining': 1} for s in c]}

json.dump(out, open('data/curriculum/invauto.json', 'w'))
open('data/compcert_bs2_invauto_idx.txt', 'w').write('\n'.join(str(v['idx']) for v in out.values()) + '\n')
print(f'matched {matched}/{len(curr)} · invauto 커리큘럼 {len(out)}정리 · '
      f'평균 후보 {sum(len(v["starts"]) for v in out.values())/max(len(out),1):.1f}')
if out:
    print('예:', [s['initial_proof'].strip().replace(chr(10), ' ') for s in list(out.values())[0]['starts'][:3]])
