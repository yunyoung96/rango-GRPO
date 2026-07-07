#!/usr/bin/env python3
"""
§6.2 — 각 정리에 대해 '원래 rango 증명이 어디서 막혔는지' 추출·toggle 생성.
rango run 로그(all_results/20260701-061839/logs/<idx>.txt)에서:
  - 검색 스텝 수(= '선택된 tactic' 횟수): 얼마나 많이 시도하고도 못 닫았나
  - 막힌 goal(마지막 'focused_goal ⊢ ...')
  - 포기 직전 누적 부분증명(끝의 Proof. 블록)
큰 로그(수백만 줄)도 grep/tail 로 효율 추출.
"""
import json, os, re, subprocess, html
import importlib.util
HERE=os.path.dirname(__file__)
# §6.1 생성기에서 하이라이터/상태배지 재사용
_s=importlib.util.spec_from_file_location("ga", os.path.join(HERE,"gen_appendix_code.py"))
ga=importlib.util.module_from_spec(_s); _s.loader.exec_module(ga)
highlight=ga.highlight; PRE_STYLE=ga.PRE_STYLE; status_badge=ga.status_badge
ROWS=json.load(open("/tmp/claude-0/-app-coq-modeling/6331508b-8918-46d1-8fc8-94a923df1143/scratchpad/suffix_rows.json"))
LOGDIR=os.path.join(HERE,"..","all_results","20260701-061839","logs")
MD=os.path.join(HERE,"..","results","compcert_report","suffix_transplant_analysis.md")

def _pre_hl(code):
    lines=[l for l in (code or "").split("\n") if l.strip()!=""]
    if not lines: return f'<pre style="{PRE_STYLE}"><code>(추출 실패)</code></pre>'
    return f'<pre style="{PRE_STYLE}"><code>'+highlight("\n".join(lines))+"</code></pre>"

def sh(cmd):
    try: return subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=60).stdout
    except Exception: return ""

def extract(idx):
    f=os.path.join(LOGDIR,f"{idx}.txt")
    if not os.path.exists(f): return None
    steps=sh(f"grep -ac '선택된 tactic' {f}").strip()
    valid=sh(f"grep -ac 'TacticResult.VALID' {f}").strip()
    goal=sh(f"grep -a 'focused_goal ⊢' {f} | tail -1").strip()
    goal=re.sub(r'^\s*쿼리 focused_goal ⊢\s*','',goal)
    # 끝의 누적 Proof. 블록: 마지막 400줄에서 마지막 'Proof.' 이후 tactic 유사 라인
    tail=sh(f"tail -400 {f}")
    tl=tail.split("\n")
    # 마지막 Proof. 위치
    pi=max((i for i,l in enumerate(tl) if l.strip()=="Proof." or l.strip().startswith("Proof.")), default=None)
    proof=[]
    if pi is not None:
        for l in tl[pi:]:
            s=l.rstrip()
            if s.strip() in ("server quit","failed") or s.startswith("# cmd"): break
            # retrieval/디버그 라인 제외: 들여쓰기 tactic 또는 Proof./Qed. 만
            if s.strip().startswith(("쿼리","Top","item_ids","매칭","전체 후보","[","→","-",".")) and not s.strip().startswith("-)"):
                # tactic 라인은 대개 소문자로 시작하는 들여쓰기; 위 마커는 스킵
                if any(m in s for m in ("쿼리","Top","item_ids","매칭 IDs","전체 후보","Retrieval","선택된","결과:")): continue
            proof.append(s)
        # 뒤쪽 빈줄/비proof 정리
        while proof and not proof[-1].strip(): proof.pop()
    endmark = "server quit" if "server quit" in tail else ("failed" if "failed" in tail else "timeout")
    return {"steps":steps or "?","valid":valid or "?","goal":goal[:400],"proof":"\n".join(proof[:40]),"end":endmark}

def block(idx,name,nb):
    e=extract(idx)
    name=name or "None"
    if not e:
        return f"<details>\n<summary><b>idx {idx}</b> · <code>{name}</code> — 로그 없음</summary>\n<pre style=\"{PRE_STYLE}\"><code>(run 로그 미존재)</code></pre>\n</details>\n"
    head=(f'<summary><b>idx {idx}</b> · <code>{name}</code> · '
          f'rango: {e["steps"]}회 시도(VALID {e["valid"]}) → <b>{e["end"]}</b> · <b>{status_badge(idx)}</b></summary>')
    # 좌우 2열: 막힌 goal | 포기 직전 누적 부분증명
    tbl=("<table><thead><tr>"
         "<th align=\"left\">막힌 goal (마지막 focused_goal)</th>"
         "<th align=\"left\">포기 직전 누적 부분증명</th>"
         "</tr></thead><tbody><tr>"
         f"<td valign=\"top\">{_pre_hl(e['goal'])}</td>"
         f"<td valign=\"top\">{_pre_hl(e['proof'])}</td>"
         "</tr></tbody></table>")
    return f"<details>\n{head}\n{tbl}\n</details>\n"

def main():
    blocks=[]
    for idx,name,tfile,nb in ROWS:
        blocks.append(block(idx,name,nb))
    section=("\n\n## 6.2 원래 rango 증명이 어디서 막혔나 (접기/펴기)\n\n"
             "> rango 실패는 전부 `valid_but_stuck`(COMPLETE 0건) — 즉 **유효한 tactic 을 계속 두면서도\n"
             "> 정해진 시간(≈600s) 안에 증명을 못 닫음**. 아래는 각 정리에서 rango 가 (1)몇 번 tactic 을\n"
             "> 시도했고 (2)어떤 goal 에서 막혔으며 (3)포기 직전 어떤 부분증명을 쌓았는지. §6/§6.1 의 80건과 대응.\n"
             "> → 이식(transplant)은 이 '못 닫은 tactic 꼬리'를 형제 증명에서 통째로 가져와 메우려는 것.\n\n"
             + "\n".join(blocks) + "\n")
    txt=open(MD,encoding="utf-8").read()
    if "## 6.2 원래 rango" in txt:
        txt=txt[:txt.index("## 6.2 원래 rango")].rstrip()+"\n"
    open(MD,"w",encoding="utf-8").write(txt.rstrip()+section)
    print(f"완료: §6.2 {len(blocks)}개 블록 추가.")

if __name__=="__main__":
    main()
