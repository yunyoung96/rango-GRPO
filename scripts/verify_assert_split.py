#!/usr/bin/env python3
"""assert 변환이 **실제 Coq 에서 통과하는지** 동적으로 검증한다.

문법만 그럴듯해 보이는 변환은 쓸모가 없다. 원래 증명과 변환된 증명을 각각 Coq 에 넣어
**둘 다 Qed 까지 가는지** 확인한다.

검증 항목
  ① 단일 lemma · bullet 방식
  ② 단일 lemma · 중괄호 방식
  ③ **여러 lemma** (t1; apply L1; apply L2 형태)
  ④ 복합 tactic 중간에 lemma 가 낀 경우 (`;` 구조 보존)
  ⑤ 이미 bullet 을 쓰고 있는 증명 안에서 (bullet 충돌)
  ⑥ 암묵인자 `{A}` 가 있는 lemma
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, "src")
from coqpyt.coq.base_file import CoqFile  # noqa: E402
from tactic_gen.assert_split import transform  # noqa: E402

S = Path("/tmp/claude-0/-app-coq-modeling/e02d0688-7cb1-43a8-aa0e-ee8afd60ce19/scratchpad/as")
S.mkdir(parents=True, exist_ok=True)

PRE = """Require Import Arith List.
Import ListNotations.

Lemma my_le_refl : forall n : nat, n <= n.
Proof. intros; apply Nat.le_refl. Qed.

Lemma my_add_0 : forall n : nat, n + 0 = n.
Proof. intros; apply Nat.add_0_r. Qed.

Lemma my_len_app {A} (l1 l2 : list A) :
  length (l1 ++ l2) = length l1 + length l2.
Proof. apply app_length. Qed.

"""

CASES = [
    # (이름, 정리, 원래 증명, [(lemma 이름, premise 텍스트)], 옵션)
    ("① 단일·bullet",
     "Goal forall n : nat, n <= n.",
     "intros n. apply my_le_refl.",
     [("my_le_refl", "Lemma my_le_refl : forall n : nat, n <= n.")],
     dict(use_bullet=True)),
    ("② 단일·중괄호",
     "Goal forall n : nat, n <= n.",
     "intros n. apply my_le_refl.",
     [("my_le_refl", "Lemma my_le_refl : forall n : nat, n <= n.")],
     dict()),
    ("③ 여러 lemma",
     "Goal forall n : nat, n + 0 = n /\\ n <= n.",
     "intros n. split; [apply my_add_0 | apply my_le_refl].",
     [("my_add_0", "Lemma my_add_0 : forall n : nat, n + 0 = n."),
      ("my_le_refl", "Lemma my_le_refl : forall n : nat, n <= n.")],
     dict()),
    ("④ ; 중간에 lemma",
     "Goal forall n : nat, n + 0 = n.",
     "intros n; rewrite my_add_0; reflexivity.",
     [("my_add_0", "Lemma my_add_0 : forall n : nat, n + 0 = n.")],
     dict()),
    ("⑤ bullet 이미 사용중",
     "Goal forall n : nat, n <= n /\\ n + 0 = n.",
     "intros n. split.\n- apply my_le_refl.\n- apply my_add_0.",
     [("my_le_refl", "Lemma my_le_refl : forall n : nat, n <= n.")],
     dict(use_bullet=True)),
    ("⑦ - bullet 안에서 변환",
     "Goal forall n : nat, n <= n /\\ n + 0 = n.",
     "split.\n- apply my_le_refl.\n- apply my_add_0.",
     [("my_le_refl", "Lemma my_le_refl : forall n : nat, n <= n.")],
     dict()),
    ("⑧ - bullet 안 · bullet 강제",
     "Goal forall n : nat, n <= n /\\ n + 0 = n.",
     "split.\n- apply my_le_refl.\n- apply my_add_0.",
     [("my_le_refl", "Lemma my_le_refl : forall n : nat, n <= n.")],
     dict(use_bullet=True)),
    # ★ 진짜 위험 상황: 모델이 **이미 - bullet 안에 있는 상태**에서 다음 tactic 을 생성한다.
    #   ⑦⑧ 은 assert 가 증명 맨 앞에 와서 bullet 밖이라 위험이 재현되지 않았다.
    ("⑨ [prefix] - 안에서 생성·중괄호",
     "Goal forall n : nat, n <= n /\\ n + 0 = n.",
     "split.\n-",
     "apply my_le_refl.",
     [("my_le_refl", "Lemma my_le_refl : forall n : nat, n <= n.")],
     dict(), "\n- apply my_add_0."),
    ("⑩ [prefix] - 안에서 생성·bullet강제",
     "Goal forall n : nat, n <= n /\\ n + 0 = n.",
     "split.\n-",
     "apply my_le_refl.",
     [("my_le_refl", "Lemma my_le_refl : forall n : nat, n <= n.")],
     dict(use_bullet=True), "\n- apply my_add_0."),
    ("⑥ 암묵인자 {A}",
     "Goal forall (l : list nat), length (l ++ l) = length l + length l.",
     "intros l. apply my_len_app.",
     [("my_len_app", "Lemma my_len_app {A} (l1 l2 : list A) : "
                     "length (l1 ++ l2) = length l1 + length l2.")],
     dict()),
]


def run(body: str, tag: str):
    f = S / f"{tag}.v"
    f.write_text(PRE + body + "\nQed.\n")
    try:
        cf = CoqFile(str(f), timeout=120)
        cf.run()
        errs = [getattr(d, "message", "")[:110] for d in cf.errors]
        cf.close()
        return errs
    except Exception as ex:
        return [f"예외: {str(ex)[:100]}"]
    finally:
        f.unlink(missing_ok=True)


# ⑧⑩ 은 bullet 강제 케이스다. ⑩ 은 **깨지는 것이 정상** — bullet 을 쓰면 안 된다는 증거.
EXPECT_FAIL = {"⑩"}
ok = 0
for i, case in enumerate(CASES):
    if len(case) == 5:
        name, thm, proof, lemmas, opt = case
        prefix, suffix = "", ""
        target = proof
    else:
        name, thm, prefix, target, lemmas, opt, suffix = case
        proof = prefix + " " + target + suffix
    orig = f"{thm}\nProof.\n{proof}"
    tr = transform(target, lemmas, proof_script=(prefix or proof), state="", **opt)
    if tr is None:
        print(f"{name:26s} ✗ 변환 불가")
        continue
    body = (prefix + " " + tr + suffix) if prefix else tr
    trans = f"{thm}\nProof.\n{body}"
    e0 = run(orig, f"o{i}")
    e1 = run(trans, f"t{i}")
    good = (not e0) and (not e1)
    if name[0] in EXPECT_FAIL:
        good = bool(e1)          # 깨져야 정상
        print(f"{name:26s} {'✓(예상대로 깨짐)' if good else '✗(안 깨졌다?)'}"
              f"  변환오류 {len(e1)}")
        ok += good
        continue
    ok += good
    print(f"{name:26s} {'✓' if good else '✗'}  원본오류 {len(e0)} · 변환오류 {len(e1)}")
    if not good:
        print("   변환문:")
        for ln in body.split("\n"):
            print("     " + ln)
        for m in (e1 or e0)[:2]:
            print("   오류:", m)
print(f"\n{ok}/{len(CASES)} 통과")
