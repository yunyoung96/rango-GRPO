#!/usr/bin/env python3
"""**비선형(GBDT) 결합**으로 RRF 를 넘어설 수 있는지 본다.

## 왜 비선형인가

선형 학습은 RRF 를 못 이겼다(§10.3: 큰 셋에서 개선 0). RRF 자체가 `1/(k+순위)` 라는
비선형 변환의 합이라, 그걸 특징으로 넣어 주면 선형 모델이 RRF 를 **재현**할 뿐 넘어서지
못한다. 신호들 사이의 **상호작용**(예: "C' 가 높은데 tfidf 도 높으면 특히 좋다")은 선형으로
표현할 수 없다. 트리 모델은 그걸 배운다.

## 어떻게

  · 특징: 원시 8 + 순위백분위 8 + RRF변환 8 = 24
  · 라벨: gold=1, 나머지=0
  · 모델: HistGradientBoostingClassifier (sklearn). 사례별 순위는 예측 확률로 매긴다
  · 학습/평가 분리: train.jsonl 로 배우고 val/test.jsonl 로 **전이**를 본다

pointwise 분류지만 **트리 + 확률 순위**는 랭킹에서 잘 통하는 조합이다(불균형은 class_weight
대신 negative 다운샘플링으로 다룬다).

사용: python3 scripts/train_ranker_gbdt.py <train.jsonl> [eval1,eval2,...]
"""
import json
import random
import sys

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

FEAT = sys.argv[1] if len(sys.argv) > 1 else "data/retfeat_train_big.jsonl"
EVALS = sys.argv[2].split(",") if len(sys.argv) > 2 else []
NEG = int(sys.argv[3]) if len(sys.argv) > 3 else 40
rng = random.Random(0)

NF = 12    # A' B C D C' E tfidf 이름sub H G 가설수 메타변수비
RRF_K = 0.15
KS = (10, 20, 50)


def ranks_pct(v):
    n = len(v)
    o = sorted(range(n), key=lambda j: -v[j])
    r = [0.0] * n
    for p, j in enumerate(o):
        r[j] = p / max(n - 1, 1)
    return r


def load(path):
    cases = []
    for line in open(path):
        d = json.loads(line)
        F, gold = d["feats"], set(d["gold"])
        if not gold or len(F) < 5:
            continue
        cols = [[r[c] for r in F] for c in range(NF)]
        pcts = [ranks_pct(c) for c in cols]
        mx = [max((abs(x) for x in cols[c]), default=1.0) or 1.0 for c in range(NF)]
        X = np.array([[F[j][c] / mx[c] for c in range(NF)]
                      + [pcts[c][j] for c in range(NF)]
                      + [1.0 / (RRF_K + pcts[c][j]) for c in range(NF)]
                      for j in range(len(F))], dtype=np.float32)
        cases.append((X, gold))
    return cases


def rrf3_scores(X):
    """비교 기준: RRF(tfidf, C', 이름subword)."""
    return X[:, 2 * NF + 6] + X[:, 2 * NF + 4] + X[:, 2 * NF + 7]


def rrf_noname_scores(X):
    """**lemma 이름을 안 쓰는** 비교 기준: RRF(tfidf, C', H 지역성)."""
    return X[:, 2 * NF + 6] + X[:, 2 * NF + 4] + X[:, 2 * NF + 8]


def evaluate(score_fn, cases):
    hit = {k: 0 for k in KS}
    for X, gold in cases:
        sc = score_fn(X)
        order = np.argsort(-sc)
        r = min(int(np.where(order == g)[0][0]) for g in gold)
        for k in KS:
            hit[k] += (r < k)
    n = max(len(cases), 1)
    return [hit[k] / n * 100 for k in KS]


train = load(FEAT)
print(f"train {len(train)}건 (후보 평균 {sum(len(x[0]) for x in train)/max(len(train),1):.0f})",
      flush=True)

# ── 학습 표본: gold 전부 + negative 다운샘플 (1:40 이면 트리가 충분히 배운다) ──
Xs, ys = [], []
for X, gold in train:
    n = X.shape[0]
    negs = [j for j in range(n) if j not in gold]
    pick = list(gold) + rng.sample(negs, min(NEG, len(negs)))
    for j in pick:
        Xs.append(X[j])
        ys.append(1 if j in gold else 0)
Xs = np.array(Xs, dtype=np.float32)
ys = np.array(ys, dtype=np.int32)
print(f"학습표본 {len(ys)} (positive {int(ys.sum())})", flush=True)

clf = HistGradientBoostingClassifier(
    max_iter=400, learning_rate=0.06, max_depth=6, min_samples_leaf=40,
    l2_regularization=1.0, early_stopping=True, validation_fraction=0.15,
    random_state=0)
clf.fit(Xs, ys)
print(f"트리 {clf.n_iter_}개 학습", flush=True)


def gbdt_scores(X):
    return clf.predict_proba(X)[:, 1]


print(f"\n{'대상':32s} {'방식':12s} {'R@10':>8s} {'R@20':>8s} {'R@50':>8s}")
for nm, cs in [(FEAT, train)] + [(p, load(p)) for p in EVALS]:
    if not cs:
        continue
    a = evaluate(rrf3_scores, cs)
    c = evaluate(rrf_noname_scores, cs)
    b = evaluate(gbdt_scores, cs)
    tag = nm.split("/")[-1]
    print(f"{tag:30s} {'RRF 3-way':14s} " + " ".join(f"{x:7.1f}%" for x in a))
    print(f"{'':30s} {'RRF 이름없이':14s} " + " ".join(f"{x:7.1f}%" for x in c))
    print(f"{'':30s} {'GBDT':14s} " + " ".join(f"{x:7.1f}%" for x in b)
          + f"   ({b[2]-a[2]:+.1f}pp)")
