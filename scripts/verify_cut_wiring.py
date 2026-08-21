#!/usr/bin/env python3
"""학습 시점 cut 치환(①-b)이 **프롬프트를 보고** 결정하는지 확인한다.

세 갈래가 다 도는지 못박는다.

    (1) gold 가 전부 보인다   → gold tactic 그대로     (cut 없음)
    (2) 일부가 안 보인다      → 그것들만 assert         (없는 것만! 보이는 것은 그대로)
    (3) 계획이 없다           → gold 그대로            (resolved_example 이 이미 거름)

★ 왜 따로 검사하나: 이 결정이 틀리면 조용히 망가진다. gold 가 보이는데 assert 하면
  증명이 쓸데없이 길어지고, gold 가 안 보이는데 assert 안 하면 **환각을 가르친다.**
  둘 다 오류 메시지가 안 난다.

사용: PYTHONPATH=src python3 scripts/verify_cut_wiring.py
"""
import logging
import os
import re
import sys

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from tactic_gen.assert_split import transform  # noqa: E402

fails = []


def ok(c, name, detail=""):
    print(f"   {'✓' if c else '✗'} {name}" + (f"   {detail}" if detail else ""))
    if not c:
        fails.append(name)


PLAN = {"tac": "rewrite add_comm, mul_comm.",
        "lem": [["add_comm", "forall x y : nat, x + y = y + x"],
                ["mul_comm", "forall x y : nat, x * y = y * x"]]}
SCRIPT = "Lemma foo : P.\nProof.\n  intros."
STATE = "n : nat\n\nP"


def decide(prompt):
    """`tactic_data.collate` ①-b 와 **같은 규칙**."""
    miss = [(nm, ty) for nm, ty in PLAN["lem"]
            if not re.search(r"(?<![\w'])" + re.escape(nm) + r"(?![\w'])", prompt)]
    if not miss:
        return PLAN["tac"]
    return transform(PLAN["tac"],
                     [(nm, f"Lemma {nm} : {ty}.") for nm, ty in miss],
                     proof_script=SCRIPT, state=STATE) or PLAN["tac"]


print("■ cut 치환 배선 검사\n")

# (1) 둘 다 보인다 → 그대로
p1 = "[PREMISES]\nLemma add_comm : forall x y, x+y=y+x.\nLemma mul_comm : forall x y, x*y=y*x."
r1 = decide(p1)
ok(r1 == PLAN["tac"] and "assert" not in r1,
   "(1) gold 가 전부 보이면 **cut 하지 않는다**", r1)

# (2) 하나만 안 보인다 → 그것만 assert, 보이는 것은 이름 그대로
p2 = "[PREMISES]\nLemma add_comm : forall x y, x+y=y+x."
r2 = decide(p2)
ok(r2.count("assert") == 1 and "exact mul_comm" in r2
   and re.search(r"(?<![\w'])add_comm(?![\w'])", r2),
   "(2) 안 보이는 것**만** assert · 보이는 것은 그대로", r2.replace("\n", " ⏎ "))

# (2') 둘 다 안 보인다 → 둘 다 assert
r3 = decide("[PREMISES]\n(비어 있음)")
ok(r3.count("assert") == 2, "(2') 둘 다 안 보이면 둘 다 assert",
   r3.replace("\n", " ⏎ ")[:96])

# (3) 부분집합이 전체보다 쉬운가 — 생성 시점 검증의 전제
full = transform(PLAN["tac"],
                 [(nm, f"Lemma {nm} : {ty}.") for nm, ty in PLAN["lem"]],
                 proof_script=SCRIPT, state=STATE)
subs = [transform(PLAN["tac"], [(nm, f"Lemma {nm} : {ty}.")],
                  proof_script=SCRIPT, state=STATE) for nm, ty in PLAN["lem"]]
ok(bool(full) and all(subs),
   "(3) 전체 조립이 되면 **모든 부분집합도** 된다 (생성 시점 검증의 전제)")

# (4) 이름 경계 — `add_comm` 이 `add_comm'` 이나 `Nat.add_comm` 에 오탐하지 않는가
p4 = "[PREMISES]\nLemma add_comm' : X.\nLemma mul_comm : Y."
r4 = decide(p4)
ok("exact add_comm" in r4, "(4) `add_comm'` 을 `add_comm` 으로 오인하지 않는다",
   r4.split("\n")[0])

print()
print("=" * 62)
if fails:
    print("✗ 실패:", fails)
    sys.exit(1)
print("✓ 배선 정상")
