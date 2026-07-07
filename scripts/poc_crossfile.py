#!/usr/bin/env python3
"""타 파일(cross-file) 형제쌍에 composed 이식 평가 — 지금까지 '미평가'였던 39건.
하네스는 이웃 증명을 target 파일 맥락에 주입해 coqc 검증하므로, 이웃이 target import 에
없는 lemma 를 쓰면 그냥 낮은 reach/NOFIX 로 잡힘(정당)."""
import os, sys, json, re, importlib.util
HERE=os.path.dirname(__file__); sys.path.insert(0, os.path.join(HERE,"..","src"))
def L(m,p):
    s=importlib.util.spec_from_file_location(m,os.path.join(HERE,p)); x=importlib.util.module_from_spec(s); s.loader.exec_module(x); return x
comp=L("comp","poc_composed.py"); cov=comp.cov; align=comp.align

def main():
    rows=json.load(open("/tmp/claude-0/-app-coq-modeling/6331508b-8918-46d1-8fc8-94a923df1143/scratchpad/suffix_rows.json"))
    cross=[r for r in rows if r[2]!=r[3]['cfile'] and r[1] not in ('None',None)]
    only=[int(a) for a in sys.argv if a.isdigit()]
    if only: cross=[r for r in cross if r[0] in only]
    use_model = "--nomodel" not in sys.argv
    print(f"# cross-file 이식 평가: {len(cross)}건 (use_model={use_model})\n", flush=True)
    out=[]
    for idx,name,tfile,nb in cross:
        nfile=nb['cfile']; nname=nb['cname']
        nl=cov.read(nfile); nloc=cov.find_lemma(nl,nname)
        if nloc:
            nsteps=len(align.split_steps("\n".join(nl[nloc[1]+1:nloc[2]])))
            if nsteps>30:
                print(f"  idx={idx:<5} {name[:30]:<30} SKIP_BIG ({nsteps})",flush=True)
                out.append({"idx":idx,"name":name,"status":"SKIP_BIG","steps":nsteps}); continue
        try:
            res=comp.composed_solve(idx,name,tfile,nfile,nname,budget=2,n_sugg=6,use_model=use_model)
        except Exception as ex:
            res={"idx":idx,"name":name,"status":"ERR","err":str(ex)[:150]}
        mcs=res.get("model_calls",0)
        print(f"  idx={idx:<5} {name[:30]:<30} {res['status']:<7} calls={mcs} {res.get('reach','')}",flush=True)
        out.append(res)
    comp.cleanup()
    npass=sum(1 for r in out if r['status']=="PASS")
    print(f"\n# cross-file 결과: PASS {npass}/{len(out)}")
    for r in out:
        if r['status']=="PASS": print(f"    PASS idx={r['idx']} {r['name']} (calls={r['model_calls']})")
    json.dump(out, open(os.path.join(HERE,"..","results","compcert_report","poc_crossfile.json"),"w"), ensure_ascii=False, indent=1)

if __name__=="__main__":
    main()
