#!/usr/bin/env python3
"""Quarry Algorithm 2 (offline): 난이도 모델 θ 학습.

입력: data/quarry_traces/traces.jsonl (quarry-trace 실행으로 수집).
  각 레코드 = {goal/stmt, success(재귀 CoqHammer로 풀렸나), depth, ...}.
처리: φ(stmt) 28차원 추출 → success=1(쉬움)/0(어려움) 라벨 → pairwise margin ranking.
출력: models/quarry_difficulty/difficulty.json.

사용:
  python3 scripts/train_quarry_difficulty.py \
      --traces data/quarry_traces/traces.jsonl \
      --out models/quarry_difficulty/difficulty.json
"""
import argparse
import json
from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from model_deployment.quarry_features import featurize_statement, N_FEATURES  # noqa: E402
from model_deployment.quarry_difficulty import DifficultyModel  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", default="data/quarry_traces/traces.jsonl")
    ap.add_argument("--out", default="models/quarry_difficulty/difficulty.json")
    ap.add_argument("--epochs", type=int, default=300)
    args = ap.parse_args()

    tp = Path(args.traces)
    if not tp.exists():
        print(f"[quarry-train] trace 없음: {tp} → heuristic θ 저장")
        DifficultyModel.heuristic().save(Path(args.out))
        return

    feats, labels = [], []
    seen = set()
    for line in tp.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        stmt = rec.get("stmt") or rec.get("goal")
        if not stmt:
            continue
        key = (stmt, rec.get("depth"))
        if key in seen:
            continue
        seen.add(key)
        feats.append(featurize_statement(stmt))
        labels.append(1 if rec.get("success") else 0)

    feats = np.asarray(feats, dtype=np.float64)
    labels = np.asarray(labels)
    n_pos = int((labels == 1).sum())
    n_neg = int((labels == 0).sum())
    print(f"[quarry-train] 샘플 {len(labels)}개 (성공 {n_pos} / 실패 {n_neg}), φ={N_FEATURES}차원")

    model = DifficultyModel.train(feats, labels, epochs=args.epochs)
    model.save(Path(args.out))
    print(f"[quarry-train] 저장 → {args.out}")

    # 학습된 가중 상위 특징 출력(해석용)
    order = np.argsort(-np.abs(model.theta))
    from model_deployment.quarry_features import FEATURE_NAMES
    print("가장 영향 큰 난이도 특징:")
    for i in order[:8]:
        print(f"  {FEATURE_NAMES[i]:22s} θ={model.theta[i]:+.3f}")


if __name__ == "__main__":
    main()
