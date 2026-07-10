#!/usr/bin/env python3
"""ablation effectiveness: 20 vs 40 비교표 생성.
각 세팅(rmaxts full/−reward/−merge/−DUCB, bfs α=0/0.5/1)을 first-20·first-40에서 나란히.
사용: python3 scripts/ablation_compare.py
"""
import json, glob

SETTINGS = [
    ("rmaxts", "RMaxTS full"),
    ("rmaxts-noreward", "  −RMax reward"),
    ("rmaxts-nomerge", "  −state merge"),
    ("rmaxts-nomcts", "  −DUCB (random)"),
    ("bfs-a0", "BFS α=0 (no norm)"),
    ("bfs-prover", "BFS α=0.5 (paper)"),
    ("bfs-a1", "BFS α=1.0"),
]


def best_for(alias, total):
    best = None
    for s in glob.glob("all_results/*/summary.json"):
        try:
            d = json.load(open(s))
        except Exception:
            continue
        if d.get("architecture") == alias and d.get("total") == total and d.get("done") == total:
            if best is None or d.get("success", 0) >= best:
                best = d.get("success")
    return best


def main():
    print("# Ablation effectiveness — 20 vs 40 비교\n")
    print(f"| 세팅 | @20 | @40 | @20율 | @40율 |")
    print(f"|------|-----|-----|-------|-------|")
    for alias, lbl in SETTINGS:
        s20, s40 = best_for(alias, 20), best_for(alias, 40)
        r20 = f"{s20/20:.0%}" if s20 is not None else "-"
        r40 = f"{s40/40:.0%}" if s40 is not None else "-"
        v20 = f"{s20}/20" if s20 is not None else "진행중"
        v40 = f"{s40}/40" if s40 is not None else "진행중"
        print(f"| {lbl} | {v20} | {v40} | {r20} | {r40} |")
    print("\n## 핵심 대비 (율 기준)")
    def rate(a, t):
        s = best_for(a, t); return (s / t) if s is not None else None
    for label, a, b in [("length-norm 효과(BFS α=0.5 − α=0)", "bfs-prover", "bfs-a0"),
                         ("MCTS 효과(rmaxts full − −DUCB)", "rmaxts", "rmaxts-nomcts")]:
        for t in (20, 40):
            ra, rb = rate(a, t), rate(b, t)
            if ra is not None and rb is not None:
                print(f"- {label} @{t}: {ra-rb:+.0%}p")


if __name__ == "__main__":
    main()
