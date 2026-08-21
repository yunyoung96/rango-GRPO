#!/usr/bin/env python3
"""inductive 타입 → 생성자 인덱스 **파일 단위(2단계)**.  CPU only.

## 왜 다시 만드나

기존 `data/ind_constructors_clean.json` 은 두 가지 문제가 있었다.

  ① **평가 코퍼스로 만들어졌다.**  `build_ind_constructors.py` 의 기본 DB 가
     `raw-data/coqstoq-test/coqstoq-test-sentences.db`(평가용 12개 프로젝트)였다.
     학습 코퍼스(~150개 프로젝트)의 고유 타입 9,356개 중 **629개(6.7%)** 만 덮었다.

  ② **평면 사전이라 동명 타입이 덮어써진다.**  실측으로 생성자를 가진 고유 이름
     5,811개 중 **816개(14.0%)** 가 정의를 2가지 이상 갖는다.

         Inductive list (A : Type) := | list_end : list A | list_add : …
         Inductive list (A : Type) := | nil      : list A | cons     : …

     평면 사전은 나중 것이 이긴다 → goal 의 `list` 에 **다른 프로젝트의 생성자**를
     주입한다. 없는 것보다 나쁘다 — 모델에게 틀린 사실을 가르친다.

`func_defs_v3.json` 은 이미 이 문제를 파일 단위 2단계 구조로 풀었다
(`{이름: {파일키: 정의}}` · 조회는 `augment.pick_def` 가 같은파일→같은디렉토리→
같은프로젝트→stdlib 순으로 좁힘). **같은 구조를 그대로 따른다.**

## 출력

    {"list": {"phadej-lens-laws/theories/Isomorphism.v": ["nil", "cons"],
              "someproj/Foo.v": ["list_end", "list_add"],
              "stdlib": ["nil", "cons"]}, …}

사용: python3 scripts/build_ind_index_v4.py [db] [out]
"""
import json
import os
import re
import sqlite3
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else "data/coq-dataset/sentences.db"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/ind_constructors_v4.json"

# 선언 머리 — Inductive 만 보면 CoInductive·Variant·Record·Class 를 통째로 놓친다.
IND = re.compile(r"^\s*(?:#\[[^\]]*\]\s*)?"
                 r"(?:Global\s+|Local\s+|Program\s+|Polymorphic\s+|Monomorphic\s+)*"
                 r"(?:Co)?Inductive\s+([A-Za-z_][\w']*)")
REC = re.compile(r"^\s*(?:#\[[^\]]*\]\s*)?"
                 r"(?:Global\s+|Local\s+|Program\s+|Polymorphic\s+|Monomorphic\s+)*"
                 r"(?:Record|Variant|Structure|Class)\s+([A-Za-z_][\w']*)")
FIELD = re.compile(r"([A-Za-z_][\w']*)\s*:(?!=)")


def _file_key(file_path: str) -> str:
    """`build_func_defs._file_key` 와 **같은 규칙** — 조회 코드가 하나이므로 어긋나면 안 된다."""
    p = (file_path or "").replace("\\", "/")
    if "/.opam/" in p or "/lib/coq/theories/" in p or "/lib/coq/user-contrib/" in p:
        return "stdlib"
    m = re.search(r"/repos/(.+)$", p)
    return m.group(1) if m else p.lstrip("/")


def _ctors_of(t: str) -> list:
    """Inductive 본문의 생성자 이름.

    ★ `|` 로만 찾으면 **첫 생성자에 막대가 없는 형태**를 놓친다:
        Inductive singleton_type : Type := Single.          (막대 0개)
        Inductive carry A := C0 : A -> carry A | C1 : …     (첫 개에만 없음)
    """
    if ":=" not in t:
        return []
    out = []
    for part in t.split(":=", 1)[1].split("|"):
        m = re.match(r"\s*([A-Za-z_][\w']*)", part)
        if m:
            out.append(m.group(1))
    return out


def _fields_of(t: str) -> list:
    """Record/Class/Structure 의 필드(사영함수).

        Record R := mk { f1 : T; f2 : T }.   ← 중괄호
        Class C (X : Set) := op : … .        ← 중괄호 없음(필드 1개)
    """
    if "{" in t:
        return FIELD.findall(t[t.index("{") + 1:])
    if ":=" in t:
        m = re.match(r"\s*([A-Za-z_][\w']*)\s*:(?!=)", t.split(":=", 1)[1])
        if m:
            return [m.group(1)]
    return []


def main():
    con = sqlite3.connect(DB)
    idx: dict = {}
    n_seen = 0
    for text, fp in con.execute("SELECT text, file_path FROM sentence"):
        t = text or ""
        m = IND.match(t)
        cs = _ctors_of(t) if m else None
        if not m:
            m = REC.match(t)
            cs = _fields_of(t) if m else None
        if not m or not cs:
            continue
        name = m.group(1)
        # 정제: 1글자 타입·비정상 생성자 제거(기존 규칙 유지)
        if len(name) < 2 or not name[0].isalpha():
            continue
        if not all(c and c[0].isalpha() for c in cs):
            continue
        n_seen += 1
        slot = idx.setdefault(name, {})
        key = _file_key(fp)
        # 같은 파일에 같은 이름이 여러 번이면 **처음 것**을 남긴다
        # (길이로 고르지 않는다 — 그 규칙이 func_defs v2 의 오염을 만들었다)
        if key not in slot:
            slot[key] = cs
    con.close()

    # stdlib 보강 — 코퍼스에 없을 수 있는 기본 타입
    for t, cs in {"and": ["conj"], "or": ["or_introl", "or_intror"], "ex": ["ex_intro"],
                  "nat": ["O", "S"], "positive": ["xI", "xO", "xH"],
                  "bool": ["true", "false"], "prod": ["pair"],
                  "sumbool": ["left", "right"], "option": ["Some", "None"],
                  "list": ["nil", "cons"]}.items():
        idx.setdefault(t, {}).setdefault("stdlib", cs)

    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    json.dump(idx, open(OUT, "w"), ensure_ascii=False)
    multi = sum(1 for v in idx.values() if len(v) > 1)
    print(f"선언 {n_seen:,}건 → 고유 이름 {len(idx):,}개 (스코프 2개 이상 {multi:,}개)")
    print(f"저장: {OUT}")
    for k in ("nat", "list", "bool", "option"):
        if k in idx:
            sc = list(idx[k].items())[:2]
            print(f"   {k}: {sc}")


if __name__ == "__main__":
    main()
