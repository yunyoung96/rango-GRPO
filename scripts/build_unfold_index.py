#!/usr/bin/env python3
"""★ **역인덱스** — goal 에 보이는 것이 정의의 **본문**일 때 그 이름을 되찾는다.

실측 결손 사례(덤프 [3]):
    goal   `Tr (-1) (hfiber ...)`
    정답   `assert (f : merely (hfiber grp_quotient_map y))`
    정의   `Definition merely (A : Type) : HProp := Build_HProp (Tr (-1) A).`

goal 에는 **펼쳐진 형태**(`Tr (-1) _`)가 보이고 정답은 **접힌 이름**(`merely`)을 쓴다.
지금 `[DEFINITIONS]` 씨앗은 "goal 에 나오는 **이름**" 으로만 확장하므로 `merely` 에
영영 못 닿는다. 방향을 뒤집어 **본문 조각 → 이름** 으로 색인한다.

조각 만드는 법: 본문의 각 식별자에서 시작해 **바인더에 묶인 변수를 만날 때까지**
확장하고 괄호를 맞춘다. 토큰 2개 이상만 남긴다 — 홑이름(`hfiber`)은 잡음이다.

    Build_HProp (Tr (-1) A)   A 는 바인더
      → `Tr(-1)`              ★ goal 에 그대로 있다
      → `Build_HProp` 은 1토큰이라 버림

출력 data/unfold_index.json  {proj: {fragment: [name, ...]}}
사용: python3 scripts/build_unfold_index.py
"""
import collections
import json
import re

FD_PATH = "data/func_defs_v3.json"
OUT = "data/unfold_index.json"

_CORE = {"forall", "fun", "match", "with", "end", "let", "in", "if", "then", "else",
         "return", "as", "Type", "Prop", "Set", "SProp", "and", "or", "not", "exists",
         "of", "is", "at", "by", "where", "struct", "for"}
_TOK = re.compile(r"[A-Za-z_][\w'.]*|\(|\)|\d+|[^\sA-Za-z_()\d]+")


def fragments(defn: str, name: str) -> list:
    d = re.sub(r"@\{[^}]*\}", "", defn or "")
    i = d.find(":=")
    if i < 0:
        return []
    head, body = d[:i], d[i + 2:].strip().rstrip(".")
    bound = set()
    for grp in re.findall(r"[({]([^:(){}]*):", head):        # (A : Type) {B : Type}
        bound |= set(re.findall(r"[A-Za-z_][\w']*", grp))
    bound |= set(re.findall(r"\b([A-Za-z_][\w']*)\s*:(?!=)", body))   # fun x : T =>
    bound.add(name)
    toks = [m.group(0) for m in _TOK.finditer(body)]
    out = []
    for i0, t0 in enumerate(toks):
        if not re.match(r"[A-Za-z_]", t0) or t0 in bound or t0 in _CORE:
            continue
        acc, depth = [], 0
        for t in toks[i0:]:
            if re.match(r"[A-Za-z_]", t) and (t in bound or t in _CORE):
                break
            if t == "(":
                depth += 1
            elif t == ")":
                if depth == 0:
                    break
                depth -= 1
            acc.append(t)
            if len(acc) > 14:
                break
        while acc and depth > 0:                 # 남은 여는 괄호를 잘라 균형을 맞춘다
            if acc.pop() == "(":
                depth -= 1
        if len(acc) < 2:
            continue
        f = "".join(acc)                          # ★ 공백 무시 매칭
        # ★ 잡음 차단: 1글자 식별자들이 이어붙어 `oto`·`om` 같은 가짜 조각이 생겼고
        #   그게 goal 아무 데나 걸렸다. **3글자 이상 식별자를 최소 하나** 요구한다.
        # ★ 잡음의 정체는 **1글자 식별자가 이어붙은 것**이었다(`o`+`to` → `oto` 가
        #   goal 아무 데나 걸렸다). 길이가 아니라 **1글자 식별자 자체를 막는다** —
        #   길이로 자르면 `Tr(-1)`(=merely 의 단서) 까지 같이 죽는다.
        if len(f) < 5:
            continue
        ids = [t for t in acc if re.match(r"[A-Za-z_]", t)]
        if not ids or any(len(t) < 2 for t in ids):
            continue
        out.append(f)
    return list(dict.fromkeys(out))


def main():
    FD = json.load(open(FD_PATH))
    idx = collections.defaultdict(lambda: collections.defaultdict(set))
    n = 0
    for nm, byfile in FD.items():
        for fp, dn in byfile.items():
            proj = fp.split("/")[0]
            if proj == "stdlib":
                continue
            for f in fragments(dn, nm):
                idx[proj][f].add(nm)
                n += 1
    # 한 프로젝트에서 **너무 많은 이름**이 걸리는 조각은 식별력이 없다 → 버린다
    out, kept, dropped = {}, 0, 0
    for proj, m in idx.items():
        keep = {f: sorted(v)[:4] for f, v in m.items() if len(v) <= 4}
        dropped += len(m) - len(keep)
        kept += len(keep)
        if keep:
            out[proj] = keep
    json.dump(out, open(OUT, "w"), ensure_ascii=False)
    import os
    print(f"■ {OUT}  {os.path.getsize(OUT)/1e6:.1f} MB")
    print(f"   프로젝트 {len(out):,} · 조각 {kept:,} (모호해서 버림 {dropped:,}) · 총생성 {n:,}")


if __name__ == "__main__":
    main()
