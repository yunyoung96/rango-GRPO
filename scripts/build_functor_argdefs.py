#!/usr/bin/env python3
"""★ 인자 모듈의 `Definition t := τ` 맵 — 전개된 이름의 추상 타입을 구체화한다.

`Module Pregmap := EMap(PregEq).` 이고 `PregEq` 안에 `Definition t := preg.` 이면
`Pregmap` 의 `elt`(=`X.t`)는 `preg` 다. 그걸 알아야 전개된 명제가 goal 과
어휘가 맞아 랭킹에 올라온다(실측: 치환 전 735위).

내는 것: {프로젝트: {인스턴스이름 N: {"t": τ}}}
사용: python3 scripts/build_functor_argdefs.py <repos_root> <out.json>
"""
import glob, json, os, re, sys
ROOT, OUT = sys.argv[1], sys.argv[2]
INST = re.compile(r"(?m)^\s*Module\s+([A-Za-z_][\w']*)\s*(?::\s*[\w'.]+\s*|<:\s*[\w'.]+\s*)?"
                  r":=\s*([A-Za-z_][\w'.]*)\s*\(\s*([A-Za-z_][\w'.]*)")
MOD  = re.compile(r"(?ms)^\s*Module\s+([A-Za-z_][\w']*)\s*\.\s*(.*?)^\s*End\s+\1\s*\.")
DEFT = re.compile(r"(?m)^\s*Definition\s+t\s*:?=\s*(.+?)\.\s*$")
out={}; n=0
for f in glob.glob(os.path.join(ROOT,"**","*.v"), recursive=True):
    proj=os.path.relpath(f,ROOT).split(os.sep)[0]
    try: s=re.sub(r"\(\*.*?\*\)"," ",open(f,errors="ignore").read(),flags=re.S)
    except Exception: continue
    # 같은 파일 안의 인자 모듈 정의를 모은다(대개 인접해 있다)
    argdef={m.group(1): DEFT.search(m.group(2)).group(1).strip()
            for m in MOD.finditer(s) if DEFT.search(m.group(2))}
    for m in INST.finditer(s):
        N, A = m.group(1), m.group(3).split(".")[-1]
        tau = argdef.get(A)
        if tau and len(tau) < 40 and re.fullmatch(r"[A-Za-z_][\w'.]*", tau):
            out.setdefault(proj, {})[N] = {"t": tau}; n+=1
json.dump(out, open(OUT,"w"), ensure_ascii=False, indent=0)
print(f"■ 프로젝트 {len(out)} · 구체화 가능한 인스턴스 {n}건 → {OUT}")
for p,d in sorted(out.items(), key=lambda kv:-len(kv[1]))[:5]:
    print(f"   {len(d):3d}  {p[:40]}  예: {dict(list(d.items())[:3])}")
