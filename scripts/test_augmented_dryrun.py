#!/usr/bin/env python3
"""augmented 프롬프트 CPU dry-run. selective [TYPES]+[DECIDERS]+[SIGNATURES]+재랭킹을
실제 CompCert gold state에 적용 → (1) 에러율 (2) 실제 토큰크기 분포 (3) 필요타입 커버.
GPU 불필요."""
import os, json, re, sys, statistics
os.environ['HF_HUB_OFFLINE'] = '1'
sys.path.insert(0, 'src')
from transformers import AutoTokenizer

TOK = AutoTokenizer.from_pretrained('deepseek-ai/deepseek-coder-1.3b-instruct')
def ntok(s): return len(TOK(s or "", add_special_tokens=False)['input_ids'])

IND = json.load(open('data/ind_constructors.json'))
DDR = json.load(open('data/ddr_index.json'))
TYPE_EQ, PRED_DEC, OP_SPEC = DDR['type_eq'], DDR['pred_dec'], DDR['op_spec']

# ── selective [TYPES]: destruct 후보 타입만, 소수생성자 우선, 예산캡 ──
MAX_TYPES = 6
MAX_CTORS = 8
TYPE_BUDGET_TOK = 200

def hyp_types(goal):
    """가설 x : T 에서 (변수, 타입head) 목록."""
    hs = goal.split('\n\n', 1)[0]
    out = []
    for ln in hs.split('\n'):
        m = re.match(r"^\s*([\w', ]+?)\s*:\s*(.+)$", ln)
        if not m: continue
        typ = m.group(2).strip()
        head = typ.split()[0].split('.')[-1] if typ.split() else typ
        for nm in re.split(r"[,\s]+", m.group(1).strip()):
            if nm: out.append((nm, head, typ))
    return out

def selective_types(goal):
    """inductive-타입 변수(가설·결론 무관) 전부 후보, 소수생성자, 결론등장 우선, 예산캡.
    selective는 '결론만'이 아니라 '모든 destruct 후보 변수의 타입'을 포함하되 랭킹+캡으로 작게 유지."""
    concl = goal.split('\n\n', 1)[1] if '\n\n' in goal else goal
    concl_ids = set(re.findall(r"[A-Za-z_][\w']*", concl))
    cands = []
    seen = set()
    for nm, head, typ in hyp_types(goal):
        if head in seen: continue
        if head in IND and len(IND[head]) <= MAX_CTORS:   # 결론등장 요구 제거(가설 destruct도 포함)
            seen.add(head)
            score = (2 if nm in concl_ids else 1) - 0.05 * len(IND[head])  # 결론등장 우선, 가설도 포함
            cands.append((score, head))
    cands.sort(key=lambda x: -x[0])
    lines = []; tot = 0
    for _, head in cands[:MAX_TYPES]:
        line = f"{head} := {' | '.join(IND[head])}"
        t = ntok(line)
        if tot + t > TYPE_BUDGET_TOK: break
        lines.append(line); tot += t
    return "\n".join(lines)

def naive_types(goal):
    ids = set(re.findall(r"[A-Za-z_][\w']*", goal))
    lines = [f"{t} := {' | '.join(IND[t])}" for t in ids if t in IND]
    return "\n".join(lines)

def deciders(goal):
    ids = set(re.findall(r"[A-Za-z_][\w']*", goal))
    out = []
    for h in ids:
        ds = OP_SPEC.get(h, []) + PRED_DEC.get(h, []) + TYPE_EQ.get(h, [])
        for d in ds[:1]:
            out.append(f"{h}: {d}")
    return "\n".join(out[:6])

# ── dry-run ──
SIMPLE = re.compile(r'^destruct\s+([A-Za-z_][\w\']*)\s*(?:as\b.*)?\.?\s*$')
def main():
    files = sys.argv[1:] or ['data/grpo_rollouts/goldsft_bs2.jsonl']
    n = err = 0
    base_toks, sel_toks, naive_toks, aug_total = [], [], [], []
    over_budget_base = over_budget_aug = 0
    need_cov_hit = need_cov_tot = 0
    BUDGET = 4096
    for f in files:
        for line in open(f):
            try:
                g = json.loads(line)
            except Exception:
                continue
            for a in g.get('attempts', []):
                for s in a.get('steps', []):
                    e = s.get('example', {}) or {}
                    goal = e.get('proof_state', '')
                    if not goal: continue
                    n += 1
                    try:
                        # 현재 프롬프트 근사(state+script+premise+proof)
                        base = ntok(goal) + ntok(e.get('proof_script', '') or '') \
                             + sum(ntok(p) for p in (e.get('premises') or [])[:20]) \
                             + sum(ntok(p) for p in (e.get('proofs') or [])[:4])
                        st = selective_types(goal); nv = naive_types(goal); dc = deciders(goal)
                        aug = base + ntok(st) + ntok(dc)
                        base_toks.append(base); aug_total.append(aug)
                        sel_toks.append(ntok(st)); naive_toks.append(ntok(nv))
                        if base > BUDGET: over_budget_base += 1
                        if aug > BUDGET: over_budget_aug += 1
                        # 필요타입 커버: gold가 destruct v 하면 v의 타입이 selective에 들었나
                        tac = (s.get('tactic') or '').strip().lstrip('\n')
                        m = SIMPLE.match(tac)
                        if m:
                            v = m.group(1)
                            tm = re.search(rf'^\s*{re.escape(v)}\s*:\s*([A-Za-z_][\w\'\.]*)', goal, re.M)
                            if tm and tm.group(1).split('.')[-1] in IND:
                                need_cov_tot += 1
                                if tm.group(1).split('.')[-1] in st: need_cov_hit += 1
                    except Exception as ex:
                        err += 1
                        if err <= 5: print(f"  ERROR: {type(ex).__name__}: {str(ex)[:80]}")
    def q(xs, p): return statistics.quantiles(xs, n=100)[p-1] if len(xs) > 2 else max(xs or [0])
    print(f"=== augmented dry-run (CPU, 실제 토크나이저) ===")
    print(f"처리 state: {n} | 에러: {err} ({100*err/max(n,1):.1f}%)")
    print(f"\n[프롬프트 토큰 (budget {BUDGET})]")
    print(f"  현재(base 근사): 중앙 {statistics.median(base_toks):.0f} | p95 {q(base_toks,95):.0f} | 최대 {max(base_toks):.0f} | 초과 {over_budget_base}({100*over_budget_base/n:.1f}%)")
    print(f"  augmented:       중앙 {statistics.median(aug_total):.0f} | p95 {q(aug_total,95):.0f} | 최대 {max(aug_total):.0f} | 초과 {over_budget_aug}({100*over_budget_aug/n:.1f}%)")
    print(f"  → augmented가 base보다 초과 추가: {over_budget_aug-over_budget_base}개")
    print(f"\n[타입주입 토큰: selective vs naive]")
    print(f"  selective: 중앙 {statistics.median(sel_toks):.0f} 평균 {statistics.mean(sel_toks):.0f} 최대 {max(sel_toks):.0f}")
    print(f"  naive:     중앙 {statistics.median(naive_toks):.0f} 평균 {statistics.mean(naive_toks):.0f} 최대 {max(naive_toks):.0f}")
    print(f"  → selective가 naive 대비 평균 {100*(1-statistics.mean(sel_toks)/max(statistics.mean(naive_toks),1)):.0f}% 절감")
    print(f"\n[필요타입 커버 (성능저하 방지 — gold destruct 타입이 selective에 드나)]")
    print(f"  {need_cov_hit}/{need_cov_tot} = {100*need_cov_hit/max(need_cov_tot,1):.0f}%")
    print(f"  (selective가 필요타입을 빠뜨리면 신호 손실 → 이 값 높아야 안전)")

if __name__ == "__main__":
    main()
