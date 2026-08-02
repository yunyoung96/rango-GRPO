#!/usr/bin/env python3
"""inductive 타입 → 생성자 목록 인덱스 (정제본). CPU. 다른 서버 재현용.
코퍼스(coqstoq sentences.db)의 Inductive 정의 파싱 → 빈생성자·1글자 제거 → data/ind_constructors_clean.json.
사용: python3 scripts/build_ind_constructors.py [db경로] [출력경로]"""
import sqlite3, re, json, sys, os

DB = sys.argv[1] if len(sys.argv) > 1 else "raw-data/coqstoq-test/coqstoq-test-sentences.db"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/ind_constructors_clean.json"

IND = re.compile(r'^\s*(?:#\[[^\]]*\]\s*)?Inductive\s+([A-Za-z_][\w\']*)')
CTOR = re.compile(r'\|\s*([A-Za-z_][\w\']*)')

def main():
    c = sqlite3.connect(DB)
    raw = {}
    for (text,) in c.execute("SELECT text FROM sentence"):
        m = IND.match(text)
        if m:
            raw[m.group(1)] = CTOR.findall(text)
    # 표준 inductive 보강(코퍼스에 없을 수 있는 stdlib)
    for t, cs in {'and': ['conj'], 'or': ['or_introl', 'or_intror'], 'ex': ['ex_intro'],
                  'nat': ['O', 'S'], 'positive': ['xI', 'xO', 'xH'], 'bool': ['true', 'false'],
                  'prod': ['pair'], 'sumbool': ['left', 'right'], 'option': ['Some', 'None'],
                  'list': ['nil', 'cons']}.items():
        raw.setdefault(t, cs)
    # 정제: 빈 생성자·1글자 타입·비정상 제거
    clean = {k: v for k, v in raw.items()
             if v and len(k) > 1 and k[0].isalpha()
             and all(cc and cc[0].isalpha() for cc in v)
             and not re.fullmatch(r'[a-z]', k)}
    os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
    json.dump(clean, open(OUT, 'w'), ensure_ascii=False)
    print(f"Inductive 파싱 {len(raw)} → 정제 {len(clean)}  저장: {OUT}")
    print("  예:", list(clean)[:12])

if __name__ == "__main__":
    main()
