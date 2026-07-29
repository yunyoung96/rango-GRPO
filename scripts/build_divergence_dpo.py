#!/usr/bin/env python3
"""divergence-DPO 데이터 생성기.
dead 롤아웃에서 '정책이 gold 경로를 처음 벗어난 그 지점'(on-path state)의 쌍을 만든다:
  chosen   = gold이 그 state서 친 tactic (경로 유지)
  rejected = 정책이 그 state서 친 (VALID지만 경로 이탈) tactic
→ {state:<example>, chosen, rejected}  (dpo_train.py 소비 포맷)

algo-dev-dpo(BFS-Prover DPO)와의 핵심 차이:
  · negative = INVALID(컴파일에러)가 아니라 **VALID-but-wrong(경로 이탈)** — 우리 실패의 80%+ 유형.
  · 일반 state 아무데나가 아니라 **divergence(fatal 분해) 지점** 타깃.
사용: python3 scripts/build_divergence_dpo.py <rollout.jsonl> <gold.jsonl> <out.jsonl>
★OCaml 무관.
"""
import json, re, sys

ROLL, GOLD, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

INTRO = {'intro', 'intros'}   # 이름만 바꾸는 tactic (destruct/induction은 실제 분해라 제외 안 함)
def kw(t):
    m = re.match(r'\s*([A-Za-z_]+)', t or ''); return m.group(1) if m else ''
def cosmetic(c, r):
    # 둘 다 intro계열 = 가설 이름만 다른 노이즈 → 스킵
    return kw(c) in INTRO and kw(r) in INTRO

def norm(st): return ' '.join((st or '').split())
def key(steps):
    return (steps[0]['example']['file_name'], steps[0]['example']['proof_idx']) if steps else None

# gold: theorem -> {norm(proof_state): gold tactic}
gmap = {}
for line in open(GOLD):
    g = json.loads(line)
    for a in g['attempts']:
        k = key(a['steps'])
        if not k: continue
        d = gmap.setdefault(k, {})
        for s in a['steps']:
            d[norm(s['example'].get('proof_state'))] = (s.get('tactic') or '').strip()

pairs = []; kinds = {}
for line in open(ROLL):
    g = json.loads(line); a = g['attempts']
    if any(x['reward'] >= 1 for x in a):  # dead 정리만
        continue
    k = key(a[0]['steps']) if a[0].get('steps') else None
    gm = gmap.get(k)
    if not gm: continue
    for att in a:
        steps = att['steps']
        if not steps: continue
        states = [norm(s['example'].get('proof_state')) for s in steps]
        on = [st in gm for st in states]
        if not on[0]:  # 시작부터 off-path (state 포맷 불일치) → 스킵
            continue
        div = next((i for i in range(len(on)) if not on[i]), None)
        if div is None or div == 0:  # 끝까지 on-path거나 즉시 off → 쌍 없음
            continue
        j = div - 1  # 마지막 on-path state
        if steps[j].get('result') != 'VALID':  # 상태를 바꾼 VALID tactic만
            continue
        gold_tac = gm.get(states[j], '')
        pol_tac = (steps[j].get('tactic') or '').strip()
        if not gold_tac or not pol_tac or gold_tac == pol_tac:
            continue
        if cosmetic(gold_tac, pol_tac):   # intro 이름차이 등 노이즈 제외
            continue
        pairs.append({'state': steps[j]['example'], 'chosen': gold_tac, 'rejected': pol_tac})

# dedup (chosen, rejected, state-goal)
seen = set(); out = []
for p in pairs:
    kk = (p['chosen'], p['rejected'], norm(p['state'].get('proof_state')))
    if kk in seen: continue
    seen.add(kk); out.append(p)

with open(OUT, 'w') as f:
    for p in out:
        f.write(json.dumps(p, ensure_ascii=False) + '\n')
print(f"divergence-DPO 쌍: {len(out)}개 (raw {len(pairs)}) → {OUT}")
