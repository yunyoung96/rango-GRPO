#!/usr/bin/env python3
"""notation 해결 3방법 A/B/C 검증 (CPU). (1)터지나 (2)decider 커버 오르나.
A: notation-map 수동확장(흔한 연산). B: coqstoq Notation 자동추출. C: 국소전개(연산head만).
GPU 불필요."""
import os, json, re, sys, sqlite3, statistics
os.environ['HF_HUB_OFFLINE'] = '1'
sys.path.insert(0, 'src')
from transformers import AutoTokenizer

TOK = AutoTokenizer.from_pretrained('deepseek-ai/deepseek-coder-1.3b-instruct')
def ntok(s): return len(TOK(s or "", add_special_tokens=False)['input_ids'])
DDR = json.load(open('data/ddr_index.json'))
TYPE_EQ, PRED_DEC, OP_SPEC = DDR['type_eq'], DDR['pred_dec'], DDR['op_spec']
KW = {'forall','exists','fun','match','if','then','else','let','in','with','end','Type','Prop','Set','return','as','is','and','or'}

# ── A: 수동 확장 notation-map (흔한 Z/nat/pos/R/bool 연산) ──
NOTA_A = {
    '^': ['Zpower','pow','Rpower','expn'], '?=': ['compare','Pcompare','Zcompare','Ncompare'],
    '<?': ['ltb','Z.ltb','Nat.ltb'], '<=?': ['leb','Z.leb','Nat.leb'], '=?': ['eqb','Z.eqb','Nat.eqb','Pos.eqb'],
    '==': ['eqb','eq_op'], '+': ['add','Zplus','Nat.add','Pos.add'], '*': ['mul','Zmult','Nat.mul'],
    '-': ['sub','Zminus','Nat.sub'], '/': ['div','Zdiv'], 'mod': ['modulo','Zmod'],
    '<': ['lt','Zlt','Nat.lt'], '<=': ['le','Zle','Nat.le'], '>': ['gt'], '>=': ['ge'],
    '||': ['orb'], '&&': ['andb'], '::': ['cons'], '++': ['app','Zpower_nat'],
}

# ── B: coqstoq Notation 자동추출 (정제) ──
def build_nota_auto():
    c = sqlite3.connect('raw-data/coqstoq-test/coqstoq-test-sentences.db')
    NOTA = re.compile(r'Notation\s+"([^"]+)"\s*:=\s*\(?\s*([A-Za-z_][\w\'\.]*)')
    m = {}
    for (t,) in c.execute("SELECT text FROM sentence WHERE text LIKE 'Notation %'"):
        mm = NOTA.search(t)
        if not mm: continue
        sym, fn = mm.group(1), mm.group(2).split('.')[-1]
        # 심볼에서 진짜 연산기호만 (알파벳 placeholder·괄호·대괄호 제외)
        ops = [tok for tok in re.findall(r'\S+', sym)
               if not re.fullmatch(r"[a-zA-Z_][\w']*", tok)
               and tok not in ('(',')','[',']','{','}',',',"'")
               and len(tok) <= 4 and re.search(r'[<>=?+\-*/^&|]', tok)]
        for op in ops:
            m.setdefault(op, set()).add(fn)
    return {k: sorted(v)[:6] for k, v in m.items() if v}

def ops_with_nota(txt, nmap):
    """텍스트의 연산head + notation 확장."""
    o = set()
    for t in re.findall(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*", txt or ""):
        s = t.split('.')[-1]
        if s in KW or len(s) < 2: continue
        if t[0].isupper() or '.' in t or len(s) >= 3: o.add(s)
    for sym, names in nmap.items():
        if sym in (txt or ""): o.update(names)
    return o

# ── decider 커버 측정: gold compound destruct의 decider가 인덱스로 잡히나 ──
CD = re.compile(r'^destruct\s+\(\s*([A-Za-z_][\w\'\.]*)')
SIMPLE = re.compile(r"[a-z]|[a-z]\d|v\d*|e\d*|H\w*|f|g")
def decider_hit(goal, head, nmap):
    """goal의 연산/타입/술어 head(notation확장 포함)로 decider 인덱스 조회 → gold head 잡히나."""
    hs = head.split('.')[-1]
    heads = ops_with_nota(goal, nmap)
    cands = set()
    for h in heads:
        for d in OP_SPEC.get(h, []) + PRED_DEC.get(h, []) + TYPE_EQ.get(h, []):
            cands.add(d.split('.')[-1])
    return hs in cands

def measure_decider(nmap, label):
    n = hit = 0
    for line in open('data/grpo_rollouts/goldsft_bs2.jsonl'):
        g = json.loads(line)
        for a in g['attempts']:
            for s in a['steps']:
                tac = (s.get('tactic') or '').strip().lstrip('\n')
                m = CD.match(tac)
                if not m: continue
                head = m.group(1)
                if SIMPLE.fullmatch(head): continue
                goal = (s.get('example', {}) or {}).get('proof_state', '')
                if not goal: continue
                n += 1
                if decider_hit(goal, head, nmap): hit += 1
    print(f"  [{label}] decider 커버(Mode2): {hit}/{n} = {100*hit/max(n,1):.0f}%")
    return hit, n

# ── C: 국소전개 프롬프트 크기 (연산 head 주석만) ──
def method_C_size():
    """C = goal 옆에 등장 연산의 함수명 주석 몇 줄. Set Printing All(전체전개) 아님."""
    sizes = []
    for line in open('data/grpo_rollouts/goldsft_bs2.jsonl'):
        g = json.loads(line)
        for a in g['attempts']:
            for s in a['steps']:
                goal = (s.get('example', {}) or {}).get('proof_state', '')
                if not goal: continue
                # 국소전개 = goal의 notation 심볼 → 함수명 주석 (심볼당 1줄)
                syms = [sym for sym in NOTA_A if sym in goal]
                block = "\n".join(f"(* {sym} = {NOTA_A[sym][0]} *)" for sym in syms[:8])
                sizes.append(ntok(block))
                if len(sizes) >= 2000: return sizes
    return sizes

if __name__ == "__main__":
    print("=== (1) 프롬프트 터지나 ===")
    print("A(notation-map): +0토큰 (goal 안 건드림, 매칭계산만) → 안 터짐 [자명]")
    print("B(자동추출): +0토큰 (동일) → 안 터짐 [자명]")
    cs = method_C_size()
    print(f"C(국소전개 주석): 중앙 {statistics.median(cs):.0f} 평균 {statistics.mean(cs):.0f} 최대 {max(cs)} 토큰 (Set Printing All은 3~8배=터짐, C는 주석만)")
    print()
    print("=== (2) decider 커버(Mode2) 오르나 — gold compound destruct ===")
    measure_decider({}, "baseline(notation 없음)")
    measure_decider(NOTA_A, "A: 수동 notation-map(19심볼)")
    nb = build_nota_auto()
    print(f"  (B 자동추출: {len(nb)}심볼)")
    measure_decider(nb, "B: 자동추출 notation-map")
    merged = dict(nb);
    for k, v in NOTA_A.items(): merged.setdefault(k, []); merged[k] = sorted(set(list(merged[k]) + v))
    measure_decider(merged, "A+B 병합")
