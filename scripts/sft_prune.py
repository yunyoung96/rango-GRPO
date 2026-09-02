#!/usr/bin/env python3
"""검사 실패 행을 **지점 단위**로 제거하고 재셔플. 사용: sft_prune.py <pairs.jsonl> <drop_idx_file> [상한비율=0.01]"""
import json, sys, os
sys.path.insert(0, "scripts")
PATH, DROP = sys.argv[1], sys.argv[2]; CAP = float(sys.argv[3]) if len(sys.argv) > 3 else 0.01
rows = [json.loads(l) for l in open(PATH)]
bad = {int(x) for x in open(DROP).read().split() if x.strip()}
pts = {(rows[i]["proj"], rows[i]["thm"], rows[i]["thmi"], rows[i]["k"]) for i in bad if i < len(rows)}
keep = [r for r in rows if (r["proj"], r["thm"], r["thmi"], r["k"]) not in pts]
dropped = len(rows) - len(keep)
assert dropped <= max(1, int(len(rows) * CAP)), f"드롭 {dropped}행 > 상한 {CAP*100}% — 체계적 문제, 프루닝 거부"
open(PATH + ".tmp", "w").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keep))
os.replace(PATH + ".tmp", PATH)
_A = sys.argv[:]; sys.argv = ["sft_build.py", "train"]
import logging; logging.disable(logging.CRITICAL)
import sft_build as SB
sys.argv = _A
n = SB.point_shuffle(PATH)
print(f"■ 프루닝: 실패 {len(bad)}행 → 지점 {len(pts)}개 → {dropped}행 제거 · 남은 {n}행 (재셔플)")
print("SFT_PRUNE_DONE")
