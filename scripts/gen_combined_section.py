#!/usr/bin/env python3
"""§6.3 — §6.1(코드 대조)+§6.2(rango 막힌 지점)를 한 카드로 합친 통합 뷰.
한 항목에서: rango 막힌 goal + [대상 정답증명 | 이웃 형제증명] 2열 + rango 포기 직전 부분증명(중첩).
(스텝별 goal state 는 분량상 §6.1 에 유지 — 여기선 링크 안내만.)"""
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
    head=(f'<summary><b>idx {idx}</b> · <code>{name}</code> ↔ <code>{nname}</code> · '
          f'suffix {suf}/full {fm} · {av} · rango {e.get("steps","?")}회→<b>{e.get("end","?")}</b> · '
          f'<b>{ga.status_badge(idx)}</b></summary>')
    stuck=(f'<b>① rango 가 막힌 goal</b> — {e.get("steps","?")}회 tactic 시도(VALID {e.get("valid","?")}) 후 <b>{e.get("end","?")}</b>'
           f'{gs._pre_hl(e.get("goal",""))}') if e else ""
    codetbl=("<b>② 대상 정답 증명 ↔ 이웃 형제 증명(이식원)</b>"
             "<table><thead><tr>"
             f"<th align=\"left\">대상 <code>{html.escape(name)}</code> — <sub>{html.escape(tloc)}</sub></th>"
             f"<th align=\"left\">이웃(형제) <code>{html.escape(nname)}</code> — <sub>{html.escape(nloc)}</sub></th>"
             "</tr></thead><tbody><tr>"
             f"<td valign=\"top\">{ga._pre(tcode)}</td><td valign=\"top\">{ga._pre(ncode)}</td>"
             "</tr></tbody></table>")
    stuckproof=(f'<details><summary><b>③ rango 포기 직전 누적 부분증명</b> — 정답과 어긋나 여기서 정지</summary>\n'
                f'{gs._pre_hl(e.get("proof",""))}\n</details>') if e.get("proof") else ""
    note='<sub>· 스텝별 goal state(가설 포함, 2열)는 §6.1 동일 항목에 있음</sub>'
    return f"<details>\n{head}\n{stuck}\n{codetbl}\n{stuckproof}\n{note}\n</details>\n"

def main():
    ROWS=json.load(open("/tmp/claude-0/-app-coq-modeling/6331508b-8918-46d1-8fc8-94a923df1143/scratchpad/suffix_rows.json"))
    blocks=[block(idx,name,tfile,nb) for idx,name,tfile,nb in ROWS]
    section=("\n\n## 6.3 통합 뷰 — rango 막힌 지점 + 형제 증명 (접기/펴기)\n\n"
             "> §6.1(코드 대조)과 §6.2(rango 막힌 지점)를 **한 항목에 합침**. 각 케이스를 펼치면:\n"
             "> **① rango 가 막힌 goal** → **② 대상 정답증명 ↔ 이웃 형제증명(좌우)** → **③ rango 포기 직전 부분증명**(중첩 toggle).\n"
             "> \"target 이 어디서 막혔나\"와 \"이웃 증명이 어떻게 생겼나\"를 한눈에. 배지: rango❌ · 이식결과 · 이웃 available.\n\n"
             + "\n".join(blocks) + "\n")
    txt=open(MD,encoding="utf-8").read()
    if "## 6.3 통합 뷰" in txt:
        txt=txt[:txt.index("## 6.3 통합 뷰")].rstrip()+"\n"
    open(MD,"w",encoding="utf-8").write(txt.rstrip()+section)
    print(f"완료: §6.3 {len(blocks)}개 블록 추가.")

if __name__=="__main__":
    main()
