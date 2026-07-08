#!/usr/bin/env python3
"""각 기법이 baseline(1000-run)이 못 푸는 정리를 풀었는지(unique solve)와 강점 집계.
- baseline 기준: all_results/baseline600 (379/1000). 이게 '베이스라인이 풀 수 있는 것'의 최대 집합.
- 각 기법 run: 성공 idx 중 baseline이 실패한 idx = unique solve(강점).
- 회귀: baseline이 풀었는데 기법이 실패한 idx(해당 eval 범위 내).
사용: python3 scripts/unique_solves.py [--md all_log/unique_solves.md]
"""
import argparse, glob, json, os


def load_summary(path):
    try:
        d = json.load(open(path))
    except Exception:
        return None
    return d


def solved_idx(d):
    return {x.get("idx") for x in d.get("results", []) if x.get("success")}


def all_idx(d):
    return {x.get("idx") for x in d.get("results", [])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default="all_log/unique_solves.md")
    ap.add_argument("--baseline", default="all_results/baseline600/summary.json")
    args = ap.parse_args()

    base = load_summary(args.baseline)
    base_solved = solved_idx(base)
    print(f"baseline: {len(base_solved)} solved (of {base.get('total')})")

    # 기법별 최고 run(성공수 최대) 선택
    best = {}  # arch -> (summary dict, dir)
    for s in sorted(glob.glob("all_results/*/summary.json")):
        d = load_summary(s)
        if d is None:
            continue
        arch = d.get("architecture")
        if arch in (None, "?") or "baseline" in s or d.get("total", 0) >= 500:
            continue  # baseline/1000-run 제외
        if d.get("done", 0) < 10:
            continue
        key = arch
        if key not in best or d.get("success", 0) > best[key][0].get("success", 0):
            best[key] = (d, os.path.dirname(s).split("/")[-1])

    rows = []
    union_unique = {}  # idx -> [techniques]
    for arch, (d, dr) in best.items():
        sset = solved_idx(d)
        rng = all_idx(d)  # 이 기법이 실제로 돈 idx 범위
        unique = sorted(sset - base_solved)  # baseline 실패인데 이 기법 성공
        regress = sorted((base_solved & rng) - sset)  # baseline 성공인데 이 기법 실패
        rows.append((arch, d.get("success"), d.get("done"), d.get("timeout_sec"),
                     len(unique), unique, len(regress), dr))
        for u in unique:
            union_unique.setdefault(u, []).append(arch)

    rows.sort(key=lambda r: (-r[4], -r[1]))  # unique 많은 순
    lines = ["# 기법별 unique-solve & 강점 분석\n",
             f"> baseline = 1000-run(379/1000). **unique solve = baseline 실패 정리를 이 기법이 성공** = 그 기법의 실증 강점.\n",
             f"> 주의: straight-line은 sampling 변동 있음 → unique 1~2개는 변동일 수 있음. 반복/자동화형 unique가 신뢰도 높음.\n",
             "\n| 기법 | 성공 | timeout | **unique** | unique idx | 회귀 | dir |",
             "|---|---|---|---|---|---|---|"]
    for arch, succ, done, to, nu, uidx, nr, dr in rows:
        uid = ",".join(map(str, uidx)) if uidx else "-"
        lines.append(f"| `{arch}` | {succ}/{done} | {to} | **{nu}** | {uid} | {nr} | {dr} |")

    lines.append("\n## baseline이 못 푼 걸 푼 정리 (union) — 어떤 기법이 강점 있나\n")
    lines.append("| idx | 푼 기법들 |")
    lines.append("|---|---|")
    for idx in sorted(union_unique):
        lines.append(f"| {idx} | {', '.join(union_unique[idx])} |")
    lines.append(f"\n**총 {len(union_unique)}개 정리**가 baseline 실패인데 어떤 기법이 성공(=inference 기법들의 종합 강점).")

    os.makedirs(os.path.dirname(args.md), exist_ok=True)
    with open(args.md, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"→ {args.md}")
    for arch, succ, done, to, nu, uidx, nr, dr in rows:
        print(f"  {arch:18s} {succ}/{done}  unique={nu} {uidx}  regress={nr}")


if __name__ == "__main__":
    main()
