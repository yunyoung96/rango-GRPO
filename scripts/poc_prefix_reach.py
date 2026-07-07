#!/usr/bin/env python3
"""
Iter 3: prefix-reachability 계측.
σ-proof(형제 증명에 자동 σ 적용)를 target 자리에서 앞에서부터 몇 tactic까지 통과하는지 측정.
  - <first k steps> + 'Admitted.'  가 컴파일되는 최대 k 를 이분탐색.
  - reach = k / total_steps.
해석: reach=1.0 → 전량 통과(원샷). 0<reach<1 → k 지점서 국소수리 1방 대상(방법 B).
      reach≈0 → 형제 아님(첫 스텝부터 어긋남).
"""
import subprocess, re, os, time, json, difflib
import importlib.util
spec=importlib.util.spec_from_file_location("cov", os.path.join(os.path.dirname(__file__),"poc_coverage.py"))
cov=importlib.util.module_from_spec(spec); spec.loader.exec_module(cov)

def split_steps(body):
    # 문장 끝 마침표(뒤가 공백/끝)에서만 분리. Int.eq 같은 정규화명은 보존. 세미콜론은 한 스텝 내 유지.
    parts=re.split(r'(?<=\.)(?=\s|$)', body)
    steps=[p.strip() for p in parts if p.strip()]
    return steps

def compile_prefix(tfile, tname, steps, k):
    lines=cov.read(tfile); loc=cov.find_lemma(lines,tname)
    if not loc: return None
    start,proof,qed=loc; stack=cov.open_sections_at(lines,start)
    body=" ".join(steps[:k])
    new=lines[:proof+1]+[body, "Admitted."]+[f"End {s}." for s in reversed(stack)]
    text="\n".join(new)+"\n"
    d=os.path.join(cov.COMPCERT, os.path.dirname(tfile))
    tmp=os.path.join(d, f"_reach_{tname}.v")
    open(tmp,"w",encoding="utf-8").write(text)
    try:
        r=subprocess.run(["coqc"]+cov.FLAGS+[os.path.relpath(tmp,cov.COMPCERT)],
                         cwd=cov.COMPCERT, capture_output=True, text=True, timeout=45)
        return r.returncode==0
    except subprocess.TimeoutExpired:
        return False
    finally:
        for junk in os.listdir(d):
            if junk.startswith(f"_reach_{tname}") or junk.startswith(f".{'_reach_'+tname}"):
                try: os.remove(os.path.join(d,junk))
                except: pass

def max_reach(tfile, tname, steps):
    # 이분탐색: compile(k) 는 k 에 대해 대체로 단조(앞이 되면 더 앞도 됨) 라 가정.
    n=len(steps)
    if n==0: return 0,0
    lo,hi,best=0,n,0
    # 먼저 전량 시도
    if compile_prefix(tfile,tname,steps,n): return n,n
    lo,hi=0,n-1
    while lo<=hi:
        mid=(lo+hi)//2
        if mid==0: ok=True
        else: ok=compile_prefix(tfile,tname,steps,mid)
        if ok: best=mid; lo=mid+1
        else: hi=mid-1
    return best,n

def main():
    same=[r for r in cov.ROWS if r[2]==r[3]['cfile'] and r[1]!='None']
    out=[]
    print(f"# prefix-reachability: 형제쌍 {len(same)}건\n")
    for idx,name,tfile,b in same:
        nfile=b['cfile']; nname=b['cname']
        tl=cov.read(tfile); nl=cov.read(nfile)
        tloc=cov.find_lemma(tl,name); nloc=cov.find_lemma(nl,nname)
        if not tloc or not nloc:
            print(f"  idx={idx:<5} {name:<30} SKIP"); out.append((idx,name,nname,-1,-1)); continue
        ns=cov.statement_text(nl,nloc[0],nloc[1]); ts=cov.statement_text(tl,tloc[0],tloc[1])
        sig=cov.derive_sigma(ns,ts)
        body=cov.apply_sigma("\n".join(nl[nloc[1]+1:nloc[2]]), sig)
        steps=split_steps(body)
        k,n=max_reach(tfile,name,steps)
        r=k/n if n else 0
        bar="█"*int(r*20)+"·"*(20-int(r*20))
        print(f"  idx={idx:<5} {name:<30} reach {k:>2}/{n:<2} {bar} {r:.0%}")
        out.append((idx,name,nname,k,n))
    json.dump(out, open(os.path.join(os.path.dirname(__file__),"..","results","compcert_report","poc_prefix_reach.json"),"w"), ensure_ascii=False, indent=1)
    # 분포 요약
    full=[o for o in out if o[3]>=0 and o[3]==o[4]]
    partial=[o for o in out if o[3]>=0 and 0<o[3]<o[4]]
    zero=[o for o in out if o[3]==0 and o[4]>0]
    print(f"\n# 요약: 전량통과(reach=1) {len(full)} · 부분통과(0<reach<1) {len(partial)} · 첫스텝실패(reach=0) {len(zero)}")
    print("# 부분통과 = '국소수리 1~수방으로 닫힐 후보'. 목록:")
    for idx,name,nn,k,n in sorted(partial,key=lambda x:-(x[3]/x[4])):
        print(f"    idx={idx:<5} {name:<30} {k}/{n} = {k/n:.0%}  (남은 {n-k} step 수리)")

if __name__=="__main__":
    main()
