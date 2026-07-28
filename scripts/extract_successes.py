#!/usr/bin/env python3
"""롤아웃 jsonl → 성공(reward>=1) attempt만 남긴 jsonl (EI RFT용). 성공 없는 그룹은 드롭."""
import json, sys

inp, out = sys.argv[1], sys.argv[2]
gk = ak = 0
with open(out, 'w') as f:
    for line in open(inp):
        if not line.strip():
            continue
        g = json.loads(line)
        succ = [a for a in g.get('attempts', []) if a.get('reward', 0) >= 1.0 and a.get('steps')]
        if succ:
            f.write(json.dumps({**g, 'attempts': succ}) + '\n')
            gk += 1
            ak += len(succ)
print(f'  성공 그룹 {gk} · 성공 attempt {ak} → {out}')
