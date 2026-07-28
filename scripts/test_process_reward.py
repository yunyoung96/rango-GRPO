#!/usr/bin/env python3
"""process_reward (Math-Shepherd PRM) 코어 단위테스트 (CPU)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from tactic_gen.process_reward import state_success_values, process_rewards, has_signal

def approx(a, b, e=1e-6): return abs(a - b) < e

def test_shared_state_graded():
    # state A를 두 궤적이 지남: 하나 성공, 하나 실패 → A 값 = 0.5
    trs = [
        {"steps": [{"state_key": "A"}, {"state_key": "B"}], "success": True},
        {"steps": [{"state_key": "A"}, {"state_key": "C"}], "success": False},
    ]
    v = state_success_values(trs)
    assert approx(v["A"], 0.5), v
    assert approx(v["B"], 1.0) and approx(v["C"], 0.0), v
    assert has_signal(v)
    print("✓ 공유 state가 graded 신호(0.5) 생성")

def test_no_sharing_falls_back():
    # state 공유 없음 → 전부 0/1, graded 신호 없음(outcome broadcast와 동일=무해)
    trs = [
        {"steps": [{"state_key": "X"}], "success": True},
        {"steps": [{"state_key": "Y"}], "success": False},
    ]
    v = state_success_values(trs)
    assert not has_signal(v)
    print("✓ 공유 없으면 graded 신호 0 (무해 폴백)")

def test_process_rewards_shape():
    trs = [
        {"steps": [{"state_key": "A"}, {"state_key": "B"}], "success": True},
        {"steps": [{"state_key": "A"}, {"state_key": "C"}], "success": False},
    ]
    v = state_success_values(trs)
    # 성공 궤적: step0 신호=다음(B)값=1.0, step1=종단앵커=1.0
    pr = process_rewards(trs[0], v)
    assert approx(pr[0], 1.0) and approx(pr[1], 1.0), pr
    # 실패 궤적: step0 신호=다음(C)값=0.0, step1=종단앵커=0.0
    pr2 = process_rewards(trs[1], v)
    assert approx(pr2[0], 0.0) and approx(pr2[1], 0.0), pr2
    print("✓ process reward가 step별로 올바르게 배분")

def test_credit_placement():
    # 핵심: 한 state가 좋은/나쁜 후속으로 갈림 → 중간 credit이 위치대로 배분
    trs = [
        {"steps": [{"state_key": "root"}, {"state_key": "good"}, {"state_key": "qed"}], "success": True},
        {"steps": [{"state_key": "root"}, {"state_key": "bad"}], "success": False},
        {"steps": [{"state_key": "root"}, {"state_key": "good"}, {"state_key": "dead"}], "success": False},
    ]
    v = state_success_values(trs)
    # good: 2회 경유 중 1성공 = 0.5, bad: 0, root: 3회 중 1 = 0.333
    assert approx(v["good"], 0.5) and approx(v["bad"], 0.0), v
    assert v["good"] > v["bad"], "good state가 bad보다 높은 credit"
    print(f"✓ credit-placement: good={v['good']:.2f} > bad={v['bad']:.2f}")

if __name__ == "__main__":
    test_shared_state_graded()
    test_no_sharing_falls_back()
    test_process_rewards_shape()
    test_credit_placement()
    print("\n전체 통과 ✅")
