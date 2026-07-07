#!/usr/bin/env python3
"""
§6 부록 80건 각각에 대해 대상/이웃 정리의 실제 Coq 코드를 추출해
접기/펴기(<details>) toggle 블록으로 생성, suffix_transplant_analysis.md 에 §6.1 로 추가.
사용자가 표만 보지 않고 코드까지 바로 대조 확인할 수 있게.
"""
import json, os, re
import importlib.util
HERE=os.path.dirname(__file__)
spec=importlib.util.spec_from_file_location("cov", os.path.join(HERE,"poc_coverage.py"))
cov=importlib.util.module_from_spec(spec); spec.loader.exec_module(cov)

ROWS=json.load(open("/tmp/claude-0/-app-coq-modeling/6331508b-8918-46d1-8fc8-94a923df1143/scratchpad/suffix_rows.json"))
MD=os.path.join(HERE,"..","results","compcert_report","suffix_transplant_analysis.md")

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

def block(idx, name, tfile, nb):
    nname=nb["cname"]; nfile=nb["cfile"]
    suf=nb.get("suf_len","?"); fm=nb.get("full_match","?")
    name=name or "None"; nname=nname or "None"
    tcode=lemma_code(tfile, name)
    ncode=lemma_code(nfile, nname)
    head=(f'<summary><b>idx {idx}</b> · <code>{name}</code> ↔ <code>{nname}</code> · '
          f'{tfile} · suffix {suf} / full-match {fm}</summary>')
    parts=[f"<details>\n{head}\n"]
    if tcode:
        parts.append(f"\n**대상 `{name}`** — `{tfile}`\n\n```coq\n{tcode}\n```\n")
    else:
        parts.append(f"\n**대상 `{name}`**: (코드 추출 실패 — 위치 특정 불가)\n")
    if ncode:
        parts.append(f"\n**이웃 `{nname}`** — `{nfile}`\n\n```coq\n{ncode}\n```\n")
    else:
        parts.append(f"\n**이웃 `{nname}`**: (코드 추출 실패)\n")
    parts.append("\n</details>\n")
    return "".join(parts)

def main():
    # 표 순서(suffix 내림차순 근사)와 무관하게 ROWS 순서대로
    blocks=[block(idx,name,tfile,nb) for idx,name,tfile,nb in ROWS]
    ok=sum(1 for b in blocks if "코드 추출 실패" not in b or b.count("코드 추출 실패")<2)
    section=("\n\n## 6.1 부록 코드 대조 (접기/펴기)\n\n"
             "> 아래 각 항목을 클릭하면 대상 정리와 이웃 정리의 **실제 Coq 코드**가 펼쳐진다.\n"
             "> (긴 증명은 90줄에서 잘림). 표(§6)의 80건과 1:1 대응.\n\n"
             + "\n".join(blocks) + "\n")
    txt=open(MD, encoding="utf-8").read()
    # 이미 있으면 교체
    marker="## 6.1 부록 코드 대조"
    if marker in txt:
        txt=txt[:txt.index("## 6.1 부록 코드 대조")].rstrip()+"\n"
    open(MD,"w",encoding="utf-8").write(txt.rstrip()+section)
    print(f"완료: {len(blocks)}개 toggle 블록 추가. 코드추출 성공(양쪽) 근사: {sum(1 for b in blocks if b.count('추출 실패')==0)}")

if __name__=="__main__":
    main()
