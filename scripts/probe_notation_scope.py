#!/usr/bin/env python3
"""★ **파일 밖 notation 을 goal 로 걸러서** 넣을 수 있는가.

파일 내 notation 은 이미 주입한다(중앙 0개 · p90 552토큰). 그런데 실측 결손 사례
`intu`(goal `A |-I phi`) · `ZeroR` · `E_IfFalse`(goal `st =[ c ]=> st'`) 는 전부
**파일 밖 notation** 이 이름을 가린 것이다. 파일 밖은 중앙 194개라 통째로는 못 넣는다.

여기서 재는 것: notation 의 **기호(anchor)** 가 goal 에 실제로 나타나는 것만 고르면
몇 개가 남는가. 남는 게 한 줌이면 **정밀 주입**이 된다.

    Notation "A |-I phi" := (prv intu A phi)
              ^^^^ anchor 가 goal 에 있는가

사용: PYTHONPATH=src python3 scripts/probe_notation_scope.py
"""
import collections
import json
import re
import sqlite3
import sys

DB = "raw-data/coq-dataset/sentences.db"

# ── notation 키에서 anchor 를 뽑는다 ────────────────────────────────────────────
#   "A |-I phi"        → ['|-I']          (기호 덩어리)
#   "'if' c 'is' p"    → ["'if'","'is'"]  (따옴표 키워드)
#   "st =[ c ]=> st'"  → ['=[', ']=>']
_KEY = re.compile(r'Notation\s+"([^"]+)"')
_RHS = re.compile(r':=\s*\(?\s*([A-Za-z_][\w\']*(?:\.[A-Za-z_][\w\']*)*)')
_WHERE = re.compile(r'where\s+"([^"]+)"\s*:=\s*\(?\s*([A-Za-z_][\w\']*)')
# 너무 흔해 anchor 로 쓸 수 없는 것 — 거의 모든 goal 에 있다
_TOO_COMMON = {
    "=", "->", "<-", "*", "+", "-", "/", "(", ")", ",", ":", ";", "|", "_",
    "<", ">", "<=", ">=", "/\\", "\\/", "~", "@", "'", '"', "{", "}", "[", "]",
    "==", "<>", "^", "%", "&", "&&", "||", "::", "++", ".", "..",
}


def anchors(key: str) -> list:
    """notation 키에서 **식별력 있는** 기호·키워드만."""
    out = []
    for q in re.findall(r"'([^']+)'", key):          # 'if' 'then' 같은 키워드
        if len(q) >= 2:
            out.append(q)
    stripped = re.sub(r"'[^']*'", " ", key)
    for sym in re.findall(r"[^\w\s]+", stripped):
        sym = sym.strip()
        # `|-I` 처럼 기호+글자가 붙은 것도 잡아야 한다 → 원본에서 다시 확인
        if sym and sym not in _TOO_COMMON and len(sym) >= 2:
            out.append(sym)
    for sym in re.findall(r"[^\w\s]+[A-Za-z]\b", stripped):   # |-I, =[ ... ]=>
        s = sym.strip()
        if s and s not in _TOO_COMMON:
            out.append(s)
    return sorted(set(out), key=len, reverse=True)


def build():
    c = sqlite3.connect(DB)
    rows = c.execute(
        "select text, file_path from sentence "
        "where sentence_type like '%NOTATION%' or sentence_type like '%INDUCTIVE%'"
    ).fetchall()
    idx = collections.defaultdict(list)          # anchor -> [(key, head, text, file)]
    n_nota = 0
    for text, fp in rows:
        pairs = []
        m = _KEY.search(text or "")
        if m:
            h = _RHS.search(text, m.end())
            pairs.append((m.group(1), h.group(1) if h else None))
        for k, h in _WHERE.findall(text or ""):   # Inductive ... where "A /\ B" := (and A B)
            pairs.append((k, h))
        for key, head in pairs:
            if not head:
                continue
            n_nota += 1
            for a in anchors(key):
                if len(idx[a]) < 40:
                    idx[a].append((key, head, (text or "").strip(), fp))
    return idx, n_nota


def hits(idx, goal, limit=8):
    """goal 에 anchor 가 나타나는 notation 들."""
    out, seen = [], set()
    for a, lst in idx.items():
        if a in goal:
            for key, head, text, fp in lst:
                k = (key, head)
                if k in seen:
                    continue
                seen.add(k)
                out.append((len(a), a, key, head, text, fp))
    out.sort(key=lambda x: -x[0])
    return out[:limit], len(seen)


if __name__ == "__main__":
    idx, n = build()
    print(f"■ notation/where 색인  {n:,}개 · anchor {len(idx):,}종\n")
    CASES = [
        ("intu",       "A ⊢I phi -> valid_ctx A phi"),
        ("intu(ascii)", "A |-I phi -> valid_ctx A phi"),
        ("E_IfFalse",  "(X !-> 2) =[ if X <= 1 then Y := 3 else Z := 4 end ]=> (Z !-> 4; X !-> 2)"),
        ("ZeroR",      "Six [*] K [#] [0]"),
        ("cs_bin_op_strext", "x [#] [0] or y [#] [0]"),
        ("merely",     "Tr (-1) (hfiber (cxfib ...))"),
        ("setU2_2",    "inc t (range x \\cup range y)"),
    ]
    for name, goal in CASES:
        h, tot = hits(idx, goal)
        found = any(head == name for _, _, _, head, _, _ in h)
        print(f"── {name:20s} anchor 매치 {tot:4d}개   "
              f"{'★ 이름 복원됨' if found else ''}")
        for _, a, key, head, text, fp in h[:4]:
            mark = "★" if head == name else " "
            print(f"   {mark} anchor {a!r:12s} \"{key[:34]:34s}\" → {head}")
        print()
