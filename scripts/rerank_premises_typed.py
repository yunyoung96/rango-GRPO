#!/usr/bin/env python3
"""타입-지향 premise 재랭킹 (CPU-only). lemma 결론이 goal 결론과 얼마나 맞나로 재점수.
BM25(어휘유사)가 아니라 '결론 head 일치 + 공유 식별자'로 apply 대상 lemma를 위로.
사용: import score_premise; 또는 단독 실행 시 goldsft_bs2로 BM25 vs 재랭킹 비교."""
import json, re, sys, statistics

LN = re.compile(r'(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint)\s+([A-Za-z_][\w\'\.]*)\s*:?\s*(.*)', re.S)

def goal_concl(goal):
    parts = goal.split('\n\n', 1)
    return parts[1] if len(parts) > 1 else goal

def concl_of_premise(ptext):
    m = LN.match(ptext.strip())
    body = m.group(2) if m else ptext
    depth = 0; last = -1; i = 0
    while i < len(body) - 1:
        ch = body[i]
        if ch == '(': depth += 1
        elif ch == ')': depth -= 1
        elif depth == 0 and body[i:i+2] == '->': last = i
        i += 1
    return body[last+2:] if last >= 0 else body

def _heads(txt): return set(re.findall(r"[A-Za-z_][\w'\.]*", txt))
def _chead(txt):
    m = re.match(r"\(?\s*([A-Za-z_][\w'\.]*)", txt.strip())
    return m.group(1).split('.')[-1] if m else None

def score_premise(goal_c, prem):
    """goal 결론 goal_c 에 대한 premise(lemma statement) 점수. 높을수록 apply 후보로 적합."""
    pc = concl_of_premise(prem)
    gh, ph = _chead(goal_c), _chead(pc)
    s = 0.0
    if gh and ph and gh == ph: s += 3.0          # 결론 head 일치(강 신호)
    s += len(_heads(goal_c) & _heads(pc)) * 0.3  # 공유 식별자
    if '=' in goal_c and '=' in pc: s += 0.5      # 둘 다 등식
    return s

def rerank(goal, premises):
    gc = goal_concl(goal)
    return sorted(range(len(premises)), key=lambda i: -score_premise(gc, premises[i]))

def prem_name(p):
    m = LN.match(p.strip()); return m.group(1).split('.')[-1] if m else None

if __name__ == "__main__":
    APP = re.compile(r'^(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*([A-Za-z_][\w\']*)')
    LOCAL = re.compile(r'H\w*|IH\w*')
    f = sys.argv[1] if len(sys.argv) > 1 else 'data/grpo_rollouts/goldsft_bs2.jsonl'
    n = b1 = b5 = r1 = r5 = 0; br = []; rr = []
    for line in open(f):
        g = json.loads(line)
        for a in g['attempts']:
            for s in a['steps']:
                tac = (s.get('tactic') or '').strip().lstrip('\n')
                m = APP.match(tac)
                if not m: continue
                L = m.group(1).split('.')[-1]
                if LOCAL.fullmatch(L): continue
                prem = (s.get('example', {}) or {}).get('premises') or []
                names = [prem_name(p) for p in prem]
                if L not in names: continue
                n += 1
                goal = (s.get('example', {}) or {}).get('proof_state', '')
                brank = names.index(L) + 1
                order = rerank(goal, prem)
                rrank = [names[i] for i in order].index(L) + 1
                br.append(brank); rr.append(rrank)
                b1 += brank <= 1; b5 += brank <= 5; r1 += rrank <= 1; r5 += rrank <= 5
    def p(x): return f"{100*x/max(n,1):.0f}%"
    print(f"retrieve된 gold apply lemma: {n}")
    print(f"  top-1  BM25 {p(b1)}  →  재랭킹 {p(r1)}")
    print(f"  top-5  BM25 {p(b5)}  →  재랭킹 {p(r5)}")
    print(f"  중앙랭크 BM25 {statistics.median(br):.0f} → 재랭킹 {statistics.median(rr):.0f}")
