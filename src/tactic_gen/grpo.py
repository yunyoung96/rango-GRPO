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
    """DeepSeek unbiased KL estimator: exp(logp_ref−logp) − (logp_ref−logp) − 1 ≥ 0. 토큰별.

    ★ 수치안정(버그수정): diff 가 큰 극단 토큰(logp≪logp_ref, ratio>e^20)에서 exp 가 inf →
      loss 에 inf 전파 or (kl_beta=0 일 때 0*inf=NaN)로 학습 전체가 망가진다. diff 를 [-20,20]로
      clamp 해 유한하게 만든다(정상 토큰 |diff|<5 는 무영향, 극단만 bound)."""
    diff = torch.clamp(logp_ref - logp, min=-20.0, max=20.0)
    return torch.exp(diff) - diff - 1.0


def group_advantages_with_gold(rewards: torch.Tensor, std_floor: float = 0.1) -> torch.Tensor:
    """LUFFY(2504.14945)용 advantage. gold(off-policy, r=1) 궤적이 그룹에 섞인 경우.

    ★ 함정 #1 (std 폭발): gold 1개 + 나머지 0 인 dead group 은 std 가 극히 작다
      (예: N=8+gold, mean=1/9, std≈0.31 → 그래도 작음; N 이 크면 더 작아짐).
      std 로 나누면 advantage 가 폭발해 발산한다. 그래서 **std_floor 로 하한**을 둔다
      (DAPO 도 std 정규화를 문제 삼아 제거하는 방향). 부호는 유지: gold=+, 실패=−.
    """
    r = rewards.float()
    mean = r.mean()
    std = r.std(unbiased=False)
    denom = max(float(std), std_floor)  # ★ 하한으로 폭발 방지
    return (r - mean) / denom


def luffy_offpolicy_weight(logp_new: torch.Tensor, gamma: float = 0.1) -> torch.Tensor:
    """LUFFY policy shaping f(x)=x/(x+γ), x=π_θ (=exp(logp_new)).

    ★ 함정 #2 (importance weight 소멸/폭발): gold 증명은 π_θ 가 극히 작다.
      - 표준 clipped ratio 를 쓰면 gradient 가 0 으로 clip → 아무것도 안 함(조용한 무효).
      - 1/π_θ 류 가중이면 폭발.
      LUFFY 해법: off-policy 토큰엔 **clip 안 걸고**, gradient 를 f(π_θ)=π_θ/(π_θ+γ) 로 reweight.
      이 함수는 낮은 π_θ 토큰을 **오히려 증폭**(x→0 에서 기울기 1/γ 로 큼)해 gold 신호를 살린다.
      detach 로 가중치만 쓰고 gradient 는 logp_new 를 통해 흐른다.
    """
    x = torch.exp(logp_new).detach()
    return x / (x + gamma)


def luffy_token_loss(
    logp_new: torch.Tensor,      # (T,) 현재 정책 하 gold 토큰 log-prob
    advantage: float,            # 이 gold 궤적의 (그룹상대) advantage (>0)
    mask: torch.Tensor,          # (T,) tactic 토큰=1 (★ state/프롬프트 토큰은 0 — 함정 #3)
    gamma: float = 0.1,
) -> torch.Tensor:
    """LUFFY off-policy 항: gold 궤적 한 개의 손실. clip 없음 + shaping.

    목적 = Σ_t [ w_t · A · logp_new_t ]   (w_t = f(π_θ), detach)
      → maximize: gold 토큰의 logp 를 A(>0) 만큼, 낮은확률 토큰은 더 크게 밀어올림.
    KL 항 없음(off-policy 는 π_ref 로 당기지 않음 — imitation 이 목적).
    ★ mask 는 반드시 tactic 토큰만. state 토큰까지 켜면 off-distribution surface 를 학습(함정 #3).
    """
    w = luffy_offpolicy_weight(logp_new, gamma)          # (T,) detach
    per_tok = w * advantage * logp_new                   # maximize 대상
    m = mask.float()
    denom = m.sum().clamp(min=1.0)
    obj = (per_tok * m).sum() / denom
    return -obj                                          # loss = −목적


def luffy_batch_loss(
    logp_new: torch.Tensor,      # (B,T) 현재 정책 하 gold 토큰 log-prob
    advantages: torch.Tensor,    # (B,) 각 gold 궤적의 (그룹상대) advantage
    mask: torch.Tensor,          # (B,T) tactic 토큰=1 (state/프롬프트=0 — 함정 #3)
    gamma: float = 0.1,
) -> torch.Tensor:
    """배치용 LUFFY off-policy 손실. luffy_token_loss 의 (B,T) 벡터화판.
    clip 없음 + KL 없음 + shaping f(π_θ). seq 별 tactic-토큰 평균 후 배치 평균."""
    w = luffy_offpolicy_weight(logp_new, gamma)          # (B,T) detach
    adv = advantages.unsqueeze(1)                        # (B,1) 브로드캐스트
    per_tok = w * adv * logp_new                         # maximize 대상
    m = mask.float()
    denom = m.sum(dim=1).clamp(min=1.0)                  # (B,)
    seq_obj = (per_tok * m).sum(dim=1) / denom
    return -seq_obj.mean()                               # loss = −목적


def luffy_kl_batch_loss(
    logp_new: torch.Tensor,      # (B,T) 현재 정책 하 gold 토큰 log-prob
    logp_ref: torch.Tensor,      # (B,T) 레퍼런스(fix) log-prob (detach)
    advantages: torch.Tensor,    # (B,)
    mask: torch.Tensor,          # (B,T) tactic 토큰=1
    gamma: float = 0.1,
    kl_beta: float = 0.04,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Conservative LUFFY: 기존 luffy_batch_loss(clip 없는 shaping)에 **KL(π_θ‖π_ref=fix) 복원**.

    ★ 진단(2026-07-16): LUFFY 는 gold 항에서 KL 을 빼서 fix 를 제약 없이 끌어냈고, 그게
      fix 가 잘 풀던 것까지 망가뜨리는 **회귀**를 냈다(covariate shift + 무제약 업데이트).
      → gold 토큰에도 D_KL(π_θ‖π_fix) 를 걸어 **fix 근처에 묶는다**. shaping 으로 gold 를 올리되
      너무 멀리 못 가게. 전체 목적(on-policy GRPO + 이 항)이 fix 로의 trust-region 이 된다.
    반환 (loss, mean_kl)."""
    w = luffy_offpolicy_weight(logp_new, gamma)          # (B,T) detach
    adv = advantages.unsqueeze(1)
    kl = kl_unbiased(logp_new, logp_ref)                 # ≥0
    per_tok = w * adv * logp_new - kl_beta * kl          # ★ KL 로 fix 근처 유지
    m = mask.float()
    denom = m.sum(dim=1).clamp(min=1.0)
    seq_obj = (per_tok * m).sum(dim=1) / denom
    seq_kl = (kl * m).sum(dim=1) / denom
    return -seq_obj.mean(), seq_kl.mean()


def sft_batch_loss(
    logp_new: torch.Tensor,      # (B,T) 현재 정책 하 completion 토큰 log-prob
    logp_ref: torch.Tensor,      # (B,T) 레퍼런스(fix) log-prob (detach) — KL anchor 용
    mask: torch.Tensor,          # (B,T) completion(tactic) 토큰=1
    kl_beta: float = 0.0,
) -> tuple[torch.Tensor, torch.Tensor]:
    """RFT / expert-iteration 의 SFT 손실 — 순수 MLE(cross-entropy).

    성공 궤적(reward=1)의 completion 토큰 logp 를 **그냥 최대화**한다. advantage/clip/group 없음.
      · self-RFT: 모델 자신의 성공 궤적 → **on-policy → covariate shift 없음**(STaR/RFT).
      · gold-SFT: 외부 gold 궤적 → fail set 직접 겨냥(단 배포시 shift 존재 — LUFFY 보다 gentle).
    kl_beta>0 이면 KL(π_θ‖fix) anchor 로 fix 근처에 묶어 과도한 drift/망각 방지.
    반환 (loss, mean_kl)."""
    kl = kl_unbiased(logp_new, logp_ref)                 # ≥0
    per_tok = logp_new - kl_beta * kl                    # maximize 대상(+ anchor)
    m = mask.float()
    denom = m.sum(dim=1).clamp(min=1.0)
    seq = (per_tok * m).sum(dim=1) / denom
    mean_kl = (kl * m).sum(dim=1) / denom
    return -seq.mean(), mean_kl.mean()


def dpo_batch_loss(
    logp_new: torch.Tensor,   # (B,T) 현재 정책의 토큰 log-prob. B는 짝수, 짝=chosen/홀=rejected 인접쌍
    logp_ref: torch.Tensor,   # (B,T) 참조(동결) 정책
    mask: torch.Tensor,       # (B,T) completion(tactic) 토큰=1
    beta: float = 0.1,
) -> tuple[torch.Tensor, torch.Tensor]:
    """DPO(Rafailov 2023) — validity 선호쌍 학습.

    우리 용법(BFS-Prover 2502.03438 식): **같은 proof state** 에서
      chosen   = Coq 가 받아들인 VALID tactic
      rejected = Coq 에러를 낸 INVALID tactic
    를 쌍으로 준다. → "깨진 tactic 을 내지 마라"를 직접 학습.
    dead group(증명 못 찾은 78%)에서도 쌍이 나오는 것이 GRPO 대비 핵심 차이.

    L = -log σ( β · [ (logπ_w - logπ_ref_w) - (logπ_l - logπ_ref_l) ] )
    반환: (loss, 평균 margin) — margin>0 이면 chosen 을 rejected 보다 선호하게 학습된 것.
    """
    m = mask.float()
    seq_new = (logp_new * m).sum(dim=1)   # (B,) DPO 표준: 시퀀스 log-prob 합
    seq_ref = (logp_ref * m).sum(dim=1)
    w_new, l_new = seq_new[0::2], seq_new[1::2]   # 짝=chosen, 홀=rejected
    w_ref, l_ref = seq_ref[0::2], seq_ref[1::2]
    logits = (w_new - w_ref) - (l_new - l_ref)    # (B/2,)
    loss = -torch.nn.functional.logsigmoid(beta * logits).mean()
    return loss, logits.detach().mean()


def awac_batch_loss(
    logp_new: torch.Tensor,      # (B,T) 현재 정책 하 데이터 tactic 토큰 log-prob
    advantages: torch.Tensor,    # (B,) 각 row 의 advantage (그룹상대, gold 포함 std_floor)
    mask: torch.Tensor,          # (B,T) tactic 토큰=1
    lam: float = 1.0,            # AWAC 온도 λ (KL-제약 강도의 역수)
    w_max: float = 20.0,         # weight 폭발 방지 클램프(AWR 표준 트릭)
) -> torch.Tensor:
    """AWAC/AWR(Peng 2019, Nair 2020) — advantage-가중 behavior cloning.

    ★ 이론 보장: argmax_π E_data[ exp(A/λ)·logπ(a|s) ] 는 **행동정책에 대한 KL-제약 하의
      정책개선 문제의 닫힌 해**다. 데이터에 있는 (s,a)만 학습(가중 BC)하므로 OOD 행동을
      절대 쿼리하지 않는다 → LUFFY 의 무제약 gold 견인(covariate shift 회귀)이 구조적으로 차단.
      gold 는 A 가 커서 강하게 모방되지만 exp(A/λ) 가중이 λ 로 제어되고 w_max 로 유계.
    clip/ratio/KL 항 없음 — 순수 가중 MLE."""
    w = torch.exp(advantages / lam).clamp(max=w_max).detach()  # (B,)
    m = mask.float()
    denom = m.sum(dim=1).clamp(min=1.0)
    seq_logp = (logp_new * m).sum(dim=1) / denom               # (B,) tactic-토큰 평균 logp
    return -(w * seq_logp).mean()


def ppo_batch_loss(
    logp_new: torch.Tensor,      # (B,T) 현재 정책 하 tactic 토큰 log-prob
    logp_old: torch.Tensor,      # (B,T) 샘플링 시점(=ref, 첫 라운드) log-prob (detach)
    values: torch.Tensor,        # (B,) 학습된 critic V(s) — state(프롬프트 끝) 가치
    returns: torch.Tensor,       # (B,) 이 시퀀스의 return(우린 proof 보상 0/1)
    mask: torch.Tensor,          # (B,T) tactic 토큰=1
    clip_eps: float = 0.2,
    value_coef: float = 0.5,
    value_bce: bool = False,
) -> tuple[torch.Tensor, torch.Tensor]:
    """PPO(actor-critic) 손실 — GRPO 와의 유일한 차이 = **학습된 V(s) baseline**.

    advantage A = return − V(s)(detach). GRPO(그룹평균 baseline)는 dead group(전부 실패)에서 A=0 이지만,
    PPO 는 A = 0 − V(s) = −V(s) 라 **전부 실패한 그룹에서도 음수 신호**가 남는다(이게 실험 요점).
    policy = PPO clip surrogate, critic = MSE(V, return). value_coef 로 두 항 합산.

    ★ value_bce=True: reward∈{0,1} 이면 V=P(provable) 확률 → critic 을 sigmoid 출력 + **BCE**로.
      MSE 보다 확률 추정에 정합적(GPT-f/HTPS provability 방식). saturation 도 BCE gradient(σ(x)−y)라 덜함.
      이 경우 values 는 이미 [0,1](sigmoid 통과) 로 들어온다고 가정.
    반환 (loss, value_loss)."""
    adv = (returns - values.detach()).unsqueeze(1)       # (B,1)
    ratio = torch.exp(logp_new - logp_old)
    surrogate = torch.minimum(ratio * adv,
                              torch.clamp(ratio, 1.0 - clip_eps, 1.0 + clip_eps) * adv)
    m = mask.float()
    denom = m.sum(dim=1).clamp(min=1.0)
    policy_obj = (surrogate * m).sum(dim=1) / denom       # (B,) 시퀀스별 tactic-토큰 평균
    if value_bce:
        _v = values.clamp(1e-6, 1 - 1e-6)                 # sigmoid 출력, 수치안정
        value_loss = -(returns * torch.log(_v) + (1 - returns) * torch.log(1 - _v))  # BCE
    else:
        value_loss = (returns - values) ** 2              # critic MSE
    loss = -policy_obj.mean() + value_coef * value_loss.mean()
    return loss, value_loss.mean()


def dapg_demo_loss(
    logp_new: torch.Tensor,      # (B,T) 현재 정책 하 gold 토큰 log-prob
    mask: torch.Tensor,          # (B,T) completion(tactic) 토큰=1
    weight: float,               # λ₀·λ₁^k  (감쇠 스케줄 스칼라)
) -> torch.Tensor:
    """DAPG(Rajeswaran 2018) demo 항 — 감쇠 가중 BC.

    g_demo = weight·∇logπ(gold), weight = λ₀·λ₁^k (k=학습 진행 step).
    초반(k작음)엔 gold 를 강하게 따르고, 모델이 따라잡을수록(k큼) weight→0 로 **gold 영향 소멸** →
    LUFFY 가 빠뜨린 covariate-shift 방지 장치. on-policy GRPO 항과 **합산**해서 쓴다.
    (LUFFY 의 f(π) shaping 대신 '감쇠 스칼라'가 gold 기여를 조절하는 게 핵심 차이.)"""
    m = mask.float()
    denom = m.sum(dim=1).clamp(min=1.0)
    seq = (logp_new * m).sum(dim=1) / denom
    return -(weight * seq).mean()


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
    clip_eps_high: float | None = None,   # DAPO clip-higher: 상한만 따로. None=대칭(1±clip_eps)
) -> tuple[torch.Tensor, torch.Tensor]:
    """배치(여러 시퀀스) GRPO 손실. 시퀀스별 loss 평균. 반환 (loss, mean_kl).

    clip_eps_high 를 주면 **비대칭 clip**(DAPO clip-higher): 하한 1−clip_eps, 상한 1+clip_eps_high.
    상한을 키우면 저확률 토큰의 확률 상승 여지를 넓혀 **entropy collapse/탐색 붕괴를 방지**한다."""
    hi = clip_eps if clip_eps_high is None else clip_eps_high
    ratio = torch.exp(logp_new - logp_old)
    adv = advantages.unsqueeze(1)                        # (B,1) → 브로드캐스트
    unclipped = ratio * adv
    clipped = torch.clamp(ratio, 1.0 - clip_eps, 1.0 + hi) * adv
    surrogate = torch.minimum(unclipped, clipped)
    kl = kl_unbiased(logp_new, logp_ref)
    per_tok = surrogate - kl_beta * kl
    m = mask.float()
    denom = m.sum(dim=1).clamp(min=1.0)                  # (B,)
    seq_obj = (per_tok * m).sum(dim=1) / denom           # 시퀀스별 완성-토큰 평균
    seq_kl = (kl * m).sum(dim=1) / denom
    return -seq_obj.mean(), seq_kl.mean()


def dapo_batch_loss(
    logp_new: torch.Tensor,     # (B,T)
    logp_old: torch.Tensor,     # (B,T)
    logp_ref: torch.Tensor,     # (B,T)
    advantages: torch.Tensor,   # (B,) 그룹상대 advantage
    mask: torch.Tensor,         # (B,T)
    clip_eps_low: float = 0.2,
    clip_eps_high: float = 0.28,
    kl_beta: float = 0.0,
) -> tuple[torch.Tensor, torch.Tensor]:
    """DAPO(2503.14476) 손실 — 4개 기법 중 loss 쪽 2개를 담는다:
      ① clip-higher: 비대칭 clip(하한 1−ε_low, 상한 1+ε_high, ε_high>ε_low) → entropy collapse 방지.
      ② token-level policy-gradient loss: 시퀀스별 평균이 아니라 **배치 전체 토큰 합 / 전체 토큰 수**로
         정규화 → 긴 시퀀스(더 많은 토큰)가 gradient 에 비례해 기여. 시퀀스평균은 긴 것을 과소가중.
      ③ KL 제거: DAPO 는 KL 정규화를 뺀다(기본 kl_beta=0). ref 로 당기지 않아 탐색 자유.
    (나머지 2개 — dynamic sampling 은 rollout(dyn_resample), overlong reward shaping 은 reward 단.)
    반환 (loss, mean_kl). mean_kl 은 모니터링용(kl_beta=0 이어도 계산)."""
    ratio = torch.exp(logp_new - logp_old)
    adv = advantages.unsqueeze(1)
    unclipped = ratio * adv
    clipped = torch.clamp(ratio, 1.0 - clip_eps_low, 1.0 + clip_eps_high) * adv
    surrogate = torch.minimum(unclipped, clipped)
    kl = kl_unbiased(logp_new, logp_ref)
    per_tok = surrogate - kl_beta * kl
    m = mask.float()
    # ★ token-level: 시퀀스별 평균(Σ/|a|) 후 배치평균이 아니라, 배치 전체 토큰에 대해 한 번에 Σ/Σ.
    tot_tok = m.sum().clamp(min=1.0)
    loss = -(per_tok * m).sum() / tot_tok
    mean_kl = (kl * m).sum() / tot_tok
    return loss, mean_kl


def overlong_shaped_rewards(
    rewards: torch.Tensor,      # (G,) binary proof-level reward
    lengths: torch.Tensor,      # (G,) 각 시도의 완성 길이(step 수 또는 토큰 수)
    cap: float,                 # 이 길이까지는 감점 없음의 상한(=L_max)
    buffer: float,              # cap 아래 buffer 구간에서 선형 감점 시작(L_max−buffer ~ L_max)
    penalty: float = 1.0,       # cap 초과 시 최대 감점량
) -> torch.Tensor:
    """DAPO overlong reward shaping(4기법 중 ④): 지나치게 긴(=한계 근접/truncation 의심) 시도의
    보상을 **소프트 선형 감점**. (cap−buffer) 이하는 감점 0, 그 위로 선형 증가, cap 초과는 penalty 로 클립.
    우리 설정: length=proof step 수, cap≈max_steps → 성공(짧게 끝난) 증명엔 거의 무해, 한계까지 끌고간
    시도만 감점 → 그룹 advantage 에서 '간신히/장황하게'를 눌러 신호 품질을 높인다."""
    r = rewards.float().clone()
    over = (lengths.float() - (cap - buffer)).clamp(min=0.0) / max(buffer, 1.0)
    return r - over.clamp(max=1.0) * penalty


def grpo_batch_loss_perstep(
    logp_new: torch.Tensor,     # (B,T)
    logp_old: torch.Tensor,     # (B,T)
    logp_ref: torch.Tensor,     # (B,T)
    adv_tokens: torch.Tensor,   # (B,T) 토큰별 advantage (PRM/process reward 유래)
    mask: torch.Tensor,         # (B,T)
    clip_eps: float = 0.2,
    kl_beta: float = 0.04,
    denom_const: float | None = None,   # None=토큰평균(Σ/|a|, 기존). 값 지정=상수 정규화(Dr.GRPO)
) -> tuple[torch.Tensor, torch.Tensor]:
    """PRM용 GRPO 손실: advantage가 시퀀스당 스칼라가 아니라 **토큰(step)별**(B,T).
    Math-Shepherd process reward를 step→token으로 펼쳐 넣으면 credit이 위치대로 걸린다.
    adv_tokens = advantages.unsqueeze(1).expand(-1,T) 이면 grpo_batch_loss와 동일(일반화)."""
    ratio = torch.exp(logp_new - logp_old)
    unclipped = ratio * adv_tokens
    clipped = torch.clamp(ratio, 1.0 - clip_eps, 1.0 + clip_eps) * adv_tokens
    surrogate = torch.minimum(unclipped, clipped)
    kl = kl_unbiased(logp_new, logp_ref)
    per_tok = surrogate - kl_beta * kl
    m = mask.float()
    # denom_const: length bias 제거(Dr.GRPO 2503.20783).
    #   토큰평균(Σ/|a|)은 순수 policy gradient(Σ)를 |a|로 나눈 것 → **긴 tactic 의 gradient 가 약해진다**.
    #   우리 데이터에서 Coq이 거부한 tactic 은 통과한 것보다 평균 2.10배 길다(18.7 vs 8.9 토큰).
    #   즉 **가장 강하게 벌줘야 할 tactic 이 가장 약하게 벌받는다.** 상수로 나누면 이 편향이 사라진다.
    denom = (
        m.sum(dim=1).clamp(min=1.0)
        if denom_const is None
        else torch.full_like(m[:, 0], float(denom_const))
    )
    seq_obj = (per_tok * m).sum(dim=1) / denom
    seq_kl = (kl * m).sum(dim=1) / denom
    return -seq_obj.mean(), seq_kl.mean()


def expand_step_advantages(step_advs: list[float], step_token_counts: list[int],
                           total_len: int) -> torch.Tensor:
    """step별 advantage → (T,) 토큰별. step_token_counts[i]=step i의 토큰 수.
    합이 total_len보다 짧으면 뒤를 0으로 패딩(프롬프트/패딩 토큰)."""
    vals = []
    for a, c in zip(step_advs, step_token_counts):
        vals.extend([float(a)] * int(c))
    vals = vals[:total_len] + [0.0] * max(0, total_len - len(vals))
    return torch.tensor(vals, dtype=torch.float32)


def selected_logprobs(logits: torch.Tensor, target_ids: torch.Tensor) -> torch.Tensor:
    """logits:(B,T,V), target_ids:(B,T) → 선택 토큰 log-prob (B,T).
    통상 logits는 위치 t가 토큰 t+1을 예측 → 호출측에서 shift 정렬해 넘길 것."""
    logp = torch.log_softmax(logits, dim=-1)
    return logp.gather(-1, target_ids.unsqueeze(-1)).squeeze(-1)
