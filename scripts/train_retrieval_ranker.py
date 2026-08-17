#!/usr/bin/env python3
"""검색 랭커를 **pairwise 로 학습**한다 (oracle 상한 76.9% 와의 격차를 메우려고).

## 왜 pointwise 가 실패했나

앞선 시도(로지스틱 회귀, pointwise)는 R@50 60.6% 로 RRF(68.2%) 보다 나빴다. 이유가 있다.

  · pointwise 는 "이 후보가 gold 인가" 를 맞히려 한다 — 1:400 불균형이라 전부 0 이라 해도 손해가 없다
  · 랭킹은 **상대 비교**가 본질이다: gold 가 나머지보다 위면 된다
  · 특징 스케일이 제각각인데 정규화를 안 했다 (tfidf 는 0~0.3, C' 는 0~1)

그래서 여기서는 **pairwise(RankNet)** 로 간다: `loss = log(1 + exp(-(s⁺ - s⁻)))`.
그리고 원시값 대신 **사례 내 순위 백분위**를 특징으로 쓴다 — 스케일 불변이고,
RRF 가 잘 되는 이유(순위 기반)를 학습이 그대로 이어받는다.

## 특징 (후보마다 16개)

    원시 8개 : A' 매칭크기 · B head · C 연산자 · D 모양 · C' 결론head · E 가설매칭
               · tfidf · 이름subword
    순위 8개 : 위 각각의 **사례 내 순위 백분위**(0=최상위)

## 평가

train/test 를 사례 단위로 나눠 R@10/20/50 을 잰다. RRF 3-way 를 같은 test 에서 함께 낸다.

사용: python3 scripts/train_retrieval_ranker.py <feat.jsonl> [epochs]
"""
import json
import math
import random
import sys

FEAT = sys.argv[1] if len(sys.argv) > 1 else "data/retfeat_train.jsonl"
EPOCHS = int(sys.argv[2]) if len(sys.argv) > 2 else 25
# ★ 전이 검증: TRAIN 에서 배운 가중치를 **학습에 없는 split** 에 그대로 적용해 본다.
EVALS = sys.argv[3].split(",") if len(sys.argv) > 3 else []
rng = random.Random(0)

NAMES = ["A'매칭크기", "B head", "C 연산자", "D 모양", "C'결론head", "E 가설매칭",
         "tfidf", "이름subword"]
NF = 8
D = NF * 3                    # 원시 + 순위백분위 + **RRF 변환**

# ★ 왜 RRF 변환 특징이 필요한가 (디버깅으로 밝힌 것)
#   RRF 는 `1/(k + 순위)` — 상위에 급격히 큰 가중을 주는 **비선형** 변환이다.
#   순위 백분위를 선형으로만 쓰면 이 모양을 표현할 수 없어서, 학습이 RRF 를 이길 수가 없다
#   (실측: pairwise 64.6% ≪ RRF 79.7%). 변환값을 특징으로 넣으면 선형 모델이 RRF 를
#   **포함**하게 되어, 최악의 경우에도 RRF 만큼은 나온다.
RRF_K = 0.15                  # 순위 백분위(0~1) 기준. 정수 순위의 K=60 에 대응


def ranks_pct(vals):
    """값 리스트 → 순위 백분위(0=최상위, 1=최하위). 스케일 불변 특징."""
    n = len(vals)
    order = sorted(range(n), key=lambda j: -vals[j])
    out = [0.0] * n
    for pos, j in enumerate(order):
        out[j] = pos / max(n - 1, 1)
    return out


cases = []
for line in open(FEAT):
    d = json.loads(line)
    F = d["feats"]
    gold = set(d["gold"])
    if not gold or len(F) < 5:
        continue
    cols = [[row[c] for row in F] for c in range(NF)]
    pcts = [ranks_pct(c) for c in cols]
    # 원시값은 스케일이 제각각(tfidf 0~0.3 vs C' 0~1) → 사례 내 최대값으로 정규화
    mx = [max((abs(v) for v in cols[c]), default=1.0) or 1.0 for c in range(NF)]
    X = [[F[j][c] / mx[c] for c in range(NF)]
         + [pcts[c][j] for c in range(NF)]
         + [1.0 / (RRF_K + pcts[c][j]) for c in range(NF)]
         for j in range(len(F))]
    cases.append((X, gold))
print(f"사례 {len(cases)}건 로드 · 후보 평균 {sum(len(x[0]) for x in cases)/max(len(cases),1):.0f}개")

rng.shuffle(cases)
# ★ 3분할. val 로 epoch 을 고르고 test 는 마지막에 한 번만 본다(과적합 방지).
n1, n2 = int(len(cases) * 0.6), int(len(cases) * 0.8)
train, val, test = cases[:n1], cases[n1:n2], cases[n2:]
print(f"  train {len(train)} / val {len(val)} / test {len(test)}")

# ★ 0 에서 시작하면 모든 점수가 같아 순서가 임의가 되고, hard negative 샘플링과 맞물려
#   순위 특징의 부호가 뒤집힌 채 수렴했다(실측: R@50 41% ≪ RRF 79.7%).
#   → **RRF 에 해당하는 해에서 출발**한다: 순위 백분위는 작을수록 좋으므로 음수 가중치.
w = [0.0] * D
for _idx in (2 * NF + 6, 2 * NF + 4, 2 * NF + 7):   # RRF변환: tfidf · C' · 이름sub
    w[_idx] = 1.0                                    # ← 이 초기해가 곧 RRF 3-way 다
lr0 = 0.002        # ★ 0.02 는 좋은 초기해(RRF)를 망가뜨렸다(loss 0.30→0.43)
NEG = 24                      # 사례당 negative 표본 (전부 쓰면 느리고 쉬운 것에 눌린다)

def _eval_w(wv, data):
    hit = 0
    for X, gold in data:
        sc = [sum(wi * xi for wi, xi in zip(wv, X[j])) for j in range(len(X))]
        order = sorted(range(len(X)), key=lambda j: -sc[j])
        hit += (min(order.index(g) for g in gold) < 50)
    return hit / max(len(data), 1) * 100


best_v, best_w = _eval_w(w, val), list(w)
print(f"  초기해(RRF) val R@50 = {best_v:.1f}%")

for ep in range(EPOCHS):
    lr = lr0 * (1 - ep / EPOCHS)
    rng.shuffle(train)
    loss_sum = 0.0
    cnt = 0
    for X, gold in train:
        n = len(X)
        negs_all = [j for j in range(n) if j not in gold]
        if not negs_all:
            continue
        # ★ hard negative 중심으로 뽑는다: 상위권(tfidf 순위 백분위가 작은) 것들이
        #   실제로 gold 를 밀어내는 경쟁자다. 무작위만 뽑으면 쉬운 쌍만 배운다.
        # hard(상위 경쟁자) + easy(전 범위) 를 섞는다. hard 만 쓰면 하위와의 구분을 못 배운다.
        negs_all.sort(key=lambda j: X[j][NF + 6])
        pool = negs_all[:40] + rng.sample(negs_all, min(40, len(negs_all)))
        for gj in gold:
            for nj in rng.sample(pool, min(NEG, len(pool))):
                dx = [X[gj][d] - X[nj][d] for d in range(D)]
                z = sum(wi * xi for wi, xi in zip(w, dx))
                z = max(-30.0, min(30.0, z))
                p = 1 / (1 + math.exp(z))        # P(순서가 틀릴 확률)
                loss_sum += math.log(1 + math.exp(-z))
                cnt += 1
                for d in range(D):
                    w[d] += lr * p * dx[d]       # gradient ascent on margin
                    w[d] -= lr * 1e-4 * w[d]     # L2
    # ★ pairwise loss 최적해 ≠ R@k 최적해다(하위 쌍의 마진을 늘리려 상위 구조를 흔든다).
    #   그래서 **val 의 R@50 으로 epoch 을 고른다**.
    v = _eval_w(w, val)
    if v > best_v:
        best_v, best_w = v, list(w)
    if ep % 5 == 0 or ep == EPOCHS - 1:
        print(f"  epoch {ep:3d}  loss {loss_sum/max(cnt,1):.4f}  val R@50 {v:.1f}%"
              f"  (best {best_v:.1f}%)")

# ── listwise 정책경사(REINFORCE) — "순서 재배열" 을 직접 최적화 ──────────────
#   점수→softmax 로 후보를 뽑는 정책으로 보고, gold 를 위로 올리면 보상을 준다.
#   pairwise 가 쌍만 보는 데 비해 **목표지표(R@k)를 직접** 겨냥한다.
w = best_w                       # pairwise 는 val 최고 epoch 을 채택
print(f"  → pairwise 채택: val R@50 {best_v:.1f}%")

wl = list(w)
best_lv, best_wl = _eval_w(wl, val), list(wl)
for ep in range(EPOCHS):
    lr = 0.002 * (1 - ep / EPOCHS)
    rng.shuffle(train)
    for X, gold in train:
        n = len(X)
        idxs = list(gold) + rng.sample([j for j in range(n) if j not in gold],
                                       min(48, max(n - len(gold), 1)))
        sc = [sum(wi * xi for wi, xi in zip(wl, X[j])) for j in idxs]
        m = max(sc)
        ex = [math.exp(min(20.0, v - m)) for v in sc]
        Z = sum(ex) or 1.0
        pr = [v / Z for v in ex]
        # 보상: gold 를 뽑으면 1, 아니면 0 → grad = (1[gold] - p) * x
        for t, j in enumerate(idxs):
            r = 1.0 if j in gold else 0.0
            coef = (r - pr[t])
            for d in range(D):
                wl[d] += lr * coef * X[j][d]
        for d in range(D):
            wl[d] -= lr * 1e-4 * wl[d]
    _v = _eval_w(wl, val)
    if _v > best_lv:
        best_lv, best_wl = _v, list(wl)
wl = best_wl
print(f"  → listwise 채택: val R@50 {best_lv:.1f}%")

KS = (10, 20, 50)


def evaluate(scorer, data):
    hit = {k: 0 for k in KS}
    for X, gold in data:
        sc = [scorer(X, j) for j in range(len(X))]
        order = sorted(range(len(X)), key=lambda j: -sc[j])
        r = min(order.index(g) for g in gold)
        for k in KS:
            hit[k] += (r < k)
    m = max(len(data), 1)
    return [hit[k] / m * 100 for k in KS]


def rrf3(X, j):
    """현재 최선안: RRF(tfidf, C', 이름subword)."""
    return X[j][2 * NF + 6] + X[j][2 * NF + 4] + X[j][2 * NF + 7]


def learned(X, j):
    return sum(wi * xi for wi, xi in zip(w, X[j]))


# ── 동적 검증 ① 초기해가 정말 RRF 와 같은 순서를 내는가 ──────────────────
_w0 = [0.0] * D
for _i in (2 * NF + 6, 2 * NF + 4, 2 * NF + 7):
    _w0[_i] = 1.0
_same = 0
for X, gold in test[:60]:
    a = sorted(range(len(X)), key=lambda j: -rrf3(X, j))[:50]
    b = sorted(range(len(X)),
               key=lambda j: -sum(wi * xi for wi, xi in zip(_w0, X[j])))[:50]
    _same += (a == b)
print(f"\n[검증①] 초기해 == RRF 3-way 순서: {_same}/60 "
      f"{'✓' if _same == 60 else '✗ (특징 구성이 틀렸다)'}")

print(f"\n■ test {len(test)}건")
print(f"   {'방식':14s} {'R@10':>8s} {'R@20':>8s} {'R@50':>8s}")
def learned_list(X, j):
    return sum(wi * xi for wi, xi in zip(wl, X[j]))


for nm, fn in (("RRF 3-way", rrf3), ("pairwise 학습", learned),
               ("listwise RL", learned_list)):
    r = evaluate(fn, test)
    print(f"   {nm:14s} " + " ".join(f"{x:7.1f}%" for x in r))

# ── 전이 평가: 다른 split 파일을 그대로 채점한다 ──────────────────────────
for path in EVALS:
    try:
        rows = []
        for line in open(path):
            d = json.loads(line)
            F, gold = d["feats"], set(d["gold"])
            if not gold or len(F) < 5:
                continue
            cols = [[r[c] for r in F] for c in range(NF)]
            pcts = [ranks_pct(c) for c in cols]
            mxv = [max((abs(v) for v in cols[c]), default=1.0) or 1.0 for c in range(NF)]
            rows.append(([[F[j][c] / mxv[c] for c in range(NF)]
                          + [pcts[c][j] for c in range(NF)]
                          + [1.0 / (RRF_K + pcts[c][j]) for c in range(NF)]
                          for j in range(len(F))], gold))
    except FileNotFoundError:
        print(f"\n   [{path}] 없음")
        continue
    if not rows:
        continue
    print(f"\n■ 전이 평가 {path} ({len(rows)}건)")
    print(f"   {'방식':14s} {'R@10':>8s} {'R@20':>8s} {'R@50':>8s}")
    for nm, fn in (("RRF 3-way", rrf3), ("pairwise 학습", learned),
                   ("listwise RL", learned_list)):
        r = evaluate(fn, rows)
        print(f"   {nm:14s} " + " ".join(f"{x:7.1f}%" for x in r))

print(f"\n   학습된 가중치 (|w| 큰 순)")
FN = NAMES + [f"순위:{x}" for x in NAMES]
for nm, wi in sorted(zip(FN, w), key=lambda x: -abs(x[1]))[:12]:
    print(f"     {nm:16s} {wi:+8.3f}")

# 학습 결과를 저장해 파이프라인에서 재사용할 수 있게 한다
with open("data/retrieval_ranker_w.json", "w") as f:
    json.dump({"w": w, "features": FN}, f)
print("\n   가중치 저장 → data/retrieval_ranker_w.json")
