#!/usr/bin/env python3
"""ablation effectiveness 표: baseline(published Rango) 대비 비교 포함.

baseline = 각 run의 original_success(=rango.json, per-theorem gold Rango 성공여부).
각 세팅에 대해: 성공수 / baseline 대비 net / unique(baseline 못 푼 걸 품) / regress(baseline은 품, 놓침).
20 vs 40 나란히.

사용: python3 scripts/ablation_compare.py
"""
import json
import glob

SETTINGS = [
    ("rmaxts", "RMaxTS full"),
    ("rmaxts-noreward", "  −RMax reward"),
    ("rmaxts-nomerge", "  −state merge"),
    ("rmaxts-nomcts", "  −DUCB (random)"),
    ("bfs-a0", "BFS α=0 (no norm)"),
    ("bfs-prover", "BFS α=0.5 (paper)"),
    ("bfs-a1", "BFS α=1.0"),
    ("rango-portfolio", "[참고] portfolio(최고)"),
]


def best_run(alias, total):
    """해당 alias·total의 완료 run 중 성공 최대인 summary dict."""
    best = None
    for s in glob.glob("all_results/*/summary.json"):
        try:
            d = json.load(open(s))
        except Exception:
            continue
        if d.get("architecture") == alias and d.get("total") == total and d.get("done") == total:
            if best is None or d.get("success", 0) >= best.get("success", 0):
                best = d
    return best


def solved_set(run):
    return {r["idx"] for r in run["results"] if r.get("success")}


def baseline_set(total):
    """total-셋에서 published Rango(original_success) 성공 idx 집합."""
    base = {}
    for s in glob.glob("all_results/*/summary.json"):
        try:
            d = json.load(open(s))
        except Exception:
            continue
        if d.get("total") == total and d.get("done") == total:
            for r in d["results"]:
                ok = r.get("original_success")
                if ok is not None:
                    base[r["idx"]] = base.get(r["idx"], False) or ok
    return {i for i, v in base.items() if v}


def main():
    for total in (20, 40):
        base = baseline_set(total)
        print(f"\n# Ablation effectiveness @{total}  "
              f"(baseline = published Rango {len(base)}/{total})\n")
        print("| 세팅 | 성공 | vs baseline | unique | regress |")
        print("|------|------|-------------|--------|---------|")
        # baseline 행 먼저
        print(f"| **baseline (published Rango)** | **{len(base)}/{total}** | — | — | — |")
        for alias, lbl in SETTINGS:
            run = best_run(alias, total)
            if run is None:
                print(f"| {lbl} | 진행중 | — | — | — |")
                continue
            sv = solved_set(run)
            n = len(sv)
            uniq = sorted(sv - base)      # baseline 못 풀었는데 푼 것
            regr = sorted(base - sv)      # baseline 풀었는데 놓친 것
            net = n - len(base)
            print(f"| {lbl} | {n}/{total} | {net:+d} | {len(uniq)}"
                  f"{' '+str(uniq) if uniq else ''} | {len(regr)}"
                  f"{' '+str(regr) if regr else ''} |")

    print("\n## 핵심 대비 (성공률)")

    def rate(a, t):
        r = best_run(a, t)
        return (r["success"] / t) if r else None

    for label, a, b in [
        ("length-norm 효과 (BFS α=0.5 − α=0)", "bfs-prover", "bfs-a0"),
        ("MCTS(DUCB) 효과 (rmaxts full − −DUCB)", "rmaxts", "rmaxts-nomcts"),
        ("RMax reward 효과 (rmaxts full − −reward)", "rmaxts", "rmaxts-noreward"),
        ("state-merge 효과 (rmaxts full − −merge)", "rmaxts", "rmaxts-nomerge"),
    ]:
        parts = []
        for t in (20, 40):
            ra, rb = rate(a, t), rate(b, t)
            if ra is not None and rb is not None:
                parts.append(f"@{t}: {ra-rb:+.0%}p")
        if parts:
            print(f"- {label} — " + ", ".join(parts))


if __name__ == "__main__":
    main()
