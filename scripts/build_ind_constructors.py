#!/usr/bin/env python3
"""inductive 타입 → 생성자 목록 인덱스 (정제본). CPU. 다른 서버 재현용.
코퍼스(coqstoq sentences.db)의 Inductive 정의 파싱 → 빈생성자·1글자 제거 → data/ind_constructors_clean.json.
사용: python3 scripts/build_ind_constructors.py [db경로|.v루트] [출력경로]

★ 소스 2종(같은 정제규칙·같은 출력스키마):
  · sentence.db  — 원본 경로. 문장 1행 = 1 statement.
  · .v 디렉토리 — db 없는 서버용 폴백(예: CoqStoq). Inductive~종결'.'까지를 한 statement로 스캔.
"""
import sqlite3, re, json, sys, os

DB = sys.argv[1] if len(sys.argv) > 1 else "raw-data/coqstoq-test/coqstoq-test-sentences.db"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/ind_constructors_clean.json"

IND = re.compile(r'^\s*(?:#\[[^\]]*\]\s*)?Inductive\s+([A-Za-z_][\w\']*)')
CTOR = re.compile(r'\|\s*([A-Za-z_][\w\']*)')
# .v 폴백용: 파일 어디서든 Inductive/CoInductive 선언 시작을 찾는다(줄머리 제한 없음).
IND_ANY = re.compile(r'\b(?:Co)?Inductive\s+([A-Za-z_][\w\']*)')
END_DOT = re.compile(r'\.(?=\s|$)')            # statement 종결 '.'(Nat.add 같은 qualified 는 뒤가 공백 아님)


def _scan_vfiles(root: str) -> dict:
    """.v 트리에서 Inductive statement 파싱 → {타입: [생성자...]}. db 폴백(동일 CTOR 규칙)."""
    raw = {}
    n_files = 0
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if not fn.endswith(".v"):
                continue
            n_files += 1
            try:
                text = open(os.path.join(dirpath, fn), encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for m in IND_ANY.finditer(text):
                e = END_DOT.search(text, m.end())          # 선언 시작 → 종결 '.' 까지가 statement
                block = text[m.start(): e.end() if e else min(len(text), m.end() + 4000)]
                raw[m.group(1)] = CTOR.findall(block)
    print(f"  .v 스캔: {n_files}개 파일 (root={root})")
    return raw


def main():
    if os.path.isdir(DB):                                   # ★ 폴백: .v 트리(sentences.db 없는 서버)
        raw = _scan_vfiles(DB)
    else:
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
