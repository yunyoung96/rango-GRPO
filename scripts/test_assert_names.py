#!/usr/bin/env python3
"""assert 가 만드는 이름이 **기존 이름을 절대 침범하지 않는지** 실제 Coq 으로 확인한다.

정적 대조만으로는 부족하다 — Coq 은 `intros` 때 이름이 이미 쓰이면 **숫자를 붙여 자동
개명**하고(전역 `H_asrt0` 이 있으면 `forall H_asrt0` 은 `H_asrt1` 로 들어온다), 그 이름은
프롬프트 어디에도 안 나온다. 실제로 `H_asrt1 is already used` 로 깨졌다.

심는 함정
  ① 가설블록에 이미 `H_asrt0`      ② `H_asrt0`·`H_asrt1` 둘 다
  ③ 앞 증명의 `intros` 가 생성       ④ 뒤 증명이 `H_asrt0` 을 쓴다
  ⑤ goal **본문** 바인더가 `H_asrt0` (전역에도 있어 Coq 이 개명한다)
  ⑥ 가설 **타입 안**에 등장          ⑦ premise(전역 lemma) 이름이 `H_asrt0`
  ⑧ 한 tactic 에 assert 2개
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, "src")
from coqpyt.coq.base_file import CoqFile  # noqa: E402
from tactic_gen import assert_split as A  # noqa: E402

S = Path("/tmp/claude-0/-app-coq-modeling/e02d0688-7cb1-43a8-aa0e-ee8afd60ce19/"
         "scratchpad/nm")
S.mkdir(parents=True, exist_ok=True)

BASE = """Require Import Arith List.
Lemma my_le_refl : forall n : nat, n <= n.
Proof. intros; apply Nat.le_refl. Qed.
Lemma my_add_0 : forall n : nat, n + 0 = n.
Proof. intros; apply Nat.add_0_r. Qed.
"""
GLOBAL_CLASH = "Lemma H_asrt0 : 1 = 1.\nProof. reflexivity. Qed.\n"
L1 = ("my_le_refl", "forall n : nat, n <= n")
L2 = ("my_add_0", "forall n : nat, n + 0 = n")

# (이름, 정리, state, 앞증명, gold tactic, 항들, 뒤증명, premise들, 전역충돌)
CASES = [
    ("① 가설블록에 H_asrt0", "Goal forall n : nat, True -> n <= n.",
     "H_asrt0 : True\nn : nat\n[GOAL]\nn <= n", "intros n H_asrt0.",
     "apply my_le_refl.", [L1], "", [], False),
    ("② H_asrt0·H_asrt1 둘 다", "Goal forall n : nat, True -> True -> n <= n.",
     "H_asrt0 : True\nH_asrt1 : True\n[GOAL]\nn <= n",
     "intros n H_asrt0 H_asrt1.", "apply my_le_refl.", [L1], "", [], False),
    ("③ 앞 증명 intros 가 생성", "Goal forall n : nat, True -> n <= n.",
     "", "intros n H_asrt0.", "apply my_le_refl.", [L1], "", [], False),
    ("④ 뒤 증명이 H_asrt0 사용", "Goal forall n : nat, n <= n /\\ n + 0 = n.",
     "", "intros n. split.", "- apply my_le_refl.",
     [L1], "\n- assert (n + 0 = n) as H_asrt0.\n  { apply my_add_0. }\n  exact H_asrt0.",
     [], False),
    # ★ Coq 자동 개명 함정: 전역에 H_asrt0 이 있어 intro 된 바인더가 H_asrt1 이 된다
    ("⑤ goal 바인더+전역충돌", "Goal forall H_asrt0 : nat, H_asrt0 <= H_asrt0.",
     "[GOAL]\nforall H_asrt0 : nat, H_asrt0 <= H_asrt0", "intros.",
     "apply my_le_refl.", [L1], "", [], True),
    ("⑥ 가설 타입 안에 등장", "Goal forall n : nat, n = n -> n <= n.",
     "n : nat\nH : n = n\n[GOAL]\nn <= n", "intros n H.",
     "apply my_le_refl.", [L1], "", [], False),
    ("⑦ premise 이름이 H_asrt0", "Goal forall n : nat, n <= n.",
     "", "intros n.", "apply my_le_refl.", [L1], "",
     ["Lemma H_asrt0 : 1 = 1."], True),
    ("⑧ 한 tactic 에 assert 2개", "Goal forall n : nat, n <= n /\\ n + 0 = n.",
     "", "intros n.", "split; [apply my_le_refl | apply my_add_0].",
     [L1, L2], "", [], False),
]


def run(body, tag, clash):
    f = S / f"{tag}.v"
    f.write_text(BASE + (GLOBAL_CLASH if clash else "") + body + "\nQed.\n")
    try:
        cf = CoqFile(str(f), timeout=120)
        cf.run()
        e = [getattr(d, "message", "")[:120] for d in cf.errors]
        cf.close()
        return e
    except Exception as ex:
        return [f"예외: {str(ex)[:100]}"]
    finally:
        f.unlink(missing_ok=True)


ok = 0
for nm, thm, st, pre, tac, lems, suf, prems, clash in CASES:
    A.WHY.clear()
    # 전역 충돌은 premise 목록으로 들어온다(실제 파이프라인과 동일)
    pr = list(prems) + ([GLOBAL_CLASH] if clash and not prems else [])
    tr = A.transform_with_types(tac, lems, state=st, proof_script=pre,
                                suffix=suf, premises=pr)
    if tr is None:
        print(f"{nm:24s} ✗ 변환 포기 — {A.WHY}")
        continue
    used = set(re.findall(r"as\s+(H_asrt\w*\d+)", tr))
    bad = [u for u in used if not A.name_is_free(u, st, pre, suf, pr)]
    body = f"{thm}\nProof.\n{pre}\n{tr}{suf}"
    # 원본도 되는지 먼저(비교 기준)
    e0 = run(f"{thm}\nProof.\n{pre}\n{tac}{suf}", "o" + nm[0], clash)
    e1 = run(body, "n" + nm[0], clash)
    good = (not bad) and (not e1) and (not e0)
    ok += good
    tail = ""
    if bad:
        tail += f"  ★침범 {bad}"
    if e0:
        tail += f"  [원본도 오류] {e0[0][:50]}"
    elif e1:
        tail += f"  Coq오류: {e1[0][:70]}"
    print(f"{nm:24s} {'✓' if good else '✗'}  이름 {sorted(used)}{tail}")
print(f"\n{ok}/{len(CASES)} 통과")
