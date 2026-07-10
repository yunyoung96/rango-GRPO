"""QEDCartographer (arXiv:2408.09237) 충실 재구현 — Proverbot9001 핵심 구조 묘사.

Proverbot9001(Sanchez-Stern et al.)의 탐색 구조:
  - 상태(state) = 현재 obligation(goal+hyps)들의 집합. 탐색은 상태 노드의 트리.
  - policy(예측기)가 상태에서 tactic 후보를 내고, 각 tactic을 **즉시 실행**해 자식 상태 생성(AND: 한 tactic이 여러 subgoal을 낳음).
  - best-first: 우선순위 큐에서 상태를 꺼내 확장. Proverbot은 (정규화 확률) 기반, QEDCartographer는 **value 기반**.

QEDCartographer가 추가한 것 (reward-free value iteration):
  - value V(s) = γ^(s에서 QED까지 남은 step수) 를 학습(critic만; policy는 supervised 유지).
  - **AND 구조 Bellman**: V(s) = max_a γ · ∏_{s'∈children(s,a)} V(s')   (모든 subgoal이 닫혀야 하므로 곱).
  - 수집한 탐색 트리에 **value iteration**(부트스트랩)으로 V 학습. 성공경로의 closed-form 타깃은 γ^dist.
  - 상태 인코딩 = **coq2vec**: goal(hyps⊢goal) 토큰열을 LSTM autoencoder로 고정벡터화(사전학습 동결).
  - 탐색 우선순위 = V(s) (A*변형: f = depth + log_γ V).

이 모듈: coq2vec식 LSTM 인코더 + γ^dist value-iteration 학습 + product-over-subgoals backup.
Rango(Coq8.18/DeepSeek)에 맞춰 재작성(원 Proverbot은 Coq8.10.2+MPI+OCaml이라 직접 이식 불가).
"""
from __future__ import annotations
import re, math
from typing import Optional
import torch
import torch.nn as nn

GAMMA = 0.9  # 논문 권장역: 짧은 증명 선호
_TOK = re.compile(r"[A-Za-z_][A-Za-z_0-9']*|[^\sA-Za-z_]")


def tokenize_goal(goal: str, max_len: int = 128) -> list[str]:
    """coq2vec 입력: goal 문자열을 토큰열로. (원 coq2vec은 char/token LSTM.)"""
    return _TOK.findall(goal or "")[:max_len]


class Coq2Vec(nn.Module):
    """coq2vec식 상태 인코더: 토큰 임베딩 → LSTM → 마지막 hidden = 고정 상태벡터.
    (원 논문은 LSTM autoencoder로 사전학습; 여기선 value와 함께 end-to-end 학습.)"""

    def __init__(self, vocab: int = 4096, emb: int = 64, hidden: int = 128):
        super().__init__()
        self.vocab = vocab
        self.emb = nn.Embedding(vocab, emb)
        self.lstm = nn.LSTM(emb, hidden, batch_first=True)
        self.hidden = hidden

    def encode_ids(self, goal: str) -> torch.Tensor:
        ids = [hash(t) % self.vocab for t in tokenize_goal(goal)] or [0]
        return torch.tensor(ids, dtype=torch.long)

    def forward(self, batch_ids: list[torch.Tensor]) -> torch.Tensor:
        device = self.emb.weight.device
        lens = [max(1, len(x)) for x in batch_ids]
        maxl = max(lens)
        padded = torch.zeros(len(batch_ids), maxl, dtype=torch.long, device=device)
        for i, x in enumerate(batch_ids):
            if len(x):
                padded[i, : len(x)] = x.to(device)
        e = self.emb(padded)
        packed = nn.utils.rnn.pack_padded_sequence(e, lens, batch_first=True, enforce_sorted=False)
        _, (h, _) = self.lstm(packed)
        return h[-1]  # [B, hidden]


class QEDValue(nn.Module):
    """V(goal) ∈ (0,1) = γ^(남은 step수) 추정. 상태당 단일 goal 값(곱 backup은 탐색에서)."""

    def __init__(self, encoder: Coq2Vec):
        super().__init__()
        self.encoder = encoder
        self.head = nn.Sequential(nn.Linear(encoder.hidden, 64), nn.ReLU(), nn.Linear(64, 1))

    def forward(self, batch_ids):
        z = self.encoder(batch_ids)
        return torch.sigmoid(self.head(z)).squeeze(-1)


class QEDValuePredictor:
    """학습된 QEDValue 로드 + 추론(캐시). 탐색기에서 product-over-subgoals에 사용."""

    def __init__(self, ckpt: str, device: Optional[str] = None, backup: str = "product"):
        blob = torch.load(ckpt, map_location="cpu")
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        enc = Coq2Vec(**blob["enc_args"])
        self.model = QEDValue(enc).to(self.device)
        self.model.load_state_dict(blob["state_dict"])
        self.model.eval()
        self._cache: dict[str, float] = {}
        # ablation: 다중 subgoal 상태값 backup 방식. product=논문(AND), sum/min=대조군.
        assert backup in ("product", "sum", "min", "mean"), backup
        self.backup = backup

    @torch.no_grad()
    def value_goal(self, goal: str) -> float:
        if goal in self._cache:
            return self._cache[goal]
        ids = self.model.encoder.encode_ids(goal).to(self.device)
        v = self.model([ids]).item()
        self._cache[goal] = v
        return v

    def value_state(self, goals: list[str]) -> float:
        """상태(여러 subgoal)의 값 backup. 논문=product(AND: 전부 닫아야 QED).
        ablation: sum/min/mean 대조군."""
        if not goals:
            return 1.0
        vs = [self.value_goal(g) for g in goals]
        if self.backup == "product":
            p = 1.0
            for v in vs:
                p *= v
            return p
        if self.backup == "sum":
            return sum(vs) / len(vs) if False else sum(vs)  # 정규화 없는 합(대조)
        if self.backup == "min":
            return min(vs)
        return sum(vs) / len(vs)  # mean
