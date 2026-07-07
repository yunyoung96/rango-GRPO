#!/usr/bin/env python3
"""
Iter 6: σ-포트폴리오 replay.
Iter5 분석에서 남은 수리의 상당수가 (a)모듈 qualifier rename 누락(Int.→Int64.),
(b)증명전용 심볼 stem 누락(decompose_and→decompose_or) 임이 드러남.
→ σ를 여러 변형으로 만들어 각각 replay, '컴파일되는 것'을 채택(합집합 커버리지).
  σ0 = base (statement difflib)
  σ1 = σ0 + 모듈 qualifier rename (M1. → M2., 예: Int.→Int64.)
  σ2 = σ0 + stem-core 전파 (andl/orl 의 공통core and→or 등)
  σ3 = σ0 + σ1 + σ2
compile 이 최종 필터라 잘못된 변형은 자동 탈락.
"""
import os, re, json, subprocess
import importlib.util
spec=importlib.util.spec_from_file_location("cov","scripts/poc_coverage.py"); cov=importlib.util.module_from_spec(spec); spec.loader.exec_module(cov)

def module_renames(sigma):
    """σ0 에서 M1.<rest> ↦ M2.<rest> 패턴을 발견하면 (M1., M2.) 모듈 rename 추가."""
    out=[]
    for a,b in sigma:
        ma=re.match(r"([A-Za-z0-9_']+)\.(.+)", a); mb=re.match(r"([A-Za-z0-9_']+)\.(.+)", b)
        if ma and mb and ma.group(2)==mb.group(2) and ma.group(1)!=mb.group(1):
            out.append((ma.group(1)+".", mb.group(1)+"."))
    # Vint/Vlong 등 값생성자 기반 힌트 → Int./Int64.
    names={(a,b) for a,b in sigma}
    if (("Vint","Vlong") in names) or any(a.startswith("Int.") and b.startswith("Int64.") for a,b in sigma):
        out.append(("Int.","Int64."))
    if (("Vlong","Vint") in names) or any(a.startswith("Int64.") and b.startswith("Int.") for a,b in sigma):
        out.append(("Int64.","Int."))
    # 중복 제거, 긴 것 우선
    seen=set(); uniq=[]
    for p in out:
        if p in seen or p[0]==p[1]: continue
        seen.add(p); uniq.append(p)
    return uniq

def stem_cores(sigma):
    """andl↦orl 처럼 공통 접두/접미를 벗긴 core(and↦or)를 전파용으로 추출."""
    out=[]
    for a,b in sigma:
        if not (a.isidentifier() and b.isidentifier()):
            # 단순 알파벳 토큰만
            if not (re.fullmatch(r"[A-Za-z0-9_']+",a) and re.fullmatch(r"[A-Za-z0-9_']+",b)): continue
        # 공통 접미 제거
        i=0
        while i<len(a) and i<len(b) and a[-1-i]==b[-1-i]: i+=1
        ca, cb = a[:len(a)-i], b[:len(b)-i]
        # 공통 접두 제거
        j=0
        while j<len(ca) and j<len(cb) and ca[j]==cb[j]: j+=1
        ca, cb = ca[j:], cb[j:]
        if 2<=len(ca)<=6 and 1<=len(cb)<=6 and ca!=cb and re.fullmatch(r"[a-z]+",ca):
            out.append((ca,cb))
    seen=set(); uniq=[]
    for p in out:
        if p in seen: continue
        seen.add(p); uniq.append(p)
    return uniq

def variants(sigma):
    s1=module_renames(sigma); s2=stem_cores(sigma)
    V={"σ0":sigma}
    if s1: V["σ1(+module)"]=sorted(sigma+s1,key=lambda p:-len(p[0]))
    if s2: V["σ2(+stem)"]=sorted(sigma+s2,key=lambda p:-len(p[0]))
    if s1 or s2: V["σ3(+both)"]=sorted(sigma+s1+s2,key=lambda p:-len(p[0]))
    return V

def main():
    same=[r for r in cov.ROWS if r[2]==r[3]['cfile'] and r[1]!='None']
    print(f"# Iter6 σ-포트폴리오: {len(same)}건\n")
    closed=[]; base_pass=[]
    for idx,name,tfile,b in same:
        nfile=b['cfile']; nn=b['cname']
        tl=cov.read(tfile); nl=cov.read(nfile)
        tloc=cov.find_lemma(tl,name); nloc=cov.find_lemma(nl,nn)
        if not tloc or not nloc: continue
        ns=cov.statement_text(nl,nloc[0],nloc[1]); ts=cov.statement_text(tl,tloc[0],tloc[1])
        sig=cov.derive_sigma(ns,ts)
        nb_body="\n".join(nl[nloc[1]+1:nloc[2]])
        won=None
        for vname,vs in variants(sig).items():
            cand=cov.apply_sigma(nb_body,vs)
            ok,err,dt=cov.compile_target(tfile,name,cand)
            if ok: won=vname; break
        if won:
            closed.append((idx,name,won));
            if won=="σ0": base_pass.append(idx)
            print(f"  idx={idx:<5} {name:<32} PASS ✅ via {won}")
    print(f"\n# 포트폴리오 커버리지: {len(closed)}/39  (base σ0만: {len(base_pass)})")
    for idx,name,won in closed:
        if won!="σ0": print(f"    +추가: idx={idx} {name}  ({won})")
    json.dump(closed, open("results/compcert_report/poc_portfolio.json","w"), ensure_ascii=False, indent=1)

if __name__=="__main__":
    main()
