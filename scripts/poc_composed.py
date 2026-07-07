#!/usr/bin/env python3
"""
Iter 12: composed loop = Iter11(state-align σ포화) + Iter10(모델 repair) 반복.

단발 Iter10(poc_iter10_repair)은 site 하나만 고쳐 divlu_one 만 닫혔다. 실제 증명은
발산 site 가 여럿(Iter7: twin 의 60%가 ≤2 site). 그래서:
  반복:
    1. state-align 으로 σ 포화 → σ-mapped steps, reach k.
    2. k==len: PASS.
    3. σ 확장 불가(STUCK)면 → reach k 의 goal state 로 모델 호출, 상위 후보 중
       reach 를 가장 멀리 미는 tactic 을 step[k] 에 splice(그 위치는 고정, σ 재적용 X).
    4. 모델 예산(budget) 소진 or 전진 실패면 종료.
경계: splice 된 step 은 concrete → σ 재매핑 대상에서 제외. degenerate(Proof./Qed.) 필터.
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

def reach_of_steps(tfile,name,steps):
    k,n=reach.max_reach(tfile,name,steps); return k,n

def saturate_sigma(tfile,name,nfile,nname,base_body,sigma,fixed_upto,max_iter=6):
    """fixed_upto 이후 부분만 σ-remap 하며 reach 를 최대화. (fixed_upto 앞은 concrete 고정)
    반환: (steps, k, n, sigma). steps = fixed_prefix + σ-mapped(remainder)."""
    # base_body 는 neighbor 원본; fixed_prefix 는 이미 확정된 concrete steps 리스트로 별도 전달됨
    return None  # (아래 composed_solve 에서 인라인 처리)

def composed_solve(idx,name,tfile,nfile,nname,budget=3,n_sugg=8,verbose=False,use_model=True):
    import importlib
    tl=cov.read(tfile); nl=cov.read(nfile)
    tloc=cov.find_lemma(tl,name); nloc=cov.find_lemma(nl,nname)
    if not tloc or not nloc: return {"idx":idx,"name":name,"status":"SKIP"}
    ns=cov.statement_text(nl,nloc[0],nloc[1]); ts=cov.statement_text(tl,tloc[0],tloc[1])
    nbr_body="\n".join(nl[nloc[1]+1:nloc[2]])
    nbr_steps_raw=align.split_steps(nbr_body)
    base_sig=cov.derive_sigma(ns,ts)
    sigma=list(base_sig)
    fixed=[]            # concrete 확정 prefix (model repair 또는 확정된 σ-step)
    model_calls=0; repairs=[]; sat_iters=0
    def cur_steps():
        # fixed + σ-mapped(나머지 neighbor steps).  fixed 길이만큼 neighbor 앞부분은 skip.
        remainder=nbr_steps_raw[len(fixed):]
        mapped=align.split_steps(cov.apply_sigma_seg(" ".join(remainder), sigma)) if remainder else []
        return fixed+mapped
    while True:
        # --- state-align σ 포화 ---
        for _ in range(6):
            steps=cur_steps(); k,n=reach_of_steps(tfile,name,steps)
            if k>=n: return {"idx":idx,"name":name,"status":"PASS","model_calls":model_calls,
                             "repairs":repairs,"discovered":[p for p in sigma if p not in base_sig]}
            if k<len(fixed):   # fixed 안에서 깨짐(이론상 없음) → 중단
                break
            tgt=align.show_state(tfile,name,steps,k,tag="_c_alt_")
            # neighbor state: fixed 개수만큼 + (k-len(fixed)) σ-step 만큼 neighbor 원본 진행
            nbr_k=k  # 근사: 같은 index
            nbr=align.show_state(nfile,nname,nbr_steps_raw,min(nbr_k,len(nbr_steps_raw)),tag="_c_aln_")
            dsig=align.state_sigma(nbr,tgt)
            newp=[p for p in dsig if p not in sigma]
            if not newp: break
            k0=k
            # greedy 수용
            trial=sigma+newp
            st2=fixed+align.split_steps(cov.apply_sigma_seg(" ".join(nbr_steps_raw[len(fixed):]),trial))
            k2,_=reach_of_steps(tfile,name,st2)
            if k2>=k0: sigma=trial; sat_iters+=1
            else:
                mod=[p for p in newp if p[0].endswith('.')]
                st3=fixed+align.split_steps(cov.apply_sigma_seg(" ".join(nbr_steps_raw[len(fixed):]),sigma+mod)) if mod else steps
                k3,_=reach_of_steps(tfile,name,st3) if mod else (k0,0)
                if mod and k3>=k0: sigma=sigma+mod; sat_iters+=1
                else: break
        # --- σ 포화 끝: reach k 에서 모델 repair ---
        steps=cur_steps(); k,n=reach_of_steps(tfile,name,steps)
        if k>=n: return {"idx":idx,"name":name,"status":"PASS","model_calls":model_calls,"repairs":repairs,
                         "discovered":[p for p in sigma if p not in base_sig]}
        if not use_model or model_calls>=budget:
            return {"idx":idx,"name":name,"status":"STUCK","reach":f"{k}/{n}","model_calls":model_calls,
                    "repairs":repairs,"failing_step":steps[k] if k<len(steps) else None,
                    "discovered":[p for p in sigma if p not in base_sig]}
        mc=_load("mc","poc_model_call.py")
        raw=align.show_state(tfile,name,steps,k,tag="_c_i10_")
        state=_clean_state(raw)
        if not state:
            return {"idx":idx,"name":name,"status":"NOSTATE","reach":f"{k}/{n}","model_calls":model_calls,"repairs":repairs}
        prefix=" ".join(steps[:k])
        sugg=mc.suggest(state, proof_script=prefix, n=n_sugg, proofs=[nbr_body])
        model_calls+=1
        # 후보를 모델 점수 순으로 보며, 전진(reach>k)하는 첫 후보 채택(후보당 1-2 coqc).
        # 먼저 full PASS 인지(1 coqc), 아니면 prefix k+1 컴파일(1 coqc)로 '적용성공' 판정.
        best=None
        for tac,score in sugg:
            tac=tac.strip()
            if DEGEN.match(tac): continue
            if not tac.endswith("."): tac=tac+"."
            full=steps[:k]+[tac]+steps[k+1:]
            ok,_,_=cov.compile_target(tfile,name," ".join(full))
            if ok: best=(tac,round(score,2),n); break
            if reach.compile_prefix(tfile,name,steps[:k]+[tac], k+1):
                best=(tac,round(score,2),k+1); break
        if verbose: print(f"    model@{k}/{n}: best={best}")
        if best is None:
            return {"idx":idx,"name":name,"status":"NOFIX","reach":f"{k}/{n}","model_calls":model_calls,
                    "repairs":repairs,"failing_step":steps[k] if k<len(steps) else None}
        # splice: fixed 를 k+1 까지 concrete 로 확정 (앞 k 개 σ-step + 모델 tactic)
        fixed=steps[:k]+[best[0]]
        repairs.append({"at":f"{k}/{n}","tactic":best[0],"score":best[1],"reach_after":f"{best[2]}/{n}"})

def _clean_state(show_out):
    if not show_out: return show_out
    lines=show_out.split("\n"); i=0
    while i<len(lines) and (re.match(r"\s*\d+ goal", lines[i]) or not lines[i].strip()): i+=1
    return "\n".join(lines[i:]).strip()

def cleanup():
    for root,_,files in os.walk(cov.COMPCERT):
        for fn in files:
            if re.match(r"\.?_c_(alt|aln|i10)_", fn) or fn.startswith("_reach_") or fn.startswith("_cov_"):
                try: os.remove(os.path.join(root,fn))
                except: pass

def main():
    data=json.load(open(os.path.join(HERE,"..","results","compcert_report","poc_state_align.json")))
    rows={r[0]:(r[2],r[3]['cfile'],r[3]['cname']) for r in cov.ROWS if r[1]!='None'}
    use_model = "--nomodel" not in sys.argv
    only = [int(a) for a in sys.argv if a.isdigit()]
    targets=[r for r in data if r['status'] in ("STUCK","PASS")]
    if only: targets=[r for r in targets if r['idx'] in only]
    print(f"# Iter12 composed loop (use_model={use_model}): {len(targets)}건, budget=4\n", flush=True)
    out=[]
    for r in targets:
        idx=r['idx']
        if idx not in rows: continue
        tfile,nfile,nname=rows[idx]
        # 크기 guard: 거대 증명(>45 step)은 transplant 부적합(reach~0)이고 reach탐색이 과도 → 스킵
        nl=cov.read(nfile); nloc=cov.find_lemma(nl,nname)
        if nloc:
            nsteps=len(align.split_steps("\n".join(nl[nloc[1]+1:nloc[2]])))
            if nsteps>45:
                print(f"  idx={idx:<5} {r['name'][:34]:<34} SKIP_BIG ({nsteps} steps)", flush=True)
                out.append({"idx":idx,"name":r['name'],"status":"SKIP_BIG","steps":nsteps}); continue
        try:
            res=composed_solve(idx,r['name'],tfile,nfile,nname,use_model=use_model,verbose=(len(targets)<=3))
        except Exception as e:
            import traceback; res={"idx":idx,"name":r['name'],"status":"ERR","err":str(e)[:200]}
            if len(targets)<=3: traceback.print_exc()
        mcs=res.get("model_calls",0); rp=len(res.get("repairs",[]))
        print(f"  idx={idx:<5} {r['name'][:34]:<34} {res['status']:<7} model_calls={mcs} repairs={rp} "
              f"{res.get('reach','')}", flush=True)
        out.append(res)
    cleanup()
    npass=sum(1 for r in out if r['status']=="PASS")
    print(f"\n# composed 결과: PASS {npass}/{len(out)}")
    for r in out:
        if r['status']=="PASS":
            print(f"    PASS idx={r['idx']} {r['name']}  (model_calls={r['model_calls']}, repairs={[x['tactic'] for x in r.get('repairs',[])]})")
    suf="_nomodel" if not use_model else ""
    json.dump(out, open(os.path.join(HERE,"..","results","compcert_report",f"poc_composed{suf}.json"),"w"),
              ensure_ascii=False, indent=1)

if __name__=="__main__":
    main()
