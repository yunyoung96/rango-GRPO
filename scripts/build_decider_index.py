#!/usr/bin/env python3
"""DDR decider 인덱스 오프라인 구축 (CPU-only, GPU 불필요).
코퍼스(coqstoq sentences.db)에서 decider/spec lemma를 스캔해 '결정 대상(타입/술어/연산) → decider' 맵 생성.

세 계열:
  A. 타입 등호/순서 decider: 이름 *_dec/eq_dec + sumbool({_}+{_}) 반환 → 결정하는 '타입'으로 색인.
  B. 술어 decider: {P args}+{~P args} 형태 → 술어 head P 로 색인.
  C. 연산 spec: *_spec (reflection) → spec 대상 연산 head 로 색인.
출력: data/ddr_index.json  {"type_eq": {T: [dec...]}, "pred_dec": {P: [dec...]}, "op_spec": {op: [spec...]}, "all_dec": [...]}
"""
import sqlite3, re, json, sys, os
from collections import defaultdict

DB = sys.argv[1] if len(sys.argv) > 1 else "raw-data/coqstoq-test/coqstoq-test-sentences.db"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/ddr_index.json"

DEFN = re.compile(r'^\s*(?:Lemma|Theorem|Definition|Fixpoint|Corollary|Remark|Fact|Instance|Program\s+Definition|Global\s+Instance|Local\s+Definition)\s+([A-Za-z_][\w\'\.]*)')
# sumbool 반환: {..}+{..}
SUMBOOL = re.compile(r'\{[^{}]*\}\s*\+\s*\{')
# {P args}+{~P args} 에서 P head 추출
PREDDEC = re.compile(r'\{\s*(?:~\s*)?([A-Za-z_][\w\'\.]*)')
# _spec: 이름에서 base 연산 = *_spec 제거
IDENT = re.compile(r"[A-Za-z_][\w'\.]*")

def main():
    c = sqlite3.connect(DB)
    rows = c.execute("SELECT text, sentence_type FROM sentence").fetchall()
    type_eq = defaultdict(set)   # 타입 → eq/ord decider
    pred_dec = defaultdict(set)  # 술어 head → decider
    op_spec = defaultdict(set)   # 연산 head → spec
    all_dec = set()
    n_scan = 0
    for text, styp in rows:
        m = DEFN.match(text)
        if not m:
            continue
        name = m.group(1)
        short = name.split('.')[-1]
        n_scan += 1
        has_sb = bool(SUMBOOL.search(text))
        # C. *_spec (reflection): op = 이름에서 _spec 뗀 것
        if short.endswith('_spec'):
            op = short[:-5]
            if op:
                op_spec[op].add(name); all_dec.add(name)
        # A/B. decider: 이름 *_dec/eq_dec 또는 sumbool 반환
        is_dec = bool(re.search(r'(_dec|eq_dec|_dec\b)$', short)) or has_sb
        if is_dec:
            all_dec.add(name)
            # A. 타입 등호: eq_dec/_eq_dec 계열 → 결정 타입 추정
            #   보통 "forall x y : T, {x=y}+{x<>y}" → T 추출
            mt = re.search(r':\s*([A-Za-z_][\w\'\.]*)\s*,\s*\{', text)  # forall .. : T, {..
            if re.search(r'eq_dec$|_dec$', short) and ('=' in text):
                if mt:
                    type_eq[mt.group(1).split('.')[-1]].add(name)
                # 이름 기반 타입 힌트: T_eq_dec / T.eq_dec
                base = re.sub(r'(_?eq)?_dec$', '', short)
                if base:
                    type_eq[base].add(name)
            # B. 술어 decider: {P args}+{~P args} → P head
            if has_sb:
                # sumbool 첫 브레이스의 head
                mm = PREDDEC.search(text[text.find('{'):])
                if mm:
                    head = mm.group(1).split('.')[-1]
                    if head and head != 'eq':
                        pred_dec[head].add(name)
                # 이름 기반: *_dec 뗀 술어
                base = re.sub(r'_dec$', '', short)
                if base and base != short:
                    pred_dec[base].add(name)
    idx = {
        "type_eq": {k: sorted(v) for k, v in type_eq.items()},
        "pred_dec": {k: sorted(v) for k, v in pred_dec.items()},
        "op_spec": {k: sorted(v) for k, v in op_spec.items()},
        "all_dec": sorted(all_dec),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(idx, open(OUT, "w"), ensure_ascii=False, indent=0)
    print(f"스캔 def/lemma: {n_scan}")
    print(f"인덱스: type_eq {len(type_eq)}타입 / pred_dec {len(pred_dec)}술어 / op_spec {len(op_spec)}연산 / all_dec {len(all_dec)}")
    print(f"예 type_eq: {list(type_eq)[:12]}")
    print(f"예 pred_dec: {list(pred_dec)[:12]}")
    print(f"예 op_spec: {list(op_spec)[:12]}")
    print(f"저장: {OUT}")

if __name__ == "__main__":
    main()
