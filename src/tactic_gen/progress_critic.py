"""LeanProgress(arXiv:2502.17925) progress critic — 정의 + 추론 헬퍼.

논문 핵심(우리와 같은 **DeepSeek-Coder 1.3B**에서 Mathlib 41.4→45.2, +3.8pp, 정책 고정):
  · 타깃 = **no_goals 까지 남은 tactic 수**(distance). P(success) 가 **아니다**.
  · 백본 = **LM 자체**. (우리 기존 value_head 는 해시 BoW + MLP, qed 는 coq2vec LSTM → 둘 다 약함)
  · frontier 점수 = C(s) = α·N(s) + (1−α)·P(s),  P = 누적 log-prob,  **α = 0.2**.
    ★ α=1.0(순수 value 랭킹)이면 18.5% 로 **붕괴**한다. value 는 반드시 **소수항**이어야 한다.
      우리 rango-qed(11/40, −1) 가 정확히 이 세 가지를 다 어겼다: value 로 랭킹, P(success) 예측,
      약한 인코더. 이 모듈은 그 셋을 전부 뒤집는다.

N(s) 정의: 예측 남은스텝 n̂ 을 [0,1] 로 정규화해 **부호를 뒤집는다**(가까울수록 높다).
    N(s) = 1 − min(n̂, N_MAX) / N_MAX
"""
from __future__ import annotations

from typing import Any, Optional

import torch
import torch.nn as nn

N_MAX = 20.0  # 이 이상 남은 것은 전부 "멀다"로 취급(라벨 꼬리가 길다: 21+ 가 전체의 절반)


# ── goal 포맷 ────────────────────────────────────────────────────────────────
# 학습 데이터(인간 코퍼스)의 state 는 dataset_file.Goal.to_string() 형식이다:
#     "n, n0: nat\nH: forall m0 : nat, ...\n\n<goal>"       (가설들 \n 로, 그 뒤 빈 줄, 그 뒤 goal)
# 탐색 중에는 coqpyt 의 Goal 객체가 온다 → **같은 문자열로 맞춰야** 분포가 어긋나지 않는다.
# (repr(goal) 을 쓰면 학습 분포와 완전히 달라져 critic 이 무의미해진다 — 기존 코드들이 repr 을 쓴다)
def format_goal(g: Any) -> str:
    """⚠️ 두 종류의 Goal 을 모두 받아 **같은 문자열**로 만든다. 이게 어긋나면 critic 은 조용히 무의미해진다.

      · data_management.dataset_file.Goal  (학습 데이터 출처): hyps: list[str],  결론 = **.goal**
      · coqpyt.coq.lsp.structs.Goal        (탐색 중):          hyps: list[Hyp], 결론 = **.ty**
        (coqpyt 의 Hyp.__repr__ 가 이미 "n, n0: nat" 형식 → dataset_file 의 hyps 문자열과 동일)

    결론 필드 이름이 다르다(.goal vs .ty). .goal 만 찾으면 coqpyt Goal 에서 None → repr 폴백 →
    학습 분포와 전혀 다른 입력이 들어간다.
    """
    lines = []
    for h in getattr(g, "hyps", None) or []:
        if isinstance(h, str):
            lines.append(h)                                   # dataset_file: 이미 "n: nat"
        else:
            names, ty = getattr(h, "names", None), getattr(h, "ty", None)
            lines.append(f"{', '.join(names)}: {ty}" if names is not None else str(h))
    concl = getattr(g, "goal", None)                          # dataset_file.Goal
    if concl is None:
        concl = getattr(g, "ty", None)                        # coqpyt Goal
    if concl is None:
        raise ValueError(f"Goal 에서 결론을 못 찾음: {type(g).__name__} / {dir(g)}")
    return "\n".join(lines) + "\n\n" + str(concl)


def format_goals(goals: Optional[list]) -> str:
    if not goals:
        return ""
    return "\n===\n".join(format_goal(g) for g in goals)


# ── 모델 ─────────────────────────────────────────────────────────────────────
class ProgressHead(nn.Module):
    """LM 마지막 은닉상태(마지막 유효 토큰) → 남은 스텝 수(스칼라, softplus 로 ≥0)."""

    def __init__(self, hidden: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(hidden, 256), nn.GELU(), nn.Dropout(0.1), nn.Linear(256, 1)
        )

    def forward(self, h: torch.Tensor) -> torch.Tensor:  # (B,H) -> (B,)
        return nn.functional.softplus(self.net(h).squeeze(-1))


def last_token_hidden(model, input_ids, attention_mask) -> torch.Tensor:
    """(B,T) → (B,H). 각 시퀀스의 **마지막 비패딩 토큰**의 최종층 은닉상태."""
    out = model(
        input_ids=input_ids,
        attention_mask=attention_mask,
        output_hidden_states=True,
        use_cache=False,
    )
    h = out.hidden_states[-1]                       # (B,T,H)
    idx = attention_mask.sum(dim=1) - 1            # 마지막 유효 토큰 위치
    idx = idx.clamp(min=0)
    rows = torch.arange(h.size(0), device=h.device)
    return h[rows, idx]                            # (B,H)


class ProgressPredictor:
    """학습된 critic 로드 + 남은스텝 예측(캐시). 탐색기가 in-process 로 쓴다."""

    def __init__(
        self,
        adapter_dir: str,
        head_path: str,
        base_model: str = "deepseek-ai/deepseek-coder-1.3b-instruct",
        device: Optional[str] = None,
        max_len: int = 1024,
    ):
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.max_len = max_len
        self.tok = AutoTokenizer.from_pretrained(base_model)
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token
        base = AutoModelForCausalLM.from_pretrained(
            base_model, torch_dtype=torch.bfloat16
        )
        self.lm = PeftModel.from_pretrained(base, adapter_dir).to(self.device).eval()
        blob = torch.load(head_path, map_location="cpu")
        self.head = ProgressHead(blob["hidden"]).to(self.device)
        self.head.load_state_dict(blob["state_dict"])
        self.head.eval().to(torch.bfloat16)
        self._cache: dict[str, float] = {}

    @torch.no_grad()
    def steps_remaining(self, state: str) -> float:
        if not state:
            return N_MAX
        if state in self._cache:
            return self._cache[state]
        enc = self.tok(
            state,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_len,
        ).to(self.device)
        h = last_token_hidden(self.lm, enc["input_ids"], enc["attention_mask"])
        n = float(self.head(h.to(torch.bfloat16))[0])
        self._cache[state] = n
        return n

    def value(self, state: str) -> float:
        """N(s) ∈ [0,1] — 끝에 가까울수록 1. frontier 블렌드에 쓰는 값."""
        n = self.steps_remaining(state)
        return 1.0 - min(n, N_MAX) / N_MAX
