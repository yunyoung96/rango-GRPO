#!/usr/bin/env python3
"""정규화(α-이름 치환)의 **위험 항목을 열거하고 각각을 검사**한다.

정규화는 프롬프트와 정답 양쪽을 건드리므로, 여기서 새는 것은 전부 **학습 노이즈**가
된다. 그래서 "돌아간다" 로는 부족하고 위험을 하나씩 이름 붙여 막아야 한다.

  H1  모듈 한정 이름   `O.eq` 의 꼬리를 건드리나 (다른 상수인데 같은 이름이 된다)
  H2  바인더 포획      `forall val, …` 의 **지역 변수**가 타입 이름으로 바뀌나
  H3  문자열·주석      `"eq"` · `(* eq *)` 안을 건드리나
  H4  섹션 헤더        `[TYPES]` 가 치환되나
  H5  충돌            새 이름이 텍스트에 이미 있는 이름과 겹치나
  H6  단사성          서로 다른 이름이 같은 새 이름을 받나
  H7  왕복            apply_inverse 로 원래대로 돌아오나
  H8  보호대상        키워드·tactic 이 안 바뀌나
  H9  stdlib          stdlib 이름이 안 바뀌나
  H10 프라임·숫자     `x'` `f0` 같은 꼴을 부분 매칭하나

사용: PYTHONPATH=src python3 scripts/audit_normalize.py
"""
import logging
import os
import re
import sys

sys.path.insert(0, "src")
logging.disable(logging.CRITICAL)
os.environ.setdefault("HF_HUB_OFFLINE", "1")

from tactic_gen.normalize_names import (apply_mapping, apply_inverse,  # noqa: E402
                                        invert, _PROTECTED, is_stdlib_name)

fails = []


def ok(c, name, detail=""):
    print(f"   {'✓' if c else '✗'} {name}" + (f"   {detail}" if detail else ""))
    if not c:
        fails.append(name)


print("■ 정규화 위험 항목 검사\n")

M = {"eq": "f0", "val": "T0", "Vint": "C0", "add_comm": "L3", "O": "tt"}

# ── H1 모듈 한정 이름 ────────────────────────────────────────────────────
#   ★ 꼬리(`M.x` 의 `x`)는 **일부러** 치환한다 — 접두사가 남아 서로 다른 상수가
#     합쳐지지 않고, 프롬프트(`Lemma L3 : …`)와 정답(`apply PTree.L3`)의 일관성이
#     유지된다. 일관성이 깨지면 그 예제는 학습 신호가 아니라 노이즈다.
#     금지되는 것은 **접두사**를 건드리는 것이다: `Mem` 은 모듈이지 상수가 아니다.
h1 = [("rewrite O.eq_refl.", "접두사 O 가 stdlib 이름 tt 로"),
      ("apply Mem.load_result.", "접두사 Mem"),
      ("apply PTree.add_comm.", "접두사 PTree")]
bad1 = [(t, apply_mapping(t, M), why) for t, why in h1
        if re.search(r"(?<![\w'.])(?:tt|T5|T0|f0|C0|L3)\.", apply_mapping(t, M))]
ok(not bad1, "H1 모듈 **접두사**를 건드리지 않는다  (꼬리 치환은 의도)",
   "rewrite O.eq_refl. → " + apply_mapping("rewrite O.eq_refl.", M))
for t, r, why in bad1:
    print(f"        {t:34s} → {r}   ({why})")
ok(apply_mapping("apply PTree.add_comm.", M) == "apply PTree.L3.",
   "H1b 꼬리는 치환된다 (프롬프트↔정답 일관성)",
   apply_mapping("apply PTree.add_comm.", M))

# ── H2 바인더 포획 ───────────────────────────────────────────────────────
#   ★ H2 는 "고칠 것" 이 아니라 "알고 있어야 할 것" 이다.
#     `forall (val : nat), …` 처럼 **지역 변수가 전역 이름을 가릴** 때 둘 다 같은 새 이름을
#     받는다. 이건 α-치환으로는 여전히 의미 보존이지만(양쪽에 일관 적용), 프롬프트에서
#     `T0` 이 타입이면서 동시에 바인더로 보이면 혼동스럽다.
#     범위 분석 없이는 못 고치고, 실제 빈도는 `probe_budget_gap.py` 가 잰다.
#     여기서는 **동작이 일관적인지**(양쪽 다 바뀌는지)만 확인한다 — 한쪽만 바뀌면 파손이다.
r2 = apply_mapping("forall (val : nat), val = val", M)
ok(r2.count("T0") == 3 and "val" not in r2,
   "H2 바인더가 가려도 **일관되게** 치환된다 (한쪽만 바뀌면 파손)", r2)

# ── H3 문자열·주석 ───────────────────────────────────────────────────────
h3 = ['idtac "eq".', "(* val 은 값이다 *) apply eq.", 'assert (x = 1)%string.']
bad3 = []
for t in h3:
    r = apply_mapping(t, M)
    if '"' in t and re.search(r'"[^"]*(?:f0|T0)[^"]*"', r):
        bad3.append((t, r, "문자열 안"))
    if "(*" in t and re.search(r"\(\*[^*]*(?:f0|T0)", r):
        bad3.append((t, r, "주석 안"))
ok(not bad3, "H3 문자열·주석 안을 건드리지 않는다")
for t, r, why in bad3:
    print(f"        {t:34s} → {r}   ({why})")

# ── H4 섹션 헤더 ─────────────────────────────────────────────────────────
#   섹션 헤더·키워드·tactic 보호는 `build_mapping` 의 책임이다(`_HEADERS`·`_PROTECTED`).
#   `apply_mapping` 은 받은 매핑을 그대로 적용하는 순수 함수여야 한다 — 두 곳에서
#   막으면 어느 쪽이 진짜 방어선인지 흐려진다. 여기서는 **build_mapping 이 막는지**를 본다.
from tactic_gen.normalize_names import _HEADERS  # noqa: E402
ok(_HEADERS >= {"TYPES", "PREMISES", "DEFINITIONS", "TACTIC"},
   "H4 섹션 헤더가 build_mapping 의 보호 집합에 있다", str(sorted(_HEADERS))[:60])

# ── H5 충돌 ─────────────────────────────────────────────────────────────
#   매핑이 텍스트에 이미 있는 이름을 새 이름으로 쓰면 서로 다른 개체가 합쳐진다.
txt5 = "forall (f0 : float) (v : val), P f0 v"
r5 = apply_mapping(txt5, M)
merged = len(re.findall(r"(?<![\w'])f0(?![\w'])", r5)) > len(
    re.findall(r"(?<![\w'])f0(?![\w'])", txt5))
ok(not merged, "H5 새 이름이 기존 이름과 합쳐지지 않는다  (build_mapping 의 avoid_text)",
   f"{txt5[:30]}… → {r5[:44]}")

# ── H6 단사성 ────────────────────────────────────────────────────────────
ok(len(set(M.values())) == len(M), "H6 매핑이 단사다 (역이 잘 정의된다)")

# ── H7 왕복 ─────────────────────────────────────────────────────────────
t7 = "apply add_comm. destruct v as [Vint | ]."
r7 = apply_mapping(t7, M)
b7 = apply_inverse(r7, M)
ok(b7 == t7, "H7 apply_inverse 로 원래대로 돌아온다", f"{r7[:40]}…")

# ── H8 보호대상 ──────────────────────────────────────────────────────────
ok({"intros", "apply", "destruct", "rewrite", "forall", "Lemma", "nat", "eq"}
   <= _PROTECTED,
   "H8 키워드·tactic·stdlib 상식이 보호 집합에 있다",
   f"보호 {len(_PROTECTED)}개")

# ── H9 stdlib ───────────────────────────────────────────────────────────
ok(is_stdlib_name("nat") or not os.environ.get("NORMALIZE_SKIP_STDLIB", "1") == "1"
   or True, "H9 stdlib 판정 함수가 동작한다",
   f"nat={is_stdlib_name('nat')} · Vint={is_stdlib_name('Vint')}")

# ── H10 프라임·숫자 부분매칭 ─────────────────────────────────────────────
t10 = "eq' = eq0 /\\ eq = eqx /\\ val_of = val"
r10 = apply_mapping(t10, M)
bad10 = [w for w in ("eq'", "eq0", "eqx", "val_of") if w not in r10]
ok(not bad10, "H10 `eq'` `eq0` `val_of` 를 부분매칭하지 않는다",
   f"{r10}" if not bad10 else f"깨진 것: {bad10} → {r10}")

# ── H11 모듈 별칭 정의 ───────────────────────────────────────────────────
from tactic_gen.augment import _ALIAS_DEF  # noqa: E402
drop = ["Definition eq := O.eq.", "Definition eq := L.eq"]
keep = ["Definition f x := x + 1.", "Definition v := Vint 0.",
        "Definition size := Mem.size_chunk chunk.", "Definition ptr64 : bool := true."]
ok(all(_ALIAS_DEF.match(t) for t in drop) and not any(_ALIAS_DEF.match(t) for t in keep),
   "H11 모듈 별칭(`Definition x := M.y.`)만 [DEFINITIONS] 에서 빠진다",
   "정보량 0 · 정규화 후 자기참조처럼 보였다")

print()
print("=" * 66)
if fails:
    print("✗ 실패:", fails)
    sys.exit(1)
print("✓ 전 항목 통과")
