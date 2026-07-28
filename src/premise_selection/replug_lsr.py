"""REPLUG-LSR (Shi et al., NAACL 2024, arXiv:2301.12652) 코어 — retrieval을 downstream
정책(tactic LLM)의 신호로 학습하는 "LM-Supervised Retrieval".

아이디어: 어떤 premise가 좋은가? = 그 premise를 문맥에 넣었을 때 **정책이 성공 tactic에
더 높은 확률을 주는가**로 판정. retriever를 이 LM-likelihood 분포에 맞추도록(KL) 학습한다.
→ "정답 proof를 직접 안 보고, 정책의 반응(reward-유사 신호)으로 retrieval을 개선"이라는
   점에서 retrieval에 강화학습적 최적화를 적용하는 가장 feasible한 형태.

이 모듈의 순수-텐서 함수는 GPU/OCaml 무관 → 단위테스트 가능.
LM 스코어링은 grpo_train의 logp 헬퍼를 재사용한다.
★OCaml 무관.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F


# ── 순수 텐서 코어 (단위테스트 대상) ──────────────────────────────────────────

def lm_target_distribution(lm_logprobs: torch.Tensor, beta: float = 1.0) -> torch.Tensor:
    """LM likelihood 분포 Q_LM. lm_logprobs[i] = logP_policy(tactic | premise_i ⊕ state).
    softmax(logP / beta) → premise들에 대한 목표 분포. beta↓ = 더 뾰족(강한 선호)."""
    return F.softmax(lm_logprobs / beta, dim=-1)


def retriever_distribution(retr_scores: torch.Tensor, gamma: float = 1.0) -> torch.Tensor:
    """retriever 유사도 점수 → 분포 P_R. (BM25/TF-IDF 점수든 학습 reranker logit이든.)"""
    return F.softmax(retr_scores / gamma, dim=-1)


def replug_lsr_loss(retr_logits: torch.Tensor, lm_target: torch.Tensor,
                    gamma: float = 1.0) -> torch.Tensor:
    """REPLUG-LSR 손실 = KL( P_R ‖ Q_LM ). retriever(P_R)를 LM 목표(Q_LM, detach)에 맞춤.
    retr_logits: (…,M) 학습 가능한 retriever 점수. lm_target: (…,M) Q_LM (합=1, detach).
    """
    logP_R = F.log_softmax(retr_logits / gamma, dim=-1)      # log P_R
    tgt = lm_target.detach()
    # KL(P_R‖Q_LM) = Σ P_R (log P_R − log Q_LM).  P_R 는 logP_R.exp().
    P_R = logP_R.exp()
    kl = (P_R * (logP_R - tgt.clamp_min(1e-9).log())).sum(dim=-1)
    return kl.mean()


def recall_at_k(ranking: list[int], gold: set[int], k: int) -> float:
    """상위 k 안에 gold(정답 premise 인덱스)가 하나라도 있으면 1.0."""
    return 1.0 if any(i in gold for i in ranking[:k]) else 0.0


# ── LM 스코어링 (모델 forward; GPU) ───────────────────────────────────────────

def tactic_logprobs_over_premises(
    model, tokenizer, state: str, tactic: str, premises: list[str],
    build_prompt, max_len: int, device: str,
) -> torch.Tensor:
    """각 premise_i 를 문맥에 넣었을 때 logP_policy(tactic | premise_i ⊕ state) 를 계산.
    build_prompt(premise, state) → 프롬프트 문자열(포매터 규약). 반환 (M,) 텐서(합 logp).
    """
    from tactic_gen.grpo_train import build_completion_batch, sequence_token_logprobs

    prompts = [build_prompt(p, state) for p in premises]
    comps = [tactic] * len(premises)
    ids, attn, cmask = build_completion_batch(tokenizer, prompts, comps, max_len, device)
    with torch.no_grad():
        tok_logp = sequence_token_logprobs(model, ids, attn)     # (M,T)
    return (tok_logp * cmask.float()).sum(dim=1)                 # (M,) 완성토큰 logp 합
