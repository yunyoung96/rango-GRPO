#!/usr/bin/env python3
"""§10 도달성 매트릭스의 opener 판.
질문: opener 롤아웃이 cascade가 학습한 gold s1(leaf) subgoal '진입 상태'에 실제로 도달(방문)하는가?
  target = cascade s1 각 subgoal의 진입 state(첫 step state_key), n≈307
  visited = 주어진 롤아웃의 모든 state_key
  reach = |target ∩ visited| / |target|.  비교기준: executor(cascade-s0) ≈16.7%(§10).
사용: python3 scripts/measure_opener_reach.py <s1.jsonl> <roll1.jsonl> [roll2 ...]"""
import json, sys, re, os

def norm_ws(s):
    return re.sub(r"\s+", " ", (s or "").strip())

def load_states(path, entry_only=False):
    """롤아웃 파일의 state_key 집합. entry_only=True면 각 group 첫 step만(진입상태)."""
    exact, ws = set(), set()
    if not os.path.exists(path):
        return exact, ws, 0
    n_groups = 0
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        try:
            g = json.loads(line)
        except:
            continue
        n_groups += 1
        for a in g.get("attempts", []):
            steps = a.get("steps", [])
            use = steps[:1] if entry_only else steps
            for s in use:
                sk = s.get("state_key")
                if sk:
                    exact.add(sk); ws.add(norm_ws(sk))
    return exact, ws, n_groups

s1_path = sys.argv[1]
roll_paths = sys.argv[2:]

# target = s1 진입 상태
t_exact, t_ws, n_s1 = load_states(s1_path, entry_only=True)
print(f"# opener 도달성(§10 opener판)")
print(f"target = gold s1 진입상태 {len(t_exact)}개 (그룹 {n_s1})  ← cascade s1 closer가 배운 상태\n")
print(f"{'롤아웃':<34} {'그룹':>5} {'reach(exact)':>13} {'reach(ws완화)':>14}")
print("-" * 72)
rows_out = []
for rp in roll_paths:
    v_exact, v_ws, ng = load_states(rp, entry_only=False)
    re_ = len(t_exact & v_exact); rw = len(t_ws & v_ws)
    pe = 100 * re_ / max(len(t_exact), 1); pw = 100 * rw / max(len(t_ws), 1)
    name = os.path.basename(rp).replace(".jsonl", "")
    print(f"{name:<34} {ng:>5} {re_:>4}/{len(t_exact)} {pe:>5.1f}% {rw:>4}/{len(t_ws)} {pw:>5.1f}%")
    rows_out.append((name, ng, pe, pw))
print()
print("해석: opener-EVERY(재귀) reach가 executor(cascade-s0 ≈16.7%)보다 확실히 높으면")
print("  → opener가 gold leaf에 더 잘 도달 → per-state opener 재학습 가치 큼.")
print("  ※ 롤아웃마다 정리집합·그룹수 다르면 절대치는 대략치(그룹수 적으면 reach 하향편향).")
