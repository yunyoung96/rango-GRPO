"""GRPO (Group Relative Policy Optimization) 코어 — DeepSeek-Prover-V1.5(2408.08152) 학습 알고리즘.

논문 GRPO(§RL): 각 prompt q에 대해 정책 π_old로 G개 출력 {o_1..o_G} 샘플 → 각 보상 r_i
(증명 검증=binary) → **그룹 상대 advantage** Â_i = (r_i − mean(r)) / (std(r)+ε)
(모든 토큰에 동일 부여) → 클립 대리목적 + KL(π‖π_ref) 정규화로 정책 업데이트.

목적함수(논문식):
  J = E[ (1/G)Σ_i (1/|o_i|)Σ_t  min(ρ_{i,t} Â_i, clip(ρ_{i,t},1−ε,1+ε) Â_i)  − β D_KL(π‖π_ref) ]
  ρ_{i,t} = π_θ(o_{i,t}|·)/π_old(o_{i,t}|·)
  D_KL(π‖π_ref) = π_ref/π − log(π_ref/π) − 1   (논문 unbiased estimator, 항상 ≥0)

이 모듈은 순수 텐서 연산만(모델/Coq 무관) → 단위테스트 가능. 학습 루프는 grpo_train.py.
"""
from __future__ import annotations

import torch

EPS_STD = 1e-4  # advantage 표준화 안정항


def group_advantages(rewards: torch.Tensor) -> torch.Tensor:
    """그룹 내 보상 → 상대 advantage. rewards:(G,) → (G,).
    표준편차 0(전부 동일 보상)이면 advantage 0(학습 신호 없음)."""
    r = rewards.float()
    mean = r.mean()
    std = r.std(unbiased=False)
    if std < EPS_STD:
        return torch.zeros_like(r)
    return (r - mean) / (std + EPS_STD)


def kl_unbiased(logp: torch.Tensor, logp_ref: torch.Tensor) -> torch.Tensor:
    """DeepSeek unbiased KL estimator: exp(logp_ref−logp) − (logp_ref−logp) − 1 ≥ 0. 토큰별."""
    diff = logp_ref - logp
    return torch.exp(diff) - diff - 1.0


def grpo_token_loss(
    logp_new: torch.Tensor,     # (T,) 현재 정책 π_θ 하의 선택 토큰 log-prob
    logp_old: torch.Tensor,     # (T,) 샘플링 시점 π_old log-prob (detach)
    logp_ref: torch.Tensor,     # (T,) 레퍼런스 π_ref log-prob (detach)
    advantage: float,           # 이 시퀀스(그룹상대) advantage Â_i (스칼라)
    mask: torch.Tensor,         # (T,) 완성(completion) 토큰=1, 프롬프트/패딩=0
    clip_eps: float = 0.2,
    kl_beta: float = 0.04,
) -> tuple[torch.Tensor, torch.Tensor]:
    """한 시퀀스의 GRPO 손실(= −목적). 반환 (loss, mean_kl).
    토큰 평균은 mask 기준(완성 토큰만). advantage는 모든 토큰에 동일."""
    ratio = torch.exp(logp_new - logp_old)              # ρ_{i,t}
    unclipped = ratio * advantage
    clipped = torch.clamp(ratio, 1.0 - clip_eps, 1.0 + clip_eps) * advantage
    surrogate = torch.minimum(unclipped, clipped)       # min() → 보수적
    kl = kl_unbiased(logp_new, logp_ref)
    per_tok = surrogate - kl_beta * kl                  # 목적(최대화 대상)
    m = mask.float()
    denom = m.sum().clamp(min=1.0)
    obj = (per_tok * m).sum() / denom
    mean_kl = (kl * m).sum() / denom
    return -obj, mean_kl                                # loss = −목적


def grpo_batch_loss(
    logp_new: torch.Tensor,     # (B,T)
    logp_old: torch.Tensor,     # (B,T)
    logp_ref: torch.Tensor,     # (B,T)
    advantages: torch.Tensor,   # (B,) 그룹상대 advantage (각 시퀀스)
    mask: torch.Tensor,         # (B,T)
    clip_eps: float = 0.2,
    kl_beta: float = 0.04,
) -> tuple[torch.Tensor, torch.Tensor]:
    """배치(여러 시퀀스) GRPO 손실. 시퀀스별 loss 평균. 반환 (loss, mean_kl)."""
    ratio = torch.exp(logp_new - logp_old)
    adv = advantages.unsqueeze(1)                        # (B,1) → 브로드캐스트
    unclipped = ratio * adv
    clipped = torch.clamp(ratio, 1.0 - clip_eps, 1.0 + clip_eps) * adv
    surrogate = torch.minimum(unclipped, clipped)
    kl = kl_unbiased(logp_new, logp_ref)
    per_tok = surrogate - kl_beta * kl
    m = mask.float()
    denom = m.sum(dim=1).clamp(min=1.0)                  # (B,)
    seq_obj = (per_tok * m).sum(dim=1) / denom           # 시퀀스별 완성-토큰 평균
    seq_kl = (kl * m).sum(dim=1) / denom
    return -seq_obj.mean(), seq_kl.mean()


def selected_logprobs(logits: torch.Tensor, target_ids: torch.Tensor) -> torch.Tensor:
    """logits:(B,T,V), target_ids:(B,T) → 선택 토큰 log-prob (B,T).
    통상 logits는 위치 t가 토큰 t+1을 예측 → 호출측에서 shift 정렬해 넘길 것."""
    logp = torch.log_softmax(logits, dim=-1)
    return logp.gather(-1, target_ids.unsqueeze(-1)).squeeze(-1)
