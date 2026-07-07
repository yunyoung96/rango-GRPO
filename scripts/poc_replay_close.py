#!/usr/bin/env python3
"""
Iter 5: prefix-replay + 자동화 tail.
σ-proof 를 reach-k(첫 발산 직전)까지 replay 한 뒤, 남은 goal 을 '일반 자동화'로 닫아본다.
oracle(정답 증명) 없이 방법 B-lite 가 몇 건을 실제로 Qed 하는지 측정.
  closer 후보: eauto / lia / auto / congruence / 조합.
전제: poc_prefix_reach.json (Iter3 산출) 존재.
"""
import subprocess, os, re, json
import importlib.util
spec=importlib.util.spec_from_file_location("cov","scripts/poc_coverage.py"); cov=importlib.util.module_from_spec(spec); spec.loader.exec_module(cov)

def steps(b): return [s.strip() for s in re.split(r'(?<=\.)(?=\s|$)',b) if s.strip()]

CLOSERS = [
    "eauto.", "lia.", "auto.", "congruence.", "reflexivity.",
    "eauto with coqlib.", "intuition eauto.", "eauto; lia.",
    "auto; lia; eauto.", "omega.", "eauto 8.", "now eauto.",
]

def try_close(tfile, tname, prefix_steps):
    lines=cov.read(tfile); loc=cov.find_lemma(lines,tname)
    if not loc: return None
    start,proof,qed=loc; stack=cov.open_sections_at(lines,start)
    d=os.path.join(cov.COMPCERT, os.path.dirname(tfile))
    for closer in CLOSERS:
        body=" ".join(prefix_steps)+" all: "+closer
        new=lines[:proof+1]+[body]+[lines[qed]]+[f"End {s}." for s in reversed(stack)]
        tmp=os.path.join(d, f"_close_{tname}.v")
        open(tmp,"w",encoding="utf-8").write("\n".join(new)+"\n")
        try:
            r=subprocess.run(["coqc"]+cov.FLAGS+[os.path.relpath(tmp,cov.COMPCERT)],
                             cwd=cov.COMPCERT, capture_output=True, text=True, timeout=90)
            ok=r.returncode==0
        except subprocess.TimeoutExpired: ok=False
        finally:
            for junk in os.listdir(d):
                if junk.startswith(f"_close_{tname}") or junk.startswith(f".{'_close_'+tname}"):
                    try: os.remove(os.path.join(d,junk))
                    except: pass
        if ok: return closer
    return None

def main():
    reach=json.load(open("results/compcert_report/poc_prefix_reach.json"))
    same={r[2]:r for r in cov.ROWS}  # by target file? need mapping; rebuild by idx
    rows_by_idx={r[0]:r for r in cov.ROWS}
    closed=[]
    print("# Iter5: prefix-replay(k) + 자동화 tail 로 Qed 시도\n")
    for idx,name,nname,k,n in reach:
        if k<=0 or k>=n:   # 첫스텝실패(형제아님) 또는 이미 전량통과는 스킵
            continue
        row=rows_by_idx.get(idx)
        if not row: continue
        tfile=row[2]; nfile=row[3]['cfile']; nn=row[3]['cname']
        tl=cov.read(tfile); nl=cov.read(nfile)
        tloc=cov.find_lemma(tl,name); nloc=cov.find_lemma(nl,nn)
        if not tloc or not nloc: continue
        ns=cov.statement_text(nl,nloc[0],nloc[1]); ts=cov.statement_text(tl,tloc[0],tloc[1])
        sig=cov.derive_sigma(ns,ts)
        allsteps=steps(cov.apply_sigma("\n".join(nl[nloc[1]+1:nloc[2]]),sig))
        got=try_close(tfile,name,allsteps[:k])
        tag = f"CLOSED ✅ via `{got}`" if got else "not closed"
        print(f"  idx={idx:<5} {name:<30} reach {k}/{n} → {tag}")
        if got: closed.append((idx,name,k,n,got))
    print(f"\n# prefix-replay + 자동화로 추가 Qed: {len(closed)}건")
    json.dump(closed, open("results/compcert_report/poc_replay_close.json","w"), ensure_ascii=False, indent=1)

if __name__=="__main__":
    main()
