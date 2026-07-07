#!/usr/bin/env python3
"""
§6 부록 80건 각각에 대해 대상/이웃 정리의 실제 Coq 코드를 추출해
접기/펴기(<details>) toggle 블록으로 생성, suffix_transplant_analysis.md 에 §6.1 로 추가.
사용자가 표만 보지 않고 코드까지 바로 대조 확인할 수 있게.
"""
import json, os, re, html
import importlib.util
HERE=os.path.dirname(__file__)
spec=importlib.util.spec_from_file_location("cov", os.path.join(HERE,"poc_coverage.py"))
cov=importlib.util.module_from_spec(spec); spec.loader.exec_module(cov)

ROWS=json.load(open("/tmp/claude-0/-app-coq-modeling/6331508b-8918-46d1-8fc8-94a923df1143/scratchpad/suffix_rows.json"))
MD=os.path.join(HERE,"..","results","compcert_report","suffix_transplant_analysis.md")

# 이식(composed) 결과: idx -> status (PASS/STUCK/NOFIX/...). rango 는 이 부록 정의상 전부 실패(❌).
_CJ=os.path.join(HERE,"..","results","compcert_report","composed_final_merged.json")
COMPOSED=json.load(open(_CJ)) if os.path.exists(_CJ) else {}
def status_badge(idx):
    """rango 실패(❌ 고정) + 우리 이식 결과 배지."""
    rango="rango ❌ 실패"
    v=COMPOSED.get(str(idx))
    if not v: return f"{rango} · 이식 —(미평가)"
    st=v[0]; tail=(v[2] if len(v)>2 else "")
    m=re.search(r"(\d+)/(\d+)", tail or "")
    reach=f" {m.group(0)}" if m else ""
    label={"PASS":"이식 ✅ 종결","STUCK":f"이식 ◑ 부분{reach}","NOFIX":"이식 ✗ 실패",
           "NOSTATE":"이식 ✗ 상태추출불가","SKIP_BIG":"이식 —(거대증명 제외)"}.get(st, f"이식 {st}")
    return f"{rango} · {label}"

def lemma_code(cfile, name, maxlines=90):
    """cfile 의 name 정리 코드(정리 시작줄~Qed) 추출. 실패 시 None."""
    if not name or name=="None": return None
    try: lines=cov.read(cfile)
    except Exception: return None
    loc=cov.find_lemma(lines, name)
    if not loc: return None
    start,proof,qed=loc
    # 정리 직전 주석 한 줄이 있으면 포함(맥락)
    s=start
    if s>0 and lines[s-1].strip().startswith("(*") and lines[s-1].strip().endswith("*)"):
        s=s-1
    body=lines[s:qed+1]
    if len(body)>maxlines:
        body=body[:maxlines]+[f"  (* ... {len(lines[s:qed+1])-maxlines} 줄 생략 ... *)", lines[qed]]
    return "\n".join(body)

KW=set("""Theorem Lemma Corollary Remark Fact Proposition Property Definition Fixpoint
Inductive CoInductive Proof Qed Defined Admitted forall exists fun match with end let in if then
else fix cofix Type Prop Set return as struct Ltac Section End Module Import Notation Local""".split())
TAC=set("""intros intro destruct induction inversion apply eapply rewrite erewrite unfold simpl
fold red split eexists assert generalize exploit constructor econstructor auto eauto lia omega ring
congruence discriminate reflexivity trivial assumption subst monadInv inv case elim clear revert set
pose remember specialize contradiction tauto intuition left right try repeat first solve by cut
transitivity symmetry f_equal replace change rename exact refine cbn cbv compute now decEq FuncInv
InvBooleans TrivialExists Simplifs""".split())
C_KW="#8250df"; C_TAC="#0969da"; C_CMT="#6a9955"
PRE_STYLE=("margin:0;padding:8px 10px;background:rgba(128,128,128,.10);border-radius:6px;"
           "overflow-x:auto;font-size:12px;line-height:1.4")

def highlight(code):
    """Coq 코드에 인라인 색상 span. (주석 보호→이스케이프→키워드/tactic 색칠→주석 복원)"""
    cmts=[]
    def stash(m): cmts.append(m.group(0)); return f"\x00{len(cmts)-1}\x00"
    code=re.sub(r"\(\*.*?\*\)", stash, code, flags=re.S)
    esc=html.escape(code)
    def wrap(m):
        w=m.group(0)
        if w in KW:  return f'<span style="color:{C_KW}">{w}</span>'
        if w in TAC: return f'<span style="color:{C_TAC}">{w}</span>'
        return w
    esc=re.sub(r"[A-Za-z_][A-Za-z0-9_']*", wrap, esc)
    esc=re.sub(r"\x00(\d+)\x00",
               lambda m:f'<span style="color:{C_CMT}">{html.escape(cmts[int(m.group(1))])}</span>', esc)
    return esc

def _pre(code):
    """Coq 코드를 색칠된 HTML <pre> 로. 빈 줄 제거(마크다운 HTML블록이 빈줄에서 끊기는 것 방지)."""
    if not code: return f'<pre style="{PRE_STYLE}"><code>(코드 추출 실패)</code></pre>'
    lines=[l for l in code.split("\n") if l.strip()!=""]
    return f'<pre style="{PRE_STYLE}"><code>'+highlight("\n".join(lines))+"</code></pre>"

def block(idx, name, tfile, nb):
    nname=nb["cname"]; nfile=nb["cfile"]
    suf=nb.get("suf_len","?"); fm=nb.get("full_match","?")
    name=name or "None"; nname=nname or "None"
    tcode=lemma_code(tfile, name)
    ncode=lemma_code(nfile, nname)
    head=(f'<summary><b>idx {idx}</b> · <code>{name}</code> ↔ <code>{nname}</code> · '
          f'{tfile} · suffix {suf} / full-match {fm} · <b>{status_badge(idx)}</b></summary>')
    # 좌우 2열(대상 | 이웃) HTML 표. 표 안엔 빈 줄이 없어야 함(한 줄로 이어붙임).
    tbl=("<table><thead><tr>"
         f"<th align=\"left\">대상 <code>{html.escape(name)}</code> — <sub>{html.escape(tfile)}</sub></th>"
         f"<th align=\"left\">이웃 <code>{html.escape(nname)}</code> — <sub>{html.escape(nfile)}</sub></th>"
         "</tr></thead><tbody><tr>"
         f"<td valign=\"top\">{_pre(tcode)}</td>"
         f"<td valign=\"top\">{_pre(ncode)}</td>"
         "</tr></tbody></table>")
    return f"<details>\n{head}\n{tbl}\n</details>\n"

def main():
    # 표 순서(suffix 내림차순 근사)와 무관하게 ROWS 순서대로
    blocks=[block(idx,name,tfile,nb) for idx,name,tfile,nb in ROWS]
    ok=sum(1 for b in blocks if "코드 추출 실패" not in b or b.count("코드 추출 실패")<2)
    section=("\n\n## 6.1 부록 코드 대조 (접기/펴기)\n\n"
             "> 아래 각 항목을 클릭하면 대상 정리와 이웃 정리의 **실제 Coq 코드**가 펼쳐진다.\n"
             "> (긴 증명은 90줄에서 잘림). 표(§6)의 80건과 1:1 대응.\n\n"
             + "\n".join(blocks) + "\n")
    txt=open(MD, encoding="utf-8").read()
    # §6.1 구간만 교체(§6.2 이하 보존)
    after=""
    if "## 6.2" in txt:
        after="\n\n"+txt[txt.index("## 6.2"):].rstrip()+"\n"
    if "## 6.1 부록 코드 대조" in txt:
        txt=txt[:txt.index("## 6.1 부록 코드 대조")].rstrip()+"\n"
    open(MD,"w",encoding="utf-8").write(txt.rstrip()+section+after)
    print(f"완료: {len(blocks)}개 toggle 블록 추가. 코드추출 성공(양쪽) 근사: {sum(1 for b in blocks if b.count('추출 실패')==0)}")

if __name__=="__main__":
    main()
