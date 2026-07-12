#!/usr/bin/env python3
"""정리별 best(head-suffix, full-match)를 1회 계산 → 여러 임계값에서 개수 집계."""
import json, re, os, importlib.util
from collections import defaultdict
HERE="scripts"
def L(m,p):
    s=importlib.util.spec_from_file_location(m,os.path.join(HERE,p)); x=importlib.util.module_from_spec(s); s.loader.exec_module(x); return x
cov=L("cov","poc_coverage.py"); reach=L("reach","poc_prefix_reach.py")
allj=json.load(open("results/compcert_report/all.json"))["results"]

def head(t):
    m=re.match(r"\s*([A-Za-z_][A-Za-z_0-9']*)", t); return m.group(1) if m else t.strip()[:8]
def proof_steps(rec):
    try: lines=cov.read(rec["file"])
    except Exception: return None
    ps=rec.get("proof_span");
    if not ps: return None
    body="\n".join(lines[ps["start"]["line"]:ps["end"]["line"]+1])
    body=re.sub(r'\bProof\b\s*\.', '', body); body=re.sub(r'\b(Qed|Defined|Admitted)\b\s*\.', '', body)
    st=reach.split_steps(body); return st or None

items=[]
for r in allj:
    st=proof_steps(r)
    if st and len(st)>=4:
        items.append((r["idx"], st, [head(t) for t in st], r.get("success")))
bucket=defaultdict(list)
for i,it in enumerate(items): bucket[it[2][-1]].append(i)

# 정리별 best (hs, fm) — 의미있는 꼬리 위해 fm 우선 정렬 저장
best=[(0,0)]*len(items)
GENERIC={"lia","auto","eauto","omega","reflexivity","trivial","congruence","ring","easy","assumption","tauto"}
best_nontrivial=[(0,0)]*len(items)  # 마지막 tactic이 generic이 아닌(=의미있는 종결) suffix만
for i,it in enumerate(items):
    idx,st,hd,succ=it
    b=(0,0); bnt=(0,0)
    for j in bucket[hd[-1]]:
        if j==i: continue
        jt=items[j]
        n=min(len(hd),len(jt[2])); hs=0
        while hs<n and hd[-1-hs]==jt[2][-1-hs]: hs+=1
        if hs<4: continue
        fm=sum(1 for k in range(hs) if st[-1-k]==jt[1][-1-k])
        if (hs,fm)>b: b=(hs,fm)
        # 의미있음: 공통 suffix 안에 generic 아닌 tactic이 ≥1 있고 full-match 구간
        nontrivial=any(head(st[-1-k]) not in GENERIC for k in range(min(hs,fm)))
        if nontrivial and (hs,fm)>bnt: bnt=(hs,fm)
    best[i]=b; best_nontrivial[i]=bnt

def count(thr_hs,thr_fm,arr,filt=None):
    c=0
    for i,it in enumerate(items):
        if filt is not None and it[3] is not filt: continue
        if arr[i][0]>=thr_hs and arr[i][1]>=thr_fm: c+=1
    return c

N=len(items)
Nf=sum(1 for it in items if it[3] is False)
Ns=sum(1 for it in items if it[3] is True)
print(f"코퍼스 {N} proofs (실패 {Nf} / 성공 {Ns})\n")
print("[A] 원기준(모든 tactic, generic 포함) — 임계값별 'sibling 보유' 정리 수")
print(f"{'기준(hs/fm)':>12} | {'전체':>6} | {'실패중':>6} | {'성공중':>6}")
for hs,fm in [(4,3),(6,4),(8,6),(10,8),(15,10),(20,15),(30,20)]:
    print(f"{'≥%d/≥%d'%(hs,fm):>12} | {count(hs,fm,best):>6} | {count(hs,fm,best,False):>6} | {count(hs,fm,best,True):>6}")
print("\n[B] '의미있는 꼬리'(공통 suffix에 generic 아닌 tactic 포함) — 보일러플레이트 제외")
print(f"{'기준(hs/fm)':>12} | {'전체':>6} | {'실패중':>6} | {'성공중':>6}")
for hs,fm in [(4,3),(6,4),(8,6),(10,8),(15,10)]:
    print(f"{'≥%d/≥%d'%(hs,fm):>12} | {count(hs,fm,best_nontrivial):>6} | {count(hs,fm,best_nontrivial,False):>6} | {count(hs,fm,best_nontrivial,True):>6}")
