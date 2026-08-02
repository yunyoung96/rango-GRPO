#!/usr/bin/env python3
"""DDR 커버리지 실측 (CPU-only). 실제 decider 인덱스(ddr_index.json)로 gold compound destruct 재구성.
  Mode1: destruct 대상 부분식이 goal에 등장 → 직접 추출.
  Mode2: goal의 타입/술어/연산 head를 인덱스 조회 → decider 후보. gold head가 그 후보에 드나.
비교: 기존 _targeted_cands 21%.
"""
import json, re, sys
sys.path.insert(0, 'src')
from tactic_gen.grpo_rollout import _targeted_cands

def norm(s): return re.sub(r'\s+', ' ', (s or '').strip())
CD = re.compile(r'^destruct\s+\(\s*(.+?)\s*\)\s*(?:as\b.*)?\.?\s*$', re.S)
SIMPLE = re.compile(r"[a-z]|[a-z]\d|v\d*|e\d*|H\w*|f|g")

idx = json.load(open('data/ddr_index.json'))
TYPE_EQ, PRED_DEC, OP_SPEC = idx['type_eq'], idx['pred_dec'], idx['op_spec']

def goal_heads(goal):
    """goal에서 함수적용 head(연산/술어 후보) + 등장 식별자 집합."""
    ids = set(re.findall(r"[A-Za-z_][\w']*", goal))
    return ids

def ddr_candidates(goal):
    """DDR이 만들 destruct 후보의 head 집합 (Mode2: 인덱스에서). Mode1은 별도 substring 판정."""
    heads = goal_heads(goal)
    cands = set()
    for h in heads:
        for dec in OP_SPEC.get(h, []): cands.add(dec.split('.')[-1])
        for dec in PRED_DEC.get(h, []): cands.add(dec.split('.')[-1])
        for dec in TYPE_EQ.get(h, []): cands.add(dec.split('.')[-1])
    return cands

n = base_hit = m1 = m2 = ddr = 0
none_ex = []
for line in open('data/grpo_rollouts/goldsft_bs2.jsonl'):
    g = json.loads(line)
    for a in g['attempts']:
        for s in a['steps']:
            tac = (s.get('tactic') or '').strip().lstrip('\n')
            m = CD.match(tac)
            if not m: continue
            E = re.split(r'\s+as\b', m.group(1))[0].strip()
            head = E.split(None, 1)[0]
            if SIMPLE.fullmatch(head): continue
            goal = (s.get('example', {}) or {}).get('proof_state', '')
            if not goal: continue
            n += 1
            ng = norm(goal)
            head_s = head.split('.')[-1]
            # 기준선
            if norm('destruct (' + E + ').') in [norm(c) for c in _targeted_cands([goal])]:
                base_hit += 1
            # Mode1: E가 goal에 등장(substring 또는 head+인자대부분)
            argtoks = [t for t in re.split(r'[\s()]+', E) if t and not re.fullmatch(r'\d+', t)]
            in_g = norm(E) in ng or (
                re.search(r'\b' + re.escape(head_s) + r'\b', ng) and
                sum(1 for t in argtoks[1:] if re.search(r'\b' + re.escape(t.split('.')[-1]) + r'\b', ng)) >= max(1, (len(argtoks) - 1) * 0.6))
            # Mode2: gold head가 인덱스 조회 결과에 드나
            in_idx = head_s in ddr_candidates(goal)
            if in_g: m1 += 1
            if in_idx: m2 += 1
            if in_g or in_idx: ddr += 1
            else:
                if len(none_ex) < 10: none_ex.append(E[:45])

def pct(x): return f"{100*x/max(n,1):.0f}%"
print(f"gold compound destruct: {n}")
print(f"기준선 _targeted_cands: {base_hit} = {pct(base_hit)}")
print(f"Mode1 (부분식 goal 등장):      {m1} = {pct(m1)}")
print(f"Mode2 (실제 인덱스 조회):       {m2} = {pct(m2)}")
print(f"★ DDR (Mode1 ∪ Mode2):        {ddr} = {pct(ddr)}")
print(f"\n둘다 못잡음 예: {none_ex}")
