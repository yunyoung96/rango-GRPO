#!/usr/bin/env python3
"""인터랙티브 Artifact 용 데이터(JSON) 생성 — 80건의 코드/막힌지점/메타를 하이라이트해 임베드."""
import json, os, re, html, importlib.util
HERE=os.path.dirname(__file__)
def L(m,p):
    s=importlib.util.spec_from_file_location(m,os.path.join(HERE,p)); x=importlib.util.module_from_spec(s); s.loader.exec_module(x); return x
ga=L("ga","gen_appendix_code.py")
gs=L("gs","gen_stuck_section.py")

# 클래스 기반 하이라이트(테마별 CSS 로 색 제어)
def hl(code, maxlines=60):
    if not code: return ""
    lines=[l for l in code.split("\n") if l.strip()!=""][:maxlines]
    code="\n".join(lines)
    cmts=[]
    code=re.sub(r"\(\*.*?\*\)", lambda m:(cmts.append(m.group(0)),f"\x00{len(cmts)-1}\x00")[1], code, flags=re.S)
    esc=html.escape(code)
    def w(m):
        t=m.group(0)
        if t in ga.KW:  return f'<span class="kw">{t}</span>'
        if t in ga.TAC: return f'<span class="tac">{t}</span>'
        return t
    esc=re.sub(r"[A-Za-z_][A-Za-z0-9_']*", w, esc)
    esc=re.sub(r"\x00(\d+)\x00", lambda m:f'<span class="cmt">{html.escape(cmts[int(m.group(1))])}</span>', esc)
    return esc

def avail_key(tfile,tL,nfile,nL):
    if tfile==nfile and tL and nL: return "avail" if nL<tL else "later"
    return "cross"

_SS=os.path.join(HERE,"..","results","compcert_report","step_states.json")
STEP=json.load(open(_SS)) if os.path.exists(_SS) else {}
def hl_trace(rec):
    """step_states 레코드를 하이라이트해 임베드용으로."""
    if not rec: return None
    return {"init":hl(rec.get("initial","")),
            "steps":[{"tac":s["tac"],"st":hl(s.get("state",""))} for s in rec.get("steps",[])]}

def main():
    items=[]
    for idx,name,tfile,nb in ga.ROWS:
        ss=STEP.get(str(idx),{})
        name=name or "None"; nname=nb["cname"] or "None"; nfile=nb["cfile"]
        tL=ga.line_of(tfile,name); nL=ga.line_of(nfile,nname)
        e=gs.extract(idx) or {}
        v=ga.COMPOSED.get(str(idx))
        cst=v[0] if v else "NOEVAL"
        creach=""
        if v and len(v)>2:
            m=re.search(r"\d+/\d+", v[2] or ""); creach=m.group(0) if m else ""
        items.append({
            "idx":idx, "t":name, "tf":tfile, "tL":tL or 0, "n":nname, "nf":nfile, "nL":nL or 0,
            "suf":nb.get("suf_len",0), "fm":nb.get("full_match",0),
            "avail":avail_key(tfile,tL,nfile,nL),
            "rsteps":int(e.get("steps") or 0), "rvalid":int(e.get("valid") or 0), "rend":e.get("end","?"),
            "cst":cst, "creach":creach,
            "tcode":hl(ga.lemma_code(tfile,name)),
            "ncode":hl(ga.lemma_code(nfile,nname)),
            "sgoal":hl(e.get("goal","")), "sproof":hl(e.get("proof","")),
            "tst":hl_trace(ss.get("t")), "nst":hl_trace(ss.get("n")),
        })
    out=os.path.join(HERE,"..","results","compcert_report","artifact_data.json")
    json.dump(items, open(out,"w"), ensure_ascii=False)
    # 요약
    from collections import Counter
    print("items:",len(items))
    print("avail:",Counter(i["avail"] for i in items))
    print("composed:",Counter(i["cst"] for i in items))
    print("size KB:", round(os.path.getsize(out)/1024))

if __name__=="__main__":
    main()
