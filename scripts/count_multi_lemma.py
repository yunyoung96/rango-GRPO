#!/usr/bin/env python3
"""한 tactic 이 lemma 를 **몇 개** 부르는가 — CompCert 실측 (forms 문서 §3.5).

선언이 실재하는 이름만 센다(sentence DB 대조). 가설·지역이름은 빼고 본다 —
`apply H` 를 "lemma 1개" 로 세면 분포가 통째로 어긋난다.

사용: python3 scripts/count_multi_lemma.py
"""
import json,re,sys,collections,glob
sys.path.insert(0,"src")
DECL=re.compile(r"^\s*(?:Local\s+|Global\s+|Program\s+)?(?:Lemma|Theorem|Definition|Corollary|Fixpoint|Inductive|Remark|Proposition|Instance|Record|Axiom)\s+([A-Za-z_][\w']*)")
def load_names():
    S=set()
    import sqlite3
    for db in ("raw-data/coqstoq-test/coqstoq-test-sentences.db",):
        c=sqlite3.connect(db); c.execute("PRAGMA query_only=1")
        for (t,) in c.execute("SELECT text FROM sentence"):
            m=DECL.match(t or "")
            if m: S.add(m.group(1))
    return S
NAMES=load_names()
print(f"선언 이름 {len(NAMES):,}개 로드")
HEAD=re.compile(r"^\s*(?:now\s+|try\s+|repeat\s+)?(e?apply|e?rewrite|setoid_rewrite)\b")
IDENT=re.compile(r"[A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*")
KW={"with","in","at","by","as","fun","forall","exists","let","match","end","if","then","else",
    "apply","eapply","rewrite","erewrite","setoid_rewrite","now","try","repeat","auto","eauto","lia","omega"}
def lemma_names(body):
    out=[]
    for m in IDENT.finditer(body):
        n=m.group(0)
        if n in KW or len(n)<=2: continue
        if n in NAMES or n.split(".")[-1] in NAMES: out.append(n)
    return out
C=collections.Counter(); FORM=collections.Counter(); EX=collections.defaultdict(list)
import pathlib
files=sorted(glob.glob("raw-data/coqstoq-test/repos/**/*.v",recursive=True))
files=[f for f in files if "compcert" in f.lower()]
print(f"CompCert .v {len(files)}개")
TAC=re.compile(r"(?m)^[ \t]*((?:now |try |repeat )?(?:e?apply|e?rewrite|setoid_rewrite)\b[^.]*\.)")
for f in files[:400]:
    try: txt=pathlib.Path(f).read_text(errors="ignore")
    except Exception: continue
    txt=re.sub(r"\(\*.*?\*\)","",txt,flags=re.S)
    for m in TAC.finditer(txt):
        t=" ".join(m.group(1).split())
        h=HEAD.match(t)
        if not h: continue
        head=h.group(1)
        body=t[h.end():]
        ns=lemma_names(body)
        u=list(dict.fromkeys(ns))
        C[f"{head} · lemma {min(len(u),3)}개"]+=1
        C[f"__{head}"]+=1
        if len(u)>=2:
            C["★ 여러 lemma"]+=1
            # 어떤 형태로 여러 개가 오나
            if re.search(r"\bwith\b",body) and not re.search(r":=",body): k="with <lemma>"
            elif re.search(r"\bwith\s*\(",body): k="with (x := …)"
            elif re.search(r"^\s*[^,]+,",body): k="쉼표 나열 L1, L2"
            elif re.search(r"\bin\b",body): k="in H (가설도 lemma명)"
            elif re.search(r"\(",body): k="괄호 적용 (L a b)"
            else: k="기타"
            FORM[f"{head} · {k}"]+=1
            if len(EX[f"{head} · {k}"])<4: EX[f"{head} · {k}"].append((t[:110],u[:4]))
print(f"\n■ tactic 호출 총 {sum(v for k,v in C.items() if k.startswith('__')):,}")
for h in ("apply","eapply","rewrite","erewrite","setoid_rewrite"):
    tot=C[f"__{h}"]
    if not tot: continue
    print(f"\n  {h}  ({tot:,}회)")
    for k in (0,1,2,3):
        v=C[f"{h} · lemma {k}개"]
        if v: print(f"     lemma {k}{'+' if k==3 else ''}개  {v:6,}  {v/tot*100:5.1f}%")
print(f"\n■ ★ 여러 lemma 를 쓰는 형태 (총 {C['★ 여러 lemma']:,})")
for k,v in FORM.most_common(12):
    print(f"   {k:34s} {v:5,}")
    for t,u in EX[k][:2]: print(f"        {t}\n           → {u}")
