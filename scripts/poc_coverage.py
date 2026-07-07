#!/usr/bin/env python3
"""
PoC 커버리지: §6 부록의 '같은 파일 형제쌍'에 대해, 케이스별 수작업 없이
**자동으로 σ를 유도**(두 정리의 문장 anti-unification)한 뒤 형제 증명을
replay 해서 몇 %가 그대로 컴파일되는지 측정한다.

σ 유도(완전 자동):
  1. neighbor/target 두 '문장'을 토큰화.
  2. difflib 로 정렬, 서로 다른(replace) 위치의 토큰쌍 (neigh↦targ) 수집.
  3. 이를 stem 치환으로 neighbor '증명' 전체에 적용 (긴 토큰 우선, placeholder 로 재매칭 방지).
  4. 변환된 증명을 target 자리에 끼워 coqc.

이 실험이 재는 것 = "방법 A(copy-and-rename replay) 원샷"으로 닫히는 비율.
(divlu 처럼 증명 전용 심볼 보정이 더 필요한 건 여기서 FAIL 로 잡히며, 그게 방법 B 몫.)
"""
import subprocess, re, os, time, json, difflib, sys

COMPCERT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "CoqStoq", "test-repos", "compcert"))
FLAGS = ["-R","lib","compcert.lib","-R","common","compcert.common","-R","x86_64","compcert.x86_64",
         "-R","x86","compcert.x86","-R","backend","compcert.backend","-R","cfrontend","compcert.cfrontend",
         "-R","driver","compcert.driver","-R","export","compcert.export","-R","cparser","compcert.cparser",
         "-R","flocq","Flocq","-R","MenhirLib","MenhirLib"]
ROWS = json.load(open(os.path.join(os.path.dirname(__file__), "..",
        "..","..","tmp","claude-0","-app-coq-modeling",
        "6331508b-8918-46d1-8fc8-94a923df1143","scratchpad","suffix_rows.json"))) \
       if False else json.load(open("/tmp/claude-0/-app-coq-modeling/6331508b-8918-46d1-8fc8-94a923df1143/scratchpad/suffix_rows.json"))

def read(path):
    with open(os.path.join(COMPCERT, path), encoding="utf-8") as f:
        return f.read().split("\n")

def find_lemma(lines, name):
    """returns (start, proof_idx, qed_idx) or None"""
    pat = re.compile(rf"\s*(Theorem|Lemma|Corollary|Remark|Fact|Proposition|Property)\s+{re.escape(name)}\b")
    starts = [i for i,l in enumerate(lines) if pat.match(l)]
    for start in starts:
        proof = next((i for i in range(start, min(start+40,len(lines))) if lines[i].strip().startswith("Proof")), None)
        if proof is None: continue
        qed = next((i for i in range(proof, len(lines)) if lines[i].strip().rstrip() in ("Qed.","Defined.")), None)
        if qed is None: continue
        return start, proof, qed
    return None

def statement_text(lines, start, proof):
    return " ".join(l.strip() for l in lines[start:proof])

def open_sections_at(lines, upto):
    """열려있는 Section/Module 블록 이름 스택. (Module ... := ... 한줄정의는 제외)"""
    stack=[]
    for i in range(upto):
        m=re.match(r"\s*(?:Section|Module(?:\s+Import)?)\s+([A-Za-z0-9_']+)\s*\.\s*$", lines[i])
        if m and ":=" not in lines[i] and "Module Type" not in lines[i]:
            stack.append(m.group(1)); continue
        m=re.match(r"\s*End\s+([A-Za-z0-9_']+)\.", lines[i])
        if m and stack and stack[-1]==m.group(1): stack.pop()
    return stack

TOK = re.compile(r"[A-Za-z_][A-Za-z0-9_'.]*|[0-9]+")
def tokens(s): return TOK.findall(s)

# Coq tactic/vernac 키워드 — σ 로 절대 건드리면 안 됨 (오염 방지)
KEYWORDS = set("""intros intro destruct induction inversion apply eapply rewrite erewrite
unfold simpl fold red split exists eexists assert generalize exploit constructor econstructor
auto eauto lia omega ring congruence discriminate reflexivity trivial assumption subst
monadInv inv case elim clear revert set pose remember specialize contradiction tauto intuition
left right now try repeat first solve by with in as eqn cut transitivity symmetry f_equal
Proof Qed Defined forall fun match end Type Prop True False Some None nil cons if then else
FuncInv TrivialExists Simplifs decEq InvBooleans""".split())

def derive_sigma(nb_stmt, tg_stmt):
    a, b = tokens(nb_stmt), tokens(tg_stmt)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    pairs=[]
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag=="replace":
            na, nb_ = a[i1:i2], b[j1:j2]
            for x,y in zip(na, nb_):     # 길이 다르면 앞부분만 (보수적)
                if x==y or not x or not y: continue
                if len(x)<3 or x in KEYWORDS or y in KEYWORDS: continue   # 짧은/키워드 stem 배제
                if not re.search(r"[A-Za-z]", x): continue                # 숫자만인 stem 배제(32/64는 살림? -> len>=3 조건에 안 걸림)
                pairs.append((x,y))
    seen=set(); uniq=[]
    for x,y in pairs:
        if (x,y) in seen: continue
        seen.add((x,y)); uniq.append((x,y))
    uniq.sort(key=lambda p:-len(p[0]))
    return uniq

def apply_sigma(text, sigma):
    # 토큰 단위로만 치환. 키워드 토큰은 보호. 한 토큰당 최장 stem 1회만 적용.
    def repl(m):
        tok=m.group(0)
        if tok in KEYWORDS: return tok
        for a,b in sigma:            # 긴 stem 우선
            if a in tok: return tok.replace(a,b)
        return tok
    return TOK.sub(repl, text)

def _distinctive(a):
    """substring 치환해도 안전할 만큼 변별적인 stem 인가 (짧은 단일세그먼트 소문자는 위험)."""
    return ('_' in a) or ('.' in a) or len(a)>=5 or any(c.isupper() for c in a)

def apply_sigma_seg(text, sigma):
    """하이브리드 치환: distinctive 키(`compare_ints`,`Int.`,`shrlu`)는 substring 전파,
    짧은 단일세그먼트 소문자 키(`int`,`sub`)는 *전체 세그먼트* 일치 시에만 치환.
    → `compare_ints`→`compare_longs` 는 `compare_ints_spec` 까지 전파하되
      `int`→`int64` 는 `intros` 를 오염시키지 않음."""
    smap={a:b for a,b in sigma}
    subs=sorted([(a,b) for a,b in sigma if _distinctive(a)], key=lambda p:-len(p[0]))
    segp={a:b for a,b in sigma if not _distinctive(a)}
    def repl(m):
        tok=m.group(0)
        if tok in KEYWORDS: return tok
        if tok in smap: return smap[tok]              # 토큰 전체 정확일치 우선
        for a,b in subs:                              # distinctive substring
            if a in tok: tok=tok.replace(a,b); break
        if segp:                                      # 짧은 stem 은 세그먼트 단위만
            segs=re.split(r'([._])', tok); ch=False
            for i,s in enumerate(segs):
                if s in segp: segs[i]=segp[s]; ch=True
            if ch: tok="".join(segs)
        return tok
    return TOK.sub(repl, text)

def compile_target(tgt_file, tgt_name, new_body):
    lines = read(tgt_file)
    loc = find_lemma(lines, tgt_name)
    if loc is None: return None, "target lemma not locatable", 0
    start, proof, qed = loc
    stack = open_sections_at(lines, start)
    new = lines[:proof+1] + [new_body] + [lines[qed]]
    for sec in reversed(stack):
        new.append(f"End {sec}.")
    text = "\n".join(new)+"\n"
    d = os.path.join(COMPCERT, os.path.dirname(tgt_file))
    tmp = os.path.join(d, f"_cov_{tgt_name}.v")
    with open(tmp,"w",encoding="utf-8") as f: f.write(text)
    try:
        t0=time.time()
        r=subprocess.run(["coqc"]+FLAGS+[os.path.relpath(tmp,COMPCERT)],
                         cwd=COMPCERT, capture_output=True, text=True, timeout=45)
        dt=time.time()-t0
        if r.returncode==0: return True, "", dt
        out=r.stdout+r.stderr
        m=re.search(r"Error:?\s*(.*?)(?:\n\n|\Z)", out, re.S)
        msg=(m.group(1) if m else out).strip().replace("\n"," ")
        return False, re.sub(r"\s+"," ",msg)[:160], dt
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", 120
    finally:
        for junk in os.listdir(d):
            if junk.startswith(f"_cov_{tgt_name}") or junk.startswith(f".{'_cov_'+tgt_name}"):
                try: os.remove(os.path.join(d,junk))
                except: pass

def main():
    same=[r for r in ROWS if r[2]==r[3]['cfile'] and r[1]!='None']
    print(f"# 같은-파일 형제쌍 {len(same)}건에 대해 자동 σ-replay 컴파일 테스트\n")
    results=[]
    for idx,name,tfile,b in same:
        nfile=b['cfile']; nname=b['cname']
        tl=read(tfile); nl=read(nfile)
        tloc=find_lemma(tl,name); nloc=find_lemma(nl,nname)
        if not tloc or not nloc:
            print(f"  idx={idx:<4} {name:<34} SKIP (위치 못 찾음)");
            results.append((idx,name,nname,"SKIP",0,"")); continue
        nb_stmt=statement_text(nl,nloc[0],nloc[1]); tg_stmt=statement_text(tl,tloc[0],tloc[1])
        nb_body="\n".join(nl[nloc[1]+1:nloc[2]])
        sigma=derive_sigma(nb_stmt,tg_stmt)
        cand=apply_sigma(nb_body,sigma)
        ok,err,dt=compile_target(tfile,name,cand)
        tag = "PASS ✅" if ok else ("SKIP" if ok is None else "FAIL ❌")
        results.append((idx,name,nname,tag,dt,err))
        print(f"  idx={idx:<4} {name:<34} ← {nname:<30} {tag} ({dt:.1f}s) |σ|={len(sigma)}")
        if not ok and err: print(f"        └ {err}")
    npass=sum(1 for r in results if r[3].startswith("PASS"))
    ntot =sum(1 for r in results if r[3] in ("PASS ✅","FAIL ❌"))
    print(f"\n# 자동 σ-replay 원샷 커버리지: {npass}/{ntot} = {100*npass/max(ntot,1):.0f}%  (SKIP {len(results)-ntot} 제외)")
    json.dump(results, open(os.path.join(os.path.dirname(__file__),"..","results","compcert_report","poc_coverage.json"),"w"), ensure_ascii=False, indent=1)

if __name__=="__main__":
    main()
