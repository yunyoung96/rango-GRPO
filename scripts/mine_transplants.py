#!/usr/bin/env python3
"""방법 ②: corpus-symmetry self-supervision.
같은 파일 내 statement-유사 형제쌍에서, sibling proof에 statement-σ(anti-unification)를
적용해 target 자리에 coqc 검증. 통과분 = 검증된 transplant 학습데이터.
사용: python3 scripts/mine_transplants.py [max_pairs] [jac_thresh]
"""
import json, re, os, sys, importlib.util, difflib
HERE=os.path.dirname(__file__)
def L(m,p):
    s=importlib.util.spec_from_file_location(m,os.path.join(HERE,p));x=importlib.util.module_from_spec(s);s.loader.exec_module(x);return x
sig=L("sig","poc_sigma_replay.py")   # compile_variant, extract_body, read, apply_rules
cov=L("cov","poc_coverage.py")

MAXP=int(sys.argv[1]) if len(sys.argv)>1 else 100
JAC=float(sys.argv[2]) if len(sys.argv)>2 else 0.55
allj=json.load(open("results/compcert_report/all.json"))["results"]

def name_of(rec):
    try:
        lines=cov.read(rec["file"]); ts=rec["theorem_span"]["start"]["line"]
        m=re.search(r'\b(Lemma|Theorem)\s+([A-Za-z0-9_\']+)', "\n".join(lines[ts:ts+3]))
        return m.group(2) if m else None
    except Exception: return None
def stmt_str(rec):
    lines=cov.read(rec["file"]); ts=rec["theorem_span"]
    return "\n".join(lines[ts["start"]["line"]:ts["end"]["line"]+1])
def toks(s): return re.findall(r"[A-Za-z_][A-Za-z0-9_'.]*", s)

# 코퍼스: 파일별로 (idx,name,stmt,tokset)
byfile={}
for r in allj:
    nm=name_of(r)
    if not nm: continue
    try: st=stmt_str(r)
    except Exception: continue
    byfile.setdefault(r["file"],[]).append((r["idx"],nm,st,set(toks(st)),r))

def anti_unify_sigma(a,b):
    """b(sibling)→a(target) 토큰 치환. 위치별 diff. 단어경계 apply용."""
    ta,tb=toks(a),toks(b)
    sm=difflib.SequenceMatcher(None,tb,ta); sig={}
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag=="equal": continue
        for x,y in zip(tb[i1:i2],ta[j1:j2]):
            if x!=y and re.match(r"[A-Za-z_]",x): sig[x]=y
    return sig
def apply_sigma(body,sigma):
    for a,b in sorted(sigma.items(),key=lambda kv:-len(kv[0])):
        body=re.sub(r"(?<![A-Za-z0-9_'.]){}(?![A-Za-z0-9_'.])".format(re.escape(a)),b,body)
    return body

_UNRESOLVED=re.compile(r"(?:The reference|reference)\s+([A-Za-z_][A-Za-z0-9_'.]*)\s+was not found"
                       r"|The reference ([A-Za-z_][\w'.]*) was not found"
                       r"|([A-Za-z_][\w'.]*) not found")
def parse_unresolved(err):
    ids=[]
    for m in _UNRESOLVED.finditer(err or ""):
        ids += [g for g in m.groups() if g]
    return ids
def edit_dist(a,b):
    if a==b: return 0
    m,n=len(a),len(b); dp=list(range(n+1))
    for i in range(1,m+1):
        prev=dp[0]; dp[0]=i
        for j in range(1,n+1):
            cur=dp[j]; dp[j]=min(dp[j]+1,dp[j-1]+1,prev+(a[i-1]!=b[j-1])); prev=cur
    return dp[n]
def resolve_symbol(x, vocab):
    """미해결 심볼 x → target 파일 스코프에서 rename-neighbor(최소 편집거리, 공통접두)."""
    xs=x.split(".")[-1]  # qualified 꼬리
    best=None; bd=99
    for c in vocab:
        cs=c.split(".")[-1]
        if cs==xs: continue
        # 공통 접두 3자 이상 + 짧은 편집거리
        pl=len(os.path.commonprefix([xs,cs]))
        if pl<3: continue
        d=edit_dist(xs,cs)
        if d<=max(2,len(xs)//3) and d<bd:
            bd=d; best=c
    return best

def compile_with_repair(f, tgt_name, sibbody, sigma0, cut, vocab, max_repair=6):
    """σ0 적용 후 compile → 실패시 미해결 심볼을 vocab에서 보정하며 재컴파일 반복."""
    sigma=dict(sigma0)
    for _ in range(max_repair+1):
        body=apply_sigma(sibbody, sigma)
        try:
            ok,dt,err=sig.compile_variant(f,tgt_name,body,cut_suffix=cut)
        except Exception as e:
            return False, sigma, str(e)[:80]
        if ok:
            return True, sigma, ""
        uns=parse_unresolved(err)
        fixed=False
        for x in uns:
            base=x.split(".")[-1]
            if base in (v.split(".")[-1] for v in sigma.values()): continue
            r=resolve_symbol(x, vocab)
            if r and r!=x:
                sigma[base]=r.split(".")[-1]; fixed=True
        if not fixed:
            return False, sigma, (err or "")[:120]
    return False, sigma, "max_repair"

# === Phase 1: 코퍼스 전체 statement-σ를 aggregate → 전역 rename-family 사전 ===
from collections import Counter
famcount=Counter()
for f,items in byfile.items():
    for a in items:
        for b in items:
            if b[1]==a[1]: continue
            jj=len(a[3]&b[3])/max(len(a[3]|b[3]),1)
            if jj<JAC: continue
            for s,t in anti_unify_sigma(a[2],b[2]).items():
                famcount[(s.split(".")[-1],t.split(".")[-1])]+=1
# 2회 이상 일관되게 관측된 (src->tgt) = family 사전 (src당 최빈 tgt)
srcbest={}
for (s,t),c in famcount.items():
    if c<2: continue
    if s not in srcbest or c>srcbest[s][1]: srcbest[s]=(t,c)
FAMILY={s:t for s,(t,c) in srcbest.items()}
print(f"[Phase1] 전역 rename-family 사전: {len(FAMILY)}개 (예: "
      + ", ".join(f'{s}→{t}' for s,t in list(FAMILY.items())[:6]) + ")")

verified=[]; tried=0
os.makedirs("data/transplant_selfsup",exist_ok=True)
out=open("data/transplant_selfsup/verified.jsonl","w")
for f,items in byfile.items():
    if tried>=MAXP: break
    for a in items:
        if tried>=MAXP: break
        # 같은 파일에서 statement 가장 비슷한 sibling
        cands=[]
        for b in items:
            if b[1]==a[1]: continue
            j=len(a[3]&b[3])/max(len(a[3]|b[3]),1)
            if j>=JAC: cands.append((j,b))
        cands.sort(reverse=True)
        for j,b in cands[:2]:
            tried+=1
            try:
                _,_,_,sibbody=sig.extract_body(cov.read(f),b[1])
            except Exception: continue
            sigma=anti_unify_sigma(a[2],b[2])
            # 전역 family 사전으로 σ 확장: sibling proof에 등장하는 토큰 중 family에 있는 것.
            sibtoks=set(t.split(".")[-1] for t in toks(sibbody))
            for s in sibtoks:
                if s in FAMILY and s not in (k.split(".")[-1] for k in sigma):
                    sigma[s]=FAMILY[s]
            # 대상 lemma가 Section/Module 안이면 Qed 뒤에서 열린 것들을 닫아줘야 컴파일됨.
            flines=cov.read(f)
            tstart=a[4]["theorem_span"]["start"]["line"]
            stack=cov.open_sections_at(flines,tstart)
            cut="\n".join(f"End {s}." for s in reversed(stack))
            # target 파일 vocabulary(보정 후보): 파일 전체 식별자
            vocab=set(toks("\n".join(flines)))
            ok,sigma_final,err=compile_with_repair(f,a[1],sibbody,sigma,cut,vocab)
            if ok:
                transplanted=apply_sigma(sibbody,sigma_final)
                verified.append((a[0],a[1],b[1],j,len(sigma_final)-len(sigma)))
                out.write(json.dumps({"idx":a[0],"name":a[1],"file":f,"sibling":b[1],
                                      "jaccard":round(j,3),"n_repair":len(sigma_final)-len(sigma),
                                      "transplanted_proof":transplanted})+"\n")
                out.flush()
                break
out.close()
print(f"\n시도 {tried}쌍 → 검증통과 transplant {len(verified)}개 ({100*len(verified)/max(tried,1):.0f}%)")
for idx,nm,sib,j,nrep in verified[:20]:
    print(f"  ✅ {nm}  ← {sib}  (jac {j:.2f}, 보정 {nrep})")
