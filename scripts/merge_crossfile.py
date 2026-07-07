#!/usr/bin/env python3
"""cross-file 평가 결과(CPU 분류 + 모델 수리)를 composed_final_merged.json 에 병합.
→ '이식 —(미평가)'였던 타 파일 항목들이 실제 status 로 갱신됨."""
import re, json, os
HERE=os.path.dirname(__file__)
SC="/tmp/claude-0/-app-coq-modeling/6331508b-8918-46d1-8fc8-94a923df1143/scratchpad/"
CM=os.path.join(HERE,"..","results","compcert_report","composed_final_merged.json")

def parse(path):
    d={}
    if not os.path.exists(path): return d
    for ln in open(path,errors="ignore"):
        if "Loading" in ln or "Materializing" in ln: continue
        m=re.search(r"idx=(\d+)\s+(\S+)\s+(PASS|STUCK|NOFIX|NOSTATE|SKIP_BIG)\b(.*)", ln)
        if not m: continue
        reach=""
        rm=re.search(r"(\d+/\d+)", m.group(4))
        if rm: reach=rm.group(1)
        d[int(m.group(1))]=(m.group(3), m.group(2), reach)
    return d

# CPU 분류(전체 base) → 모델 결과(유망 override)
base={}
for f in ["crossfile_nm","crossfile","crossfile2"]:
    base.update(parse(SC+f+".log"))
model=parse(SC+"cf_model.log")
cross={**base, **model}   # model 이 우선

cm=json.load(open(CM))
added=0
for idx,(st,name,reach) in cross.items():
    cm[str(idx)]=[st, name, reach]; added+=1
json.dump(cm, open(CM,"w"), ensure_ascii=False, indent=1)

from collections import Counter
print(f"cross-file 병합: {added}건")
print("전체 composed 분포:", Counter(v[0] for v in cm.values()))
print("cross PASS:", sorted([i for i,(st,n,r) in cross.items() if st=="PASS"]))
