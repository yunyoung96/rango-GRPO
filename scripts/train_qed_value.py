#!/usr/bin/env python3
"""QEDCartographer value 학습 — reward-free value iteration의 closed-form 타깃(γ^dist) 회귀.

수집 트리(data/vguided_trees/*.jsonl; goal,label,dist)에서:
  - 성공경로/조상 상태(label=1, dist>=0): 타깃 V* = γ^dist  (value iteration 수렴값)
  - 실패 상태(label=0): 타깃 0
coq2vec식 LSTM 인코더 + head를 MSE로 학습. (원 논문은 트리에 반복 Bellman 부트스트랩;
성공경로의 수렴값이 γ^dist이므로 동치 타깃으로 1-pass 회귀 — 코드 간결화.)
출력: models/qed_value/qed.pt
사용: python3 scripts/train_qed_value.py [--epochs 40]
"""
import argparse, glob, json, os, sys
import torch
import torch.nn as nn

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from model_deployment.qed_cartographer import Coq2Vec, QEDValue, GAMMA


def load(vocab):
    goals, tgts, seen = [], [], {}
    for fp in glob.glob("data/vguided_trees/*.jsonl"):
        for line in open(fp, errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            state = r.get("goal", "")
            dist = r.get("dist", -1)
            lbl = int(r.get("label", 0))
            tgt = (GAMMA ** dist) if (lbl == 1 and dist >= 0) else 0.0
            # 다중 subgoal 상태를 per-goal로 분해(=== 구분) → 각 subgoal에 동일 타깃(product backup 학습)
            for g in state.split("\n===\n"):
                g = g.strip()
                if not g:
                    continue
                if g in seen:
                    if tgt > seen[g]:
                        seen[g] = tgt
                    continue
                seen[g] = tgt
    for g, t in seen.items():
        goals.append(g); tgts.append(t)
    return goals, tgts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vocab", type=int, default=4096)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--bs", type=int, default=128)
    ap.add_argument("--out", default="models/qed_value/qed.pt")
    args = ap.parse_args()

    goals, tgts = load(args.vocab)
    if not goals:
        print("데이터 없음: data/vguided_trees/*.jsonl 필요(rango-vlog).")
        return
    pos = sum(1 for t in tgts if t > 0)
    print(f"상태 {len(goals)} (성공타깃>0: {pos})")
    if pos == 0:
        print("성공 타깃 0 → 학습 무의미.")
        return

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    enc_args = {"vocab": args.vocab, "emb": 64, "hidden": 128}
    model = QEDValue(Coq2Vec(**enc_args)).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    lossf = nn.MSELoss()
    ids = [model.encoder.encode_ids(g) for g in goals]
    y = torch.tensor(tgts, dtype=torch.float32)

    n = len(goals)
    for ep in range(args.epochs):
        model.train()
        perm = torch.randperm(n)
        tot = 0.0
        for i in range(0, n, args.bs):
            bidx = perm[i : i + args.bs]
            bids = [ids[j].to(dev) for j in bidx.tolist()]
            by = y[bidx].to(dev)
            opt.zero_grad()
            pred = model(bids)
            loss = lossf(pred, by)
            loss.backward(); opt.step()
            tot += loss.item() * len(bidx)
        if (ep + 1) % 10 == 0:
            print(f"ep{ep+1} mse={tot/n:.4f}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "enc_args": enc_args}, args.out)
    print(f"저장 → {args.out}")


if __name__ == "__main__":
    main()
