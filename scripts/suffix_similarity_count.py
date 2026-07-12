#!/usr/bin/env python3
"""1000(=전체 test) 정리 중 'suffix가 비슷한 sibling'을 가진 정리 개수 계산.
기준(§6 재현): 두 정리 proof를 끝에서 정렬 → tactic-head 공통 suffix ≥ HS,
그중 full-tactic(문자열 완전일치) ≥ FM. sibling은 다른 정리.
tactic 분할 = split_steps(세미콜론 보존). head = 선행 식별자.
"""
import json, re, os, importlib.util, sys
HERE="scripts"
def L(m,p):
    s=importlib.util.spec_from_file_location(m,os.path.join(HERE,p)); x=importlib.util.module_from_spec(s); s.loader.exec_module(x); return x
cov=L("cov","poc_coverage.py"); reach=L("reach","poc_prefix_reach.py")

HS=int(sys.argv[1]) if len(sys.argv)>1 else 4   # head-suffix 최소
FM=int(sys.argv[2]) if len(sys.argv)>2 else 3   # full-match 최소

allj=json.load(open("results/compcert_report/all.json"))["results"]

def head(t):
    m=re.match(r"\s*([A-Za-z_][A-Za-z_0-9']*)", t)
    return m.group(1) if m else t.strip()[:8]

def proof_steps(rec):
    try:
        lines=cov.read(rec["file"])
    except Exception:
        return None
    ps=rec.get("proof_span")
    if not ps: return None
    s=ps["start"]["line"]; e=ps["end"]["line"]
    body="\n".join(lines[s:e+1])
    body=re.sub(r'\bProof\b\s*\.', '', body)
    body=re.sub(r'\b(Qed|Defined|Admitted)\b\s*\.', '', body)
    st=reach.split_steps(body)
    return st if st else None

# 코퍼스 구축
items=[]  # (idx, file, steps, heads, success)
for r in allj:
    st=proof_steps(r)
    if st and len(st)>=HS:
        items.append((r["idx"], r["file"], st, [head(t) for t in st], r.get("success")))
print(f"코퍼스: {len(items)} proofs (tactic≥{HS})  기준 HS≥{HS}, FM≥{FM}")

# last-head 버킷으로 후보 제한(공통 suffix≥1 필요조건)
from collections import defaultdict
bucket=defaultdict(list)
for i,it in enumerate(items):
    bucket[it[3][-1]].append(i)

def match_len(a_heads,b_heads,a_st,b_st):
    """끝에서 정렬한 head 공통 suffix 길이 hs, 그 구간 full-match 수 fm."""
    n=min(len(a_heads),len(b_heads)); hs=0
    while hs<n and a_heads[-1-hs]==b_heads[-1-hs]:
        hs+=1
    if hs<HS: return hs,0
    fm=sum(1 for k in range(hs) if a_st[-1-k]==b_st[-1-k])
    return hs,fm

qual=[]  # (idx, best_sibling_idx, hs, fm, success)
for i,it in enumerate(items):
    idx,f,st,hd,succ=it
    best=None
    for j in bucket[hd[-1]]:
        if j==i: continue
        jt=items[j]
        if jt[0]==idx: continue
        hs,fm=match_len(hd,jt[3],st,jt[2])
        if hs>=HS and fm>=FM:
            if best is None or (hs,fm)>(best[2],best[3]):
                best=(idx,jt[0],hs,fm,succ)
    if best: qual.append(best)

total=len(qual)
failed=[q for q in qual if q[4] is False]
succ_q=[q for q in qual if q[4] is True]
print(f"\n=== 결과 ===")
print(f"suffix 유사 sibling 보유 정리: {total} / {len(items)}  ({100*total/len(items):.1f}%)")
print(f"  ├ rango 실패(❌) 중: {len(failed)}   (←§6의 80건에 대응, 검증용)")
print(f"  └ rango 성공(✅) 중: {len(succ_q)}")
# 상위 예시
qual.sort(key=lambda q:(-q[2],-q[3]))
print("상위 예시 (idx→sibling, hs/fm):")
for q in qual[:12]:
    print(f"  idx {q[0]:4d} → {q[1]:4d}  suffix {q[2]:2d} / full {q[3]:2d}  {'❌' if q[4] is False else '✅'}")
