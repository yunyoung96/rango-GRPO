#!/usr/bin/env python3
"""
Iter 10: STUCK repair site 에서 실제 rango 모델 호출로 잔여 tactic 공급.

입력: Iter 11(state-align)이 STUCK 으로 남긴 케이스들(poc_state_align.json).
각 케이스는 reach k 까지 σ-transplant 로 도달했고, step[k] 가 genuine 발산(rename 아님).
여기서:
  1. reach k 지점의 target goal state 를 coqc `Show.` 로 추출.
  2. rango 모델(get_recs)에 (state, script) 주고 상위 n tactic 후보 받음.
  3. 각 후보로 step[k] 를 대체(또는 step[k] 앞에 삽입) → reach 가 전진하면 성공.
Iter 5(음성): 일반 자동화 tail 은 0/22. 여기선 "모델이 goal 을 보고 정확한 tactic 예측"을
검증한다. 성공 = 자동화로는 못 닫던 site 를 모델 1회 호출로 넘김.

GPU 필요. 다른 run 양보 위해 이 스크립트는 명시 실행할 때만 모델 로드.
"""
import os, sys, json, subprocess, re
HERE=os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE,"..","src"))
import importlib.util
def _load(mod,path):
    s=importlib.util.spec_from_file_location(mod,os.path.join(HERE,path))
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
cov=_load("cov","poc_coverage.py")
reach=_load("reach","poc_prefix_reach.py")
align=_load("align","poc_state_align.py")
mc=_load("mc","poc_model_call.py")

def clean_tac(t):
    t=t.strip()
    # 모델이 여러 줄/불필요 접두 낼 수 있음 — 첫 tactic 한 줄만, 마침표 보장
    if not t: return "idtac."
    if not t.endswith("."): t=t+"."
    return t

def clean_state(show_out):
    """coqc Show 출력에서 'N goal(s)' 헤더 제거 → 훈련 proof_state 포맷(hyps+====+goal)에 근접."""
    if not show_out: return show_out
    lines=show_out.split("\n")
    # 첫 'N goal' 줄 및 빈 줄 스킵
    i=0
    while i<len(lines) and (re.match(r"\s*\d+ goal", lines[i]) or not lines[i].strip()): i+=1
    return "\n".join(lines[i:]).strip()

def _advance(tfile,name,steps,k,tac):
    """steps[:k]+tac 가 컴파일되면(=tactic 적용성공) 전진. 전체 PASS 면 'PASS' 반환."""
    full=steps[:k]+[tac]+steps[k+1:]
    ok,_,_=cov.compile_target(tfile,name," ".join(full))
    if ok: return "PASS"
    # 전진(1스텝 이상)만이라도?
    adv=reach.compile_prefix(tfile,name,steps[:k]+[tac], k+1)
    if adv: return "ADV"
    # 대체 아닌 삽입도 시도
    ins=reach.compile_prefix(tfile,name,steps[:k]+[tac]+[steps[k]] if k<len(steps) else steps[:k]+[tac], k+1)
    return "ADV" if ins else "NO"

def repair_site(idx, name, tfile, nfile, nname, sigma, n_sugg=12, use_retrieval=True):
    """STUCK 케이스: reach 지점 state→모델→후보 시도. 후보당 1-2 coqc."""
    nl=cov.read(nfile); nloc=cov.find_lemma(nl,nname)
    nbr_body="\n".join(nl[nloc[1]+1:nloc[2]])
    steps=align.split_steps(cov.apply_sigma_seg(nbr_body, sigma))
    k,nt=reach.max_reach(tfile,name,steps)
    raw=align.show_state(tfile,name,steps,k,tag="_i10_")
    state=clean_state(raw)
    if not state:
        return {"idx":idx,"name":name,"status":"NOSTATE","reach":f"{k}/{nt}"}
    prefix=" ".join(steps[:k])
    # retrieval: 이웃(형제) 증명을 검색된 proof 로 제공 (rango 는 retrieval-augmented)
    proofs=[nbr_body] if use_retrieval else None
    sugg=mc.suggest(state, proof_script=prefix, n=n_sugg, proofs=proofs)
    failing=steps[k] if k<len(steps) else "(none)"
    tried=[]
    for tac,score in sugg:
        tac=clean_tac(tac)
        if tac in ("idtac.",): continue
        r=_advance(tfile,name,steps,k,tac)
        tried.append((tac,round(score,2),r))
        if r in ("PASS","ADV"):
            return {"idx":idx,"name":name,"status":"PASS" if r=="PASS" else "ADVANCED",
                    "reach_before":f"{k}/{nt}","failing_step":failing,
                    "model_tactic":tac,"score":round(score,2),"tried":tried}
    return {"idx":idx,"name":name,"status":"NOFIX","reach":f"{k}/{nt}",
            "failing_step":failing,"tried":tried[:6]}

def main():
    aj=os.path.join(HERE,"..","results","compcert_report","poc_state_align.json")
    data=json.load(open(aj)) if os.path.exists(aj) else []
    stuck=[r for r in data if r.get("status")=="STUCK"]
    def frac(r):
        t=r.get("trace",[]); s=t[-1]["reach"] if t else "0/1"
        try: k,n=s.split("/"); return int(k)/int(n)
        except: return 0
    stuck.sort(key=frac, reverse=True)   # reach 높은(=genuine site 하나만 남은) 순
    # suffix_rows 에서 nfile/nname 복구
    rows={r[0]:(r[2],r[3]['cfile'],r[3]['cname']) for r in cov.ROWS if r[1]!='None'}
    print(f"# Iter10: STUCK {len(stuck)}건에 모델 호출 (reach 높은 순)\n")
    out=[]
    for r in stuck:
        idx=r['idx'];
        if idx not in rows: continue
        tfile,nfile,nname=rows[idx]
        res=repair_site(idx,r['name'],tfile,nfile,nname,r['sigma'])
        print(f"  idx={idx:<5} {r['name']:<40} {res['status']}"
              f"  {res.get('reach_before','')}→{res.get('reach_after','')}"
              f"  {('['+res.get('model_tactic','')+']') if res.get('model_tactic') else ''}", flush=True)
        out.append(res)
    for j in os.listdir(os.path.join(cov.COMPCERT)):  # noop safety
        pass
    npass=sum(1 for r in out if r['status']=="PASS")
    nadv=sum(1 for r in out if r['status']=="ADVANCED")
    print(f"\n# 결과: PASS {npass} · ADVANCED {nadv} · NOFIX {sum(1 for r in out if r['status']=='NOFIX')}")
    json.dump(out, open(os.path.join(HERE,"..","results","compcert_report","poc_iter10_repair.json"),"w"),
              ensure_ascii=False, indent=1)

if __name__=="__main__":
    main()
