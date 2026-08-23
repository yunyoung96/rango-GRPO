#!/usr/bin/env python3
"""★ stdlib 이름 집합 **보강** — 생성자·필드가 통째로 빠져 있었다.

기존 `build_stdlib_names.py` 는 DatasetFile 의 premise 선언에서 이름을 모았다.
그런데 rango 의 premise 는 `Lemma|Definition|...` 선언만 담고 **`Inductive` 의
생성자**는 담지 않는다. 그래서 `Acc_intro`(= `Inductive Acc ... := Acc_intro : ...`)
같은 이름이 집합에 없어 **환각으로 오신고**됐다(덤프 [8]).

여기서는 문장 DB 를 **전수** 훑어 다음을 전부 모은다:
    · 선언 head 이름            Lemma/Definition/Fixpoint/Inductive/Record/Class/...
    · Inductive·Variant 의 생성자   `:= | C1 : ... | C2 : ...`
    · Record·Class 의 필드·생성자   `:= mk { f1 : ...; f2 : ... }`
    · `Notation "..." := (head ...)` 의 head

사용: python3 scripts/build_stdlib_names2.py
"""
import json
import re
import sqlite3

DB = "raw-data/coq-dataset/sentences.db"
OUT = "data/stdlib_names.json"

_HEAD = re.compile(
    r"^\s*(?:#\[[^\]]*\]\s*)?(?:Global\s+|Local\s+|Polymorphic\s+|Monomorphic\s+|"
    r"Program\s+|Cumulative\s+|NonCumulative\s+|Private\s+)*"
    r"(Lemma|Theorem|Corollary|Remark|Fact|Proposition|Property|Definition|Example|"
    r"Fixpoint|CoFixpoint|Inductive|CoInductive|Variant|Record|Structure|Class|"
    r"Instance|Axiom|Parameter|Conjecture|Ltac|Scheme|Let)\s+([A-Za-z_][\w']*)")
_WITH = re.compile(r"\bwith\s+([A-Za-z_][\w']*)")
_NOTA = re.compile(r'(?:Notation|Infix)\s+"[^"]+"\s*:=\s*\(?\s*@?\s*([A-Za-z_][\w\']*)')


def ctors(text: str) -> set:
    """`:=` 뒤의 생성자 이름. `| C : T` 와 첫 생성자(막대 없음) 둘 다."""
    out = set()
    i = text.find(":=")
    if i < 0:
        return out
    body = text[i + 2:]
    # 중괄호 안(레코드 필드)은 따로 처리하므로 여기서는 막대 기준만
    for m in re.finditer(r"(?:^|\|)\s*([A-Za-z_][\w']*)\s*(?::|\s*\()", body):
        out.add(m.group(1))
    m = re.match(r"\s*([A-Za-z_][\w']*)\s*:", body)      # 막대 없는 첫 생성자
    if m:
        out.add(m.group(1))
    return out


def fields(text: str) -> set:
    """`{ f1 : T; f2 : T }` 의 필드 + `:= mkX {` 의 생성자."""
    out = set()
    m = re.search(r":=\s*([A-Za-z_][\w']*)?\s*\{(.*)\}", text, re.S)
    if not m:
        return out
    if m.group(1):
        out.add(m.group(1))
    for f in re.finditer(r"(?:^|[;{])\s*([A-Za-z_][\w']*)\s*(?::>?|\s*:=)", m.group(2)):
        out.add(f.group(1))
    return out


def main():
    old = set(json.load(open(OUT)))
    c = sqlite3.connect(DB)
    rows = c.execute(
        "select text, sentence_type from sentence where file_path like '%lib/coq/theories%'"
    ).fetchall()
    new = set()
    n_ctor = n_field = 0
    for text, stype in rows:
        text = text or ""
        m = _HEAD.match(text)
        if m:
            new.add(m.group(2))
            kind = m.group(1)
            if kind in ("Inductive", "CoInductive", "Variant"):
                cs = ctors(text)
                n_ctor += len(cs)
                new |= cs
                for w in _WITH.findall(text):      # 상호재귀 Inductive
                    new.add(w)
            elif kind in ("Record", "Structure", "Class"):
                fs = fields(text)
                n_field += len(fs)
                new |= fs
        for h in _NOTA.findall(text):
            new.add(h)
    # 한 글자·숫자시작 등 잡음 제거
    new = {x for x in new if len(x) >= 2 and not x[0].isdigit()}
    merged = sorted(old | new)
    json.dump(merged, open(OUT, "w"))
    print(f"■ {OUT}")
    print(f"   기존 {len(old):,} → **{len(merged):,}**  (+{len(merged)-len(old):,})")
    print(f"   DB 문장 {len(rows):,} · 생성자 {n_ctor:,} · 필드 {n_field:,}")
    for probe in ("Acc_intro", "or_introl", "conj", "eq_refl", "S", "cons",
                  "Rlt_trans", "ex_intro", "existT", "mkRat"):
        print(f"   {probe:12s} {'있음' if probe in set(merged) else '없음'}")


if __name__ == "__main__":
    main()
