#!/usr/bin/env python3
"""AU(anti-unification / lgg) 기반 premise 랭킹 — 독립 구현(고전 Plotkin/Reynolds lgg).
목적: 결론 AST의 '최소일반화에 살아남는 공유 골격 크기'로 premise를 랭킹, BM25/텍스트재랭킹과 비교.
※ 타인 미공개 논문(ctxau)과 무관하게, 표준 anti-unification을 이 랭킹 문제에 최소로 구현.
CPU-only.
"""
import json, re, sys, statistics

# ── 경량 파서: 연산자 우선순위 → (label, [children]) 트리 ──
_TOK = re.compile(r"<->|->|/\\|\\/|<=|>=|<>|::|[A-Za-z_][A-Za-z0-9_']*|\d+|[()=<>+\-*/,.@]")
_PREC = [["<->"], ["->"], ["\\/"], ["/\\"], ["=", "<>", "<", ">", "<=", ">="], ["+", "-"], ["*", "/"]]
_BINDERS = {"forall", "exists", "fun"}

def _toks(s):
    m = re.search(r"(?:Lemma|Theorem|Corollary|Remark|Fact|Definition|Fixpoint)\b[^:]*:(.*)", s, re.DOTALL)
    if m: s = m.group(1)
    s = s.split(":=")[0]
    s = re.sub(r"\.\s*$", "", s.strip())
    return _TOK.findall(s)

class _P:
    def __init__(self, toks): self.t = toks; self.i = 0
    def peek(self): return self.t[self.i] if self.i < len(self.t) else None
    def eat(self): x = self.peek(); self.i += 1; return x
    def parse(self):
        try: return self.expr(0)
        except Exception: return ("?", [])
    def expr(self, lvl):
        if lvl >= len(_PREC): return self.app()
        left = self.expr(lvl + 1)
        while self.peek() in _PREC[lvl]:
            op = self.eat(); right = self.expr(lvl + 1); left = (op, [left, right])
        return left
    def app(self):
        f = self.atom()
        while self.peek() and self.peek() not in sum(_PREC, []) + [")", ",", None]:
            f = ("app", [f, self.atom()])
        return f
    def atom(self):
        tk = self.peek()
        if tk in _BINDERS:
            self.eat()
            bvs = []
            while self.peek() and self.peek() != ",":
                if self.peek() == ":":  # 타입주석 스킵
                    self.eat()
                    while self.peek() and self.peek() not in (",",): self.eat()
                    break
                bvs.append(self.eat())
            if self.peek() == ",": self.eat()
            body = self.expr(0)
            return ("binder", [("bvs", [(b, []) for b in bvs[:6]]), body])
        if tk == "(":
            self.eat(); e = self.expr(0)
            if self.peek() == ")": self.eat()
            return e
        return (self.eat() or "?", [])

def parse(s): return _P(_toks(s)).parse()

def tree_size(t):
    n = 0; stack = [t]
    while stack:
        lbl, ch = stack.pop(); n += 1; stack.extend(ch)
    return n

# ── lgg: 두 트리의 공유 골격 노드 수(위치정렬, 일관 변수 재명명) ──
def lgg_size(a, b, mapAB=None, mapBA=None):
    """a,b가 같은 위치에서 얼마나 일치하나(anti-unifier에 살아남는 노드 수).
    변수(자식없는 소문자 식별자)는 일관 재명명 허용."""
    if mapAB is None: mapAB, mapBA = {}, {}
    la, ca = a; lb, cb = b
    a_var = not ca and re.fullmatch(r"[a-z_][\w']*", la or "")
    b_var = not cb and re.fullmatch(r"[a-z_][\w']*", lb or "")
    if a_var and b_var:
        # 일관 재명명 하에 매칭되면 1(공유 변수 슬롯)
        if mapAB.get(la, lb) == lb and mapBA.get(lb, la) == la:
            mapAB[la] = lb; mapBA[lb] = la; return 1
        return 0
    if la != lb or len(ca) != len(cb):
        return 0   # head 불일치 → 이 위치서 일반화(변수로 대체), 하위 골격 소멸
    n = 1
    for x, y in zip(ca, cb):
        n += lgg_size(x, y, mapAB, mapBA)
    return n

def au_sim(sa, sb):
    ta, tb = parse(sa), parse(sb)
    l = lgg_size(ta, tb)
    denom = max(tree_size(ta), tree_size(tb), 1)
    return l / denom

# ── premise 랭킹 측정 ──
def goal_concl(goal):
    p = goal.split('\n\n', 1); return p[1] if len(p) > 1 else goal
LN = re.compile(r'(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint)\s+([A-Za-z_][\w\'\.]*)')
def prem_name(p):
    m = LN.match(p.strip()); return m.group(1).split('.')[-1] if m else None
def prem_concl(p):
    body = p.split(':', 1)[1] if ':' in p else p
    depth = 0; last = -1; i = 0
    while i < len(body) - 1:
        c = body[i]
        if c == '(': depth += 1
        elif c == ')': depth -= 1
        elif depth == 0 and body[i:i+2] == '->': last = i
        i += 1
    return body[last+2:] if last >= 0 else body

if __name__ == "__main__":
    APP = re.compile(r'^(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*([A-Za-z_][\w\']*)')
    LOCAL = re.compile(r'H\w*|IH\w*')
    f = sys.argv[1] if len(sys.argv) > 1 else 'data/grpo_rollouts/goldsft_bs2.jsonl'
    n = b1 = b5 = a1 = a5 = 0; br = []; ar = []
    for line in open(f):
        g = json.loads(line)
        for att in g['attempts']:
            for s in att['steps']:
                tac = (s.get('tactic') or '').strip().lstrip('\n')
                m = APP.match(tac)
                if not m: continue
                L = m.group(1).split('.')[-1]
                if LOCAL.fullmatch(L): continue
                prem = (s.get('example', {}) or {}).get('premises') or []
                names = [prem_name(p) for p in prem]
                if L not in names: continue
                n += 1
                gc = goal_concl((s.get('example', {}) or {}).get('proof_state', ''))
                brank = names.index(L) + 1
                scores = [au_sim(gc, prem_concl(p)) for p in prem]
                order = sorted(range(len(prem)), key=lambda i: -scores[i])
                arank = [names[i] for i in order].index(L) + 1
                br.append(brank); ar.append(arank)
                b1 += brank <= 1; b5 += brank <= 5; a1 += arank <= 1; a5 += arank <= 5
    def p(x): return f"{100*x/max(n,1):.0f}%"
    print(f"AU(lgg) premise 랭킹 — retrieve된 gold apply {n}개")
    print(f"  top-1  BM25 {p(b1)}  →  AU {p(a1)}")
    print(f"  top-5  BM25 {p(b5)}  →  AU {p(a5)}")
    print(f"  중앙랭크 BM25 {statistics.median(br):.0f} → AU {statistics.median(ar):.0f}")
