#!/usr/bin/env python3
"""
Iter 11: state-indexed anti-unification (coqc + Show. 방식).

Iter 8 상한: rename 정보가 *문장이 아니라 증명 중간 goal state* 에만 있는 경우(testcond:
Int.eq↔Int64.eq)를 statement-σ 는 못 본다. 여기서는 발산 지점에서 두 형제 증명의 중간
goal state 를 뽑아(diff) 그 rename 을 자동 발견하고 σ 에 더해 transplant 를 재시도한다.

coqpyt(coq-lsp)는 CompCert 대형 파일 elaborate 가 너무 느려(>400s) 폐기.
대신 검증된 coqc 하네스에 `Show. Admitted.` 를 주입해 중간 상태를 stdout 으로 뽑는다(~2s).

루프:
  σ = statement-σ (base)
  반복:
    steps = split(apply_sigma(neighbor_body, σ))
    k = max prefix of steps that compiles on target  (reach)
    if k == n: PASS  ← transplant 완주
    tgt_state = Show(target, σ-mapped steps[:k])
    nbr_state = Show(neighbor, neighbor_steps[:k])
    Δσ = derive_sigma(nbr_state, tgt_state) + module_renames  (state 기반)
    if Δσ 새로움: σ += Δσ; 계속
    else: repair_site 기록(k) → Iter 10 모델 호출 대상; 중단
"""
import subprocess, re, os, time, json, sys
import importlib.util
HERE=os.path.dirname(__file__)
spec=importlib.util.spec_from_file_location("cov", os.path.join(HERE,"poc_coverage.py"))
cov=importlib.util.module_from_spec(spec); spec.loader.exec_module(cov)
rspec=importlib.util.spec_from_file_location("reach", os.path.join(HERE,"poc_prefix_reach.py"))
reach=importlib.util.module_from_spec(rspec); rspec.loader.exec_module(reach)
pspec=importlib.util.spec_from_file_location("port", os.path.join(HERE,"poc_sigma_portfolio.py"))
port=importlib.util.module_from_spec(pspec); pspec.loader.exec_module(port)

split_steps=reach.split_steps

def show_state(tfile, tname, steps, k, tag="_align_"):
    """target lemma 에 steps[:k] + Show. Admitted. 주입, coqc stdout 의 goal state 반환(None=컴파일실패)."""
    lines=cov.read(tfile); loc=cov.find_lemma(lines,tname)
    if not loc: return None
    start,proof,qed=loc; stack=cov.open_sections_at(lines,start)
    body=" ".join(steps[:k])
    new=lines[:proof+1]+[body, "Show.", "Admitted."]+[f"End {s}." for s in reversed(stack)]
    d=os.path.join(cov.COMPCERT, os.path.dirname(tfile))
    tmp=os.path.join(d, f"{tag}{tname}.v")
    open(tmp,"w",encoding="utf-8").write("\n".join(new)+"\n")
    try:
        r=subprocess.run(["coqc"]+cov.FLAGS+[os.path.relpath(tmp,cov.COMPCERT)],
                         cwd=cov.COMPCERT, capture_output=True, text=True, timeout=45)
        out=r.stdout
        # Show 는 goal 을 stdout 에 먼저 출력하므로, 뒤에 'module needs to be closed' 등
        # rc≠0 에러가 나도 goal 블록을 회수한다(Module 닫기 regex 한계 우회).
        m=re.search(r'(?:^|\n)(\d+ goal[s]?\b.*?)(?:\nError|\Z)', out, re.S)
        if m: return m.group(1).strip()
        if "No more goals" in out: return "No more goals."
        return None
    except subprocess.TimeoutExpired:
        return None
    finally:
        for junk in os.listdir(d):
            if junk.startswith(tag+tname) or junk.startswith("."+tag+tname):
                try: os.remove(os.path.join(d,junk))
                except: pass

import difflib as _dl
def _looks_rename(a,b):
    """a→b 가 '치환'이 아니라 '이름변형'(rename)처럼 보이는가: 유사한 문자열이거나
    포함관계(int⊂int64)거나, 공통 접두/접미가 뚜렷. rs'→nextinstr 같은 잡음 제거."""
    if a in b or b in a: return True
    return _dl.SequenceMatcher(a=a, b=b, autojunk=False).ratio() >= 0.5

def state_sigma(nbr_state, tgt_state):
    """두 goal-state 텍스트에서 rename σ 유도(문장 대신 state 를 anti-unify)."""
    if not nbr_state or not tgt_state: return []
    base=[p for p in cov.derive_sigma(nbr_state, tgt_state) if _looks_rename(*p)]
    mods=port.module_renames(base)                   # Int.→Int64. 등 모듈 rename 승격
    out=[]
    for p in base+mods:
        if p[0]!=p[1] and p not in out: out.append(p)
    out.sort(key=lambda p:-len(p[0]))
    return out

def align_transplant(idx, name, tfile, nfile, nname, max_iter=6, verbose=True):
    tl=cov.read(tfile); nl=cov.read(nfile)
    tloc=cov.find_lemma(tl,name); nloc=cov.find_lemma(nl,nname)
    if not tloc or not nloc: return {"idx":idx,"name":name,"status":"SKIP"}
    ns=cov.statement_text(nl,nloc[0],nloc[1]); ts=cov.statement_text(tl,tloc[0],tloc[1])
    nbr_body="\n".join(nl[nloc[1]+1:nloc[2]])
    nbr_steps_raw=split_steps(nbr_body)
    base_sig=cov.derive_sigma(ns,ts)
    sigma=list(base_sig)
    trace=[]
    def steps_of(sig): return split_steps(cov.apply_sigma_seg(nbr_body, sig))
    def reach_of(sig):
        s=steps_of(sig); k,n=reach.max_reach(tfile,name,s); return k,n,s
    for it in range(max_iter):
        k,n,steps=reach_of(sigma)
        if k==n:
            return {"idx":idx,"name":name,"status":"PASS","iters":it,"sigma":sigma,
                    "discovered":[p for p in sigma if p not in base_sig],"trace":trace}
        # 발산 지점 두 state 추출
        tgt_state=show_state(tfile,name,steps,k,tag="_alt_")
        nbr_state=show_state(nfile,nname,nbr_steps_raw,k,tag="_aln_")
        dsig=state_sigma(nbr_state,tgt_state)
        cand=[p for p in dsig if p not in sigma]
        # greedy 수용: 후보 전체 추가 시 reach 가 떨어지면(spurious) 모듈-prefix 만 채택
        accepted=[]
        if cand:
            k2,_,_=reach_of(sigma+cand)
            if k2>=k:
                accepted=cand
            else:
                mod_only=[p for p in cand if p[0].endswith('.')]
                k3,_,_=reach_of(sigma+mod_only) if mod_only else (k,n,steps)
                accepted=mod_only if k3>=k else []
        trace.append({"iter":it,"reach":f"{k}/{n}","cand":cand[:8],"accepted":accepted[:8]})
        if verbose:
            print(f"    it{it}: reach {k}/{n}, cand={cand[:5]}, accepted={accepted[:5]}")
        if not accepted:
            return {"idx":idx,"name":name,"status":"STUCK","reach":f"{k}/{n}",
                    "repair_step":steps[k] if k<len(steps) else None,
                    "sigma":sigma,"trace":trace,
                    "discovered":[p for p in sigma if p not in base_sig]}
        sigma=sigma+accepted
        sigma.sort(key=lambda p:-len(p[0]))
    return {"idx":idx,"name":name,"status":"MAXITER","sigma":sigma,"trace":trace}

if __name__=="__main__":
    # 단일 케이스 검증: testcond
    import argparse
    targets=[(527,"testcond_for_unsigned_comparison_64_correct","x86/Asmgenproof1.v",
              "x86/Asmgenproof1.v","testcond_for_unsigned_comparison_32_correct")]
    if len(sys.argv)>1 and sys.argv[1]=="all":
        same=[r for r in cov.ROWS if r[2]==r[3]['cfile'] and r[1]!='None']
        targets=[(idx,name,tfile,b['cfile'],b['cname']) for idx,name,tfile,b in same]
    allres=[]
    for idx,name,tfile,nfile,nname in targets:
        print(f"\n=== idx={idx} {name} ← {nname} ===", flush=True)
        try:
            res=align_transplant(idx,name,tfile,nfile,nname, verbose=(len(targets)==1))
        except Exception as e:
            res={"idx":idx,"name":name,"status":"ERR","err":str(e)[:120]}
        print(f"  → {res['status']}  discovered σ: {res.get('discovered')}", flush=True)
        if res.get('status')=="STUCK":
            print(f"    repair site @ {res.get('reach')}: {res.get('repair_step')}", flush=True)
        allres.append(res)
    if len(allres)>1:
        npass=sum(1 for r in allres if r['status']=="PASS")
        nstuck=sum(1 for r in allres if r['status']=="STUCK")
        # 실제로 rename 을 새로 발견한(discovered 비어있지 않은) 케이스
        ndisc=sum(1 for r in allres if r.get('discovered'))
        print(f"\n# Iter11 state-align 결과: PASS {npass} · STUCK {nstuck} · 그외 {len(allres)-npass-nstuck}")
        print(f"# state 로 새 rename 발견한 케이스: {ndisc}")
        json.dump(allres, open(os.path.join(HERE,"..","results","compcert_report","poc_state_align.json"),"w"),
                  ensure_ascii=False, indent=1)
        print("PASS 목록:", [r['name'] for r in allres if r['status']=="PASS"])
