#!/usr/bin/env python3
"""
방법 D — 상태-지향(trajectory-prior) repair.

composed(Iter12)는 발산지점서 '전진하는 첫 후보'(greedy)를 splice 한다. 방법 D 는
후보 top-N 의 **full reach-after 를 실측**해 *가장 멀리 가는*(= 형제 suffix 에 가장 잘
재정렬되는) 것을 고른다. reach 가 크게 점프 = 형제 궤적 재합류 = suffix 도달의 신호.
즉 'best-reach beam' 이 greedy 보다 STUCK 을 더 닫는지 검증.

near-miss STUCK(예: cmpu_bool_sound 22/23) 처럼 greedy 가 못 닫은 케이스에서
best-reach 선택이 이득을 주는지 본다.
"""
import os, sys, json, re
HERE=os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE,"..","src"))
import importlib.util
def _load(m,p):
    s=importlib.util.spec_from_file_location(m,os.path.join(HERE,p)); x=importlib.util.module_from_spec(s); s.loader.exec_module(x); return x
cov=_load("cov","poc_coverage.py"); reach=_load("reach","poc_prefix_reach.py")
align=_load("align","poc_state_align.py")
DEGEN=re.compile(r"^\s*(Proof|Qed|Defined|Abort|idtac|admit|Admitted)\b")

def _clean_state(s):
    if not s: return s
    L=s.split("\n"); i=0
    while i<len(L) and (re.match(r"\s*\d+ goal",L[i]) or not L[i].strip()): i+=1
    return "\n".join(L[i:]).strip()

def solve(idx,name,tfile,nfile,nname,budget=5,n_sugg=8,select="bestreach",verbose=False):
    tl=cov.read(tfile); nl=cov.read(nfile)
    tloc=cov.find_lemma(tl,name); nloc=cov.find_lemma(nl,nname)
    if not tloc or not nloc: return {"idx":idx,"name":name,"status":"SKIP"}
    ns=cov.statement_text(nl,nloc[0],nloc[1]); ts=cov.statement_text(tl,tloc[0],tloc[1])
    nbr_body="\n".join(nl[nloc[1]+1:nloc[2]]); nbr_raw=align.split_steps(nbr_body)
    base_sig=cov.derive_sigma(ns,ts); sigma=list(base_sig); fixed=[]
    model_calls=0; repairs=[]
    mc=_load("mc","poc_model_call.py")
    def cur():
        rem=nbr_raw[len(fixed):]
        return fixed+(align.split_steps(cov.apply_sigma_seg(" ".join(rem),sigma)) if rem else [])
    while True:
        # σ 포화
        for _ in range(6):
            steps=cur(); k,n=reach.max_reach(tfile,name,steps)
            if k>=n: return {"idx":idx,"name":name,"status":"PASS","model_calls":model_calls,"repairs":repairs,"select":select}
            tgt=align.show_state(tfile,name,steps,k,tag="_d_alt_")
            nbr=align.show_state(nfile,nname,nbr_raw,min(k,len(nbr_raw)),tag="_d_aln_")
            newp=[p for p in align.state_sigma(nbr,tgt) if p not in sigma]
            if not newp: break
            trial=sigma+newp
            st2=fixed+align.split_steps(cov.apply_sigma_seg(" ".join(nbr_raw[len(fixed):]),trial))
            k2,_=reach.max_reach(tfile,name,st2)
            if k2>=k: sigma=trial
            else:
                mod=[p for p in newp if p[0].endswith('.')]
                if not mod: break
                st3=fixed+align.split_steps(cov.apply_sigma_seg(" ".join(nbr_raw[len(fixed):]),sigma+mod))
                k3,_=reach.max_reach(tfile,name,st3)
                if k3>=k: sigma=sigma+mod
                else: break
        steps=cur(); k,n=reach.max_reach(tfile,name,steps)
        if k>=n: return {"idx":idx,"name":name,"status":"PASS","model_calls":model_calls,"repairs":repairs,"select":select}
        if model_calls>=budget:
            return {"idx":idx,"name":name,"status":"STUCK","reach":f"{k}/{n}","model_calls":model_calls,"repairs":repairs,"select":select}
        state=_clean_state(align.show_state(tfile,name,steps,k,tag="_d_i10_"))
        if not state:
            return {"idx":idx,"name":name,"status":"NOSTATE","reach":f"{k}/{n}","model_calls":model_calls,"repairs":repairs,"select":select}
        sugg=mc.suggest(state, proof_script=" ".join(steps[:k]), n=n_sugg, proofs=[nbr_body])
        model_calls+=1
        cands=[]
        for tac,score in sugg:
            tac=tac.strip()
            if DEGEN.match(tac): continue
            if not tac.endswith("."): tac=tac+"."
            cands.append((tac,score))
        best=None; best_r=k
        if select=="firstadvance":       # composed 방식(비교용)
            for tac,score in cands:
                if reach.compile_prefix(tfile,name,steps[:k]+[tac],k+1): best=(tac,k+1); break
        else:                            # bestreach: 후보별 full reach-after 실측→최대
            for tac,score in cands:
                full=steps[:k]+[tac]+steps[k+1:]
                ok,_,_=cov.compile_target(tfile,name," ".join(full))
                if ok: best=(tac,n); best_r=n; break
                r,_=reach.max_reach(tfile,name,full)
                if r>best_r: best_r=r; best=(tac,r)
        if verbose: print(f"    D@{k}/{n}: best={best}  (후보 {len(cands)})")
        if best is None:
            return {"idx":idx,"name":name,"status":"NOFIX","reach":f"{k}/{n}","model_calls":model_calls,"repairs":repairs,"select":select}
        fixed=steps[:k]+[best[0]]; repairs.append({"at":f"{k}/{n}","tac":best[0],"reach_after":f"{best[1]}/{n}"})

def cleanup():
    for root,_,f in os.walk(cov.COMPCERT):
        for fn in f:
            if re.match(r"\.?_d_(alt|aln|i10)_",fn) or fn.startswith("_reach_") or fn.startswith("_cov_"):
                try: os.remove(os.path.join(root,fn))
                except: pass

def main():
    data=json.load(open(os.path.join(HERE,"..","results","compcert_report","poc_state_align.json")))
    rows={r[0]:(r[2],r[3]['cfile'],r[3]['cname']) for r in cov.ROWS if r[1]!='None'}
    idxs=[int(a) for a in sys.argv if a.isdigit()] or [412,776,236,1068,338,527]
    print(f"# 방법D best-reach beam: {idxs}\n", flush=True)
    out=[]
    for idx in idxs:
        if idx not in rows: continue
        tfile,nfile,nname=rows[idx]
        r=next((x for x in data if x['idx']==idx),{})
        nm=r.get('name','?')
        try: res=solve(idx,nm,tfile,nfile,nname,verbose=True)
        except Exception as e:
            import traceback; traceback.print_exc(); res={"idx":idx,"name":nm,"status":"ERR","err":str(e)[:150]}
        print(f"  idx={idx:<5} {nm[:32]:<32} {res['status']:<7} calls={res.get('model_calls',0)} {res.get('reach','')}", flush=True)
        out.append(res)
    cleanup()
    npass=sum(1 for r in out if r['status']=="PASS")
    print(f"\n# 방법D 결과: PASS {npass}/{len(out)}")
    for r in out:
        if r['status']=="PASS": print(f"    PASS idx={r['idx']} {r['name']}  calls={r['model_calls']} repairs={[x['tac'] for x in r.get('repairs',[])]}")
    json.dump(out, open(os.path.join(HERE,"..","results","compcert_report","poc_method_d.json"),"w"), ensure_ascii=False, indent=1)

if __name__=="__main__":
    main()
