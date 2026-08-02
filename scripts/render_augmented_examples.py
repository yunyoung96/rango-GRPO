#!/usr/bin/env python3
"""실제 ProofPremiseCollator로 augmented 프롬프트를 렌더 (CPU, 충실). 재랭킹 배선 검증 겸용.
train(goldsft_bs2)/test split에서 destruct·apply 예시 선별 → base vs augmented 프롬프트 + 토큰수."""
import os, json, re, sys
os.environ['HF_HUB_OFFLINE'] = '1'
sys.path.insert(0, 'src')
from transformers import AutoTokenizer
from tactic_gen.tactic_data import ProofPremiseCollator, rerank_premises
from tactic_gen.lm_example import LmExample

TOK = AutoTokenizer.from_pretrained('deepseek-ai/deepseek-coder-1.3b-instruct')
def ntok(s): return len(TOK(s or "", add_special_tokens=False)['input_ids'])
# 실제 conf 값 (training_conf.yaml proof-premise)
COL = ProofPremiseCollator(script_tokens=512, state_tokens=1024, proof_tokens=1024,
                           premise_tokens=512, out_tokens=128, whole_proof=False)
IND = json.load(open('data/ind_constructors_clean.json'))   # ★ 정제본(빈생성자·1글자 제거)
DDR = json.load(open('data/ddr_index.json'))
TYPE_EQ, PRED_DEC, OP_SPEC = DDR['type_eq'], DDR['pred_dec'], DDR['op_spec']
# ★ Coq 키워드/바운드변수 blocklist — [TYPES]/[DECIDERS] 노이즈 방지
KW = {'forall','exists','fun','match','if','then','else','let','in','with','end','Type',
      'Prop','Set','return','as','of','at','struct','fix','cofix','is','and','or'}
def _bad_head(h):
    return (h in KW) or len(h.split('.')[-1]) < 2   # 키워드거나 1글자 변수

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
    concl = goal.split('\n\n', 1)[1] if '\n\n' in goal else goal
    concl_ids = set(re.findall(r"[A-Za-z_][\w']*", concl))
    cands, seen = [], set()
    for nm, head in hyp_types(goal):
        if head in seen or _bad_head(head): continue
        if head in IND and len(IND[head]) <= 8:
            seen.add(head); cands.append(((2 if nm in concl_ids else 1) - 0.05*len(IND[head]), head))
    cands.sort(key=lambda x: -x[0])
    lines, tot = [], 0
    for _, head in cands[:6]:
        line = f"{head} := {' | '.join(IND[head])}"; t = ntok(line)
        if tot + t > 200: break
        lines.append(line); tot += t
    return "\n".join(lines)

def deciders(goal):
    # ★ 결론부의 연산/술어 head만(가설 변수명·키워드 제외). 노이즈 방지.
    concl = goal.split('\n\n', 1)[1] if '\n\n' in goal else goal
    ids = [i for i in set(re.findall(r"[A-Za-z_][\w'\.]*", concl)) if not _bad_head(i)]
    out = []
    for h in ids:
        hs = h.split('.')[-1]
        for d in (OP_SPEC.get(hs, []) + PRED_DEC.get(hs, []) + TYPE_EQ.get(hs, []))[:1]:
            if d.split('.')[-1] != hs:   # 자기자신 매칭 제외
                out.append(f"{h}: {d}")
    return "\n".join(sorted(set(out))[:5])

def find_gold_premise_pos(prompt, gold_lemma):
    """gold lemma가 [PREMISES] 블록 내 몇 번째 줄(위/아래)인지 — reverse 검증용."""
    try:
        block = prompt.split('[PREMISES]')[1].split('[PROOFS]')[0]
    except Exception:
        return None
    lines = [l for l in block.split('\n') if l.strip()]
    for i, l in enumerate(lines):
        if re.search(r'\b' + re.escape(gold_lemma) + r'\b', l):
            return f"{i+1}/{len(lines)}줄" + (" (state에서 먼→위)" if i < len(lines)/2 else " (state에 가까움→아래=recency)")
    return "블록에 없음(truncation됨?)"

APP = re.compile(r'^(?:e?apply|e?rewrite)\s+(?:<-\s*)?\(?\s*([A-Za-z_][\w\']*)')
SIMPLE = re.compile(r'^destruct\s+\(?\s*([A-Za-z_][\w\'\.]*)')

def pick_and_render(path, want, k, label):
    """want='destruct' or 'apply'. k개 골라 렌더."""
    picked = 0
    for line in open(path):
        if picked >= k: break
        try: g = json.loads(line)
        except: continue
        for a in g.get('attempts', []):
            if picked >= k: break
            for s in a.get('steps', []):
                tac = (s.get('tactic') or '').strip().lstrip('\n')
                e = s.get('example', {}) or {}
                goal = e.get('proof_state', '')
                prem = e.get('premises') or []
                if not goal or not prem: continue
                if want == 'destruct':
                    m = SIMPLE.match(tac)
                    if not m or m.group(1).split('.')[-1] not in IND: continue
                elif want == 'apply':
                    m = APP.match(tac)
                    if not m: continue
                    gl = m.group(1).split('.')[-1]
                    names = [re.match(r'(?:Lemma|Theorem|Definition)\s+([A-Za-z_][\w\'\.]*)', p.strip()) for p in prem]
                    names = [x.group(1).split('.')[-1] if x else None for x in names]
                    if gl not in names: continue
                ex = LmExample.from_json(e)
                # base (rerank off)
                os.environ['RERANK_PREMISES'] = '0'
                base = COL.collate_input(TOK, ex)
                # rerank on
                os.environ['RERANK_PREMISES'] = '1'
                rr = COL.collate_input(TOK, ex)
                os.environ['RERANK_PREMISES'] = '0'
                # augmented sections
                st = selective_types(goal); dc = deciders(goal)
                print("=" * 78)
                print(f"[{label}] want={want} | gold tactic: {tac[:60]}")
                print(f"  base 토큰 {ntok(base)} | rerank 토큰 {ntok(rr)}")
                print(f"  [TYPES]({ntok(st)}tok): {st.replace(chr(10),' || ') or '(none)'}")
                print(f"  [DECIDERS]({ntok(dc)}tok): {dc.replace(chr(10),' || ') or '(none)'}")
                if want == 'apply':
                    print(f"  gold lemma '{gl}' 위치 — base: {find_gold_premise_pos(base, gl)}")
                    print(f"                        rerank: {find_gold_premise_pos(rr, gl)}")
                # augmented 프롬프트 전문(앞부분)
                aug = base.replace('[STATE]', f'[TYPES]\n{st}\n[DECIDERS]\n{dc}\n[STATE]', 1) if (st or dc) else base
                print(f"  --- augmented 프롬프트 (앞 900자) ---")
                print("  " + aug[:900].replace('\n', '\n  '))
                picked += 1
                break

if __name__ == "__main__":
    import sys
    kap = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    kde = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    pick_and_render('data/grpo_rollouts/goldsft_bs2.jsonl', 'apply', kap, 'TRAIN')
    pick_and_render('data/grpo_rollouts/goldsft_bs2.jsonl', 'destruct', kde, 'TRAIN')
