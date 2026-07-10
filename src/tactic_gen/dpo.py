"""DPO (Direct Preference Optimization) 코어 — BFS-Prover(2502.03438) full 학습의 선호학습 항.

BFS-Prover는 expert-iteration(성공 trace SFT) + DPO(선호쌍)로 정책을 강화.
선호쌍: 같은 state x에서 성공 경로의 tactic y_w(chosen) vs 실패/막다른 tactic y_l(rejected).

DPO 손실(Rafailov et al.):
  L = −log σ( β · [ (logπ_θ(y_w|x) − logπ_ref(y_w|x)) − (logπ_θ(y_l|x) − logπ_ref(y_l|x)) ] )
  → chosen의 (정책−레퍼런스) 우위를 rejected보다 크게. β=0.1 기본.

순수 텐서 → 단위테스트 가능. 시퀀스 log-prob는 grpo_train.sequence_token_logprobs 재사용.
★OCaml 무관.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F


def dpo_loss(
    logp_w_policy: torch.Tensor,   # (B,) chosen 완성 토큰 logp 합 (정책)
    logp_l_policy: torch.Tensor,   # (B,) rejected  (정책)
    logp_w_ref: torch.Tensor,      # (B,) chosen  (레퍼런스, detach)
    logp_l_ref: torch.Tensor,      # (B,) rejected(레퍼런스, detach)
    beta: float = 0.1,
) -> tuple[torch.Tensor, torch.Tensor]:
    """반환 (loss, accuracy). accuracy = chosen이 rejected보다 선호되는 비율."""
    pi_logratios = logp_w_policy - logp_l_policy
    ref_logratios = logp_w_ref - logp_l_ref
    logits = beta * (pi_logratios - ref_logratios)
    loss = -F.logsigmoid(logits).mean()
    acc = (logits > 0).float().mean()
    return loss, acc


def masked_sum_logprob(tok_logp: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """(B,T) per-token logp + completion mask → (B,) 완성 토큰 logp 합."""
    return (tok_logp * mask.float()).sum(dim=1)
