"""Progress critic 단위 테스트 — GPU 불필요.

가장 중요한 검증: **학습 시 goal 문자열 == 탐색 시 goal 문자열**.
어긋나면 critic 은 에러 없이 조용히 무의미해진다(가장 잡기 어려운 종류의 버그).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from coqpyt.coq.lsp.structs import Goal as CoqGoal  # noqa: E402
from coqpyt.coq.lsp.structs import Hyp  # noqa: E402

from data_management.dataset_file import Goal as DsGoal  # noqa: E402
from tactic_gen.progress_critic import (  # noqa: E402
    N_MAX,
    format_goal,
    format_goals,
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


print("1) ★ 학습(dataset_file.Goal) 과 탐색(coqpyt.Goal) 의 문자열이 동일한가")
# 같은 증명 상태를 두 표현으로 만든다.
ds = DsGoal(hyps=["n, n0: nat", "H: forall m0 : nat, n0 <= m0"], goal="S n0 <= S n1")
cq = CoqGoal(
    hyps=[Hyp(names=["n", "n0"], ty="nat"),
          Hyp(names=["H"], ty="forall m0 : nat, n0 <= m0")],
    ty="S n0 <= S n1",
)
s_train, s_search = format_goal(ds), format_goal(cq)
check("두 표현이 같은 문자열로 정규화됨", s_train == s_search,
      f"\n     train : {s_train!r}\n     search: {s_search!r}")
check("결론이 실제로 들어있음(repr 폴백이 아님)", "S n0 <= S n1" in s_search)
check("가설 형식 'n, n0: nat'", s_search.startswith("n, n0: nat"))
check("가설과 결론 사이 빈 줄", "\n\n" in s_search)
print(f"     → {s_search!r}")

print("\n2) 다중 goal (AND 상태)")
multi = format_goals([cq, cq])
check("'\\n===\\n' 로 결합", multi == s_search + "\n===\n" + s_search)
check("goal 없음 → 빈 문자열", format_goals([]) == "" and format_goals(None) == "")

print("\n3) 실제 학습 데이터와 대조 (data/progress/train.jsonl)")
p = Path("data/progress/train.jsonl")
if not p.exists():
    print("  ⏭  학습 데이터 없음 — 건너뜀")
else:
    with p.open() as f:
        rows = [json.loads(next(f)) for _ in range(300)]
    # 학습 state 는 "hyps\n\ngoal" 형식이어야 한다(다중 goal 은 \n===\n 로 결합)
    bad = [r for r in rows if "\n\n" not in r["state"]]
    check("학습 state 가 전부 '가설\\n\\n결론' 형식", not bad,
          f"어긋난 샘플 {len(bad)}개")
    # 가설이 있는 샘플을 골라 우리 파서가 같은 모양을 만드는지 육안 대조
    withhyp = next((r for r in rows if r["state"].split("\n\n")[0].strip()), None)
    if withhyp:
        head = withhyp["state"].split("\n\n")[0].splitlines()[0]
        check("학습 가설 줄이 'names: ty' 형식", ":" in head, f"실제: {head!r}")
        print(f"     실제 학습 샘플 첫 가설: {head!r}")
    rem = [r["remaining"] for r in rows]
    check("remaining 이 음수 없음", min(rem) >= 0)
    check("N_MAX clip 대상이 존재(꼬리가 길다)", max(rem) > N_MAX,
          f"max={max(rem)}")

print("\n4) 결론 필드가 없는 이상한 객체 → 조용히 넘어가지 않고 에러")


class Bogus:
    hyps = []


try:
    format_goal(Bogus())
    check("결론 없는 Goal 은 예외를 던진다", False, "예외가 안 났다")
except ValueError:
    check("결론 없는 Goal 은 예외를 던진다", True)

print(f"\n{'='*50}\n통과 {ok} / 실패 {fail}")
sys.exit(1 if fail else 0)
