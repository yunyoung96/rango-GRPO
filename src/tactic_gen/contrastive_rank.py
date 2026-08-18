"""★ 학습된 contrastive cross-encoder 로 premise 를 재랭킹한다 — 런타임 쪽.

`scripts/train_contrastive.py` 가 저장한 `data/contrastive_ce.pt` 를 읽어, goal 과 후보
premise 쌍마다 점수를 낸다.

## 표현 — 왜 전이가 가능한가

`structural_repr.pair_tokens` 가 goal·premise 쌍을 **닫힌 어휘 57개**로 익명화한다.

    goal    : le (succ zero) a   →  ( S0 ( S1 G ) V )
    premise : le (succ n) m      →  ( S0 ( S1 M ) M )

공유 상수만 같은 슬롯(S0,S1)을 받고 프로젝트 고유 이름은 하나도 남지 않는다. 그래서
TRAIN 에서 배운 것이 VAL/TEST 의 **처음 보는 프로젝트**에도 그대로 적용된다.
(v8 익명화 프롬프트와도 충돌하지 않는다 — 애초에 이름을 안 쓴다.)

## cross-encoder 인 이유와 비용

정렬 익명화는 **쌍**에 의존한다(무엇이 공유되는지 알아야 슬롯을 준다) → 독립 인코딩
(bi-encoder)이 불가능하다. 그래서 후보마다 한 번씩 돌려야 하고, 비용이 크다.
**재랭킹 전용**으로 쓴다: tfidf/RRF 로 상위 N 개만 추린 뒤 그 안에서 다시 정렬한다.
"""
from __future__ import annotations

import os

_model = None
_dev = None


def load(path: str | None = None):
    """모델을 한 번만 읽어 캐시한다."""
    global _model, _dev
    if _model is not None:
        return _model
    import torch
    from torch import nn
    from tactic_gen.structural_repr import VOCAB

    MAXLEN = int(os.environ.get("MAXLEN", "192"))
    d = int(os.environ.get("DIM", "256"))
    layers = int(os.environ.get("LAYERS", "6"))

    class Encoder(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = nn.Embedding(len(VOCAB), d)
            self.pos = nn.Embedding(MAXLEN, d)
            enc = nn.TransformerEncoderLayer(d, 8, d * 4, batch_first=True,
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

    _dev = "cuda" if torch.cuda.is_available() else "cpu"
    m = Encoder().to(_dev)
    p = path or os.environ.get("CTR_MODEL", "data/contrastive_ce.pt")
    m.load_state_dict(torch.load(p, map_location=_dev))
    m.eval()
    _model = m
    return _model


def score(goal_text: str, texts: list[str], cand: list[int],
          batch: int = 256, path: str | None = None) -> dict[int, float]:
    """`cand` 인덱스에 대해서만 점수를 낸다 (재랭킹 전용 — 전체는 너무 비싸다)."""
    import torch
    from tactic_gen.structural_repr import pair_tokens, token_ids

    m = load(path)
    MAXLEN = int(os.environ.get("MAXLEN", "192"))
    out: dict[int, float] = {}
    buf_ids, buf_idx = [], []

    def flush():
        if not buf_ids:
            return
        n = max(len(x) for x in buf_ids)
        ids = torch.zeros(len(buf_ids), n, dtype=torch.long)
        msk = torch.zeros(len(buf_ids), n, dtype=torch.bool)
        for i, v in enumerate(buf_ids):
            ids[i, :len(v)] = torch.tensor(v, dtype=torch.long)
            msk[i, :len(v)] = True
        with torch.no_grad():
            s = m(ids.to(_dev), msk.to(_dev)).float().cpu().tolist()
        for j, v in zip(buf_idx, s):
            out[j] = float(v)
        buf_ids.clear()
        buf_idx.clear()

    for j in cand:
        try:
            toks, _ = pair_tokens(goal_text, texts[j], max_len=MAXLEN)
            ids = token_ids(toks)
        except Exception:
            continue
        if not ids:
            continue
        buf_ids.append(ids[:MAXLEN])
        buf_idx.append(j)
        if len(buf_ids) >= batch:
            flush()
    flush()
    return out
