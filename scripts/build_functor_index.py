#!/usr/bin/env python3
"""★ **펑터 인스턴스 전개 인덱스** — `Module N := F(A).` 로 생겨나는 이름을 되살린다.

문제(`docs/premise/functor-names.md`): CompCert 가 tactic 인자로 부르는 한정이름의
27.0% 는 **소스 어디에도 선언이 없다.** `Pregmap.gso` 는 40회 쓰이는데 선언은 0회다 —
`Module Pregmap := EMap(PregEq).` 한 줄이 만들어 낸다. 검색 풀은 선언문으로
만들어지므로 그 이름은 원리적으로 풀에 없다.

여기서 하는 일
    ① 모든 .v 에서 `Module N := F(A).` 를 찾는다            (Coq 실행 불필요)
    ② sentence DB 에서 module 이 F 인 선언들을 긁는다
    ③ `N.member` 이름으로 항목을 만든다

명제 본문은 두 선택지가 있고 둘 다 낸다.
    abstract : 펑터 안의 원문 그대로 (이름만 N.member)
    concrete : 인자 모듈 A 의 `Definition t := τ` 를 따라 추상 타입을 치환

사용: python3 scripts/build_functor_index.py <sentences.db> <repos_root> <out.json>
예:   python3 scripts/build_functor_index.py \
        raw-data/coqstoq-test/coqstoq-test-sentences.db CoqStoq/test-repos \
        data/functor_index_test.json
"""
import collections
import glob
import json
import os
import re
import sqlite3
import sys

DB, ROOT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

# `Module N := F(A).` / `Module N : S := F(A).` / `Module N <: S := F(A) (B).`
INST = re.compile(
    r"(?m)^\s*Module\s+([A-Za-z_][\w']*)\s*(?::\s*[\w'.]+\s*|<:\s*[\w'.]+\s*)?"
    r":=\s*([A-Za-z_][\w'.]*)\s*\(([^)]*)\)")
DECL = re.compile(
    r"^\s*(?:Global\s+|Local\s+|Program\s+)?"
    r"(Lemma|Theorem|Corollary|Remark|Fact|Proposition|Definition|Fixpoint|Inductive|Record)"
    r"\s+([A-Za-z_][\w']*)")
DEFT = re.compile(r"(?m)^\s*Definition\s+t\s*:?=?\s*(.+?)\.\s*$")

# ── ① 인스턴스 수집 ───────────────────────────────────────────────────
inst = []          # (N, F, A, file)
argdef = {}        # A -> {"t": τ}
for f in glob.glob(os.path.join(ROOT, "**", "*.v"), recursive=True):
    try:
        s = re.sub(r"\(\*.*?\*\)", " ", open(f, errors="ignore").read(), flags=re.S)
    except Exception:
        continue
    for m in INST.finditer(s):
        inst.append((m.group(1), m.group(2).split(".")[-1], m.group(3).strip(), f))
    # 인자 모듈의 `Definition t := τ` (구체화용)
    for m in re.finditer(r"(?ms)^\s*Module\s+([A-Za-z_][\w']*)\s*\.\s*(.*?)^\s*End\s+\1\s*\.", s):
        d = DEFT.search(m.group(2))
        if d:
            argdef.setdefault(m.group(1), {})["t"] = d.group(1).strip()
print(f"■ 펑터 인스턴스 {len(inst)}건 · 인자 모듈 정의 {len(argdef)}종", flush=True)

# ── ② 펑터 멤버 수집 ──────────────────────────────────────────────────
con = sqlite3.connect(DB)
members = collections.defaultdict(list)   # F -> [(kind, name, text)]
rows = con.execute("SELECT text, module, sentence_type FROM sentence "
                   "WHERE module IS NOT NULL AND module != '[]'").fetchall()
for text, mod, st in rows:
    d = DECL.match(text or "")
    if not d:
        continue
    for part in re.findall(r'"([^"]+)"', mod or ""):
        members[part].append((d.group(1), d.group(2), text))
print(f"■ module 컬럼이 있는 선언 {sum(len(v) for v in members.values()):,}개 "
      f"· 모듈 {len(members):,}종", flush=True)

# ── ③ 전개 ────────────────────────────────────────────────────────────
out = []
hit = collections.Counter()
for N, F, A, f in inst:
    ms = members.get(F, [])
    if not ms:
        hit["펑터 멤버 못 찾음"] += 1
        continue
    hit["전개됨"] += 1
    tau = (argdef.get(A) or {}).get("t")
    for kind, name, text in ms:
        # abstract: 이름만 N.name
        abstract = re.sub(r"^(\s*(?:Global\s+|Local\s+|Program\s+)?"
                          r"(?:Lemma|Theorem|Corollary|Remark|Fact|Proposition|"
                          r"Definition|Fixpoint|Inductive|Record)\s+)" + re.escape(name),
                          r"\g<1>" + N + "." + name, text, count=1)
        concrete = None
        if tau:
            # elt / X.t / t  →  τ  (문자열 치환. Coq 실행 없이 근사)
            concrete = re.sub(r"(?<![\w'])(?:elt|X\.t)(?![\w'])", tau, abstract)
        out.append(dict(name=f"{N}.{name}", instance=N, functor=F, arg=A,
                        kind=kind, member=name, file=f,
                        abstract=abstract, concrete=concrete))
print(f"■ {dict(hit)}")
print(f"■ 전개된 이름 {len(out):,}개 (서로 다른 {len({o['name'] for o in out}):,}종)", flush=True)
json.dump(out, open(OUT, "w"), ensure_ascii=False)
print(f"→ {OUT}")

# 검증: 실제로 쓰이는데 선언이 없던 이름을 얼마나 덮나
used = collections.Counter()
REF = re.compile(r"\b(?:e?apply|e?rewrite|exact|specialize|refine|destruct|induction|unfold)"
                 r"\s+(?:<-\s*)?\(?\s*([A-Z][\w']*)\.([a-z_][\w']*)")
for f in glob.glob(os.path.join(ROOT, "**", "*.v"), recursive=True):
    try:
        s = re.sub(r"\(\*.*?\*\)", " ", open(f, errors="ignore").read(), flags=re.S)
    except Exception:
        continue
    for m in REF.finditer(s):
        used[f"{m.group(1)}.{m.group(2)}"] += 1
have = {o["name"] for o in out}
tot = sum(used.values())
cov = sum(v for k, v in used.items() if k in have)
print(f"\n■ 검증 — tactic 인자 한정 참조 {tot:,}회 중 전개 인덱스가 덮는 것 "
      f"{cov:,} = {cov/max(tot,1)*100:.1f}%")
for k, v in used.most_common(400):
    if k in have:
        print(f"   ✓ {v:5d}  {k}")
        if v < 40:
            break
