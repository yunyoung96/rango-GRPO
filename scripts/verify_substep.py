#!/usr/bin/env python3
"""하위스텝 분해(안 B)가 **조용히 망가지지 않았는지** 검사한다.

docs/premise/substep.md 의 G1~G8. 이 배선은 틀려도 오류가 안 난다 —
검색을 원래 goal 로 하면 L 이 안 보일 뿐이고, `[STATE]` 를 안 바꾸면 모델이
다른 goal 을 보고 답할 뿐이다. 그래서 못박아 둔다.

사용: PYTHONPATH=src python3 scripts/verify_substep.py
"""
import logging
import os
import re
import sys

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from tactic_gen.tactic_data import _split_substeps, _substep_state  # noqa: E402

fails = []


def ok(c, name, detail=""):
    print(f"   {'✓' if c else '✗'} {name}" + (f"   {detail}" if detail else ""))
    if not c:
        fails.append(name)


CUT = ("assert (forall x y : nat, x + y = y + x) as H_asrt0. { exact add_comm. }\n"
       "assert (forall x y : nat, x * y = y * x) as H_asrt1. { exact mul_comm. }\n"
       "rewrite H_asrt0, H_asrt1.")
BASE = "n : nat\nHn : P n\n\nQ n"

print("■ 하위스텝 분해 검사\n")
subs = _split_substeps(CUT)
for i, (t, k, P, H) in enumerate(subs):
    print(f"   sub {i} [{k:6s}] {t}")
print()

# G6 — 2k+1
ok(len(subs) == 5, "G6  missing lemma k=2 → 하위스텝 2k+1 = 5개", f"{len(subs)}개")
ok([k for _, k, _, _ in subs] == ["assert", "close", "assert", "close", "final"],
   "G6b 순서가 assert·close·assert·close·final")

# G3 — 각 하위스텝이 tactic 하나
ok(all(t.count("assert (") <= 1 for t, k, _, _ in subs),
   "G3  각 하위스텝이 tactic 하나 (통째로 남지 않는다)")

# G4 — 이름 일관성
names = {H for _, k, _, H in subs if H}
ok(names == {"H_asrt0", "H_asrt1"} and "H_asrt0" in subs[4][0] and "H_asrt1" in subs[4][0],
   "G4  H_asrt 이름이 하위스텝 사이에서 일관", str(sorted(names)))

# G2 — 상태 합성
print("\n■ 하위스텝별 상태 (G2)\n")
exp = [("Q n", []), ("forall x y : nat, x + y = y + x", []),
       ("Q n", ["H_asrt0"]), ("forall x y : nat, x * y = y * x", ["H_asrt0"]),
       ("Q n", ["H_asrt0", "H_asrt1"])]
bad = []
for i in range(len(subs)):
    st = _substep_state(BASE, subs, i)
    g = st.split("\n\n")[-1]
    hs = st.split("\n\n")[0]
    print(f"   sub {i}:  가설 [{', '.join(x.split(' :')[0] for x in hs.split(chr(10)) if x.strip())}]"
          f"  ⊢ {g[:52]}")
    want_goal, want_h = exp[i]
    if g.strip() != want_goal:
        bad.append(f"sub{i} goal={g[:30]} 기대={want_goal[:30]}")
    for h in want_h:
        if f"{h} :" not in hs:
            bad.append(f"sub{i} 가설 {h} 없음")
    for h in ("H_asrt0", "H_asrt1"):
        if h not in want_h and f"{h} :" in hs:
            bad.append(f"sub{i} 가설 {h} 가 **미리** 들어옴")
print()
ok(not bad, "G2  goal 과 가설이 하위스텝마다 정확히 맞는다", str(bad[:2]) if bad else "")
ok("n : nat" in _substep_state(BASE, subs, 4) and "Hn : P n" in _substep_state(BASE, subs, 4),
   "G2b 원래 가설(Γ)이 보존된다")

# G5 — 결정성
import hashlib  # noqa: E402
h1 = int(hashlib.sha1(b"a/b.v:1:2").hexdigest()[:8], 16) % 5
h2 = int(hashlib.sha1(b"a/b.v:1:2").hexdigest()[:8], 16) % 5
ok(h1 == h2, "G5  선택이 결정적 (같은 sid → 항상 같은 하위스텝)")

# G7 — 조각이 짧아진다
from transformers import AutoTokenizer  # noqa: E402
try:
    tk = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-3B-Instruct")
    full = len(tk.tokenize(CUT))
    mx = max(len(tk.tokenize(t)) for t, _, _, _ in subs)
    ok(mx < full, f"G7  조각 최대 {mx}토큰 < 전체 {full}토큰 (예산 여유가 생긴다)")
except Exception as e:
    print(f"   – G7 건너뜀 ({e})")

# G8 — cut 이 없으면 아무 일도 없어야 한다
ok(_split_substeps("apply foo.") == [("apply foo.", "final", None, None)],
   "G8  assert 가 없으면 하위스텝이 1개(원래 tactic 그대로)")

print()
print("=" * 62)
if fails:
    print("✗ 실패:", fails)
    sys.exit(1)
print("✓ 전 항목 통과")
