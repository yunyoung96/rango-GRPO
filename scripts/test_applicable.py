#!/usr/bin/env python3
"""applicable.py 단위 검증 — 정답을 아는 케이스로 파서·매처를 잡는다.

실전(CompCert gold)에서 재현율이 32% 로 나왔을 때 드러난 실패들을 회귀 케이스로 박아둔다.
"""
import sys

sys.path.insert(0, "src")
from tactic_gen.applicable import (applicability, decompose, parse)  # noqa: E402

fail = []


def ck(name, got, want):
    if got != want:
        fail.append(f"  ✗ {name}: got={got} want={want}")
    else:
        print(f"  ✓ {name}")


def concl(p):
    d = decompose(p)
    return " ".join(d[2]) if d else None


print("── 1. 파서: 우선순위 ──")
ck("prec */+", parse("a + b * c"),
   ("op", "+", ("id", "a"), ("op", "*", ("id", "b"), ("id", "c"))))
ck("app 좌결합", parse("f x y"), ("app", ("app", ("id", "f"), ("id", "x")), ("id", "y")))
ck("prec =/+", parse("a + b = c"),
   ("op", "=", ("op", "+", ("id", "a"), ("id", "b")), ("id", "c")))
ck("arrow 우결합", parse("A -> B -> C"),
   ("op", "->", ("id", "A"), ("op", "->", ("id", "B"), ("id", "C"))))
ck("괄호", parse("(a + b) * c"),
   ("op", "*", ("op", "+", ("id", "a"), ("id", "b")), ("id", "c")))
ck("app > op", parse("f x + g y"),
   ("op", "+", ("app", ("id", "f"), ("id", "x")), ("app", ("id", "g"), ("id", "y"))))

print("\n── 2. 회귀: 실전에서 깨졌던 것들 ──")
# (a) <-> 를 -> 로 자르면 안 된다
ck("<-> 안 쪼개짐",
   concl("Lemma s: forall m1 m2, d m1 m2 <-> d m2 m1."), "d m1 m2 <-> d m2 m1")
ck("<-> 가설 0개", len(decompose("Lemma s: forall m1 m2, d m1 m2 <-> d m2 m1.")[1]), 0)
# (b) (s, d) :: m2 를 s 로 뭉개면 안 된다
t = parse("f m1 ((s, d) :: m2)")
ck("pair::cons 보존", t[0] == "app" and t[2][0] in ("op", "opq"), True)
ck("cons 인자 유지", str(t).count("m2") >= 1, True)
# (c) 화살표 중간 forall 의 변수도 메타변수
d = decompose("Lemma t: forall (A: Type) (l1 l2: list A), is_tail l1 l2 -> "
              "forall (l3: list A), is_tail l2 l3 -> is_tail l1 l3.")
ck("중간 forall 변수 수집", {"l1", "l2", "l3", "A"} <= d[0], True)
ck("중간 forall 결론", " ".join(d[2]), "is_tail l1 l3")
# (d) 선언부 바인더도 메타변수
d = decompose("Lemma f {A} (pt : tree A) : size pt = 0.")
ck("선언부 바인더", "pt" in d[0], True)
ck("선언부 결론", " ".join(d[2]), "size pt = 0")
# (e) 상호재귀 with 는 끊는다
d = decompose("Lemma a (x : T) : P x = Q x with b (y : U) : R y = S y.")
ck("with 끊김", " ".join(d[2]), "P x = Q x")

print("\n── 3. applicability: apply ──")
a = applicability("H : True\n\nx + y = y + x", "Lemma c : forall n m, n + m = m + n.")
ck("apply 성공", (a["apply"], a["parsed"]), (True, True))
a = applicability("\n\nx * y = y * x", "Lemma c : forall n m, n + m = m + n.")
ck("apply 실패(연산자 다름)", a["apply"], False)
a = applicability("\n\nx + y = z + x", "Lemma c : forall n m, n + m = m + n.")
ck("apply 실패(변수 불일치)", a["apply"], False)
# 중간 forall 케이스가 실제로 apply 되나
a = applicability("\n\nis_tail l1 l3",
                  "Lemma t: forall (A: Type) (l1 l2: list A), is_tail l1 l2 -> "
                  "forall (l3: list A), is_tail l2 l3 -> is_tail l1 l3.")
ck("is_tail_trans apply", a["apply"], True)
# goal 이 A -> B 여도 몸통에 apply 성립
a = applicability("\n\nP -> x + y = y + x", "Lemma c : forall n m, n + m = m + n.")
ck("goal 화살표 몸통", a["apply"], True)

print("\n── 4. applicability: rewrite ──")
a = applicability("\n\na + b * c = b * c + a", "Lemma mc : forall n m, n * m = m * n.")
ck("rewrite 가능", a["rw"], True)
ck("같은 케이스 apply 불가", a["apply"], False)
a = applicability("\n\na + b = b + a", "Lemma mc : forall n m, n * m = m * n.")
ck("rewrite 불가", a["rw"], False)
a = applicability("\n\nlength (rev l) = 0", "Lemma rl : forall l, length (rev l) = length l.")
ck("rw 정방향", a["rw"], True)
a = applicability("\n\nlength l = 0", "Lemma rl : forall l, length (rev l) = length l.")
ck("rw 역방향", a["rw_rev"], True)
ck("rw 역방향 케이스 정방향불가", a["rw"], False)
# <-> 도 rewrite 대상
a = applicability("\n\nd m1 ((s,e) :: m2) <-> Q",
                  "Lemma s: forall m1 m2, d m1 m2 <-> d m2 m1.")
ck("<-> rewrite", a["rw"] or a["rw_rev"], True)

print("\n── 5. 보수성 ──")
# 파싱이 불가능하면 **적용 가능으로 간주**해야 한다 (gold 를 떨어뜨리면 안 되므로)
a = applicability("\n\nfoo", "")
ck("빈 premise → 판정불가", a["parsed"], False)
ck("판정불가 apply True", a["apply"], True)
a = applicability("", "Lemma z : forall k, k + 0 = k.")
ck("빈 goal → 판정불가", a["parsed"], False)

print("\n── 6. 한정이름 ──")
a = applicability("\n\nInt.add x y = Int.add y x",
                  "Lemma ac : forall a b, Int.add a b = Int.add b a.")
ck("qualified apply", a["apply"], True)

print("\n── 7. 자명 lemma 억제 ──")
a = applicability("\n\nP a", "Lemma junk : forall x, x = x.")
ck("?x = ?x rw 억제", a["rw"], False)

print("\n── 8. notation ↔ 함수 정규화 ──")
# ^ 는 Zpower 의 notation — 서로 매칭돼야 한다
a = applicability("\n\n(beta ^ e <= beta ^ (e + k))",
                  "Theorem zp : forall n k1 k2, Zpower n (k1 + k2) = Zpower n k1 * Zpower n k2.")
ck("^ vs Zpower rw", a["rw"], True)
# || 는 bool 이라 = 보다 강하게 묶인다: `a = b || c` 는 `a = (b||c)`
d = decompose("Theorem c: forall f1 f2, cmp Cge f1 f2 = cmp Cgt f1 f2 || cmp Ceq f1 f2.")
from tactic_gen.applicable import parse_toks, canon, as_eq
ck("|| 레벨(= 가 최상위)", as_eq(canon(parse_toks(d[2]))) is not None, True)
# 모듈 접두사 무시
a = applicability("\n\nZ.add x y = Z.add y x", "Lemma ac : forall a b, plus a b = plus b a.")
ck("Z.add ~ plus", a["apply"], True)
# a > b ≡ lt b a
a = applicability("\n\n3 > n", "Lemma g : forall k, lt k 3.")
ck("> 뒤집기", a["apply"], True)

print("\n── 9. goal 결론 추출 ──")
a = applicability("n: nat\nm: nat\nH: n <= m\n\nn + 0 = n",
                  "Lemma z : forall k, k + 0 = k.")
ck("가설블록 무시", a["apply"], True)
# [GOAL] 로 이어진 여러 goal 중 **첫** goal 이 현재 goal
a = applicability("h: T\n\nn + 0 = n\n[GOAL]\nh: T\n\nfoo bar = baz",
                  "Lemma z : forall k, k + 0 = k.")
ck("첫 goal 사용", a["apply"], True)
a = applicability("h: T\n\nfoo bar = baz\n[GOAL]\nh: T\n\nn + 0 = n",
                  "Lemma z : forall k, k + 0 = k.")
ck("뒤 goal 안 봄", a["apply"], False)

print()
if fail:
    print(f"실패 {len(fail)}건:")
    print("\n".join(fail))
    sys.exit(1)
print("전부 통과")
