#!/usr/bin/env python3
"""tactic-단위 opener 학습 데이터 (v2: structural만 opener target, 비분해는 바로 NMD).

opener의 역할 = **분해(destruct/induction/inversion/case/inv) 선택**만. intros/unfold/simpl 같은
non-structural opening은 executor(rango)가 알아서 → opener는 그거 생성 안 함.
  · 분해가 필요한 state → 그 structural tactic (인자 포함).
  · 더 분해할 게 없으면(자동화로 닫히거나 intros만 필요) → "No More Decomposition"(NMD).

입력(프롬프트): GOAL + CANDIDATE(_targeted_cands, compound 인자) + lemma retrieval(premises) + proof retrieval(proofs).
출력(타겟): 다음 **structural 분해 tactic 1개** 또는 NMD.
데이터: goldsft_bs2.jsonl. 출력: data/grpo_rollouts/opener_tac.jsonl {input, target}. ★OCaml 무관."""
import json, re, sys
sys.path.insert(0, 'src')
from tactic_gen.grpo_rollout import _targeted_cands

STRUCT = {'destruct', 'induction', 'inv', 'inversion', 'case'}
# non-structural opening(intros/unfold/simpl 등)은 그냥 지나감(state는 진행) — opener 학습 target 아님.
PASSTHROUGH = {'intros', 'intro', 'simpl', 'unfold', 'cbn', 'red', 'hnf'}
NMD = "No More Decomposition"

def kw(t):
    m = re.match(r'\s*([A-Za-z_]+)', (t or '').strip().lstrip('\n')); return m.group(1) if m else ''

def clean_state(s):
    return (s or '').strip().lstrip('\n')

def build_input(state, premises, proofs, n_prem=30, n_proof=4):
    cands = [c.strip() for c in _targeted_cands([state])]
    lines = [f"GOAL:\n{clean_state(state)}", ""]
    ct = "\n".join(f"- {c}" for c in cands) if cands else "(none)"
    lines.append(f"CANDIDATE DECOMPOSITIONS:\n{ct}"); lines.append("")
    prem = [p.split('\n')[0][:140] for p in (premises or [])[:n_prem]]
    lines.append("RELEVANT LEMMAS:\n" + ("\n".join(f"- {p}" for p in prem) if prem else "(none)"))
    lines.append("")
    prf = []
    for p in (proofs or [])[:n_proof]:
        head = p.split('\n'); nm = head[0][:100]; body = " ".join(x.strip() for x in head[1:4])[:120]
        prf.append(f"- {nm} | {body}")
    lines.append("RELEVANT PROOFS:\n" + ("\n".join(prf) if prf else "(none)"))
    return "\n".join(lines)

out = []
n_thm = n_nmd = n_struct = n_nostruct_nmd = 0
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
            if tac == 'Proof.' or not tac:
                continue
            k = kw(tac)
            e = s.get('example') or {}
            state = e.get('proof_state', '')
            if k in STRUCT:
                # 분해 지점 → opener가 이 structural tactic을 학습 (인자 포함)
                out.append({"input": build_input(state, e.get('premises'), e.get('proofs')),
                            "target": tac})
                n_struct += 1
                # 이 분해 후 다음 state가 곧바로 NMD인지/또 분해인지는 다음 loop iteration이 결정
                continue
            elif k in PASSTHROUGH:
                # intros/unfold/simpl → opener 학습 안 함(executor 몫). state만 진행.
                continue
            else:
                # 첫 non-opening/non-struct (closing 시작 or 자동화) → 여기서 분해 끝 = NMD
                out.append({"input": build_input(state, e.get('premises'), e.get('proofs')),
                            "target": NMD})
                n_nmd += 1
                emitted = True
                break
        if not emitted:
            # 전부 passthrough/struct로 끝남(closing 단계 없음) — 마지막 상태 NMD 예시 추가 못 함(state 없음).
            # 단, 분해가 하나도 없던 정리(자동화)는 첫 state에서 바로 NMD 학습.
            has_struct = any(kw((s.get('tactic') or '').strip().lstrip('\n')) in STRUCT for s in steps)
            if not has_struct:
                fs = next((s for s in steps if (s.get('tactic') or '').strip() not in ('', 'Proof.')), None)
                if fs:
                    e = fs.get('example') or {}
                    out.append({"input": build_input(e.get('proof_state', ''), e.get('premises'), e.get('proofs')),
                                "target": NMD})
                    n_nostruct_nmd += 1
        break  # gold 정리당 attempt 1개

with open('data/grpo_rollouts/opener_tac.jsonl', 'w') as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

print(f"정리 {n_thm}개 처리")
print(f"학습 예시 {len(out)}개 = structural분해 {n_struct} + NMD(closing) {n_nmd} + NMD(비분해정리) {n_nostruct_nmd}")
print("→ intros/unfold/simpl은 target에서 제외(executor 몫). opener는 분해 or NMD만.")
print("저장: data/grpo_rollouts/opener_tac.jsonl")
from collections import Counter
c = Counter(r['target'] if r['target'] == NMD else kw(r['target']) for r in out)
print("target 분포:", dict(c.most_common()))
