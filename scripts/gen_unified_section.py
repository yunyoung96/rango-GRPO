#!/usr/bin/env python3
"""§6.1/§6.2/§6.3 을 없애고 idx별 '하나의 통합 항목'으로 병합.
각 항목(펼치면): ① rango 막힌 goal → ② 대상 정답증명 | 이웃 형제증명(이식원) 2열
→ ③ rango 포기 직전 부분증명(중첩) → ④ 스텝별 goal state 2열(중첩)."""
import json, os, html, importlib.util
HERE=os.path.dirname(__file__)
def L(m,p):
    s=importlib.util.spec_from_file_location(m,os.path.join(HERE,p)); x=importlib.util.module_from_spec(s); s.loader.exec_module(x); return x
ga=L("ga","gen_appendix_code.py")
gs=L("gs","gen_stuck_section.py")
MD=os.path.join(HERE,"..","results","compcert_report","suffix_transplant_analysis.md")

def block(idx,name,tfile,nb):
    name=name or "None"; nname=nb.get("cname") or "None"; nfile=nb.get("cfile","")
    tL=ga.line_of(tfile,name); nL=ga.line_of(nfile,nname)
    tloc=f"{tfile}:L{tL}" if tL else tfile
    nloc=f"{nfile}:L{nL}" if nL else nfile
    av=ga.avail_mark(tfile,tL,nfile,nL)
    e=gs.extract(idx) or {}
    suf=nb.get("suf_len","?"); fm=nb.get("full_match","?")
    tcode=ga.lemma_code(tfile,name); ncode=ga.lemma_code(nfile,nname)
    ss=ga.STEPSTATES.get(str(idx),{})
    head=(f'<summary><b>idx {idx}</b> · <code>{name}</code> ↔ <code>{nname}</code> · '
          f'<code>{html.escape(tloc)}</code> ← <code>{html.escape(nloc)}</code> · suffix {suf}/full {fm} · '
          f'{av} · rango {e.get("steps","?")}회→<b>{e.get("end","?")}</b> · <b>{ga.status_badge(idx)}</b></summary>')
    stuck=(f'<b>① rango 가 막힌 goal</b> — {e.get("steps","?")}회 tactic 시도(VALID {e.get("valid","?")}) 후 <b>{e.get("end","?")}</b>'
           f'{gs._pre_hl(e.get("goal",""))}') if e else ""
    codetbl=("<b>② 대상 정답 증명 ↔ 이웃 형제 증명(이식원)</b>"
             "<table><thead><tr>"
             f"<th align=\"left\">대상 <code>{html.escape(name)}</code> — <sub>{html.escape(tloc)}</sub></th>"
             f"<th align=\"left\">이웃(형제) <code>{html.escape(nname)}</code> — <sub>{html.escape(nloc)}</sub></th>"
             "</tr></thead><tbody><tr>"
             f"<td valign=\"top\">{ga._pre(tcode)}</td><td valign=\"top\">{ga._pre(ncode)}</td>"
             "</tr></tbody></table>")
    stuckproof=(f'<details {ga.NEST_L2}><summary {ga.SUM_STYLE}><b>③ rango 포기 직전 누적 부분증명</b> — 정답과 어긋나 여기서 정지</summary>\n'
                f'{gs._pre_hl(e.get("proof",""))}\n</details>') if e.get("proof") else ""
    # ④ 스텝별 trace — 먼저 2열(대상|이웃)로 쪼개고, 각 열에서 tactic 나열(스텝마다 goal+proof term)
    steps=ga.trace_cols(ss.get("t"), ss.get("n"), html.escape(name), html.escape(nname)) if ss else ""
    steps4=steps.replace("스텝별 trace (대상 열 | 이웃 열)","④ 스텝별 trace (대상 열 | 이웃 열)") if steps else ""
    return f"<details {ga.NEST_L1}>\n{head}\n{stuck}\n{codetbl}\n{stuckproof}\n{steps4}\n</details>\n"

def main():
    ROWS=json.load(open("/tmp/claude-0/-app-coq-modeling/6331508b-8918-46d1-8fc8-94a923df1143/scratchpad/suffix_rows.json"))
    blocks=[block(idx,name,tfile,nb) for idx,name,tfile,nb in ROWS]
    section=("\n\n## 6.1 부록 상세 — 항목별 통합 (접기/펴기)\n\n"
             "> §6 표의 80건을 **idx 하나당 한 항목으로 통합**. 각 항목을 펼치면 순서대로:\n"
             "> **① rango 가 막힌 goal** → **② 대상 정답증명 ↔ 이웃 형제증명(이식원) 좌우 2열** →\n"
             "> **③ rango 포기 직전 부분증명**(중첩) → **④ 스텝별 trace**(먼저 대상|이웃 2열로 쪼개고,\n"
             "> 각 열 안에서 tactic 을 순서대로 나열 — 스텝 토글을 열면 그 시점 goal state + proof term.\n"
             "> 두 증명의 스텝 수가 달라 열 길이가 다를 수 있음).\n"
             "> \"target 이 어디서 막혔나\"와 \"이웃 증명·중간 상태가 어떻게 흐르나\"를 한 항목에서. \n"
             "> 헤더 배지: `파일:라인` · 이웃 available(✅앞/⚠️뒤/타파일) · `rango ❌` · 이식결과(✅/◑/✗/미평가).\n"
             "> 색상: <span style=\"color:#8250df\">키워드</span>·<span style=\"color:#0969da\">tactic</span>·<span style=\"color:#6a9955\">주석</span>.\n\n"
             + "\n".join(blocks) + "\n")
    txt=open(MD,encoding="utf-8").read()
    # §6.1/§6.2/§6.3 모두 제거하고 하나로 교체 — 첫 '## 6.1' 부터 파일 끝까지 잘라냄
    cut=None
    for mk in ["## 6.1","## 6.2","## 6.3"]:
        i=txt.find(mk)
        if i!=-1: cut=i if cut is None else min(cut,i)
    if cut is not None:
        txt=txt[:cut].rstrip()+"\n"
    open(MD,"w",encoding="utf-8").write(txt.rstrip()+section)
    print(f"완료: §6.1/6.2/6.3 → 통합 {len(blocks)}개 항목으로 병합.")

if __name__=="__main__":
    main()
