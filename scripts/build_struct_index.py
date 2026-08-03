#!/usr/bin/env python3
"""구조 인덱스 빌드 (전체 코퍼스, cross-project 전이용). CPU.
타입 정의(Inductive+Definition) + 함수 정의(Definition+Fixpoint) → stdlib여부 태깅.
소스: coqstoq sentences.db(12프로젝트) + 모든 repos/*.v (compcert만 아님 = 전이 위해).
출력: data/type_defs.json, data/func_defs.json  = {name: [정의, is_stdlib]}
"""
import sqlite3, re, json, sys, glob, os

DB = "raw-data/coqstoq-test/coqstoq-test-sentences.db"
STDLIB_NAMES = {'nat','Z','positive','N','bool','list','option','prod','sum','comparison','unit',
                'sumbool','sumor','sig','ex','and','or','eq','byte','int','int64','float','float32',
                'Q','R','True','False','ascii','string','le','lt'}
DEFT = re.compile(r'^\s*(?:#\[[^\]]*\]\s*)?(?:Inductive|Definition|Record|Variant)\s+([A-Za-z_][\w\']*)')
DEFF = re.compile(r'^\s*(?:Definition|Fixpoint)\s+([A-Za-z_][\w\']*)')

def is_std_path(fp):
    return bool(re.search(r'/lib/coq|/theories/coq|stdlib|/Coq/', fp or ''))

def main():
    type_def = {}   # name -> [def, is_stdlib]
    func_def = {}
    # 1) sentences.db (12 프로젝트)
    c = sqlite3.connect(DB)
    for text, fp, st in c.execute(
            "SELECT text, file_path, sentence_type FROM sentence "
            "WHERE sentence_type IN ('TermType.INDUCTIVE','TermType.DEFINITION','TermType.FIXPOINT')"):
        tt = re.sub(r'\s+', ' ', text.strip())
        std = is_std_path(fp)
        mt = DEFT.match(text.strip())
        if mt:
            nm = mt.group(1).split('.')[-1]
            if nm not in type_def:
                type_def[nm] = [tt, std or nm in STDLIB_NAMES]
        mf = DEFF.match(text.strip())
        if mf:
            nm = mf.group(1).split('.')[-1]
            if nm not in func_def:
                func_def[nm] = [tt, std or nm in STDLIB_NAMES]
    # 2) 모든 repos .v (전이: compcert만 아니라 전체)
    for vf in glob.glob('raw-data/coqstoq-test/repos/**/*.v', recursive=True):
        try:
            txt = open(vf, errors='ignore').read()
        except Exception:
            continue
        for stmt in re.split(r'\.\s*\n', txt):
            s2 = re.sub(r'\s+', ' ', stmt.strip()[:250])
            mt = DEFT.match(stmt.strip())
            if mt:
                nm = mt.group(1).split('.')[-1]
                type_def.setdefault(nm, [s2, nm in STDLIB_NAMES])
            mf = DEFF.match(stmt.strip())
            if mf:
                nm = mf.group(1).split('.')[-1]
                func_def.setdefault(nm, [s2, nm in STDLIB_NAMES])

    json.dump(type_def, open('data/type_defs.json', 'w'), ensure_ascii=False)
    json.dump(func_def, open('data/func_defs.json', 'w'), ensure_ascii=False)
    nstd_t = sum(1 for v in type_def.values() if v[1])
    print(f"type_defs: {len(type_def)} (stdlib {nstd_t}, domain {len(type_def)-nstd_t}) → data/type_defs.json")
    print(f"func_defs: {len(func_def)} → data/func_defs.json")

if __name__ == "__main__":
    main()
