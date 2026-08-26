#!/usr/bin/env python3
"""`apply L with X` 의 X 가 **증명**인가 **데이터**인가 — CompCert 실측 (forms 문서 §3.5).

`with (N := …)` 의 N 은 lemma 의 **N 번째 전제**를 가리키고 거기 들어가는 것은
증명이다. 그 증명이 가설(H1)인지 다른 lemma(Rle_refl x)인지 정의인지를 가른다 —
"두 lemma 를 동시에 떠올려야 하는" 형태가 얼마나 되는지가 v10 에 직접 걸린다.

사용: python3 scripts/count_with_args.py
"""
import re,sys,sqlite3,collections,glob,pathlib
KIND={}
c=sqlite3.connect("raw-data/coqstoq-test/coqstoq-test-sentences.db"); c.execute("PRAGMA query_only=1")
D=re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?(Lemma|Theorem|Corollary|Remark|Proposition|Definition|Fixpoint|Inductive|Record|Instance|Axiom|Parameter)\s+([A-Za-z_][\w']*)")
for (t,) in c.execute("SELECT text FROM sentence"):
    m=D.match(t or "")
    if m: KIND.setdefault(m.group(2), m.group(1))
PROOF={"Lemma","Theorem","Corollary","Remark","Proposition","Axiom"}
files=[f for f in sorted(glob.glob("raw-data/coqstoq-test/repos/**/*.v",recursive=True)) if "compcert" in f.lower()]
WITH=re.compile(r"(?m)^[ \t]*(?:now |try |repeat )?(e?apply|e?rewrite)\s+([A-Za-z_][\w'.]*)\s+with\s+([^.]*)\.")
NUM =re.compile(r"\(\s*(\d+)\s*:=\s*([A-Za-z_][\w'.]*)")
IDENT=re.compile(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*")
S=collections.Counter(); EX=collections.defaultdict(list)
for f in files[:400]:
    try: txt=pathlib.Path(f).read_text(errors="ignore")
    except Exception: continue
    txt=re.sub(r"\(\*.*?\*\)","",txt,flags=re.S)
    for m in WITH.finditer(txt):
        head,L,arg=m.group(1),m.group(2),m.group(3)
        S[f"{head} … with"]+=1
        for nm in NUM.finditer(arg):
            k=KIND.get(nm.group(2).split(".")[-1])
            key=f"{head} with ({nm.group(1)} := {'증명lemma' if k in PROOF else ('가설/지역' if k is None else k)})"
            S[key]+=1
            if len(EX[key])<3: EX[key].append(" ".join(m.group(0).split())[:100])
        for i in IDENT.finditer(arg):
            n=i.group(0)
            if n in ("with","in","at","by","as") or len(n)<=2: continue
            k=KIND.get(n.split(".")[-1])
            if k in PROOF:
                S[f"{head} with … <증명 lemma {n}>"]+=1
                key=f"★ {head} L1 with L2 (둘 다 증명)"
                S[key]+=1
                if len(EX[key])<5: EX[key].append((" ".join(m.group(0).split())[:100],L,n))
                break
            elif k: S[f"{head} with … <{k}>"]+=1; break
print("■ `with` 인자의 정체")
for k,v in sorted(S.items(), key=lambda x:-x[1])[:16]:
    print(f"   {k:46s} {v:5,}")
print("\n■ ★ apply L1 with L2 — 둘 다 증명 lemma 인 사례")
for t,L,n in EX.get("★ apply L1 with L2 (둘 다 증명)",[])[:5]: print(f"   {t}\n      L1={L}  L2={n}")
for t,L,n in EX.get("★ rewrite L1 with L2 (둘 다 증명)",[])[:3]: print(f"   {t}\n      L1={L}  L2={n}")
print("\n■ (N := H) 숫자 형태")
for k in sorted(S):
    if ":=" in k and "with (" in k:
        print(f"   {k:46s} {S[k]:4,}")
        for e in EX[k][:2]: print(f"        {e}")
