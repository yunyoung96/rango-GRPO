#!/usr/bin/env python3
"""compound decider 커버 개선 방법 누적 측정 (CPU).
baseline → +notation → +순서 → +CompCert소스인덱스 → +조회수정 → +Mode1 union.
각 단계가 얼마나 올리나. GPU 불필요."""
import json, re, sqlite3, glob, sys
from collections import defaultdict

DDR = json.load(open('data/ddr_index.json'))
OS0, PD0, TE0 = DDR['op_spec'], DDR['pred_dec'], DDR['type_eq']
ALLDEC = set(DDR.get('all_dec', []))
KW = {'forall','exists','fun','match','if','then','else','let','in','with','end','Type','Prop','Set','return','as','is','and','or'}
ORDER = {'Rle_or_lt','Rlt_le_dec','Zle_or_lt','zlt','zle','zeq','peq','eq_block','ident_eq','le_lt_dec'}

# notation-map (B)
_c = sqlite3.connect('raw-data/coqstoq-test/coqstoq-test-sentences.db')
_NOTA = re.compile(r'Notation\s+"([^"]+)"\s*:=\s*\(?\s*([A-Za-z_][\w\'\.]*)')
NMAP = {}
for (t,) in _c.execute("SELECT text FROM sentence WHERE text LIKE 'Notation %'"):
    mm = _NOTA.search(t)
    if not mm: continue
    for op in [tok for tok in re.findall(r'\S+', mm.group(1))
               if not re.fullmatch(r"[a-zA-Z_][\w']*", tok) and tok not in ('(',')','[',']','{','}',',',"'")
               and len(tok) <= 4 and re.search(r'[<>=?+\-*/^&|]', tok)]:
        NMAP.setdefault(op, set()).add(mm.group(2).split('.')[-1])
NMAP = {k: sorted(v)[:6] for k, v in NMAP.items()}

# CompCert 소스 인덱스 확장 (D): .v 파일서 decider/spec 스캔 (더 관대하게)
def build_cc_index():
    te, pd, os_, alld = defaultdict(set), defaultdict(set), defaultdict(set), set()
    DEFN = re.compile(r'(?:Definition|Lemma|Theorem|Fixpoint|Remark|Corollary|Fact|Program\s+Definition)\s+([A-Za-z_][\w\']*)')
    SUMBOOL = re.compile(r'\{[^{}]*\}\s*\+\s*\{')
    for vf in glob.glob('raw-data/coqstoq-test/repos/compcert/**/*.v', recursive=True):
        try: txt = open(vf, errors='ignore').read()
        except: continue
        for stmt in re.split(r'\.\s*(?:\n|$)', txt):
            m = DEFN.search(stmt[:200])
            if not m: continue
            short = m.group(1).split('.')[-1]
            has_sb = bool(SUMBOOL.search(stmt))
            if short.endswith('_spec'):
                os_[short[:-5]].add(short); alld.add(short)
            if re.search(r'(_dec|eq_dec|_eq)$', short) or has_sb:
                alld.add(short)
                base = re.sub(r'(_?eq)?_dec$|_eq$', '', short)
                if base: te[base].add(short); pd[base].add(short)
                if has_sb:
                    mm = re.search(r'\{\s*(?:~\s*)?([A-Za-z_][\w\'\.]*)', stmt[stmt.find('{'):]) if '{' in stmt else None
                    if mm: pd[mm.group(1).split('.')[-1]].add(short)
                # 순서/삼분(sumbool인데 _dec 아닌 이름): 자기이름으로도 등록
                if has_sb and short[0].islower():
                    os_[short].add(short)
    return te, pd, os_, alld

TE_CC, PD_CC, OS_CC, ALLDEC_CC = build_cc_index()

def merge(a, b):
    out = {k: list(v) for k, v in a.items()}
    for k, v in b.items():
        out.setdefault(k, []); out[k] = list(set(out[k]) | set(v))
    return out

def ops(txt, use_nota=True, use_order=True):
    o = set()
    for t in re.findall(r"[A-Za-z_][\w']*", txt or ""):
        if t in KW or len(t) < 2: continue
        if t[0].isupper() or len(t) >= 3: o.add(t)
    if use_nota:
        for sym, names in NMAP.items():
            if sym in (txt or ""): o.update(names)
    if use_order and any(x in txt for x in ['<', 'Rle', 'Rlt']):
        o |= ORDER
    return o

def make_dcands(te, pd, os_, use_nota, use_order, fix_base):
    def f(goal):
        cs = set()
        heads = ops(goal, use_nota, use_order)
        for h in heads:
            for d in os_.get(h, []) + pd.get(h, []) + te.get(h, []):
                cs.add(d.split('.')[-1])
        if use_order: cs |= ORDER
        # 조회수정(②): gold head의 base가 goal head에 있으면 인정 (base 매칭)
        return cs
    return f

COMPOUND = re.compile(r'^destruct\s+\(\s*(.+?)\s*\)\s*(?:as\b.*|eqn:.*)?\.?\s*$', re.S)
LOW = re.compile(r"[a-z]|[a-z]\d|v\d*|e\d*|H\w*|f|g")

def measure(dcands_fn, mode1=False, base_fix=False):
    def osp(s): return re.sub(r'\s+', ' ', (s or '').strip())
    n = hit = 0
    for ds in ['goldsft_bs2', 'tst1000tr5091_gold']:
        for line in open(f'data/grpo_rollouts/{ds}.jsonl'):
            try: g = json.loads(line)
            except: continue
            for a in g.get('attempts', []):
                for s in a.get('steps', []):
                    tac = (s.get('tactic') or '').strip().lstrip('\n')
                    m = COMPOUND.match(tac)
                    if not m: continue
                    E = re.split(r'\s+as\b|\s+eqn:', m.group(1))[0].strip()
                    head = E.split(None, 1)[0]
                    if LOW.fullmatch(head.split('.')[-1]): continue
                    goal = (s.get('example', {}) or {}).get('proof_state', '')
                    if not goal: continue
                    n += 1; hs = head.split('.')[-1]; ng = osp(goal)
                    ok = hs in dcands_fn(goal)
                    if not ok and base_fix:
                        base = re.sub(r'(_dec|eq_dec|_spec|_lt_dec|_le_dec)$', '', hs)
                        if base and re.search(r'\b' + re.escape(base) + r'\b', ng): ok = True
                    if not ok and mode1:
                        # Mode1: E(부분식)가 goal에 등장 → destruct 대상이 goal 안
                        argt = [t for t in re.split(r'[\s()]+', E) if t and not re.fullmatch(r'\d+', t)]
                        if osp(E) in ng or (re.search(r'\b' + re.escape(hs) + r'\b', ng) and
                            sum(1 for t in argt[1:] if re.search(r'\b' + re.escape(t.split('.')[-1]) + r'\b', ng)) >= max(1, (len(argt)-1)*0.6)):
                            ok = True
                    if ok: hit += 1
                    if n >= 1400: break
                if n >= 1400: break
    return hit, n

print("compound destruct 커버 — 개선 누적 (gold 데이터, n≈1400):")
base = make_dcands(TE0, PD0, OS0, False, False, False)
print(f"  ① baseline(인덱스만, notation×):        {measure(base)[0]}/{measure(base)[1]} = {100*measure(base)[0]/measure(base)[1]:.0f}%")
nb = make_dcands(TE0, PD0, OS0, True, False, False)
h, n = measure(nb); print(f"  ② +notation-map:                       {h}/{n} = {100*h/n:.0f}%")
no = make_dcands(TE0, PD0, OS0, True, True, False)
h, n = measure(no); print(f"  ③ +순서decider:                        {h}/{n} = {100*h/n:.0f}%")
TE, PD, OSm = merge(TE0, TE_CC), merge(PD0, PD_CC), merge(OS0, OS_CC)
cc = make_dcands(TE, PD, OSm, True, True, False)
h, n = measure(cc); print(f"  ④ +CompCert소스인덱스({len(ALLDEC_CC)}decider): {h}/{n} = {100*h/n:.0f}%")
h, n = measure(cc, base_fix=True)
print(f"  ⑤ +조회base수정:                       {h}/{n} = {100*h/n:.0f}%")
h, n = measure(cc, mode1=True, base_fix=True)
print(f"  ⑥ +Mode1(goal부분식) union:            {h}/{n} = {100*h/n:.0f}%  ★진짜 후보생성 상한")