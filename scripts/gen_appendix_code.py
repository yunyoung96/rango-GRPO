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

_SSJ=os.path.join(HERE,"..","results","compcert_report","step_states.json")
STEPSTATES=json.load(open(_SSJ)) if os.path.exists(_SSJ) else {}

def _pre_state(raw):
    """goal state 텍스트 → 색칠된 <pre> (빈 줄 제거)."""
    lines=[l for l in (raw or "").split("\n") if l.strip()!=""]
    if not lines: return f'<pre style="{PRE_STYLE}"><code><span style="color:{C_CMT}">증명 종료 — no more goals</span></code></pre>'
    return f'<pre style="{PRE_STYLE}"><code>'+highlight("\n".join(lines))+"</code></pre>"

# 중첩 계층 시각화: 왼쪽 색상 레일 + 들여쓰기 (레벨별 색/굵기 차등). VS Code 미리보기·Artifact 에서 표시.
NEST_L1='style="margin:10px 0;border-left:4px solid rgba(70,110,240,.75);border-radius:0 10px 10px 0;padding:4px 0 4px 15px;background:rgba(70,110,240,.05)"'
NEST_L2='style="margin:7px 0;border-left:3px solid rgba(130,110,225,.55);border-radius:0 8px 8px 0;padding:3px 0 3px 13px;background:rgba(130,110,225,.045)"'
NEST_L3='style="margin:5px 0;border-left:2px solid rgba(90,150,120,.55);border-radius:0 7px 7px 0;padding:2px 0 2px 11px;background:rgba(90,150,120,.05)"'
SUM_STYLE='style="cursor:pointer"'

def _trace_items(rec):
    """한 정리의 스텝별 goal state 를 중첩 <details> 리스트로(레벨3 레일)."""
    if not rec or not rec.get("steps"): return "<i>(스텝 상태 추출 없음 — 파일/타임아웃)</i>"
    out=[f'<details {NEST_L3}><summary {SUM_STYLE}>0 · <i>초기 goal</i></summary>\n{_pre_state(rec.get("initial",""))}\n</details>']
    for i,s in enumerate(rec.get("steps",[]),1):
        out.append(f'<details {NEST_L3}><summary {SUM_STYLE}>{i} · <code>{html.escape(s["tac"])}</code></summary>\n{_pre_state(s.get("state",""))}\n</details>')
    return "".join(out)

PROOF_CAP=4000  # proof term 은 매우 길어질 수 있어 표시 상한(전체는 step_states.json)

def _pre_proof(raw):
    """proof term(Show Proof) → <pre>. 빈 줄 제거(마크다운 HTML블록 끊김 방지) + 너무 길면 소프트 캡."""
    txt="\n".join(l for l in (raw or "").split("\n") if l.strip()!="")
    if not txt:
        return f'<pre style="{PRE_STYLE}"><code><span style="color:{C_CMT}">— (proof term 없음)</span></code></pre>'
    note=""
    if len(txt)>PROOF_CAP:
        note=f' … (전체 {len(txt)}자 중 {PROOF_CAP}자 표시 — 전체는 step_states.json)'
        txt=txt[:PROOF_CAP]
    return f'<pre style="{PRE_STYLE}"><code>{html.escape(txt)}<span style="color:{C_CMT}">{note}</span></code></pre>'

def _step_toggle(k, tac, tval, nval, tlabel, nlabel, is_proof, init=False):
    """한 스텝 = 토글 1개. 열면 대상|이웃 2열. ★ 줄바꿈 없는 한 줄(마크다운 HTML블록 끊김 방지)."""
    lab=f'<i>{html.escape(tac)}</i>' if init else f'<code>{html.escape(tac)}</code>'
    cell=_pre_proof if is_proof else _pre_state
    return (f'<details {NEST_L3}><summary {SUM_STYLE}>{k} · {lab}</summary>'
            f'<table><thead><tr><th align="left">대상 <code>{tlabel}</code></th>'
            f'<th align="left">이웃 <code>{nlabel}</code></th></tr></thead>'
            f'<tbody><tr><td valign="top">{cell(tval)}</td>'
            f'<td valign="top">{cell(nval)}</td></tr></tbody></table></details>')

def _steps_2col(trec, nrec, tlabel, nlabel, field, initkey, title, is_proof):
    """스텝당 토글 1개(내부 대상|이웃 2열) 리스트. 레벨2 레일로 감쌈. 전부 한 줄(줄바꿈 없음)."""
    if not trec and not nrec: return ""
    ts=(trec or {}).get("steps",[]); ns=(nrec or {}).get("steps",[])
    kind="proof term" if is_proof else "goal"
    items=[_step_toggle(0, f"초기 {kind}", (trec or {}).get(initkey,""),
                        (nrec or {}).get(initkey,""), tlabel, nlabel, is_proof, init=True)]
    for i in range(max(len(ts),len(ns))):
        t=ts[i] if i<len(ts) else None; n=ns[i] if i<len(ns) else None
        tac=(t or n or {}).get("tac","")
        items.append(_step_toggle(i+1, tac, (t or {}).get(field,""),
                                  (n or {}).get(field,""), tlabel, nlabel, is_proof))
    return (f'<details {NEST_L2}><summary {SUM_STYLE}><b>{title}</b> — 스텝당 토글, 열면 대상|이웃 2열</summary>'
            + "".join(items) + "</details>")

def trace_table(trec, nrec, tlabel, nlabel):
    """④ 스텝별 goal state — 스텝당 토글1개+내부 2열."""
    return _steps_2col(trec, nrec, tlabel, nlabel, "state", "initial",
                       "스텝별 goal state (대상 | 이웃)", is_proof=False)

def trace_proof_table(trec, nrec, tlabel, nlabel):
    """⑤ 스텝별 proof term(Show Proof) — 스텝당 토글1개+내부 2열."""
    return _steps_2col(trec, nrec, tlabel, nlabel, "proof", "initial_proof",
                       "스텝별 proof term (대상 | 이웃)", is_proof=True)

def _col_step(k, tac, state, proof, init=False):
    """열 내부 한 스텝 토글: 열면 goal state + proof term 세로 나열. ★ 한 줄(HTML블록 끊김 방지)."""
    lab=f'<i>{html.escape(tac)}</i>' if init else f'<code>{html.escape(tac)}</code>'
    return (f'<details {NEST_L3}><summary {SUM_STYLE}>{k} · {lab}</summary>'
            f'<div><b>goal</b></div>{_pre_state(state)}'
            f'<div><b>proof term</b></div>{_pre_proof(proof)}</details>')

def _col_items(rec):
    """한 정리(=한 열)의 trace 전체: 0(초기)부터 tactic 순서대로, 스텝마다 goal+proof term."""
    if not rec or not rec.get("steps"): return "<i>(스텝 상태 추출 없음 — 파일/타임아웃)</i>"
    out=[_col_step(0, "초기", rec.get("initial",""), rec.get("initial_proof",""), init=True)]
    for i,s in enumerate(rec.get("steps",[]),1):
        out.append(_col_step(i, s.get("tac",""), s.get("state",""), s.get("proof","")))
    return "".join(out)

def trace_cols(trec, nrec, tlabel, nlabel):
    """스텝별 trace — 먼저 2열(대상|이웃)로 쪼개고, 각 열 안에서 tactic 나열.
    스텝 토글을 열면 그 시점 goal state + proof term. 열마다 스텝 수가 달라 길이가 다를 수 있음."""
    if not trec and not nrec: return ""
    tn=len((trec or {}).get("steps",[]) or []); nn=len((nrec or {}).get("steps",[]) or [])
    return (f'<details {NEST_L2}><summary {SUM_STYLE}><b>스텝별 trace (대상 열 | 이웃 열)</b>'
            f' — 열별 tactic 나열({tn} vs {nn}스텝), 스텝을 열면 goal+proof term</summary>'
            f'<table><thead><tr><th align="left">대상 <code>{tlabel}</code> — {tn}스텝</th>'
            f'<th align="left">이웃 <code>{nlabel}</code> — {nn}스텝</th></tr></thead>'
            f'<tbody><tr><td valign="top">{_col_items(trec)}</td>'
            f'<td valign="top">{_col_items(nrec)}</td></tr></tbody></table></details>')

def line_of(cfile, nm):
    if not nm or nm=="None": return None
    try: L=cov.read(cfile)
    except Exception: return None
    loc=cov.find_lemma(L,nm)
    return loc[0]+1 if loc else None

def avail_mark(tfile,tL,nfile,nL):
    """이웃이 rango 증명시점에 접근 가능한가. 같은파일: 앞이면 available. 타파일: 의존성 확인필요."""
    if tfile==nfile and tL and nL:
        return "이웃 available ✅" if nL<tL else "이웃 나중 ⚠️(rango 미접근)"
    return "타 파일(의존성 확인要)"

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
    tL=line_of(tfile,name); nL=line_of(nfile,nname)
    tloc=f"{tfile}:L{tL}" if tL else tfile
    nloc=f"{nfile}:L{nL}" if nL else nfile
    av=avail_mark(tfile,tL,nfile,nL)
    head=(f'<summary><b>idx {idx}</b> · <code>{name}</code> ↔ <code>{nname}</code> · '
          f'suffix {suf}/full {fm} · {av} · <b>{status_badge(idx)}</b></summary>')
    # 좌우 2열(대상 | 이웃) HTML 표. 표 안엔 빈 줄이 없어야 함(한 줄로 이어붙임).
    tbl=("<table><thead><tr>"
         f"<th align=\"left\">대상 <code>{html.escape(name)}</code> — <sub>{html.escape(tloc)}</sub></th>"
         f"<th align=\"left\">이웃 <code>{html.escape(nname)}</code> — <sub>{html.escape(nloc)}</sub></th>"
         "</tr></thead><tbody><tr>"
         f"<td valign=\"top\">{_pre(tcode)}</td>"
         f"<td valign=\"top\">{_pre(ncode)}</td>"
         "</tr></tbody></table>")
    ss=STEPSTATES.get(str(idx),{})
    tr=trace_table(ss.get("t"), ss.get("n"), html.escape(name), html.escape(nname)) if ss else ""
    return f"<details>\n{head}\n{tbl}\n{tr}\n</details>\n"

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
