#!/usr/bin/env python3
"""★ **표준 라이브러리 이름 집합**을 만든다 — 익명화·주입에서 제외하기 위해.

## 왜

익명화의 목적은 "**그 프로젝트에만 통하는 이름**을 외워서 찍는 습관" 을 끊는 것이다.
`Nat.add_comm` 같은 표준 라이브러리 이름을 아는 것은 암기가 아니라 **어느 프로젝트에서나
통하는 진짜 지식**이고, 사전학습 모델이 이미 안다. 익명화하면 그 지식을 막는다.

실측(TRAIN 800건): **gold lemma 의 62.1% 가 stdlib** · 후보 풀의 92.7% 가 stdlib.

## 왜 별도 인덱스가 필요한가

  · `func_defs_v3.json` 은 **정의**(타입·함수)만 담고 `stdlib` 키로 출처를 구분한다
  · **premise lemma** 는 거기 없다 → `renameable()` 을 쓰면 235건 중 134건이 걸려
    치환이 아예 안 된다(코드 주석의 실측)
  · collate 시점의 `example.premises` 는 **문자열**이라 파일 경로를 모른다

→ `sentences.db` 의 `file_path` 로 **이름 → stdlib 여부**를 미리 뽑아 둔다.

## 판정

경로가 Coq 표준 라이브러리이면 stdlib.
같은 이름이 stdlib 과 프로젝트 양쪽에 있으면 **프로젝트 쪽을 우선**한다(익명화 대상 유지) —
잘못 남기는 것보다 잘못 바꾸는 편이 안전하다.

사용: python3 scripts/build_stdlib_index.py [out.json]
"""
import collections
import json
import re
import sqlite3
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "data/stdlib_names.json"
DB = "/tmp/coq-dataset/sentences.db"

# ★ 프로젝트 안에 **복사된** stdlib 도 잡아야 한다
#   (예: UniMath/sub/coq/theories/... · Priyanka-Mondal-Coq/lib/theories/Numbers/...)
_STD = re.compile(
    r"(opam/[^/]*/lib/coq/theories/"
    r"|/coq/theories/"
    r"|coq_projects/coq/theories/"
    r"|/stdlib/"
    r"|/Coq/theories/"
    r"|/lib/theories/(Init|Lists|Arith|ZArith|NArith|Bool|Logic|Reals|QArith|Sets|"
    r"Relations|Classes|Numbers|Strings|Sorting|Structures|Program|Wellfounded|"
    r"FSets|MSets|Vectors|setoid_ring|micromega|btauto|nsatz|funind|ssr)/"
    r"|/theories/(Init|Arith|ZArith|NArith|Numbers|Lists|Bool|Logic|Reals|QArith|"
    r"Sets|Relations|Classes|Strings|Sorting|Structures|Program|Wellfounded|"
    r"FSets|MSets|Vectors|setoid_ring|micromega|ssr)/)", re.I)
_DECL = re.compile(
    r"^\s*(?:Lemma|Theorem|Corollary|Remark|Fact|Proposition|Property|Example|"
    r"Definition|Fixpoint|CoFixpoint|Inductive|CoInductive|Variant|Record|"
    r"Instance|Axiom|Parameter|Let|Notation|Class|Structure|Program\s+\w+)\s+"
    r"([A-Za-z_][\w']*)")

con = sqlite3.connect(DB)
std, proj = set(), set()
n = 0
for text, path in con.execute("select text, file_path from sentence"):
    n += 1
    m = _DECL.match(text or "")
    if not m:
        continue
    name = m.group(1)
    if _STD.search(path or ""):
        std.add(name)
    else:
        proj.add(name)
    if n % 2_000_000 == 0:
        print(f"   … {n:,} 문장", flush=True)

# ★ **stdlib 우선**. 한 번이라도 stdlib 경로에 나오면 stdlib 으로 본다.
#
#   처음엔 "양쪽에 있으면 프로젝트 우선" 으로 했는데 틀렸다(실측):
#     · `nztail` 은 11개 경로 전부 stdlib 사본인데, `UniMath/sub/coq/theories/...`
#       처럼 **프로젝트 안에 복사된 stdlib** 이라 프로젝트로 분류됐다
#     · `add_comm` 은 103개 경로 중 대부분이 실습 파일에서 각자 정의한 것이다
#   → 이런 **보편적인 이름**은 그 프로젝트 고유 지식이 아니다. 익명화의 목적
#     (프로젝트 고유 이름 암기 차단)에 해당하지 않으므로 stdlib 으로 본다.
only_std = std
both = std & proj
json.dump(sorted(only_std), open(OUT, "w"))
print(f"\n■ stdlib 이름 인덱스")
print(f"   문장 {n:,}")
print(f"   stdlib 이름(제외 대상)   {len(only_std):,}")
print(f"   그중 프로젝트에도 있음   {len(both):,}   (보편적 이름 — 그래도 제외)")
print(f"   프로젝트에만            {len(proj - std):,}")
print(f"\n   → {OUT}")
samples = sorted(x for x in only_std if x.startswith(("add_", "app_", "rev_", "mul_")))[:10]
print(f"   표본: {samples}")
