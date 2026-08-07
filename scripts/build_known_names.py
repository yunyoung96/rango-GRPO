#!/usr/bin/env python3
"""실재 이름 집합 — 환각 lemma 필터의 허용집합(scripts/../src/model_deployment/name_filter.py).

★ 선언 이름만으로는 부족하다: `Inductive permission := Freeable | Writable | Readable | Nonempty`
  에서 `permission` 만 담으면 `destruct (... Readable)` 같은 **정상** 후보를 오탐한다.
  → 생성자·레코드 필드 이름까지 담는다(실측: 오탐 2.72% → 아래 참조).
"""
import json, os, re, sqlite3, sys

DECL = re.compile(r'^\s*(?:#\[[^\]]*\]\s*)?(?:Local\s+|Global\s+|Program\s+|Polymorphic\s+)*'
                  r'(?:Lemma|Theorem|Definition|Fixpoint|CoFixpoint|Inductive|CoInductive|Corollary|'
                  r'Remark|Fact|Proposition|Property|Instance|Record|Variant|Structure|Class|'
                  r'Axiom|Parameter|Notation|Ltac|Hypothesis|Variable|Let|Scheme|Function)\s+([A-Za-z_][\w\']*)')
IS_TYPE = re.compile(r'^\s*(?:#\[[^\]]*\]\s*)?(?:Local\s+|Global\s+|Polymorphic\s+)*'
                     r'(?:Inductive|CoInductive|Variant|Record|Structure|Class)\b')
# ':=' 뒤 '|' 로 구분된 각 분기의 선두 식별자 = 생성자. Record 는 '{ f1 : T; f2 : T }' 필드.
CTOR = re.compile(r"\|\s*([A-Za-z_][\w']*)")
FIELD = re.compile(r"[{;]\s*([A-Za-z_][\w']*)\s*:")


def main():
    names = set()
    for db in sys.argv[1:] or ["data/coq-dataset/sentences.db"]:
        if not os.path.exists(db):
            continue
        c = sqlite3.connect(db)
        try:
            rows = c.execute("SELECT text FROM sentence")
        except sqlite3.Error:
            c.close(); continue
        for (t,) in rows:
            t = t or ""
            m = DECL.match(t)
            if m:
                names.add(m.group(1).split('.')[-1])
            if IS_TYPE.match(t):
                body = t.split(':=', 1)[-1]
                names.update(CTOR.findall(body))          # 생성자
                names.update(FIELD.findall(body))         # 레코드 필드
                # '|' 없이 첫 생성자를 쓰는 표기: ':= Ctor : T | ...'
                m2 = re.match(r"\s*([A-Za-z_][\w']*)\s*:", body)
                if m2:
                    names.add(m2.group(1))
        c.close()
    names = {n for n in names if len(n) > 1}
    out = os.environ.get("KNOWN_NAMES_PATH", "data/known_names.json")
    json.dump(sorted(names), open(out, "w"))
    print(f"실재 이름 {len(names):,}개 (선언+생성자+필드) → {out}")


if __name__ == "__main__":
    main()
