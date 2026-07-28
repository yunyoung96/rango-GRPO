#!/usr/bin/env python3
"""각 정리의 스텝별 중간 goal state(가설 포함)를 추출.
효율: 프루프 1개당 coqc 1회 — 각 tactic 뒤에 `idtac "@@k@@". Show.` 를 심어 모든 중간
상태를 한 컴파일의 stdout 으로 뽑고 마커로 분리한다."""
import os, re, subprocess, json, importlib.util, time
HERE=os.path.dirname(__file__)
def L(m,p):
    s=importlib.util.spec_from_file_location(m,os.path.join(HERE,p)); x=importlib.util.module_from_spec(s); s.loader.exec_module(x); return x
cov=L("cov","poc_coverage.py"); reach=L("reach","poc_prefix_reach.py")

def step_states(cfile, name, maxsteps=45):
    lines=cov.read(cfile); loc=cov.find_lemma(lines,name)
    if not loc: return None
    start,proof,qed=loc
    body="\n".join(lines[proof+1:qed])
    steps=reach.split_steps(body)[:maxsteps]
    stack=cov.open_sections_at(lines,start)
    # 각 스텝마다 goal(Show) + proof term(Show Proof) 를 마커(@@Gk@@ / @@Pk@@)와 함께 뽑는다.
    #   Gk 와 Pk 는 같은 proof state(둘 다 Show 계열 command 앞의 idtac 마커)라 함께 성공/실패.
    inj=[f'idtac "@@G0@@".','Show.',f'idtac "@@P0@@".','Show Proof.']
    for k,s in enumerate(steps,1):
        inj += [s, f'idtac "@@G{k}@@".','Show.', f'idtac "@@P{k}@@".','Show Proof.']
    new=lines[:proof+1]+inj+["Admitted."]+[f"End {x}." for x in reversed(stack)]
    d=os.path.join(cov.COMPCERT, os.path.dirname(cfile)); tmp=os.path.join(d,f"_ss_{name}.v")
    open(tmp,"w",encoding="utf-8").write("\n".join(new)+"\n")
    try:
        r=subprocess.run(["coqc"]+cov.FLAGS+[os.path.relpath(tmp,cov.COMPCERT)],
                         cwd=cov.COMPCERT,capture_output=True,text=True,timeout=90)
        out=r.stdout
    except subprocess.TimeoutExpired:
        out=""
    finally:
        for j in os.listdir(d):
            if j.startswith(f"_ss_{name}") or j.startswith(f"._ss_{name}"):
                try: os.remove(os.path.join(d,j))
                except: pass
    # 마커로 분리: @@G{k}@@ = goal, @@P{k}@@ = proof term. parts=[pre,'G','0',txt,...]
    parts=re.split(r'@@([GP])(\d+)@@', out)
    goal={}; pterm={}
    for i in range(1,len(parts)-2,3):
        kind=parts[i]; k=int(parts[i+1]); txt=parts[i+2]
        txt=re.split(r'\nError', txt)[0].strip()
        (goal if kind=="G" else pterm)[k]=txt
    res=[]
    for k,s in enumerate(steps,1):
        res.append({"tac":s.strip(), "state":goal.get(k,""), "proof":pterm.get(k,"")})
    return {"initial":goal.get(0,""), "initial_proof":pterm.get(0,""), "steps":res}

def build_all():
    ROWS=json.load(open("/tmp/claude-0/-app-coq-modeling/6331508b-8918-46d1-8fc8-94a923df1143/scratchpad/suffix_rows.json"))
    out={}
    for idx,name,tfile,nb in ROWS:
        rec={}
        if name and name!="None":
            t0=time.time(); rec["t"]=step_states(tfile,name); print(f"  idx={idx} t={name} ({time.time()-t0:.0f}s)",flush=True)
        nn=nb.get("cname")
        if nn and nn!="None":
            t0=time.time(); rec["n"]=step_states(nb["cfile"],nn); print(f"  idx={idx} n={nn} ({time.time()-t0:.0f}s)",flush=True)
        out[str(idx)]=rec
    dst=os.path.join(HERE,"..","results","compcert_report","step_states.json")
    json.dump(out, open(dst,"w"), ensure_ascii=False)
    print("SAVED", dst, round(os.path.getsize(dst)/1024),"KB")

if __name__=="__main__":
    import sys
    if "all" in sys.argv:
        build_all()
    else:
        for cf,nm in [("common/Values.v","divlu_one"),("common/Values.v","divu_one")]:
            print("="*40, nm); r=step_states(cf,nm)
            for i,s in enumerate(r["steps"]): print(f"  step{i+1}: {s['tac'][:50]} -> {s['state'][:90]}")
