"""MR1(RL): value head — 특징화 + 모델 정의 + 추론 헬퍼.
train_value.py(학습)와 classical_searcher.py(추론) 공용.
특징 v1(경량, LM 불필요): hand feats + goal 토큰 해시 BoW.
"""
from __future__ import annotations
import math, re
from typing import Optional
import torch
import torch.nn as nn

HASH_DIM_DEFAULT = 512
N_HAND = 8
_TOK = re.compile(r"[A-Za-z_][A-Za-z_0-9']*|[=<>+*/\\|-]+")


def hand_feats(goal: str, depth: float, cum_score: float, tactic_score: float) -> list[float]:
    g = goal or ""
    return [
        float(depth),
        float(cum_score),
        float(tactic_score),
        math.log1p(len(g)),
        float(g.count("forall")),
        float(g.count("->")),
        float(g.count(":")),
        float(g.count("=")),
    ]


def bow(goal: str, dim: int) -> torch.Tensor:
    v = torch.zeros(dim)
    for t in _TOK.findall(goal or ""):
        v[hash(t) % dim] += 1.0
    n = v.sum()
    if n > 0:
        v /= n
    return v


def featurize(goal: str, depth: float, cum_score: float, tactic_score: float, dim: int) -> torch.Tensor:
    return torch.cat([
        torch.tensor(hand_feats(goal, depth, cum_score, tactic_score), dtype=torch.float32),
        bow(goal, dim),
    ])


class ValueHead(nn.Module):
    def __init__(self, in_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 128), nn.ReLU(), nn.Dropout(0.1),
            nn.Linear(128, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


class ValuePredictor:
    """학습된 value head 로드 + P(solvable) 추론(캐시)."""

    def __init__(self, ckpt_path: str, device: Optional[str] = None):
        blob = torch.load(ckpt_path, map_location="cpu")
        self.dim = blob["dim"]
        self.in_dim = blob["in_dim"]
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = ValueHead(self.in_dim).to(self.device)
        self.model.load_state_dict(blob["state_dict"])
        self.model.eval()
        self._cache: dict[str, float] = {}

    @torch.no_grad()
    def value(self, goal: str, depth: float = 0.0, cum_score: float = 0.0, tactic_score: float = 0.0) -> float:
        key = goal
        if key in self._cache:
            return self._cache[key]
        x = featurize(goal, depth, cum_score, tactic_score, self.dim).unsqueeze(0).to(self.device)
        p = torch.sigmoid(self.model(x)).item()
        self._cache[key] = p
        return p
