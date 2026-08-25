#!/usr/bin/env python3
"""★ **펑터 인스턴스 맵** — 프로젝트별 `F -> [N, …]`.

`Module N := F(A).` 한 줄이 `N.member` 를 만들어 내는데 그 이름은 소스에 선언이 없다
(`docs/premise/functor-names.md`). 검색 풀에서 그 이름을 되살리려면
"이 프로젝트에서 펑터 F 의 인스턴스가 누구누구인가"만 알면 된다 — 그 맵을 만든다.

전개 인덱스(`build_functor_index.py`)와 달리 **명제를 복제하지 않는다.**
풀에 이미 있는 F 의 선언을 런타임에 N 이름으로 복제하므로 맵만 있으면 된다(수십 KB).

사용: python3 scripts/build_functor_instances.py <repos_root> <out.json>
"""
import collections
import glob
import json
import os
import re
import sys

ROOT, OUT = sys.argv[1], sys.argv[2]
INST = re.compile(
    r"(?m)^\s*Module\s+([A-Za-z_][\w']*)\s*(?::\s*[\w'.]+\s*|<:\s*[\w'.]+\s*)?"
    r":=\s*([A-Za-z_][\w'.]*)\s*\(")
out: dict = {}
n = 0
for f in glob.glob(os.path.join(ROOT, "**", "*.v"), recursive=True):
    rel = os.path.relpath(f, ROOT)
    proj = rel.split(os.sep)[0]
    try:
        s = re.sub(r"\(\*.*?\*\)", " ", open(f, errors="ignore").read(), flags=re.S)
    except Exception:
        continue
    for m in INST.finditer(s):
        N, F = m.group(1), m.group(2).split(".")[-1]
        out.setdefault(proj, {}).setdefault(F, [])
        if N not in out[proj][F]:
            out[proj][F].append(N); n += 1
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=0)
print(f"■ 프로젝트 {len(out)}종 · 인스턴스 {n}건 → {OUT}")
for p, d in sorted(out.items(), key=lambda kv: -sum(len(v) for v in kv[1].values()))[:6]:
    tot = sum(len(v) for v in d.values())
    print(f"   {tot:3d}  {p[:46]}  예: " +
          ", ".join(f"{k}→{v[:3]}" for k, v in list(d.items())[:2]))
