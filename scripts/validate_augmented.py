#!/usr/bin/env python3
"""augmented 종합 검증 (CPU). 다양한 데이터셋 × 다수 차원 → PASS/FAIL.
학습 전 '문제 없는지' 엄격 검증. GPU 불필요."""
import os, json, re, sys, statistics, random
os.environ['HF_HUB_OFFLINE'] = '1'
sys.path.insert(0, 'src')
from tactic_gen.tactic_data import (rerank_premises, _rr_score, _rr_goal_concl,
                                    ProofPremiseCollator)
from tactic_gen.lm_example import LmExample
from transformers import AutoTokenizer

TOK = AutoTokenizer.from_pretrained('deepseek-ai/deepseek-coder-1.3b-instruct')
def ntok(s): return len(TOK(s or "", add_special_tokens=False)['input_ids'])
COL = ProofPremiseCollator(512, 1024, 1024, 512, 128, False)
IND = json.load(open('data/ind_constructors_clean.json'))
DDR = json.load(open('data/ddr_index.json'))
KW = {'forall','exists','fun','match','if','then','else','let','in','with','end','Type','Prop','Set','return','as','is','and','or'}

LN = re.compile(r'(?:Lemma|Theorem|Definition|Corollary|Remark|Fact|Fixpoint)\s+([A-Za-z_][\w\'\.]*)')
def pname(p):
    m = LN.match((p or '').strip()); return m.group(1).split('.')[-1] if m else None
APP = re.compile(r'^(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*([A-Za-z_][\w\']*)')
SIMPLE = re.compile(r'^destruct\s+([A-Za-z_][\w\']*)\s*(?:as\b.*)?\.?\s*$')
LOCAL = re.compile(r'H\w*|IH\w*')

def hyp_types(goal):
    hs = goal.split('\n\n', 1)[0]; out = []
    for ln in hs.split('\n'):
        m = re.match(r"^\s*([\w', ]+?)\s*:\s*(.+)$", ln)
        if not m: continue
        typ = m.group(2).strip(); head = typ.split()[0].split('.')[-1] if typ.split() else typ
        for nm in re.split(r"[,\s]+", m.group(1).strip()):
            if nm: out.append((nm, head))
    return out

def selective_types(goal):
    cands, seen = [], set()
    concl_ids = set(re.findall(r"[A-Za-z_][\w']*", goal.split('\n\n',1)[1] if '\n\n' in goal else goal))
    for nm, head in hyp_types(goal):
        if head in seen or head in KW or len(head) < 2: continue
        if head in IND and len(IND[head]) <= 8:
            seen.add(head); cands.append(((2 if nm in concl_ids else 1) - 0.05*len(IND[head]), head))
    cands.sort(key=lambda x: -x[0])
    lines, tot = [], 0
    for _, head in cands[:6]:
        line = f"{head} := {' | '.join(IND[head])}"; t = ntok(line)
        if tot + t > 200: break
        lines.append((head, line)); tot += t
    return lines

def iter_steps(path, limit=4000):
    rng = random.Random(42); n = 0
    for line in open(path):
        try: g = json.loads(line)
        except: continue
        for a in g.get('attempts', []):
            for s in a.get('steps', []):
                e = s.get('example', {}) or {}
                if not e.get('proof_state'): continue
                yield s, e
                n += 1
                if n >= limit: return

DATASETS = ['goldsft_bs2', 'tst1000tr5091_gold', 'once_v2_pipe', 'rango-grpo-cascade-s0',
            'bigscale2', 'rango-grpo-subgoal-bs2-s0', 'opener_once_pipe2']

results = {}   # dim -> list of (dataset, pass, detail)
def rec(dim, ds, ok, detail): results.setdefault(dim, []).append((ds, ok, detail))

for ds in DATASETS:
    path = f'data/grpo_rollouts/{ds}.jsonl'
    if not os.path.exists(path): continue
    # 누적 카운터
    perm_ok = det_ok = True
    b1 = r1 = b5 = r5 = napp = 0
    need_hit = need_tot = 0
    garbage_types = garbage_dec = 0
    over_base = over_aug = nstate = 0
    crashes = 0
    leak = 0
    seltypes_a, seltypes_b = {}, {}   # 결정성: 같은 goal 2회 호출
    for s, e in iter_steps(path):
        goal = e['proof_state']; prem = e.get('premises') or []
        try:
            ex = LmExample.from_json(e)
            # A. rerank permutation (집합 보존)
            rr = rerank_premises(ex)
            if prem and (sorted(rr) != sorted(prem) or len(rr) != len(prem)):
                perm_ok = False
            # B. determinism
            if rerank_premises(ex) != rr: det_ok = False
            # C. rerank aggregate (apply만)
            tac = (s.get('tactic') or '').strip().lstrip('\n')
            m = APP.match(tac)
            if m and prem:
                L = m.group(1).split('.')[-1]
                if not LOCAL.fullmatch(L):
                    names = [pname(p) for p in prem]
                    if L in names:
                        napp += 1
                        gc = _rr_goal_concl(goal)
                        br = names.index(L)+1
                        order = sorted(range(len(prem)), key=lambda i: -_rr_score(gc, prem[i]))
                        rk = [names[i] for i in order].index(L)+1
                        b1 += br <= 1; r1 += rk <= 1; b5 += br <= 5; r5 += rk <= 5
            # D+F. [TYPES] coverage + garbage
            sel = selective_types(goal)
            for head, line in sel:
                if not IND.get(head) or head in KW:
                    garbage_types += 1
                if head + ' :=' not in line or line.endswith(':= '):
                    garbage_types += 1
            md = SIMPLE.match(tac)
            if md:
                v = md.group(1)
                tm = re.search(rf'^\s*{re.escape(v)}\s*:\s*([A-Za-z_][\w\'\.]*)', goal, re.M)
                if tm and tm.group(1).split('.')[-1] in IND:
                    need_tot += 1
                    if tm.group(1).split('.')[-1] in [h for h,_ in sel]: need_hit += 1
            # H. prompt size
            base = ntok(goal) + ntok(e.get('proof_script','') or '') + sum(ntok(p) for p in prem[:20]) + sum(ntok(p) for p in (e.get('proofs') or [])[:4])
            aug = base + sum(ntok(l) for _,l in sel)
            nstate += 1
            if base > 4096: over_base += 1
            if aug > 4096: over_aug += 1
            # J. leakage: [TYPES]가 정리 이름/문장 주입? (타입정의만이어야)
            thm_name = (e.get('proof_script','') or '').split('\n')[0]
            for _, line in sel:
                # 타입정의 line이 goal 결론 전체를 담으면 누수 의심(정상은 'T := c1|c2')
                if len(line) > 300: leak += 1
        except Exception as ex_:
            crashes += 1
    # 판정
    rec('A. rerank=순열(집합보존)', ds, perm_ok, 'OK' if perm_ok else 'FAIL')
    rec('B. rerank 결정성', ds, det_ok, 'OK' if det_ok else 'FAIL')
    if napp:
        rec('C. rerank top-1 개선(≥BM25)', ds, r1 >= b1, f'BM25 {100*b1/napp:.0f}%→rr {100*r1/napp:.0f}% (n={napp})')
        rec('C2. rerank top-5 개선(≥BM25)', ds, r5 >= b5, f'BM25 {100*b5/napp:.0f}%→rr {100*r5/napp:.0f}%')
    rec('E. [TYPES] 노이즈 0', ds, garbage_types == 0, f'garbage={garbage_types}')
    if need_tot:
        cov = 100*need_hit/need_tot
        rec('F. 필요타입 커버≥90%', ds, cov >= 90, f'{need_hit}/{need_tot}={cov:.0f}%')
    rec('H. 프롬프트 budget초과 augΔ≤2pp', ds, (over_aug-over_base) <= 0.02*max(nstate,1), f'base {100*over_base/max(nstate,1):.1f}%→aug {100*over_aug/max(nstate,1):.1f}%')
    rec('I. 크래시 0', ds, crashes == 0, f'crashes={crashes}')
    rec('J. [TYPES] 누수의심 0', ds, leak == 0, f'leak={leak}')

# 출력
print("="*90)
print("augmented 종합 검증 (7 데이터셋 × 다차원)")
print("="*90)
allpass = True
for dim in sorted(results):
    rows = results[dim]
    npass = sum(1 for _,ok,_ in rows if ok)
    status = "✅" if npass == len(rows) else "❌"
    if npass != len(rows): allpass = False
    print(f"{status} {dim}: {npass}/{len(rows)} 데이터셋 통과")
    for ds, ok, detail in rows:
        mark = "  ✓" if ok else "  ✗★"
        print(f"{mark} {ds:<28} {detail}")
print("="*90)
print(f"{'✅ 전체 통과' if allpass else '❌ 실패 항목 있음(★ 확인)'}")
