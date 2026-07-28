#!/usr/bin/env python3
"""replug_lsr 순수-텐서 코어 단위테스트 (GPU 무관, CPU)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import torch
from premise_selection.replug_lsr import (
    lm_target_distribution, retriever_distribution, replug_lsr_loss, recall_at_k,
)

def approx(a, b, e=1e-5): return abs(float(a) - float(b)) < e

def test_target_sums_to_one():
    d = lm_target_distribution(torch.tensor([1.0, 2.0, 3.0]))
    assert approx(d.sum(), 1.0), d
    # 가장 큰 logp가 가장 큰 확률
    assert d.argmax().item() == 2
    print("✓ target 분포 합=1, argmax 정확")

def test_beta_sharpens():
    logp = torch.tensor([0.0, 1.0, 2.0])
    hot = lm_target_distribution(logp, beta=0.2)   # 뾰족
    cold = lm_target_distribution(logp, beta=5.0)  # 평평
    assert hot.max() > cold.max(), (hot, cold)
    print("✓ beta↓ → 분포 더 뾰족")

def test_loss_zero_when_matched():
    # retriever logit == LM logp 면 P_R==Q_LM → KL 0
    logp = torch.tensor([[0.5, 1.5, -0.3, 2.0]])
    tgt = lm_target_distribution(logp)
    loss = replug_lsr_loss(logp.clone(), tgt)
    assert approx(loss, 0.0, 1e-4), loss
    print(f"✓ 일치 시 KL≈0 (loss={float(loss):.2e})")

def test_loss_positive_when_mismatched():
    logp = torch.tensor([[3.0, 0.0, 0.0, 0.0]])
    tgt = lm_target_distribution(logp)               # premise0에 집중
    bad = torch.tensor([[0.0, 0.0, 0.0, 3.0]])       # retriever는 premise3 선호
    loss = replug_lsr_loss(bad, tgt)
    assert float(loss) > 0.5, loss
    print(f"✓ 불일치 시 KL>0 (loss={float(loss):.3f})")

def test_gradient_moves_retriever_toward_lm():
    torch.manual_seed(0)
    logp = torch.tensor([[3.0, 0.0, 0.0, 0.0]])
    tgt = lm_target_distribution(logp)
    retr = torch.zeros(1, 4, requires_grad=True)     # 균등 시작
    opt = torch.optim.SGD([retr], lr=1.0)
    l0 = float(replug_lsr_loss(retr, tgt))
    for _ in range(200):
        opt.zero_grad(); loss = replug_lsr_loss(retr, tgt); loss.backward(); opt.step()
    l1 = float(replug_lsr_loss(retr, tgt))
    assert l1 < l0, (l0, l1)
    # 학습 후 retriever가 premise0을 최선호
    assert retr.argmax().item() == 0, retr
    print(f"✓ 학습으로 KL 감소 {l0:.3f}→{l1:.3f}, retriever가 LM 선호 premise 학습")

def test_recall_at_k():
    assert recall_at_k([3, 1, 0, 2], {0}, k=2) == 0.0   # 0은 3위 → top2 밖
    assert recall_at_k([3, 1, 0, 2], {0}, k=3) == 1.0
    print("✓ recall@k 정확")

if __name__ == "__main__":
    test_target_sums_to_one()
    test_beta_sharpens()
    test_loss_zero_when_matched()
    test_loss_positive_when_mismatched()
    test_gradient_moves_retriever_toward_lm()
    test_recall_at_k()
    print("\n전체 통과 ✅")
