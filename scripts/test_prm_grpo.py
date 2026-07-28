"""PRM-GRPO(2606.20068) 배선 단위 테스트. CPU 전용, GPU 불필요.

검증 대상:
  1. φ 값과 first-error propagation
  2. **dead group 부활** — 이 방법의 존재 이유. 전부 실패한 그룹은 outcome advantage가 전부 0이라
     기존 GRPO가 통째로 버렸다(40개 중 28개). process reward는 신호를 남기는가?
  3. 첫-토큰 credit 배치 (논문: first-token > all-tokens > last-token)
  4. grpo_batch_loss_perstep 이 adv를 broadcast하면 기존 grpo_batch_loss와 동일한가(일반화 확인)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import torch  # noqa: E402

from tactic_gen.grpo import (  # noqa: E402
    group_advantages,
    grpo_batch_loss,
    grpo_batch_loss_perstep,
)
from tactic_gen.grpo_train import flatten_group  # noqa: E402
from tactic_gen.process_reward import (  # noqa: E402
    PHI_ERROR,
    PHI_SOUND_BUT_FAILED,
    PHI_SUCCESS,
    checker_process_rewards,
)

ok = 0
fail = 0


def check(name: str, cond: bool, extra: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  ✅ {name}")
    else:
        fail += 1
        print(f"  ❌ {name}  {extra}")


def step(result: str, tactic: str = "auto."):
    return {"prompt": "GOAL", "tactic": tactic, "result": result}


print("1) φ 값 + first-error propagation")
solved = {"steps": [step("VALID"), step("VALID"), step("COMPLETE")], "reward": 1.0}
check("성공 시도 → 모든 tactic +1", checker_process_rewards(solved) == [PHI_SUCCESS] * 3)

errored = {"steps": [step("VALID"), step("INVALID")], "reward": 0.0}
check(
    "유효 tactic -0.05, 에러 tactic -0.10",
    checker_process_rewards(errored) == [PHI_SOUND_BUT_FAILED, PHI_ERROR],
)

# ★ 재샘플링(max_retries>0): 에러 뒤에 같은 state 에서 다시 뽑아 이어간다.
#   INVALID 는 state 를 안 바꾸므로 뒤의 tactic 은 멀쩡하다 → 벌점을 물리면 안 된다.
after_err = {
    "steps": [step("VALID"), step("INVALID"), step("VALID"), step("VALID")],
    "reward": 0.0,
}
check(
    "재샘플링: 에러 뒤 정상 tactic 은 -0.05 (전파 안 함)",
    checker_process_rewards(after_err)
    == [PHI_SOUND_BUT_FAILED, PHI_ERROR, PHI_SOUND_BUT_FAILED, PHI_SOUND_BUT_FAILED],
)
check(
    "propagate_first_error=True 로 켜면 옛 규칙(whole-proof용)",
    checker_process_rewards(after_err, propagate_first_error=True)
    == [PHI_SOUND_BUT_FAILED, PHI_ERROR, PHI_ERROR, PHI_ERROR],
)

# ★★ 재샘플링으로 회복해서 성공한 시도 — 그 안의 INVALID 에 +1 을 주면 에러를 학습한다
recovered = {
    "steps": [step("VALID", "intros."), step("INVALID", "lia."),
              step("VALID", "simpl."), step("COMPLETE", "auto.")],
    "reward": 1.0,
}
check(
    "성공한 시도 안의 INVALID 는 여전히 -0.10 (에러를 강화하지 않음)",
    checker_process_rewards(recovered)
    == [PHI_SUCCESS, PHI_ERROR, PHI_SUCCESS, PHI_SUCCESS],
    f"{checker_process_rewards(recovered)}",
)

exhausted = {"steps": [step("VALID"), step("VALID")], "reward": 0.0}
check(
    "에러 없이 스텝 소진 → 전부 -0.05",
    checker_process_rewards(exhausted) == [PHI_SOUND_BUT_FAILED] * 2,
)

print("\n2) ★ dead group 부활 (이 방법의 존재 이유)")
# 전부 실패한 그룹: 한 시도는 즉시 에러, 다른 시도는 유효 tactic을 여러 개 쌓다가 소진.
dead_group = {
    "theorem": 7,
    "attempts": [
        {"steps": [step("INVALID", "lia.")], "reward": 0.0},
        {"steps": [step("VALID", "intros."), step("VALID", "simpl.")], "reward": 0.0},
    ],
}
_, _, adv_out, adv_proc, _ = flatten_group(dead_group, process=True)
check(
    "outcome advantage는 전부 0 (기존 GRPO가 버리는 그룹)",
    all(abs(a) < 1e-8 for a in adv_out),
    f"adv_out={adv_out}",
)
check(
    "process advantage에는 신호가 남는다",
    any(abs(a) > 1e-8 for a in adv_proc),
    f"adv_proc={adv_proc}",
)
check(
    "에러 tactic이 유효 tactic보다 낮은 advantage",
    adv_proc[0] < adv_proc[1],
    f"에러={adv_proc[0]:.3f} vs 유효={adv_proc[1]:.3f}",
)
print(f"     adv_outcome={[round(a,3) for a in adv_out]}")
print(f"     adv_process={[round(a,3) for a in adv_proc]}")

# process=False 면 기존과 동일해야 함
_, _, adv_out2, adv_proc2, _ = flatten_group(dead_group, process=False)
check("process=False면 process advantage 전부 0", all(a == 0.0 for a in adv_proc2))

print("\n3) 첫-토큰 credit 배치")
# cmask: 프롬프트 3토큰 + 완성 4토큰 / 프롬프트 5토큰 + 완성 2토큰
cmask = torch.tensor(
    [[0, 0, 0, 1, 1, 1, 1], [0, 0, 0, 0, 0, 1, 1]], dtype=torch.long
)
ba = torch.tensor([0.5, -0.5])       # outcome advantage
bap = torch.tensor([2.0, -2.0])      # process advantage
m = cmask.float()
first = torch.zeros_like(m)
idx = m.argmax(dim=1)
rows = torch.arange(m.size(0))
first[rows, idx] = m[rows, idx]
adv_tokens = ba.unsqueeze(1) * m + bap.unsqueeze(1) * first

check("첫 완성토큰 위치가 정확", idx.tolist() == [3, 5], f"idx={idx.tolist()}")
check(
    "행0: 첫 완성토큰만 outcome+process, 나머지 완성토큰은 outcome만",
    torch.allclose(adv_tokens[0], torch.tensor([0.0, 0.0, 0.0, 2.5, 0.5, 0.5, 0.5])),
    f"{adv_tokens[0].tolist()}",
)
check(
    "행1: 부호가 반대인 경우도 동일 구조",
    torch.allclose(adv_tokens[1], torch.tensor([0.0, 0.0, 0.0, 0.0, 0.0, -2.5, -0.5])),
    f"{adv_tokens[1].tolist()}",
)
check("프롬프트 토큰엔 credit 0", bool((adv_tokens * (1 - m) == 0).all()))

# 완성토큰이 하나도 없는 행(전부 패딩)은 credit 0이어야 함 — argmax가 0을 가리키는 함정
empty = torch.zeros(1, 7)
first_e = torch.zeros_like(empty)
idx_e = empty.argmax(dim=1)
first_e[torch.arange(1), idx_e] = empty[torch.arange(1), idx_e]
check("완성토큰 없는 행 → credit 0 (argmax 함정 회피)", float(first_e.sum()) == 0.0)

print("\n4) perstep 손실이 기존 손실의 일반화인가")
torch.manual_seed(0)
B, T = 3, 6
logp_new = torch.randn(B, T)
logp_old = logp_new.clone()
logp_ref = torch.randn(B, T)
mask = torch.tensor([[0, 0, 1, 1, 1, 0], [0, 1, 1, 1, 1, 1], [0, 0, 0, 1, 1, 0]])
adv = torch.tensor([1.0, -0.5, 0.25])
l1, k1 = grpo_batch_loss(logp_new, logp_old, logp_ref, adv, mask)
l2, k2 = grpo_batch_loss_perstep(
    logp_new, logp_old, logp_ref, adv.unsqueeze(1).expand(-1, T), mask
)
check(
    "adv broadcast → perstep 손실 == 기존 손실",
    torch.allclose(l1, l2) and torch.allclose(k1, k2),
    f"{float(l1):.6f} vs {float(l2):.6f}",
)

print("\n5) ★ 길이 보정 — PRM 신호가 tactic 길이에 희석되지 않는가")
# grpo_batch_loss* 는 시퀀스 목적을 토큰평균(Σ/|a|)으로 낸다.
# process advantage 는 첫 토큰 1개에만 걸리므로 보정 없으면 유효 가중치가 bap/|a| 로 희석된다.
# 실측: Coq이 거부한 tactic 은 통과한 것보다 평균 2.10배 길다(18.7 vs 8.9 토큰).
cmask2 = torch.tensor(
    [[0, 0, 0, 0, 1, 1], [0, 0, 1, 1, 1, 1]], dtype=torch.long  # 완성 2토큰 / 4토큰
)
m2 = cmask2.float()
n_tok = m2.sum(dim=1).clamp(min=1.0)                     # |a| = [2, 4]
first2 = torch.zeros_like(m2)
i2 = m2.argmax(dim=1)
first2[torch.arange(2), i2] = m2[torch.arange(2), i2]
bap2 = torch.tensor([1.0, 1.0])                          # 같은 process advantage

# 보정 없음 → 평균(Σ/|a|)을 거치면 유효 가중치가 1/|a| 로 희석
raw = (bap2.unsqueeze(1) * first2).sum(dim=1) / n_tok
# 보정 있음 → |a| 를 곱해 상쇄
fixed = ((bap2 * n_tok).unsqueeze(1) * first2).sum(dim=1) / n_tok

check(
    "보정 전: 긴 tactic 일수록 PRM 신호가 약해진다(버그)",
    abs(float(raw[0]) - 0.5) < 1e-6 and abs(float(raw[1]) - 0.25) < 1e-6,
    f"2토큰={float(raw[0]):.3f} 4토큰={float(raw[1]):.3f}",
)
check(
    "보정 후: 길이와 무관하게 동일한 PRM 신호",
    abs(float(fixed[0]) - 1.0) < 1e-6 and abs(float(fixed[1]) - 1.0) < 1e-6,
    f"2토큰={float(fixed[0]):.3f} 4토큰={float(fixed[1]):.3f}",
)
print(f"     보정 전: 2토큰={float(raw[0]):.3f}  4토큰={float(raw[1]):.3f}  ← 2배 차이")
print(f"     보정 후: 2토큰={float(fixed[0]):.3f}  4토큰={float(fixed[1]):.3f}  ← 동일")

print("\n6) denom_const — outcome 항의 length bias(Dr.GRPO 2503.20783)")
ln = torch.zeros(2, 6); lo = torch.zeros(2, 6); lref = torch.zeros(2, 6)
adv2 = torch.tensor([[0, 0, 0, 0, -1.0, -1.0], [0, 0, -1.0, -1.0, -1.0, -1.0]])
l_mean, _ = grpo_batch_loss_perstep(ln, lo, lref, adv2, cmask2, kl_beta=0.0)
l_const, _ = grpo_batch_loss_perstep(ln, lo, lref, adv2, cmask2, kl_beta=0.0, denom_const=16.0)
check("토큰평균: 길이와 무관하게 동일 기여 (긴 tactic 이 덜 벌받음)", abs(float(l_mean) - 1.0) < 1e-6)
check("상수정규화: 긴 tactic 이 토큰 수만큼 더 기여 (순수 PG)", float(l_const) < float(l_mean))
print(f"     토큰평균 loss={float(l_mean):.4f}  상수정규화 loss={float(l_const):.4f}")

print("\n7) ★ backward curriculum — GRPO 수학 성질 검증")
# 시나리오: 어려운 시작점 s_0 (거의 실패) + 쉬운 시작점 s_k (자주 성공)
#
# ❌ 잘못된 설계: 한 그룹에 섞기
#    advantage 가 "궤적이 좋았나"가 아니라 "시작점이 쉬웠나"를 학습하게 된다.
mixed_group = {
    "attempts": [
        {"steps": [step("VALID")], "reward": 0.0},   # s_0 (어려움)
        {"steps": [step("VALID")], "reward": 0.0},   # s_0
        {"steps": [step("VALID")], "reward": 0.0},   # s_0
        {"steps": [step("VALID")], "reward": 0.0},   # s_0
        {"steps": [step("COMPLETE")], "reward": 1.0},  # s_k (쉬움)
        {"steps": [step("COMPLETE")], "reward": 1.0},  # s_k
        {"steps": [step("COMPLETE")], "reward": 1.0},  # s_k
        {"steps": [step("VALID")], "reward": 0.0},     # s_k
    ]
}
_, _, adv_mixed, _, _ = flatten_group(mixed_group, process=False)
s0_adv = adv_mixed[:4]
sk_adv = adv_mixed[4:]
check(
    "❌ 섞인 그룹: s_0 시도가 전부 음수, s_k 시도가 대부분 양수",
    all(a < 0 for a in s0_adv) and sum(1 for a in sk_adv if a > 0) == 3,
    f"s0={[round(a,2) for a in s0_adv]} sk={[round(a,2) for a in sk_adv]}",
)
print(f"     s_0 시도 advantage: {[round(a,2) for a in s0_adv]}  ← 정책 잘못이 아니라 시작점이 어려웠을 뿐")
print(f"     s_k 시도 advantage: {[round(a,2) for a in sk_adv]}  ← 시작점이 쉬웠을 뿐")
print(f"     → advantage 가 '궤적 품질'이 아니라 '시작점 난이도'를 반영한다 = baseline 오염")

# ✅ 올바른 설계: 시작점마다 별도 그룹 → 각자의 baseline
g_s0 = {"attempts": [{"steps": [step("VALID")], "reward": 0.0} for _ in range(4)]}
g_sk = {"attempts": [
    {"steps": [step("COMPLETE")], "reward": 1.0},
    {"steps": [step("COMPLETE")], "reward": 1.0},
    {"steps": [step("COMPLETE")], "reward": 1.0},
    {"steps": [step("VALID")], "reward": 0.0},
]}
_, _, adv_s0, _, _ = flatten_group(g_s0, process=False)
_, _, adv_sk, _, _ = flatten_group(g_sk, process=False)
check(
    "✅ 분리된 그룹: s_0 그룹은 전멸 → advantage 0 (기존 dead group, PRM 이 담당)",
    all(abs(a) < 1e-8 for a in adv_s0),
    f"{[round(a,2) for a in adv_s0]}",
)
check(
    "✅ 분리된 그룹: s_k 그룹은 3/4 성공 → 자기 baseline 대비 신호 발생",
    any(a > 0 for a in adv_sk) and any(a < 0 for a in adv_sk),
    f"{[round(a,2) for a in adv_sk]}",
)
print(f"     s_0 그룹 advantage: {[round(a,2) for a in adv_s0]}")
print(f"     s_k 그룹 advantage: {[round(a,2) for a in adv_sk]}  ← 같은 시작점끼리 비교 = 올바른 baseline")

print(f"\n{'='*50}\n최종: 통과 {ok} / 실패 {fail}")
sys.exit(1 if fail else 0)
