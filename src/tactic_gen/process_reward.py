"""Math-Shepherd식 PRM (Wang et al. 2023, arXiv:2312.08935) 코어 — sparse reward의
credit-placement 처방. 최종 QED에만 붙는 outcome reward 대신, **각 step의 값 =
그 state에서 완성했을 때 성공하는 비율**로 per-step dense 신호를 만든다.

추정 방식(하드/MC): 같은 state를 지나는 rollout들 중 최종 성공한 비율.
tree(state-merge)나 여러 rollout이 state를 공유할 때 graded label이 나온다.
공유 없으면 outcome broadcast로 폴백(= GRPO 기존과 동일)이라 무해.

순수 파이썬 → 단위테스트 가능. GRPO advantage에 per-step으로 주입해 사용.
★OCaml 무관.
"""
from __future__ import annotations
import re
from collections import defaultdict


def state_success_values(trajectories: list[dict]) -> dict:
    """trajectories: [{"steps":[{"state_key":str, ...}], "success":bool}].
    반환 {state_key: 성공비율}. Math-Shepherd 하드 추정(경유 rollout 성공률)."""
    hit = defaultdict(int); succ = defaultdict(int)
    for tr in trajectories:
        s = 1 if tr.get("success") else 0
        seen = set()
        for st in tr.get("steps", []):
            k = st.get("state_key")
            if k is None or k in seen:  # 같은 궤적서 중복 state 1회만
                continue
            seen.add(k)
            hit[k] += 1; succ[k] += s
    return {k: succ[k] / hit[k] for k in hit}


def process_rewards(trajectory: dict, values: dict, gamma: float = 1.0) -> list[float]:
    """각 step에 process reward 부여. step_value(다음 state의 성공비율)를 그 step의 신호로.
    마지막 step은 outcome(성공=1/실패=0)로 앵커. gamma로 미래 할인 가능."""
    steps = trajectory.get("steps", [])
    n = len(steps)
    out = []
    for i, st in enumerate(steps):
        if i == n - 1:
            out.append(1.0 if trajectory.get("success") else 0.0)  # 종단 앵커
        else:
            nxt = steps[i + 1].get("state_key")
            v = values.get(nxt, 0.0)
            out.append(gamma * v)
    return out


def has_signal(values: dict, eps: float = 1e-6) -> bool:
    """graded 신호가 실제로 존재하나 (0/1 외 중간값 = state 공유가 credit 만들어냄)."""
    return any(eps < v < 1 - eps for v in values.values())


# ─────────────────────────────────────────────────────────────────────────────
# Process-Verified RL (arXiv:2606.20068, ICLR'26) — **checker 기반** process reward.
#
# 왜 이걸 쓰나: 위의 Math-Shepherd 는 rollout 들이 state 를 공유해야 graded label 이 나온다.
# 우리 GRPORolloutSearcher 는 각 시도를 독립 롤아웃으로 돌려 **state 를 공유하지 않는다** →
# state_success_values 가 전부 0/1 로 떨어져 outcome broadcast 로 폴백한다(= 기존 GRPO 와 동일,
# 효과 0). 반면 이 방식은 **coq-lsp 의 검증 결과를 그대로 per-tactic 보상으로** 쓰므로 MC 추정도,
# state 공유도 필요 없다.
#
# 게다가 우리가 논문보다 유리하다: 논문은 whole-proof 텍스트에서 tactic 경계를 역추적해야 하지만,
# 우리는 tactic 을 한 개씩 생성하고 coq-lsp 가 **어느 tactic 이 틀렸는지 정확히** 알려준다.
#
# φ (논문 값 그대로):
#   +1.00  증명이 최종 검증됨(그 시도의 모든 tactic)
#   -0.05  tactic 자체는 유효하나 증명은 실패
#   -0.10  tactic 이 에러
# first-error propagation: 첫 에러 이후의 모든 tactic 도 -0.10 을 물려받는다.
#   (우리 롤아웃은 INVALID 에서 break 하므로 에러 뒤에 tactic 이 없다 → 실질적으로 no-op 이지만,
#    롤아웃이 에러 후에도 계속하도록 바뀔 경우를 대비해 규칙을 그대로 구현해 둔다.)
PHI_SUCCESS = 1.0
PHI_SOUND_BUT_FAILED = -0.05
PHI_ERROR = -0.10


def checker_process_rewards(
    attempt: dict, propagate_first_error: bool = False
) -> list[float]:
    """한 롤아웃 시도의 step 별 process reward φ.

    attempt: {"steps": [{"result": "VALID"|"INVALID"|"COMPLETE", ...}], "reward": float}

    규칙 (step 마다 독립적으로 판정):
        result == INVALID        → PHI_ERROR            (-0.10)   ← 성공한 시도 안에 있어도 마찬가지
        그 외이고 시도가 성공     → PHI_SUCCESS          (+1.00)
        그 외이고 시도가 실패     → PHI_SOUND_BUT_FAILED (-0.05)

    ★ 재샘플링(max_retries>0) 때문에 규칙을 두 군데 고쳤다. 안 고치면 틀린다:

      (1) **성공한 시도 안의 INVALID 에 +1 을 주면 안 된다.** 재샘플링을 켜면 한 시도가
          "틀린 tactic → 다시 뽑아서 → 맞는 tactic" 을 거쳐 성공할 수 있다. 그 틀린 tactic 에
          +1 을 주면 **에러를 강화학습하게 된다**. 반드시 result 로 판정해야 한다.

      (2) **first-error propagation 을 끈다(기본값 False).** 논문(2606.20068)이 이 규칙을 쓰는 이유는
          whole-proof 생성에서 첫 에러 이후의 텍스트가 **망가진 state 위에 쌓이기** 때문이다.
          우리 롤아웃에서 INVALID 는 **state 를 바꾸지 않는다**(Coq이 거부했으므로 같은 state 에서 재샘플).
          따라서 그 뒤의 tactic 들은 멀쩡한 state 위에 있고, 벌점을 물리면 **정상 tactic 을 처벌**한다.
          (max_retries=0 인 옛 롤아웃에서는 INVALID 가 항상 마지막 step 이라 이 규칙이 no-op 이었다.)
          whole-proof 계열 롤아웃을 쓰게 되면 propagate_first_error=True 로 켤 것.
    """
    steps = attempt.get("steps", [])
    if not steps:
        return []
    solved = attempt.get("reward", 0.0) >= 1.0 or any(
        s.get("result") == "COMPLETE" for s in steps
    )

    out: list[float] = []
    seen_error = False
    for st in steps:
        is_err = st.get("result") == "INVALID"
        if is_err:
            seen_error = True
        if is_err or (propagate_first_error and seen_error):
            out.append(PHI_ERROR)
        elif solved:
            out.append(PHI_SUCCESS)
        else:
            out.append(PHI_SOUND_BUT_FAILED)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Dense-VALID reward — "인자 생성 성공(=valid tactic)"을 직접 보상 (sparse 처방).
#
# 동기: 벽 = apply/rewrite 등에서 **타입 맞는 인자(lemma/term) 생성 실패**(INVALID).
#   sparse(Qed=1)는 "이 tactic이 valid한지"에 신호가 0 → 인자 생성을 학습할 gradient가 없다.
#   → 인자-필요 tactic이 **VALID면 +보상(타입 맞는 인자 생성 성공), INVALID면 −보상.**
#   자동화/구조 tactic(auto/intros/simpl…)은 중립(0) — 항상-valid를 남발해 farming 하는 것 방지.
#
# potential 관점: 순수 raw 보너스라 Ng1999 potential-shaping(최적정책 불변)과 다르다.
#   → 완화책: (a) ARG tactic만(auto-spam 차단), (b) COMPLETE=+1로 종결이 지배, (c) 그룹 정규화.
#   엄밀 potential 변형(Φ=닫힌 goal 수 차분)은 DESIGN.md 참조.

# 인자(lemma/term/식)를 생성해야 하는 tactic — "인자 생성 성공/실패"에 dense 신호.
ARG_HEADS = {
    "apply", "eapply", "rewrite", "erewrite", "destruct", "induction", "exists",
    "specialize", "replace", "assert", "elim", "case", "inversion", "injection",
    "generalize", "pose", "set", "remember", "change", "unfold", "fold",
}


def _tactic_head(tac: str) -> str:
    t = re.sub(r"^[\-\+\*\d\.\)\s]+", "", (tac or "").strip())
    m = re.match(r"([A-Za-z_]+)", t)
    return m.group(1) if m else ""


def dense_valid_process_rewards(
    attempt: dict,
    r_valid: float = 0.1,
    r_invalid: float = -0.1,
    r_complete: float = 1.0,
    arg_only: bool = True,
) -> list[float]:
    """인자-필요 tactic의 '유효 인자 생성'을 dense 보상. checker_process_rewards 대체용.

        COMPLETE(any tactic)      → r_complete   (+1.0, 증명 종결이 지배)
        ARG tactic + VALID        → r_valid      (+, 타입 맞는 인자 생성 성공)
        ARG tactic + INVALID      → r_invalid    (−, 틀린 인자)
        비-ARG(auto/intros/simpl…) → 0            (gaming 방지 — 항상-valid 남발 무보상)

    arg_only=False 면 모든 tactic에 valid/invalid 신호(비추천 — auto-spam 위험).
    ※ 재샘플(max_retries>0)이면 성공 시도 안 INVALID 도 그대로 r_invalid(에러 강화 방지).
    """
    steps = attempt.get("steps", [])
    if not steps:
        return []
    out: list[float] = []
    for st in steps:
        res = st.get("result")
        if res == "COMPLETE":
            out.append(r_complete)
            continue
        is_arg = (not arg_only) or (_tactic_head(st.get("tactic", "")) in ARG_HEADS)
        if not is_arg:
            out.append(0.0)
        elif res == "INVALID":
            out.append(r_invalid)
        elif res == "VALID":
            out.append(r_valid)
        else:
            out.append(0.0)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 진짜 potential-based shaping (Ng, Harada, Russell 1999) — Φ는 **state s**에 정의.
#   F(s→s') = γ·Φ(s') − Φ(s).   telescoping → 최적정책 불변(invariance).
#   Φ(s) = −(goal 복잡도).  goal이 작아질수록(닫힐수록) Φ↑ → 진전에 +.
#   COMPLETE: Φ(terminal)=0(최대). INVALID: s'=s → F≈0(γ=1, state 안 바뀜).
#   ★ dense_valid 와의 차이: 이건 **state 진전**을 보상(불변), 'valid 인자 생성'을 직접 보상하진 않음.
#     validity 는 (s,a) 전이 속성이라 Φ(s) 로 표현 불가 → dense_valid 는 raw 보너스일 수밖에 없음.


def _goal_complexity(state_key: str | None) -> float:
    """Φ 재료: goal 복잡도. 여러 goal 을 세되(개수), 폴백은 길이. 작을수록 done 에 가까움."""
    if not state_key:
        return 0.0
    # coq-lsp goals 문자열: 각 goal 앞의 '⊢' 또는 목표줄 개수로 goal 수 근사. 없으면 길이/500.
    n_goals = state_key.count("⊢")
    if n_goals >= 1:
        return float(n_goals) + len(state_key) / 5000.0   # 주 신호=goal 수, 미세=크기
    return len(state_key) / 500.0                          # ⊢ 없으면 크기 프록시


def potential_shaping_rewards(attempt: dict, gamma: float = 1.0) -> list[float]:
    """진짜 PBRS: F_t = γ·Φ(s_{t+1}) − Φ(s_t), Φ(s) = −goal_complexity(s).
    checker_process_rewards/dense_valid 대체용. 최적정책 불변(Ng1999)."""
    steps = attempt.get("steps", [])
    if not steps:
        return []

    def phi(sk):
        return -_goal_complexity(sk)

    out: list[float] = []
    n = len(steps)
    for i, st in enumerate(steps):
        s = st.get("state_key")
        res = st.get("result")
        if res == "COMPLETE":
            phi_next = 0.0                                  # 종결 = 최대 potential(0)
        elif res == "INVALID":
            phi_next = phi(s)                               # state 안 바뀜 → F≈0
        elif i + 1 < n:
            phi_next = phi(steps[i + 1].get("state_key"))   # 다음 state
        else:
            phi_next = phi(s)                               # 마지막 valid·미완
        out.append(gamma * phi_next - phi(s))
    return out


def normalize_process(phis: list[float]) -> list[float]:
    """그룹 내 process reward 표준화. group_advantages 와 같은 취지(스케일 정규화)."""
    if not phis:
        return []
    n = len(phis)
    mean = sum(phis) / n
    var = sum((p - mean) ** 2 for p in phis) / n
    std = var**0.5
    if std < 1e-8:
        return [0.0] * n            # 전부 같으면 신호 없음
    return [(p - mean) / std for p in phis]
