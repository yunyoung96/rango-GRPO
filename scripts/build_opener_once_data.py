#!/usr/bin/env python3
"""opener-once(with compound) 학습 데이터 — opener가 '전체 opening'을 첫 한 번에 다 하는 버전.

사용자 의도: Theorem → Proof → intros → destruct(compound) → ... **분해 가능한 만큼 다 열고(NMD까지)**,
그 뒤 closing은 전부 rango. 즉 opener = **여는 것 전부**(Proof/intros/simpl/unfold/destruct/induction/inv),
첫 closing(apply/rewrite/auto 등) 지점에서 **NMD**.
  · opener는 pre-loop으로 tactic 하나씩 생성·적용 → NMD 나올 때까지 반복 → 그 뒤 rango.
  · 입력엔 compound 후보(_targeted_cands) + lemma/proof retrieval 포함.

이전 opener-tac(structural만, intros는 rango 몫)과 차이: **intros/simpl/unfold도 opener가** = 전체 opening 담당.
데이터: goldsft_bs2.jsonl. 출력: data/grpo_rollouts/opener_once.jsonl {input, target}. ★OCaml 무관."""
import json, re, sys
sys.path.insert(0, 'src')
from tactic_gen.grpo_rollout import _targeted_cands

# opener가 담당하는 '여는' tactic (Proof. 제외 — Proof는 executor가; opener가 Proof만 반복하는 버그 방지).
OPENING = {'intros', 'intro', 'simpl', 'unfold', 'cbn', 'red', 'hnf',
           'destruct', 'induction', 'inv', 'inversion', 'case', 'revert', 'generalize'}
NMD = "No More Decomposition"

def kw(t):
    m = re.match(r'\s*([A-Za-z_]+)', (t or '').strip().lstrip('\n')); return m.group(1) if m else ''

def build_input(state, premises, proofs, n_prem=30, n_proof=4):
    cands = [c.strip() for c in _targeted_cands([state])]
    lines = [f"GOAL:\n{(state or '').strip().lstrip(chr(10))}", ""]
    ct = "\n".join(f"- {c}" for c in cands) if cands else "(none)"
    lines.append(f"CANDIDATE DECOMPOSITIONS:\n{ct}"); lines.append("")
    prem = [p.split('\n')[0][:140] for p in (premises or [])[:n_prem]]
    lines.append("RELEVANT LEMMAS:\n" + ("\n".join(f"- {p}" for p in prem) if prem else "(none)"))
    lines.append("")
    prf = []
    for p in (proofs or [])[:n_proof]:
        h = p.split('\n'); nm = h[0][:100]; body = " ".join(x.strip() for x in h[1:4])[:120]
        prf.append(f"- {nm} | {body}")
    lines.append("RELEVANT PROOFS:\n" + ("\n".join(prf) if prf else "(none)"))
    return "\n".join(lines)

out = []
n_thm = n_open = n_nmd = 0
for line in open('data/grpo_rollouts/goldsft_bs2.jsonl'):
    g = json.loads(line)
    for a in g['attempts']:
        steps = a['steps']
        if not steps:
            continue
        n_thm += 1
        emitted = False
        for s in steps:
            tac = (s.get('tactic') or '').strip().lstrip('\n')
            if not tac:
                continue
            if tac == 'Proof.' or kw(tac) == 'Proof':
                continue   # ★ Proof.는 opener target 아님(pre-loop이 냄) — 건너뜀(NMD로 안 침)
            e = s.get('example') or {}
            state = e.get('proof_state', '')
            if kw(tac) in OPENING:
                # opener가 이 opening tactic 학습 (Proof/intros/destruct compound 등)
                out.append({"input": build_input(state, e.get('premises'), e.get('proofs')), "target": tac})
                n_open += 1
                continue
            else:
                # 첫 non-opening(closing 시작) → 여기서 opener 정지: NMD
                out.append({"input": build_input(state, e.get('premises'), e.get('proofs')), "target": NMD})
                n_nmd += 1
                emitted = True
                break
        if not emitted:
            # 전부 opening으로 끝(closing 단계 없음) → 마지막에 NMD 예시 (state 없어 스킵 or 첫 state NMD)
            pass
        break  # gold 정리당 attempt 1개

with open('data/grpo_rollouts/opener_once.jsonl', 'w') as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')
print(f"정리 {n_thm}개 처리")
print(f"학습 예시 {len(out)}개 = 전체opening {n_open} + NMD {n_nmd}")
print("→ opener가 Proof/intros/destruct(compound)/... 전부 담당, 첫 closing서 NMD. 그 뒤 rango.")
print("저장: data/grpo_rollouts/opener_once.jsonl")
from collections import Counter
c = Counter(r['target'] if r['target'] == NMD else kw(r['target']) for r in out)
print("target 분포:", dict(c.most_common()))
