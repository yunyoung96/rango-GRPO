#!/usr/bin/env python3
"""SearchPattern 이 **몇 건을 뱉는지**와, 상한 정책이 회수율을 해치는지 잰다.

## 문제

프롬프트에 실리는 premise 는 중앙 21개다. 그런데 넓은 질의는 수백 건을 뱉는다
(`SearchPattern (_ <= _)` → 192건). 그대로 합치면 노이즈가 gold 를 밀어낸다.

## 정책 후보

질의를 **좁은 것부터** 날리고 누적 결과가 상한 K 를 넘으면 멈춘다. 좁은 질의가 1~3건으로
정확히 집어내므로 대부분은 K 에 닿기 전에 gold 를 회수할 것이다 — 이 가정을 검증한다.

  · K 별 회수율(gold 를 얻었나)
  · K 별 실제 반환 건수
  · 몇 번째 질의에서 gold 가 나왔나

사용: python3 scripts/measure_search_yield.py
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, "src")
from coqpyt.coq.base_file import CoqFile  # noqa: E402
from tactic_gen.search_query import queries  # noqa: E402

S = Path("/tmp/claude-0/-app-coq-modeling/e02d0688-7cb1-43a8-aa0e-ee8afd60ce19/scratchpad/sy")
S.mkdir(parents=True, exist_ok=True)

Z = "Require Import ZArith.\nOpen Scope Z_scope.\n"
L = "Require Import List.\nImport ListNotations.\n"
N = "Require Import Arith.\n"

# (헤더, goal 을 세우는 문장, 모델이 보는 proof_state, 찾아야 할 gold)
CASES = [
    (Z, "Goal forall a:Z, 0 < a -> Z.succ 0 <= a.\nProof.\nintros a H.\n",
     "a: Z\nH: 0 < a\n\nZ.succ 0 <= a", "Zlt_le_succ"),
    (Z, "Goal forall a b:Z, a * b = b * a.\nProof.\nintros a b.\n",
     "a, b: Z\n\na * b = b * a", "mul_comm"),
    (L, "Goal forall (l: list nat), length (rev l) = length l.\nProof.\nintros l.\n",
     "l: list nat\n\nlength (rev l) = length l", "rev_length"),
    (L, "Goal forall (A:Type) (l1 l2: list A), length (l1 ++ l2) = length l1 + length l2.\n"
        "Proof.\nintros A l1 l2.\n",
     "A: Type\nl1, l2: list A\n\nlength (l1 ++ l2) = length l1 + length l2", "app_length"),
    (Z, "Goal forall a b c:Z, 0 <= a -> 0 <= b -> 0 < c -> (a+b)^c <= 2^Z.pred c * (a^c + b^c).\n"
        "Proof.\nintros a b c Ha Hb Hc.\n",
     "a, b, c: Z\nHa: 0 <= a\nHb: 0 <= b\nHc: 0 < c\n\n(a + b) ^ c <= 2 ^ Z.pred c * (a ^ c + b ^ c)",
     "pow_add_upper"),
    (L, "Goal forall (A:Type) (l: list A) (x:A), In x (rev l) -> In x l.\nProof.\nintros A l x H.\n",
     "A: Type\nl: list A\nx: A\nH: In x (rev l)\n\nIn x l", "in_rev"),
    (N, "Goal forall n m:nat, n + m = m + n.\nProof.\nintros n m.\n",
     "n, m: nat\n\nn + m = m + n", "add_comm"),
    (Z, "Goal forall a:Z, Z.abs a >= 0.\nProof.\nintros a.\n",
     "a: Z\n\nZ.abs a >= 0", "abs_nonneg"),
    (L, "Goal forall (A:Type) (l: list A), rev (rev l) = l.\nProof.\nintros A l.\n",
     "A: Type\nl: list A\n\nrev (rev l) = l", "rev_involutive"),
    (Z, "Goal forall a b:Z, Z.max a b >= a.\nProof.\nintros a b.\n",
     "a, b: Z\n\nZ.max a b >= a", "le_max_l"),
]

_NM = re.compile(r"^\s*([A-Za-z_][\w'\.]*)\s*:")
KS = [10, 20, 30, 50, 1000]
hit_at = {k: 0 for k in KS}
yield_at = {k: [] for k in KS}
first_q = []
all_rows = []

for ci, (hdr, setup, state, gold) in enumerate(CASES):
    f = S / f"c{ci}.v"
    f.write_text(hdr + setup)
    qs = queries(state)
    cf = CoqFile(str(f), timeout=90)
    cf.run()
    per = []
    for q in qs:
        before = len([d for d in cf.diagnostics if getattr(d, "severity", 0) == 3])
        n = len(cf.steps) - 1
        t0 = time.time()
        try:
            cf.add_step(n, "\n" + q)
            cf.exec(1)
        except Exception:
            per.append((q, 0.0, []))
            continue
        dt = time.time() - t0
        ds = [d for d in cf.diagnostics if getattr(d, "severity", 0) == 3][before:]
        got = [m.group(1) for m in (_NM.match(getattr(d, "message", "")) for d in ds) if m]
        per.append((q, dt, got))
    cf.close()

    # 좁은 것부터 누적, 상한 K 에서 중단했을 때의 결과
    base = gold.split(".")[-1]
    fq = None
    for k in KS:
        acc, seen = [], set()
        stopped = False
        for qi, (q, dt, got) in enumerate(per):
            if len(acc) + len(got) > k and acc:
                stopped = True
                break
            for g in got:
                if g not in seen:
                    seen.add(g)
                    acc.append(g)
            if fq is None and any(g.split(".")[-1] == base for g in got):
                fq = qi + 1
        h = any(g.split(".")[-1] == base for g in acc)
        hit_at[k] += h
        yield_at[k].append(len(acc))
    first_q.append(fq)
    all_rows.append((gold, [(q, len(got)) for q, _, got in per],
                     sum(dt for _, dt, _ in per)))

print(f"■ 케이스 {len(CASES)}개 · 질의별 반환 건수\n")
for gold, rows, t in all_rows:
    print(f"  {gold:16s} ({t*1000:5.0f}ms)")
    for q, c in rows:
        mark = "  ← 넓음" if c > 30 else ""
        print(f"      {c:4d}건  {q}{mark}")

print(f"\n■ 상한 K 별 — 회수율과 실제 반환량\n")
print(f"   {'K':>6s} {'회수율':>8s} {'반환 중앙':>10s} {'반환 최대':>10s}")
for k in KS:
    ys = sorted(yield_at[k])
    lbl = "무제한" if k == 1000 else str(k)
    print(f"   {lbl:>6s} {hit_at[k]}/{len(CASES)} = {hit_at[k]/len(CASES)*100:3.0f}%"
          f" {ys[len(ys)//2]:9d} {ys[-1]:10d}")

ok = [x for x in first_q if x]
print(f"\n   gold 가 나온 질의 순번: {first_q}")
if ok:
    print(f"   → {sum(1 for x in ok if x <= 2)}/{len(ok)} 이 **1~2번째(가장 좁은) 질의**에서 회수")
