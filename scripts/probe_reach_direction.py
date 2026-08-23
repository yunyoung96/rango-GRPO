#!/usr/bin/env python3
"""★ 결손 이름은 **어느 방향으로도** 안 닿는다 — 주입이 왜 못 잡는지의 근거.

두 방향을 구분해야 한다.

    아래로(unfold)   goal 의 이름 → 그 정의 → 그 정의가 쓰는 이름 → …
                     = goal 이 **무엇으로 만들어졌나**. `[TYPES]`/`[DEFINITIONS]` 가 이것이다.
    위로(mention)    goal 의 어휘를 **언급하는** 선언들.
                     = goal 에 **관한** 정리. 검색기가 맡는 방향이다.

실측(대표 사례): 아래로 depth 3 까지 못 닿고, 위로도 **어휘 교집합이 공집합**이라
후보에조차 안 든다. 필요한 lemma 는 goal 의 재료도 아니고 goal 의 어휘를 쓰지도 않는다.

사용: python3 scripts/probe_reach_direction.py [cases.json]
      (없으면 내장 대표 사례로 돈다)
"""
import json
import re
import sqlite3
import sys

sys.path.insert(0, "scripts")
from _coq_vocab import is_core  # noqa: E402

DB = "raw-data/coq-dataset/sentences.db"
FD = json.load(open("data/func_defs_v3.json"))
_PROJ = re.compile(r"(?:^|/)repos/([^/]+)/")
_HEAD = re.compile(
    r"^\s*(?:#\[[^\]]*\]\s*)?(?:Global\s+|Local\s+|Polymorphic\s+|Program\s+)*"
    r"(?:Lemma|Theorem|Definition|Fixpoint|Inductive|Record|Class|Instance|"
    r"Corollary|Fact|Axiom|Variant|Structure)\s+([A-Za-z_][\w']*)")


def ids(t):
    return {w for w in re.findall(r"[A-Za-z_][\w']*", t or "")
            if len(w) >= 3 and not is_core(w)}


def unfold(seed, proj, depth=3):
    """아래로 — 정의를 따라 재귀적으로 펼친다."""
    seen, frontier = set(), set(seed)
    for _ in range(depth):
        nxt = set()
        for n in frontier:
            if n in seen:
                continue
            seen.add(n)
            for fp, d in (FD.get(n) or {}).items():
                if fp == "stdlib" or fp.split("/")[0] == proj:
                    nxt |= ids(d)
        frontier = nxt - seen
        if not frontier:
            break
    return seen | frontier


def run(cases):
    """★ 세 경로를 잰다.
        아래로      goal 이름 → 정의 펼치기 (= [DEFINITIONS] 가 하는 일)
        위로        goal 어휘를 언급하는 선언 (= 검색기)
        아래1+위로  goal 을 **한 걸음 펼친 뒤** 언급 검색 ← 실제로 닿는 경로
    """
    c = sqlite3.connect(DB)
    cache = {}
    n_down = n_up = n_du = n_tot = 0
    fans = []
    print(f"   {'이름':22s} {'goal id':>7s} {'아래d3':>6s} {'위로':>6s} "
          f"{'위로적중':>8s} | {'아래1+위로 후보':>14s} {'적중':>5s}")
    for nm, proj, goal in cases:
        G = ids(goal)
        down = nm in unfold(G, proj)
        if proj not in cache:
            cache[proj] = c.execute(
                "select text from sentence where file_path like ?",
                (f"%/repos/{proj}/%",)).fetchall()
        up_names, decl = set(), None
        for (t,) in cache[proj]:
            m = _HEAD.match(t or "")
            if m and m.group(1) == nm:
                decl = t
            if ids(t) & G and m:
                up_names.add(m.group(1))
        # ★ 아래로 **한 걸음** 펼친 개념집합으로 위로 검색
        D1 = unfold(G, proj, depth=1)
        du_names = set()
        for (t,) in cache[proj]:
            m = _HEAD.match(t or "")
            if m and (ids(t) & D1):
                du_names.add(m.group(1))
        hit_du = nm in du_names
        n_tot += 1
        n_down += bool(down)
        n_up += (nm in up_names)
        n_du += hit_du
        if hit_du:
            fans.append(len(du_names))
        print(f"   {nm:22s} {len(G):7d} {str(down):>6s} {len(up_names):6d} "
              f"{str(nm in up_names):>8s} | {len(du_names):14,} {str(hit_du):>5s}")
    print(f"\n   아래로만        닿음 {n_down}/{n_tot} = {n_down/max(n_tot,1)*100:.1f}%")
    print(f"   위로만          닿음 {n_up}/{n_tot} = {n_up/max(n_tot,1)*100:.1f}%")
    print(f"   ★ 아래1+위로    닿음 {n_du}/{n_tot} = {n_du/max(n_tot,1)*100:.1f}%")
    if fans:
        fans.sort()
        print(f"   그때의 후보 수  중앙 {fans[len(fans)//2]:,} · p25 {fans[len(fans)//4]:,} "
              f"· p75 {fans[3*len(fans)//4]:,} · 최대 {fans[-1]:,}   (예산 ≈22개)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        d = json.load(open(sys.argv[1]))
        cs = []
        for cse in d["cases"]:
            m = _PROJ.search(cse["file"])
            if not m:
                continue
            g = re.search(r"\[STATE\]\n(.*?)(?=\n\[[A-Z]+\]|\Z)", cse["vp"], re.S)
            goal = g.group(1) if g else ""
            for dg in cse["diag"]:
                cs.append((dg["name"].split(".")[-1], m.group(1), goal))
        run(cs)
    else:
        run([
            ("isequiv_adjointify", "HoTT-Coq-HoTT",
             "IsPullback (fun z : {d : D & P d * Q d} => 1 : (z.1; fst z.2).1 = (z.1; snd z.2).1)"),
            ("cancelL", "HoTT-Coq-HoTT",
             "ap (Colimit_rec P C) (colimp i j g x) = legs_comm C i j g x"),
            ("cs_bin_op_strext", "coq-community-corn", "x [#] [0] or y [#] [0]"),
        ])
