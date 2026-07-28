"""LUFFY(2504.14945) 손실 단위테스트 — 함정 3개 방어 검증. CPU 전용.

함정:
  #1 std 폭발: gold 1개 + 나머지 0 → std 극소 → advantage 폭발
  #2 importance weight 소멸/폭발: gold 는 π_θ 극소 → clip 0 or 폭발
  #3 token mask: tactic 토큰만. state 토큰 켜면 off-distribution 학습
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import torch  # noqa: E402

from tactic_gen.grpo import (  # noqa: E402
    group_advantages,
    group_advantages_with_gold,
    luffy_offpolicy_weight,
    luffy_token_loss,
)

ok = fail = 0


def check(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ✅ {name}")
    else:
        fail += 1
        print(f"  ❌ {name}  {extra}")


print("1) ★ dead group 부활 — gold 주입으로 group mean != 0")
# 기존 GRPO: dead group(전부 0) → advantage 0 (학습 신호 없음)
dead = torch.tensor([0.0] * 8)
adv_old = group_advantages(dead)
check("기존: dead group advantage 전부 0", torch.allclose(adv_old, torch.zeros(8)))

# LUFFY: gold(r=1) 추가 → 9개 그룹, mean=1/9
withgold = torch.tensor([0.0] * 8 + [1.0])  # 마지막이 gold
adv_new = group_advantages_with_gold(withgold)
check("LUFFY: gold advantage > 0", adv_new[-1] > 0, f"gold adv={adv_new[-1]:.3f}")
check("LUFFY: 실패 롤아웃 advantage < 0", (adv_new[:8] < 0).all(), f"{adv_new[:8]}")
check("LUFFY: 신호 생김(전부 0 아님)", adv_new.abs().sum() > 0.1)
print(f"     advantage: 실패 {adv_new[0]:.3f} × 8, gold {adv_new[-1]:.3f}")

print("\n2) ★ 함정 #1 — std 폭발 방지")
# gold 1 + 실패 많음 → std 작음. floor 없으면 advantage 폭발
big_dead = torch.tensor([0.0] * 31 + [1.0])  # 32개 중 gold 1
raw_std = big_dead.std(unbiased=False)
adv_floored = group_advantages_with_gold(big_dead, std_floor=0.1)
adv_nofloor = (big_dead - big_dead.mean()) / raw_std  # floor 없는 버전
check("floor 없으면 advantage 큼(폭발 위험)", adv_nofloor.abs().max() > 5,
      f"max={adv_nofloor.abs().max():.1f}")
check("floor 있으면 advantage 제한됨", adv_floored.abs().max() < 10,
      f"max={adv_floored.abs().max():.2f}")
print(f"     std={raw_std:.4f} | floor無 max|A|={adv_nofloor.abs().max():.1f} | floor有 max|A|={adv_floored.abs().max():.2f}")

print("\n3) ★ 함정 #2 — importance weight: 낮은 π_θ 토큰을 증폭 (소멸 아님)")
gamma = 0.1
# gold 토큰들의 π_θ: 매우 낮음(0.001)부터 보통(0.5)까지
logp = torch.log(torch.tensor([0.001, 0.01, 0.1, 0.5]))
w = luffy_offpolicy_weight(logp, gamma)
# f(x)=x/(x+γ): x=0.001→0.0099, x=0.5→0.833. 낮은 x 도 0 아님(소멸 안 함)
check("아주 낮은 π_θ(0.001) 도 weight>0 (소멸 안 함)", w[0] > 0.005, f"w={w[0]:.4f}")
check("weight 가 π_θ 증가에 단조증가", (w[1:] > w[:-1]).all())
check("weight 유한(폭발 안 함)", w.max() < 1.0 and torch.isfinite(w).all())
# 표준 clip 과 대조: clip(ratio,0.8,1.2)*A, ratio=π_θ/π_old. gold 는 π_old 개념 없음
print(f"     π_θ=[0.001,0.01,0.1,0.5] → weight=[{w[0]:.4f},{w[1]:.3f},{w[2]:.3f},{w[3]:.3f}]")
print(f"     ※ x→0 에서 기울기 1/γ={1/gamma:.0f} → 낮은확률 gold 토큰 증폭")

print("\n4) ★ 함정 #3 — token mask: state 토큰 제외, tactic 토큰만")
# 프롬프트(state) 5토큰 + tactic 3토큰
logp8 = torch.log(torch.tensor([0.5]*5 + [0.01, 0.1, 0.3]))
mask_tactic = torch.tensor([0,0,0,0,0, 1,1,1])   # tactic 만
mask_all = torch.ones(8)                          # 잘못: 전부
loss_tactic = luffy_token_loss(logp8, advantage=1.0, mask=mask_tactic, gamma=gamma)
loss_all = luffy_token_loss(logp8, advantage=1.0, mask=mask_all, gamma=gamma)
check("tactic-only 와 all 이 다름 (state 토큰이 영향 줌)", abs(float(loss_tactic-loss_all))>1e-4)
# tactic-only 는 state 토큰 gradient 없어야
logp8.requires_grad_(True)
l = luffy_token_loss(logp8, 1.0, mask_tactic, gamma)
l.backward()
g = logp8.grad
check("state 토큰(0~4) gradient = 0", torch.allclose(g[:5], torch.zeros(5)),
      f"state grad={g[:5]}")
check("tactic 토큰(5~7) gradient != 0", (g[5:].abs() > 0).all())
print(f"     state grad={g[:5].tolist()} | tactic grad={[round(x,4) for x in g[5:].tolist()]}")

print("\n5) 손실 방향 — gold logp 를 올리는가 (imitation)")
# advantage>0 이면 gold 토큰 logp 를 높이는 방향(loss 감소)이어야
lp = torch.log(torch.tensor([0.1, 0.2])).requires_grad_(True)
m = torch.ones(2)
loss = luffy_token_loss(lp, advantage=2.0, mask=m, gamma=gamma)
loss.backward()
# loss = -Σ w·A·logp. d(loss)/d(logp) = -w·A < 0 → GD 가 logp 를 올림
check("gradient 가 logp 를 올리는 방향 (d loss/d logp < 0)", (lp.grad < 0).all(),
      f"grad={lp.grad}")

print("\n6) ★ flatten_group 통합 — dead group 에 gold 주입 시 데이터 경로")
from tactic_gen.grpo_train import flatten_group  # noqa: E402
# dead group: on-policy 시도 3개 전부 실패(reward 0) + gold 1개(off_policy, reward 1)
dead_group = {
    "attempts": [
        {"steps": [{"prompt": "s0", "tactic": "wrong1.", "result": "INVALID"}], "reward": 0.0},
        {"steps": [{"prompt": "s0", "tactic": "wrong2.", "result": "INVALID"}], "reward": 0.0},
        {"steps": [{"prompt": "s0", "tactic": "wrong3.", "result": "INVALID"}], "reward": 0.0},
        {"steps": [{"prompt": "s0", "tactic": "gold_t.", "result": "VALID"},
                   {"prompt": "s1", "tactic": "Qed.", "result": "COMPLETE"}],
         "reward": 1.0, "off_policy": True},
    ]
}
# golds 는 off_policy 데이터 속성이라 luffy 플래그와 무관하게 표시된다(학습루프가 luffy 일 때만 소비).
# luffy=False 면 advantage 는 std-floor 없이 group_advantages(gold=성공으로 섞임) — with_gold 아님.
_, _, adv_no, _, golds_no = flatten_group(dead_group, process=False, luffy=False)
check("golds 는 luffy 무관하게 off_policy 표시", golds_no == [False, False, False, True, True],
      f"golds_no={golds_no}")
# luffy=True: gold 인식 → std-floor advantage, gold row 양수 / 실패 row 음수
pr, cp, adv_l, _, golds_l = flatten_group(dead_group, process=False, luffy=True)
check("luffy=True: gold step 만 golds=True", golds_l == [False, False, False, True, True],
      f"golds={golds_l}")
gold_adv = [a for a, g in zip(adv_l, golds_l) if g]
fail_adv = [a for a, g in zip(adv_l, golds_l) if not g]
check("gold row advantage > 0", all(a > 0 for a in gold_adv), f"gold_adv={gold_adv}")
check("실패 row advantage < 0", all(a < 0 for a in fail_adv), f"fail_adv={fail_adv}")
check("gold 2 step 모두 같은 advantage(시도 단위 broadcast)",
      abs(gold_adv[0] - gold_adv[1]) < 1e-6)
print(f"     실패 adv={round(fail_adv[0],3)}×3, gold adv={round(gold_adv[0],3)}×2  (row {len(pr)}개)")

print(f"\n{'='*50}\n통과 {ok} / 실패 {fail}")
sys.exit(1 if fail else 0)
