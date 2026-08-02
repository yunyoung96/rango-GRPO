#!/usr/bin/env python3
"""opener 학습 데이터 확장 — whole-theorem opening만이 아니라 **모든 분해 지점(=각 subgoal opening)**.
기존 build_opener_data.py 는 정리당 첫 structural 하나만(break) → whole-theorem opening.
여기서는 gold 증명의 **모든 structural 분해 step**에서 (그 시점 (sub)goal 상태 → 분해 tactic) 을 뽑는다.
  · 각 structural step i 에 대해: intros/simpl 등 opening-like 선행 step 을 run-back 으로 포함.
  · goal = run 시작 시점 proof_state (그 subgoal 을 여는 시점 상태).
  · opening = [run-back .. structural] tactic 리스트.
→ opener 가 정리뿐 아니라 **subgoal 상태도 여는 법**을 배운다 (s0 롤아웃서 PLANNER_EVERY 로 매 분기 opener 사용 가능).
★OCaml 무관."""
import json, re, sys
sys.path.insert(0, 'src')
STRUCT = {'induction', 'destruct', 'inversion', 'case', 'inv'}
OPEN_LIKE = {'intro', 'intros', 'simpl', 'unfold', 'cbn', 'red', 'hnf'}

def kw(t):
    m = re.match(r'\s*([A-Za-z_]+)', t or ''); return m.group(1) if m else ''

gen = []
seen = set()
n_thm = 0
per_thm = []
for line in open('data/grpo_rollouts/goldsft_bs2.jsonl'):
    g = json.loads(line)
    for a in g['attempts']:
        steps = a['steps']
        if not steps:
            continue
        n_thm += 1
        cnt = 0
        for i, s in enumerate(steps):
            if kw(s.get('tactic', '')) not in STRUCT:
                continue
            j0 = i
            while j0 - 1 >= 0 and kw(steps[j0 - 1].get('tactic', '')) in OPEN_LIKE:
                j0 -= 1
            goal = steps[j0]['example'].get('proof_state', '') or ''
            opening = [(steps[k].get('tactic') or '').strip() for k in range(j0, i + 1)]
            opening = [t for t in opening if t]
            key = (goal.strip(), tuple(opening))
            if not goal.strip() or not opening or key in seen:
                continue
            seen.add(key)
            gen.append({'goal': goal, 'opening': opening})
            cnt += 1
        per_thm.append(cnt)
        break  # gold 정리당 attempt 1개

with open('data/grpo_rollouts/opener_gen_sub.jsonl', 'w') as f:
    for r in gen:
        f.write(json.dumps(r, ensure_ascii=False) + '\n')

n_multi = sum(1 for c in per_thm if c >= 2)
print(f"정리 {n_thm}개 처리")
print(f"opening 예시 총 {len(gen)}개 (기존 whole-theorem 147 대비)")
print(f"  정리당 평균 분해지점 {sum(per_thm)/max(len(per_thm),1):.1f}개, 2+ 분해 정리 {n_multi}개")
print(f"  → subgoal opening(2번째 이후) 추가분 ≈ {len(gen)-n_thm}개")
print("저장: data/grpo_rollouts/opener_gen_sub.jsonl")
print("\n=== 샘플(subgoal opening 예시) ===")
shown = 0
for r in gen:
    if shown >= 3:
        break
    goal1 = r['goal'].replace('\n', ' ')[:90]
    print(f"  goal: {goal1}")
    print(f"  opening: {r['opening']}")
    shown += 1
