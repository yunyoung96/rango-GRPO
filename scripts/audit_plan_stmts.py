#!/usr/bin/env python3
"""계획 파일의 assert 명제가 **그 자리에서 설 수 없는** 유형을 정적으로 센다.

## 배경

동적 Coq 검증 250건에서 12건(4.8%)이 실패했다. 원인은 하나를 셋으로 말한 것이다 —
계획은 lemma 의 **선언 원문**을 assert 명제로 쓰는데, Coq 이 사용 지점에서
**정교화(elaborate)한 타입**은 그것과 다를 수 있다.

  ① 섹션 변수 / 암묵 인자   `Section S. Variable R : Type. Lemma foo : forall a b c : R, …`
                            섹션 밖에서 foo 의 타입은 `forall R a b c, …` 다.
                            원문을 그대로 assert 하면 `The variable R was not found`.
  ② notation 스코프         `∀ x y : string, … ↔ … ≠ …` · `(p <=? q) = true <-> p <= q`
                            그 notation 을 여는 Import 가 그 지점에 없으면 렉서가 막힌다.
  ③ 바인더 문법 재조립      `Lemma f (E F : Type) (h : E -> F) : …` 를
                            `forall E F : Type (h : E -> F), …` 로 옮기면 문법이 깨진다.

## 무엇을 세나

명제 안에서 **어디에도 묶이지 않은 자유 식별자**(①③ 의 표지)와 **비 ASCII 기호**(②)를
센다. 완벽한 판정이 아니라 **상한 추정**이다 — 정확한 판정은 Coq 뿐이다.

사용: PYTHONPATH=src python3 scripts/audit_plan_stmts.py [계획파일] [표본수]
"""
import collections
import json
import re
import sys

PLANS = sys.argv[1] if len(sys.argv) > 1 else "data/cut_plans_all.jsonl"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 0        # 0 = 전량

# 명제 안에서 이름을 **묶는** 자리들
_BIND = re.compile(
    r"(?:forall|fun|exists|∀|∃|λ)\s+([^,]*?)[,.]|"     # forall x y : T,
    r"\(\s*([A-Za-z_][\w']*(?:\s+[A-Za-z_][\w']*)*)\s*:", re.S)
_ID = re.compile(r"(?<![\w'])([A-Za-z_][\w']*)(?![\w'])")
# 자유로워도 되는 것 — Coq 기본 어휘·타입·연산
_OK = set("""forall exists fun let in if then else match with end return as
nat bool Prop Set Type Z N R positive list option unit True False tt nil cons
Some None and or not iff eq refl S O prod sum sig sigT ex proj1 proj2 fst snd
plus mult minus le lt ge gt eqb leb ltb negb andb orb implb xorb id comp
string ascii bytes char int int63 float array""".split())

st = collections.Counter()
samples = collections.defaultdict(list)
n = 0
for ln in open(PLANS):
    if N and n >= N:
        break
    try:
        d = json.loads(ln)
    except Exception:
        continue
    if d.get("kind") != "plan" or not d.get("cut"):
        continue
    n += 1
    for m in re.finditer(r"e?assert\s*\((.*?)\)\s*as\s+H_asrt", d["cut"], re.S):
        stmt = m.group(1)
        st["명제"] += 1
        # ② 비 ASCII 기호 — notation 스코프가 필요할 가능성이 높다
        if any(ord(c) > 127 for c in stmt):
            st["② 비ASCII 기호 (notation 스코프)"] += 1
            if len(samples["②"]) < 3:
                samples["②"].append(stmt[:90])
            continue
        # ①③ 어디에도 안 묶인 자유 식별자
        bound = set()
        for b in _BIND.finditer(stmt):
            for g in b.groups():
                if g:
                    bound |= set(_ID.findall(g))
        ids = set(_ID.findall(stmt))
        free = {x for x in ids - bound - _OK
                if len(x) <= 3 and (x[0].isupper() or x.islower())}
        # 대문자 한두 글자(R·A·E·F)나 짧은 소문자(elt·g)가 자유로우면 섹션 변수 냄새
        if free:
            st["①③ 안 묶인 짧은 자유 식별자 (섹션 변수 의심)"] += 1
            if len(samples["①③"]) < 3:
                samples["①③"].append(f"{sorted(free)[:4]}  ←  {stmt[:70]}")
        else:
            st["✓ 표지 없음"] += 1

print(f"■ 계획 {n:,}건 · assert 명제 {st['명제']:,}개\n")
tot = max(st["명제"], 1)
for k in sorted(st):
    if k == "명제":
        continue
    print(f"   {k:44s} {st[k]:8,}  {st[k]/tot*100:5.1f}%")
print()
for k, v in samples.items():
    print(f"   [{k}] 예")
    for x in v:
        print(f"      {x}")
print()
print("   ※ 상한 추정이다 — 자유 식별자가 있어도 그 자리에서 정의돼 있으면 통과한다.")
print("     정확한 판정은 Coq 뿐이고, 동적 검증 실측 실패율은 4.8% 였다.")
