#!/usr/bin/env python3
"""MR1(RL): value head 학습.
입력: data/vguided_trees/*.jsonl (rango-vlog가 생성한 (goal,label,...) 레코드).
특징 v1(경량, LM 불필요): hand feats + goal 토큰 해시 BoW (src/model_deployment/value_head.py).
출력: models/value_head/value.pt. P(solvable) 예측.

사용: python3 scripts/train_value.py [--dim 512] [--epochs 200]
"""
import argparse, glob, json, os, sys
import torch
import torch.nn as nn

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from model_deployment.value_head import featurize, ValueHead, HASH_DIM_DEFAULT, N_HAND


def load_data(dim: int):
    X, y = [], []
    seen = {}
    for fp in glob.glob("data/vguided_trees/*.jsonl"):
        for line in open(fp, errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            key = (rec.get("goal", ""), rec.get("depth", 0))
            lbl = int(rec.get("label", 0))
            # 같은 (goal,depth) 중복 시 positive 우선(한 번이라도 풀렸으면 solvable)
            if key in seen:
                if lbl > seen[key][1]:
                    seen[key] = (rec, lbl)
                continue
            seen[key] = (rec, lbl)
    for rec, lbl in seen.values():
        X.append(featurize(rec.get("goal", ""), rec.get("depth", 0),
                           rec.get("cum_score", 0.0), rec.get("tactic_score", 0.0), dim))
        y.append(float(lbl))
    if not X:
        return None, None
    return torch.stack(X), torch.tensor(y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, default=HASH_DIM_DEFAULT)
    ap.add_argument("--epochs", type=int, default=200)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--out", default="models/value_head/value.pt")
    args = ap.parse_args()

    X, y = load_data(args.dim)
    if X is None:
        print("데이터 없음: data/vguided_trees/*.jsonl 먼저 생성(rango-vlog).")
        return
    n = len(y)
    pos = int(y.sum())
    print(f"샘플 {n} (pos {pos}, neg {n-pos})  특징차원 {X.shape[1]}")
    if pos == 0 or pos == n:
        print("한쪽 클래스만 존재 → 학습 무의미. 더 많은 트리 필요.")
        return

    g = torch.Generator().manual_seed(0)
    perm = torch.randperm(n, generator=g)
    X, y = X[perm], y[perm]
    nv = max(1, n // 10)
    Xtr, ytr, Xva, yva = X[nv:], y[nv:], X[:nv], y[:nv]

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = ValueHead(X.shape[1]).to(dev)
    Xtr, ytr, Xva, yva = Xtr.to(dev), ytr.to(dev), Xva.to(dev), yva.to(dev)
    pos_weight = torch.tensor([(n - pos) / max(1, pos)], device=dev)
    lossf = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)

    for ep in range(args.epochs):
        model.train()
        opt.zero_grad()
        loss = lossf(model(Xtr), ytr)
        loss.backward()
        opt.step()
        if (ep + 1) % 20 == 0:
            model.eval()
            with torch.no_grad():
                pv = torch.sigmoid(model(Xva))
                acc = ((pv > 0.5).float() == yva).float().mean().item()
                gap = (pv[yva == 1].mean() - pv[yva == 0].mean()).item() if (yva == 1).any() and (yva == 0).any() else float("nan")
            print(f"ep{ep+1} loss={loss.item():.4f} val_acc={acc:.3f} pos-neg_gap={gap:.3f}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "in_dim": X.shape[1],
                "dim": args.dim, "n_hand": N_HAND, "feat_version": "v1"}, args.out)
    print(f"저장 → {args.out}")


if __name__ == "__main__":
    main()
