#!/usr/bin/env python3
"""suffix 유사 sibling — 상세 통계표. 임계값별 + 컴포넌트별 + sibling 관계 분해."""
import json, re, os, importlib.util
from collections import defaultdict
HERE="scripts"
def L(m,p):
    s=importlib.util.spec_from_file_location(m,os.path.join(HERE,p)); x=importlib.util.module_from_spec(s); s.loader.exec_module(x); return x
cov=L("cov","poc_coverage.py"); reach=L("reach","poc_prefix_reach.py")
allj=json.load(open("results/compcert_report/all.json"))["results"]

def head(t):
    m=re.match(r"\s*([A-Za-z_][A-Za-z_0-9']*)", t); return m.group(1) if m else t.strip()[:8]
def comp(f):  # CompCert 컴포넌트(최상위 디렉토리)
    return f.split("/")[0] if "/" in f else f
def proof_steps(rec):
    try: lines=cov.read(rec["file"])
    except Exception: return None
    ps=rec.get("proof_span")
    if not ps: return None
    body="\n".join(lines[ps["start"]["line"]:ps["end"]["line"]+1])
    body=re.sub(r'\bProof\b\s*\.', '', body); body=re.sub(r'\b(Qed|Defined|Admitted)\b\s*\.', '', body)
    return reach.split_steps(body) or None

items=[]
for r in allj:
    st=proof_steps(r)
    if st and len(st)>=4:
        items.append({"idx":r["idx"],"file":r["file"],"st":st,"hd":[head(t) for t in st],
                      "succ":r.get("success"),"n":len(st)})
bucket=defaultdict(list)
for i,it in enumerate(items): bucket[it["hd"][-1]].append(i)

# 정리별 best 매치(hs,fm,sibling_i)
best=[None]*len(items)
for i,it in enumerate(items):
    b=None
    for j in bucket[it["hd"][-1]]:
        if j==i or items[j]["idx"]==it["idx"]: continue
        jt=items[j]; n=min(it["n"],jt["n"]); hs=0
        while hs<n and it["hd"][-1-hs]==jt["hd"][-1-hs]: hs+=1
        if hs<4: continue
        fm=sum(1 for k in range(hs) if it["st"][-1-k]==jt["st"][-1-k])
        if b is None or (hs,fm)>(b[0],b[1]): b=(hs,fm,j)
    best[i]=b

def rows(thr_hs,thr_fm):
    sel=[i for i,b in enumerate(best) if b and b[0]>=thr_hs and b[1]>=thr_fm]
    tot=len(sel); fail=sum(1 for i in sel if items[i]["succ"] is False)
    succ=tot-fail
    if not sel: return tot,fail,succ,0,0,0,0
    avg_hs=sum(best[i][0] for i in sel)/tot
    avg_fm=sum(best[i][1] for i in sel)/tot
    # suffix가 증명에서 차지하는 평균 비율(fm/proof길이)
    avg_frac=sum(best[i][1]/items[i]["n"] for i in sel)/tot
    samefile=sum(1 for i in sel if items[i]["file"]==items[best[i][2]]["file"])
    return tot,fail,succ,avg_hs,avg_fm,avg_frac,samefile

N=len(items); Nf=sum(1 for it in items if it["succ"] is False)
print(f"# suffix 유사 sibling 상세 (코퍼스 {N} proofs, 실패 {Nf}/성공 {N-Nf})\n")
print("| 기준 hs/fm | 전체 | 실패중 | 성공중 | 전체율 | 평균 suffix길이 | 평균 full일치 | 증명중 suffix비중 | 같은파일 sibling |")
print("|---|---|---|---|---|---|---|---|---|")
for hs,fm in [(4,3),(6,4),(8,6),(10,8),(15,10),(20,15),(30,20)]:
    t,f,s,ah,af,afr,sf=rows(hs,fm)
    print(f"| ≥{hs}/≥{fm} | {t} | {f} | {s} | {100*t/N:.1f}% | {ah:.1f} | {af:.1f} | {100*afr:.0f}% | {sf} ({100*sf/max(t,1):.0f}%) |")

# 컴포넌트별 분해 (기준 ≥8/≥6)
print("\n## CompCert 컴포넌트별 (기준 hs≥8/fm≥6)")
print("| 컴포넌트 | 유사sibling 보유 | 해당 컴포넌트 전체 | 비율 |")
print("|---|---|---|---|")
compsel=defaultdict(int); comptot=defaultdict(int)
for i,it in enumerate(items):
    comptot[comp(it["file"])]+=1
    if best[i] and best[i][0]>=8 and best[i][1]>=6: compsel[comp(it["file"])]+=1
for c in sorted(comptot,key=lambda x:-compsel[x]):
    if comptot[c]>=20:
        print(f"| {c} | {compsel[c]} | {comptot[c]} | {100*compsel[c]/comptot[c]:.0f}% |")
