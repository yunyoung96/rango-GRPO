#!/usr/bin/env python3
"""학습 loss 추세 리포트 — grpo_train.py 의 --loss_log jsonl 을 읽어 '잘 내려가는지' 판정.

사용: python3 scripts/report_loss.py <loss.jsonl> [<loss.jsonl> ...]
출력: arm 별 (a) epoch 평균 (b) 전/후반 window 평균 (c) 최소제곱 기울기 (d) 판정.
※ step loss 는 배치마다 예제가 달라 노이즈가 큼 → **구간 평균·기울기**로 본다(단일 step 비교 X).
"""
import json
import sys
from pathlib import Path


def load(p):
    rows = []
    for line in Path(p).read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def slope(xs, ys):
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else 0.0


def report(p):
    rows = load(p)
    if not rows:
        print(f"  {p}: (비어있음)")
        return None
    name = Path(p).parent.parent.name
    xs = [r["step"] for r in rows]
    ys = [r["loss_win"] for r in rows]
    k = max(1, len(ys) // 5)
    first, last = sum(ys[:k]) / k, sum(ys[-k:]) / k
    sl = slope(xs, ys)
    eps = {}
    for r in rows:                     # epoch 마지막 행의 loss_ep = 그 epoch 평균
        eps[r["epoch"]] = r["loss_ep"]
    print(f"\n■ {name}  ({p})")
    print(f"   step {xs[0]}~{xs[-1]} ({len(rows)} 기록)")
    for e in sorted(eps):
        print(f"   epoch {e} 평균 loss : {eps[e]:.4f}")
    print(f"   앞 20% 평균 {first:.4f} → 뒤 20% 평균 {last:.4f}  (Δ {last - first:+.4f}, {(last - first) / first * 100:+.1f}%)")
    print(f"   최소제곱 기울기: {sl * 1000:+.5f} / 1000step")
    ok_ep = len(eps) < 2 or eps[max(eps)] < eps[min(eps)]
    verdict = "내려감 ✓" if (last < first and sl < 0) else ("보합/노이즈" if abs(last - first) < 0.02 else "★올라감")
    print(f"   판정: {verdict}" + ("" if ok_ep or len(eps) < 2 else "  (단 epoch 평균은 증가 — 확인 필요)"))
    return {"name": name, "first": first, "last": last, "slope": sl, "epochs": eps}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    outs = [report(p) for p in sys.argv[1:] if Path(p).exists()]
    outs = [o for o in outs if o]
    if len(outs) >= 2:
        print("\n■ arm 비교 (같은 gold target, 프롬프트만 다름 → 낮을수록 문맥이 gold tactic 을 잘 예측)")
        for o in outs:
            e = o["epochs"]
            print(f"   {o['name']:28s} 최종 epoch 평균 {e[max(e)]:.4f}   뒤20% {o['last']:.4f}")
        a, b = outs[0], outs[1]
        ea, eb = a["epochs"][max(a["epochs"])], b["epochs"][max(b["epochs"])]
        print(f"   Δ({a['name']} − {b['name']}) = {ea - eb:+.4f}")


if __name__ == "__main__":
    main()
