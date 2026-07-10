"""Quarry 난이도 모델 d_θ(ℓ) = θ^T φ(ℓ) + β (선형, 28차원).

- 학습: pairwise margin ranking. 성공 후보(=재귀 CoqHammer로 풀린 서브레마)는 난이도 낮음,
  실패는 높음. loss = Σ_{(s+,s-)} max(0, μ − (d(s-) − d(s+)))² + λ‖θ‖².  μ=1.0, λ=1e-3.
- feature 표준화(mean/std) 적용.
- 학습 데이터 없을 때: heuristic θ(문제 크기·논리연산·가설수 많을수록 어려움)로 초기화.

★제약: 순수 Python/numpy. OCaml 무관.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np

from model_deployment.quarry_features import FEATURE_NAMES, N_FEATURES

MU = 1.0        # margin
LAMBDA = 1e-3   # L2

# heuristic: 값이 클수록 어렵다고 보는 특징에 +가중. (표준화 후 곱해짐)
_HEURISTIC_POS = {
    "goal_tok_count": 1.0, "goal_len": 0.5, "goal_logic_ops": 1.0, "goal_arrow": 0.5,
    "num_hyps": 0.8, "hyp_tok_count_total": 0.8, "hyp_logic_ops_total": 0.7,
    "match_fix_let": 1.0, "num_goals": 0.8, "stmt_tok_count": 0.6, "stmt_logic_ops": 0.6,
    "goal_exists": 0.7, "mapset_tokens": 0.3,
}


class DifficultyModel:
    def __init__(
        self,
        theta: np.ndarray,
        beta: float,
        feat_mean: np.ndarray,
        feat_std: np.ndarray,
    ):
        self.theta = theta.astype(np.float64)
        self.beta = float(beta)
        self.feat_mean = feat_mean.astype(np.float64)
        self.feat_std = feat_std.astype(np.float64)

    # ── heuristic 초기화(학습셋 없을 때) ──
    @classmethod
    def heuristic(cls) -> "DifficultyModel":
        theta = np.zeros(N_FEATURES)
        for i, name in enumerate(FEATURE_NAMES):
            theta[i] = _HEURISTIC_POS.get(name, 0.0)
        return cls(theta, 0.0, np.zeros(N_FEATURES), np.ones(N_FEATURES))

    def _z(self, phi: np.ndarray) -> np.ndarray:
        return (phi - self.feat_mean) / self.feat_std

    def difficulty(self, phi: list[float]) -> float:
        x = self._z(np.asarray(phi, dtype=np.float64))
        return float(self.theta @ x + self.beta)

    # ── pairwise 학습 (Algorithm 2) ──
    @classmethod
    def train(
        cls,
        feats: np.ndarray,      # (M, 28)
        labels: np.ndarray,     # (M,) 1=성공(쉬움) 0=실패(어려움)
        epochs: int = 300,
        lr: float = 0.05,
    ) -> "DifficultyModel":
        feats = np.asarray(feats, dtype=np.float64)
        labels = np.asarray(labels)
        mean = feats.mean(axis=0)
        std = feats.std(axis=0)
        std[std < 1e-8] = 1.0
        Z = (feats - mean) / std

        pos = np.where(labels == 1)[0]  # 쉬움 → 낮은 난이도 목표
        neg = np.where(labels == 0)[0]  # 어려움 → 높은 난이도 목표
        theta = np.zeros(N_FEATURES)
        beta = 0.0
        if len(pos) == 0 or len(neg) == 0:
            # 한쪽만 있으면 학습 불가 → heuristic 반환(표준화만 반영)
            h = cls.heuristic()
            return cls(h.theta, 0.0, mean, std)

        rng = np.random.default_rng(0)
        pairs = [(p, n) for p in pos for n in neg]
        for _ in range(epochs):
            rng.shuffle(pairs)
            for p, n in pairs:
                dp = theta @ Z[p] + beta   # 난이도(쉬움) — 낮아야
                dn = theta @ Z[n] + beta   # 난이도(어려움) — 높아야
                margin = MU - (dn - dp)
                if margin > 0:
                    # loss = margin²  → grad wrt (dn-dp) = -2*margin
                    g = -2.0 * margin
                    # d(dn-dp)/dθ = Z[n]-Z[p]
                    grad_theta = g * (Z[n] - Z[p]) + 2 * LAMBDA * theta
                    theta -= lr * grad_theta
                    # β는 dn-dp에서 상쇄되어 무영향 → 고정 0
        return cls(theta, beta, mean, std)

    # ── 저장/로드 ──
    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "theta": self.theta.tolist(),
            "beta": self.beta,
            "feat_mean": self.feat_mean.tolist(),
            "feat_std": self.feat_std.tolist(),
            "feature_names": FEATURE_NAMES,
        }, indent=2))

    @classmethod
    def load(cls, path: Optional[Path]) -> "DifficultyModel":
        if path is None or not Path(path).exists():
            return cls.heuristic()
        d = json.loads(Path(path).read_text())
        return cls(
            np.asarray(d["theta"]), d["beta"],
            np.asarray(d["feat_mean"]), np.asarray(d["feat_std"]),
        )
