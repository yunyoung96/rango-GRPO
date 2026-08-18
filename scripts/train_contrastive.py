#!/usr/bin/env python3
"""**정렬 익명 구조 표현 위의 contrastive cross-encoder** — 프로젝트 전이를 겨냥한다.

## 왜 이 표현인가

이름 기반 신호(lemma 이름 subword)는 그 라이브러리의 작명 관례라 새 프로젝트로 전이하지
않고, v8 익명화 프롬프트에서는 모델이 볼 수도 없다.
`structural_repr.pair_tokens` 는 goal·premise 를 **닫힌 어휘 57개**로 익명화한다.

    goal    : le (succ zero) a        →  ( S0 ( S1 G ) V )
    premise : le (succ n) m           →  ( S0 ( S1 M ) M )

공유 상수만 같은 슬롯(S0,S1)을 받으므로 **이름은 사라지고 겹침 구조만 남는다**.
어휘에 프로젝트 고유 이름이 하나도 없어 TRAIN 에서 배운 것이 VAL/TEST 에 그대로 쓰인다.

## 왜 cross-encoder 인가

정렬 익명화는 **쌍**에 의존한다(무엇이 공유되는지 알아야 슬롯을 준다). 그래서 독립 인코딩
(bi-encoder)이 안 되고, 대신 **재랭킹 단계**에만 쓴다: tfidf/RRF 로 상위 N 개를 뽑고
cross-encoder 로 다시 정렬한다.

## 학습

InfoNCE: 사례마다 gold 1개 + hard negative(tfidf 상위) 다수를 한 묶음으로 두고
gold 의 점수가 가장 높도록 softmax cross-entropy 를 최소화한다.

사용: python3 scripts/train_contrastive.py [epochs] [학습쌍수]
"""
import json
import math
import os
import random
import sys
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
sys.path.insert(0, "src")
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
import torch  # noqa: E402
import torch.nn as nn  # noqa: E402
from tactic_gen.structural_repr import VOCAB, pair_tokens, token_ids  # noqa: E402

EPOCHS = int(sys.argv[1]) if len(sys.argv) > 1 else 6
NCASE = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
NEG = int(os.environ.get("NEG", "24"))
MAXLEN = int(os.environ.get("MAXLEN", "192"))
DEV = "cuda" if torch.cuda.is_available() else "cpu"
rng = random.Random(0)


class Encoder(nn.Module):
    """작은 Transformer. 어휘가 57개뿐이라 이 정도로 충분하다."""

    def __init__(self, d=int(os.environ.get('DIM','256')),
                 layers=int(os.environ.get('LAYERS','6')), heads=8):
        super().__init__()
        self.emb = nn.Embedding(len(VOCAB), d)
        self.pos = nn.Embedding(MAXLEN, d)
        enc = nn.TransformerEncoderLayer(d, heads, d * 4, batch_first=True,
                                         dropout=0.1, norm_first=True)
        self.tr = nn.TransformerEncoder(enc, layers)
        self.head = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d), nn.GELU(),
                                  nn.Linear(d, 1))

    def forward(self, ids, mask):
        p = torch.arange(ids.size(1), device=ids.device).unsqueeze(0)
        x = self.emb(ids) + self.pos(p)
        x = self.tr(x, src_key_padding_mask=~mask)
        x = (x * mask.unsqueeze(-1)).sum(1) / mask.sum(1, keepdim=True).clamp(min=1)
        return self.head(x).squeeze(-1)


def encode(goal: str, prem: str):
    toks, _ = pair_tokens(goal, prem, max_len=MAXLEN)
    return token_ids(toks)


def load(path, limit):
    out = []
    if not os.path.exists(path):
        return out
    for line in open(path):
        d = json.loads(line)
        if not d["pos"] or not d["neg"]:
            continue
        out.append(d)
        if len(out) >= limit:
            break
    return out


def batchify(rows):
    L = max(len(r) for r in rows)
    ids = torch.zeros(len(rows), L, dtype=torch.long)
    msk = torch.zeros(len(rows), L, dtype=torch.bool)
    for i, r in enumerate(rows):
        ids[i, :len(r)] = torch.tensor(r, dtype=torch.long)
        msk[i, :len(r)] = True
    return ids.to(DEV), msk.to(DEV)


train = load("data/cpairs_train.jsonl", NCASE)
val = load("data/cpairs_val.jsonl", 800)
print(f"train {len(train)} · val {len(val)} · device {DEV} · 어휘 {len(VOCAB)}", flush=True)
if len(train) < 50:
    print("학습 데이터 부족 — 덤프가 끝나지 않았다"), sys.exit(1)

model = Encoder().to(DEV)
opt = torch.optim.AdamW(model.parameters(), lr=float(os.environ.get('LR','5e-4')),
                        weight_decay=0.01)
sched = torch.optim.lr_scheduler.OneCycleLR(
    opt, max_lr=float(os.environ.get('LR', '5e-4')),
    total_steps=max(EPOCHS * min(len(train), NCASE), 100), pct_start=0.1)
n_params = sum(p.numel() for p in model.parameters())
print(f"파라미터 {n_params/1e6:.2f}M", flush=True)


def evaluate(data, topk=(1, 5, 10)):
    """tfidf 상위 후보를 cross-encoder 로 재정렬했을 때 gold 순위."""
    model.eval()
    hit = {k: 0 for k in topk}
    base = {k: 0 for k in topk}
    n = 0
    with torch.no_grad():
        for d in data:
            cands = d["pos"][:1] + d["neg"]
            rows = [encode(d["goal"], c) for c in cands]
            sc = []
            for i in range(0, len(rows), 64):
                ids, msk = batchify(rows[i:i + 64])
                sc += model(ids, msk).tolist()
            order = sorted(range(len(cands)), key=lambda j: -sc[j])
            r = order.index(0)
            n += 1
            # ★ 공정 비교: 재랭킹은 이 후보집합(gold+neg) 안의 순위다. tfidf 쪽도
            #   **같은 집합 안의 순위**로 맞춘다. neg 는 tfidf 상위 순서대로 저장돼
            #   있으므로 gold 의 집합 내 순위는 min(전체순위, neg 개수) 다.
            rt = min(d["pos_rank"][0], len(d["neg"]))
            for k in topk:
                hit[k] += (r < k)
                base[k] += (rt < k)
    model.train()
    return ([hit[k] / max(n, 1) * 100 for k in topk],
            [base[k] / max(n, 1) * 100 for k in topk])


best = -1.0
t0 = time.time()
for ep in range(EPOCHS):
    rng.shuffle(train)
    tot, cnt = 0.0, 0
    for d in train:
        pos = d["pos"][0]
        negs = rng.sample(d["neg"], min(NEG, len(d["neg"])))
        rows = [encode(d["goal"], pos)] + [encode(d["goal"], x) for x in negs]
        ids, msk = batchify(rows)
        sc = model(ids, msk).unsqueeze(0)              # (1, 1+NEG)
        loss = nn.functional.cross_entropy(
            sc, torch.zeros(1, dtype=torch.long, device=DEV))   # 0번이 gold
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        sched.step()
        tot += loss.item()
        cnt += 1
        if cnt % 400 == 0:
            print(f"  ep{ep} {cnt}/{len(train)} loss {tot/cnt:.4f} "
                  f"({time.time()-t0:.0f}s)", flush=True)
    r, b = evaluate(val)
    print(f"■ epoch {ep}: loss {tot/max(cnt,1):.4f} · "
          f"재랭킹 top1 {r[0]:.1f}% top5 {r[1]:.1f}% top10 {r[2]:.1f}%  "
          f"(tfidf 원본 {b[0]:.1f}/{b[1]:.1f}/{b[2]:.1f})", flush=True)
    if r[1] > best:
        best = r[1]
        torch.save(model.state_dict(), "data/contrastive_ce.pt")
        print("   → 저장 (val top5 최고)", flush=True)
print(f"\n최고 val top5 = {best:.1f}%")
